import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_supabase() -> Client:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 
    
    if not supabase_url or not supabase_key:
         raise ValueError("Kredensial Supabase tidak lengkap di .env backend")
         
    return create_client(supabase_url, supabase_key)