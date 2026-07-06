import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from collections import Counter

# ─── Setup Logging ────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"parsing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                            encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StructureParser")


# ─── Pola struktur (zona Pasal) ───────────────────────────────
RE_BUKU   = re.compile(r'^\s*Buku\s+(KESATU|KEDUA|KETIGA|KEEMPAT|KELIMA|[IVX]+|\d+)\b',
                       re.IGNORECASE | re.MULTILINE)
RE_BAB    = re.compile(r'^\s*BAB\s+([IVXLCDM]+|\d+)\b', re.IGNORECASE | re.MULTILINE)
RE_BAGIAN = re.compile(r'^\s*Bagian\s+(\w+)', re.IGNORECASE | re.MULTILINE)
RE_PASAL_SPLIT = re.compile(r'(?m)^\s*Pasal\s+(\d+[A-Z]?)\s*$')

# Header awal bagian PENJELASAN (batas batang tubuh → penjelasan)
RE_PENJELASAN_HEADER = re.compile(
    r'(?im)^\s*PENJELASAN\s*\n\s*ATAS'
    r'|^\s*PENJELASAN\s+ATAS\s+(?:UNDANG|PERATURAN)'
    r'|^\s*P\s*E\s*N\s*J\s*E\s*L\s*A\s*S\s*A\s*N\s*$'
)

# ─── Pola deteksi zona (perbaikan false positive Lampiran) ────
RE_HEADER_LAMPIRAN = re.compile(
    r'(?im)^\s*LAMPIRAN\s*(?:[IVX]+|\d+)?\s*$'
    r'|^\s*LAMPIRAN\s+[IVX]+\s*\n\s*PERATURAN'
)
RE_PASAL_LINE = re.compile(r'(?m)^\s*Pasal\s+\d+[A-Z]?\s*$')

# ─── Pola KBLI ────────────────────────────────────────────────
RE_KBLI = re.compile(r'\b(\d{5})\b')
RE_KBLI_ENTRY = re.compile(r'(?m)^\s*(\d{5})\s+([A-Z][A-Z\s,/()-]{3,})$')

# ─── Cakupan F&B (presisi per sektor) ─────────────────────────
KBLI_FNB_PREFIXES = (
    "10", "11",   # industri makanan & minuman
    "55",         # akomodasi
    "56",         # penyediaan makan-minum (inti F&B)
)
KBLI_FNB_ECERAN_PANGAN = (
    "4711",
    "4721", "4722", "4723", "4724",
    "4781",
)


def is_fnb_kbli(code: str) -> bool:
    if code.startswith(KBLI_FNB_PREFIXES):
        return True
    if code.startswith(KBLI_FNB_ECERAN_PANGAN):
        return True
    return False


def is_true_lampiran_header(text: str) -> bool:
    """True hanya kalau halaman punya HEADER Lampiran sejati (bukan sekadar menyebut kata)."""
    return bool(RE_HEADER_LAMPIRAN.search(text[:800]))


def looks_like_batang_tubuh(text: str) -> bool:
    """True kalau halaman masih jelas batang tubuh (>=2 penanda 'Pasal X' di baris sendiri)."""
    return len(RE_PASAL_LINE.findall(text)) >= 2


def strip_vertical_watermark(text: str) -> str:
    """Buang watermark 'www.bps.go.id' yang ter-interleave vertikal (1 karakter/baris)."""
    lines = text.split('\n')
    out = [ln for ln in lines if len(ln.strip()) != 1]
    text = '\n'.join(out)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text


# ─── Struktur unit hasil parsing ──────────────────────────────
@dataclass
class ParsedUnit:
    unit_type: str
    content: str
    pasal_number: str = None
    pasal_int: int = None
    buku: str = None
    bab: str = None
    bagian: str = None
    section: str = "batang_tubuh"         # 'batang_tubuh' | 'penjelasan'
    kbli_code: str = None
    lampiran_ref: str = None
    source_pages: list = field(default_factory=list)
    order_index: int = 0


