# app/ml/agent/assessor.py
"""
Assessor — scores the current observation and determines risk level.

The assessor answers: "How likely is the user to procrastinate?"

It combines:
1. ML model prediction (Random Forest from Day 9)
2. Real-time behavioral signals (from Observer)
3. Rule-based overrides (for obvious cases)
"""

from typing import Dict, Any
from datetime import datetime
from app.ml.model_manager  import model_manager
from app.ml.dataset_builder import DatasetBuilder
from app.ml.agent.states   import (
    AgentState,
    RISK_THRESHOLD_AT_RISK,
    RISK_THRESHOLD_INTERVENING,
    RISK_THRESHOLD_RECOVERY
)


class Assessor:

    def __init__(self, user_id: str):
        self.user_id = user_id

    def assess(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess procrastination risk from observation.

        Args:
            observation: Output from Observer.observe()

        Returns:
            Assessment dict with risk_score, recommended_state, signals
        """
        signals    = []
        risk_score = 0.30   # Default: low risk

        # ── No active session → IDLE ───────────────────────────────────
        if not observation.get('active_session'):
            return {
                'risk_score':          0.0,
                'risk_level':          'none',
                'recommended_state':   AgentState.IDLE,
                'signals':             ['No active session'],
                'ml_score':            None,
                'rule_overrides':      [],
                'assessed_at':         datetime.utcnow().isoformat()
            }

        metrics = observation.get('session_metrics', {})

        # ── Rule-based signals (fast, no ML needed) ────────────────────

        rule_overrides = []

        # Signal 1: Currently on a distraction site
        if metrics.get('is_on_distraction_site'):
            domain = metrics.get('last_domain', 'unknown')
            signals.append(f"Currently on {domain}")
            risk_score += 0.25
            rule_overrides.append({
                'rule':   'active_distraction',
                'impact': +0.25,
                'reason': f"On {domain} right now"
            })

        # Signal 2: High recent distraction ratio
        recent_ratio = metrics.get('recent_distraction_ratio', 0)
        if recent_ratio > 0.5:
            pct = round(recent_ratio * 100)
            signals.append(f"{pct}% of last 10 min on distracting sites")
            risk_score += 0.20
            rule_overrides.append({
                'rule':   'high_recent_distraction',
                'impact': +0.20,
                'reason': f"{pct}% distraction in last 10 minutes"
            })

        # Signal 3: Session very short (< 5 minutes) with distractions
        elapsed = metrics.get('elapsed_minutes', 0)
        if elapsed < 5 and metrics.get('recent_distraction_count', 0) > 0:
            signals.append("Distracted within first 5 minutes")
            risk_score += 0.15
            rule_overrides.append({
                'rule':   'early_distraction',
                'impact': +0.15,
                'reason': "Distracted in first 5 minutes of session"
            })

        # Signal 4: Low historical focus at this hour
        context = observation.get('context', {})
        if context.get('avg_focus_score_week', 10) < 4:
            signals.append("Historically low focus this week")
            risk_score += 0.10
            rule_overrides.append({
                'rule':   'low_historical_focus',
                'impact': +0.10,
                'reason': "Average focus score below 4 this week"
            })

        # ── ML model prediction ────────────────────────────────────────
        ml_score = self._get_ml_score(observation)

        if ml_score is not None:
            # Blend rule-based (40%) with ML (60%)
            risk_score = (risk_score * 0.40) + (ml_score * 0.60)
            signals.append(f"ML model: {round(ml_score * 100)}% risk")
        else:
            # No ML model yet — rely on rules only
            signals.append("ML model not trained yet (using rules only)")

        # Clamp to [0, 1]
        risk_score = max(0.0, min(1.0, risk_score))

        # ── Determine recommended state ────────────────────────────────
        if risk_score >= RISK_THRESHOLD_INTERVENING:
            recommended_state = AgentState.INTERVENING
        elif risk_score >= RISK_THRESHOLD_AT_RISK:
            recommended_state = AgentState.AT_RISK
        else:
            recommended_state = AgentState.ACTIVE

        # ── Risk level label ───────────────────────────────────────────
        if risk_score >= 0.75:
            risk_level = 'critical'
        elif risk_score >= 0.60:
            risk_level = 'high'
        elif risk_score >= 0.40:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'risk_score':        round(risk_score, 4),
            'risk_level':        risk_level,
            'recommended_state': recommended_state,
            'signals':           signals,
            'ml_score':          ml_score,
            'rule_overrides':    rule_overrides,
            'assessed_at':       datetime.utcnow().isoformat()
        }

    def _get_ml_score(
        self,
        observation: Dict
    ) -> float | None:
        """
        Get risk score from trained ML model.
        Returns None if model not available.
        """
        if not model_manager.has_model(self.user_id):
            return None

        try:
            session = observation.get('active_session', {})
            if not session:
                return None

            builder = DatasetBuilder(
                user_id=self.user_id,
                days_back=30
            )
            X = builder.build_inference_row(session)

            prediction = model_manager.predict(self.user_id, X)
            return prediction.get('risk_score')

        except Exception as e:
            print(f"WARNING ML assessment error: {e}")
            return None
