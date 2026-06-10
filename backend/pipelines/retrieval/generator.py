"""
KlausulaAI - Generator: Answer Synthesis

Menghasilkan jawaban dalam Bahasa Indonesia yang sederhana dan praktis
berdasarkan chunk-chunk yang sudah lolos relevance grading.

Target audiens: pelaku UMKM — bukan ahli hukum.
Menggunakan gemini-1.5-pro (temperature=0.7) untuk jawaban yang natural.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.llm_clients import llm_for_generation
from pipelines.retrieval.prompts import GENERATOR_HUMAN, GENERATOR_SYSTEM

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", GENERATOR_SYSTEM),
        ("human", GENERATOR_HUMAN),
    ]
)

_chain = _prompt | llm_for_generation | StrOutputParser()


def _format_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata") or {}

        label_parts = []
        # uu_name ada yang ada, ada yang tidak — fallback ke pasal_id
        if meta.get("uu_name"):
            label_parts.append(meta["uu_name"])
        elif meta.get("pasal_id"):
            # Extract UU code dari pasal_id (misal "uu_33_2014_pasal_64" → "UU 33/2014")
            pasal_id = meta["pasal_id"]
            uu_part = pasal_id.split("_pasal_")[0].replace("_", " ").upper()
            label_parts.append(uu_part)
        
        if meta.get("pasal_number"):
            label_parts.append(f"Pasal {meta['pasal_number']}")
        # ayat_number dihapus — tidak ada di metadata

        header = f"[Sumber {i}: {' - '.join(label_parts)}]" if label_parts else f"[Sumber {i}]"
        parts.append(f"{header}\n{chunk['content'].strip()}")

    return "\n\n".join(parts)


def generate_answer(query: str, chunks: list[dict]) -> str:
    """
    Generate jawaban berdasarkan query dan chunk yang relevan.

    Args:
        query  : Pertanyaan dari pelaku UMKM
        chunks : Chunk yang sudah lolos grading (terurut by relevansi)

    Returns:
        Jawaban dalam Bahasa Indonesia yang mudah dipahami UMKM.
    """
    context = _format_context(chunks)
    return _chain.invoke({"context": context, "question": query})

def generate_answer_stream(query: str, chunks: list[dict]):
    context = _format_context(chunks)
    for chunk in _chain.stream({"context": context, "question": query}):
        yield chunk
