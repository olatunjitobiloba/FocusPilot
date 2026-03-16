# app/routes/stats.py
from fastapi import APIRouter, Depends
from app.auth import get_current_user_id
from app.database import get_supabase, execute_with_retries
from app.domain_whitelist import is_whitelisted_domain
from datetime import datetime, timedelta, timezone
import re

router = APIRouter(prefix="/stats", tags=["Statistics"])


def normalize_domain(value: str) -> str:
    domain = (value or '').strip().lower()
    domain = domain.replace('https://', '').replace('http://', '')
    domain = domain.split('/')[0]
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def safe_parse_datetime(value: str) -> datetime:
    """Parse DB timestamps with tolerant fractional second handling."""
    if value is None:
        raise ValueError("Missing datetime value")

    text = str(value).strip().strip("\"'")
    if not text:
        raise ValueError("Empty datetime value")

    text = "".join(ch for ch in text if ch.isprintable())
    text = text.replace('Z', '+00:00')

    match = re.search(
        r"(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(?:[+-]\d{2}:?\d{2})?",
        text
    )
    if match:
        fractional = match.group(7) or "0"
        microsecond = int(fractional[:6].ljust(6, '0'))
        return datetime(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            int(match.group(5)),
            int(match.group(6)),
            microsecond,
            tzinfo=timezone.utc
        )

    parsed = datetime.fromisoformat(text.replace(' ', 'T', 1))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_productive_domains(supabase, user_id: str) -> set[str]:
    result = execute_with_retries(
        lambda db: db.table('suggestion_feedback').select('domain').eq('user_id', user_id).eq('action', 'productive').execute()
    )
    return {
        normalize_domain(item.get('domain', ''))
        for item in (result.data or [])
        if item.get('domain')
    }

@router.get("/daily")
def get_daily_stats(user_id: str = Depends(get_current_user_id)):
    """
    Get today's focus statistics for the authenticated user.
    """
    supabase = get_supabase()
    
    # Get today's date
    today = datetime.now().date()
    
    # Query completed sessions for today
    result = execute_with_retries(lambda db: db.table('focus_sessions').select(
        'duration_minutes, focus_score, distraction_count'
    ).eq('user_id', user_id).gte(
        'start_time', f'{today}T00:00:00'
    ).lte(
        'start_time', f'{today}T23:59:59'
    ).execute())
    sessions = result.data
    
    # Check for active session (no end_time)
    active_result = execute_with_retries(lambda db: db.table('focus_sessions').select(
        'id, start_time'
    ).eq('user_id', user_id).is_('end_time', 'null').gte(
        'start_time', f'{today}T00:00:00'
    ).lte(
        'start_time', f'{today}T23:59:59'
    ).execute())
    
    # Calculate stats
    total_focus_minutes = sum((s.get('duration_minutes') or 0) for s in sessions)
    sessions_count = len(sessions)
    
    # Add active session elapsed time if exists
    if active_result.data:
        active_session = active_result.data[0]
        start_time_str = active_session['start_time']

        # Parse start_time robustly across inconsistent DB timestamp formats.
        start_time = safe_parse_datetime(start_time_str)
        
        # Calculate elapsed minutes
        now = datetime.now(timezone.utc)
        elapsed_minutes = (now - start_time).total_seconds() / 60
        total_focus_minutes += elapsed_minutes
        sessions_count += 1
    total_distractions = sum((s.get('distraction_count') or 0) for s in sessions)
    avg_focus_score = (
        sum((s.get('focus_score') or 0) for s in sessions) / sessions_count 
        if sessions_count > 0 else 0
    )

    # Get top distractions (from browsing_activity table)
    distractions_result = execute_with_retries(lambda db: db.table('browsing_activity').select(
        'domain'
    ).eq('user_id', user_id).gte(
        'timestamp', f'{today}T00:00:00'
    ).execute())
    productive_domains = get_productive_domains(supabase, user_id)

    # Count domain frequency
    from collections import Counter
    domain_counts = Counter(
        normalize_domain(d['domain'])
        for d in distractions_result.data
        if d.get('domain')
        and not is_whitelisted_domain(d['domain'])
        and normalize_domain(d['domain']) not in productive_domains
    )
    top_distractions = [domain for domain, _ in domain_counts.most_common(3)]
    
    return {
        "date": str(today),
        "total_focus_minutes": round(total_focus_minutes),
        "sessions_count": sessions_count,
        "distraction_count": total_distractions,
        "avg_focus_score": round(avg_focus_score, 1),
        "top_distractions": top_distractions
    }

