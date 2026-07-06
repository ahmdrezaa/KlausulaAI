# scripts/intip_kbli.py
import json
from pathlib import Path

path = Path("03_cleaned_text/KBLI_2020_cleaned.json")
with open(path, encoding="utf-8") as f:
    doc = json.load(f)

pages = {p["page_num"]: p for p in doc["pages"]}

# Ambil beberapa halaman yang kemungkinan berisi entri KBLI sektor makanan (56xxx)
# dan satu halaman awal untuk lihat pola umum
for pn in [15, 40, 300]:
    p = pages.get(pn, {})
    print(f"\n{'='*66}\nHAL {pn} | zone={p.get('effective_zone')} | "
          f"tabel={p.get('has_table')}")
    print("-"*66)
    print(p.get("cleaned_text", "")[:900])