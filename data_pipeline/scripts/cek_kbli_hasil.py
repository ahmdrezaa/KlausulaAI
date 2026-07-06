# scripts/cek_kbli_hasil.py
import json
from pathlib import Path

with open("04_parsed/KBLI_2020_parsed.json", encoding="utf-8") as f:
    doc = json.load(f)

units = doc["units"]
codes = sorted(u["kbli_code"] for u in units)

# Kelompokkan per prefix 2-digit
from collections import Counter
prefix_count = Counter(c[:2] for c in codes)
print("Distribusi per prefix 2-digit:")
for pref, n in sorted(prefix_count.items()):
    print(f"  {pref}xxx : {n} kode")

print(f"\nTotal: {len(codes)} kode\n")

# Tampilkan kode sektor 56 (makan-minum) — inti F&B
print("=== Kode 56xxx (penyediaan makan-minum) ===")
for u in units:
    if u["kbli_code"].startswith("56"):
        nama = u["content"][:80].replace("\n", " ")
        print(f"  {u['kbli_code']}: {nama}")

# Contoh satu entri lengkap untuk cek kualitas teks
print("\n=== Contoh entri lengkap (56101) ===")
for u in units:
    if u["kbli_code"] == "56101":
        print(u["content"][:600])
        break