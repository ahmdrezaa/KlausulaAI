"""
===============================================================
KlausulaAI - Data Pipeline | Step 02: Text Cleaning & Normalization
===============================================================
Tanggung Jawab: Dzaky Muttaqi Sunaryadi (Data Engineer)
Fase: D1 - Dataset Dokumen UU

DESKRIPSI:
    Membersihkan dan menormalkan teks hasil ekstraksi PDF.
    Khusus dirancang untuk struktur dokumen Undang-Undang Indonesia.

CLEANING RULES yang diterapkan:
    1. Hapus header/footer berulang (nomor halaman, nama dokumen)
    2. Hapus karakter noise (karakter kontrol, unicode aneh)
    3. Normalisasi whitespace & baris kosong berlebih
    4. Normalisasi tanda baca & tanda hubung yang terpotong
    5. Perbaiki kata yang terpotong antar baris (hyphenation)
    6. Normalisasi format nomor pasal, ayat, huruf
    7. Hapus watermark & disclaimer umum dokumen pemerintah

OUTPUT:
    - File JSON cleaned per dokumen
    - Cleaned text report (statistik before-after)

CARA PAKAI:
    python 02_text_cleaner.py --input ../02_extracted_text/ --output ../03_cleaned_text/
===============================================================
"""

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
        logging.FileHandler(LOG_DIR / f"cleaning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TextCleaner")


# ─── Pattern Library ─────────────────────────────────────────
class UUPatterns:
    """
    Kumpulan regex patterns untuk struktur dokumen UU Indonesia.
    Berdasarkan analisis format dari JDIH, DPR.go.id, dan Peraturan.go.id
    """

    # ── Header/Footer Patterns ────────────────────────────────
    # Pola header/footer yang sering muncul di PDF UU pemerintah
    HEADER_FOOTER_PATTERNS = [
        # Nomor halaman standalone
        r'^\s*-\s*\d+\s*-\s*$',
        r'^\s*\d+\s*$',
        r'^\s*Halaman\s+\d+\s*(dari|of)?\s*\d*\s*$',

        # Watermark & disclaimer dokumen pemerintah
        r'(?i)^\s*Direktorat\s+Jenderal\s+Peraturan\s+Perundang.+$',
        r'(?i)^\s*www\.hukumonline\.com.*$',
        r'(?i)^\s*www\.dpr\.go\.id.*$',
        r'(?i)^\s*www\.jdih.*$',
        r'(?i)^\s*www\.peraturan\.go\.id.*$',
        r'(?i)^\s*Catatan.*Hukumonline.*$',
        r'(?i)^\s*JDIH.*BPK.*$',
        r'(?i)^\s*Pusat\s+Peraturan\s+Perundang.*$',

        # Header dokumen berulang (nama UU di tiap halaman)
        r'(?i)^\s*UNDANG.UNDANG\s+REPUBLIK\s+INDONESIA\s*$',
        r'(?i)^\s*PERATURAN\s+PEMERINTAH.*NOMOR.*$',

        # Footer keterangan sumber
        r'(?i)^\s*Sumber\s*:.*$',
        r'(?i)^\s*Diunduh\s+dari\s+.*$',
        r'(?i)^\s*Diperoleh\s+dari\s+.*$',
    ]

    # ── Struktur UU Patterns ──────────────────────────────────
    # Untuk identifikasi & strukturisasi nanti (Step 03)
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
        r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]'  # karakter kontrol
        r'|[\uf000-\uf8ff]'                       # private use area unicode (watermark font)
        r'|[^\x00-\x7f\u00c0-\u024f\u0400-\u04ff]'  # non-Latin non-Cyrillic (typo artifacts)
        , re.UNICODE
    )

    # ── Hyphenation (kata terpotong di akhir baris) ──────────
    HYPHENATION = re.compile(r'(\w+)-\n(\w+)')

    # ── Whitespace normalization ──────────────────────────────
    MULTIPLE_SPACES = re.compile(r'[ \t]+')
    MULTIPLE_NEWLINES = re.compile(r'\n{3,}')

    # ── Tanda baca aneh ───────────────────────────────────────
    QUOTE_NORMALIZE = re.compile(r'["""]')  # smart quotes → biasa
    DASH_NORMALIZE = re.compile(r'[–—]')    # em/en dash → hyphen


