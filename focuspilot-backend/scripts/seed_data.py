# scripts/seed_data.py
"""
Run this script to seed realistic test data into Supabase.
Usage: python scripts/seed_data.py

This creates:
- 14 days of focus sessions
- Browsing activity with realistic distraction patterns
- Varied focus scores
"""

import sys
import os
import json
import base64
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from datetime import datetime, timedelta, timezone
import random
import uuid
from pathlib import Path


def load_local_env() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    env_path = backend_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and not os.getenv(key):
            os.environ[key] = value


load_local_env()

# ── Config ────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_KEY", "").strip()
USER_ID = os.getenv("SEED_USER_ID", "").strip()
SEED_USER_JWT = os.getenv("SEED_USER_JWT", "").strip()


def decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload = parts[1]
        padding = '=' * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode((payload + padding).encode('utf-8')).decode('utf-8')
        return json.loads(decoded)
    except Exception:
        return {}


def is_uuid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", value.lower()))


def validate_config() -> None:
    if not SUPABASE_URL:
        raise RuntimeError(
            "Missing SUPABASE_URL environment variable. "
            "Create focuspilot-backend/.env with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SEED_USER_ID."
        )
    if not SUPABASE_KEY:
        raise RuntimeError(
            "Missing SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY). "
            "Use your Supabase service_role key for seeding."
        )
    payload = decode_jwt_payload(SUPABASE_KEY)
    role = payload.get('role')
    if role and role != 'service_role':
        raise RuntimeError(
            f"Invalid Supabase key role '{role}'. Use SUPABASE service_role key for seeding."
        )


validate_config()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def resolve_user_id() -> str:
    if USER_ID:
        if not is_uuid(USER_ID):
            raise RuntimeError("SEED_USER_ID must be a UUID from users.id, not a JWT token")
        return USER_ID

    if SEED_USER_JWT:
        payload = decode_jwt_payload(SEED_USER_JWT)
        token_user_id = (payload.get("user_id") or "").strip()
        if token_user_id and is_uuid(token_user_id):
            print(f"ℹ️ Using user_id from SEED_USER_JWT: {token_user_id}")
            return token_user_id

    users_result = (
        supabase.table('users')
        .select('id, created_at')
        .order('created_at', desc=True)
        .limit(1)
        .execute()
    )

    if users_result.data:
        fallback_user_id = users_result.data[0]['id']
        print(f"ℹ️ SEED_USER_ID missing; using latest user from DB: {fallback_user_id}")
        return fallback_user_id

    raise RuntimeError(
        "Could not resolve seed user. Set SEED_USER_ID (UUID), or SEED_USER_JWT, "
        "or create a user first via /auth/signup."
    )


USER_ID = resolve_user_id()

# ── Realistic distraction sites ───────────────────────────────────────
DISTRACTION_SITES = [
    'youtube.com',
    'twitter.com',
    'instagram.com',
    'tiktok.com',
    'reddit.com',
    'facebook.com',
    'whatsapp.web.com',
    'netflix.com',
]

PRODUCTIVE_SITES = [
    'github.com',
    'stackoverflow.com',
    'docs.python.org',
    'google.com',
    'wikipedia.org',
]


def seed_sessions_and_activities():
    print("🌱 Seeding 14 days of focus sessions...")

    sessions_created = 0
    activities_created = 0

    for day_offset in range(14, 0, -1):
        date = datetime.now(timezone.utc) - timedelta(days=day_offset)

        # 1–3 sessions per day
        num_sessions = random.randint(1, 3)

        for session_num in range(num_sessions):
            # Session start time (morning, afternoon, or evening)
            hour = random.choice([8, 9, 10, 14, 15, 20, 21])
            start_time = date.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=0,
                microsecond=0
            )

            # Session duration (10–90 minutes)
            duration_minutes = random.randint(10, 90)
            end_time = start_time + timedelta(minutes=duration_minutes)

            # Focus score (1–10, biased toward medium)
            focus_score = random.choices(
                range(1, 11),
                weights=[2, 3, 5, 7, 10, 10, 8, 6, 5, 4],
                k=1
            )[0]

            session_id = str(uuid.uuid4())

            # Insert session
            supabase.table('focus_sessions').insert({
                'id':               session_id,
                'user_id':          USER_ID,
                'start_time':       start_time.isoformat(),
                'end_time':         end_time.isoformat(),
                'duration_minutes': duration_minutes,
                'focus_score':      focus_score,
                'distraction_count': 0
            }).execute()

            sessions_created += 1

            # ── Generate browsing activity ─────────────────────────────
            # Low-focus sessions have MORE distraction sites
            if focus_score < 5:
                distraction_ratio = 0.8   # 80% of time on distractions
            elif focus_score < 7:
                distraction_ratio = 0.4
            else:
                distraction_ratio = 0.1

            num_activities = random.randint(3, 12)
            current_time   = start_time

            for _ in range(num_activities):
                # Decide: distraction or productive?
                is_distraction = random.random() < distraction_ratio

                if is_distraction:
                    domain = random.choice(DISTRACTION_SITES)
                    # Distractions last longer
                    duration_seconds = random.randint(60, 600)
                else:
                    domain = random.choice(PRODUCTIVE_SITES)
                    duration_seconds = random.randint(30, 300)

                supabase.table('browsing_activity').insert({
                    'session_id':       session_id,
                    'user_id':          USER_ID,
                    'url':              f"https://www.{domain}/page",
                    'domain':           domain,
                    'timestamp':        current_time.isoformat(),
                    'duration_seconds': duration_seconds
                }).execute()

                activities_created += 1
                current_time += timedelta(seconds=duration_seconds + random.randint(5, 30))

                # Don't go past session end
                if current_time >= end_time:
                    break

    print(f"✅ Created {sessions_created} sessions")
    print(f"✅ Created {activities_created} browsing activities")
    print(f"🎉 Seed complete! Visit /suggestions/ to see ML recommendations")


if __name__ == "__main__":
    seed_sessions_and_activities()
