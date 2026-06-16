from core.config import supabase_admin
from pipelines.retrieval.retriever import embed_query

query = "Pesangon karyawan kontrak 2 tahun berapa?"
vector = embed_query(query)

result = supabase_admin.rpc("match_chunks_vector", {
    "query_embedding": vector,
    "match_count": 20,
    "filter_project_id": None
}).execute()

for i, row in enumerate(result.data, 1):
    pasal_id = row["metadata"].get("pasal_id", "?")
    if "13_2003" in pasal_id:
        print(f"Rank {i} | {pasal_id} | similarity: {round(row['similarity'], 4)}")


result2 = supabase_admin.table("document_chunks").select("content, metadata").eq("metadata->>pasal_id", "uu_13_2003_pasal_156").execute()
print("=== ISI PASAL 156 ===")
print(result2.data[0]["content"])
