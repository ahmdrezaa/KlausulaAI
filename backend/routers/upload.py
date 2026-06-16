import os
import shutil
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from supabase import Client

# --- 1. Import Fitur Infrastruktur (Dari GitHub) ---
from dependencies import get_current_user, get_supabase
from services.storage import StorageService

# --- 2. Import Fitur AI Ingestion (Dari Lokal/Buatanmu) ---
from backend.core.llm_clients import embeddings
from backend.pipelines.ingestion.document_processor import UserDocumentProcessor

# Catatan: Endpoint sekarang menggunakan standar RESTful API dari GitHub
router = APIRouter(prefix="/api/v1/projects", tags=["upload"])

@router.post("/{project_id}/upload")
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Mengunggah banyak file sekaligus, menyimpan ke Storage, 
    dan melakukan ekstraksi Vector Embedding AI.
    """
    if not files:
        raise HTTPException(400, "Tidak ada file yang diberikan")
    
    # Verifikasi kepemilikan proyek
    project = supabase.table("projects")\
        .select("id")\
        .eq("id", project_id)\
        .eq("user_id", current_user.id)\
        .execute()
    
    if not project.data:
        raise HTTPException(404, "Proyek tidak ditemukan atau akses ditolak")
    
    # Inisialisasi alat
    storage = StorageService(supabase)
    processor = UserDocumentProcessor(supabase, embeddings)
    
    uploaded_files = []
    errors = []
    
    for file in files:
        temp_file_path = f"temp_{file.filename}"
        try:
            # A. Simpan PDF sementara untuk diakses oleh PyPDFLoader (Lokal)
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # B. Upload file fisik ke Supabase Storage (GitHub)
            upload_result = await storage.upload_file(
                file, 
                current_user.id, 
                project_id
            )
            
            # C. Simpan metadata ke tabel PostgreSQL (GitHub)
            new_doc_id = str(uuid.uuid4())
            source_data = {
                "id": new_doc_id,
                "project_id": project_id,
                "file_name": upload_result["file_name"],
                "storage_path": upload_result["file_path"],
                "file_size_bytes": upload_result["file_size"],
                "file_type": upload_result["mime_type"],
                "doc_type": "user_doc",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
            }
            
            supabase.table("documents").insert(source_data).execute()

            # D. Eksekusi AI Vector Ingestion LangChain (Lokal)
            processor.process_and_ingest(temp_file_path, file.filename, project_id)
            
            uploaded_files.append({
                "id": new_doc_id,
                "name": file.filename,
                "size": upload_result["file_size"],
                "status": "success - stored and embedded"
            })
            
        except Exception as e:
            print(f"Error processing {file.filename}:", str(e))
            errors.append({
                "name": file.filename,
                "error": str(e)
            })
        finally:
            # E. WAJIB: Selalu hapus file sampah sementara (Lokal)
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    if errors and not uploaded_files:
        raise HTTPException(500, f"Upload gagal: {errors[0]['error']}")
    
    return {
        "message": f"Berhasil mengunggah dan memproses {len(uploaded_files)} file",
        "files": uploaded_files,
        "errors": errors if errors else None
    }

# --- Fitur Baca dan Hapus Dokumen (Dari GitHub) ---

@router.get("/{project_id}/sources")
async def get_sources(
    project_id: str,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    sources = supabase.table("documents")\
        .select("*")\
        .eq("project_id", project_id)\
        .execute()
    
    return {"sources": sources.data}

@router.delete("/{project_id}/sources/{source_id}")
async def delete_source(
    project_id: str,
    source_id: str,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    source = supabase.table("documents")\
        .select("storage_path")\
        .eq("id", source_id)\
        .eq("project_id", project_id)\
        .execute()
    
    if not source.data:
        raise HTTPException(404, "Dokumen tidak ditemukan")
    
    # Hapus file fisik dari Storage
    supabase.storage.from_("project_files").remove([source.data[0]["storage_path"]])
    
    # Hapus metadata (Otomatis akan menghapus chunks jika ada pengaturan CASCADE di database)
    supabase.table("documents")\
        .delete()\
        .eq("id", source_id)\
        .execute()
    
    return {"message": "Dokumen berhasil dihapus"}