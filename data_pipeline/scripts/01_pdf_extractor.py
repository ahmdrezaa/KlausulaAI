import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
import pdfplumber
import docx2txt

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DocumentExtractor")

@dataclass
class PageResult:
    page_num: int
    text: str
    char_count: int
    has_error: bool = False
    error_msg: str = ""

@dataclass
class DocumentResult:
    file_name: str
    file_path: str
    file_type: str # 'pdf' atau 'docx'
    total_pages: int
    extracted_pages: int = 0
    failed_pages: list = field(default_factory=list)
    pages: list = field(default_factory=list)
    extraction_date: str = field(default_factory=lambda: datetime.now().isoformat())
    success_rate: float = 0.0
    total_chars: int = 0
    metadata: dict = field(default_factory=dict) # Metadata krusial untuk Supabase

    def calculate_stats(self):
        self.extracted_pages = sum(1 for p in self.pages if not p.has_error)
        self.success_rate = (self.extracted_pages / self.total_pages * 100) if self.total_pages > 0 else 0
        self.total_chars = sum(p.char_count for p in self.pages)
        self.failed_pages = [p.page_num for p in self.pages if p.has_error]

def extract_document(file_path: str, doc_type_meta: str, status_meta: str, project_id_meta: str) -> DocumentResult:
    path = Path(file_path)
    file_ext = path.suffix.lower()
    logger.info(f"Memproses: {path.name} ({file_ext})")

    result = DocumentResult(
        file_name=path.name,
        file_path=str(file_path),
        file_type=file_ext.replace('.', ''),
        total_pages=0,
    )

    # Injeksi Metadata Standar KlausulaAI
    result.metadata = {
        "doc_type": doc_type_meta,
        "status": status_meta,
        "superseded_by": None,
        "project_id": project_id_meta if project_id_meta else None,
        "is_global": doc_type_meta == 'global_uu'
    }

    if file_ext == '.pdf':
        with pdfplumber.open(file_path) as pdf:
            result.total_pages = len(pdf.pages)
            result.metadata["pdf_info"] = pdf.metadata or {}
            
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                try:
                    text = page.extract_text(x_tolerance=3, y_tolerance=3, layout=True) or ""
                    if not text.strip():
                        text = page.extract_text() or ""

                    result.pages.append(PageResult(page_num=page_num, text=text, char_count=len(text)))
                except Exception as e:
                    logger.warning(f"  Halaman {page_num} error: {e}")
                    result.pages.append(PageResult(page_num=page_num, text="", char_count=0, has_error=True, error_msg=str(e)))

                if page_num % 10 == 0:
                    logger.info(f"  Progress: {page_num}/{result.total_pages} halaman")

    elif file_ext == '.docx':
        try:
            # docx2txt tidak memiliki konsep "halaman", jadi kita anggap seluruh teks adalah 1 halaman
            text = docx2txt.process(file_path)
            result.total_pages = 1
            result.pages.append(PageResult(page_num=1, text=text, char_count=len(text)))
        except Exception as e:
            logger.warning(f"  Gagal mengekstrak DOCX: {e}")
            result.total_pages = 1
            result.pages.append(PageResult(page_num=1, text="", char_count=0, has_error=True, error_msg=str(e)))
    else:
        raise ValueError(f"Format {file_ext} tidak didukung.")

    result.calculate_stats()
    return result

def save_result(result: DocumentResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.file_name).stem
    output_path = output_dir / f"{stem}_extracted.json"

    data = asdict(result)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Tersimpan: {output_path}")
    return output_path

def print_summary(result: DocumentResult):
    print("\n" + "="*60)
    print(f"File          : {result.file_name} ({result.file_type.upper()})")
    print(f"Tipe Metadata : {result.metadata['doc_type']} | Status: {result.metadata['status']}")
    print(f"Total Halaman : {result.total_pages}")
    print(f"Berhasil      : {result.extracted_pages} halaman ({result.success_rate:.1f}%)")
    print(f"Total Karakter: {result.total_chars:,}")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="KlausulaAI - Document Extractor (PDF & DOCX)")
    parser.add_argument("--input", "-i", required=True, help="Path folder dokumen atau single file")
    parser.add_argument("--output", "-o", default="../02_extracted_text", help="Folder output JSON")
    parser.add_argument("--single", action="store_true", help="Proses single file")
    
    # Argumen baru untuk metadata Supabase
    parser.add_argument("--doctype", default="global_uu", choices=["global_uu", "user_doc"], help="Jenis dokumen untuk database")
    parser.add_argument("--status", default="active", help="Status dokumen regulasi")
    parser.add_argument("--projectid", default="", help="UUID project_id jika ini adalah user_doc")
    
    args = parser.parse_args()
    output_dir = Path(args.output)

    if args.single or Path(args.input).is_file():
        file_path = Path(args.input)
        if not file_path.exists():
            print(f"File tidak ditemukan: {file_path}")
            return
        result = extract_document(str(file_path), args.doctype, args.status, args.projectid)
        print_summary(result)
        save_result(result, output_dir)
        return

    input_dir = Path(args.input)
    # Mencari PDF dan DOCX
    files = []
    for ext in ["*.pdf", "*.PDF", "*.docx", "*.DOCX"]:
        files.extend(list(input_dir.glob(ext)))

    if not files:
        print(f"Tidak ada file PDF/DOCX di: {input_dir}")
        return

    print(f"\nDitemukan {len(files)} file")
    all_results, failed_files = [], []

    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file_path.name}")
        try:
            result = extract_document(str(file_path), args.doctype, args.status, args.projectid)
            save_result(result, output_dir)
            all_results.append(result)
        except Exception as e:
            logger.error(f"GAGAL: {file_path.name}: {e}")
            failed_files.append(file_path.name)

    print("\n" + "="*60 + f"\nBATCH SUMMARY: {len(all_results)} Berhasil | {len(failed_files)} Gagal")

if __name__ == "__main__":
    main()