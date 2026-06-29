import os
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from supabase import Client

# --- 1. Import Fitur Infrastruktur (Dari GitHub) ---
from dependencies import get_current_user, get_supabase
from services.storage import StorageService

# --- 2. Import Fitur AI Ingestion (Dari Lokal/Buatanmu) ---
from core.llm_clients import embeddings
from pipelines.ingestion.document_processor import UserDocumentProcessor

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
        temp_file_path = f"temp_{uuid.uuid4().hex}.pdf"
        try:
            # A. Baca isi file SEKALI. Stream UploadFile hanya bisa dibaca sekali —
            #    dulu di-copy ke temp (mengosongkan stream) lalu storage membaca
            #    lagi dan dapat 0 byte. Sekarang: baca sekali, pakai untuk temp
            #    PDF DAN untuk upload ke storage.
            content = await file.read()
            if not content:
                raise HTTPException(400, f"File '{file.filename}' kosong (0 byte)")

            # B. Tulis temp PDF untuk PyPDFLoader (ingestion lokal)
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content)

            # C. Upload file fisik ke Supabase Storage (pakai content yang sama)
            upload_result = await storage.upload_file(
                file, content, current_user.id, project_id
            )

            # D. Simpan SATU baris metadata ke tabel documents.
            #    (Dulu double-insert: di sini DAN di process_and_ingest → 2 entri
            #     per file. Sekarang process_and_ingest hanya menulis chunk yang
            #     di-link ke new_doc_id ini, tanpa membuat baris documents lagi.)
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

            # E. Ingestion: chunk + embed, di-link ke new_doc_id (tanpa baris baru)
            chunk_count = processor.process_and_ingest(temp_file_path, new_doc_id, project_id)

            uploaded_files.append({
                "id": new_doc_id,
                "name": file.filename,
                "size": upload_result["file_size"],
                "chunks": chunk_count,
                "status": "success - stored and embedded",
            })

        except Exception as e:
            print(f"Error processing {file.filename}:", str(e))
            errors.append({
                "name": file.filename,
                "error": str(e)
            })
        finally:
            # F. WAJIB: Selalu hapus file sampah sementara (Lokal)
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
    
    # Hapus chunks dulu (eksplisit). FK document_chunks.document_id memang sudah
    # ON DELETE CASCADE, tapi ini jaring pengaman agar tidak pernah ada chunk
    # yatim yang masih terbaca retrieval ("dokumen hantu").
    supabase.table("document_chunks").delete().eq("document_id", source_id).execute()

    # Hapus baris metadata
    supabase.table("documents").delete().eq("id", source_id).execute()

    # Hapus file fisik dari Storage (best-effort)
    storage_path = source.data[0].get("storage_path")
    if storage_path:
        try:
            supabase.storage.from_("project_files").remove([storage_path])
        except Exception as e:
            print(f"[DELETE] storage remove gagal utk {source_id}: {e}", flush=True)

    return {"message": "Dokumen berhasil dihapus"}


class DeleteSourcesRequest(BaseModel):
    source_ids: List[str]


@router.post("/{project_id}/sources/bulk-delete")
async def bulk_delete_sources(
    project_id: str,
    body: DeleteSourcesRequest,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """Hapus beberapa dokumen sekaligus (fitur 'pilih lalu hapus' di sidebar Sumber).

    Untuk TIAP dokumen, hapus konsisten & lengkap:
      1. document_chunks (eksplisit; FK juga ON DELETE CASCADE — terverifikasi)
      2. baris di tabel documents
      3. file fisik di Supabase Storage (best-effort)
    Pakai service-role client (bypass RLS) supaya delete-nya benar-benar terjadi.
    """
    # Verifikasi kepemilikan project (jangan biarkan user menghapus dok project lain)
    project = (
        supabase.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", current_user.id)
        .execute()
    )
    if not project.data:
        raise HTTPException(404, "Proyek tidak ditemukan atau akses ditolak")

    deleted: List[str] = []
    errors: List[dict] = []

    for sid in body.source_ids:
        try:
            row = (
                supabase.table("documents")
                .select("storage_path")
                .eq("id", sid)
                .eq("project_id", project_id)  # pastikan dok milik project ini
                .execute()
            )
            if not row.data:
                errors.append({"id": sid, "error": "tidak ditemukan di project ini"})
                continue

            storage_path = row.data[0].get("storage_path")

            supabase.table("document_chunks").delete().eq("document_id", sid).execute()
            supabase.table("documents").delete().eq("id", sid).execute()
            if storage_path:
                try:
                    supabase.storage.from_("project_files").remove([storage_path])
                except Exception as e:
                    print(f"[DELETE] storage remove gagal utk {sid}: {e}", flush=True)

            deleted.append(sid)
        except Exception as e:
            errors.append({"id": sid, "error": str(e)})

    return {"deleted": deleted, "deleted_count": len(deleted), "errors": errors}