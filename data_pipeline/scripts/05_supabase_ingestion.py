import os
import json
import time
import logging
import argparse
import uuid
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import create_client, Client

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

# ─── Konfigurasi kuota ────────────────────────────────────────
BATCH_SIZE = 40
JEDA_ANTAR_BATCH = 2.0
RPD_LIMIT = 1000

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("[ERROR] Kredensial Supabase tidak ditemukan di .env")
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("[ERROR] GOOGLE_API_KEY tidak ditemukan di .env")

# IDENTIK dengan kode lama — WAJIB sama agar vektor kompatibel
_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=GOOGLE_API_KEY,
    output_dimensionality=768
)


class ChunkIngestor:
    def __init__(self):
        self.request_count = 0

    def format_text_for_embedding(self, chunk: dict) -> str:
        """Bungkus konten dengan konteks (pola kode lama, diperluas utk KBLI)."""
        meta = chunk.get("metadata", {})
        unit_type = meta.get("unit_type", "pasal")
        dokumen = meta.get("source_file", "").replace("_", " ").replace(".pdf", "")
        isi = chunk.get("content", "")

        if unit_type == "pasal":
            buku = f"Buku: {meta.get('buku')}. " if meta.get("buku") else ""
            bab = f"Bab: {meta.get('bab')}. " if meta.get("bab") else ""
            sect = f"Bagian: {meta.get('section')}. " if meta.get("section") else ""
            return f"Dokumen Hukum: {dokumen}. {buku}{bab}{sect}Isi: {isi}"
        elif unit_type in ("kbli_block", "kbli_dictionary"):
            kode = meta.get("kbli_code", "")
            jenis = ("Klasifikasi usaha" if unit_type == "kbli_dictionary"
                     else "Persyaratan perizinan")
            return f"Dokumen Hukum: {dokumen}. {jenis} KBLI {kode}. Isi: {isi}"
        return f"Dokumen Hukum: {dokumen}. Isi: {isi}"

    def get_or_create_document(self, chunk: dict) -> str:
        meta = chunk.get("metadata", {})
        source_file = meta.get("source_file", "unknown")
        uu_slug = Path(source_file).stem
        doc_type = meta.get("doc_type", "global_uu")
        status = meta.get("status", "active")

        resp = supabase_admin.table("documents") \
            .select("id").eq("doc_type", doc_type).eq("uu_code", uu_slug).execute()
        if resp.data:
            return resp.data[0]["id"]

        new_id = str(uuid.uuid4())
        doc_data = {
            "id": new_id, "doc_type": doc_type, "file_name": source_file,
            "uu_code": uu_slug, "file_type": "json", "status": status,
        }
        if meta.get("superseded_by"):
            doc_data["superseded_by"] = meta["superseded_by"]
        supabase_admin.table("documents").insert(doc_data).execute()
        logger.info(f"[SUCCESS] Dokumen induk baru: {uu_slug} → {new_id}")
        return new_id

    def _get_existing_chunk_indexes(self, doc_id: str) -> set:
        """
        Ambil SEMUA chunk_index yang sudah ada di DB untuk dokumen ini.
        Inilah kunci idempotensi — cek langsung ke database, bukan checkpoint.
        Pakai paginasi karena Supabase batasi 1000 baris per query.
        """
        existing = set()
        page_size = 1000
        offset = 0
        while True:
            resp = supabase_admin.table("document_chunks") \
                .select("chunk_index") \
                .eq("document_id", doc_id) \
                .range(offset, offset + page_size - 1) \
                .execute()
            rows = resp.data or []
            for r in rows:
                if r.get("chunk_index") is not None:
                    existing.add(r["chunk_index"])
            if len(rows) < page_size:
                break
            offset += page_size
        return existing

    def ingest_file(self, json_path: Path):
        logger.info(f"\n[PROCESS] {json_path.name}")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        chunks = data.get("chunks", [])
        if not chunks:
            logger.warning("[WARNING] Tidak ada chunk.")
            return

        doc_id = self.get_or_create_document(chunks[0])

        # KUNCI IDEMPOTEN: ambil chunk_index yang SUDAH ada di database
        existing_idx = self._get_existing_chunk_indexes(doc_id)
        logger.info(f"[INFO] {len(existing_idx)} chunk sudah ada di DB, "
                    f"{len(chunks)} total di file")

        # Hanya proses chunk yang BELUM ada
        pending = [c for c in chunks if c.get("chunk_index") not in existing_idx]

        if not pending:
            logger.info("[SKIP] Dokumen sudah lengkap di DB.")
            return

        logger.info(f"[PROCESS] {len(pending)} chunk perlu di-embed")

        for i in range(0, len(pending), BATCH_SIZE):
            if self.request_count >= RPD_LIMIT:
                logger.warning(f"[STOP] RPD limit ({RPD_LIMIT}) tercapai hari ini. "
                               f"Jalankan lagi besok — otomatis lanjut dari sini.")
                return

            batch = pending[i:i + BATCH_SIZE]
            texts = [self.format_text_for_embedding(c) for c in batch]

            try:
                vectors = _embeddings.embed_documents(texts)
                self.request_count += 1
            except Exception as e:
                logger.error(f"[ERROR] Embedding gagal: {e}")
                logger.warning("[PAUSE] Kemungkinan kena limit. Jeda 30 detik.")
                time.sleep(30)
                continue

            rows = []
            for c, vec in zip(batch, vectors):
                rows.append({
                    "document_id": doc_id,
                    "content": c.get("content", ""),
                    "embedding": vec,
                    "chunk_index": c.get("chunk_index"),
                    "pasal_start": c.get("pasal_start"),
                    "pasal_end": c.get("pasal_end"),
                    "metadata": c.get("metadata", {}),
                    "project_id": None,
                })

            try:
                supabase_admin.table("document_chunks").insert(rows).execute()
                logger.info(f"  [OK] Batch {i//BATCH_SIZE + 1}: "
                            f"{len(rows)} chunk masuk (req #{self.request_count})")
            except Exception as e:
                logger.error(f"[ERROR] Insert gagal: {e}")

            time.sleep(JEDA_ANTAR_BATCH)

        logger.info(f"[SUCCESS] Selesai (sejauh kuota): {json_path.name}")


def main():
    ap = argparse.ArgumentParser(description="KlausulaAI - Ingestion Idempotent")
    ap.add_argument("--input", "-i", required=True, help="Folder *_chunks.json")
    ap.add_argument("--only", default=None,
                    help="Proses hanya file yang namanya mengandung string ini "
                         "(mis. --only cipta_kerja)")
    args = ap.parse_args()

    input_dir = Path(args.input)
    files = sorted(input_dir.glob("*_chunks.json"))
    if args.only:
        files = [f for f in files if args.only in f.name]
    if not files:
        logger.error(f"[ERROR] Tidak ada file cocok di {input_dir}")
        return

    ingestor = ChunkIngestor()
    print(f"\n[START] Ingestion {len(files)} dokumen (idempotent)")
    print(f"Request hari ini akan dihitung, batas RPD {RPD_LIMIT}\n")

    for jf in files:
        if ingestor.request_count >= RPD_LIMIT:
            print(f"\n[STOP] Kuota harian habis. Sisanya lanjut besok.")
            break
        ingestor.ingest_file(jf)

    print(f"\n[DONE] Total request sesi ini: {ingestor.request_count}/{RPD_LIMIT}")
    print("Jalankan lagi kapan saja — chunk yang sudah masuk otomatis dilewati.")


if __name__ == "__main__":
    main()