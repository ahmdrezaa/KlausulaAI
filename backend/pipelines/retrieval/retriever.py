"""
KlausulaAI - Retriever: Vector Search + Full-Text Search (BM25-like)

Implementasi hybrid retrieval menggunakan:
- Vector search  : pgvector (cosine similarity) via Supabase RPC
- Keyword search : PostgreSQL FTS dengan config 'simple' via Supabase RPC

Cakupan pencarian:
- Dokumen global UU/PP (doc_type = 'global_uu') — selalu disertakan
- Dokumen milik user  (doc_type = 'user_doc')   — filter per project_id

=============================================================================
SUPABASE SQL SETUP — jalankan sekali di SQL Editor Supabase sebelum deploy
=============================================================================

-- 1. Vector search function
CREATE OR REPLACE FUNCTION match_chunks_vector(
    query_embedding vector(768),
    match_count     int,
    filter_project_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id          uuid,
    content     text,
    metadata    jsonb,
    document_id uuid,
    project_id  uuid,
    similarity  float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.content,
        dc.metadata,
        dc.document_id,
        dc.project_id,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE
        d.doc_type = 'global_uu'
        OR (d.doc_type = 'user_doc' AND dc.project_id = filter_project_id)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 2. Full-text search function (BM25-like via ts_rank_cd)
CREATE OR REPLACE FUNCTION match_chunks_fts(
    query_text        text,
    match_count       int,
    filter_project_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id          uuid,
    content     text,
    metadata    jsonb,
    document_id uuid,
    project_id  uuid,
    rank        float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.content,
        dc.metadata,
        dc.document_id,
        dc.project_id,
        ts_rank_cd(
            to_tsvector('simple', dc.content),
            plainto_tsquery('simple', query_text)
        ) AS rank
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE
        (d.doc_type = 'global_uu'
         OR (d.doc_type = 'user_doc' AND dc.project_id = filter_project_id))
        AND to_tsvector('simple', dc.content)
            @@ plainto_tsquery('simple', query_text)
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;

=============================================================================
"""

import os
from typing import Optional

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from backend.core.config import supabase_admin

from core.llm_clients import embeddings

def embed_query(text: str) -> list[float]:
    """Ubah teks query menjadi embedding vector 768-dimensi."""
    return _embeddings.embed_query(text)


def vector_search(
    query_embedding: list[float],
    top_k: int = 10,
    project_id: Optional[str] = None,
) -> list[dict]:
    """
    Cari chunk paling mirip secara semantik menggunakan cosine similarity.

    Returns list of dicts dengan keys:
        id, content, metadata, document_id, project_id, score
    """
    response = supabase_admin.rpc(
        "match_chunks_vector",
        {
            "query_embedding": query_embedding,
            "match_count": top_k,
            "filter_project_id": project_id,
        },
    ).execute()

    return [
        {
            "id": row["id"],
            "content": row["content"],
            "metadata": row["metadata"] or {},
            "document_id": row["document_id"],
            "project_id": row["project_id"],
            "score": row["similarity"],
        }
        for row in (response.data or [])
    ]


def bm25_search(
    query: str,
    top_k: int = 10,
    project_id: Optional[str] = None,
) -> list[dict]:
    """
    Cari chunk berdasarkan keyword menggunakan PostgreSQL FTS (ts_rank_cd).
    Cocok untuk query yang mengandung istilah hukum spesifik (Pasal, UU, dll).

    Returns list of dicts dengan keys:
        id, content, metadata, document_id, project_id, score
    """
    response = supabase_admin.rpc(
        "match_chunks_fts",
        {
            "query_text": query,
            "match_count": top_k,
            "filter_project_id": project_id,
        },
    ).execute()

    return [
        {
            "id": row["id"],
            "content": row["content"],
            "metadata": row["metadata"] or {},
            "document_id": row["document_id"],
            "project_id": row["project_id"],
            "score": row["rank"],
        }
        for row in (response.data or [])
    ]
