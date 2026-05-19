"""
KlausulaAI - Reciprocal Rank Fusion (RRF)

Menggabungkan hasil dari dua retriever (vector + BM25) menjadi satu
ranked list yang lebih akurat dari masing-masing retriever secara individual.

Formula: score(d) = sum( 1 / (k + rank(d)) )
Default k=60 mengikuti paper orisinil Cormack et al. (2009).
"""

from typing import Optional


def reciprocal_rank_fusion(
    results_a: list[dict],
    results_b: list[dict],
    k: int = 60,
    top_n: int = 6,
) -> list[dict]:
    """
    Gabungkan dua ranked list menggunakan RRF.

    Args:
        results_a : Hasil dari vector search (sudah terurut by score DESC)
        results_b : Hasil dari BM25/FTS search (sudah terurut by score DESC)
        k         : Konstanta RRF, default 60
        top_n     : Jumlah chunk teratas yang dikembalikan

    Returns:
        List of chunk dicts terurut by rrf_score DESC, max top_n items.
        Setiap dict memiliki tambahan key 'rrf_score'.
    """
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for rank, doc in enumerate(results_a):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        docs[doc_id] = doc

    for rank, doc in enumerate(results_b):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        docs[doc_id] = doc

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return [
        {**docs[doc_id], "rrf_score": round(score, 6)}
        for doc_id, score in ranked[:top_n]
    ]
