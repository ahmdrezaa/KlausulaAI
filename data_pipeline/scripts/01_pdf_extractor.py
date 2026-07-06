import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
import pdfplumber

# Bungkam warning kosmetik pdfminer (soal warna, bukan teks)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# python-docx menggantikan docx2txt agar tabel ikut terekstraksi
try:
    from docx import Document as DocxDocument
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DocumentExtractor")

# Ambang batas karakter non-spasi. Di bawah ini = halaman dicurigai scan/gambar/kosong.
NONSPACE_THRESHOLD = 50


@dataclass
class PageResult:
    page_num: int
    text: str
    char_count: int
    nonspace_count: int = 0            # karakter nyata (tanpa spasi/newline)
    method_used: str = "plain"         # 'plain' | 'layout' | 'none'
    has_error: bool = False
    error_msg: str = ""
    is_suspicious_empty: bool = False  # halaman minim konten (kemungkinan scan)
    is_lampiran: bool = False          # halaman terindikasi Lampiran
    has_table: bool = False            # halaman mengandung tabel terdeteksi


@dataclass
class DocumentResult:
    file_name: str
    file_path: str
    file_type: str
    total_pages: int
    extracted_pages: int = 0
    failed_pages: list = field(default_factory=list)
    suspicious_empty_pages: list = field(default_factory=list)
    lampiran_pages: list = field(default_factory=list)
    pages: list = field(default_factory=list)
    extraction_date: str = field(default_factory=lambda: datetime.now().isoformat())
    success_rate: float = 0.0
    total_chars: int = 0
    total_nonspace: int = 0
    metadata: dict = field(default_factory=dict)

    def calculate_stats(self):
        self.extracted_pages = sum(1 for p in self.pages if not p.has_error)
        self.success_rate = (self.extracted_pages / self.total_pages * 100) if self.total_pages > 0 else 0
        self.total_chars = sum(p.char_count for p in self.pages)
        self.total_nonspace = sum(p.nonspace_count for p in self.pages)
        self.failed_pages = [p.page_num for p in self.pages if p.has_error]
        self.suspicious_empty_pages = [p.page_num for p in self.pages if p.is_suspicious_empty]
        self.lampiran_pages = [p.page_num for p in self.pages if p.is_lampiran]


# Penanda awal bagian Lampiran pada dokumen hukum Indonesia.
# Termasuk varian dengan spasi antar-huruf akibat layout PDF ("L A M P I R A N").
LAMPIRAN_MARKERS = ("LAMPIRAN", "L A M P I R A N", "DAFTAR KBLI", "STANDAR DAN PERSYARATAN")


def _count_nonspace(text: str) -> int:
    """Hitung karakter nyata, buang spasi/newline/tab."""
    return len(text.replace(" ", "").replace("\n", "").replace("\t", ""))


def _detect_lampiran(text: str) -> bool:
    """Deteksi apakah halaman kemungkinan bagian Lampiran (zona tabel/daftar)."""
    head = text[:600].upper()
    return any(marker in head for marker in LAMPIRAN_MARKERS)


