# backend/routers/upload.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
from supabase import Client
import uuid
from datetime import datetime

from dependencies import get_current_user, get_supabase
from services.storage import StorageService

router = APIRouter(prefix="/api/v1/projects", tags=["upload"])

@router.post("/{project_id}/upload")
async def upload_files(
    project_id: str,
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """
    Upload multiple files to a project
    """
    if not files:
        raise HTTPException(400, "No files provided")
    
    # Verify project ownership
    project = supabase.table("projects")\
        .select("id")\
        .eq("id", project_id)\
        .eq("user_id", current_user.id)\
        .execute()
    
    if not project.data:
        raise HTTPException(404, "Project not found or access denied")
    
    storage = StorageService(supabase)
    uploaded_files = []
    errors = []
    
    for file in files:
        try:
            # Upload file to storage
            upload_result = await storage.upload_file(
                file, 
                current_user.id, 
                project_id
            )
            
            # Save metadata to database
            source_data = {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "file_name": upload_result["file_name"],
                "storage_path": upload_result["file_path"],
                "file_size_bytes": upload_result["file_size"],
                "file_type": upload_result["mime_type"],
                "doc_type": "user_doc",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
            }
            
            result = supabase.table("documents")\
                .insert(source_data)\
                .execute()
            uploaded_files.append({
                "id": result.data[0]["id"],
                "name": file.filename,
                "size": upload_result["file_size"],
                "status": "success"
            })
            
        except Exception as e:
            print("error", str(e))
            errors.append({
                "name": file.filename,
                "error": str(e)
            })
    
    if errors and not uploaded_files:
        raise HTTPException(500, f"Upload failed: {errors[0]['error']}")
    
    return {
        "message": f"Uploaded {len(uploaded_files)} files successfully",
        "files": uploaded_files,
        "errors": errors if errors else None
    }

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
        raise HTTPException(404, "Source not found")
    
    supabase.storage.from_("project_files").remove([source.data[0]["storage_path"]])
    
    supabase.table("documents")\
        .delete()\
        .eq("id", source_id)\
        .execute()
    
    return {"message": "Source deleted"}