class StructureParser:
    def __init__(self, doc_meta: dict):
        self.doc_meta = doc_meta or {}

    # ── util ──
    @staticmethod
    def _pasal_to_int(pasal_number: str):
        m = re.match(r'(\d+)', pasal_number or "")
        return int(m.group(1)) if m else None

    @staticmethod
    def _last(rx, text):
        found = list(rx.finditer(text))
        return found[-1].group(0).strip() if found else None

    @staticmethod
    def _page_at(page_map, pos):
        page = None
        for offset, pnum in page_map:
            if offset <= pos:
                page = pnum
            else:
                break
        return page

    # ── Hitung ulang zona (perbaikan false positive Lampiran) ──
    def _tentukan_zona(self, pages: list) -> dict:
        zona = {}
        in_lampiran = False
        for p in pages:
            text = p.get("cleaned_text", "")
            pnum = p["page_num"]
            header_lampiran = is_true_lampiran_header(text)
            batang_tubuh = looks_like_batang_tubuh(text)

            if not in_lampiran:
                if header_lampiran and not batang_tubuh:
                    in_lampiran = True
            else:
                if batang_tubuh and not header_lampiran:
                    in_lampiran = False
            zona[pnum] = "lampiran" if in_lampiran else "pasal"
        return zona

    # ── Tandai section via header PENJELASAN ──────────────────
    def _tandai_section(self, units: list, text: str, positions: list) -> list:
        m = RE_PENJELASAN_HEADER.search(text)
        if not m:
            for u in units:
                u.section = "batang_tubuh"
            return units
        batas = m.start()
        for u, pos in zip(units, positions):
            u.section = "penjelasan" if pos >= batas else "batang_tubuh"
        return units

    # ── JALUR 1: ZONA PASAL ───────────────────────────────────
    def parse_pasal_zone(self, pages: list) -> list:
        full, page_map = [], []
        for p in pages:
            t = p.get("cleaned_text", "")
            page_map.append((sum(len(x) for x in full), p["page_num"]))
            full.append(t)
        text = "\n".join(full)

        matches = list(RE_PASAL_SPLIT.finditer(text))
        if not matches:
            return []

        units, positions = [], []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            pasal_number = m.group(1)
            body = text[m.end():end].strip()

            head = text[:start]
            buku = self._last(RE_BUKU, head)
            bab = self._last(RE_BAB, head)
            bagian = self._last(RE_BAGIAN, head)
            src_page = self._page_at(page_map, start)

            units.append(ParsedUnit(
                unit_type="pasal",
                content=f"Pasal {pasal_number}\n{body}",
                pasal_number=pasal_number,
                pasal_int=self._pasal_to_int(pasal_number),
                buku=buku, bab=bab, bagian=bagian,
                source_pages=[src_page] if src_page else [],
                order_index=i,
            ))
            positions.append(start)

        units = self._tandai_section(units, text, positions)
        return units

    # ── JALUR 2: ZONA LAMPIRAN (kode KBLI → kewajiban) ────────
    def parse_lampiran_zone(self, pages: list) -> list:
        units, order = [], 0
        for p in pages:
            text = p.get("cleaned_text", "")
            ref = (p.get("position_markers") or {}).get("lampiran_ref")
            hits = list(RE_KBLI.finditer(text))
            if not hits:
                continue

            for j, h in enumerate(hits):
                start = h.start()
                end = hits[j + 1].start() if j + 1 < len(hits) else len(text)
                kbli = h.group(1)
                block = text[start:end].strip()
                if len(block) < 25:
                    continue

                units.append(ParsedUnit(
                    unit_type="kbli_block",
                    content=block,
                    kbli_code=kbli,
                    lampiran_ref=ref,
                    source_pages=[p["page_num"]],
                    order_index=order,
                ))
                order += 1
        return units

    # ── JALUR 3: KAMUS KBLI 2020 ──────────────────────────────
    def parse_kbli_dictionary(self, pages: list) -> list:
        full = "\n".join(strip_vertical_watermark(p.get("cleaned_text", "")) for p in pages)
        entries = list(RE_KBLI_ENTRY.finditer(full))
        if not entries:
            return []

        units, order = [], 0
        for i, m in enumerate(entries):
            code = m.group(1)
            if not is_fnb_kbli(code):
                continue
            start = m.start()
            end = entries[i + 1].start() if i + 1 < len(entries) else len(full)
            block = full[start:end].strip()

            units.append(ParsedUnit(
                unit_type="kbli_dictionary",
                content=block,
                kbli_code=code,
                order_index=order,
            ))
            order += 1

        logger.info(f"    [KBLI-DICT] {len(units)} entri F&B dari {len(entries)} total entri")
        return units

    # ── Orkestrasi ────────────────────────────────────────────
    def parse(self, cleaned_doc: dict) -> dict:
        pages = cleaned_doc.get("pages", [])
        fname = cleaned_doc.get("file_name", "")
        is_kbli_dict = "kbli" in fname.lower()

        # KASUS KHUSUS: file hasil split Lampiran (tak punya header 'LAMPIRAN'
        # di halaman awal karena sudah terpotong). Paksa SEMUA halaman ke
        # jalur KBLI Lampiran, abaikan deteksi zona otomatis.
        is_forced_lampiran = "lampiran_L_pariwisata" in fname

        if is_forced_lampiran:
            all_pages = [p for p in pages if p.get("cleaned_text", "").strip()]
            kbli_units = self.parse_lampiran_zone(all_pages)
            pasal_units, kbli_dict_units = [], []
            zona = {p["page_num"]: "lampiran" for p in pages}

        elif is_kbli_dict:
            all_pages = [p for p in pages if p.get("cleaned_text", "").strip()]
            kbli_dict_units = self.parse_kbli_dictionary(all_pages)
            pasal_units, kbli_units = [], []
            zona = {p["page_num"]: "pasal" for p in pages}

        else:
            zona = self._tentukan_zona(pages)
            pasal_pages = [p for p in pages
                           if zona.get(p["page_num"]) == "pasal"
                           and p.get("cleaned_text", "").strip()]
            lampiran_pages = [p for p in pages
                              if zona.get(p["page_num"]) == "lampiran"
                              and p.get("cleaned_text", "").strip()]
            pasal_units = self.parse_pasal_zone(pasal_pages)
            kbli_units = self.parse_lampiran_zone(lampiran_pages)
            kbli_dict_units = []

        low_quality = "lampiran_L_pariwisata" in fname
        all_units = pasal_units + kbli_units + kbli_dict_units

        kbli_prefix_dist = dict(Counter(u.kbli_code[:2] for u in all_units if u.kbli_code))
        section_dist = dict(Counter(u.section for u in all_units if u.unit_type == "pasal"))
        zona_dist = dict(Counter(zona.values()))

        result = {
            "file_name": fname,
            "metadata": cleaned_doc.get("metadata", {}),
            "parsed_date": datetime.now().isoformat(),
            "text_quality": "low" if low_quality else "normal",
            "stats": {
                "total_units": len(all_units),
                "pasal_units": len(pasal_units),
                "kbli_units": len(kbli_units),
                "kbli_dict_units": len(kbli_dict_units),
                "distinct_kbli": len(set(u.kbli_code for u in all_units if u.kbli_code)),
                "kbli_prefix_dist": kbli_prefix_dist,
                "section_dist": section_dist,
                "zona_dist": zona_dist,
            },
            "units": [asdict(u) for u in all_units],
        }
        logger.info(f"  [OK] {len(pasal_units)} pasal "
                    f"(BT={section_dist.get('batang_tubuh', 0)} "
                    f"PJ={section_dist.get('penjelasan', 0)}), "
                    f"{len(kbli_units)} blok KBLI, "
                    f"{len(kbli_dict_units)} entri kamus | "
                    f"zona: pasal={zona_dist.get('pasal', 0)}hal "
                    f"lampiran={zona_dist.get('lampiran', 0)}hal")
        return result


