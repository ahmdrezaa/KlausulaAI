from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routers import chat

try:
    from routers import upload
    _upload_available = True
except ImportError as e:
    print(f"[WARNING] Upload router not loaded (missing dependency): {e}")
    _upload_available = False

try:
    from config import settings
    frontend_origins = [settings.FRONTEND_URL]
except ImportError:
    frontend_origins = ["*"]

app = FastAPI(
    title="KlausulaAI Backend API",
    description="Sistem Ingestion & Retrieval berbasis Vector",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    # Terima localhost DAN 127.0.0.1 di port dev apa pun. Tanpa ini, preflight
    # CORS (OPTIONS) balas 400 kalau frontend dibuka via 127.0.0.1 padahal
    # allow_origins cuma berisi http://localhost:3000 (atau sebaliknya).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

if _upload_available:
    app.include_router(upload.router)
app.include_router(chat.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    raise HTTPException(status_code=204)


@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "Server KlausulaAI aktif dan siap menerima perintah!",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "KlausulaAI Vector Engine",
    }
