from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import SessionStart, SessionEnd, ActivityLog
from app.auth import verify_token
from app.database import get_supabase
from datetime import datetime, timezone
from collections import defaultdict
import uuid

router = APIRouter(prefix="/sessions", tags=["Sessions"])
security = HTTPBearer()


def parse_session_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


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
    supabase = get_supabase()

    # Check for active session
    active = supabase.table('focus_sessions').select("*").eq('user_id', user_id).is_('end_time', 'null').execute()

    if active.data:
        raise HTTPException(status_code=400, detail="Active session already exists")

    # Create session
    session_id = str(uuid.uuid4())
    result = supabase.table('focus_sessions').insert({
        'id': session_id,
        'user_id': user_id,
        'start_time': datetime.now(timezone.utc).isoformat(),
        'distraction_count': 0
    }).execute()

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
    supabase = get_supabase()

    # Get session
    session = supabase.table('focus_sessions').select("*").eq('id', session_data.session_id).eq('user_id', user_id).single().execute()

    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Calculate duration
    start_time = parse_session_datetime(session.data['start_time'])
    end_time = datetime.now(timezone.utc)
    duration = int((end_time - start_time).total_seconds() / 60)

    # Update session
    result = supabase.table('focus_sessions').update({
        'end_time': end_time.isoformat(),
        'duration_minutes': duration,
        'focus_score': session_data.focus_score,
        'distraction_count': session_data.distraction_count
    }).eq('id', session_data.session_id).execute()

    return {
        "session_id": session_data.session_id,
        "duration_minutes": duration,
        "focus_score": session_data.focus_score,
        "message": "Session ended"
    }


@router.get("/active")
def get_active_session(user_id: str = Depends(get_current_user_id)):
    """Get current active session"""
    supabase = get_supabase()

    result = supabase.table('focus_sessions').select("*").eq('user_id', user_id).is_('end_time', 'null').execute()

    if not result.data:
        return {"active": False, "session": None}

    session_data = result.data[0]
    start_time = parse_session_datetime(session_data['start_time'])
    elapsed = int((datetime.now(timezone.utc) - start_time).total_seconds() / 60)

    return {
        "active": True,
        "session": {
            "id": session_data['id'],
            "user_id": session_data['user_id'],
            "start_time": session_data['start_time'],
            "distraction_count": session_data.get('distraction_count', 0),
            "elapsed_minutes": elapsed
        }
    }


@router.get("/history")
def get_session_history(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    """Get user's session history"""
    supabase = get_supabase()

    result = supabase.table('focus_sessions').select("*").eq('user_id', user_id).order('start_time', desc=True).limit(limit).execute()

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
    supabase = get_supabase()

    # Verify session belongs to user
    session = supabase.table('focus_sessions').select("*").eq('id', session_id).eq('user_id', user_id).single().execute()

    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Log activity
    supabase.table('browsing_activity').insert({
        'session_id': session_id,
        'user_id': user_id,
        'url': activity.url,
        'domain': activity.domain,
        'duration_seconds': activity.duration_seconds
    }).execute()

    return {"message": "Activity logged"}


@router.get("/{session_id}/activity")
def get_session_activity(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all activity logs for a session"""
    supabase = get_supabase()

    result = supabase.table('browsing_activity').select("*").eq('session_id', session_id).eq('user_id', user_id).execute()

    return {"activities": result.data}


# ─────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────

@router.post("/cleanup/orphaned")
def cleanup_orphaned_sessions(user_id: str = Depends(get_current_user_id)):
    """Clean up any orphaned (not ended) sessions for the current user"""
    supabase = get_supabase()

    # Find any sessions without end_time
    orphaned = supabase.table('focus_sessions').select("*").eq('user_id', user_id).is_('end_time', 'null').execute()

    if not orphaned.data:
        return {"message": "No orphaned sessions found"}

    # End all orphaned sessions
    for session in orphaned.data:
        supabase.table('focus_sessions').update({
            'end_time': datetime.now(timezone.utc).isoformat(),
            'duration_minutes': 0
        }).eq('id', session['id']).execute()

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
    supabase = get_supabase()

    # Get only completed sessions (with end_time and duration > 0)
    sessions_result = supabase.table('focus_sessions').select("*").eq('user_id', user_id).not_.is_('end_time', 'null').gt('duration_minutes', 0).order('start_time', desc=True).range(offset, offset + limit - 1).execute()

    sessions = sessions_result.data

    # For each session, get activities
    detailed_sessions = []

    for session in sessions:
        session_id = session['id']

        # Get activities for this session
        activities_result = supabase.table('browsing_activity').select("*").eq('session_id', session_id).execute()

        activities = activities_result.data

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
    supabase = get_supabase()

    # Get all completed sessions
    result = supabase.table('focus_sessions').select("*").eq('user_id', user_id).not_.is_('end_time', 'null').execute()

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