# app/database.py
from supabase import create_client, Client
import os
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

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


def _is_transient_db_error(exc: Exception) -> bool:
    message = str(exc).lower()
    transient_markers = [
        'winerror 10035',
        'readerror',
        'httpcore.readerror',
        'a non-blocking socket operation could not be completed immediately',
        'connection reset',
        'timed out',
    ]
    return any(marker in message for marker in transient_markers)


def get_supabase(force_refresh: bool = False):
    global supabase
    if force_refresh:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


def execute_with_retries(operation, retries: int = 2, base_delay_seconds: float = 0.12):
    last_error = None

    for attempt in range(retries + 1):
        try:
            client = get_supabase(force_refresh=attempt > 0)
            return operation(client)
        except Exception as exc:
            last_error = exc
            if not _is_transient_db_error(exc) or attempt == retries:
                raise
            time.sleep(base_delay_seconds * (attempt + 1))

    raise last_error
