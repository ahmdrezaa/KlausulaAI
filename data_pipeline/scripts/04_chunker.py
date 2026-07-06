import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime

# ─── Setup Logging ────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"chunking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                            encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Chunker")

# ─── Parameter chunking ───────────────────────────────────────
# gemini-embedding-001 mendukung konteks besar, tapi chunk hukum sebaiknya
# tetap fokus. Ambang konservatif agar mayoritas pasal utuh, hanya pasal
# raksasa (mis. di UU Cipta Kerja) yang dipecah.
MAX_TOKEN_APPROX = 1800
CHARS_PER_TOKEN = 4                       # estimasi kasar teks Indonesia
MAX_CHARS = MAX_TOKEN_APPROX * CHARS_PER_TOKEN

# Pola ayat untuk memecah pasal panjang: (1), (2), (3)...
RE_AYAT = re.compile(r'(?m)^\s*\((\d+)\)\s')


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def split_pasal_by_ayat(content: str, pasal_number: str) -> list:
    """
    Pecah pasal panjang per-ayat, replikasi header 'Pasal X' di tiap pecahan
    agar tiap chunk tetap tahu induknya. Fallback: pecah per-paragraf.
    """
    header = f"Pasal {pasal_number}"
    body = re.sub(rf'^\s*Pasal\s+{re.escape(str(pasal_number))}\s*\n', '',
                  content, count=1)

    matches = list(RE_AYAT.finditer(body))

    # Tanpa ayat bernomor → pecah per-paragraf ganda
    if len(matches) < 2:
        parts = re.split(r'\n\s*\n', body)
        chunks, buf = [], ""
        for part in parts:
            if len(buf) + len(part) > MAX_CHARS and buf:
                chunks.append(f"{header}\n{buf.strip()}")
                buf = part
            else:
                buf += ("\n\n" + part) if buf else part
        if buf.strip():
            chunks.append(f"{header}\n{buf.strip()}")
        return chunks if chunks else [f"{header}\n{body.strip()}"]

    # Pecah per-ayat, gabung sampai mendekati MAX_CHARS
    segments = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        segments.append(body[start:end].strip())

    chunks, buf = [], ""
    for seg in segments:
        if len(buf) + len(seg) > MAX_CHARS and buf:
            chunks.append(f"{header}\n{buf.strip()}")
            buf = seg
        else:
            buf += ("\n" + seg) if buf else seg
    if buf.strip():
        chunks.append(f"{header}\n{buf.strip()}")
    return chunks


