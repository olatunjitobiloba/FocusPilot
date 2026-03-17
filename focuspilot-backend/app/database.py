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

# Cache unsupported agent_state columns discovered at runtime.
_agent_state_unsupported_columns: set[str] = set()


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
        'server disconnected',
        'remoteprocotolerror',
        'remoteprotocolerror',
        'protocol_error',
        'connectionterminated',
        'connection_terminated',
        'errorcodes.protocol_error',
        'errorcode',
        'last_stream_id',
        'stream_id',
        'h2',
    ]
    return any(marker in message for marker in transient_markers)


def get_supabase(force_refresh: bool = False):
    global supabase
    if force_refresh:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


def execute_with_retries(operation, retries: int = 3, base_delay_seconds: float = 0.15):
    last_error = None

    for attempt in range(retries + 1):
        try:
            client = get_supabase(force_refresh=attempt > 0)
            return operation(client)
        except Exception as exc:
            last_error = exc
            error_str = str(exc).lower()

            print(
                f"[DB] Attempt {attempt + 1}/{retries + 1} failed: "
                f"{type(exc).__name__}: {exc}"
            )

            # Schema mismatches (PGRST204) are permanent — never retry.
            if _is_schema_mismatch_error(exc):
                print("[DB] Schema error (PGRST204) — not retrying")
                raise

            is_http2_error = any(marker in error_str for marker in [
                'protocol_error',
                'connectionterminated',
                'connection_terminated',
                'stream_id',
                'last_stream_id',
                'remoteprotocolerror',
                'errorcodes.protocol_error',
                'h2',
            ])

            if is_http2_error:
                # Ensure next retry uses a fresh HTTP connection/session.
                print("[DB] HTTP/2 error detected - forcing client refresh")
                get_supabase(force_refresh=True)

            if not _is_transient_db_error(exc) or attempt == retries:
                raise

            delay_seconds = base_delay_seconds * (attempt + 1)
            print(f"[DB] Retrying in {delay_seconds:.2f}s...")
            time.sleep(delay_seconds)

    raise last_error


def safe_query(operation, fallback=None):
    """
    Execute a query with retry logic and return fallback on failure.
    """
    try:
        result = execute_with_retries(operation)
        if hasattr(result, 'data'):
            return result.data
        return result
    except Exception as exc:
        print(f"[DB] safe_query failed after retries: {exc}")
        return fallback if fallback is not None else []


def _is_schema_mismatch_error(exc: Exception) -> bool:
    """PGRST204 = column not found in schema cache. Never transient — don't retry."""
    msg = str(exc)
    return (
        'PGRST204' in msg
        or ('Could not find' in msg and 'column' in msg)
        or 'schema cache' in msg
    )


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

    # Ensure schema-required state is always present.
    if normalized.get('state') in (None, ''):
        normalized['state'] = 'idle'

    # Keep only columns that exist in the agent_state table schema.
    allowed_columns = {
        'user_id', 'state', 'risk_score',
        'last_cycle', 'cycle_count',
        'last_action', 'last_assessed', 'updated_at',
    }
    normalized = {k: v for k, v in normalized.items() if k in allowed_columns}

    # Also drop any columns runtime-detected as unsupported in this deployment.
    for column in list(_agent_state_unsupported_columns):
        normalized.pop(column, None)

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
            _agent_state_unsupported_columns.add(unknown_column)
            normalized_payload.pop(unknown_column, None)
