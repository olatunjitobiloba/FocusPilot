# app/ml/clustering/feature_extractor.py
"""
Feature Extractor for Clustering.

Extracts behavioral features from focus sessions
that are useful for K-Means clustering.

Features per session:
    1.  hour_of_day          (0-23)
    2.  day_of_week          (0-6, Mon=0)
    3.  duration_minutes     (actual session length)
    4.  focus_score          (1-10, user-rated)
    5.  distraction_ratio    (% time on distraction sites)
    6.  distraction_count    (number of distraction visits)
    7.  task_switches        (how many times switched tasks)
    8.  session_completed    (1=completed, 0=abandoned)
    9.  avg_visit_duration   (avg seconds per site visit)
    10. productive_ratio     (% time on productive sites)
    11. is_morning           (1 if 6-12, else 0)
    12. is_afternoon         (1 if 12-17, else 0)
    13. is_evening           (1 if 17-22, else 0)
    14. is_weekend           (1 if Sat/Sun, else 0)
    15. session_length_bucket (0=short<20, 1=medium 20-45, 2=long>45)
"""

import numpy as np
from datetime import datetime
import re
from typing import Dict, List, Tuple, Optional
from dateutil.parser import isoparse
from app.database import get_supabase


# Productive domains (opposite of distraction)
PRODUCTIVE_DOMAINS = [
    'github.com', 'stackoverflow.com', 'docs.python.org',
    'developer.mozilla.org', 'coursera.org', 'udemy.com',
    'notion.so', 'figma.com', 'linear.app', 'jira.atlassian.com',
    'google.com', 'scholar.google.com', 'arxiv.org',
    'medium.com', 'dev.to', 'leetcode.com', 'hackerrank.com'
]

DISTRACTION_DOMAINS = [
    'youtube.com', 'twitter.com', 'instagram.com', 'tiktok.com',
    'reddit.com', 'facebook.com', 'netflix.com', 'twitch.tv',
    'snapchat.com', 'pinterest.com', 'buzzfeed.com', '9gag.com'
]

FEATURE_NAMES = [
    'hour_of_day', 'day_of_week', 'duration_minutes',
    'focus_score', 'distraction_ratio', 'distraction_count',
    'task_switches', 'session_completed', 'avg_visit_duration',
    'productive_ratio', 'is_morning', 'is_afternoon',
    'is_evening', 'is_weekend', 'session_length_bucket'
]


