"""
KlausulaAI - Generator: Answer Synthesis

Menghasilkan jawaban dalam Bahasa Indonesia yang sederhana dan praktis
berdasarkan chunk-chunk yang sudah lolos relevance grading.

Target audiens: pelaku UMKM — bukan ahli hukum.
Menggunakan gemini-1.5-pro (temperature=0.7) untuk jawaban yang natural.
"""

from typing import Optional

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


def _format_history(chat_history: Optional[list[dict]]) -> str:
    if not chat_history:
        return "(Tidak ada riwayat, ini pertanyaan pertama)"
    parts = []
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "Asisten"
        parts.append(f"{role}: {msg['content']}")
    return "\n".join(parts)


def _format_instruction(system_instruction: Optional[str]) -> str:
    """Instruksi khusus per-project (kolom projects.master_prompt) yang ditetapkan
    user saat membuat project. Disuntikkan ke system prompt generator. Kosong =
    tidak ada instruksi khusus → string kosong (tidak mengubah perilaku default)."""
    if not system_instruction or not system_instruction.strip():
        return ""
    return (
        "\n──────────────────────────────────────────────────────────────────────\n"
        "INSTRUKSI KHUSUS PROJECT (ditetapkan pengguna untuk project ini) — IKUTI "
        "selama tidak bertentangan dengan aturan relevansi & kejujuran di atas:\n"
        f"{system_instruction.strip()}\n"
        "──────────────────────────────────────────────────────────────────────"
    )


def generate_answer(
    query: str,
    chunks: list[dict],
    chat_history: Optional[list[dict]] = None,
    system_instruction: Optional[str] = None,
) -> str:
    return _chain.invoke(
        {
            "context": _format_context(chunks),
            "question": query,
            "history": _format_history(chat_history),
            "project_instruction": _format_instruction(system_instruction),
        }
    )


def generate_answer_stream(
    query: str,
    chunks: list[dict],
    chat_history: Optional[list[dict]] = None,
    system_instruction: Optional[str] = None,
):
    payload = {
        "context": _format_context(chunks),
        "question": query,
        "history": _format_history(chat_history),
        "project_instruction": _format_instruction(system_instruction),
    }
    for chunk in _chain.stream(payload):
        yield chunk
