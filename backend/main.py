from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import upload

# 1. Inisialisasi Aplikasi Utama
app = FastAPI(
    title="KlausulaAI Backend API",
    description="Sistem Ingestion & Retrieval berbasis Vector",
    version="1.0.0"
)

# 2. Konfigurasi CORS (Wajib agar Frontend Next.js bisa terhubung)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Mengizinkan akses dari semua URL (bisa diubah ke http://localhost:3000 nanti)
    allow_credentials=True,
    allow_methods=["*"], # Mengizinkan semua method (GET, POST, dll)
    allow_headers=["*"], # Mengizinkan semua header
)

# 3. Endpoint Dasar (Hanya untuk tes ping server)
@app.get("/")
def ping_server():
    return {"status": "success", "message": "Server KlausulaAI aktif dan siap menerima perintah!"}

# 4. Pendaftaran Router
app.include_router(upload.router)