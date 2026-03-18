# app/analytics/aggregator.py
"""
Analytics Aggregator — computes all productivity metrics.

Pulls from:
- focus_sessions
- browsing_activity
- risk_history
- intervention_outcomes
- agent_actions
- session_clusters

Returns structured analytics data ready for the frontend.
"""

import numpy as np
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple, Set
from dateutil.parser import isoparse
from app.database import get_supabase


class AnalyticsAggregator:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()
        self._productive_domains_cache: Optional[Set[str]] = None

    def _normalize_domain(self, value: str) -> str:
        domain = (value or '').strip().lower()
        domain = domain.replace('https://', '').replace('http://', '')
        domain = domain.split('/')[0]
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def _get_productive_domains(self) -> Set[str]:
        if self._productive_domains_cache is not None:
            return self._productive_domains_cache

        result = (
            self.supabase
            .table('suggestion_feedback')
            .select('domain')
            .eq('user_id', self.user_id)
            .eq('action', 'productive')
            .execute()
        )

        self._productive_domains_cache = {
            self._normalize_domain(item.get('domain', ''))
            for item in (result.data or [])
            if item.get('domain')
        }
        return self._productive_domains_cache

    # ── Main method ────────────────────────────────────────────────────

    def compute_all(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Compute all analytics for the last N days.

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Complete analytics dict
        """
        since = (
            datetime.utcnow() - timedelta(days=days)
        ).isoformat()

        print(f"📊 Computing analytics for {self.user_id[:8]} ({days} days)")

        sessions   = self._load_sessions(since)
        activity   = self._load_activity(since)
        risk_hist  = self._load_risk_history(since)
        outcomes   = self._load_intervention_outcomes(since)
        actions    = self._load_agent_actions(since)

        return {
            'summary':          self._compute_summary(sessions, activity),
            'weekly_trend':     self._compute_weekly_trend(sessions),
            'daily_breakdown':  self._compute_daily_breakdown(sessions, days),
            'time_breakdown':   self._compute_time_breakdown(activity),
            'risk_trend':       self._compute_risk_trend(risk_hist),
            'session_stats':    self._compute_session_stats(sessions),
            'agent_stats':      self._compute_agent_stats(outcomes, actions),
            'streak':           self._compute_streak(sessions),
            'best_day':         self._compute_best_day(sessions),
            'best_hour':        self._compute_best_hour(sessions),
            'sessions':         self._format_sessions(sessions),
            'computed_at':      datetime.utcnow().isoformat(),
            'days_analyzed':    days
        }

    # ── Data loaders ───────────────────────────────────────────────────

    def _load_sessions(self, since: str) -> List[Dict]:
        result = (
            self.supabase
            .table('focus_sessions')
            .select("*")
            .eq('user_id', self.user_id)
            .gte('start_time', since)
            .not_.is_('end_time', 'null')
            .order('start_time', desc=False)
            .execute()
        )
        return result.data or []

    def _load_activity(self, since: str) -> List[Dict]:
        result = (
            self.supabase
            .table('browsing_activity')
            .select("domain, duration_seconds, timestamp, session_id")
            .eq('user_id', self.user_id)
            .gte('timestamp', since)
            .execute()
        )
        return result.data or []

    def _load_risk_history(self, since: str) -> List[Dict]:
        result = (
            self.supabase
            .table('risk_history')
            .select("risk_score, assessed_at")
            .eq('user_id', self.user_id)
            .gte('assessed_at', since)
            .order('assessed_at', desc=False)
            .execute()
        )
        return result.data or []

    def _load_intervention_outcomes(self, since: str) -> List[Dict]:
        result = (
            self.supabase
            .table('intervention_outcomes')
            .select("intervention_type, outcome, created_at")
            .eq('user_id', self.user_id)
            .gte('created_at', since)
            .execute()
        )
        return result.data or []

    def _load_agent_actions(self, since: str) -> List[Dict]:
        result = (
            self.supabase
            .table('agent_actions')
            .select("action_type, status, created_at")
            .eq('user_id', self.user_id)
            .gte('created_at', since)
            .execute()
        )
        return result.data or []

    # ── Computations ───────────────────────────────────────────────────

    def _parse_datetime(self, value: str) -> datetime:
        """
        Parse DB timestamps with tolerance for legacy formats.

        Handles:
        - trailing Z timezone marker
        - space separator instead of 'T'
        - fractional seconds longer than 6 digits
        """
        text = str(value or '').strip().strip("\"'")
        if not text:
            raise ValueError('Empty datetime value')

        text = text.replace(' ', 'T', 1).replace('Z', '+00:00')

        normalized = re.sub(
            r"\.(\d{6})\d+(?=([+-]\d{2}:\d{2})?$)",
            r".\1",
            text
        )

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            parsed = isoparse(normalized)

        return parsed.replace(tzinfo=None)

    def _compute_summary(
        self,
        sessions: List[Dict],
        activity: List[Dict]
    ) -> Dict:
        """Top-level summary metrics."""
        if not sessions:
            return {
                'total_sessions':       0,
                'total_focused_hours':  0.0,
                'avg_focus_score':      0.0,
                'avg_session_duration': 0.0,
                'total_distraction_mins': 0.0,
                'completion_rate':      0.0
            }

        # Total focused time
        total_mins = 0.0
        for s in sessions:
            start = self._parse_datetime(s['start_time'])
            end = self._parse_datetime(s['end_time'])
            total_mins += (end - start).total_seconds() / 60

        total_hours = round(total_mins / 60, 1)

        # Average focus score
        scores = [
            s['focus_score'] for s in sessions
            if s.get('focus_score') is not None
        ]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        # Average session duration
        avg_duration = round(total_mins / len(sessions), 1)

        # Completion rate
        completed = sum(
            1 for s in sessions
            if s.get('focus_score') is not None
        )
        completion_rate = round(completed / len(sessions) * 100, 1)

        # Total distraction time
        from app.ml.clustering.feature_extractor import DISTRACTION_DOMAINS
        productive_domains = self._get_productive_domains()
        distraction_secs = sum(
            a.get('duration_seconds') or 0
            for a in activity
            if self._normalize_domain(a.get('domain', '')) in DISTRACTION_DOMAINS
            and self._normalize_domain(a.get('domain', '')) not in productive_domains
        )
        distraction_mins = round(distraction_secs / 60, 1)

        return {
            'total_sessions':         len(sessions),
            'total_focused_hours':    total_hours,
            'avg_focus_score':        avg_score,
            'avg_session_duration':   avg_duration,
            'total_distraction_mins': distraction_mins,
            'completion_rate':        completion_rate
        }

    def _compute_weekly_trend(
        self,
        sessions: List[Dict]
    ) -> List[Dict]:
        """
        Compute weekly aggregates for trend chart.
        Returns one data point per week.
        """
        if not sessions:
            return []

        # Group sessions by ISO week
        weeks: Dict[str, List[Dict]] = {}

        for s in sessions:
            start = self._parse_datetime(s['start_time'])

            week_key = start.strftime('%Y-W%W')

            if week_key not in weeks:
                weeks[week_key] = []
            weeks[week_key].append(s)

        trend = []
        for week_key in sorted(weeks.keys()):
            week_sessions = weeks[week_key]

            scores = [
                s['focus_score'] for s in week_sessions
                if s.get('focus_score') is not None
            ]

            total_mins = 0.0
            for s in week_sessions:
                start = self._parse_datetime(s['start_time'])
                end = self._parse_datetime(s['end_time'])
                total_mins += (end - start).total_seconds() / 60

            trend.append({
                'week':          week_key,
                'week_label':    self._format_week_label(week_key),
                'sessions':      len(week_sessions),
                'avg_score':     round(
                    sum(scores) / len(scores), 1
                ) if scores else 0.0,
                'total_hours':   round(total_mins / 60, 1),
                'total_minutes': round(total_mins, 0)
            })

        return trend

    def _compute_daily_breakdown(
        self,
        sessions: List[Dict],
        days: int
    ) -> List[Dict]:
        """
        Compute daily aggregates for the last N days.
        Returns one data point per day (including days with no sessions).
        """
        # Build date range
        today      = date.today()
        date_range = [
            today - timedelta(days=i)
            for i in range(days - 1, -1, -1)
        ]

        # Group sessions by date
        by_date: Dict[str, List[Dict]] = {}
        for s in sessions:
            d = s['start_time'][:10]
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(s)

        breakdown = []
        for d in date_range:
            d_str     = d.isoformat()
            day_sess  = by_date.get(d_str, [])

            scores = [
                s['focus_score'] for s in day_sess
                if s.get('focus_score') is not None
            ]

            total_mins = 0.0
            for s in day_sess:
                start = self._parse_datetime(s['start_time'])
                end = self._parse_datetime(s['end_time'])
                total_mins += (end - start).total_seconds() / 60

            breakdown.append({
                'date':        d_str,
                'day_label':   d.strftime('%b %d'),
                'day_short':   d.strftime('%a'),
                'sessions':    len(day_sess),
                'avg_score':   round(
                    sum(scores) / len(scores), 1
                ) if scores else 0.0,
                'total_mins':  round(total_mins, 0),
                'total_hours': round(total_mins / 60, 1),
                'has_session': len(day_sess) > 0
            })

        return breakdown

    def _compute_time_breakdown(
        self,
        activity: List[Dict]
    ) -> Dict:
        """
        Compute time breakdown by site category.
        Returns data for pie/donut chart.
        """
        from app.ml.clustering.feature_extractor import (
            DISTRACTION_DOMAINS, PRODUCTIVE_DOMAINS
        )
        productive_override = self._get_productive_domains()

        if not activity:
            return {
                'categories': [],
                'top_sites':  []
            }

        # Categorize each activity entry
        distraction_secs = 0
        productive_secs  = 0
        neutral_secs     = 0

        site_times: Dict[str, int] = {}

        for a in activity:
            domain   = self._normalize_domain(a.get('domain', '')) or 'unknown'
            duration = a.get('duration_seconds') or 0

            site_times[domain] = site_times.get(domain, 0) + duration

            if domain in productive_override:
                productive_secs += duration
            elif domain in DISTRACTION_DOMAINS:
                distraction_secs += duration
            elif domain in PRODUCTIVE_DOMAINS:
                productive_secs += duration
            else:
                neutral_secs += duration

        total = distraction_secs + productive_secs + neutral_secs

        if total == 0:
            return {'categories': [], 'top_sites': []}

        categories = [
            {
                'name':    'Productive',
                'minutes': round(productive_secs / 60, 1),
                'pct':     round(productive_secs / total * 100, 1),
                'color':   '#10b981'
            },
            {
                'name':    'Distraction',
                'minutes': round(distraction_secs / 60, 1),
                'pct':     round(distraction_secs / total * 100, 1),
                'color':   '#ef4444'
            },
            {
                'name':    'Neutral',
                'minutes': round(neutral_secs / 60, 1),
                'pct':     round(neutral_secs / total * 100, 1),
                'color':   '#9ca3af'
            }
        ]

        # Top 8 sites by time
        top_sites = sorted(
            site_times.items(),
            key=lambda x: x[1],
            reverse=True
        )[:8]

        top_sites_formatted = [
            {
                'domain':  domain,
                'minutes': round(secs / 60, 1),
                'pct':     round(secs / total * 100, 1),
                'is_distraction': domain in DISTRACTION_DOMAINS and domain not in productive_override,
                'is_productive':  domain in PRODUCTIVE_DOMAINS or domain in productive_override
            }
            for domain, secs in top_sites
        ]

        return {
            'categories': categories,
            'top_sites':  top_sites_formatted
        }

    def _compute_risk_trend(
        self,
        risk_hist: List[Dict]
    ) -> List[Dict]:
        """Compute daily average risk score trend."""
        if not risk_hist:
            return []

        by_date: Dict[str, List[float]] = {}
        for r in risk_hist:
            d = r['assessed_at'][:10]
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(r['risk_score'])

        return [
            {
                'date':       d,
                'day_label':  datetime.strptime(d, '%Y-%m-%d').strftime('%b %d'),
                'avg_risk':   round(sum(scores) / len(scores), 3),
                'risk_pct':   round(sum(scores) / len(scores) * 100, 1),
                'max_risk':   round(max(scores), 3),
                'data_points': len(scores)
            }
            for d, scores in sorted(by_date.items())
        ]

    def _compute_session_stats(
        self,
        sessions: List[Dict]
    ) -> Dict:
        """Compute detailed session statistics."""
        if not sessions:
            return {}

        durations = []
        for s in sessions:
            start = self._parse_datetime(s['start_time'])
            end = self._parse_datetime(s['end_time'])
            durations.append((end - start).total_seconds() / 60)

        scores = [
            s['focus_score'] for s in sessions
            if s.get('focus_score') is not None
        ]

        return {
            'min_duration':  round(min(durations), 1),
            'max_duration':  round(max(durations), 1),
            'avg_duration':  round(sum(durations) / len(durations), 1),
            'min_score':     round(min(scores), 1) if scores else 0,
            'max_score':     round(max(scores), 1) if scores else 0,
            'avg_score':     round(sum(scores) / len(scores), 1) if scores else 0,
            'total_sessions': len(sessions),
            'sessions_with_score': len(scores)
        }

    def _compute_agent_stats(
        self,
        outcomes: List[Dict],
        actions: List[Dict]
    ) -> Dict:
        """Compute agent effectiveness statistics."""
        total_outcomes  = len(outcomes)
        successful      = sum(
            1 for o in outcomes if o.get('outcome') == 'success'
        )
        success_rate = (
            round(successful / total_outcomes * 100, 1)
            if total_outcomes > 0 else 0.0
        )

        total_actions    = len(actions)
        completed_actions = sum(
            1 for a in actions if a.get('status') == 'completed'
        )

        # Count by action type
        by_type: Dict[str, int] = {}
        for a in actions:
            t = a.get('action_type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1

        return {
            'total_interventions':    total_outcomes,
            'successful_interventions': successful,
            'intervention_success_rate': success_rate,
            'total_actions':          total_actions,
            'completed_actions':      completed_actions,
            'actions_by_type':        by_type
        }

    def _compute_streak(
        self,
        sessions: List[Dict]
    ) -> Dict:
        """Compute current and longest focus streak (consecutive days)."""
        if not sessions:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'streak_start':   None
            }

        # Get unique session dates
        session_dates = sorted(set(
            s['start_time'][:10] for s in sessions
        ))

        if not session_dates:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'streak_start':   None
            }

        # Compute streaks
        streaks        = []
        current_streak = 1
        streak_start   = session_dates[0]

        for i in range(1, len(session_dates)):
            prev = date.fromisoformat(session_dates[i - 1])
            curr = date.fromisoformat(session_dates[i])

            if (curr - prev).days == 1:
                current_streak += 1
            else:
                streaks.append(current_streak)
                current_streak = 1
                streak_start   = session_dates[i]

        streaks.append(current_streak)
        longest_streak = max(streaks)

        # Check if current streak is still active (includes today or yesterday)
        last_date    = date.fromisoformat(session_dates[-1])
        today        = date.today()
        streak_active = (today - last_date).days <= 1

        active_streak = current_streak if streak_active else 0

        return {
            'current_streak': active_streak,
            'longest_streak': longest_streak,
            'streak_start':   streak_start if streak_active else None,
            'last_session':   session_dates[-1]
        }

    def _compute_best_day(
        self,
        sessions: List[Dict]
    ) -> Dict:
        """Find the day of week with the best average focus score."""
        if not sessions:
            return {}

        day_scores: Dict[int, List[float]] = {i: [] for i in range(7)}

        for s in sessions:
            if s.get('focus_score') is None:
                continue
            start = self._parse_datetime(s['start_time'])
            dow     = start.weekday()
            day_scores[dow].append(s['focus_score'])

        day_avgs = {
            dow: sum(scores) / len(scores)
            for dow, scores in day_scores.items()
            if scores
        }

        if not day_avgs:
            return {}

        best_dow   = max(day_avgs, key=day_avgs.get)
        day_names  = ['Monday','Tuesday','Wednesday',
                      'Thursday','Friday','Saturday','Sunday']

        return {
            'day_of_week':  best_dow,
            'day_name':     day_names[best_dow],
            'avg_score':    round(day_avgs[best_dow], 1),
            'session_count': len(day_scores[best_dow])
        }

    def _compute_best_hour(
        self,
        sessions: List[Dict]
    ) -> Dict:
        """Find the hour of day with the best average focus score."""
        if not sessions:
            return {}

        hour_scores: Dict[int, List[float]] = {}

        for s in sessions:
            if s.get('focus_score') is None:
                continue
            start = self._parse_datetime(s['start_time'])
            h = start.hour
            if h not in hour_scores:
                hour_scores[h] = []
            hour_scores[h].append(s['focus_score'])

        if not hour_scores:
            return {}

        hour_avgs = {
            h: sum(scores) / len(scores)
            for h, scores in hour_scores.items()
        }

        best_hour = max(hour_avgs, key=hour_avgs.get)

        return {
            'hour':        best_hour,
            'hour_label':  self._format_hour(best_hour),
            'avg_score':   round(hour_avgs[best_hour], 1),
            'session_count': len(hour_scores[best_hour])
        }

    def _format_sessions(
        self,
        sessions: List[Dict]
    ) -> List[Dict]:
        """Format sessions for the session history table."""
        formatted = []
        for s in sessions:
            start = self._parse_datetime(s['start_time'])
            end = self._parse_datetime(s['end_time'])
            duration = round((end - start).total_seconds() / 60, 1)

            formatted.append({
                'id':           s['id'],
                'date':         start.strftime('%b %d, %Y'),
                'day':          start.strftime('%A'),
                'start_time':   start.strftime('%I:%M %p'),
                'end_time':     end.strftime('%I:%M %p'),
                'duration_mins': duration,
                'focus_score':  s.get('focus_score'),
                'planned_mins': s.get('duration_minutes'),
                'auto_started': s.get('auto_started', False)
            })

        return list(reversed(formatted))   # Most recent first

    # ── Helpers ────────────────────────────────────────────────────────

    def _format_week_label(self, week_key: str) -> str:
        """Format week key as 'Mar 10 - Mar 16'."""
        try:
            year, week = week_key.split('-W')
            d = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
            end = d + timedelta(days=6)
            return f"{d.strftime('%b %d')} – {end.strftime('%b %d')}"
        except Exception:
            return week_key

    def _format_hour(self, hour: int) -> str:
        if hour == 0:   return "12:00 AM"
        if hour < 12:   return f"{hour}:00 AM"
        if hour == 12:  return "12:00 PM"
        return f"{hour - 12}:00 PM"
