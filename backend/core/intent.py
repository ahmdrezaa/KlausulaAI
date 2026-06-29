"""
Intent classification ringan untuk KlausulaAI.

Memutuskan apakah sebuah pesan perlu melewati pipeline RAG penuh (retrieval +
grading + generation) atau cukup dijawab langsung karena hanya sapaan / obrolan
ringan. Murni heuristik (tanpa LLM) → instan & tidak memakai kuota Gemini.

PRINSIP: bias ke RAG. Hanya sapaan yang JELAS yang di-skip; apa pun yang
mengandung indikasi pertanyaan/hukum tetap masuk RAG supaya tidak ada
pertanyaan substantif yang salah dilewati.
"""

import re

# Sapaan / obrolan ringan yang boleh dijawab langsung tanpa retrieval.
_SMALLTALK_EXACT = {
    "halo", "hallo", "helo", "hello", "hi", "hai", "hay", "hey", "hei",
    "p", "pagi", "siang", "sore", "malam",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "selamat datang",
    "assalamualaikum", "assalamualaikum wr wb", "salam",
    "terima kasih", "terimakasih", "makasih", "thanks", "thank you", "thx", "tq",
    "ok", "oke", "okay", "okee", "sip", "siap", "mantap", "baik", "noted",
    "tes", "tess", "test", "testing", "coba", "cek",
    "permisi", "yo", "yoo", "hehe", "wkwk", "lol",
}

# Pesan diawali kata sapaan (mis. "halo kak", "hai bot", "hallooo").
_GREETING_PREFIX = re.compile(
    r"^(hai+|halo+|hallo+|helo+|hello+|hi+|hey+|hei+|pagi|siang|sore|malam|"
    r"assalamualaikum|permisi)\b",
    re.IGNORECASE,
)

# Pola kata "test" berulang (tes, tess, teesst, dll).
_TEST_PATTERN = re.compile(r"^te+s+t*$", re.IGNORECASE)

# Indikator pesan SUBSTANTIF (pertanyaan / istilah hukum). Kalau salah satu
# muncul, pesan TIDAK dianggap sapaan walau pendek.
_SUBSTANTIVE = re.compile(
    r"\?|\b("
    r"apa|apakah|bagaimana|gimana|berapa|kapan|kenapa|mengapa|siapa|dimana|"
    r"jelaskan|sebutkan|bisakah|bolehkah|tolong|cara|maksud|arti|"
    r"syarat|aturan|atur|ketentuan|prosedur|hak|kewajiban|wajib|sanksi|denda|"
    r"pasal|uu|undang|hukum|perjanjian|kontrak|klausul|notaris|akta|"
    r"pt|cv|firma|koperasi|pkwt|pkwtt|phk|pesangon|upah|gaji|karyawan|buruh|"
    r"izin|perizinan|nib|oss|pajak|npwp|umkm|umk|merek|haki|waralaba|sengketa"
    r")\b",
    re.IGNORECASE,
)


# Indikator pesan yang MERUJUK ke dokumen milik user sendiri (mis. "jelaskan
# dokumen saya", "isi perjanjian ini", "ringkas file yang saya upload"). Dipakai
# rag_chain untuk MENJAMIN chunk dokumen user ikut jadi kandidat retrieval —
# karena untuk frasa samar begini, chunk dokumen user sering kalah ambang
# kemiripan dari pasal UU yang kebetulan memuat kata "dokumen".
_DOC_NOUN = r"dokumen|file|berkas|lampiran|perjanjian|kontrak|surat|akta|laporan|proposal|sertifikat|naskah"
_DOC_REFERENCE = re.compile(
    # (a) kata-benda-dokumen diikuti kata milik/penunjuk: "dokumen saya", "perjanjian ini"
    rf"\b({_DOC_NOUN})\b(?:\s+\w+){{0,3}}?\s+(saya|aku|kami|ini|itu|tersebut|nya)\b"
    # (b) "... yang saya/aku/kami upload/unggah/kirim/berikan/lampirkan/kasih"
    rf"|\byang\s+(saya|aku|kami)\s+(upload|unggah|kirim|beri|berikan|lampir\w*|kasih|kasi)\b"
    # (c) verba baca/jelaskan/ringkas + kata-benda-dokumen dalam jarak dekat
    rf"|\b(isi|maksud|jelas\w*|ringkas\w*|rangkum\w*|baca|bacakan|analis\w*|review|tinjau\w*|paham\w*)\b.{{0,30}}?\b({_DOC_NOUN})\b",
    re.IGNORECASE,
)


def is_document_reference(message: str) -> bool:
    """True jika pesan merujuk ke dokumen yang diunggah user (bukan pertanyaan
    hukum umum). Heuristik tanpa LLM."""
    return bool(_DOC_REFERENCE.search(message or ""))


