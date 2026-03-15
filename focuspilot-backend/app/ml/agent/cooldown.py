# app/ml/agent/cooldown.py
"""
Cooldown System — prevents the agent from spamming interventions.

Rules:
- No two interventions within 10 minutes
- No more than 3 interventions per hour
- No more than 6 interventions per day
- Escalation: if same intervention failed twice, try a different one
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.database import get_supabase


class CooldownManager:

    # Cooldown periods
    MIN_BETWEEN_INTERVENTIONS = 10   # minutes
    MAX_PER_HOUR              = 3
    MAX_PER_DAY               = 6

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    def can_intervene(self) -> Dict[str, Any]:
        """
        Check if agent is allowed to intervene right now.

        Returns:
            Dict with:
            - allowed: bool
            - reason:  why not allowed (if blocked)
            - next_allowed_at: when next intervention is allowed
        """
        recent = self._get_recent_interventions()

        # ── Check: too soon since last intervention ────────────────────
        if recent:
            last_time = datetime.fromisoformat(
                recent[0]['created_at'].replace('Z', '+00:00')
            ).replace(tzinfo=None)

            elapsed = (datetime.utcnow() - last_time).total_seconds() / 60

            if elapsed < self.MIN_BETWEEN_INTERVENTIONS:
                wait = round(self.MIN_BETWEEN_INTERVENTIONS - elapsed)
                return {
                    'allowed':          False,
                    'reason':           f'Cooldown active. Wait {wait} more minutes.',
                    'next_allowed_at':  (
                        last_time +
                        timedelta(minutes=self.MIN_BETWEEN_INTERVENTIONS)
                    ).isoformat()
                }

        # ── Check: too many this hour ──────────────────────────────────
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        hourly_count = sum(
            1 for r in recent
            if datetime.fromisoformat(
                r['created_at'].replace('Z', '+00:00')
            ).replace(tzinfo=None) >= one_hour_ago
        )

        if hourly_count >= self.MAX_PER_HOUR:
            return {
                'allowed': False,
                'reason':  f'Too many interventions this hour ({hourly_count}/{self.MAX_PER_HOUR})',
                'next_allowed_at': None
            }

        # ── Check: too many today ──────────────────────────────────────
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        daily_count = sum(
            1 for r in recent
            if datetime.fromisoformat(
                r['created_at'].replace('Z', '+00:00')
            ).replace(tzinfo=None) >= today_start
        )

        if daily_count >= self.MAX_PER_DAY:
            return {
                'allowed': False,
                'reason':  f'Daily intervention limit reached ({daily_count}/{self.MAX_PER_DAY})',
                'next_allowed_at': None
            }

        return {
            'allowed':         True,
            'reason':          None,
            'interventions_today': daily_count,
            'interventions_this_hour': hourly_count
        }

    def get_failed_interventions(self) -> List[str]:
        """
        Get list of intervention types that failed recently.
        Used to avoid repeating failed interventions.
        """
        result = (
            self.supabase
            .table('intervention_outcomes')
            .select("intervention_type, outcome")
            .eq('user_id', self.user_id)
            .eq('outcome', 'ignored')
            .gte(
                'created_at',
                (datetime.utcnow() - timedelta(hours=2)).isoformat()
            )
            .execute()
        )

        return [r['intervention_type'] for r in (result.data or [])]

    def _get_recent_interventions(self) -> List[Dict]:
        """Get interventions from the last 24 hours."""
        since = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        result = (
            self.supabase
            .table('agent_interventions')
            .select("*")
            .eq('user_id', self.user_id)
            .gte('created_at', since)
            .order('created_at', desc=True)
            .execute()
        )

        return result.data or []
