from pipelines.retrieval.retriever import embed_query, vector_search, bm25_search
from pipelines.retrieval.rrf import reciprocal_rank_fusion
from pipelines.retrieval.grader import _chain

query = "Pesangon karyawan kontrak 2 tahun berapa?"

# Retrieve
vec = vector_search(embed_query(query), top_k=10)
bm = bm25_search(query, top_k=10)
fused = reciprocal_rank_fusion(vec, bm, top_n=6)

print("=== CHUNKS YANG DI-RETRIEVE ===")
for i, c in enumerate(fused, 1):
    pasal_id = c["metadata"].get("pasal_id", "?")
    content = c["content"][:100]
    print(f"{i}. {pasal_id}")
    print(f"   {content}")
    print()

# Test grader untuk chunk pertama
print("=== TEST GRADER (chunk 1) ===")
response = _chain.invoke({"question": query, "chunk": fused[0]["content"]})
raw = response.content if hasattr(response, "content") else str(response)
print("Raw response grader:")
print(raw)