# ── Intent: pertanyaan tentang KEMAMPUAN / IDENTITAS produk ──────────────────
# "kamu bisa apa", "kamu siapa", "bisa bantu apa aja", "fungsimu apa", dll.
# → dijawab langsung dgn perkenalan + 3 tahap (tanpa RAG).
_CAPABILITY = re.compile(
    r"\b("
    r"(kamu|kau|km|anda|lo|lu)\s+(bisa|dapat)\s+(apa|apa\s*aja|apa\s*saja|ngapain|ngapain\s*aja|bantu\s+apa|melakukan\s+apa)"
    r"|bisa\s+(apa|apa\s*aja|apa\s*saja|ngapain|ngapain\s*aja|bantu\s+apa|melakukan\s+apa|tolong\s+apa)"
    r"|(kamu|kau|km|anda)\s+(siapa|ini\s+apa|itu\s+apa|tuh\s+apa|apaan)"
    r"|(fungsi|kemampuan|kegunaan|kapabilitas|kebisaan|guna|manfaat)(mu|nya|\s*kamu|\s*anda)?\s+(apa|apa\s*aja|apa\s*saja)"
    r"|apa\s+(saja\s+)?(yang\s+)?(bisa|dapat)\s+(kamu|anda|km)\s+(bantu|lakukan|kerjakan|kerjain)"
    r")",
    re.IGNORECASE,
)

# ── Intent: pertanyaan CARA PAKAI FITUR aplikasi ─────────────────────────────
# "cara ganti judul obrolan", "gimana upload dokumen", "cara hapus chat", dll.
# → dijawab langsung dgn panduan fitur (tanpa RAG). Object difokuskan ke objek
# APLIKASI (obrolan/chat/dokumen/sumber) supaya tidak menabrak pertanyaan hukum
# (mis. "cara mengakhiri kontrak sewa" tetap masuk RAG).
_APP_FEATURE = r"judul|obrolan|chat|sesi|percakapan|dokumen|file|berkas|sumber|source"
_APP_VERB = (
    r"ganti|ubah|mengganti|mengubah|rename|edit|"
    r"upload|unggah|mengunggah|tambah\w*|"
    r"hapus|menghapus|delete|hilangkan|"
    r"buat|membuat|bikin|mulai"
)
_APP_HOW = r"cara|caranya|gimana|gmn|bagaimana|gymana"
_APP_HELP = re.compile(
    rf"\b({_APP_HOW})\b.{{0,40}}?\b({_APP_VERB})\b.{{0,25}}?\b({_APP_FEATURE})\b",
    re.IGNORECASE,
)


def is_capability_question(message: str) -> bool:
    """True jika user menanyakan kemampuan/identitas produk ("kamu bisa apa?")."""
    return bool(_CAPABILITY.search(message or ""))


def is_app_help_question(message: str) -> bool:
    """True jika user menanyakan cara memakai fitur aplikasi (rename, upload, dst)."""
    return bool(_APP_HELP.search(message or ""))


def _normalize(message: str) -> str:
    s = (message or "").strip().lower()
    s = re.sub(r"[!.,?~\-]+$", "", s).strip()  # buang tanda baca di akhir
    s = re.sub(r"\s+", " ", s)
    return s


def is_smalltalk(message: str) -> bool:
    """True jika pesan hanya sapaan / obrolan ringan (boleh skip RAG)."""
    s = _normalize(message)
    if not s:
        return False
    # Apa pun yang berbau pertanyaan/hukum → RAG.
    if _SUBSTANTIVE.search(s):
        return False
    if s in _SMALLTALK_EXACT:
        return True
    if _TEST_PATTERN.match(s):
        return True
    # Pesan pendek (≤4 kata) yang diawali sapaan / ucapan ringan.
    words = s.split()
    if len(words) <= 4:
        if _GREETING_PREFIX.match(s):
            return True
        # Kata pertama termasuk sapaan/ucapan ("makasih ya", "oke deh").
        if words[0] in _SMALLTALK_EXACT:
            return True
        # Dua kata pertama berupa frasa ("terima kasih banyak").
        if len(words) >= 2 and f"{words[0]} {words[1]}" in _SMALLTALK_EXACT:
            return True
    return False


def smalltalk_reply(message: str) -> str:
    """Jawaban langsung untuk sapaan — tanpa retrieval, instan."""
    return (
        "Halo! 👋 Saya **KlausulaAI**, pendamping legal khusus usaha F&B "
        "(cafe, resto, kedai). Saya bantu Anda dari **mendirikan** usaha "
        "(badan usaha & izin), **melindungi** merek, sampai **menjalankan** "
        "(tinjau kontrak & kewajiban ke pelanggan).\n\n"
        "Mau mulai dari mana? Contoh: \"Untuk cafe saya, sebaiknya CV atau PT?\" "
        "— atau unggah kontrak Anda untuk saya tinjau."
    )


