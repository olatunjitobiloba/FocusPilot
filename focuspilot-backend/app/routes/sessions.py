from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import SessionStart, SessionEnd, ActivityLog
from app.auth import verify_token
from app.database import execute_with_retries
from app.domain_whitelist import is_whitelisted_domain, filter_activities_by_domain
from datetime import datetime, timezone
from collections import defaultdict
import uuid

router = APIRouter(prefix="/sessions", tags=["Sessions"])
security = HTTPBearer()


def run_db(operation, failure_message: str):
    try:
        return execute_with_retries(operation)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail=failure_message)


def parse_session_datetime(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def session_sort_key(session: dict) -> datetime:
    try:
        return parse_session_datetime(session.get('start_time'))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def get_newest_active_session(active_sessions: list[dict]) -> tuple[dict, list[dict]]:
    sorted_sessions = sorted(active_sessions, key=session_sort_key, reverse=True)
    newest = sorted_sessions[0]
    stale = sorted_sessions[1:]
    return newest, stale


def get_elapsed_minutes_from_start(start_time_value) -> int:
    if not start_time_value:
        return 0
    try:
        start_time = parse_session_datetime(start_time_value)
        return max(0, int((datetime.now(timezone.utc) - start_time).total_seconds() / 60))
    except Exception:
        return 0


def get_elapsed_seconds_from_start(start_time_value) -> int:
    if not start_time_value:
        return 0
    try:
        start_time = parse_session_datetime(start_time_value)
        return max(0, int((datetime.now(timezone.utc) - start_time).total_seconds()))
    except Exception:
        return 0


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract user_id from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload['user_id']


# ─────────────────────────────────────────────
# SESSION MANAGEMENT
# ─────────────────────────────────────────────

@router.post("/start")
def start_session(
    session_data: SessionStart,
    user_id: str = Depends(get_current_user_id)
):
    """Start a new focus session"""
    # Check for active session(s)
    active = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).is_('end_time', 'null').execute(),
        "Database unavailable while starting session"
    )

    if active.data:
        newest_active, stale_sessions = get_newest_active_session(active.data)

        # Self-heal old duplicate active sessions if they exist
        if stale_sessions:
            now_iso = datetime.now(timezone.utc).isoformat()
            for stale_session in stale_sessions:
                stale_duration = get_elapsed_minutes_from_start(stale_session.get('start_time'))
                run_db(
                    lambda supabase: supabase.table('focus_sessions').update({
                        'end_time': now_iso,
                        'duration_minutes': stale_duration,
                        'focus_score': stale_session.get('focus_score') or 0,
                        'distraction_count': stale_session.get('distraction_count') or 0
                    }).eq('id', stale_session['id']).execute(),
                    "Database unavailable while cleaning duplicate active sessions"
                )

        raise HTTPException(status_code=400, detail="Active session already exists")

    # Create session
    session_id = str(uuid.uuid4())
    result = run_db(
        lambda supabase: supabase.table('focus_sessions').insert({
            'id': session_id,
            'user_id': user_id,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'distraction_count': 0
        }).execute(),
        "Database unavailable while starting session"
    )

    return {
        "message": "Session started",
        "session": {
            "id": session_id,
            "user_id": user_id,
            "start_time": result.data[0]['start_time'],
            "distraction_count": 0
        }
    }


@router.post("/end")
def end_session(
    session_data: SessionEnd,
    user_id: str = Depends(get_current_user_id)
):
    """End an active focus session"""
    # Get session
    session = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('id', session_data.session_id).eq('user_id', user_id).single().execute(),
        "Database unavailable while ending session"
    )

    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Calculate duration safely (fallback to 0 if start_time is malformed)
    end_time = datetime.now(timezone.utc)
    duration = max(0, int(get_elapsed_seconds_from_start(session.data.get('start_time')) / 60))

    # Update session
    run_db(
        lambda supabase: supabase.table('focus_sessions').update({
            'end_time': end_time.isoformat(),
            'duration_minutes': duration,
            'focus_score': session_data.focus_score,
            'distraction_count': session_data.distraction_count
        }).eq('id', session_data.session_id).execute(),
        "Database unavailable while ending session"
    )

    return {
        "session_id": session_data.session_id,
        "duration_minutes": duration,
        "focus_score": session_data.focus_score,
        "message": "Session ended"
    }


