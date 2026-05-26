import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
import pdfplumber

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
logger = logging.getLogger("PDFExtractor")


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
    total_pages: int
    extracted_pages: int = 0
    failed_pages: list = field(default_factory=list)
    pages: list = field(default_factory=list)
    extraction_date: str = field(default_factory=lambda: datetime.now().isoformat())
    success_rate: float = 0.0
    total_chars: int = 0
    metadata: dict = field(default_factory=dict)

    def calculate_stats(self):
        self.extracted_pages = sum(1 for p in self.pages if not p.has_error)
        self.success_rate = (self.extracted_pages / self.total_pages * 100) if self.total_pages > 0 else 0
        self.total_chars = sum(p.char_count for p in self.pages)
        self.failed_pages = [p.page_num for p in self.pages if p.has_error]


def extract_pdf(pdf_path: str) -> DocumentResult:
    path = Path(pdf_path)
    logger.info(f"[pdfplumber] Memproses: {path.name}")

    result = DocumentResult(
        file_name=path.name,
        file_path=str(pdf_path),
        total_pages=0,
    )

    with pdfplumber.open(pdf_path) as pdf:
        result.total_pages = len(pdf.pages)
        result.metadata = {
            "pdf_info": pdf.metadata or {},
            "page_count": len(pdf.pages)
        }

        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            try:
                text = page.extract_text(
                    x_tolerance=3,
                    y_tolerance=3,
                    layout=True,
                ) or ""

                if not text.strip():
                    text = page.extract_text() or ""

                page_result = PageResult(
                    page_num=page_num,
                    text=text,
                    char_count=len(text),
                )
            except Exception as e:
                logger.warning(f"  Halaman {page_num} error: {e}")
                page_result = PageResult(
                    page_num=page_num,
                    text="",
                    char_count=0,
                    has_error=True,
                    error_msg=str(e)
                )

            result.pages.append(page_result)

            if page_num % 10 == 0:
                logger.info(f"  Progress: {page_num}/{result.total_pages} halaman")

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
    print(f"File          : {result.file_name}")
    print(f"Total Halaman : {result.total_pages}")
    print(f"Berhasil      : {result.extracted_pages} halaman ({result.success_rate:.1f}%)")
    print(f"Gagal         : {len(result.failed_pages)} halaman {result.failed_pages if result.failed_pages else ''}")
    print(f"Total Karakter: {result.total_chars:,}")

    print("\nPreview (Halaman 1-3):")
    for page in result.pages[:3]:
        preview = page.text[:200].replace('\n', ' ')
        print(f"  [Hal. {page.page_num}] {preview}...")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="KlausulaAI - PDF Extractor (pdfplumber)")
    parser.add_argument("--input", "-i", required=True, help="Path folder PDF atau single file PDF")
    parser.add_argument("--output", "-o", default="../02_extracted_text", help="Folder output JSON")
    parser.add_argument("--single", action="store_true", help="Proses single file")
    args = parser.parse_args()

    output_dir = Path(args.output)

    # Single file
    if args.single or Path(args.input).is_file():
        pdf_path = Path(args.input)
        if not pdf_path.exists():
            print(f"File tidak ditemukan: {pdf_path}")
            return
        result = extract_pdf(str(pdf_path))
        print_summary(result)
        save_result(result, output_dir)
        return

    # Batch folder
    input_dir = Path(args.input)
    pdf_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))

    if not pdf_files:
        print(f"Tidak ada file PDF di: {input_dir}")
        return

    print(f"\nDitemukan {len(pdf_files)} file PDF")
    all_results = []
    failed_files = []

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] {pdf_path.name}")
        try:
            result = extract_pdf(str(pdf_path))
            print_summary(result)
            save_result(result, output_dir)
            all_results.append(result)
        except Exception as e:
            logger.error(f"GAGAL: {pdf_path.name}: {e}")
            failed_files.append(pdf_path.name)

    # Batch summary
    print("\n" + "="*60)
    print("RINGKASAN BATCH")
    print(f"Total   : {len(pdf_files)}")
    print(f"Berhasil: {len(all_results)}")
    print(f"Gagal   : {len(failed_files)}")
    if failed_files:
        print(f"File gagal: {', '.join(failed_files)}")

    if all_results:
        avg_success = sum(r.success_rate for r in all_results) / len(all_results)
        total_chars = sum(r.total_chars for r in all_results)
        print(f"Avg success rate: {avg_success:.1f}%")
        print(f"Total karakter  : {total_chars:,}")

    summary = {
        "extraction_date": datetime.now().isoformat(),
        "total_files": len(pdf_files),
        "success_count": len(all_results),
        "failed_count": len(failed_files),
        "failed_files": failed_files,
        "documents": [
            {
                "file_name": r.file_name,
                "total_pages": r.total_pages,
                "success_rate": r.success_rate,
                "total_chars": r.total_chars,
            }
            for r in all_results
        ]
    }
    summary_path = output_dir / "extraction_summary.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSummary: {summary_path}")


if __name__ == "__main__":
    main()