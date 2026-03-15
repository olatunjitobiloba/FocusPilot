# app/ml/agent/decision_engine.py
"""
Decision Engine — the brain of the Decision Agent.

Given an assessment from the Monitoring Agent, it decides:
1. Should we intervene? (cooldown check)
2. What type of intervention? (context + history)
3. What message? (personalized)
4. Schedule outcome tracking

This is the most important class in the agent system.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List

from app.ml.agent.interventions    import (
    INTERVENTIONS, get_intervention, get_message
)
from app.ml.agent.cooldown         import CooldownManager
from app.ml.agent.history_analyzer import HistoryAnalyzer
from app.ml.agent.outcome_tracker  import OutcomeTracker
from app.ml.agent.states           import (
    AgentState,
    RISK_THRESHOLD_AT_RISK,
    RISK_THRESHOLD_INTERVENING
)
from app.database import get_supabase


class DecisionEngine:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.cooldown = CooldownManager(user_id)
        self.analyzer = HistoryAnalyzer(user_id)
        self.tracker  = OutcomeTracker(user_id)
        self.supabase = get_supabase()

    # ── Main decision method ───────────────────────────────────────────

    def decide(
        self,
        assessment: Dict[str, Any],
        observation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make an intervention decision.

        Args:
            assessment:  Output from Assessor.assess()
            observation: Output from Observer.observe()

        Returns:
            Decision dict with:
            - should_intervene: bool
            - intervention_type: str (if intervening)
            - message: str (if intervening)
            - reason: str
            - intervention_id: str (for outcome tracking)
        """
        risk_score = assessment.get('risk_score', 0)

        # ── Gate 1: Is risk high enough? ───────────────────────────────
        if risk_score < RISK_THRESHOLD_AT_RISK:
            return self._no_intervention(
                reason=f"Risk {risk_score:.2f} below threshold {RISK_THRESHOLD_AT_RISK}"
            )

        # ── Gate 2: Is cooldown active? ────────────────────────────────
        cooldown_check = self.cooldown.can_intervene()

        if not cooldown_check['allowed']:
            return self._no_intervention(
                reason=cooldown_check['reason']
            )

        # ── Gate 3: Is agent paused? ───────────────────────────────────
        agent_state = self._get_agent_state()
        if agent_state == AgentState.PAUSED.value:
            return self._no_intervention(reason="Agent is paused")

        # ── Choose intervention type ───────────────────────────────────
        iv_type = self._choose_intervention_type(
            risk_score=risk_score,
            assessment=assessment,
            observation=observation
        )

        # ── Build personalized message ─────────────────────────────────
        context = self._build_message_context(observation)
        message = get_message(iv_type, context)

        # ── Log the intervention ───────────────────────────────────────
        intervention_id = self._log_intervention(
            iv_type=iv_type,
            risk_score=risk_score,
            assessment=assessment
        )

        # ── Schedule outcome tracking ──────────────────────────────────
        self.tracker.schedule_outcome_check(
            intervention_id=intervention_id,
            risk_score_before=risk_score,
            intervention_type=iv_type
        )

        intervention = get_intervention(iv_type)

        print(
            f"   Decision: {iv_type} | "
            f"Risk={risk_score:.2f} | "
            f"Priority={intervention.priority}"
        )

        return {
            'should_intervene':  True,
            'intervention_type': iv_type,
            'intervention_name': intervention.name,
            'message':           message,
            'risk_score':        risk_score,
            'priority':          intervention.priority,
            'intervention_id':   intervention_id,
            'reason':            f"Risk {risk_score:.2f} >= threshold",
            'decided_at':        datetime.utcnow().isoformat()
        }

    # ── Intervention selection ─────────────────────────────────────────

    def _choose_intervention_type(
        self,
        risk_score: float,
        assessment: Dict,
        observation: Dict
    ) -> str:
        """
        Choose the best intervention type for this situation.

        Selection logic (in order of priority):
        1. Get all interventions valid for current risk/context
        2. Remove interventions that failed recently
        3. Use history to pick the one most likely to work
        4. Fall back to focus_reminder if nothing else fits
        """
        metrics = observation.get('session_metrics', {})
        elapsed = metrics.get('elapsed_minutes', 0)
        distraction_ratio = metrics.get('recent_distraction_ratio', 0)

        # ── Build candidate list ───────────────────────────────────────
        candidates = []

        for iv_id, iv in INTERVENTIONS.items():
            conditions = iv.conditions

            # Check risk threshold
            min_risk = conditions.get('min_risk', 0)
            max_risk = conditions.get('max_risk', 1.0)
            if not (min_risk <= risk_score <= max_risk):
                continue

            # Check elapsed time
            min_elapsed = conditions.get('min_elapsed', 0)
            if elapsed < min_elapsed:
                continue

            # Check distraction ratio
            min_dr = conditions.get('min_distraction_ratio', 0)
            if distraction_ratio < min_dr:
                continue

            candidates.append(iv_id)

        if not candidates:
            return 'focus_reminder'

        # ── Remove recently failed interventions ───────────────────────
        failed = self.cooldown.get_failed_interventions()
        filtered = [c for c in candidates if c not in failed]

        # If all candidates failed recently, use them anyway
        if not filtered:
            filtered = candidates

        # ── Use history to pick best ───────────────────────────────────
        return self.analyzer.get_best_intervention(filtered)

    # ── Context building ───────────────────────────────────────────────

    def _build_message_context(
        self,
        observation: Dict
    ) -> Dict[str, Any]:
        """
        Build context dict for message personalization.
        Fills in variables like {sessions_today}, {streak_days}.
        """
        context_data = observation.get('context', {})
        metrics      = observation.get('session_metrics', {})

        # Get streak from agent state
        streak = 0
        try:
            result = (
                self.supabase
                .table('agent_state')
                .select("state")
                .eq('user_id', self.user_id)
                .execute()
            )
            if result.data:
                state_data = result.data[0].get('state') or {}
                streak     = state_data.get('streak_days', 0)
        except Exception:
            pass

        # Count sessions today
        from datetime import date
        today = date.today().isoformat()
        try:
            result = (
                self.supabase
                .table('focus_sessions')
                .select("id")
                .eq('user_id', self.user_id)
                .gte('start_time', today)
                .not_.is_('end_time', 'null')
                .execute()
            )
            sessions_today = len(result.data or [])
        except Exception:
            sessions_today = 0

        return {
            'sessions_today': sessions_today,
            'streak_days':    streak,
            'elapsed_mins':   round(metrics.get('elapsed_minutes', 0)),
            'risk_pct':       round(
                observation.get('risk_score', 0.5) * 100
            )
        }

    # ── Helpers ────────────────────────────────────────────────────────

    def _no_intervention(self, reason: str) -> Dict:
        """Return a no-intervention decision."""
        return {
            'should_intervene': False,
            'reason':           reason,
            'decided_at':       datetime.utcnow().isoformat()
        }

    def _get_agent_state(self) -> str:
        """Get current agent state from DB."""
        try:
            result = (
                self.supabase
                .table('agent_state')
                .select("state")
                .eq('user_id', self.user_id)
                .execute()
            )
            if result.data:
                return result.data[0].get('state', 'idle')
        except Exception:
            pass
        return 'idle'

    def _log_intervention(
        self,
        iv_type: str,
        risk_score: float,
        assessment: Dict
    ) -> str:
        """Log intervention to DB and return its ID."""
        try:
            signals = ' | '.join(assessment.get('signals', []))

            result = (
                self.supabase
                .table('agent_interventions')
                .insert({
                    'user_id':               self.user_id,
                    'intervention_type':     iv_type,
                    'trigger_reason':        signals,
                    'risk_score_at_trigger': risk_score,
                    'outcome':               'pending'
                })
                .execute()
            )

            if result.data:
                return result.data[0]['id']

        except Exception as e:
            print(f"WARNING Intervention log error: {e}")

        return 'unknown'
