"""
===============================================================
KlausulaAI - Data Pipeline | Step 03: Structure Parsing (Bab/Pasal/Ayat)
===============================================================
Tanggung Jawab: Dzaky Muttaqi Sunaryadi (Data Engineer)
Fase: D1 - Dataset Dokumen UU
===============================================================
"""

import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

# ─── Setup Logging ────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        # Pastikan encoding="utf-8" ada di sini agar tidak error di Windows
        logging.FileHandler(LOG_DIR / f"parsing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StructureParser")


# ─── Data Structures ──────────────────────────────────────────
@dataclass
class Ayat:
    nomor: str
    teks: str
    huruf: list = field(default_factory=list)


@dataclass
class Pasal:
    pasal_id: str
    pasal_number: str
    full_text: str
    ayat: list
    uu_name: str = ""
    uu_number: str = ""
    uu_year: str = ""
    uu_topic: str = ""
    uu_slug: str = ""
    bab_number: str = ""
    bab_title: str = ""
    bagian: str = ""
    paragraf: str = ""
    source_pages: list = field(default_factory=list)
    parsed_date: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UUDocument:
    uu_id: str
    uu_name: str
    uu_number: str
    uu_year: str
    uu_topic: str
    total_pasal: int = 0
    total_bab: int = 0
    pasal_list: list = field(default_factory=list)
    raw_text: str = ""
    parsed_date: str = field(default_factory=lambda: datetime.now().isoformat())


# ─── UU Metadata Catalog ─────────────────────────────────────
UU_CATALOG = {
    "uu_ketenagakerjaan": {
        "name": "Undang-Undang Nomor 13 Tahun 2003 tentang Ketenagakerjaan",
        "number": "13", "year": "2003", "topic": "Ketenagakerjaan",
        "keywords": ["ketenagakerjaan", "tenaga kerja", "buruh"]
    },
    "uu_ite": {
        "name": "Undang-Undang Nomor 11 Tahun 2008 tentang Informasi dan Transaksi Elektronik",
        "number": "11", "year": "2008", "topic": "Informasi dan Transaksi Elektronik",
        "keywords": ["ite", "informasi elektronik", "transaksi elektronik"]
    },
    "uu_perlindungan_konsumen": {
        "name": "Undang-Undang Nomor 8 Tahun 1999 tentang Perlindungan Konsumen",
        "number": "8", "year": "1999", "topic": "Perlindungan Konsumen",
        "keywords": ["konsumen", "perlindungan konsumen"]
    },
    "uu_umkm": {
        "name": "Undang-Undang Nomor 20 Tahun 2008 tentang Usaha Mikro, Kecil, dan Menengah",
        "number": "20", "year": "2008", "topic": "Usaha Mikro, Kecil, dan Menengah",
        "keywords": ["umkm", "usaha mikro", "usaha kecil", "usaha menengah"]
    },
    # ... Tambahkan UU lainnya sesuai kebutuhan
}


