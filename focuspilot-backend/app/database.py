# app/database.py
from supabase import create_client, Client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Guard against missing env vars
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        f"Missing Supabase credentials! "
        f"SUPABASE_URL={'SET' if SUPABASE_URL else 'MISSING'}, "
        f"SUPABASE_KEY={'SET' if SUPABASE_KEY else 'MISSING'}"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase():
    return supabase
