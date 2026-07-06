# scripts/cek_duplikasi_pasal.py
import json
from pathlib import Path
from collections import Counter

path = Path("04_parsed/uu_13_2003_ketenagakerjaan_parsed.json")
with open(path, encoding="utf-8") as f:
    doc = json.load(f)

units = [u for u in doc["units"] if u["unit_type"] == "pasal"]
print(f"Total unit pasal: {len(units)}\n")

# Hitung berapa kali tiap nomor pasal muncul
counter = Counter(u["pasal_number"] for u in units)
duplikat = {k: v for k, v in counter.items() if v > 1}
print(f"Nomor pasal yang muncul >1 kali: {len(duplikat)}")
print(f"Contoh: {dict(list(duplikat.items())[:10])}\n")

# Lihat DUA kemunculan 'Pasal 1' — bandingkan isinya
print("=== Kemunculan 'Pasal 1' ===")
pasal1 = [u for u in units if u["pasal_number"] == "1"]
for i, u in enumerate(pasal1, 1):
    print(f"\n--- Kemunculan #{i} | bab={u.get('bab')} | hal={u.get('source_pages')} ---")
    print(u["content"][:300])

# Lihat di posisi mana transisi Batang Tubuh → Penjelasan terjadi
# (biasanya ada lonjakan: pasal naik terus lalu reset ke 1)
print("\n=== Urutan nomor pasal (deteksi titik reset) ===")
nums = [u.get("pasal_int") for u in units if u.get("pasal_int")]
for i in range(1, len(nums)):
    if nums[i] < nums[i-1] - 5:  # turun drastis = mulai bagian baru
        print(f"  Reset di index {i}: pasal {nums[i-1]} → {nums[i]}")