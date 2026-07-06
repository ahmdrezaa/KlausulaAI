# scripts/intip_cleaned.py
import json
from pathlib import Path

CLEANED_DIR = Path("03_cleaned_text")

def intip(json_name, page_nums, n=800):
    path = CLEANED_DIR / json_name
    if not path.exists():
        print(f"❌ {path} tidak ada")
        return
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    pages = {p["page_num"]: p for p in doc["pages"]}
    for pn in page_nums:
        p = pages.get(pn, {})
        print(f"\n{'='*66}\nHAL {pn} | zone={p.get('effective_zone')} | "
              f"markers={p.get('position_markers')}")
        print("-"*66)
        print(p.get("cleaned_text", "")[:n])

# Permenkes 14 — Lampiran KBLI (teks bersih, patokan utama)
intip("permenkes_14_2021_standar_kesehatan_cleaned.json", [14, 200])

# PP 28 Lampiran L — tabel KBLI pariwisata
intip("pp28_2025_lampiran_L_pariwisata_cleaned.json", [1, 25])

# Satu UU naratif — patokan zona Pasal
intip("uu_8_1999_perlindungan_konsumen_cleaned.json", [3, 5])

# Satu kitab — patokan struktur Buku/Pasal
intip("kuhperdata_buku_3_perikatan_cleaned.json", [1, 10])