import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("Cek .env: GOOGLE_API_KEY tidak ditemukan")

# Untuk grading (relevance check) — deterministic, temperature=0
# max_retries=0: kalau kena 429 (rate-limit), JANGAN tunggu backoff ~30 detik —
# langsung gagal cepat supaya fallback "tanpa grading" di rag_chain bisa jalan.
llm_for_grading: ChatGoogleGenerativeAI = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0,
    google_api_key=GOOGLE_API_KEY,
    max_retries=0,
)

# Untuk generation (answer synthesis) — sedikit kreatif, temperature=0.7
llm_for_generation: ChatGoogleGenerativeAI = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY,
)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=GOOGLE_API_KEY,
    output_dimensionality=768,
)

print("LLM clients ready")
