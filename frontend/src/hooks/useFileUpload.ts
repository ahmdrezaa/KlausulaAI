// frontend/src/hooks/useFileUpload.ts
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { uploadService, UploadResult } from '@/services/uploadService';
import toast from 'react-hot-toast';

export function useFileUpload(projectId: string, onSuccess?: () => void) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const { supabase } = useAuth();

  const uploadFiles = async (files: File[]) => {
    if (!projectId) {
      toast.error('Project ID tidak ditemukan');
      return;
    }

    if (files.length === 0) {
      toast.error('Tidak ada file yang dipilih');
      return;
    }

    setUploading(true);
    setProgress(0);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        throw new Error('Anda belum login');
      }

      // Simulate progress
      const interval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const result = await uploadService.uploadFiles(projectId, files, token);
      
      clearInterval(interval);
      setProgress(100);
      
      // Show success message with file count
      const successCount = result.files?.length || files.length;
      toast.success(`${successCount} file berhasil diupload`);
      
      onSuccess?.();
      
      return result;
    } catch (error: any) {
      console.error('Upload error:', error);
      
      // Show detailed error message
      const errorMessage = error.message || 'Gagal upload file';
      
      // Split multiple errors for better display
      if (errorMessage.includes('\n')) {
        const errors = errorMessage.split('\n');
        errors.forEach((err: string) => toast.error(err));
      } else {
        toast.error(errorMessage);
      }
      
      throw error;
    } finally {
      setUploading(false);
      setTimeout(() => setProgress(0), 1000);
    }
  };

  return {
    uploadFiles,
    uploading,
    progress,
  };
}