from core.config import supabase_admin

# Cek apakah dokumen "Manajemen Kualitas" / "Progke 2" sudah punya chunks
result = supabase_admin.table("documents").select("id, file_name, status").ilike("file_name", "%kualitas%").execute()
print(result.data)

for doc in result.data:
    chunks = supabase_admin.table("document_chunks").select("id").eq("document_id", doc["id"]).execute()
    print(f"{doc['file_name']}: {len(chunks.data)} chunks")