# app/ml/feature_engineer.py
"""
Feature Engineer — transforms raw session data into ML features.

Each session becomes one ROW of training data.
Each row has 15 features + 1 label (did_procrastinate).

Features are grouped into 4 categories:
1. Temporal   — WHEN the session happened
2. Behavioral — HOW the user behaved
3. Historical — PATTERNS from past sessions
4. Contextual — SURROUNDING circumstances
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import math
import re


# ── Known distraction domains ──────────────────────────────────────────
DISTRACTION_DOMAINS = {
    'youtube.com', 'twitter.com', 'instagram.com', 'tiktok.com',
    'reddit.com', 'facebook.com', 'netflix.com', 'twitch.tv',
    'whatsapp.web.com', 'snapchat.com', 'pinterest.com', 'tumblr.com'
}


def normalize_domain(value: str) -> str:
    return (value or '').strip().lower().replace('www.', '')


class FeatureEngineer:

    def build_feature_matrix(
        self,
        sessions: List[Dict]
    ) -> List[Dict]:
        """
        Main method. Converts list of sessions into feature rows.

        Args:
            sessions: List of session dicts WITH activities attached
                      (use DataExtractor.get_sessions_with_activities)

        Returns:
            List of feature dicts. Each dict = one training row.
        """
        if not sessions:
            return []

        feature_rows = []

        for i, session in enumerate(sessions):

            # Skip sessions without end_time (incomplete)
            if not session.get('end_time'):
                continue

            # Get past sessions for historical features
            past_sessions = sessions[:i]  # All sessions before this one

            try:
                # Build feature row
                features = {}

                # ── Group 1: Temporal Features (4 features) ───────────
                features.update(
                    self._temporal_features(session)
                )

                # ── Group 2: Behavioral Features (5 features) ─────────
                features.update(
                    self._behavioral_features(session)
                )

                # ── Group 3: Historical Features (4 features) ─────────
                features.update(
                    self._historical_features(session, past_sessions)
                )

                # ── Group 4: Contextual Features (2 features) ─────────
                features.update(
                    self._contextual_features(session, past_sessions)
                )

                # ── Label: Did the user procrastinate? ────────────────
                features['did_procrastinate'] = self._label(session)

                # ── Metadata (not used in training, kept for debugging) ─
                features['_session_id']   = session['id']
                features['_start_time']   = session['start_time']
                features['_focus_score']  = session.get('focus_score')

                feature_rows.append(features)
            except Exception as e:
                session_id = session.get('id', 'unknown')
                print(
                    f"WARNING Feature row skipped for session {session_id}: {e}"
                )
                continue

        return feature_rows

    # ── Group 1: Temporal Features ─────────────────────────────────────

    def _temporal_features(self, session: Dict) -> Dict:
        """
        WHEN did the session happen?

        Features:
        - hour_of_day:    0-23 (14 = 2 PM)
        - is_night:       1 if hour >= 22 or hour <= 5
        - day_of_week:    0=Monday ... 6=Sunday
        - is_weekend:     1 if Saturday or Sunday
        """
        start_time = self._parse_dt(session['start_time'])

        hour        = start_time.hour
        day_of_week = start_time.weekday()  # 0=Monday, 6=Sunday

        return {
            'hour_of_day': hour,
            'is_night':    int(hour >= 22 or hour <= 5),
            'day_of_week': day_of_week,
            'is_weekend':  int(day_of_week >= 5)
        }

    # ── Group 2: Behavioral Features ──────────────────────────────────

    def _behavioral_features(self, session: Dict) -> Dict:
        """
        HOW did the user behave during this session?

        Features:
        - session_duration_mins:  How long the session lasted
        - distraction_ratio:      % of time on distraction sites
        - distraction_count:      Number of distraction site visits
        - abandoned_early:        1 if session < 10 minutes
        - peak_distraction_mins:  Longest single distraction visit
        """
        activities = session.get('activities', [])
        duration   = session.get('duration_minutes') or 0

        # Separate distraction vs productive activities
        distraction_acts = [
            a for a in activities
            if normalize_domain(a.get('domain', '')) in DISTRACTION_DOMAINS
        ]

        # Total time on distraction sites
        distraction_seconds = sum(
            a.get('duration_seconds') or 0
            for a in distraction_acts
        )
        distraction_minutes = distraction_seconds / 60

        # Distraction ratio (0.0 to 1.0)
        distraction_ratio = (
            distraction_minutes / duration
            if duration > 0 else 0.0
        )
        distraction_ratio = min(distraction_ratio, 1.0)  # Cap at 1.0

        # Longest single distraction visit (in minutes)
        peak_distraction = 0
        if distraction_acts:
            peak_distraction = max(
                a.get('duration_seconds') or 0
                for a in distraction_acts
            ) / 60

        return {
            'session_duration_mins':  duration,
            'distraction_ratio':      round(distraction_ratio, 3),
            'distraction_count':      len(distraction_acts),
            'abandoned_early':        int(duration < 10),
            'peak_distraction_mins':  round(peak_distraction, 2)
        }

    # ── Group 3: Historical Features ──────────────────────────────────

    def _historical_features(
        self,
        session: Dict,
        past_sessions: List[Dict]
    ) -> Dict:
        """
        What are the USER'S PATTERNS from past sessions?

        Features:
        - avg_focus_score_last3:    Average focus score of last 3 sessions
        - days_since_last_session:  Gap since last session (0 = same day)
        - sessions_today:           How many sessions already today
        - avg_duration_last7:       Average session duration last 7 days
        """
        completed_past = [
            s for s in past_sessions
            if s.get('end_time') and s.get('focus_score')
        ]

        # Average focus score of last 3 sessions
        last_3 = completed_past[-3:]
        avg_score_last3 = (
            sum(s['focus_score'] for s in last_3) / len(last_3)
            if last_3 else 5.0   # Default to neutral
        )

        # Days since last session
        days_since_last = 0
        if past_sessions:
            last_session_time = self._parse_dt(past_sessions[-1]['start_time'])
            current_time      = self._parse_dt(session['start_time'])
            delta             = current_time - last_session_time
            days_since_last   = delta.days

        # Sessions already completed today
        today = session['start_time'][:10]
        sessions_today = sum(
            1 for s in past_sessions
            if s['start_time'][:10] == today and s.get('end_time')
        )

        # Average duration over last 7 days
        week_ago = (
            self._parse_dt(session['start_time']) - timedelta(days=7)
        )
        last_week_sessions = [
            s for s in past_sessions
            if self._parse_dt(s['start_time']) >= week_ago
            and s.get('duration_minutes')
        ]
        avg_duration_last7 = (
            sum(s['duration_minutes'] for s in last_week_sessions)
            / len(last_week_sessions)
            if last_week_sessions else 25.0   # Default Pomodoro
        )

        return {
            'avg_focus_score_last3':  round(avg_score_last3, 2),
            'days_since_last_session': days_since_last,
            'sessions_today':          sessions_today,
            'avg_duration_last7':      round(avg_duration_last7, 2)
        }

    # ── Group 4: Contextual Features ──────────────────────────────────

    def _contextual_features(
        self,
        session: Dict,
        past_sessions: List[Dict]
    ) -> Dict:
        """
        SURROUNDING CIRCUMSTANCES.

        Features:
        - same_hour_avg_score:  User's historical avg score at this hour
        - streak_days:          Consecutive days with sessions before today
        """
        start_time = self._parse_dt(session['start_time'])
        hour       = start_time.hour

        # Historical average score at this hour
        same_hour_sessions = [
            s for s in past_sessions
            if self._parse_dt(s['start_time']).hour == hour
            and s.get('focus_score')
        ]
        same_hour_avg = (
            sum(s['focus_score'] for s in same_hour_sessions)
            / len(same_hour_sessions)
            if same_hour_sessions else 5.0
        )

        # Streak: consecutive days with at least 1 session
        streak      = 0
        today       = self._parse_dt(session['start_time']).date()
        check_date  = today - timedelta(days=1)

        past_dates = set(
            self._parse_dt(s['start_time']).date()
            for s in past_sessions
            if s.get('end_time')
        )

        while check_date in past_dates:
            streak     += 1
            check_date -= timedelta(days=1)

        return {
            'same_hour_avg_score': round(same_hour_avg, 2),
            'streak_days':         streak
        }

    # ── Label ──────────────────────────────────────────────────────────

    def _label(self, session: Dict) -> int:
        """
        Did the user procrastinate in this session?

        Procrastination = 1 if ANY of:
        - Focus score <= 4 (self-reported low focus)
        - Distraction ratio > 50% (spent more time distracted than focused)
        - Abandoned early (< 10 minutes)

        Returns: 1 (procrastinated) or 0 (focused)
        """
        focus_score = session.get('focus_score') or 5
        duration    = session.get('duration_minutes') or 0
        activities  = session.get('activities', [])

        # Check distraction ratio
        distraction_seconds = sum(
            a.get('duration_seconds') or 0
            for a in activities
            if normalize_domain(a.get('domain', '')) in DISTRACTION_DOMAINS
        )
        distraction_ratio = (
            (distraction_seconds / 60) / duration
            if duration > 0 else 0
        )

        # Label logic
        if focus_score <= 4:
            return 1
        if distraction_ratio > 0.5:
            return 1
        if duration < 10 and session.get('end_time'):
            return 1

        return 0

    # ── Utility ────────────────────────────────────────────────────────

    def _parse_dt(self, dt_string: str) -> datetime:
        """Parse datetime string safely across legacy timestamp formats."""
        if dt_string is None:
            raise ValueError("Datetime value is None")

        value = str(dt_string).strip().strip("\"'")
        if not value:
            raise ValueError("Datetime value is empty")

        # Normalize common variants before parsing.
        value = value.replace(' ', 'T', 1).replace('Z', '+00:00')

        # Normalize fractional precision to max 6 digits for fromisoformat.
        match = re.match(
            r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?([+-]\d{2}:\d{2})?$",
            value
        )
        if match:
            base = match.group(1)
            frac = match.group(2) or ""
            tz = match.group(3) or ""

            if frac:
                frac = frac[:6]
                value = f"{base}.{frac}{tz}"
            else:
                value = f"{base}{tz}"

        # Fallback: extract parseable prefix if source stored extra suffix text.
        fallback = re.match(
            r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:[+-]\d{2}:\d{2})?)",
            value
        )
        if fallback:
            value = fallback.group(1)

        return datetime.fromisoformat(value).replace(tzinfo=None)

    def get_feature_names(self) -> List[str]:
        """Return list of all feature names (for model explainability)."""
        return [
            # Temporal
            'hour_of_day',
            'is_night',
            'day_of_week',
            'is_weekend',
            # Behavioral
            'session_duration_mins',
            'distraction_ratio',
            'distraction_count',
            'abandoned_early',
            'peak_distraction_mins',
            # Historical
            'avg_focus_score_last3',
            'days_since_last_session',
            'sessions_today',
            'avg_duration_last7',
            # Contextual
            'same_hour_avg_score',
            'streak_days'
        ]
