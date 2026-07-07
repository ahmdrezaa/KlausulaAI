"""
KlausulaAI - RAG Chain: Orchestrator

Mengorkestrasi seluruh pipeline Hybrid RAG:
  1. Embed query         (text → vector 768-dim)
  2. Vector search       (cosine similarity via pgvector)
  3. BM25 search         (FTS via PostgreSQL ts_rank_cd)
  4. RRF fusion          (gabungkan + re-rank hasil kedua retriever)
  5. Relevance grading   (filter chunk tidak relevan via LLM)
  6. Answer generation   (sintesis jawaban dalam Bahasa Indonesia)

Entry point utama: run_rag_stream()
"""

import concurrent.futures
import time
from typing import Optional

from core.intent import is_document_reference
from pipelines.retrieval.generator import generate_answer, generate_answer_stream
from pipelines.retrieval.grader import grade_chunks
from pipelines.retrieval.retriever import (
    bm25_search,
    embed_query,
    expand_query,
    user_doc_vector_search,
    vector_search,
)
from pipelines.retrieval.rrf import reciprocal_rank_fusion

# Konstanta pipeline
_TOP_K_RETRIEVE = 10   # jumlah kandidat dari tiap retriever
_FUSION_POOL = 20    # kandidat hasil fusion SEBELUM prioritas user-doc, lalu dipotong ke _TOP_N_RRF
_TOP_N_RRF = 6       # jumlah chunk setelah fusion yang masuk ke grader
_FALLBACK_TOP_N = 4  # jumlah chunk teratas yang dipakai kalau grader kena rate-limit
_GRADE_TIMEOUT_S = 6  # batas waktu grading; lebih dari ini → fallback (anti-hang akibat retry rate-limit SDK)

# Executor kecil untuk membungkus grade_chunks dengan timeout. Grading tidak
# layak ditunggu lama (fallback sudah cukup baik); generator yang layak ditunggu.
_grade_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="grade")

# Pesan fallback (positioning F&B; TANPA frasa "Dinas Koperasi dan UKM" lama).
_FNB_FALLBACK = (
    "Maaf, saya belum menemukan informasi yang cukup untuk menjawab pertanyaan ini "
    "secara akurat dari dokumen yang tersedia. Fokus saya adalah legalitas dan kontrak "
    "usaha F&B — pendirian usaha, perizinan, merek, kontrak, dan perlindungan konsumen. "
    "Anda bisa mencoba memperjelas pertanyaan, atau mengunggah dokumen terkait untuk saya tinjau."
)

_NO_RESULT_MSG = _FNB_FALLBACK
_NO_RELEVANT_MSG = _FNB_FALLBACK


def _is_quota_error(e: Exception) -> bool:
    msg = str(e)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()


def _grade_or_fallback(query: str, fused_chunks: list[dict]) -> list[dict]:
    """Saring chunk lewat grader LLM. Kalau grader kena rate-limit (429 quota),
    JANGAN matikan seluruh chat — pakai chunk teratas hasil RRF apa adanya
    (tanpa grading) supaya pipeline tetap bisa menjawab.

    Grading normal tetap berjalan selama kuota tersedia & cepat; fallback ini
    aktif saat grader kena error kuota (429) ATAU terlalu lama (rate-limit retry
    SDK bisa bikin 1 panggilan makan ~6-12 detik). Dengan timeout, response tetap
    cepat apa pun kondisi kuotanya.
    """
    future = _grade_executor.submit(grade_chunks, query, fused_chunks)
    try:
        return future.result(timeout=_GRADE_TIMEOUT_S)
    except concurrent.futures.TimeoutError:
        print(
            f"[RAG] WARNING: grading > {_GRADE_TIMEOUT_S}s (kemungkinan rate-limit) — "
            f"fallback ke {_FALLBACK_TOP_N} chunk teratas tanpa grading.",
            flush=True,
        )
        return fused_chunks[:_FALLBACK_TOP_N]
    except Exception as e:
        # Grading bersifat best-effort: error APA PUN (429 kuota, 503 overload,
        # network, parse) tidak boleh mematikan chat — cukup fallback ke chunk
        # teratas. Generator yang tetap dijalankan penuh.
        reason = "rate-limit (429)" if _is_quota_error(e) else f"{type(e).__name__}: {str(e)[:80]}"
        print(
            f"[RAG] WARNING: grader gagal [{reason}] — "
            f"fallback ke {_FALLBACK_TOP_N} chunk teratas tanpa grading.",
            flush=True,
        )
        return fused_chunks[:_FALLBACK_TOP_N]


def _augment_with_user_docs(
    query: str,
    query_embedding: list[float],
    project_id: Optional[str],
    vector_results: list[dict],
) -> list[dict]:
    """Kalau pertanyaan merujuk ke dokumen user sendiri ("jelaskan dokumen saya"),
    JAMIN chunk dokumen user project ini ikut jadi kandidat — karena RPC global
    mem-filter dengan ambang kemiripan, chunk dokumen user yang skornya rendah
    untuk frasa samar bisa hilang total sebelum sempat diprioritaskan.

    Untuk pertanyaan yang TIDAK merujuk dokumen (mis. murni hukum), kandidat
    tidak diubah → Q&A hukum tetap normal (dokumen user yang tak relevan tidak
    dipaksa masuk).
    """
    if not project_id or not is_document_reference(query):
        return vector_results

    user_hits = user_doc_vector_search(query_embedding, project_id, top_k=_TOP_K_RETRIEVE)
    if not user_hits:
        return vector_results

    seen = {r["id"] for r in vector_results}
    merged = vector_results + [r for r in user_hits if r["id"] not in seen]
    merged.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    return merged


