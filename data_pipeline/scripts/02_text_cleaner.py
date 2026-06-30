import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from copy import deepcopy

# ─── Setup Logging ───────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"cleaning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", 
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TextCleaner")


# ─── Pattern Library ─────────────────────────────────────────
class UUPatterns:
    """
    Kumpulan regex patterns untuk struktur dokumen Hukum Indonesia.
    Diperluas untuk mencakup KUHPerdata dan KUHD selain UU/PP standar.
    """

    # ── Header/Footer Patterns ────────────────────────────────
    HEADER_FOOTER_PATTERNS = [
        r'^\s*-\s*\d+\s*-\s*$',
        r'^\s*\d+\s*$',
        r'^\s*Halaman\s+\d+\s*(dari|of)?\s*\d*\s*$',
        r'(?i)^\s*Direktorat\s+Jenderal\s+Peraturan\s+Perundang.+$',
        r'(?i)^\s*www\.hukumonline\.com.*$',
        r'(?i)^\s*www\.dpr\.go\.id.*$',
        r'(?i)^\s*www\.jdih.*$',
        r'(?i)^\s*www\.peraturan\.go\.id.*$',
        r'(?i)^\s*Catatan.*Hukumonline.*$',
        r'(?i)^\s*JDIH.*BPK.*$',
        r'(?i)^\s*Pusat\s+Peraturan\s+Perundang.*$',
        r'(?i)^\s*UNDANG.UNDANG\s+REPUBLIK\s+INDONESIA\s*$',
        r'(?i)^\s*PERATURAN\s+PEMERINTAH.*NOMOR.*$',
        r'(?i)^\s*Sumber\s*:.*$',
        r'(?i)^\s*Diunduh\s+dari\s+.*$',
        r'(?i)^\s*Diperoleh\s+dari\s+.*$',
    ]

    # ── Struktur Hukum Patterns ───────────────────────────────
    # Ditambahkan BUKU_PATTERN untuk mengakomodasi KUHPerdata/KUHD
    BUKU_PATTERN = re.compile(
        r'^\s*(Buku\s+(?:Kesatu|Kedua|Ketiga|Keempat|Kelima|I|II|III|IV|V|\d+))\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    BAB_PATTERN = re.compile(
        r'^\s*(BAB\s+[IVXLCDM]+|BAB\s+\d+)\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    BAGIAN_PATTERN = re.compile(
        r'^\s*(Bagian\s+(?:Kesatu|Kedua|Ketiga|Keempat|Kelima|Keenam|Ketujuh|Kedelapan|Kesembilan|Kesepuluh|\w+))\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    PARAGRAF_PATTERN = re.compile(
        r'^\s*(Paragraf\s+\d+)\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    PASAL_PATTERN = re.compile(
        r'^\s*Pasal\s+(\d+[A-Z]?)\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    AYAT_PATTERN = re.compile(
        r'^\s*\((\d+)\)\s+',
        re.MULTILINE
    )
    HURUF_PATTERN = re.compile(
        r'^\s*([a-z])\.\s+',
        re.MULTILINE
    )
    ANGKA_PATTERN = re.compile(
        r'^\s*(\d+)\.\s+',
        re.MULTILINE
    )

    # ── Karakter Noise ────────────────────────────────────────
    NOISE_CHARS = re.compile(
        r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]'  
        r'|[\uf000-\uf8ff]'                  
        r'|[^\x00-\x7f\u00c0-\u024f\u0400-\u04ff]'  
        , re.UNICODE
    )

    # ── Hyphenation ───────────────────────────────────────────
    HYPHENATION = re.compile(r'(\w+)-\n(\w+)')

    # ── Whitespace normalization ──────────────────────────────
    MULTIPLE_SPACES = re.compile(r'[ \t]+')
    MULTIPLE_NEWLINES = re.compile(r'\n{3,}')
    
    # ── Tanda baca aneh ───────────────────────────────────────
    QUOTE_NORMALIZE = re.compile(r'["""]')  
    DASH_NORMALIZE = re.compile(r'[–—]')    


