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
    buku_number: str = "" # Tambahan untuk KUHPerdata/KUHD
    buku_title: str = ""
    bab_number: str = ""
    bab_title: str = ""
    bagian: str = ""
    paragraf: str = ""
    parsed_date: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Field Metadata Tagging & Database
    tags: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict) # Untuk menyimpan doc_type, status, dll

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
    metadata: dict = field(default_factory=dict) # Mewarisi dari step sebelumnya


# ─── F&B Legal Catalog (Lapisan 1 & 2) ────────────────────────
UU_CATALOG = {
    # TAHAP 1 & 3: Badan Usaha & Kontrak
    "uu_40_2007_perseroan_terbatas": {
        "name": "Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas",
        "number": "40", "year": "2007", "type": "UU", "topic": "Badan Usaha PT",
        "keywords": ["perseroan terbatas", "uu_40"]
    },
    "kuhd": {
        "name": "Kitab Undang-Undang Hukum Dagang (KUHD)",
        "number": "-", "year": "-", "type": "KUH", "topic": "Hukum Dagang & CV",
        "keywords": ["kuhd", "dagang"]
    },
    "kuhperdata_buku_3_perikatan": {
        "name": "Kitab Undang-Undang Hukum Perdata (Buku III tentang Perikatan)",
        "number": "-", "year": "-", "type": "KUH", "topic": "Kontrak & Perjanjian",
        "keywords": ["kuhperdata", "perikatan"]
    },
    "uu_11_2020_cipta_kerja": {
        "name": "Undang-Undang Nomor 11 Tahun 2020 tentang Cipta Kerja",
        "number": "11", "year": "2020", "type": "UU", "topic": "Cipta Kerja & PT Perorangan",
        "keywords": ["cipta kerja", "uu_11"]
    },
    
    # TAHAP 1: Perizinan & Operasional
    "pp_5_2021_perizinan_berbasis_risiko": {
        "name": "Peraturan Pemerintah Nomor 5 Tahun 2021 tentang Penyelenggaraan Perizinan Berusaha Berbasis Risiko",
        "number": "5", "year": "2021", "type": "PP", "topic": "OSS & Perizinan",
        "keywords": ["perizinan", "oss", "pp_5"]
    },
    "permenkes_1096_2011_higiene_sanitasi": {
        "name": "Peraturan Menteri Kesehatan Nomor 1096 Tahun 2011 tentang Higiene Sanitasi Jasaboga",
        "number": "1096", "year": "2011", "type": "Permenkes", "topic": "Higiene Sanitasi",
        "keywords": ["higiene", "sanitasi", "permenkes"]
    },
    "uu_33_2014_jaminan_produk_halal": {
        "name": "Undang-Undang Nomor 33 Tahun 2014 tentang Jaminan Produk Halal",
        "number": "33", "year": "2014", "type": "UU", "topic": "Sertifikasi Halal",
        "keywords": ["halal", "uu_33"]
    },
    "pp_39_2021_jaminan_produk_halal": {
        "name": "Peraturan Pemerintah Nomor 39 Tahun 2021 tentang Penyelenggaraan Bidang Jaminan Produk Halal",
        "number": "39", "year": "2021", "type": "PP", "topic": "Pelaksanaan Halal",
        "keywords": ["pp_39", "produk halal"]
    },

    # TAHAP 2: Melindungi
    "uu_20_2016_merek_indikasi_geografis": {
        "name": "Undang-Undang Nomor 20 Tahun 2016 tentang Merek dan Indikasi Geografis",
        "number": "20", "year": "2016", "type": "UU", "topic": "HKI & Merek",
        "keywords": ["merek", "indikasi geografis", "uu_20"]
    },

    # TAHAP 3: Menjalankan
    "uu_13_2003_ketenagakerjaan": {
        "name": "Undang-Undang Nomor 13 Tahun 2003 tentang Ketenagakerjaan",
        "number": "13", "year": "2003", "type": "UU", "topic": "Ketenagakerjaan",
        "keywords": ["ketenagakerjaan", "uu_13"]
    },
    "uu_8_1999_perlindungan_konsumen": {
        "name": "Undang-Undang Nomor 8 Tahun 1999 tentang Perlindungan Konsumen",
        "number": "8", "year": "1999", "type": "UU", "topic": "Perlindungan Konsumen",
        "keywords": ["perlindungan konsumen", "konsumen", "uu_8"]
    },
}