class TextCleaner:
    """
    Pembersih teks dokumen UU Indonesia.
    Menerapkan cleaning rules secara bertahap dan terdokumentasi.
    """

    def __init__(self, aggressive: bool = False):
        """
        Args:
            aggressive: Jika True, hapus lebih banyak noise (bisa hilangkan konten valid)
        """
        self.aggressive = aggressive
        self.patterns = UUPatterns()
        self._compiled_hf = [re.compile(p, re.MULTILINE) for p in UUPatterns.HEADER_FOOTER_PATTERNS]

    def remove_header_footer(self, text: str) -> tuple[str, int]:
        """
        Hapus baris yang merupakan header/footer berulang.
        Returns: (cleaned_text, jumlah baris yang dihapus)
        """
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
        """Hapus karakter kontrol dan Unicode noise."""
        # Ganti karakter noise dengan spasi
        text = self.patterns.NOISE_CHARS.sub(' ', text)
        # Normalisasi smart quotes
        text = self.patterns.QUOTE_NORMALIZE.sub('"', text)
        # Normalisasi dash
        text = self.patterns.DASH_NORMALIZE.sub('-', text)
        return text

    def fix_hyphenation(self, text: str) -> str:
        """
        Perbaiki kata yang terpotong di akhir baris.
        Contoh: "keten-\ntuan" → "ketentuan"
        """
        return self.patterns.HYPHENATION.sub(r'\1\2', text)

    def normalize_whitespace(self, text: str) -> str:
        """Normalisasi spasi dan baris kosong berlebih."""
        # Normalisasi spasi horizontal
        text = self.patterns.MULTIPLE_SPACES.sub(' ', text)
        # Strip tiap baris
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        # Maksimal 2 baris kosong berturut-turut
        text = self.patterns.MULTIPLE_NEWLINES.sub('\n\n', text)
        return text.strip()

    def normalize_pasal_format(self, text: str) -> str:
        """
        Normalisasi format penulisan pasal agar konsisten.
        Contoh: "Pasal  12" → "Pasal 12"
                "PASAL 12" → "Pasal 12"
        """
        # Normalisasi kapitalisasi kata kunci struktural
        text = re.sub(r'\bPASAL\b', 'Pasal', text)
        text = re.sub(r'\bBAGIAN\b', 'Bagian', text)
        text = re.sub(r'\bPARAGRAF\b', 'Paragraf', text)
        # Hapus spasi ganda setelah kata kunci
        text = re.sub(r'(Pasal|Bagian|Paragraf)\s{2,}', r'\1 ', text)
        return text

    def clean_page(self, page_text: str, page_num: int = 0) -> dict:
        """
        Bersihkan teks satu halaman dan kembalikan statistik.

        Returns:
            dict dengan keys: cleaned_text, stats
        """
        original_len = len(page_text)
        stats = {
            "page_num": page_num,
            "original_chars": original_len,
            "steps": {}
        }

        # Step 1: Hapus karakter noise
        text = self.remove_noise_chars(page_text)
        stats["steps"]["noise_chars_removed"] = original_len - len(text)

        # Step 2: Hapus header/footer
        text, hf_removed = self.remove_header_footer(text)
        stats["steps"]["header_footer_lines_removed"] = hf_removed

        # Step 3: Perbaiki hyphenation
        text = self.fix_hyphenation(text)

        # Step 4: Normalisasi format pasal
        text = self.normalize_pasal_format(text)

        # Step 5: Normalisasi whitespace (SELALU TERAKHIR)
        text = self.normalize_whitespace(text)

        stats["cleaned_chars"] = len(text)
        stats["reduction_pct"] = round((1 - len(text) / original_len) * 100, 1) if original_len > 0 else 0

        return {
            "cleaned_text": text,
            "stats": stats
        }

    def clean_document(self, extracted_json_path: str) -> dict:
        """
        Bersihkan seluruh dokumen dari file JSON hasil ekstraksi.

        Args:
            extracted_json_path: Path ke file JSON dari step 01

        Returns:
            Dict dokumen yang sudah dibersihkan
        """
        logger.info(f"🧹 Membersihkan: {Path(extracted_json_path).name}")

        with open(extracted_json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        cleaned_pages = []
        total_stats = {
            "total_pages": len(doc["pages"]),
            "pages_with_content": 0,
            "pages_empty_after_cleaning": 0,
            "total_original_chars": 0,
            "total_cleaned_chars": 0,
            "total_hf_removed": 0
        }

        for page_data in doc["pages"]:
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

            # Update total stats
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

        # Reduction percentage
        if total_stats["total_original_chars"] > 0:
            total_stats["overall_reduction_pct"] = round(
                (1 - total_stats["total_cleaned_chars"] / total_stats["total_original_chars"]) * 100, 1
            )
        else:
            total_stats["overall_reduction_pct"] = 0

        # Build output document
        cleaned_doc = {
            **doc,
            "cleaning_date": datetime.now().isoformat(),
            "cleaning_stats": total_stats,
            "pages": cleaned_pages
        }

        logger.info(f"  ✅ Selesai: {total_stats['total_original_chars']:,} → {total_stats['total_cleaned_chars']:,} chars "
                    f"(berkurang {total_stats['overall_reduction_pct']}%)")
        logger.info(f"  📄 {total_stats['pages_with_content']} halaman berkonten, "
                    f"{total_stats['pages_empty_after_cleaning']} halaman kosong setelah cleaning")

        return cleaned_doc

    def merge_pages_to_full_text(self, cleaned_doc: dict) -> str:
        """
        Gabungkan semua halaman menjadi satu teks utuh.
        Berguna untuk analisis & debugging.
        """
        parts = []
        for page in cleaned_doc["pages"]:
            text = page.get("cleaned_text", "").strip()
            if text:
                parts.append(f"[HALAMAN {page['page_num']}]\n{text}")

        return "\n\n".join(parts)


# ─── CLI Interface ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="KlausulaAI - Text Cleaner untuk Dokumen UU Indonesia"
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

    # Kumpulkan file yang akan diproses
    if input_path.is_file():
        json_files = [input_path]
    else:
        json_files = [f for f in input_path.glob("*_extracted.json")]

    if not json_files:
        print(f"❌ Tidak ada file JSON ditemukan di: {input_path}")
        return

    print(f"\n🧹 Membersihkan {len(json_files)} dokumen...")
    print("="*60)

    all_stats = []
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] {json_file.name}")

        try:
            cleaned_doc = cleaner.clean_document(str(json_file))

            # Simpan cleaned JSON
            stem = json_file.stem.replace("_extracted", "")
            output_path = output_dir / f"{stem}_cleaned.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_doc, f, ensure_ascii=False, indent=2)

            # Opsional: simpan full text untuk inspeksi
            if args.save_full_text:
                full_text = cleaner.merge_pages_to_full_text(cleaned_doc)
                txt_path = output_dir / f"{stem}_full.txt"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                logger.info(f"  📄 Full text: {txt_path}")

            stats = cleaned_doc["cleaning_stats"]
            stats["file_name"] = json_file.name
            all_stats.append(stats)

        except Exception as e:
            logger.error(f"❌ Gagal membersihkan {json_file.name}: {e}")

    # ── Ringkasan ─────────────────────────────────────────────
    print("\n" + "="*60)
    print("📊 RINGKASAN CLEANING")
    print("="*60)
    print(f"Dokumen diproses  : {len(all_stats)}")

    if all_stats:
        total_orig = sum(s["total_original_chars"] for s in all_stats)
        total_clean = sum(s["total_cleaned_chars"] for s in all_stats)
        avg_reduction = sum(s["overall_reduction_pct"] for s in all_stats) / len(all_stats)
        total_hf = sum(s["total_hf_removed"] for s in all_stats)

        print(f"Total original    : {total_orig:,} karakter")
        print(f"Total cleaned     : {total_clean:,} karakter")
        print(f"Rata-rata reduksi : {avg_reduction:.1f}%")
        print(f"Total HF dihapus  : {total_hf:,} baris")

    print(f"\n✅ Output tersimpan di: {output_dir}")


if __name__ == "__main__":
    main()
