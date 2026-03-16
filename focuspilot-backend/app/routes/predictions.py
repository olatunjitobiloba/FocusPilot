# app/routes/predictions.py
"""
Prediction endpoints — real-time procrastination risk scoring.

Endpoints:
- POST /predictions/train         — Train model for current user
- GET  /predictions/risk          — Get current risk score
- GET  /predictions/model-status  — Check if model is trained
- GET  /predictions/feature-importance — What drives predictions
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from app.auth import get_current_user_id
from app.database import get_supabase, upsert_agent_state
from app.ml.training_pipeline import TrainingPipeline
from app.ml.model_manager     import model_manager
from app.ml.dataset_builder   import DatasetBuilder
from app.ml.preprocessor      import Preprocessor
from typing import Dict, List
from datetime import datetime
import json
import os

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _risk_level_from_score(score: float) -> str:
    if score >= 0.75:
        return 'critical'
    if score >= 0.60:
        return 'high'
    if score >= 0.40:
        return 'medium'
    return 'low'


def _get_latest_agent_risk(user_id: str, supabase) -> float | None:
    try:
        result = (
            supabase.table('agent_state')
            .select('risk_score')
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )
        if result.data:
            risk = result.data[0].get('risk_score')
            if isinstance(risk, (int, float)):
                return float(risk)
    except Exception as exc:
        print(f"WARNING Agent risk lookup error: {exc}")
    return None


# ── Train ──────────────────────────────────────────────────────────────

@router.post("/train")
def train_model(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Trigger model training for the current user.
    Runs in background — returns immediately.
    Poll /predictions/model-status to check when done.
    """
    def _train():
        pipeline = TrainingPipeline(user_id=user_id)
        result   = pipeline.run()

        # Invalidate cache so new model is loaded
        model_manager.invalidate(user_id)

        # Save training result to Supabase
        supabase = get_supabase()
        upsert_agent_state({
            'user_id':       user_id,
            'last_trained':  datetime.utcnow().isoformat(),
            'model_metrics': result.get('metrics', {}),
            'training_result': result
        })

        if result['success']:
            print(f"Training complete for {user_id[:8]}: "
                  f"accuracy={result['metrics']['accuracy']:.1%}")
        else:
            print(f"WARNING Training failed for {user_id[:8]}: "
                  f"{result.get('message')}")

    background_tasks.add_task(_train)

    return {
        'message': 'Model training started',
        'status':  'training',
        'note':    'Poll /predictions/model-status to check progress'
    }


@router.post("/train/sync")
def train_model_sync(user_id: str = Depends(get_current_user_id)):
    """
    Train model synchronously (waits for completion).
    Use this for testing. Use /train for production.
    """
    pipeline = TrainingPipeline(user_id=user_id)

    try:
        result = pipeline.run()
    except Exception as exc:
        print(f"WARNING Training sync error for {user_id[:8]}: {exc}")
        raise HTTPException(
            status_code=422,
            detail=f"Training failed: {exc}"
        )

    if not result.get('success', False):
        raise HTTPException(
            status_code=422,
            detail=result.get('message', 'Training failed')
        )

    if result['success']:
        model_manager.invalidate(user_id)

    return result


# ── Model Status ───────────────────────────────────────────────────────

@router.get("/model-status")
def get_model_status(user_id: str = Depends(get_current_user_id)):
    """
    Check if a trained model exists for this user.
    Also returns training metrics if available.
    """
    has_model  = model_manager.has_model(user_id)
    user_key   = user_id[:8]
    meta_path  = f"app/ml/models/{user_key}/model_meta.json"

    if not has_model:
        # Check data readiness
        from app.ml.data_extractor import DataExtractor
        extractor    = DataExtractor(user_id)
        data_summary = extractor.get_data_summary()

        return {
            'model_trained':   False,
            'data_summary':    data_summary,
            'can_train':       data_summary['has_enough_data'],
            'message': (
                'Ready to train! Call POST /predictions/train'
                if data_summary['has_enough_data']
                else f"Need {max(0, 5 - data_summary['completed_sessions'])} "
                     f"more sessions before training"
            )
        }

    # Load metadata
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)

    return {
        'model_trained':      True,
        'trained_at':         meta.get('trained_at'),
        'training_samples':   meta.get('n_samples'),
        'feature_importance': meta.get('feature_importance', [])[:5],
        'message':            'Model is ready for predictions'
    }


