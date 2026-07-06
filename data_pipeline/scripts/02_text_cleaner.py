import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime

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
    """Regex untuk struktur & noise dokumen hukum Indonesia."""

    # ── Noise MURNI: dibuang total, tidak punya nilai sitasi ──
    # Judul dokumen (PERATURAN PEMERINTAH ... NOMOR ...) TIDAK dimasukkan
    # ke sini, karena itu identitas dokumen.
    NOISE_LINE_PATTERNS = [
        r'^\s*-\s*\d+\s*-\s*$',                   # -14-
        r'^\s*\d+\s*$',                            # nomor halaman polos (dilindungi di mode safe)
        r'^\s*Halaman\s+\d+\s*(dari|of)?\s*\d*\s*$',
        r'(?i)^\s*www\.hukumonline\.com.*$',
        r'(?i)^\s*www\.dpr\.go\.id.*$',
        r'(?i)^\s*www\.jdih.*$',
        r'(?i)^\s*www\.peraturan\.go\.id.*$',
        r'(?i)^\s*www\.bps\.go\.id.*$',
        r'(?i)^\s*Catatan.*Hukumonline.*$',
        r'(?i)^\s*JDIH.*BPK.*$',
        r'(?i)^\s*Pusat\s+Peraturan\s+Perundang.*$',
        r'(?i)^\s*Direktorat\s+Jenderal\s+Peraturan\s+Perundang.+$',
        r'^\s*\d{4},\s*No\.\s*\d+\s*$',            # "2021, No.316" (Berita Negara)
        r'(?i)^\s*SK\s+No\s+\d+\s*[A-Z]?\s*$',     # "SK No 130252 C" (footer PP 28)
        r'(?i)^\s*Sumber\s*:.*$',
        r'(?i)^\s*Diunduh\s+dari\s+.*$',
        r'(?i)^\s*Diperoleh\s+dari\s+.*$',
    ]

    # ── Penanda POSISI: diangkat ke metadata, lalu dibersihkan dari teks ──
    LAMPIRAN_REF = re.compile(r'^\s*([IVX]+\.[A-Z]\.\d+)\s*$', re.MULTILINE)  # I.L.25
    KOP_PRESIDEN = re.compile(r'(?i)^\s*PRES[Il!]DEN\s*$', re.MULTILINE)
    KOP_REPUBLIK = re.compile(r'(?i)^\s*R[.,]?EP[IU][BE]L[Il]K\s+INDONESIA\s*$', re.MULTILINE)
    KOP_UU_RI     = re.compile(r'(?i)^\s*UNDANG.UNDANG\s+REPUBLIK\s+INDONESIA\s*$', re.MULTILINE)

    # ── Struktur hierarki (untuk metadata & normalisasi) ──────
    BUKU_PATTERN = re.compile(
        r'^\s*(Buku\s+(?:Kesatu|Kedua|Ketiga|Keempat|Kelima|I|II|III|IV|V|\d+))\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    BAB_PATTERN = re.compile(
        r'^\s*BAB\s+([IVXLCDM]+|\d+)\s*$', re.IGNORECASE | re.MULTILINE
    )
    PASAL_PATTERN = re.compile(
        r'^\s*Pasal\s+(\d+[A-Z]?)\s*$', re.IGNORECASE | re.MULTILINE
    )

    # ── Karakter kontrol (AMAN dibuang di semua mode) ─────────
    # HANYA karakter kontrol & private-use-area. TIDAK membuang non-ASCII
    # secara membabi buta (itu bug lama yang merusak tabel).
    CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]|[\uf000-\uf8ff]')

    # ── Normalisasi ringan ────────────────────────────────────
    HYPHENATION = re.compile(r'(\w+)-\n(\w+)')
    MULTIPLE_SPACES = re.compile(r'[ \t]+')
    MULTIPLE_NEWLINES = re.compile(r'\n{3,}')
    SMART_QUOTES = re.compile(r'[\u201c\u201d\u2018\u2019]')
    DASHES = re.compile(r'[\u2013\u2014]')

    # Istilah hukum bertanda hubung yang SAH — jangan disambung saat fix hyphenation
    HYPHEN_WHITELIST = {
        "perundang-undangan", "undang-undang", "masing-masing", "sebaik-baiknya",
        "sebesar-besarnya", "selambat-lambatnya", "sungguh-sungguh", "hati-hati",
        "rata-rata", "bagian-bagian", "hal-hal", "syarat-syarat", "barang-barang",
        "kadang-kadang", "tiba-tiba", "berturut-turut", "sewaktu-waktu",
    }