def extract_pdf(file_path: str, result: DocumentResult):
    """
    Ekstraksi PDF per halaman.
    Strategi: extract_text() polos sebagai UTAMA (teks terbersih untuk RAG),
    layout=True hanya sebagai FALLBACK jika polos menghasilkan teks minim.
    """
    with pdfplumber.open(file_path) as pdf:
        result.total_pages = len(pdf.pages)
        result.metadata["pdf_info"] = pdf.metadata or {}

        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            try:
                # METODE UTAMA: extract_text() polos
                plain = page.extract_text() or ""
                plain_ns = _count_nonspace(plain)

                text = plain
                nonspace = plain_ns
                method = "plain"

                # FALLBACK: kalau polos minim konten, coba layout=True
                if plain_ns < NONSPACE_THRESHOLD:
                    layout = page.extract_text(
                        x_tolerance=3, y_tolerance=3, layout=True
                    ) or ""
                    layout_ns = _count_nonspace(layout)
                    # pakai layout hanya kalau benar-benar lebih berisi
                    if layout_ns > plain_ns:
                        text = layout
                        nonspace = layout_ns
                        method = "layout"

                # Deteksi tabel (best-effort; tidak selalu akurat, hanya sinyal)
                try:
                    has_table = len(page.find_tables()) > 0
                except Exception:
                    has_table = False

                pr = PageResult(
                    page_num=page_num,
                    text=text,
                    char_count=len(text),
                    nonspace_count=nonspace,
                    method_used=method if nonspace > 0 else "none",
                    is_lampiran=_detect_lampiran(text),
                    has_table=has_table,
                )

                # Deteksi halaman palsu-berisi / scan / kosong
                if nonspace < NONSPACE_THRESHOLD:
                    pr.is_suspicious_empty = True
                    logger.warning(
                        f"  ⚠️  Halaman {page_num} minim konten "
                        f"({nonspace} char nyata). Kemungkinan scan/gambar/kosong."
                    )

                result.pages.append(pr)

            except Exception as e:
                logger.warning(f"  Halaman {page_num} error: {e}")
                result.pages.append(PageResult(
                    page_num=page_num, text="", char_count=0,
                    has_error=True, error_msg=str(e), method_used="none"
                ))

            if page_num % 50 == 0:
                logger.info(f"  Progress: {page_num}/{result.total_pages} halaman")


def extract_docx(file_path: str, result: DocumentResult):
    """
    Ekstraksi DOCX dengan python-docx (paragraf DAN tabel).
    Isi tabel dirender pipe-separated agar relasi antar-sel terjaga.
    """
    if not HAS_PYTHON_DOCX:
        raise RuntimeError("python-docx belum terpasang. Jalankan: pip install python-docx")

    doc = DocxDocument(file_path)
    parts = []
    table_count = 0

    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.split('}')[-1]

        if tag == 'p':
            para_text = ''.join(
                node.text or '' for node in child.iter() if node.tag.endswith('}t')
            )
            if para_text.strip():
                parts.append(para_text)

        elif tag == 'tbl':
            table_count += 1
            parts.append(f"[TABEL {table_count}]")
            for row in child.iter():
                if row.tag.endswith('}tr'):
                    cells = [
                        ''.join(n.text or '' for n in cell.iter() if n.tag.endswith('}t'))
                        for cell in row.iter() if cell.tag.endswith('}tc')
                    ]
                    if any(c.strip() for c in cells):
                        parts.append(" | ".join(c.strip() for c in cells))

    text = "\n".join(parts)
    nonspace = _count_nonspace(text)

    result.total_pages = 1
    result.pages.append(PageResult(
        page_num=1,
        text=text,
        char_count=len(text),
        nonspace_count=nonspace,
        method_used="docx",
        is_lampiran=_detect_lampiran(text),
        has_table=table_count > 0,
        is_suspicious_empty=nonspace < NONSPACE_THRESHOLD,
    ))

    if table_count > 0:
        logger.info(f"  {table_count} tabel diekstraksi dari DOCX")
    if nonspace < NONSPACE_THRESHOLD:
        logger.warning("  ⚠️  DOCX minim konten setelah ekstraksi.")


def extract_document(file_path: str, doc_type_meta: str, status_meta: str,
                     project_id_meta: str, superseded_by_meta: str = None) -> DocumentResult:
    path = Path(file_path)
    file_ext = path.suffix.lower()
    logger.info(f"Memproses: {path.name} ({file_ext})")

    result = DocumentResult(
        file_name=path.name,
        file_path=str(file_path),
        file_type=file_ext.replace('.', ''),
        total_pages=0,
    )

    # Injeksi metadata standar KlausulaAI (terbawa ke step berikutnya)
    result.metadata = {
        "doc_type": doc_type_meta,
        "status": status_meta,
        "superseded_by": superseded_by_meta if superseded_by_meta else None,
        "project_id": project_id_meta if project_id_meta else None,
        "is_global": doc_type_meta == 'global_uu',
    }

    if file_ext == '.pdf':
        extract_pdf(file_path, result)
    elif file_ext == '.docx':
        extract_docx(file_path, result)
    else:
        raise ValueError(f"Format {file_ext} tidak didukung.")

    result.calculate_stats()
    return result