# ── Real-time Risk Score ───────────────────────────────────────────────

@router.get("/risk")
def get_current_risk(user_id: str = Depends(get_current_user_id)):
    """
    Get the user's CURRENT procrastination risk score.

    This is the core prediction endpoint.
    The agent calls this every minute to monitor the user.

    Returns:
        risk_score:       0.0 to 1.0
        risk_percentage:  0 to 100
        risk_level:       low / medium / high / critical
        will_procrastinate: True/False
        top_risk_factors: What's driving the risk
    """
    supabase = get_supabase()
    agent_risk = _get_latest_agent_risk(user_id, supabase)

    # Check if model exists
    if not model_manager.has_model(user_id):
        fallback_risk = agent_risk if agent_risk is not None else 0.3
        return {
            'risk_score':         round(fallback_risk, 4),
            'risk_percentage':    round(fallback_risk * 100),
            'risk_level':         _risk_level_from_score(fallback_risk),
            'will_procrastinate': fallback_risk >= 0.60,
            'model_available':    False,
            'message':            (
                'Using live agent risk (model not trained yet)'
                if agent_risk is not None
                else 'Train model first via POST /predictions/train'
            )
        }

    # Build current feature row
    builder = DatasetBuilder(user_id=user_id, days_back=30)

    # Get current active session (if any)
    active_result = (
        supabase.table('focus_sessions')
        .select("*")
        .eq('user_id', user_id)
        .is_('end_time', 'null')
        .execute()
    )

    # Build a "virtual" current session for prediction
    current_session = None

    if active_result.data:
        current_session = active_result.data[0]
    else:
        # No active session — create virtual session at current time
        current_session = {
            'id':         'virtual',
            'user_id':    user_id,
            'start_time': datetime.utcnow().isoformat(),
            'end_time':   None,
            'duration_minutes': 0,
            'focus_score': None,
            'activities': []
        }

    # Build inference feature row
    try:
        X = builder.build_inference_row(current_session)
    except Exception as e:
        print(f"WARNING Feature build error: {e}")
        return {
            'risk_score':      0.3,
            'risk_percentage': 30,
            'risk_level':      'low',
            'error':           str(e)
        }

    # Get prediction
    prediction = model_manager.predict(user_id, X)

    if agent_risk is not None and agent_risk > prediction.get('risk_score', 0):
        merged_risk = max(0.0, min(1.0, float(agent_risk)))
        prediction['risk_score'] = round(merged_risk, 4)
        prediction['risk_percentage'] = round(merged_risk * 100)
        prediction['risk_level'] = _risk_level_from_score(merged_risk)
        prediction['will_procrastinate'] = merged_risk >= 0.60
        prediction['message'] = 'Live agent risk applied'

    # Get top risk factors
    top_factors = _get_top_risk_factors(user_id, current_session)

    # Update agent state in database
    _update_agent_risk_state(user_id, prediction['risk_score'], supabase)

    return {
        **prediction,
        'top_risk_factors': top_factors,
        'assessed_at':      datetime.utcnow().isoformat()
    }


