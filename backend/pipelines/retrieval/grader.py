"""
KlausulaAI - Grader: Relevance Filtering (CRAG pattern)

Menyaring chunk hasil retrieval sebelum masuk ke generator.
Chunk yang tidak relevan dengan pertanyaan user dibuang agar
generator tidak menghasilkan jawaban yang menyimpang (hallucination).

Menggunakan gemini-1.5-flash (temperature=0) untuk penilaian yang konsisten.
"""

import json
import time

from langchain_core.prompts import ChatPromptTemplate

from core.llm_clients import llm_for_grading
from pipelines.retrieval.prompts import GRADER_HUMAN, GRADER_SYSTEM

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", GRADER_SYSTEM),
        ("human", GRADER_HUMAN),
    ]
)

_chain = _prompt | llm_for_grading


def _parse_grade(raw: str) -> bool:
    """Parse JSON response dari LLM. Fallback ke True jika gagal parse."""
    try:
        # LLM kadang wrap JSON dengan markdown code block
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(cleaned)
        return bool(result.get("relevant", True))
    except (json.JSONDecodeError, AttributeError):
        # Jika parse gagal, anggap relevan agar tidak kehilangan info penting
        return True


def grade_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Filter chunks yang relevan dengan query dari pelaku UMKM.

    Args:
        query  : Pertanyaan asli dari user
        chunks : List chunk dari hasil RRF

    Returns:
        Subset chunks yang dinilai relevan oleh LLM grader.
        Setiap chunk yang lolos mendapat tambahan key 'grade_reason'.
    """
    relevant = []

    for chunk in chunks:
        response = _chain.invoke(
            {
                "question": query,
                "chunk": chunk["content"],
            }
        )

        raw_text = response.content if hasattr(response, "content") else str(response)
        is_relevant = _parse_grade(raw_text)

        if is_relevant:
            try:
                cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                reason = json.loads(cleaned).get("reason", "")
            except (json.JSONDecodeError, AttributeError):
                reason = ""

            relevant.append({**chunk, "grade_reason": reason})
        
        time.sleep(13)

    return relevant
