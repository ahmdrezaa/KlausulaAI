"""
KlausulaAI - RAG Chain: Orchestrator

Mengorkestrasi seluruh pipeline Hybrid RAG:
  1. Embed query         (text → vector 768-dim)
  2. Vector search       (cosine similarity via pgvector)
  3. BM25 search         (FTS via PostgreSQL ts_rank_cd)
  4. RRF fusion          (gabungkan + re-rank hasil kedua retriever)
  5. Relevance grading   (filter chunk tidak relevan via LLM)
  6. Answer generation   (sintesis jawaban dalam Bahasa Indonesia)

Entry point utama: run_rag()
"""

from typing import Optional

from pipelines.retrieval.generator import generate_answer, generate_answer_stream
from pipelines.retrieval.grader import grade_chunks
from pipelines.retrieval.retriever import bm25_search, embed_query, vector_search
from pipelines.retrieval.rrf import reciprocal_rank_fusion

# Konstanta pipeline
_TOP_K_RETRIEVE = 10   # jumlah kandidat dari tiap retriever
_TOP_N_RRF = 6       # jumlah chunk setelah fusion yang masuk ke grader

_NO_RESULT_MSG = (
    "Maaf, saya tidak menemukan informasi yang relevan untuk pertanyaan Anda. "
    "Coba pertajam pertanyaan Anda, atau konsultasikan langsung dengan ahli hukum atau notaris."
)

_NO_RELEVANT_MSG = (
    "Maaf, informasi yang saya temukan kurang cukup untuk menjawab pertanyaan Anda secara akurat. "
    "Pertimbangkan untuk berkonsultasi dengan ahli hukum atau Dinas Koperasi dan UKM setempat."
)


def run_rag(
    query: str,
    project_id: Optional[str] = None,
) -> dict:
    """
    Jalankan full Hybrid RAG pipeline untuk satu query dari user.

    Args:
        query      : Pertanyaan dari pelaku UMKM (Bahasa Indonesia)
        project_id : UUID project user untuk menyertakan dokumen pribadi mereka.
                     Jika None, hanya dokumen global UU/PP yang dicari.

    Returns:
        dict dengan keys:
            answer              (str)  : Jawaban dalam Bahasa Indonesia
            sources             (list) : Metadata chunk yang dipakai sebagai sumber
            chunks_retrieved    (int)  : Jumlah chunk setelah RRF
            chunks_after_grading(int)  : Jumlah chunk yang lolos grading
    """

def run_rag_stream(query: str, project_id: Optional[str] = None):
    # 1-3: Embed, retrieve, RRF (SAMA seperti run_rag)
    query_embedding = embed_query(query)
    vector_results = vector_search(query_embedding, top_k=_TOP_K_RETRIEVE, project_id=project_id)
    bm25_results = bm25_search(query, top_k=_TOP_K_RETRIEVE, project_id=project_id)
    fused_chunks = reciprocal_rank_fusion(vector_results, bm25_results, top_n=_TOP_N_RRF)

    # Kalau tidak ada hasil → yield pesan, lalu stop
    if not fused_chunks:
        yield {"type": "token", "data": _NO_RESULT_MSG}
        yield {"type": "done", "data": {"chunks_retrieved": 0, "chunks_after_grading": 0}}
        return

    # 4. Grade
    relevant_chunks = grade_chunks(query, fused_chunks)

    if not relevant_chunks:
        yield {"type": "token", "data": _NO_RELEVANT_MSG}
        yield {"type": "done", "data": {"chunks_retrieved": len(fused_chunks), "chunks_after_grading": 0}}
        return

    # 5. Kirim SOURCES dulu (sebelum token mulai)
    sources = [
        {
            "id": chunk["id"],
            "document_id": chunk.get("document_id"),
            "metadata": chunk.get("metadata", {}),
            "rrf_score": chunk.get("rrf_score", 0.0),
        }
        for chunk in relevant_chunks
    ]
    yield {"type": "sources", "data": sources}

    # 6. Stream answer token per token
    for token in generate_answer_stream(query, relevant_chunks):
        yield {"type": "token", "data": token}

    # 7. Kirim sinyal selesai + stats
    yield {
        "type": "done",
        "data": {
            "chunks_retrieved": len(fused_chunks),
            "chunks_after_grading": len(relevant_chunks),
        }
    }

    # 1. Embed query
    query_embedding = embed_query(query)

    # 2. Dual retrieval (paralel secara konseptual, sequential di sini)
    vector_results = vector_search(query_embedding, top_k=_TOP_K_RETRIEVE, project_id=project_id)
    bm25_results = bm25_search(query, top_k=_TOP_K_RETRIEVE, project_id=project_id)

    # 3. RRF — gabungkan dan re-rank
    fused_chunks = reciprocal_rank_fusion(vector_results, bm25_results, top_n=_TOP_N_RRF)

    if not fused_chunks:
        return {
            "answer": _NO_RESULT_MSG,
            "sources": [],
            "chunks_retrieved": 0,
            "chunks_after_grading": 0,
        }

    # 4. Grade — filter chunk yang tidak relevan
    relevant_chunks = grade_chunks(query, fused_chunks)

    if not relevant_chunks:
        return {
            "answer": _NO_RELEVANT_MSG,
            "sources": [],
            "chunks_retrieved": len(fused_chunks),
            "chunks_after_grading": 0,
        }

    # 5. Generate jawaban
    answer = generate_answer(query, relevant_chunks)

    # 6. Susun sumber untuk referensi frontend
    sources = [
        {
            "id": chunk["id"],
            "document_id": chunk.get("document_id"),
            "metadata": chunk.get("metadata", {}),
            "rrf_score": chunk.get("rrf_score", 0.0),
        }
        for chunk in relevant_chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
        "chunks_retrieved": len(fused_chunks),
        "chunks_after_grading": len(relevant_chunks),
    }