@router.get("/risk/history")
def get_risk_history(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get historical risk scores for the user.
    Used to show risk trend on dashboard.
    """
    supabase = get_supabase()

    result = (
        supabase.table('risk_history')
        .select("*")
        .eq('user_id', user_id)
        .order('assessed_at', desc=True)
        .limit(limit)
        .execute()
    )

    return {
        'history': result.data or [],
        'total':   len(result.data or [])
    }


# ── Feature Importance ─────────────────────────────────────────────────

@router.get("/feature-importance")
def get_feature_importance(user_id: str = Depends(get_current_user_id)):
    """
    Return which features drive procrastination predictions most.
    Used for explainability UI.
    """
    user_key  = user_id[:8]
    meta_path = f"app/ml/models/{user_key}/model_meta.json"

    if not os.path.exists(meta_path):
        raise HTTPException(
            status_code=404,
            detail="Model not trained yet"
        )

    with open(meta_path, 'r') as f:
        meta = json.load(f)

    importance = meta.get('feature_importance', [])

    # Add human-readable descriptions
    descriptions = {
        'distraction_ratio':      'Time spent on distracting sites',
        'avg_focus_score_last3':  'Your recent focus performance',
        'hour_of_day':            'Time of day you are studying',
        'distraction_count':      'Number of distraction site visits',
        'days_since_last_session':'Days since you last studied',
        'streak_days':            'Your current study streak',
        'session_duration_mins':  'How long your sessions last',
        'is_night':               'Whether you study late at night',
        'abandoned_early':        'Whether you quit sessions early',
        'same_hour_avg_score':    'Your historical score at this hour',
        'sessions_today':         'Sessions completed today',
        'avg_duration_last7':     'Average session length this week',
        'peak_distraction_mins':  'Longest single distraction visit',
        'is_weekend':             'Whether it is a weekend',
        'day_of_week':            'Day of the week'
    }

    for item in importance:
        item['description'] = descriptions.get(
            item['feature'],
            item['feature']
        )

    return {
        'feature_importance': importance,
        'top_3': importance[:3]
    }


# ── Private helpers ────────────────────────────────────────────────────

def _get_top_risk_factors(
    user_id: str,
    session: Dict
) -> List[Dict]:
    """
    Identify the top factors contributing to current risk.
    Returns human-readable explanations.
    """
    from app.ml.feature_engineer import FeatureEngineer, DISTRACTION_DOMAINS
    from app.ml.data_extractor   import DataExtractor

    factors = []

    try:
        extractor     = DataExtractor(user_id)
        past_sessions = extractor.get_sessions(days_back=30, completed_only=True)
        engineer      = FeatureEngineer()

        all_sessions  = past_sessions + [session]
        feature_rows  = engineer.build_feature_matrix(all_sessions)

        if not feature_rows:
            return []

        current = feature_rows[-1]

        # Check each risk factor
        if current.get('distraction_ratio', 0) > 0.4:
            pct = round(current['distraction_ratio'] * 100)
            factors.append({
                'factor':  'High distraction ratio',
                'value':   f"{pct}% of session time on distracting sites",
                'severity': 'high' if pct > 60 else 'medium'
            })

        if current.get('avg_focus_score_last3', 10) < 5:
            score = current['avg_focus_score_last3']
            factors.append({
                'factor':  'Low recent focus scores',
                'value':   f"Average score of {score}/10 in last 3 sessions",
                'severity': 'high'
            })

        if current.get('days_since_last_session', 0) > 2:
            days = current['days_since_last_session']
            factors.append({
                'factor':  'Study gap detected',
                'value':   f"{days} days since last session",
                'severity': 'medium'
            })

        if current.get('is_night', 0) == 1:
            factors.append({
                'factor':  'Late night studying',
                'value':   'Studying after 10 PM reduces focus quality',
                'severity': 'medium'
            })

        if current.get('streak_days', 0) == 0:
            factors.append({
                'factor':  'No active streak',
                'value':   'You have not studied consistently recently',
                'severity': 'low'
            })

    except Exception as e:
        print(f"WARNING Risk factor error: {e}")

    return factors[:3]  # Top 3 factors


def _update_agent_risk_state(
    user_id: str,
    risk_score: float,
    supabase
):
    """Save current risk score to agent state and history."""
    try:
        current_state = 'idle'
        state_result = (
            supabase.table('agent_state')
            .select('state')
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )
        if state_result.data and state_result.data[0].get('state'):
            current_state = state_result.data[0]['state']

        # Update agent state
        upsert_agent_state({
            'user_id':    user_id,
            'state':      current_state,
            'risk_score': risk_score,
            'last_cycle': datetime.utcnow().isoformat()
        })

        # Log to risk history
        supabase.table('risk_history').insert({
            'user_id':     user_id,
            'risk_score':  risk_score,
            'assessed_at': datetime.utcnow().isoformat()
        }).execute()

    except Exception as e:
        print(f"WARNING Agent state update error: {e}")

