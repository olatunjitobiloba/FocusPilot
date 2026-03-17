# app/routes/pipeline.py
"""
Pipeline endpoints — unified view of the full agent system.
"""

from fastapi import APIRouter, Depends
from app.auth import get_current_user_id
from app.database import get_supabase
from app.ml.agent.orchestrator import orchestrator
from app.ml.agent.executors    import SiteBlockExecutor
from app.ml.model_manager      import model_manager
from datetime import datetime

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


def _degraded_health_payload(error_message: str | None = None):
    payload = {
        'overall_status': 'degraded',
        'components': {
            'orchestrator': {
                'status': 'healthy' if orchestrator.is_running else 'down',
                'description': 'Running — checking users every 60s' if orchestrator.is_running else 'Not running — restart backend'
            },
            'ml_model': {
                'status': 'degraded',
                'description': 'Status unavailable (temporary backend issue)'
            },
            'active_session': {
                'status': 'degraded',
                'description': 'Status unavailable (temporary backend issue)'
            },
            'site_blocker': {
                'status': 'degraded',
                'description': 'Status unavailable (temporary backend issue)'
            }
        },
        'agent_state': 'unknown',
        'last_risk_score': None,
        'last_cycle': None,
        'today': {
            'interventions': 0,
            'successful_interventions': 0,
            'autonomous_actions': 0,
            'completed_actions': 0,
        },
        'checked_at': datetime.utcnow().isoformat(),
    }
    if error_message:
        payload['error'] = error_message
    return payload


def _degraded_summary_payload(error_message: str | None = None):
    payload = {
        'risk_timeline': [],
        'avg_risk_today': 0,
        'peak_risk_today': 0,
        'events_today': [],
        'interventions': [],
        'actions': [],
        'total_cycles': 0,
        'status': 'degraded',
        'summary_at': datetime.utcnow().isoformat(),
    }
    if error_message:
        payload['error'] = error_message
    return payload


@router.get("/health")
def get_pipeline_health(user_id: str = Depends(get_current_user_id)):
    """
    Full system health check.
    Shows status of every component in the pipeline.
    """
    try:
        supabase = get_supabase()

        # ── Check each component ───────────────────────────────────────────

        # 1. Orchestrator
        orchestrator_ok = orchestrator.is_running

        # 2. ML Model
        model_ok = model_manager.has_model(user_id)

        # 3. Active session
        session_result = (
            supabase.table('focus_sessions')
            .select("id, start_time")
            .eq('user_id', user_id)
            .is_('end_time', 'null')
            .execute()
        )
        has_active_session = bool(session_result.data)

        # 4. Agent state
        state_result = (
            supabase.table('agent_state')
            .select("*")
            .eq('user_id', user_id)
            .execute()
        )
        agent_state = state_result.data[0] if state_result.data else {}

        # 5. Recent cycles
        events_result = (
            supabase.table('agent_events')
            .select("created_at")
            .eq('user_id', user_id)
            .eq('event_type', 'pipeline_cycle')
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )
        last_cycle = (
            events_result.data[0]['created_at']
            if events_result.data else None
        )

        # 6. Block state
        blocker     = SiteBlockExecutor(user_id)
        block_state = blocker.get_block_state()

        # 7. Today's stats
        today = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        interventions_result = (
            supabase.table('agent_interventions')
            .select("id, outcome")
            .eq('user_id', user_id)
            .gte('created_at', today)
            .execute()
        )
        interventions_today = interventions_result.data or []

        actions_result = (
            supabase.table('agent_actions')
            .select("id, status")
            .eq('user_id', user_id)
            .gte('created_at', today)
            .execute()
        )
        actions_today = actions_result.data or []

    # ── Build health report ────────────────────────────────────────────

        components = {
            'orchestrator': {
                'status':      'healthy' if orchestrator_ok else 'down',
                'description': (
                    'Running — checking users every 60s'
                    if orchestrator_ok
                    else 'Not running — restart backend'
                )
            },
            'ml_model': {
                'status':      'healthy' if model_ok else 'not_trained',
                'description': (
                    'Model trained and ready'
                    if model_ok
                    else 'No model yet — complete 5+ sessions then train'
                )
            },
            'active_session': {
                'status':      'active' if has_active_session else 'idle',
                'description': (
                    'Session in progress — agent is monitoring'
                    if has_active_session
                    else 'No active session'
                )
            },
            'site_blocker': {
                'status':      'blocking' if block_state.get('is_blocked') else 'idle',
                'description': (
                    f"Blocking {len(block_state.get('blocked_domains', []))} sites"
                    if block_state.get('is_blocked')
                    else 'No active blocks'
                )
            }
        }

        overall_healthy = orchestrator_ok

        return {
            'overall_status':   'healthy' if overall_healthy else 'degraded',
            'components':       components,
            'agent_state':      agent_state.get('state', 'idle'),
            'last_risk_score':  agent_state.get('risk_score'),
            'last_cycle':       last_cycle,
            'today': {
                'interventions':           len(interventions_today),
                'successful_interventions': sum(
                    1 for i in interventions_today
                    if i.get('outcome') == 'success'
                ),
                'autonomous_actions': len(actions_today),
                'completed_actions':  sum(
                    1 for a in actions_today
                    if a.get('status') == 'completed'
                )
            },
            'checked_at': datetime.utcnow().isoformat()
        }
    except Exception as exc:
        return _degraded_health_payload(str(exc))


