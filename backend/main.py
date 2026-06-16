from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Wajib menggunakan prefix 'backend.' sesuai dengan struktur lokasimu
from backend.routers import upload

# Kita coba mengimpor pengaturan dari GitHub (jika file config.py sudah ditarik)
try:
    from backend.config import settings
    frontend_origins = [settings.FRONTEND_URL]
except ImportError:
    # Fallback sementara ke "*" jika file config belum ada, agar tes lokalmu tidak terganggu
    frontend_origins = ["*"]

# 1. Inisialisasi Aplikasi Utama
app = FastAPI(
    title="KlausulaAI Backend API",
    description="Sistem Ingestion & Retrieval berbasis Vector",
    version="1.0.0"
)

# 2. Konfigurasi CORS (Gabungan: lebih aman dan fleksibel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 3. Pendaftaran Router
app.include_router(upload.router)

# --- 4. Endpoints Dasar & Pemantauan Server ---

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Menghindari error di terminal saat API diakses lewat browser
    raise HTTPException(status_code=204)

@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "Server KlausulaAI aktif dan siap menerima perintah!",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "KlausulaAI Vector Engine"
    }