import os
import json
import logging
import argparse
import uuid
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client, Client

# ─── Setup Logging ────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "supabase_ingestion.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SupabaseIngestion")

# ─── Inisialisasi Klien ───────────────────────────────────────
load_dotenv()

# Setup Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Wajib Service Role Key

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("[ERROR] Kredensial Supabase tidak ditemukan di .env")

supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Setup Gemini Embeddings
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("[ERROR] GOOGLE_API_KEY tidak ditemukan di .env")

# [UPDATE] Menggunakan model embedding terbaru dengan kompresi dimensi 768
_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=GOOGLE_API_KEY,
    output_dimensionality=768
)


class RelationalSupabaseIngestor:
    def format_text_for_embedding(self, pasal: dict) -> str:
        """
        Menyiapkan teks yang akan di-embed.
        Konteks judul sangat penting agar vektor tidak kehilangan arah makna.
        """
        return f"Undang-Undang: {pasal.get('uu_name', '')}. Bab: {pasal.get('bab_title', '')}. Isi: {pasal.get('full_text', '')}"

    def get_or_create_document(self, first_pasal: dict) -> str:
        """
        Mengecek apakah dokumen UU sudah ada di tabel 'documents'.
        Disesuaikan dengan skema Supabase KlausulaAI.
        """
        uu_slug = first_pasal.get("uu_slug", "unknown_slug")
        uu_name = first_pasal.get("uu_name", "Unknown Document")
        
        # Cari dokumen berdasarkan uu_code
        response = supabase_admin.table("documents")\
            .select("id")\
            .eq("doc_type", "global_uu")\
            .eq("uu_code", uu_slug)\
            .execute()
        
        if response.data and len(response.data) > 0:
            doc_id = response.data[0]["id"]
            logger.info(f"[INFO] Dokumen Induk ditemukan di DB dengan ID: {doc_id}")
            return doc_id
            
        # Jika tidak ada, buat dokumen baru
        new_doc_id = str(uuid.uuid4())
        
        doc_data = {
            "id": new_doc_id,
            "doc_type": "global_uu",
            "file_name": uu_name,       
            "uu_code": uu_slug,         
            "file_type": "json",        
            "status": "active"          
        }
        
        supabase_admin.table("documents").insert(doc_data).execute()
        logger.info(f"[SUCCESS] Dokumen Induk baru dibuat dengan ID: {new_doc_id}")
        return new_doc_id

    def ingest_document(self, json_path: Path):
        logger.info(f"\n[PROCESS] Membaca file: {json_path.name}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            pasal_list = json.load(f)

        if not pasal_list:
            logger.warning("[WARNING] File JSON kosong.")
            return

        # 1. Dapatkan atau Buat ID Dokumen Induk
        document_id = self.get_or_create_document(pasal_list[0])

        logger.info(f"[PROCESS] Melakukan embedding dan insert untuk {len(pasal_list)} chunk...")
        
        # 2. Proses Insert Chunk ke tabel 'document_chunks'
        # [UPDATE] Menambahkan enumerate untuk mendapatkan index urutan pasal
        for index, pasal in enumerate(tqdm(pasal_list, desc="Supabase Ingestion")):
            pasal_id = pasal["pasal_id"]
            
            # Cek duplikasi di level chunk menggunakan filter metadata JSONB
            response = supabase_admin.table("document_chunks")\
                .select("id")\
                .contains("metadata", {"pasal_id": pasal_id})\
                .execute()
                
            if response.data and len(response.data) > 0:
                continue
            
            # Lakukan Embedding dengan Gemini
            teks_untuk_diembed = self.format_text_for_embedding(pasal)
            vektor = _embeddings.embed_query(teks_untuk_diembed)
            
            # Siapkan Metadata spesifik chunk (Format JSONB)
            chunk_metadata = {
                "pasal_id": pasal_id,
                "pasal_number": pasal.get("pasal_number", ""),
                "bab_title": pasal.get("bab_title", ""),
                "is_umkm_relevant": pasal.get("is_umkm_relevant", False),
                "tags": pasal.get("tags", [])
            }
            
            # Siapkan Payload untuk tabel 'document_chunks'
            chunk_data = {
                "document_id": document_id,
                "content": pasal.get("full_text", ""),
                "metadata": chunk_metadata,
                "embedding": vektor,
                "chunk_index": index  # [UPDATE] Menyuntikkan nilai chunk_index
            }
            
            try:
                supabase_admin.table("document_chunks").insert(chunk_data).execute()
            except Exception as e:
                logger.error(f"[ERROR] Gagal insert chunk {pasal_id}: {str(e)}")

        logger.info(f"[SUCCESS] Selesai memproses {json_path.name}")


def main():
    parser = argparse.ArgumentParser(description="KlausulaAI - Relational Supabase Vector Ingestion")
    parser.add_argument("--input", "-i", required=True, help="Folder berisi file _pasal_list.json")
    args = parser.parse_args()

    input_dir = Path(args.input)
    
    if not input_dir.exists():
        logger.error(f"[ERROR] Folder input tidak ditemukan: {input_dir}")
        return

    json_files = list(input_dir.glob("*_pasal_list.json"))
    
    if not json_files:
        logger.error(f"[ERROR] Tidak ada file *_pasal_list.json di {input_dir}")
        return

    ingestor = RelationalSupabaseIngestor()
    print(f"\n[START] Memulai Ingestion ke Supabase untuk {len(json_files)} dokumen...")
    
    for json_file in json_files:
        ingestor.ingest_document(json_file)

    print("\n[DONE] Seluruh proses Ingestion selesai.")


if __name__ == "__main__":
    main()