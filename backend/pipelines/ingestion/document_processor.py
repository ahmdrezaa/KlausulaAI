from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class UserDocumentProcessor:
    def __init__(self, supabase_client, embeddings_model):
        self.supabase = supabase_client
        self.embeddings = embeddings_model

        # Pemotong teks: membagi dokumen per 1000 karakter, dengan overlap 150 karakter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150
        )

    def process_and_ingest(self, file_path: str, document_id: str, project_id: str) -> int:
        """Chunk + embed sebuah PDF, lalu simpan ke 'document_chunks' yang
        DI-LINK ke document_id yang SUDAH dibuat oleh caller (routers/upload.py).

        CATATAN: dulu metode ini juga meng-insert baris 'documents' sendiri →
        menghasilkan DUA baris documents per file (satu dari upload.py, satu di
        sini) dengan file_type berbeda ('application/pdf' vs 'pdf'). Sekarang
        tidak lagi: caller yang membuat satu-satunya baris documents, di sini
        cukup menulis chunk-nya. Return jumlah chunk tersimpan.
        """
        # 1. Ekstrak teks dari PDF + chunking
        chunks = self.text_splitter.split_documents(PyPDFLoader(file_path).load())
        if not chunks:
            return 0

        # 2. Embedding BATCH (satu panggilan utk banyak teks) — jauh lebih hemat
        #    kuota & cepat dibanding embed_query per-chunk, dan tidak gagal
        #    separuh jalan saat dokumen besar.
        texts = [c.page_content for c in chunks]
        vectors = self.embeddings.embed_documents(texts)

        # 3. Insert chunk (di-link ke document_id milik caller)
        rows = [
            {
                "document_id": document_id,
                "project_id": project_id,
                "content": c.page_content,
                "embedding": v,
                "chunk_index": i,
                "metadata": {"source_page": c.metadata.get("page", 0)},
            }
            for i, (c, v) in enumerate(zip(chunks, vectors))
        ]
        for s in range(0, len(rows), 50):
            self.supabase.table("document_chunks").insert(rows[s:s + 50]).execute()
        return len(rows)