class TextCleaner:
    """
    Cleaner dua-mode untuk dokumen hukum.

    Mode dipilih PER-HALAMAN berdasarkan zona (carry-forward is_lampiran):
      - Zona Lampiran (tabel/daftar KBLI) → mode SAFE:
          pembersihan minimal, lindungi angka/kode/simbol/struktur baris.
      - Zona Pasal (naratif)              → mode AGGRESSIVE:
          normalisasi lebih dalam (aman karena tidak ada tabel).

    --force-mode memaksa satu mode untuk seluruh dokumen (mis. file hasil
    split Lampiran yang tak punya penanda 'LAMPIRAN' di halaman awal).
    """

    def __init__(self, force_mode: str = "auto"):
        # force_mode: 'auto' | 'safe' | 'aggressive'
        self.force_mode = force_mode
        self.p = UUPatterns()
        self._noise_re = [re.compile(pat, re.MULTILINE) for pat in UUPatterns.NOISE_LINE_PATTERNS]

    # ── Ekstraksi penanda posisi SEBELUM pembersihan ──────────
    def extract_position_markers(self, text: str) -> dict:
        """Angkat penanda struktural ke metadata sebelum teks dibersihkan."""
        markers = {}

        ref = self.p.LAMPIRAN_REF.findall(text)
        if ref:
            markers["lampiran_ref"] = ref[0]        # mis. "I.L.25"

        pasal = self.p.PASAL_PATTERN.findall(text)
        if pasal:
            markers["pasal_in_page"] = pasal        # mis. ["29", "30", "31"]

        bab = self.p.BAB_PATTERN.findall(text)
        if bab:
            markers["bab_in_page"] = bab

        buku = self.p.BUKU_PATTERN.findall(text)
        if buku:
            markers["buku_in_page"] = buku

        return markers

    # ── Pembersihan bertahap ──────────────────────────────────
    def remove_control_chars(self, text: str) -> str:
        """Buang HANYA karakter kontrol & private-use. Aman untuk tabel."""
        text = self.p.CONTROL_CHARS.sub(' ', text)
        text = self.p.SMART_QUOTES.sub('"', text)
        text = self.p.DASHES.sub('-', text)
        return text

    def remove_position_markers_from_text(self, text: str) -> str:
        """Hapus penanda posisi & kop dari BADAN teks (sudah disimpan ke metadata)."""
        text = self.p.LAMPIRAN_REF.sub('', text)
        text = self.p.KOP_PRESIDEN.sub('', text)
        text = self.p.KOP_REPUBLIK.sub('', text)
        text = self.p.KOP_UU_RI.sub('', text)
        return text

    def remove_noise_lines(self, text: str, protect_bare_numbers: bool) -> tuple[str, int]:
        """
        Buang baris noise murni.
        protect_bare_numbers=True (mode safe/Lampiran): JANGAN buang baris
        yang isinya cuma angka — bisa jadi kode KBLI atau data tabel.
        """
        lines = text.split('\n')
        kept, removed = [], 0

        for line in lines:
            is_noise = False
            for rx in self._noise_re:
                # Di mode safe, lewati aturan "angka polos" agar data tabel aman
                if protect_bare_numbers and rx.pattern == r'^\s*\d+\s*$':
                    continue
                if rx.match(line):
                    is_noise = True
                    removed += 1
                    break
            if not is_noise:
                kept.append(line)

        return '\n'.join(kept), removed

    def fix_hyphenation(self, text: str) -> str:
        """
        Sambung kata terpotong di akhir baris, TAPI hormati istilah
        bertanda hubung yang sah (perundang-undangan, masing-masing, dst).
        """
        def _join(m):
            bertanda = (m.group(1) + '-' + m.group(2)).lower()
            if bertanda in self.p.HYPHEN_WHITELIST:
                return m.group(1) + '-' + m.group(2)
            return m.group(1) + m.group(2)

        return self.p.HYPHENATION.sub(_join, text)

    def normalize_structural_keywords(self, text: str) -> str:
        """Normalisasi kapitalisasi kata kunci struktural (mode aggressive saja)."""
        text = re.sub(r'\bBUKU\b', 'Buku', text)
        text = re.sub(r'\bPASAL\b', 'Pasal', text)
        text = re.sub(r'\bBAGIAN\b', 'Bagian', text)
        text = re.sub(r'\bPARAGRAF\b', 'Paragraf', text)
        text = re.sub(r'(Buku|Pasal|Bagian|Paragraf)\s{2,}', r'\1 ', text)
        return text

    def normalize_whitespace(self, text: str) -> str:
        text = self.p.MULTIPLE_SPACES.sub(' ', text)
        lines = [ln.rstrip() for ln in text.split('\n')]
        text = '\n'.join(lines)
        text = self.p.MULTIPLE_NEWLINES.sub('\n\n', text)
        return text.strip()

    # ── Pembersih satu halaman (mode-aware) ───────────────────
    def clean_page(self, page_text: str, page_num: int, is_lampiran: bool) -> dict:
        original_len = len(page_text)

        # Tentukan mode efektif
        if self.force_mode == "safe":
            mode = "safe"
        elif self.force_mode == "aggressive":
            mode = "aggressive"
        else:  # auto: Lampiran → safe, Pasal → aggressive
            mode = "safe" if is_lampiran else "aggressive"

        # 1. Angkat penanda posisi ke metadata (SEBELUM apa pun dihapus)
        markers = self.extract_position_markers(page_text)

        # 2. Buang karakter kontrol (aman di semua mode)
        text = self.remove_control_chars(page_text)

        # 3. Hapus penanda posisi & kop dari badan teks
        text = self.remove_position_markers_from_text(text)

        # 4. Buang baris noise murni (lindungi angka polos jika mode safe)
        text, hf_removed = self.remove_noise_lines(
            text, protect_bare_numbers=(mode == "safe")
        )

        # 5. Perbaikan hyphenation (kedua mode; aman karena whitelist)
        text = self.fix_hyphenation(text)

        # 6. Normalisasi kata kunci struktural HANYA di mode aggressive
        #    (di Lampiran, "PASAL" bisa muncul di dalam sel tabel — jangan diutak-atik)
        if mode == "aggressive":
            text = self.normalize_structural_keywords(text)

        # 7. Normalisasi whitespace (selalu terakhir)
        text = self.normalize_whitespace(text)

        cleaned_len = len(text)
        return {
            "cleaned_text": text,
            "position_markers": markers,
            "stats": {
                "page_num": page_num,
                "mode": mode,
                "original_chars": original_len,
                "cleaned_chars": cleaned_len,
                "hf_removed": hf_removed,
                "reduction_pct": round((1 - cleaned_len / original_len) * 100, 1) if original_len else 0,
            }
        }

    # ── Pembersih satu dokumen (dengan carry-forward zona) ────
    def clean_document(self, extracted_json_path: str) -> dict:
        logger.info(f"[CLEANING] {Path(extracted_json_path).name}")

        with open(extracted_json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        if "metadata" in doc:
            logger.info(f"  [META] doc_type={doc['metadata'].get('doc_type')} "
                        f"status={doc['metadata'].get('status')}")

        cleaned_pages = []
        total = {
            "total_pages": len(doc.get("pages", [])),
            "pages_with_content": 0,
            "pages_empty_after_cleaning": 0,
            "total_original_chars": 0,
            "total_cleaned_chars": 0,
            "total_hf_removed": 0,
            "pages_safe_mode": 0,
            "pages_aggressive_mode": 0,
            "lampiran_zone_start": None,
        }

        # ── CARRY-FORWARD: sekali masuk zona Lampiran, tetap Lampiran ──
        in_lampiran_zone = False

        for page in doc.get("pages", []):
            # Lewati halaman error/kosong
            if page.get("has_error") or not page.get("text", "").strip():
                cleaned_pages.append({
                    **page,
                    "cleaned_text": "",
                    "position_markers": {},
                    "effective_zone": "lampiran" if in_lampiran_zone else "pasal",
                    "cleaning_stats": {"skipped": True, "reason": "error_or_empty"}
                })
                continue

            # Aktifkan zona Lampiran begitu halaman pertama ber-is_lampiran ditemukan.
            # Setelah aktif, SEMUA halaman berikutnya dianggap Lampiran (carry-forward).
            if page.get("is_lampiran", False) and not in_lampiran_zone:
                in_lampiran_zone = True
                total["lampiran_zone_start"] = page["page_num"]
                logger.info(f"  [ZONA] Lampiran mulai halaman {page['page_num']} "
                            f"→ carry-forward aktif")

            # Mode paksa mengabaikan zona; mode auto memakai zona efektif
            if self.force_mode == "safe":
                effective_is_lampiran = True
            elif self.force_mode == "aggressive":
                effective_is_lampiran = False
            else:
                effective_is_lampiran = in_lampiran_zone

            res = self.clean_page(page["text"], page["page_num"], effective_is_lampiran)
            st = res["stats"]

            total["total_original_chars"] += st["original_chars"]
            total["total_cleaned_chars"] += st["cleaned_chars"]
            total["total_hf_removed"] += st["hf_removed"]
            if st["mode"] == "safe":
                total["pages_safe_mode"] += 1
            else:
                total["pages_aggressive_mode"] += 1

            if res["cleaned_text"].strip():
                total["pages_with_content"] += 1
            else:
                total["pages_empty_after_cleaning"] += 1

            cleaned_pages.append({
                **page,
                "cleaned_text": res["cleaned_text"],
                "position_markers": res["position_markers"],
                "effective_zone": "lampiran" if effective_is_lampiran else "pasal",
                "cleaning_stats": st,
            })

        total["overall_reduction_pct"] = round(
            (1 - total["total_cleaned_chars"] / total["total_original_chars"]) * 100, 1
        ) if total["total_original_chars"] else 0

        cleaned_doc = {
            **doc,
            "cleaning_date": datetime.now().isoformat(),
            "cleaning_stats": total,
            "pages": cleaned_pages,
        }

        logger.info(f"  [OK] {total['total_original_chars']:,} → "
                    f"{total['total_cleaned_chars']:,} chars "
                    f"({total['overall_reduction_pct']}% turun) | "
                    f"safe={total['pages_safe_mode']} agg={total['pages_aggressive_mode']}"
                    + (f" | Lampiran dari hal {total['lampiran_zone_start']}"
                       if total['lampiran_zone_start'] else ""))
        return cleaned_doc

    # ── Gabung halaman jadi full text (untuk inspeksi manual) ──
    def merge_pages_to_full_text(self, cleaned_doc: dict) -> str:
        parts = []
        for page in cleaned_doc["pages"]:
            text = page.get("cleaned_text", "").strip()
            if text:
                ref = page.get("position_markers", {}).get("lampiran_ref", "")
                tag = f"[HAL {page['page_num']}{' | ' + ref if ref else ''}]"
                parts.append(f"{tag}\n{text}")
        return "\n\n".join(parts)


# ─── CLI ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="KlausulaAI - Text Cleaner dua-mode untuk dokumen hukum"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="Folder/file JSON hasil ekstraksi (step 01)")
    parser.add_argument("--output", "-o", default="../03_cleaned_text")
    parser.add_argument("--force-mode", choices=["auto", "safe", "aggressive"],
                        default="auto",
                        help="auto=per-halaman via zona (default); "
                             "safe/aggressive=paksa satu mode utk seluruh dokumen")
    parser.add_argument("--save-full-text", action="store_true",
                        help="Simpan juga .txt untuk inspeksi manual")
    args = parser.parse_args()

    cleaner = TextCleaner(force_mode=args.force_mode)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)
    json_files = ([input_path] if input_path.is_file()
                  else sorted(input_path.glob("*_extracted.json")))

    if not json_files:
        print(f"[ERROR] Tidak ada *_extracted.json di: {input_path}")
        return

    print(f"\n[START] Membersihkan {len(json_files)} dokumen (mode: {args.force_mode})")
    print("=" * 60)

    all_stats = []
    for i, jf in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] {jf.name}")
        try:
            cleaned = cleaner.clean_document(str(jf))
            stem = jf.stem.replace("_extracted", "")

            with open(output_dir / f"{stem}_cleaned.json", "w", encoding="utf-8") as f:
                json.dump(cleaned, f, ensure_ascii=False, indent=2)

            if args.save_full_text:
                with open(output_dir / f"{stem}_full.txt", "w", encoding="utf-8") as f:
                    f.write(cleaner.merge_pages_to_full_text(cleaned))

            st = cleaned["cleaning_stats"]
            st["file_name"] = jf.name
            all_stats.append(st)
        except Exception as e:
            logger.error(f"[ERROR] {jf.name}: {e}", exc_info=True)

    # Ringkasan
    print("\n" + "=" * 60)
    print("[SUMMARY]")
    print(f"Dokumen diproses : {len(all_stats)}")
    if all_stats:
        to = sum(s["total_original_chars"] for s in all_stats)
        tc = sum(s["total_cleaned_chars"] for s in all_stats)
        avg = sum(s["overall_reduction_pct"] for s in all_stats) / len(all_stats)
        safe = sum(s["pages_safe_mode"] for s in all_stats)
        agg = sum(s["pages_aggressive_mode"] for s in all_stats)
        print(f"Total original   : {to:,} char")
        print(f"Total cleaned    : {tc:,} char")
        print(f"Rata-rata reduksi: {avg:.1f}%")
        print(f"Halaman safe/agg : {safe} / {agg}")
    print(f"\n[DONE] Output → {output_dir}")


if __name__ == "__main__":
    main()