@router.get("/summary")
def get_pipeline_summary(user_id: str = Depends(get_current_user_id)):
    """
    Today's agent activity summary.
    Used by the Agent Dashboard.
    """
    try:
        supabase = get_supabase()
        today    = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        # Risk history today
        risk_result = (
            supabase.table('risk_history')
            .select("risk_score, assessed_at")
            .eq('user_id', user_id)
            .gte('assessed_at', today)
            .order('assessed_at', desc=False)
            .execute()
        )
        risk_history = risk_result.data or []

        # Events today
        events_result = (
            supabase.table('agent_events')
            .select("event_type, event_data, created_at, state_after")
            .eq('user_id', user_id)
            .gte('created_at', today)
            .order('created_at', desc=True)
            .limit(50)
            .execute()
        )
        events_today = events_result.data or []

        # Interventions today
        iv_result = (
            supabase.table('agent_interventions')
            .select("*")
            .eq('user_id', user_id)
            .gte('created_at', today)
            .execute()
        )
        interventions = iv_result.data or []

        # Actions today
        actions_result = (
            supabase.table('agent_actions')
            .select("*")
            .eq('user_id', user_id)
            .gte('created_at', today)
            .execute()
        )
        actions = actions_result.data or []

        # Compute stats
        avg_risk = (
            sum(r['risk_score'] for r in risk_history) / len(risk_history)
            if risk_history else 0
        )
        peak_risk = (
            max(r['risk_score'] for r in risk_history)
            if risk_history else 0
        )

        return {
            'risk_timeline':     risk_history,
            'avg_risk_today':    round(avg_risk, 3),
            'peak_risk_today':   round(peak_risk, 3),
            'events_today':      events_today,
            'interventions':     interventions,
            'actions':           actions,
            'total_cycles':      len([
                e for e in events_today
                if e['event_type'] == 'pipeline_cycle'
            ]),
            'summary_at':        datetime.utcnow().isoformat()
        }
    except Exception as exc:
        return _degraded_summary_payload(str(exc))


@router.post("/run")
def run_pipeline_now(user_id: str = Depends(get_current_user_id)):
    """
    Manually trigger one full pipeline cycle.
    Runs observe → assess → decide → execute.
    """
    result = orchestrator.run_cycle_for_user(user_id)
    return {
        'message': 'Pipeline cycle complete',
        'result':  result
    }
