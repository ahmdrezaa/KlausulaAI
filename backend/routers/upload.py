from fastapi import APIRouter, UploadFile, File, Form
import shutil
import os
from backend.core.llm_clients import embeddings
from backend.lib.supabase_client import get_supabase
from backend.pipelines.ingestion.document_processor import UserDocumentProcessor

router = APIRouter()

@router.post("/upload-document/")
async def upload_document(
    project_id: str = Form(...), 
    file: UploadFile = File(...)
):
    # Simpan file PDF sementara
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 2. Inisialisasi koneksi database & AI
        supabase_db = get_supabase()
        
        # 3. Panggil mesin pemroses dokumen (Ingestion)
        # Kita masukkan supabase_db dan variabel 'embeddings' dari llm_clients
        processor = UserDocumentProcessor(supabase_db, embeddings)
        
        # 4. Eksekusi proses pemotongan dan penyimpanan ke Supabase
        doc_id = processor.process_and_ingest(temp_file_path, file.filename, project_id)
        
        # Bersihkan file PDF sementara
        os.remove(temp_file_path)
        
        return {
            "status": "success", 
            "message": "Dokumen berhasil di-embedding dan disimpan.",
            "document_id": doc_id
        }
        
    except Exception as e:
        # Bersihkan file PDF sementara jika terjadi error (misal API Gemini limit)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return {"status": "error", "message": str(e)}