@router.get("/active")
def get_active_session(user_id: str = Depends(get_current_user_id)):
    """Get current active session"""
    result = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).is_('end_time', 'null').execute(),
        "Database unavailable while loading active session"
    )

    if not result.data:
        return {"active": False, "session": None}

    session_data, stale_sessions = get_newest_active_session(result.data)

    # Auto-close stale duplicate active sessions to prevent incorrect resume timers.
    if stale_sessions:
        now_iso = datetime.now(timezone.utc).isoformat()
        for stale_session in stale_sessions:
            stale_duration = get_elapsed_minutes_from_start(stale_session.get('start_time'))
            run_db(
                lambda supabase: supabase.table('focus_sessions').update({
                    'end_time': now_iso,
                    'duration_minutes': stale_duration,
                    'focus_score': stale_session.get('focus_score') or 0,
                    'distraction_count': stale_session.get('distraction_count') or 0
                }).eq('id', stale_session['id']).execute(),
                "Database unavailable while cleaning duplicate active sessions"
            )

    elapsed_seconds = get_elapsed_seconds_from_start(session_data.get('start_time'))
    elapsed = max(0, int(elapsed_seconds / 60))

    return {
        "active": True,
        "session": {
            "id": session_data['id'],
            "user_id": session_data['user_id'],
            "start_time": session_data['start_time'],
            "distraction_count": session_data.get('distraction_count', 0),
            "elapsed_seconds": elapsed_seconds,
            "elapsed_minutes": elapsed,
            "stale_sessions_closed": len(stale_sessions)
        }
    }


@router.post("/cleanup-active")
def cleanup_active_session(user_id: str = Depends(get_current_user_id)):
    """End the user's current active session, if any."""
    active = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).is_('end_time', 'null').order('start_time', desc=True).execute(),
        "Database unavailable while cleaning active session"
    )

    if not active.data:
        return {"message": "No active session found", "cleaned": False}

    session_data = active.data[0]
    end_time = datetime.now(timezone.utc)
    duration = get_elapsed_minutes_from_start(session_data.get('start_time'))

    run_db(
        lambda supabase: supabase.table('focus_sessions').update({
            'end_time': end_time.isoformat(),
            'duration_minutes': duration,
            'focus_score': session_data.get('focus_score') or 0,
            'distraction_count': session_data.get('distraction_count') or 0
        }).eq('id', session_data['id']).execute(),
        "Database unavailable while cleaning active session"
    )

    return {
        "message": "Active session cleaned up",
        "cleaned": True,
        "session_id": session_data['id'],
        "duration_minutes": duration
    }


@router.get("/history")
def get_session_history(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    """Get user's session history"""
    result = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).order('start_time', desc=True).limit(limit).execute(),
        "Database unavailable while loading session history"
    )

    return {"sessions": result.data}


# ─────────────────────────────────────────────
# ACTIVITY LOGGING
# ─────────────────────────────────────────────

@router.post("/{session_id}/activity")
def log_activity(
    session_id: str,
    activity: ActivityLog,
    user_id: str = Depends(get_current_user_id)
):
    """Log browsing activity during session"""
    # Verify session belongs to user
    session_result = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('id', session_id).eq('user_id', user_id).limit(1).execute(),
        "Database unavailable while logging activity"
    )

    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    if is_whitelisted_domain(activity.domain):
        return {"message": "Activity ignored (whitelisted domain)", "ignored": True}

    # Log activity
    run_db(
        lambda supabase: supabase.table('browsing_activity').insert({
            'session_id': session_id,
            'user_id': user_id,
            'url': activity.url,
            'domain': activity.domain,
            'duration_seconds': activity.duration_seconds
        }).execute(),
        "Database unavailable while logging activity"
    )

    return {"message": "Activity logged"}


