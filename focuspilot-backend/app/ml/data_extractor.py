# app/ml/data_extractor.py
"""
Data Extractor — pulls raw data from Supabase for ML training.

Responsibility:
- Fetch sessions, activities, agent states
- Join related tables
- Return clean Python dicts/lists
- Handle missing data gracefully

This layer knows about the DATABASE.
It does NOT know about ML features.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.database import get_supabase


class DataExtractor:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    # ── Sessions ───────────────────────────────────────────────────────

    def get_sessions(
        self,
        days_back: int = 30,
        completed_only: bool = False
    ) -> List[Dict]:
        """
        Fetch focus sessions for the user.

        Args:
            days_back:      How many days of history to fetch
            completed_only: If True, only return sessions with end_time

        Returns:
            List of session dicts ordered by start_time ascending
        """
        start_date = (
            datetime.utcnow() - timedelta(days=days_back)
        ).isoformat()

        query = (
            self.supabase
            .table('focus_sessions')
            .select("*")
            .eq('user_id', self.user_id)
            .gte('start_time', start_date)
            .order('start_time', desc=False)
        )

        if completed_only:
            query = query.not_.is_('end_time', 'null')

        result = query.execute()
        return result.data or []

    def get_activities(
        self,
        days_back: int = 30,
        session_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch browsing activities.

        Args:
            days_back:  How many days of history
            session_id: If provided, only fetch for that session

        Returns:
            List of activity dicts ordered by timestamp ascending
        """
        start_date = (
            datetime.utcnow() - timedelta(days=days_back)
        ).isoformat()

        query = (
            self.supabase
            .table('browsing_activity')
            .select("*")
            .eq('user_id', self.user_id)
            .gte('timestamp', start_date)
            .order('timestamp', desc=False)
        )

        if session_id:
            query = query.eq('session_id', session_id)

        result = query.execute()
        return result.data or []

    def get_agent_state(self) -> Optional[Dict]:
        """Fetch the current agent state for the user."""
        result = (
            self.supabase
            .table('agent_state')
            .select("*")
            .eq('user_id', self.user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # ── Joined data ────────────────────────────────────────────────────

    def get_sessions_with_activities(
        self,
        days_back: int = 30
    ) -> List[Dict]:
        """
        Fetch sessions and attach their activities.

        Returns:
            List of session dicts, each with an 'activities' key
        """
        sessions   = self.get_sessions(days_back=days_back)
        activities = self.get_activities(days_back=days_back)

        # Build lookup: session_id → list of activities
        activity_map: Dict[str, List] = {}
        for act in activities:
            sid = act.get('session_id')
            if sid:
                activity_map.setdefault(sid, []).append(act)

        # Attach activities to sessions
        for session in sessions:
            session['activities'] = activity_map.get(session['id'], [])

        return sessions

    # ── Aggregate helpers ──────────────────────────────────────────────

    def get_daily_summaries(self, days_back: int = 30) -> List[Dict]:
        """
        Summarize sessions by day.

        Returns one dict per day with:
        - total_sessions, total_minutes, avg_focus_score
        - total_distractions, days_studied
        """
        sessions = self.get_sessions(
            days_back=days_back,
            completed_only=True
        )

        # Group by date
        daily: Dict[str, Dict] = {}

        for session in sessions:
            date = session['start_time'][:10]

            if date not in daily:
                daily[date] = {
                    'date':             date,
                    'total_sessions':   0,
                    'total_minutes':    0,
                    'focus_scores':     [],
                    'total_distractions': 0
                }

            daily[date]['total_sessions']    += 1
            daily[date]['total_minutes']     += session.get('duration_minutes') or 0
            daily[date]['total_distractions']+= session.get('distraction_count') or 0

            if session.get('focus_score'):
                daily[date]['focus_scores'].append(session['focus_score'])

        # Compute averages
        summaries = []
        for date, data in sorted(daily.items()):
            scores = data.pop('focus_scores')
            data['avg_focus_score'] = (
                round(sum(scores) / len(scores), 2)
                if scores else 0.0
            )
            summaries.append(data)

        return summaries

    def get_domain_stats(self, days_back: int = 30) -> Dict[str, Dict]:
        """
        Aggregate browsing stats per domain.

        Returns:
            Dict mapping domain → {total_seconds, visit_count, session_ids}
        """
        activities = self.get_activities(days_back=days_back)

        domain_stats: Dict[str, Dict] = {}

        for act in activities:
            domain = act.get('domain', 'unknown')

            if domain not in domain_stats:
                domain_stats[domain] = {
                    'total_seconds': 0,
                    'visit_count':   0,
                    'session_ids':   set()
                }

            domain_stats[domain]['total_seconds'] += act.get('duration_seconds') or 0
            domain_stats[domain]['visit_count']   += 1

            if act.get('session_id'):
                domain_stats[domain]['session_ids'].add(act['session_id'])

        # Convert sets to counts
        for domain in domain_stats:
            domain_stats[domain]['unique_sessions'] = len(
                domain_stats[domain].pop('session_ids')
            )

        return domain_stats

    def get_data_summary(self) -> Dict:
        """
        Quick summary of available data.
        Use this to check if user has enough data for ML.
        """
        sessions   = self.get_sessions(days_back=30)
        activities = self.get_activities(days_back=30)

        completed = [s for s in sessions if s.get('end_time')]

        return {
            'total_sessions':    len(sessions),
            'completed_sessions': len(completed),
            'total_activities':  len(activities),
            'days_of_data':      len(set(s['start_time'][:10] for s in sessions)),
            'has_enough_data':   len(completed) >= 5,   # Minimum for ML
            'recommended_data':  len(completed) >= 20   # Better accuracy
        }