def _prioritize_user_chunks(chunks: list[dict]) -> list[dict]:
    """Dahulukan chunk milik dokumen USER (project_id != None) di atas chunk
    UU/PP global (project_id == None). Urutan RRF dipertahankan dalam tiap
    kelompok. UU global tetap disertakan sebagai PELENGKAP di bawah.

    Tujuan: kalau project punya dokumen user, pertanyaan dijawab dari dokumen
    itu lebih dulu — bukan dari korpus UU global yang kebetulan mirip secara
    semantik (mis. query "baca dokumen" yang nyangkut ke "Dokumen Elektronik"
    di UU ITE). Kalau dokumen user TIDAK ikut ter-retrieve sebagai kandidat
    (mis. pertanyaan murni hukum), tidak ada yang diprioritaskan → UU global
    tampil normal, jadi Q&A hukum tidak terganggu.
    """
    user_chunks = [c for c in chunks if c.get("project_id") is not None]
    global_chunks = [c for c in chunks if c.get("project_id") is None]
    return user_chunks + global_chunks


def _build_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "id": chunk["id"],
            "document_id": chunk.get("document_id"),
            "metadata": chunk.get("metadata", {}),
            "rrf_score": chunk.get("rrf_score", 0.0),
        }
        for chunk in chunks
    ]


def run_rag(
    query: str,
    project_id: Optional[str] = None,
    chat_history: Optional[list[dict]] = None,
    system_instruction: Optional[str] = None,
) -> dict:
    query_embedding = embed_query(expand_query(query))
    vector_results = vector_search(query_embedding, top_k=_TOP_K_RETRIEVE, project_id=project_id)
    vector_results = _augment_with_user_docs(query, query_embedding, project_id, vector_results)
    bm25_results = bm25_search(query, top_k=_TOP_K_RETRIEVE, project_id=project_id)
    fused_pool = reciprocal_rank_fusion(vector_results, bm25_results, top_n=_FUSION_POOL)
    fused_chunks = _prioritize_user_chunks(fused_pool)[:_TOP_N_RRF]

    if not fused_chunks:
        return {
            "answer": _NO_RESULT_MSG,
            "sources": [],
            "chunks_retrieved": 0,
            "chunks_after_grading": 0,
        }

    relevant_chunks = _grade_or_fallback(query, fused_chunks)

    if not relevant_chunks:
        return {
            "answer": _NO_RELEVANT_MSG,
            "sources": [],
            "chunks_retrieved": len(fused_chunks),
            "chunks_after_grading": 0,
        }

    answer = generate_answer(
        query, relevant_chunks, chat_history=chat_history, system_instruction=system_instruction
    )

    return {
        "answer": answer,
        "sources": _build_sources(relevant_chunks),
        "chunks_retrieved": len(fused_chunks),
        "chunks_after_grading": len(relevant_chunks),
    }


def run_rag_stream(
    query: str,
    project_id: Optional[str] = None,
    chat_history: Optional[list[dict]] = None,
    system_instruction: Optional[str] = None,
):
    _t = time.perf_counter()

    def _lap(label: str):
        nonlocal _t
        now = time.perf_counter()
        print(f"[TIMING] {label}: {now - _t:.2f}s", flush=True)
        _t = now

    _wall = time.perf_counter()

    query_embedding = embed_query(expand_query(query))
    _lap("embed_query")

    vector_results = vector_search(query_embedding, top_k=_TOP_K_RETRIEVE, project_id=project_id)
    _lap("vector_search")

    vector_results = _augment_with_user_docs(query, query_embedding, project_id, vector_results)
    _lap("augment_user_docs")

    bm25_results = bm25_search(query, top_k=_TOP_K_RETRIEVE, project_id=project_id)
    _lap("bm25_search")

    fused_pool = reciprocal_rank_fusion(vector_results, bm25_results, top_n=_FUSION_POOL)
    fused_chunks = _prioritize_user_chunks(fused_pool)[:_TOP_N_RRF]
    _n_user = sum(1 for c in fused_chunks if c.get("project_id") is not None)
    _lap(f"rrf_fusion+prioritas ({_n_user} user-doc / {len(fused_chunks) - _n_user} global)")

    if not fused_chunks:
        yield {"type": "token", "data": _NO_RESULT_MSG}
        yield {"type": "done", "data": {"chunks_retrieved": 0, "chunks_after_grading": 0}}
        return

    relevant_chunks = _grade_or_fallback(query, fused_chunks)
    _lap(f"grading ({len(fused_chunks)}->{len(relevant_chunks)} chunks)")

    if not relevant_chunks:
        yield {"type": "token", "data": _NO_RELEVANT_MSG}
        yield {"type": "done", "data": {"chunks_retrieved": len(fused_chunks), "chunks_after_grading": 0}}
        return

    yield {"type": "sources", "data": _build_sources(relevant_chunks)}

    _gen_start = time.perf_counter()
    first_token_at = None
    for token in generate_answer_stream(
        query, relevant_chunks, chat_history=chat_history, system_instruction=system_instruction
    ):
        if first_token_at is None:
            first_token_at = time.perf_counter()
            print(f"[TIMING] generator_first_token: {first_token_at - _gen_start:.2f}s", flush=True)
        yield {"type": "token", "data": token}
    print(f"[TIMING] generator_full: {time.perf_counter() - _gen_start:.2f}s", flush=True)
    print(f"[TIMING] >>> TOTAL run_rag_stream: {time.perf_counter() - _wall:.2f}s", flush=True)

    yield {
        "type": "done",
        "data": {
            "chunks_retrieved": len(fused_chunks),
            "chunks_after_grading": len(relevant_chunks),
        },
    }