def save_result(result: DocumentResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.file_name).stem
    output_path = output_dir / f"{stem}_extracted.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, ensure_ascii=False, indent=2)

    logger.info(f"Tersimpan: {output_path}")
    return output_path


def print_summary(result: DocumentResult):
    print("\n" + "=" * 60)
    print(f"File          : {result.file_name} ({result.file_type.upper()})")
    print(f"Tipe Metadata : {result.metadata['doc_type']} | Status: {result.metadata['status']}")
    print(f"Total Halaman : {result.total_pages}")
    print(f"Berhasil      : {result.extracted_pages} halaman ({result.success_rate:.1f}%)")
    print(f"Total Karakter: {result.total_chars:,} (non-spasi: {result.total_nonspace:,})")
    if result.suspicious_empty_pages:
        n = len(result.suspicious_empty_pages)
        preview = result.suspicious_empty_pages[:15]
        print(f"⚠️  Halaman minim : {n} halaman {preview}{'...' if n > 15 else ''}  <-- PERIKSA")
    if result.lampiran_pages:
        print(f"📎 Halaman Lampiran: {result.lampiran_pages[:15]}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="KlausulaAI - Document Extractor (PDF & DOCX)")
    parser.add_argument("--input", "-i", required=True, help="Path folder dokumen atau single file")
    parser.add_argument("--output", "-o", default="../02_extracted_text", help="Folder output JSON")
    parser.add_argument("--single", action="store_true", help="Proses single file")
    parser.add_argument("--doctype", default="global_uu", choices=["global_uu", "user_doc"])
    parser.add_argument("--status", default="active", help="Status dokumen regulasi")
    parser.add_argument("--projectid", default="", help="UUID project_id jika user_doc")
    parser.add_argument("--supersededby", default="", help="ID dokumen pengganti (untuk aturan dicabut)")

    args = parser.parse_args()
    output_dir = Path(args.output)

    if args.single or Path(args.input).is_file():
        file_path = Path(args.input)
        if not file_path.exists():
            print(f"File tidak ditemukan: {file_path}")
            return
        result = extract_document(str(file_path), args.doctype, args.status,
                                  args.projectid, args.supersededby)
        print_summary(result)
        save_result(result, output_dir)
        return

    input_dir = Path(args.input)
    files = []
    for ext in ["*.pdf", "*.PDF", "*.docx", "*.DOCX"]:
        files.extend(list(input_dir.glob(ext)))
    files = sorted(set(files))

    if not files:
        print(f"Tidak ada file PDF/DOCX di: {input_dir}")
        return

    print(f"\nDitemukan {len(files)} file")
    all_results, failed_files = [], []

    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file_path.name}")
        try:
            result = extract_document(str(file_path), args.doctype, args.status,
                                      args.projectid, args.supersededby)
            print_summary(result)
            save_result(result, output_dir)
            all_results.append(result)
        except Exception as e:
            logger.error(f"GAGAL: {file_path.name}: {e}")
            failed_files.append(file_path.name)

    # Ringkasan batch
    total_empty = sum(len(r.suspicious_empty_pages) for r in all_results)
    print("\n" + "=" * 60)
    print(f"BATCH SUMMARY: {len(all_results)} Berhasil | {len(failed_files)} Gagal")
    if total_empty:
        print(f"⚠️  Total {total_empty} halaman minim konten di seluruh batch. Periksa log.")
    if failed_files:
        print(f"File gagal: {', '.join(failed_files)}")
    print("=" * 60)


if __name__ == "__main__":
    main()