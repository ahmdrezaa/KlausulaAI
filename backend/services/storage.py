# backend/services/storage.py
from supabase import Client
from fastapi import UploadFile, HTTPException
import uuid
from datetime import datetime
from typing import List, Dict
import os

class StorageService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.bucket_name = "project_files"
        # ✅ Tambahkan allowed extensions
        self.allowed_extensions = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    def validate_file(self, filename: str, file_size: int) -> None:
        """Validate file extension and size"""
        
        # Check file extension
        file_extension = os.path.splitext(filename)[1].lower()
        
        if not file_extension:
            raise HTTPException(400, f"File '{filename}' has no extension")
        
        if file_extension not in self.allowed_extensions:
            allowed_str = ", ".join(self.allowed_extensions)
            raise HTTPException(
                400, 
                f"File type '{file_extension}' not allowed. Allowed types: {allowed_str}"
            )
        
        # Check file size
        if file_size > self.max_file_size:
            raise HTTPException(
                400, 
                f"File '{filename}' too large (max 50MB)"
            )
    
    async def upload_file(
        self, 
        file: UploadFile, 
        user_id: str, 
        project_id: str
    ) -> Dict:
        """Upload single file to Supabase storage"""
        
        # ✅ Validate file first
        content = await file.read()
        file_size = len(content)
        self.validate_file(file.filename, file_size)
        
        # Generate safe filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize filename (remove special chars)
        safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
        safe_filename = f"{timestamp}_{safe_name}"
        
        # Storage path: {user_id}/{project_id}/{filename}
        storage_path = f"{user_id}/{project_id}/{safe_filename}"
        
        try:
            # Upload to Supabase
            self.supabase.storage.from_(self.bucket_name).upload(
                storage_path,
                content,
                file_options={"content-type": file.content_type or "application/octet-stream"}
            )
            
            # Get signed URL
            signed = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=storage_path,
                expires_in=3600
            )
            public_url = signed.get("signedURL") or signed.get("publicURL") or ""
            
            return {
                "file_name": file.filename,
                "file_path": storage_path,
                "file_size": file_size,
                "mime_type": file.content_type,
                "public_url": public_url,
                "status": "uploaded"
            }
            
        except Exception as e:
            raise HTTPException(500, f"Storage upload failed: {str(e)}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        try:
            self.supabase.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False