@router.get("/weekly")
def get_weekly_stats(user_id: str = Depends(get_current_user_id)):
    """
    Get this week's focus statistics for the authenticated user.
    """
    supabase = get_supabase()
    
    # Get week start (Monday) and end (Sunday)
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday

    # Query sessions for this week
    result = execute_with_retries(lambda db: db.table('focus_sessions').select(
        'duration_minutes, start_time, focus_score'
    ).eq('user_id', user_id).gte(
        'start_time', f'{week_start}T00:00:00'
    ).lte(
        'start_time', f'{week_end}T23:59:59'
    ).execute())
    
    sessions = result.data
    
    # Calculate stats
    total_focus_minutes = sum((s.get('duration_minutes') or 0) for s in sessions)
    total_sessions = len(sessions)
    avg_session_duration = (
        total_focus_minutes / total_sessions 
        if total_sessions > 0 else 0
    )

    # Calculate streak (consecutive days with sessions)
    from collections import defaultdict
    sessions_by_date = defaultdict(lambda: {'minutes': 0, 'sessions': 0})
    for session in sessions:
        date = session['start_time'][:10]  # Extract date part
        sessions_by_date[date]['minutes'] += (session.get('duration_minutes') or 0)
        sessions_by_date[date]['sessions'] += 1

    # Count consecutive days from today backwards
    current_streak = 0
    check_date = today
    while str(check_date) in sessions_by_date:
        current_streak += 1
        check_date -= timedelta(days=1)

    # Find best day
    best_day = max(sessions_by_date.items(), key=lambda x: x[1]['sessions'])[0] if sessions_by_date else str(today)

    # Productivity trend (compare first half vs second half of week)
    mid_week = week_start + timedelta(days=3)
    first_half = [s for s in sessions if s['start_time'][:10] < str(mid_week)]
    second_half = [s for s in sessions if s['start_time'][:10] >= str(mid_week)]

    first_half_minutes = sum((s.get('duration_minutes') or 0) for s in first_half)
    second_half_minutes = sum((s.get('duration_minutes') or 0) for s in second_half)

    if first_half_minutes == 0:
        trend = "new"
    elif second_half_minutes > first_half_minutes:
        trend = "increasing"
    elif second_half_minutes < first_half_minutes:
        trend = "decreasing"
    else:
        trend = "stable"
    
    # Create daily breakdown for chart
    daily_breakdown = {}
    for i in range(7):
        date = week_start + timedelta(days=i)
        date_str = str(date)
        daily_breakdown[date_str] = sessions_by_date.get(date_str, {'minutes': 0, 'sessions': 0})
    
    return {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "total_focus_hours": round(total_focus_minutes / 60, 1),
        "total_sessions": total_sessions,
        "avg_session_duration": round(avg_session_duration, 0),
        "current_streak": current_streak,
        "best_day": best_day,
        "productivity_trend": trend,
        "daily_breakdown": daily_breakdown
    }

def calculate_streak(user_id: str, supabase):
    """Calculate consecutive days with at least 1 session"""
    # Get all sessions ordered by date
    result = execute_with_retries(lambda db: db.table('focus_sessions').select("start_time").eq('user_id', user_id).order('start_time', desc=True).execute())
    
    if not result.data:
        return 0
    
    # Extract unique dates
    dates = set()
    for session in result.data:
        date = session['start_time'][:10]
        dates.add(date)
    
    # Count consecutive days from today
    streak = 0
    current_date = datetime.now(timezone.utc).date()
    
    while current_date.isoformat() in dates:
        streak += 1
        current_date -= timedelta(days=1)
    
    return streak
