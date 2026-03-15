# app/routes/decisions.py
"""
Decision endpoints — expose decision engine via API.
"""

from fastapi import APIRouter, Depends
from app.auth import get_current_user_id
from app.ml.agent.decision_engine import DecisionEngine
from app.ml.agent.outcome_tracker import OutcomeTracker
from app.ml.agent.interventions   import list_interventions
from app.ml.agent.orchestrator    import orchestrator

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.post("/decide")
def make_decision(user_id: str = Depends(get_current_user_id)):
    """
    Manually trigger a decision cycle.
    Runs observe → assess → decide and returns result.
    """
    from app.ml.agent.observer import Observer
    from app.ml.agent.assessor import Assessor

    observer = Observer(user_id)
    assessor = Assessor(user_id)
    engine   = DecisionEngine(user_id)

    observation = observer.observe()
    assessment  = assessor.assess(observation)
    decision    = engine.decide(assessment, observation)

    return {
        'observation': {
            'has_active_session': bool(observation.get('active_session')),
            'session_metrics':    observation.get('session_metrics', {})
        },
        'assessment': assessment,
        'decision':   decision
    }


@router.get("/outcome-stats")
def get_outcome_stats(user_id: str = Depends(get_current_user_id)):
    """Get intervention effectiveness statistics."""
    tracker = OutcomeTracker(user_id)
    return tracker.get_outcome_stats()


@router.get("/user-profile")
def get_user_profile(user_id: str = Depends(get_current_user_id)):
    """Get learned user behavior profile."""
    from app.ml.agent.history_analyzer import HistoryAnalyzer
    analyzer = HistoryAnalyzer(user_id)
    return analyzer.get_user_profile()


@router.get("/interventions")
def get_available_interventions():
    """List all available intervention types."""
    return {
        'interventions': list_interventions(),
        'total':         len(list_interventions())
    }


@router.post("/outcome/{intervention_id}")
def record_outcome(
    intervention_id: str,
    outcome: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually record an intervention outcome.
    Used when user clicks 'I refocused' or 'Dismiss' in the UI.

    outcome: 'success' | 'ignored' | 'partial'
    """
    from app.database import get_supabase
    from datetime import datetime

    supabase = get_supabase()

    supabase.table('agent_interventions').update({
        'outcome':     outcome,
        'resolved_at': datetime.utcnow().isoformat()
    }).eq('id', intervention_id).eq('user_id', user_id).execute()

    # Also record in outcomes table
    supabase.table('intervention_outcomes').insert({
        'user_id':           user_id,
        'intervention_type': 'manual_feedback',
        'outcome':           outcome
    }).execute()

    return {
        'message': f'Outcome recorded: {outcome}',
        'intervention_id': intervention_id
    }