# ─── Structure Parser ─────────────────────────────────────────
class UUStructureParser:
    # REVISI 1: Tambahkan \s* di awal untuk mentoleransi spasi hasil extract PDF
    RE_BAB = re.compile(r'^\s*(?:BAB)\s+([IVXLCDM]+|\d+)(?:\s*\n\s*(.+))?', re.IGNORECASE | re.MULTILINE)
    RE_BAGIAN = re.compile(r'^\s*Bagian\s+(Kesatu|Kedua|Ketiga|Keempat|Kelima|Keenam|Ketujuh|Kedelapan|Kesembilan|Kesepuluh|ke-\w+|\w+)(?:\s*\n\s*(.+))?', re.IGNORECASE | re.MULTILINE)
    RE_PARAGRAF = re.compile(r'^\s*Paragraf\s+(\d+)(?:\s*\n\s*(.+))?', re.IGNORECASE | re.MULTILINE)
    RE_PASAL_SPLIT = re.compile(r'^\s*(Pasal\s+\d+[A-Z]?)\s*$', re.IGNORECASE | re.MULTILINE)
    RE_AYAT = re.compile(r'^\s*\((?P<nomor>\d+)\)\s+(?P<teks>.+?)(?=^\s*\(\d+\)|^\s*Pasal\s|\Z)', re.MULTILINE | re.DOTALL)
    RE_HURUF = re.compile(r'^\s*([a-z])\.\s+(.+?)(?=^\s*[a-z]\.\s|\Z)', re.MULTILINE | re.DOTALL)

    def __init__(self, uu_slug: str):
        self.uu_slug = uu_slug
        self.uu_meta = UU_CATALOG.get(uu_slug, {
            "name": uu_slug, "number": "?", "year": "?", "topic": uu_slug
        })

    def truncate_penjelasan(self, full_text: str) -> str:
        """REVISI 2: Memotong bagian lampiran PENJELASAN agar tidak ikut ter-parse menjadi pasal."""
        penjelasan_match = re.search(r'\n\s*PENJELASAN\s+ATAS\s+', full_text, re.IGNORECASE)
        if penjelasan_match:
            logger.info("✂️  Memotong bagian Penjelasan di akhir dokumen.")
            return full_text[:penjelasan_match.start()]
        return full_text

    def split_into_pasal_blocks(self, full_text: str) -> list[dict]:
        pasal_blocks = []
        current_bab_num, current_bab_title = "", ""
        current_bagian, current_paragraf = "", ""

        # Gunakan regex yang sudah direlaksasi
        parts = self.RE_PASAL_SPLIT.split(full_text)
        
        pre_text = parts[0] if parts else ""
        current_bab_num, current_bab_title = self._extract_bab_from_text(pre_text, current_bab_num, current_bab_title)
        current_bagian = self._extract_bagian_from_text(pre_text, current_bagian)
        current_paragraf = self._extract_paragraf_from_text(pre_text, current_paragraf)

        for i in range(1, len(parts) - 1, 2):
            pasal_header = parts[i].strip()
            pasal_content = parts[i + 1] if i + 1 < len(parts) else ""

            pasal_num_match = re.search(r'Pasal\s+(\d+[A-Z]?)', pasal_header, re.IGNORECASE)
            if not pasal_num_match:
                continue
            pasal_number = pasal_num_match.group(1)

            current_bab_num, current_bab_title = self._extract_bab_from_text(pasal_content, current_bab_num, current_bab_title)
            current_bagian = self._extract_bagian_from_text(pasal_content, current_bagian)
            current_paragraf = self._extract_paragraf_from_text(pasal_content, current_paragraf)

            full_pasal_text = f"{pasal_header}\n{pasal_content}".strip()
            
            pasal_blocks.append({
                "pasal_number": pasal_number,
                "raw_text": full_pasal_text,
                "bab_number": current_bab_num,
                "bab_title": current_bab_title,
                "bagian": current_bagian,
                "paragraf": current_paragraf,
            })

        logger.info(f"  📑 Ditemukan {len(pasal_blocks)} pasal")
        return pasal_blocks

    def _extract_bab_from_text(self, text: str, current_num: str, current_title: str) -> tuple[str, str]:
        for match in self.RE_BAB.finditer(text):
            current_num = match.group(1)
            current_title = match.group(2).strip() if match.group(2) else ""
        return current_num, current_title

    def _extract_bagian_from_text(self, text: str, current: str) -> str:
        for match in self.RE_BAGIAN.finditer(text):
            ordinal = match.group(1)
            title = match.group(2).strip() if match.group(2) else ""
            current = f"Bagian {ordinal}" + (f" - {title}" if title else "")
        return current

    def _extract_paragraf_from_text(self, text: str, current: str) -> str:
        for match in self.RE_PARAGRAF.finditer(text):
            current = f"Paragraf {match.group(1)}"
        return current

    def parse_ayat(self, pasal_text: str) -> list[dict]:
        ayat_list = []
        ayat_matches = list(self.RE_AYAT.finditer(pasal_text))

        if ayat_matches:
            for match in ayat_matches:
                nomor = match.group('nomor')
                teks = match.group('teks').strip()

                huruf_list = []
                for hm in self.RE_HURUF.finditer(teks):
                    huruf_list.append({"huruf": hm.group(1), "teks": hm.group(2).strip()})

                ayat_list.append({"nomor": nomor, "teks": teks, "huruf": huruf_list})
        else:
            content_match = re.search(r'^\s*Pasal\s+\d+[A-Z]?\s*\n(.+)', pasal_text, re.DOTALL | re.IGNORECASE)
            if content_match:
                teks = content_match.group(1).strip()
                if teks:
                    ayat_list.append({"nomor": "1", "teks": teks, "huruf": []})

        return ayat_list

    def build_pasal_id(self, pasal_number: str) -> str:
        num = self.uu_meta.get("number", "?")
        year = self.uu_meta.get("year", "?")
        return f"uu_{num}_{year}_pasal_{pasal_number}"

    def parse_document(self, cleaned_json_path: str) -> UUDocument:
        logger.info(f"📖 Parsing struktur: {Path(cleaned_json_path).name}")

        with open(cleaned_json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        full_text_parts = []
        for page in doc.get("pages", []):
            text = page.get("cleaned_text", "").strip()
            if text:
                full_text_parts.append(text)

        full_text = "\n\n".join(full_text_parts)
        
        # Bersihkan bagian lampiran
        full_text = self.truncate_penjelasan(full_text)

        # REVISI 3: Selalu utamakan data dari UU_CATALOG
        uu_doc = UUDocument(
            uu_id=self.uu_slug,
            uu_name=self.uu_meta.get("name", self.uu_slug),
            uu_number=self.uu_meta.get("number", "?"),
            uu_year=self.uu_meta.get("year", "?"),
            uu_topic=self.uu_meta.get("topic", self.uu_slug),
            raw_text=full_text
        )

        pasal_blocks = self.split_into_pasal_blocks(full_text)
        uu_doc.total_pasal = len(pasal_blocks)

        for block in pasal_blocks:
            ayat_list = self.parse_ayat(block["raw_text"])

            pasal = Pasal(
                pasal_id=self.build_pasal_id(block["pasal_number"]),
                pasal_number=block["pasal_number"],
                full_text=block["raw_text"],
                ayat=[vars(a) if not isinstance(a, dict) else a for a in ayat_list],
                uu_name=uu_doc.uu_name,
                uu_number=uu_doc.uu_number,
                uu_year=uu_doc.uu_year,
                uu_topic=uu_doc.uu_topic,
                uu_slug=self.uu_slug,
                bab_number=block["bab_number"],
                bab_title=block["bab_title"],
                bagian=block["bagian"],
                paragraf=block["paragraf"],
            )
            uu_doc.pasal_list.append(pasal)

        bab_numbers = set(p.bab_number for p in uu_doc.pasal_list if p.bab_number)
        uu_doc.total_bab = len(bab_numbers)

        logger.info(f"  ✅ Parsed: {uu_doc.total_pasal} pasal, {uu_doc.total_bab} bab")
        return uu_doc


# ─── Output Functions ──────────────────────────────────────────
def save_parsed_document(uu_doc: UUDocument, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    full_path = output_dir / f"{uu_doc.uu_id}_parsed.json"
    doc_dict = {
        "uu_id": uu_doc.uu_id,
        "uu_name": uu_doc.uu_name,
        "uu_number": uu_doc.uu_number,
        "uu_year": uu_doc.uu_year,
        "uu_topic": uu_doc.uu_topic,
        "total_pasal": uu_doc.total_pasal,
        "total_bab": uu_doc.total_bab,
        "parsed_date": uu_doc.parsed_date,
        "pasal_list": [asdict(p) if isinstance(p, Pasal) else p for p in uu_doc.pasal_list]
    }
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(doc_dict, f, ensure_ascii=False, indent=2)

    pasal_only_path = output_dir / f"{uu_doc.uu_id}_pasal_list.json"
    pasal_list = []
    for p in uu_doc.pasal_list:
        p_dict = asdict(p) if isinstance(p, Pasal) else p
        p_clean = {k: v for k, v in p_dict.items() if k != "raw_text"}
        pasal_list.append(p_clean)

    with open(pasal_only_path, "w", encoding="utf-8") as f:
        json.dump(pasal_list, f, ensure_ascii=False, indent=2)

    stats_path = output_dir / f"{uu_doc.uu_id}_stats.json"
    stats = {
        "uu_id": uu_doc.uu_id,
        "uu_name": uu_doc.uu_name,
        "total_pasal": uu_doc.total_pasal,
        "total_bab": uu_doc.total_bab,
        "pasal_dengan_ayat": sum(1 for p in uu_doc.pasal_list if isinstance(p, Pasal) and len(p.ayat) > 1),
        "rata_rata_ayat": sum(len(p.ayat) for p in uu_doc.pasal_list if isinstance(p, Pasal)) / max(uu_doc.total_pasal, 1),
        "bab_list": list(set(p.bab_number for p in uu_doc.pasal_list if isinstance(p, Pasal) and p.bab_number)),
    }
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 Tersimpan: {full_path.name}, {pasal_only_path.name}, {stats_path.name}")


# ─── CLI ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="KlausulaAI - Structure Parser untuk Dokumen UU Indonesia")
    parser.add_argument("--input", "-i", required=True, help="Folder JSON cleaned (dari step 02) atau single file")
    parser.add_argument("--output", "-o", default="../04_chunked_data", help="Folder output parsed JSON")
    parser.add_argument("--slug", "-s", default="auto", help="UU slug dari catalog (contoh: uu_ketenagakerjaan). 'auto' = detect dari nama file")
    args = parser.parse_args()

    output_dir = Path(args.output)
    input_path = Path(args.input)

    if input_path.is_file():
        json_files = [input_path]
    else:
        json_files = list(input_path.glob("*_cleaned.json"))

    if not json_files:
        print(f"❌ Tidak ada file *_cleaned.json di: {input_path}")
        return

    print(f"\n📖 Parsing {len(json_files)} dokumen...")

    for json_file in json_files:
        slug = args.slug
        if slug == "auto":
            stem = json_file.stem.replace("_cleaned", "")
            for catalog_slug in UU_CATALOG.keys():
                if any(kw in stem.lower() for kw in UU_CATALOG[catalog_slug].get("keywords", [])):
                    slug = catalog_slug
                    break
            if slug == "auto":
                slug = stem

        logger.info(f"\nMemproses: {json_file.name} → slug: {slug}")
        struct_parser = UUStructureParser(uu_slug=slug)

        try:
            uu_doc = struct_parser.parse_document(str(json_file))
            save_parsed_document(uu_doc, output_dir)

            print(f"\n✅ {uu_doc.uu_name}")
            print(f"   Total Pasal: {uu_doc.total_pasal} | Total Bab: {uu_doc.total_bab}")

        except Exception as e:
            logger.error(f"❌ Gagal parsing {json_file.name}: {e}", exc_info=True)

    print(f"\n✅ Output tersimpan di: {output_dir}")

if __name__ == "__main__":
    main()