class Chunker:
    def __init__(self, doc: dict):
        self.doc = doc
        self.meta = doc.get("metadata", {})
        self.fname = doc.get("file_name", "")
        self.text_quality = doc.get("text_quality", "normal")

    def _base_metadata(self) -> dict:
        """Metadata dasar yang melekat di semua chunk dokumen ini.
        Field-field ini dibaca oleh format_text_for_embedding & retrieval."""
        return {
            "source_file": self.fname,
            "doc_type": self.meta.get("doc_type"),
            "status": self.meta.get("status"),
            "superseded_by": self.meta.get("superseded_by"),
            "text_quality": self.text_quality,
        }

    # ── Chunk unit PASAL ──────────────────────────────────────
    def chunk_pasal(self, unit: dict) -> list:
        content = unit["content"]
        pasal_num = unit.get("pasal_number")
        pasal_int = unit.get("pasal_int")

        struct_meta = {
            "unit_type": "pasal",
            "pasal_number": pasal_num,       # versi lengkap (mis. "156A")
            "section": unit.get("section"),
            "buku": unit.get("buku"),
            "bab": unit.get("bab"),
            "bagian": unit.get("bagian"),
            "source_pages": unit.get("source_pages"),
        }
        base = self._base_metadata()

        # Pasal utuh kalau di bawah ambang
        if estimate_tokens(content) <= MAX_TOKEN_APPROX:
            return [{
                "content": content,
                "pasal_start": pasal_int,
                "pasal_end": pasal_int,
                "metadata": {**base, **struct_meta},
            }]

        # Pasal panjang → pecah per-ayat, replikasi header
        pieces = split_pasal_by_ayat(content, pasal_num)
        out = []
        for i, piece in enumerate(pieces):
            out.append({
                "content": piece,
                "pasal_start": pasal_int,
                "pasal_end": pasal_int,
                "metadata": {**base, **struct_meta,
                             "split_part": i + 1, "split_total": len(pieces)},
            })
        return out

    # ── Chunk unit KBLI_BLOCK (Lampiran: kode → kewajiban) ────
    def chunk_kbli_block(self, unit: dict) -> list:
        base = self._base_metadata()
        return [{
            "content": unit["content"],
            "pasal_start": None,
            "pasal_end": None,
            "metadata": {
                **base,
                "unit_type": "kbli_block",
                "kbli_code": unit.get("kbli_code"),
                "lampiran_ref": unit.get("lampiran_ref"),
                "source_pages": unit.get("source_pages"),
            },
        }]

    # ── Chunk unit KBLI_DICTIONARY (kamus: kode → arti) ───────
    def chunk_kbli_dictionary(self, unit: dict) -> list:
        base = self._base_metadata()
        return [{
            "content": unit["content"],
            "pasal_start": None,
            "pasal_end": None,
            "metadata": {
                **base,
                "unit_type": "kbli_dictionary",
                "kbli_code": unit.get("kbli_code"),
            },
        }]

    # ── Orkestrasi ────────────────────────────────────────────
    def run(self) -> list:
        chunks = []
        for unit in self.doc.get("units", []):
            ut = unit.get("unit_type")
            if ut == "pasal":
                chunks.extend(self.chunk_pasal(unit))
            elif ut == "kbli_block":
                chunks.extend(self.chunk_kbli_block(unit))
            elif ut == "kbli_dictionary":
                chunks.extend(self.chunk_kbli_dictionary(unit))
            else:
                logger.warning(f"[SKIP] unit_type tak dikenal: {ut}")

        # chunk_index berurutan per dokumen
        for i, c in enumerate(chunks):
            c["chunk_index"] = i
        return chunks


def main():
    ap = argparse.ArgumentParser(description="KlausulaAI - Chunker (poin 7-8)")
    ap.add_argument("--input", "-i", required=True, help="Folder/file *_parsed.json")
    ap.add_argument("--output", "-o", default="../05_chunks")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    inp = Path(args.input)
    files = [inp] if inp.is_file() else sorted(inp.glob("*_parsed.json"))
    if not files:
        print(f"[ERROR] Tidak ada *_parsed.json di {inp}")
        return

    print(f"\n[START] Chunking {len(files)} dokumen")
    print("=" * 60)

    grand_total = 0
    dist = {"pasal": 0, "kbli_block": 0, "kbli_dictionary": 0}
    split_count = 0
    per_doc = []

    for i, f in enumerate(files, 1):
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        chunks = Chunker(doc).run()

        stem = f.stem.replace("_parsed", "")
        with open(out / f"{stem}_chunks.json", "w", encoding="utf-8") as fh:
            json.dump({
                "file_name": doc.get("file_name"),
                "metadata": doc.get("metadata", {}),
                "text_quality": doc.get("text_quality", "normal"),
                "chunk_count": len(chunks),
                "chunks": chunks,
            }, fh, ensure_ascii=False, indent=2)

        for c in chunks:
            ut = c["metadata"].get("unit_type", "?")
            if ut in dist:
                dist[ut] += 1
            if c["metadata"].get("split_total"):
                split_count += 1

        grand_total += len(chunks)
        per_doc.append((f.name, len(chunks)))
        print(f"[{i}/{len(files)}] {f.name}: {len(chunks)} chunk")

    print("\n" + "=" * 60)
    print("[SUMMARY]")
    print(f"Dokumen           : {len(files)}")
    print(f"Total chunk       : {grand_total}")
    print(f"  pasal           : {dist['pasal']}")
    print(f"  kbli_block      : {dist['kbli_block']}")
    print(f"  kbli_dictionary : {dist['kbli_dictionary']}")
    print(f"Chunk hasil split : {split_count} (pasal panjang yang dipecah)")
    print(f"\n[DONE] Output → {out}")
    print(f"\nCatatan kuota: {grand_total} chunk. Dengan batch 40/req = "
          f"~{(grand_total + 39) // 40} panggilan embedding (aman thd RPD 1000).")


if __name__ == "__main__":
    main()