def capability_reply() -> str:
    """Perkenalan + daftar kemampuan 3 tahap (untuk pertanyaan 'kamu bisa apa')."""
    return (
        "Saya **KlausulaAI**, pendamping legal untuk usaha F&B Anda. Saya bisa "
        "membantu di tiga tahap usaha kuliner Anda:\n\n"
        "• **Mendirikan** — memilih badan usaha (CV/PT) dan mengurus izin yang "
        "wajib (NIB/OSS, halal, higiene sanitasi, PIRT)\n"
        "• **Melindungi** — mendaftarkan merek (nama & logo) cafe Anda\n"
        "• **Menjalankan** — meninjau kontrak Anda (sewa, supplier, karyawan) "
        "dan kewajiban ke pelanggan\n\n"
        "Anda bisa langsung bertanya, atau unggah dokumen kontrak lewat tombol "
        "**Tambahkan Sumber** di panel kanan untuk saya tinjau."
    )


def app_help_reply(message: str) -> str:
    """Panduan singkat fitur aplikasi yang relevan dengan pertanyaan user."""
    s = (message or "").lower()

    def has(*words: str) -> bool:
        return any(w in s for w in words)

    # Ganti judul / nama obrolan
    if has("judul") or (
        has("ganti", "ubah", "rename", "nama")
        and has("obrolan", "chat", "sesi", "percakapan")
    ):
        return (
            "Untuk mengganti judul obrolan: arahkan kursor ke obrolan pada "
            "**sidebar kiri**, klik ikon **pensil (✎)** di sebelah namanya, "
            "ketik nama baru, lalu klik **Simpan**."
        )

    # Hapus dokumen / sumber
    if has("hapus", "delete", "hilangkan") and has(
        "dokumen", "file", "berkas", "sumber", "source"
    ):
        return (
            "Untuk menghapus dokumen: centang dokumen yang ingin dihapus di "
            "panel **Sumber** (sebelah kanan), lalu klik tombol **Hapus**."
        )

    # Upload / tambah dokumen
    if has("upload", "unggah", "tambah", "tambahkan") and has(
        "dokumen", "file", "berkas", "sumber", "source"
    ):
        return (
            "Untuk mengunggah dokumen: klik tombol **+ Tambahkan Sumber** di "
            "panel **Sumber** (sebelah kanan), lalu pilih file PDF Anda. Setelah "
            "diproses, dokumen siap saya tinjau."
        )

    # Hapus obrolan / chat
    if has("hapus", "delete", "hilangkan") and has(
        "obrolan", "chat", "sesi", "percakapan"
    ):
        return (
            "Untuk menghapus obrolan: arahkan kursor ke obrolan pada "
            "**sidebar kiri**, lalu klik ikon **tempat sampah (🗑)**."
        )

    # Obrolan baru
    if has("baru", "mulai", "buat", "bikin", "tambah") and has(
        "obrolan", "chat", "percakapan", "sesi"
    ):
        return (
            "Untuk memulai obrolan baru: klik tombol **+ Obrolan Baru** di "
            "**sidebar kiri**."
        )

    # Fallback umum: ringkasan fitur
    return (
        "Berikut cara memakai fitur utama KlausulaAI:\n"
        "• **Unggah dokumen** — tombol **+ Tambahkan Sumber** di panel kanan.\n"
        "• **Ganti judul obrolan** — ikon **pensil (✎)** di sebelah nama obrolan (sidebar kiri).\n"
        "• **Hapus obrolan** — ikon **tempat sampah (🗑)** pada obrolan (sidebar kiri).\n"
        "• **Hapus dokumen** — centang dokumen di panel **Sumber**, lalu **Hapus**.\n"
        "• **Obrolan baru** — tombol **+ Obrolan Baru** di sidebar kiri."
    )


def get_direct_reply(message: str):
    """Kembalikan jawaban LANGSUNG (tanpa RAG) jika pesan berupa:
    pertanyaan kemampuan produk, cara pakai fitur, atau sapaan. Selain itu None
    (artinya perlu pipeline RAG penuh). Semua heuristik regex — instan, 0 kuota.

    Urutan penting: kemampuan & cara-pakai dicek SEBELUM sapaan (keduanya pasti
    bukan sapaan karena mengandung kata tanya)."""
    if is_capability_question(message):
        return capability_reply()
    if is_app_help_question(message):
        return app_help_reply(message)
    if is_smalltalk(message):
        return smalltalk_reply(message)
    return None
