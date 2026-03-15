# app/ml/agent/alert_system.py
"""
Alert System — sends notifications and logs interventions.

The alert system is the OUTPUT layer of the agent.
It decides HOW to communicate risk to the user.

Alert types:
    WARNING     → Risk is rising. Gentle nudge.
    INTERVENTION → Risk is critical. Strong action.
    RECOVERY    → Risk dropped. Positive reinforcement.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from app.database import get_supabase


class AlertSystem:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    # ── Alert types ────────────────────────────────────────────────────

    def send_warning(
        self,
        risk_score: float,
        signals: List[str]
    ) -> Dict:
        """
        Send a gentle warning when risk is rising.
        Risk level: medium-high (0.60 - 0.74)
        """
        message = self._build_warning_message(risk_score, signals)

        alert = {
            'type':       'warning',
            'title':      '⚠️ Focus Risk Detected',
            'message':    message,
            'risk_score': risk_score,
            'signals':    signals,
            'sent_at':    datetime.utcnow().isoformat()
        }

        self._log_alert(alert)
        self._push_to_notification_queue(alert)

        print(f"   ⚠️  Warning sent: {message[:60]}...")
        return alert

    def send_intervention(
        self,
        risk_score: float,
        signals: List[str],
        observation: Dict
    ) -> Dict:
        """
        Send a strong intervention when risk is critical.
        Risk level: critical (>= 0.75)
        """
        message       = self._build_intervention_message(risk_score, signals)
        intervention_type = self._choose_intervention_type(observation)

        alert = {
            'type':              'intervention',
            'title':             '🚨 Procrastination Detected',
            'message':           message,
            'risk_score':        risk_score,
            'signals':           signals,
            'intervention_type': intervention_type,
            'sent_at':           datetime.utcnow().isoformat()
        }

        self._log_alert(alert)
        self._log_intervention(alert)
        self._push_to_notification_queue(alert)

        print(f"   🚨 Intervention: {intervention_type} | "
              f"Risk={risk_score:.2f}")
        return alert

    def send_recovery(self, risk_score: float) -> Dict:
        """
        Send positive reinforcement when user recovers focus.
        """
        messages = [
            "Great job refocusing! Keep it up! 💪",
            "You got back on track. That's what matters! ✅",
            "Focus restored. You're doing great! 🎯",
            "Nice recovery! Stay in the zone! 🔥"
        ]

        import random
        message = random.choice(messages)

        alert = {
            'type':       'recovery',
            'title':      '✅ Focus Restored',
            'message':    message,
            'risk_score': risk_score,
            'sent_at':    datetime.utcnow().isoformat()
        }

        self._log_alert(alert)
        self._push_to_notification_queue(alert)

        print(f"   ✅ Recovery sent")
        return alert

    # ── Message builders ───────────────────────────────────────────────

    def _build_warning_message(
        self,
        risk_score: float,
        signals: List[str]
    ) -> str:
        pct = round(risk_score * 100)

        if signals:
            top_signal = signals[0]
            return (
                f"Your focus risk is {pct}%. "
                f"{top_signal}. "
                f"Consider refocusing on your task."
            )
        return (
            f"Your focus risk is {pct}%. "
            f"Stay on track!"
        )

    def _build_intervention_message(
        self,
        risk_score: float,
        signals: List[str]
    ) -> str:
        pct = round(risk_score * 100)

        if len(signals) >= 2:
            return (
                f"High procrastination risk ({pct}%). "
                f"{signals[0]}. "
                f"Take a 2-minute break then return to your task."
            )
        return (
            f"Procrastination risk is {pct}%. "
            f"Time to refocus. Close distracting tabs and restart."
        )

    def _choose_intervention_type(
        self,
        observation: Dict
    ) -> str:
        """
        Choose the best intervention type based on context.

        Types:
        - focus_reminder:   Simple reminder to refocus
        - break_suggestion: Suggest a short break
        - site_block:       Trigger emergency site blocking
        - session_restart:  Suggest ending and restarting session
        """
        metrics = observation.get('session_metrics', {})
        elapsed = metrics.get('elapsed_minutes', 0)

        # If very early in session and already distracted
        if elapsed < 10:
            return 'focus_reminder'

        # If high distraction ratio
        if metrics.get('recent_distraction_ratio', 0) > 0.7:
            return 'site_block'

        # If session has been going a long time
        if elapsed > 60:
            return 'break_suggestion'

        return 'focus_reminder'

    # ── Persistence ────────────────────────────────────────────────────

    def _log_alert(self, alert: Dict):
        """Log alert to agent_events table."""
        try:
            self.supabase.table('agent_events').insert({
                'user_id':    self.user_id,
                'event_type': f"alert_{alert['type']}",
                'event_data': alert
            }).execute()
        except Exception as e:
            print(f"⚠️  Alert log error: {e}")

    def _log_intervention(self, alert: Dict):
        """Log intervention to agent_interventions table."""
        try:
            self.supabase.table('agent_interventions').insert({
                'user_id':               self.user_id,
                'intervention_type':     alert.get('intervention_type'),
                'trigger_reason':        ' | '.join(alert.get('signals', [])),
                'risk_score_at_trigger': alert.get('risk_score')
            }).execute()
        except Exception as e:
            print(f"⚠️  Intervention log error: {e}")

    def _push_to_notification_queue(self, alert: Dict):
        """
        Push alert to notification queue in database.
        The frontend polls this to show browser notifications.
        """
        try:
            self.supabase.table('notification_queue').insert({
                'user_id':   self.user_id,
                'title':     alert['title'],
                'message':   alert['message'],
                'type':      alert['type'],
                'read':      False,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            print(f"⚠️  Notification queue error: {e}")