class TextCleaner:
    def __init__(self, aggressive: bool = False):
        self.aggressive = aggressive
        self.patterns = UUPatterns()
        self._compiled_hf = [re.compile(p, re.MULTILINE) for p in UUPatterns.HEADER_FOOTER_PATTERNS]

    def remove_header_footer(self, text: str) -> tuple[str, int]:
        lines = text.split('\n')
        cleaned_lines = []
        removed_count = 0

        for line in lines:
            is_noise = False
            for pattern in self._compiled_hf:
                if pattern.match(line):
                    is_noise = True
                    removed_count += 1
                    break

            if not is_noise:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines), removed_count

    def remove_noise_chars(self, text: str) -> str:
        text = self.patterns.NOISE_CHARS.sub(' ', text)
        text = self.patterns.QUOTE_NORMALIZE.sub('"', text)
        text = self.patterns.DASH_NORMALIZE.sub('-', text)
        return text

    def fix_hyphenation(self, text: str) -> str:
        return self.patterns.HYPHENATION.sub(r'\1\2', text)

    def normalize_whitespace(self, text: str) -> str:
        text = self.patterns.MULTIPLE_SPACES.sub(' ', text)
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        text = self.patterns.MULTIPLE_NEWLINES.sub('\n\n', text)
        return text.strip()

    def normalize_pasal_format(self, text: str) -> str:
        # Ditambahkan 'Buku' untuk normalisasi hierarki KUHPerdata
        text = re.sub(r'\bBUKU\b', 'Buku', text, flags=re.IGNORECASE)
        text = re.sub(r'\bPASAL\b', 'Pasal', text, flags=re.IGNORECASE)
        text = re.sub(r'\bBAGIAN\b', 'Bagian', text, flags=re.IGNORECASE)
        text = re.sub(r'\bPARAGRAF\b', 'Paragraf', text, flags=re.IGNORECASE)
        
        # Hapus spasi ganda setelah kata kunci
        text = re.sub(r'(Buku|Pasal|Bagian|Paragraf)\s{2,}', r'\1 ', text)
        return text

    def clean_page(self, page_text: str, page_num: int = 0) -> dict:
        original_len = len(page_text)
        stats = {
            "page_num": page_num,
            "original_chars": original_len,
            "steps": {}
        }

        text = self.remove_noise_chars(page_text)
        stats["steps"]["noise_chars_removed"] = original_len - len(text)

        text, hf_removed = self.remove_header_footer(text)
        stats["steps"]["header_footer_lines_removed"] = hf_removed

        text = self.fix_hyphenation(text)
        text = self.normalize_pasal_format(text)
        text = self.normalize_whitespace(text)

        stats["cleaned_chars"] = len(text)
        stats["reduction_pct"] = round((1 - len(text) / original_len) * 100, 1) if original_len > 0 else 0

        return {
            "cleaned_text": text,
            "stats": stats
        }

    def clean_document(self, extracted_json_path: str) -> dict:
        logger.info(f"[CLEANING] Membersihkan: {Path(extracted_json_path).name}")

        with open(extracted_json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
            
        # Logging untuk memastikan Data Engineer tahu metadata dari langkah 01 aman
        if "metadata" in doc:
            logger.info(f"  [METADATA] Tipe: {doc['metadata'].get('doc_type')} | Status: {doc['metadata'].get('status')}")

        cleaned_pages = []
        total_stats = {
            "total_pages": len(doc.get("pages", [])),
            "pages_with_content": 0,
            "pages_empty_after_cleaning": 0,
            "total_original_chars": 0,
            "total_cleaned_chars": 0,
            "total_hf_removed": 0
        }

        for page_data in doc.get("pages", []):
            if page_data.get("has_error") or not page_data.get("text"):
                cleaned_pages.append({
                    **page_data,
                    "cleaned_text": "",
                    "cleaning_stats": {"skipped": True, "reason": "error_or_empty"}
                })
                continue

            result = self.clean_page(page_data["text"], page_data["page_num"])
            cleaned_text = result["cleaned_text"]
            stats = result["stats"]

            total_stats["total_original_chars"] += stats["original_chars"]
            total_stats["total_cleaned_chars"] += stats["cleaned_chars"]
            total_stats["total_hf_removed"] += stats["steps"].get("header_footer_lines_removed", 0)

            if cleaned_text.strip():
                total_stats["pages_with_content"] += 1
            else:
                total_stats["pages_empty_after_cleaning"] += 1

            cleaned_pages.append({
                **page_data,
                "cleaned_text": cleaned_text,
                "cleaning_stats": stats
            })

        if total_stats["total_original_chars"] > 0:
            total_stats["overall_reduction_pct"] = round(
                (1 - total_stats["total_cleaned_chars"] / total_stats["total_original_chars"]) * 100, 1
            )
        else:
            total_stats["overall_reduction_pct"] = 0

        # Build output document - metadata dari step 01 otomatis terbawa lewat **doc
        cleaned_doc = {
            **doc,
            "cleaning_date": datetime.now().isoformat(),
            "cleaning_stats": total_stats,
            "pages": cleaned_pages
        }

        logger.info(f"  [SUCCESS] Selesai: {total_stats['total_original_chars']:,} -> {total_stats['total_cleaned_chars']:,} chars "
                    f"(berkurang {total_stats['overall_reduction_pct']}%)")

        return cleaned_doc

    def merge_pages_to_full_text(self, cleaned_doc: dict) -> str:
        parts = []
        for page in cleaned_doc["pages"]:
            text = page.get("cleaned_text", "").strip()
            if text:
                parts.append(f"[HALAMAN {page['page_num']}]\n{text}")
        return "\n\n".join(parts)


# ─── CLI Interface ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="KlausulaAI - Text Cleaner untuk Dokumen Hukum (UU, PP, KUHP)"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="Folder JSON hasil ekstraksi (dari step 01) atau single file JSON")
    parser.add_argument("--output", "-o", default="../03_cleaned_text",
                        help="Folder output cleaned JSON")
    parser.add_argument("--aggressive", action="store_true",
                        help="Mode agresif: hapus lebih banyak noise")
    parser.add_argument("--save-full-text", action="store_true",
                        help="Simpan juga versi full text (.txt) untuk inspeksi manual")
    args = parser.parse_args()

    cleaner = TextCleaner(aggressive=args.aggressive)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)

    if input_path.is_file():
        json_files = [input_path]
    else:
        json_files = [f for f in input_path.glob("*_extracted.json")]

    if not json_files:
        print(f"[ERROR] Tidak ada file JSON ditemukan di: {input_path}")
        return

    print(f"\n[START] Membersihkan {len(json_files)} dokumen...")
    print("="*60)

    all_stats = []
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] {json_file.name}")

        try:
            cleaned_doc = cleaner.clean_document(str(json_file))

            stem = json_file.stem.replace("_extracted", "")
            output_path = output_dir / f"{stem}_cleaned.json"
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_doc, f, ensure_ascii=False, indent=2)

            if args.save_full_text:
                full_text = cleaner.merge_pages_to_full_text(cleaned_doc)
                txt_path = output_dir / f"{stem}_full.txt"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                logger.info(f"  [INFO] Full text: {txt_path}")

            stats = cleaned_doc["cleaning_stats"]
            stats["file_name"] = json_file.name
            all_stats.append(stats)

        except Exception as e:
            logger.error(f"[ERROR] Gagal membersihkan {json_file.name}: {e}")

    print("\n" + "="*60)
    print("[SUMMARY] RINGKASAN CLEANING")
    print("="*60)
    print(f"Dokumen diproses  : {len(all_stats)}")

    if all_stats:
        total_orig = sum(s["total_original_chars"] for s in all_stats)
        total_clean = sum(s["total_cleaned_chars"] for s in all_stats)
        avg_reduction = sum(s.get("overall_reduction_pct", 0) for s in all_stats) / len(all_stats)
        total_hf = sum(s["total_hf_removed"] for s in all_stats)

        print(f"Total original    : {total_orig:,} karakter")
        print(f"Total cleaned     : {total_clean:,} karakter")
        print(f"Rata-rata reduksi : {avg_reduction:.1f}%")
        print(f"Total HF dihapus  : {total_hf:,} baris")

    print(f"\n[DONE] Output tersimpan di: {output_dir}")

if __name__ == "__main__":
    main()