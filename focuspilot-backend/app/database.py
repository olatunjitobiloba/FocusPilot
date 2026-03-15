# app/database.py
from supabase import create_client, Client
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import re
from typing import Any, Dict

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
        'connecterror',
        'httpx.connecterror',
        'httpcore.connecterror',
        'getaddrinfo failed',
        'name or service not known',
        'temporary failure in name resolution',
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


def _extract_unknown_column_name(exc: Exception) -> str | None:
    message = str(exc)
    match = re.search(r"Could not find the '([^']+)' column", message)
    if match:
        return match.group(1)
    return None


def normalize_agent_state_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    state_value = normalized.get('state')

    if isinstance(state_value, dict):
        normalized['state'] = state_value.get('status', 'idle')

        current_risk = state_value.get('current_risk')
        if current_risk is not None and normalized.get('risk_score') is None:
            normalized['risk_score'] = current_risk

        last_assessed = state_value.get('last_assessed')
        if last_assessed and not normalized.get('last_cycle'):
            normalized['last_cycle'] = last_assessed

    return normalized


def upsert_agent_state(payload: Dict[str, Any]):
    normalized_payload = normalize_agent_state_payload(payload)

    while True:
        try:
            return execute_with_retries(
                lambda client: client.table('agent_state').upsert(normalized_payload).execute()
            )
        except Exception as exc:
            unknown_column = _extract_unknown_column_name(exc)
            if not unknown_column or unknown_column not in normalized_payload:
                raise
            normalized_payload.pop(unknown_column, None)