@router.get("/{session_id}/activity")
def get_session_activity(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all activity logs for a session"""
    result = run_db(
        lambda supabase: supabase.table('browsing_activity').select("*").eq('session_id', session_id).eq('user_id', user_id).execute(),
        "Database unavailable while loading session activity"
    )
    activities = filter_activities_by_domain(result.data)

    return {"activities": activities}


# ─────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────

@router.post("/cleanup/orphaned")
def cleanup_orphaned_sessions(user_id: str = Depends(get_current_user_id)):
    """Clean up any orphaned (not ended) sessions for the current user"""
    # Find any sessions without end_time
    orphaned = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).is_('end_time', 'null').execute(),
        "Database unavailable while cleaning orphaned sessions"
    )

    if not orphaned.data:
        return {"message": "No orphaned sessions found"}

    # End all orphaned sessions
    for session in orphaned.data:
        run_db(
            lambda supabase: supabase.table('focus_sessions').update({
                'end_time': datetime.now(timezone.utc).isoformat(),
                'duration_minutes': 0
            }).eq('id', session['id']).execute(),
            "Database unavailable while cleaning orphaned sessions"
        )

    return {"message": f"Cleaned up {len(orphaned.data)} orphaned session(s)"}


# ─────────────────────────────────────────────
# HISTORY & SUMMARY (NEW - ADDED DAY 5)
# ─────────────────────────────────────────────

@router.get("/history/detailed")
def get_detailed_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id)
):
    """Get detailed session history with activities"""
    # Get only completed sessions (with end_time and duration > 0)
    sessions_result = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).not_.is_('end_time', 'null').gt('duration_minutes', 0).order('start_time', desc=True).range(offset, offset + limit - 1).execute(),
        "Database unavailable while loading detailed session history"
    )

    sessions = sessions_result.data

    # For each session, get activities
    detailed_sessions = []

    for session in sessions:
        session_id = session['id']

        # Get activities for this session
        activities_result = run_db(
            lambda supabase: supabase.table('browsing_activity').select("*").eq('session_id', session_id).execute(),
            "Database unavailable while loading detailed session activity"
        )

        activities = filter_activities_by_domain(activities_result.data)

        # Calculate distraction count
        distraction_count = len(activities)

        # Get top distraction for this session
        top_distraction = None
        if activities:
            domain_time = defaultdict(int)
            for activity in activities:
                domain_time[activity['domain']] += activity['duration_seconds'] or 0

            top_domain = max(domain_time, key=domain_time.get)
            top_distraction = {
                'domain': top_domain,
                'seconds': domain_time[top_domain]
            }

        # Format session
        detailed_sessions.append({
            'id': session['id'],
            'start_time': session['start_time'],
            'end_time': session['end_time'],
            'duration_minutes': session['duration_minutes'],
            'focus_score': session['focus_score'],
            'distraction_count': distraction_count,
            'top_distraction': top_distraction,
            'activities': activities[:5]  # First 5 activities
        })

    return {
        "sessions": detailed_sessions,
        "total": len(sessions),
        "limit": limit,
        "offset": offset
    }


@router.get("/summary")
def get_session_summary(user_id: str = Depends(get_current_user_id)):
    """Get overall session summary stats"""
    # Get all completed sessions
    result = run_db(
        lambda supabase: supabase.table('focus_sessions').select("*").eq('user_id', user_id).not_.is_('end_time', 'null').execute(),
        "Database unavailable while loading session summary"
    )

    sessions = result.data

    if not sessions:
        return {
            "total_sessions": 0,
            "total_hours": 0,
            "avg_session_minutes": 0,
            "avg_focus_score": 0,
            "longest_session_minutes": 0,
            "total_distractions": 0
        }

    # Calculate stats
    total_minutes = sum(s['duration_minutes'] or 0 for s in sessions)
    total_hours = round(total_minutes / 60, 2)
    avg_minutes = round(total_minutes / len(sessions), 1)

    focus_scores = [s['focus_score'] for s in sessions if s['focus_score']]
    avg_focus_score = round(sum(focus_scores) / len(focus_scores), 1) if focus_scores else 0

    longest_session = max(sessions, key=lambda s: s['duration_minutes'] or 0)

    total_distractions = sum(s['distraction_count'] or 0 for s in sessions)

    return {
        "total_sessions": len(sessions),
        "total_hours": total_hours,
        "total_minutes": total_minutes,
        "avg_session_minutes": avg_minutes,
        "avg_focus_score": avg_focus_score,
        "longest_session_minutes": longest_session['duration_minutes'],
        "total_distractions": total_distractions,
        "avg_distractions_per_session": round(total_distractions / len(sessions), 1)
    }