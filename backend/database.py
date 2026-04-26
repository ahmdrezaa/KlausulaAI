import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Load variabel dari .env
load_dotenv()

# 2. Ambil URL dan Key dari environment
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# 3. Validasi singkat (biar nggak bingung kalau kosong)
if not url or not key:
    raise ValueError("❌ Gagal mengambil SUPABASE_URL atau KEY. Cek file .env kamu!")

# 4. Inisialisasi Client
supabase: Client = create_client(url, key)

print("✅ Koneksi Supabase berhasil diinisialisasi!")