# ─── CLI ──────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="KlausulaAI - Structure Parser tiga-jalur")
    ap.add_argument("--input", "-i", required=True, help="Folder/file *_cleaned.json")
    ap.add_argument("--output", "-o", default="../04_parsed")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    inp = Path(args.input)
    files = [inp] if inp.is_file() else sorted(inp.glob("*_cleaned.json"))
    if not files:
        print(f"[ERROR] Tidak ada *_cleaned.json di {inp}")
        return

    print(f"\n[START] Parsing {len(files)} dokumen")
    print("=" * 60)
    grand = []
    for i, f in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {f.name}")
        try:
            with open(f, encoding="utf-8") as fh:
                doc = json.load(fh)
            parser = StructureParser(doc.get("metadata", {}))
            res = parser.parse(doc)

            stem = f.stem.replace("_cleaned", "")
            with open(out / f"{stem}_parsed.json", "w", encoding="utf-8") as fh:
                json.dump(res, fh, ensure_ascii=False, indent=2)
            grand.append((f.name, res["stats"]))
        except Exception as e:
            logger.error(f"[ERROR] {f.name}: {e}", exc_info=True)

    print("\n" + "=" * 60)
    print("[SUMMARY]")
    tp = sum(s["pasal_units"] for _, s in grand)
    tk = sum(s["kbli_units"] for _, s in grand)
    td = sum(s["kbli_dict_units"] for _, s in grand)
    tbt = sum(s["section_dist"].get("batang_tubuh", 0) for _, s in grand)
    tpj = sum(s["section_dist"].get("penjelasan", 0) for _, s in grand)
    print(f"Dokumen           : {len(grand)}")
    print(f"Total pasal       : {tp}  (batang_tubuh={tbt}, penjelasan={tpj})")
    print(f"Total blok KBLI   : {tk}")
    print(f"Total entri kamus : {td}")
    print(f"\n[DONE] Output → {out}")


if __name__ == "__main__":
    main()