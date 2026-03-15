# app/routes/agent.py
"""
Agent endpoints - control and monitor the agent.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from app.auth import get_current_user_id
from app.database import get_supabase
from app.ml.agent.orchestrator import orchestrator
from datetime import datetime, timedelta

router = APIRouter(prefix="/agent", tags=["Agent"])


def _get_persisted_cycle_count(supabase, user_id: str) -> int:
    result = (
        supabase.table('agent_events')
        .select('id')
        .eq('user_id', user_id)
        .eq('event_type', 'monitoring_cycle')
        .execute()
    )
    return len(result.data or [])


def _normalize_persisted_state(raw_state):
    if isinstance(raw_state, str) and raw_state:
        return raw_state
    return 'idle'


@router.get("/status")
def get_agent_status(user_id: str = Depends(get_current_user_id)):
    """Get current agent status for the user."""
    agent = orchestrator.get_agent(user_id)

    if not agent:
        # Agent not yet created - check DB for last known state
        supabase = get_supabase()
        result = (
            supabase.table('agent_state')
            .select("*")
            .eq('user_id', user_id)
            .execute()
        )

        if result.data:
            db_state = result.data[0]
            cycle_count = db_state.get('cycle_count')
            if cycle_count is None:
                cycle_count = _get_persisted_cycle_count(supabase, user_id)

            return {
                'state': _normalize_persisted_state(db_state.get('state')),
                'risk_score': db_state.get('risk_score', 0),
                'last_cycle': db_state.get('last_cycle'),
                'cycle_count': cycle_count,
                'agent_active': False,
                'orchestrator_running': orchestrator.is_running,
            }

        return {
            'state': 'idle',
            'risk_score': 0,
            'last_cycle': None,
            'cycle_count': 0,
            'agent_active': False,
            'orchestrator_running': orchestrator.is_running,
        }

    status = agent.get_status()
    status['agent_active'] = True
    status['orchestrator_running'] = orchestrator.is_running
    return status


@router.post("/cycle")
def trigger_cycle(user_id: str = Depends(get_current_user_id)):
    """
    Manually trigger one monitoring cycle.
    Useful for testing and immediate assessment.
    """
    result = orchestrator.run_cycle_for_user(user_id)
    return {
        'message': 'Cycle completed',
        'result': result,
    }


@router.post("/pause")
def pause_agent(user_id: str = Depends(get_current_user_id)):
    """Pause the agent for this user."""
    orchestrator.pause_agent(user_id)
    return {'message': 'Agent paused', 'state': 'paused'}


@router.post("/resume")
def resume_agent(user_id: str = Depends(get_current_user_id)):
    """Resume the agent for this user."""
    orchestrator.resume_agent(user_id)
    return {'message': 'Agent resumed', 'state': 'idle'}


@router.get("/events")
def get_agent_events(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id),
):
    """Get recent agent events for the user."""
    supabase = get_supabase()

    result = (
        supabase.table('agent_events')
        .select("*")
        .eq('user_id', user_id)
        .order('created_at', desc=True)
        .limit(limit)
        .execute()
    )

    return {
        'events': result.data or [],
        'total': len(result.data or []),
    }


@router.get("/interventions")
def get_interventions(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id),
):
    """Get intervention history for the user."""
    supabase = get_supabase()

    result = (
        supabase.table('agent_interventions')
        .select("*")
        .eq('user_id', user_id)
        .order('created_at', desc=True)
        .limit(limit)
        .execute()
    )

    return {
        'interventions': result.data or [],
        'total': len(result.data or []),
    }


@router.get("/notifications")
def get_notifications(
    unread_only: bool = True,
    user_id: str = Depends(get_current_user_id),
):
    """Get pending notifications for the user."""
    supabase = get_supabase()

    query = (
        supabase.table('notification_queue')
        .select("*")
        .eq('user_id', user_id)
        .order('created_at', desc=True)
        .limit(10)
    )

    if unread_only:
        query = query.eq('read', False)

    result = query.execute()

    return {
        'notifications': result.data or [],
        'unread_count': len(result.data or []),
    }


@router.post("/notifications/mark-read")
def mark_notifications_read(user_id: str = Depends(get_current_user_id)):
    """Mark all notifications as read."""
    supabase = get_supabase()

    supabase.table('notification_queue').update(
        {'read': True}
    ).eq('user_id', user_id).eq('read', False).execute()

    return {'message': 'All notifications marked as read'}