# ─── Structure Parser ─────────────────────────────────────────
class UUStructureParser:
    RE_BUKU = re.compile(r'^\s*(?:Buku)\s+([IVXLCDM]+|\d+)(?:\s*\n\s*(.+))?', re.IGNORECASE | re.MULTILINE)
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
        penjelasan_match = re.search(r'\n\s*PENJELASAN\s+ATAS\s+', full_text, re.IGNORECASE)
        if penjelasan_match:
            logger.info("[TRUNCATE] Memotong bagian Penjelasan di akhir dokumen.")
            return full_text[:penjelasan_match.start()]
        return full_text

    def split_into_pasal_blocks(self, full_text: str) -> list[dict]:
        pasal_blocks = []
        current_buku_num, current_buku_title = "", ""
        current_bab_num, current_bab_title = "", ""
        current_bagian, current_paragraf = "", ""

        parts = self.RE_PASAL_SPLIT.split(full_text)
        
        pre_text = parts[0] if parts else ""
        current_buku_num, current_buku_title = self._extract_buku_from_text(pre_text, current_buku_num, current_buku_title)
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

            current_buku_num, current_buku_title = self._extract_buku_from_text(pasal_content, current_buku_num, current_buku_title)
            current_bab_num, current_bab_title = self._extract_bab_from_text(pasal_content, current_bab_num, current_bab_title)
            current_bagian = self._extract_bagian_from_text(pasal_content, current_bagian)
            current_paragraf = self._extract_paragraf_from_text(pasal_content, current_paragraf)

            full_pasal_text = f"{pasal_header}\n{pasal_content}".strip()
            
            pasal_blocks.append({
                "pasal_number": pasal_number,
                "raw_text": full_pasal_text,
                "buku_number": current_buku_num,
                "buku_title": current_buku_title,
                "bab_number": current_bab_num,
                "bab_title": current_bab_title,
                "bagian": current_bagian,
                "paragraf": current_paragraf,
            })

        return pasal_blocks

    def _extract_buku_from_text(self, text: str, current_num: str, current_title: str) -> tuple[str, str]:
        for match in self.RE_BUKU.finditer(text):
            current_num = match.group(1)
            current_title = match.group(2).strip() if match.group(2) else ""
        return current_num, current_title

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
        return f"{self.uu_slug}_pasal_{pasal_number}"

    def generate_tags(self, text: str) -> list:
        """ F&B Specific Smart Tagging berdasarkan KlausulaAI v2 """
        text_lower = text.lower()
        tags = set()
        
        # Tahap 1: Mendirikan
        if any(kw in text_lower for kw in ["perseroan", "saham", "direksi", "modal dasar", "cv", "firma"]):
            tags.add("badan_usaha")
        if any(kw in text_lower for kw in ["izin", "oss", "nib", "perizinan", "kbli"]):
            tags.add("perizinan")
            
        # Tahap 2: Melindungi
        if any(kw in text_lower for kw in ["merek", "logo", "indikasi geografis", "hak cipta"]):
            tags.add("hki_merek")
            
        # Tahap 3: Menjalankan (Kontrak & Operasional F&B)
        if any(kw in text_lower for kw in ["sewa", "perjanjian", "wanprestasi", "ganti rugi", "batal", "pekerja", "pkwt"]):
            tags.add("kontrak")
        if any(kw in text_lower for kw in ["halal", "sanitasi", "higiene", "konsumen", "keracunan", "makanan", "minuman", "restoran"]):
            tags.add("fnb_operasional")
            
        return list(tags)

    def parse_document(self, cleaned_json_path: str) -> UUDocument:
        logger.info(f"[PROCESS] Parsing struktur: {Path(cleaned_json_path).name}")

        with open(cleaned_json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        # Mengambil metadata database dari step sebelumnya
        db_metadata = doc.get("metadata", {})

        full_text_parts = []
        for page in doc.get("pages", []):
            text = page.get("cleaned_text", "").strip()
            if text:
                full_text_parts.append(text)

        full_text = "\n\n".join(full_text_parts)
        full_text = self.truncate_penjelasan(full_text)

        uu_doc = UUDocument(
            uu_id=self.uu_slug,
            uu_name=self.uu_meta.get("name", self.uu_slug),
            uu_number=self.uu_meta.get("number", "?"),
            uu_year=self.uu_meta.get("year", "?"),
            uu_topic=self.uu_meta.get("topic", self.uu_slug),
            raw_text=full_text,
            metadata=db_metadata
        )

        pasal_blocks = self.split_into_pasal_blocks(full_text)
        uu_doc.total_pasal = len(pasal_blocks)

        for block in pasal_blocks:
            ayat_list = self.parse_ayat(block["raw_text"])
            tags_list = self.generate_tags(block["raw_text"])

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
                buku_number=block["buku_number"],
                buku_title=block["buku_title"],
                bab_number=block["bab_number"],
                bab_title=block["bab_title"],
                bagian=block["bagian"],
                paragraf=block["paragraf"],
                tags=tags_list,
                metadata=db_metadata # Penting untuk diturunkan ke level pasal/chunk
            )
            uu_doc.pasal_list.append(pasal)

        bab_numbers = set(p.bab_number for p in uu_doc.pasal_list if p.bab_number)
        uu_doc.total_bab = len(bab_numbers)

        logger.info(f"  [SUCCESS] Parsed: {uu_doc.total_pasal} pasal, {uu_doc.total_bab} bab")
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
        "metadata": uu_doc.metadata, # Simpan metadata DB di level dokumen
        "pasal_list": [asdict(p) if isinstance(p, Pasal) else p for p in uu_doc.pasal_list]
    }
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(doc_dict, f, ensure_ascii=False, indent=2)

    # File ini yang biasanya dikonsumsi oleh script Ingestion
    pasal_only_path = output_dir / f"{uu_doc.uu_id}_pasal_list.json"
    pasal_list = []
    for p in uu_doc.pasal_list:
        p_dict = asdict(p) if isinstance(p, Pasal) else p
        p_clean = {k: v for k, v in p_dict.items() if k != "raw_text"}
        pasal_list.append(p_clean)

    with open(pasal_only_path, "w", encoding="utf-8") as f:
        json.dump(pasal_list, f, ensure_ascii=False, indent=2)

    logger.info(f"[SAVED] Tersimpan di: {output_dir.name}")


