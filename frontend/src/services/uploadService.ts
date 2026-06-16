// frontend/src/services/uploadService.ts

const ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt"];
const MAX_FILE_SIZE = 50 * 1024 * 1024;

export interface UploadResult {
  id: string;
  name: string;
  size: number;
  status: string;
}

export interface Source {
  id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  is_active: boolean;
  created_at: string;
}

class UploadService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }

  validateFiles(files: File[]): { valid: File[]; errors: string[] } {
    const valid: File[] = [];
    const errors: string[] = [];

    for (const file of files) {
      // Check extension
      const extension = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(extension)) {
        errors.push(`${file.name}: Tipe file tidak diizinkan`);
        continue;
      }

      // Check size
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: Ukuran file terlalu besar (max 50MB)`);
        continue;
      }

      valid.push(file);
    }

    return { valid, errors };
  }

  async uploadFiles(
    projectId: string,
    files: File[],
    token: string,
  ): Promise<{ files: UploadResult[]; message: string }> {
    // ✅ Client-side validation
    const { valid, errors } = this.validateFiles(files);

    if (errors.length > 0) {
      throw new Error(errors.join("\n"));
    }

    if (valid.length === 0) {
      throw new Error("Tidak ada file yang valid untuk diupload");
    }

    const formData = new FormData();
    valid.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(
      `${this.baseUrl}/api/v1/projects/${projectId}/upload`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      },
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  }

  async getSources(projectId: string, token: string): Promise<Source[]> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/projects/${projectId}/sources`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error("Failed to fetch sources");
    }

    const data = await response.json();
    return data.sources || [];
  }

  async deleteSource(
    projectId: string,
    sourceId: string,
    token: string,
  ): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/projects/${projectId}/sources/${sourceId}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error("Failed to delete source");
    }
  }
}

export const uploadService = new UploadService();