class SessionFeatureExtractor:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    def extract_all_sessions(
        self,
        min_sessions: int = 5
    ) -> Tuple[np.ndarray, List[Dict], List[str]]:
        """
        Extract features from all completed sessions.

        Returns:
            X:        Feature matrix (n_sessions × n_features)
            sessions: Raw session dicts
            ids:      Session IDs (for assignment mapping)
        """
        sessions = self._load_sessions()

        if len(sessions) < min_sessions:
            raise ValueError(
                f"Need at least {min_sessions} completed sessions. "
                f"Found {len(sessions)}."
            )

        features = []
        valid_sessions = []
        session_ids    = []

        for session in sessions:
            try:
                feat = self._extract_session_features(session)
                features.append(feat)
                valid_sessions.append(session)
                session_ids.append(session['id'])
            except Exception as e:
                print(f"   ⚠️  Skipping session {session['id'][:8]}: {e}")
                continue

        if len(features) < min_sessions:
            raise ValueError(
                f"Only {len(features)} sessions had enough data."
            )

        X = np.array(features, dtype=np.float32)

        print(
            f"   ✅ Extracted features: "
            f"{X.shape[0]} sessions × {X.shape[1]} features"
        )

        return X, valid_sessions, session_ids

    def _load_sessions(self) -> List[Dict]:
        """Load all completed sessions with activity data."""
        result = (
            self.supabase
            .table('focus_sessions')
            .select("*")
            .eq('user_id', self.user_id)
            .not_.is_('end_time', 'null')
            .not_.is_('start_time', 'null')
            .execute()
        )
        return result.data or []

    def _extract_session_features(
        self,
        session: Dict
    ) -> List[float]:
        """Extract feature vector for one session."""

        # ── Parse times ────────────────────────────────────────────────
        start_time = self._parse_datetime(session['start_time'])
        end_time = self._parse_datetime(session['end_time'])

        # ── Time features ──────────────────────────────────────────────
        hour_of_day  = start_time.hour
        day_of_week  = start_time.weekday()   # 0=Mon, 6=Sun
        is_morning   = 1 if 6  <= hour_of_day < 12 else 0
        is_afternoon = 1 if 12 <= hour_of_day < 17 else 0
        is_evening   = 1 if 17 <= hour_of_day < 22 else 0
        is_weekend   = 1 if day_of_week >= 5 else 0

        # ── Duration ───────────────────────────────────────────────────
        actual_duration = (
            end_time - start_time
        ).total_seconds() / 60

        duration_minutes = max(1.0, actual_duration)

        if duration_minutes < 20:
            session_length_bucket = 0   # short
        elif duration_minutes <= 45:
            session_length_bucket = 1   # medium
        else:
            session_length_bucket = 2   # long

        # ── Focus score ────────────────────────────────────────────────
        focus_score = float(session.get('focus_score') or 5.0)

        # ── Session completed ──────────────────────────────────────────
        planned   = float(session.get('duration_minutes') or 25)
        completed = 1 if duration_minutes >= (planned * 0.80) else 0

        # ── Activity features ──────────────────────────────────────────
        activity = self._load_session_activity(session['id'])

        distraction_ratio  = 0.0
        distraction_count  = 0
        productive_ratio   = 0.0
        task_switches      = 0
        avg_visit_duration = 0.0

        if activity:
            total_time = sum(
                a.get('duration_seconds') or 0 for a in activity
            )

            distraction_time = sum(
                a.get('duration_seconds') or 0
                for a in activity
                if a.get('domain', '') in DISTRACTION_DOMAINS
            )

            productive_time = sum(
                a.get('duration_seconds') or 0
                for a in activity
                if a.get('domain', '') in PRODUCTIVE_DOMAINS
            )

            distraction_count = sum(
                1 for a in activity
                if a.get('domain', '') in DISTRACTION_DOMAINS
            )

            if total_time > 0:
                distraction_ratio = distraction_time / total_time
                productive_ratio  = productive_time  / total_time

            # Task switches = number of domain changes
            domains = [a.get('domain', '') for a in activity]
            task_switches = sum(
                1 for i in range(1, len(domains))
                if domains[i] != domains[i-1]
            )

            avg_visit_duration = (
                total_time / len(activity)
                if activity else 0.0
            )

        return [
            float(hour_of_day),
            float(day_of_week),
            float(duration_minutes),
            float(focus_score),
            float(distraction_ratio),
            float(distraction_count),
            float(task_switches),
            float(completed),
            float(avg_visit_duration),
            float(productive_ratio),
            float(is_morning),
            float(is_afternoon),
            float(is_evening),
            float(is_weekend),
            float(session_length_bucket)
        ]

    def _parse_datetime(self, value: str) -> datetime:
        """
        Parse timestamps from DB rows with tolerance for legacy formats.

        Handles:
        - trailing Z timezone marker
        - space separator instead of 'T'
        - fractional seconds longer than 6 digits
        """
        text = str(value or '').strip()
        if not text:
            raise ValueError('Empty datetime value')

        text = text.replace(' ', 'T', 1).replace('Z', '+00:00')

        # Normalize overly precise fractional seconds for fromisoformat.
        normalized = re.sub(
            r"\.(\d{6})\d+(?=([+-]\d{2}:\d{2})?$)",
            r".\1",
            text
        )

        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            dt = isoparse(normalized)

        return dt.replace(tzinfo=None)

    def _load_session_activity(
        self,
        session_id: str
    ) -> List[Dict]:
        """Load browsing activity for a session."""
        result = (
            self.supabase
            .table('browsing_activity')
            .select("domain, duration_seconds, timestamp")
            .eq('session_id', session_id)
            .execute()
        )
        return result.data or []
