# scripts/cek_pp28.py
import json
from pathlib import Path

path = Path("03_cleaned_text/pp_28_2025_perizinan_berbasis_risiko_cleaned.json")
with open(path, encoding="utf-8") as f:
    doc = json.load(f)

pages = doc["pages"]

# 1. Peta zona per halaman + apakah ada penanda Pasal di tiap halaman
print("=== Peta zona 15 halaman pertama ===")
for p in pages[:15]:
    txt = p.get("cleaned_text", "")
    ada_pasal = "Pasal" in txt
    is_lamp = p.get("is_lampiran")
    zone = p.get("effective_zone")
    # cari kata pertama yang memicu deteksi lampiran
    lampiran_kata = "LAMPIRAN" in txt[:600].upper()
    print(f"Hal {p['page_num']:3} | zona={zone:9} | is_lampiran={str(is_lamp):5} | "
          f"ada 'Pasal'={str(ada_pasal):5} | ada 'LAMPIRAN'={lampiran_kata}")

# 2. Di halaman mana carry-forward mulai (is_lampiran pertama = true)
first_lamp = next((p["page_num"] for p in pages if p.get("is_lampiran")), None)
print(f"\n→ is_lampiran pertama TRUE di halaman: {first_lamp}")

# 3. Intip isi halaman pemicu itu — apa benar Lampiran, atau batang tubuh?
if first_lamp:
    p = pages[first_lamp - 1]
    print(f"\n=== Isi halaman {first_lamp} (pemicu carry-forward) ===")
    print(p.get("cleaned_text", "")[:700])

# 4. Berapa total halaman yang PUNYA kata 'Pasal' (perkiraan luas batang tubuh)
hal_berpasal = [p["page_num"] for p in pages if "Pasal" in p.get("cleaned_text", "")]
print(f"\n→ Total halaman mengandung 'Pasal': {len(hal_berpasal)}")
print(f"  Rentang: hal {min(hal_berpasal)} sampai {max(hal_berpasal)}")