from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from routers import upload
from config import settings

app = FastAPI(title="KlausulaAI API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(upload.router)

@app.get("/favicon.ico")
async def favicon():
    # Return empty response atau file favicon
    raise HTTPException(status_code=204)  # No content

@app.get("/")
async def root():
    return {
        "message": "KlausulaAI Backend API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}