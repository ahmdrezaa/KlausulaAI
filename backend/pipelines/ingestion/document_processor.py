import os
import uuid
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

    def process_and_ingest(self, file_path: str, file_name: str, project_id: str):
        # 1. Ekstrak Teks dari PDF
        loader = PyPDFLoader(file_path)
        raw_documents = loader.load()
        
        # 2. Potong-potong (Chunking)
        chunks = self.text_splitter.split_documents(raw_documents)
        
        # 3. Buat Entri Dokumen Induk di Tabel 'documents'
        doc_id = str(uuid.uuid4())
        self.supabase.table("documents").insert({
            "id": doc_id,
            "project_id": project_id,
            "doc_type": "user_doc", # Sangat penting untuk privasi!
            "file_name": file_name,
            "file_type": "pdf",
            "status": "active"
        }).execute()

        # 4. Embedding dan Insert ke 'document_chunks'
        for index, chunk in enumerate(chunks):
            # Ubah teks ke vektor 768 dimensi menggunakan Gemini
            vektor = self.embeddings.embed_query(chunk.page_content)
            
            self.supabase.table("document_chunks").insert({
                "document_id": doc_id,
                "project_id": project_id,
                "content": chunk.page_content,
                "embedding": vektor,
                "chunk_index": index,
                "metadata": {
                    "source_page": chunk.metadata.get("page", 0)
                }
            }).execute()
            
        return doc_id