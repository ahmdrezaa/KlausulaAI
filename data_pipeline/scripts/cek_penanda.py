# scripts/cek_penanda.py
"""
Cek cepat is_lampiran & has_table di semua file _extracted.json.
Berguna untuk verifikasi sebelum lanjut ke cleaning/parsing.

Pakai:
    python scripts/cek_penanda.py --input 02_extracted_text/
"""
import json
import argparse
from pathlib import Path


def cek_dokumen(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    pages = doc.get("pages", [])
    total = len(pages)

    lampiran_pages = [p["page_num"] for p in pages if p.get("is_lampiran")]
    table_pages = [p["page_num"] for p in pages if p.get("has_table")]
    empty_pages = [p["page_num"] for p in pages if p.get("is_suspicious_empty")]

    print(f"\n{'='*60}")
    print(f"📄 {json_path.name}")
    print(f"   Total halaman     : {total}")
    print(f"   Terdeteksi Lampiran: {len(lampiran_pages)} halaman "
          f"{lampiran_pages[:10]}{'...' if len(lampiran_pages) > 10 else ''}")
    print(f"   Mengandung tabel   : {len(table_pages)} halaman "
          f"{table_pages[:10]}{'...' if len(table_pages) > 10 else ''}")

    if empty_pages:
        print(f"   ⚠️  Halaman kosong  : {empty_pages}  <-- PERIKSA")

    # Diagnosa: di mana zona Pasal berakhir & Lampiran dimulai?
    if lampiran_pages:
        awal_lampiran = min(lampiran_pages)
        print(f"   → Zona Pasal   : halaman 1–{awal_lampiran - 1}")
        print(f"   → Zona Lampiran: halaman {awal_lampiran}–{total}")
    else:
        print(f"   → Tidak ada Lampiran terdeteksi (seluruhnya zona Pasal?)")

    # Peringatan ketidakcocokan: ada tabel tapi tak tertandai Lampiran
    tabel_non_lampiran = [p for p in table_pages if p not in lampiran_pages]
    if tabel_non_lampiran:
        print(f"   ℹ️  Tabel di luar zona Lampiran: {tabel_non_lampiran[:10]} "
              f"(mungkin tabel dalam Pasal, atau penanda Lampiran terlewat)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True)
    args = ap.parse_args()

    input_path = Path(args.input)
    files = ([input_path] if input_path.is_file()
             else sorted(input_path.glob("*_extracted.json")))

    if not files:
        print(f"Tidak ada file _extracted.json di {input_path}")
        return

    for f in files:
        cek_dokumen(f)

    print(f"\n{'='*60}\nSelesai memeriksa {len(files)} dokumen.")


if __name__ == "__main__":
    main()