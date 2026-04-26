import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL           = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY      = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY   = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_KEY:
    raise ValueError("❌ Cek .env: SUPABASE_URL, ANON_KEY, SERVICE_ROLE_KEY")

# Admin client (bypass RLS) — untuk ingestion, background jobs
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Public client (RLS aktif) — untuk user queries
supabase_public: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_user_client(jwt_token: str) -> Client:
    """
    Client dengan session user spesifik.
    Pakai untuk queries yang harus respect RLS.
    
    jwt_token: access_token dari Supabase auth (dari Next.js)
    """
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    # Set JWT token untuk authentication
    # Format: "Bearer <token>" di header Authorization
    client.postgrest.auth(jwt_token)
    
    return client

print("✅ Database clients ready")