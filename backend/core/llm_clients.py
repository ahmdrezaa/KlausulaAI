import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("Cek .env: GOOGLE_API_KEY tidak ditemukan")

# Untuk grading (relevance check) — deterministic, temperature=0
llm_for_grading: ChatGoogleGenerativeAI = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    google_api_key=GOOGLE_API_KEY,
)

# Untuk generation (answer synthesis) — sedikit kreatif, temperature=0.7
llm_for_generation: ChatGoogleGenerativeAI = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY,
)

_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=GOOGLE_API_KEY,
)

print("LLM clients ready")
