"""
KlausulaAI - Grader: Relevance Filtering (CRAG pattern)

Menyaring chunk hasil retrieval sebelum masuk ke generator.
Chunk yang tidak relevan dengan pertanyaan user dibuang agar
generator tidak menghasilkan jawaban yang menyimpang (hallucination).

BATCH GRADING: semua chunk dinilai dalam SATU panggilan LLM (bukan satu
panggilan per chunk). Ini memangkas waktu dari ~80 detik menjadi ~3 detik
dan menghemat kuota Gemini (1 request, bukan 6).

Menggunakan gemini-2.5-flash-lite (temperature=0) untuk penilaian konsisten.
"""

import json
import re

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


def _format_chunks(chunks: list[dict]) -> str:
    """Susun semua chunk jadi satu teks bernomor untuk dinilai sekaligus."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}]\n{chunk['content'].strip()}")
    return "\n\n".join(parts)


def _parse_batch_grades(raw: str, n: int) -> set[int]:
    """Parse array JSON [{"index": i, "relevant": bool}, ...].

    Mengembalikan himpunan index (1-based) yang DIPERTAHANKAN.
    Aturan: sebuah chunk dianggap relevan KECUALI ditandai eksplisit
    `relevant: false` — supaya chunk yang lupa disebut LLM tidak hilang.
    Jika JSON gagal di-parse, fail-open: kembalikan semua index.
    """
    try:
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        data = json.loads(cleaned)

        irrelevant: set[int] = set()
        for item in data:
            idx = item.get("index")
            if isinstance(idx, int) and item.get("relevant") is False:
                irrelevant.add(idx)
        return set(range(1, n + 1)) - irrelevant
    except (json.JSONDecodeError, AttributeError, TypeError):
        # Tidak bisa parse → jangan buang info, anggap semua relevan.
        return set(range(1, n + 1))


def grade_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Filter chunk yang relevan dengan query — SATU panggilan LLM untuk semua chunk.

    Args:
        query  : Pertanyaan asli dari user
        chunks : List chunk dari hasil RRF

    Returns:
        Subset chunks yang dinilai relevan oleh LLM grader (urutan dipertahankan).
    """
    if not chunks:
        return []

    response = _chain.invoke(
        {
            "question": query,
            "chunks": _format_chunks(chunks),
        }
    )
    raw_text = response.content if hasattr(response, "content") else str(response)

    relevant_idx = _parse_batch_grades(raw_text, len(chunks))
    return [chunk for i, chunk in enumerate(chunks, 1) if i in relevant_idx]