# ─── CLI ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="KlausulaAI - Structure Parser untuk F&B Legal DB")
    parser.add_argument("--input", "-i", required=True, help="Folder JSON cleaned (dari step 02) atau single file")
    parser.add_argument("--output", "-o", default="../04_chunked_data", help="Folder output parsed JSON")
    args = parser.parse_args()

    output_dir = Path(args.output)
    input_path = Path(args.input)

    if input_path.is_file():
        json_files = [input_path]
    else:
        json_files = list(input_path.glob("*_cleaned.json"))

    if not json_files:
        print(f"[ERROR] Tidak ada file *_cleaned.json di: {input_path}")
        return

    print(f"\n[START] Parsing {len(json_files)} dokumen hukum...")

    for json_file in json_files:
        slug = "auto"
        stem = json_file.stem.replace("_cleaned", "")
        
        # Pengecekan cerdas berbasis nama file
        for catalog_slug in UU_CATALOG.keys():
            if any(kw in stem.lower() for kw in UU_CATALOG[catalog_slug].get("keywords", [])):
                slug = catalog_slug
                break
                
        if slug == "auto":
            slug = stem # Fallback jika tidak ada di katalog

        logger.info(f"\n[PROCESS] Memproses: {json_file.name} -> slug: {slug}")
        struct_parser = UUStructureParser(uu_slug=slug)

        try:
            uu_doc = struct_parser.parse_document(str(json_file))
            save_parsed_document(uu_doc, output_dir)
            print(f"[SUCCESS] {uu_doc.uu_name} ({uu_doc.total_pasal} Pasal)")

        except Exception as e:
            logger.error(f"[ERROR] Gagal parsing {json_file.name}: {e}", exc_info=True)

    print(f"\n[DONE] Selesai. Lanjutkan ke script Ingestion.")

if __name__ == "__main__":
    main()