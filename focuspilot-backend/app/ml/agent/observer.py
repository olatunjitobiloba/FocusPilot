# app/ml/agent/observer.py
"""
Observer — collects current user state from all data sources.

The observer answers: "What is the user doing RIGHT NOW?"

It collects:
- Active session info
- Recent browsing activity
- Current risk score from ML model
- Historical context
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from app.database import get_supabase


def _normalize_domain(value: str) -> str:
    return (value or '').strip().lower().replace('www.', '')


class Observer:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    def observe(self) -> Dict[str, Any]:
        """
        Collect complete current state snapshot.

        Returns:
            Dict with all observable user state
        """
        observation = {
            'user_id':       self.user_id,
            'observed_at':   datetime.utcnow().isoformat(),
            'active_session': None,
            'recent_activity': [],
            'session_metrics': {},
            'context': {}
        }

        # ── Active session ─────────────────────────────────────────────
        active = self._get_active_session()
        observation['active_session'] = active

        if active:
            # ── Recent activity in this session ────────────────────────
            observation['recent_activity'] = (
                self._get_recent_activity(
                    session_id=active['id'],
                    minutes_back=10
                )
            )

            # ── Session metrics ────────────────────────────────────────
            observation['session_metrics'] = (
                self._compute_session_metrics(
                    active,
                    observation['recent_activity']
                )
            )

        # ── Historical context ─────────────────────────────────────────
        observation['context'] = self._get_context()

        return observation

    # ── Private methods ────────────────────────────────────────────────

    def _get_active_session(self) -> Optional[Dict]:
        """Fetch currently active session."""
        result = (
            self.supabase
            .table('focus_sessions')
            .select("*")
            .eq('user_id', self.user_id)
            .is_('end_time', 'null')
            .execute()
        )
        return result.data[0] if result.data else None

    def _get_recent_activity(
        self,
        session_id: str,
        minutes_back: int = 10
    ) -> List[Dict]:
        """Fetch browsing activity from last N minutes."""
        since = (
            datetime.utcnow() - timedelta(minutes=minutes_back)
        ).isoformat()

        result = (
            self.supabase
            .table('browsing_activity')
            .select("*")
            .eq('session_id', session_id)
            .gte('timestamp', since)
            .order('timestamp', desc=True)
            .execute()
        )
        return result.data or []

    def _compute_session_metrics(
        self,
        session: Dict,
        recent_activity: List[Dict]
    ) -> Dict:
        """
        Compute real-time metrics for the active session.
        These feed directly into the risk assessment.
        """
        from app.ml.feature_engineer import DISTRACTION_DOMAINS

        # Session elapsed time
        start_time = datetime.fromisoformat(
            session['start_time'].replace('Z', '+00:00')
        ).replace(tzinfo=None)
        elapsed_minutes = (
            datetime.utcnow() - start_time
        ).total_seconds() / 60

        # Recent distraction analysis (last 10 minutes)
        distraction_acts = [
            a for a in recent_activity
            if _normalize_domain(a.get('domain', '')) in DISTRACTION_DOMAINS
        ]

        distraction_seconds_recent = sum(
            a.get('duration_seconds') or 0
            for a in distraction_acts
        )

        total_seconds_recent = sum(
            a.get('duration_seconds') or 0
            for a in recent_activity
        )

        recent_distraction_ratio = (
            distraction_seconds_recent / total_seconds_recent
            if total_seconds_recent > 0 else 0.0
        )

        # Last visited domain
        last_domain = (
            _normalize_domain(recent_activity[0].get('domain'))
            if recent_activity else None
        )

        return {
            'elapsed_minutes':          round(elapsed_minutes, 1),
            'recent_distraction_ratio': round(recent_distraction_ratio, 3),
            'recent_distraction_count': len(distraction_acts),
            'last_domain':              last_domain,
            'activity_count_10min':     len(recent_activity),
            'is_on_distraction_site':   (
                last_domain in DISTRACTION_DOMAINS
                if last_domain else False
            )
        }

    def _get_context(self) -> Dict:
        """
        Get historical context for the current moment.
        """
        now  = datetime.utcnow()
        hour = now.hour

        # Sessions in last 7 days
        week_ago = (now - timedelta(days=7)).isoformat()
        result   = (
            self.supabase
            .table('focus_sessions')
            .select("focus_score, duration_minutes")
            .eq('user_id', self.user_id)
            .gte('start_time', week_ago)
            .not_.is_('end_time', 'null')
            .execute()
        )

        past_sessions = result.data or []

        avg_score = (
            sum(s['focus_score'] for s in past_sessions if s.get('focus_score'))
            / len([s for s in past_sessions if s.get('focus_score')])
            if any(s.get('focus_score') for s in past_sessions)
            else 5.0
        )

        return {
            'current_hour':        hour,
            'is_typical_study_hour': 8 <= hour <= 22,
            'sessions_this_week':  len(past_sessions),
            'avg_focus_score_week': round(avg_score, 2)
        }
