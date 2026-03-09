# app/ml/distraction_scorer.py

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any
import math


class DistractionScorer:
    """
    Scores websites by how much they hurt user focus.

    Scoring factors:
    1. Frequency during low-focus sessions (weight: 0.35)
    2. Time spent on site during sessions (weight: 0.25)
    3. Correlation with session abandonment (weight: 0.20)
    4. Visit timing (right before session ends early) (weight: 0.20)
    """

    def __init__(self):
        self.weights = {
            'low_focus_frequency': 0.35,
            'time_spent':          0.25,
            'session_abandonment': 0.20,
            'timing_correlation':  0.20
        }

    def score_domains(
        self,
        sessions: List[Dict],
        activities: List[Dict]
    ) -> List[Dict]:
        """
        Main scoring function.
        Returns list of domains with distraction scores.
        """

        if not sessions or not activities:
            return []

        # Build lookup: session_id → session data
        session_map = {s['id']: s for s in sessions}

        # Group activities by domain
        domain_activities = defaultdict(list)
        for activity in activities:
            domain_activities[activity['domain']].append(activity)

        scored_domains = []

        for domain, acts in domain_activities.items():

            # ── Factor 1: Low-focus frequency ──────────────────────────
            # How often does this domain appear in low-focus sessions?
            low_focus_visits  = 0
            total_visits      = len(acts)

            for act in acts:
                session = session_map.get(act.get('session_id'))
                if session and session.get('focus_score'):
                    if session['focus_score'] < 5:
                        low_focus_visits += 1

            low_focus_ratio = (
                low_focus_visits / total_visits if total_visits > 0 else 0
            )

            # ── Factor 2: Time spent ────────────────────────────────────
            # Normalize total time (cap at 120 minutes for scoring)
            total_seconds = sum(a.get('duration_seconds', 0) for a in acts)
            total_minutes = total_seconds / 60
            time_score    = min(total_minutes / 120, 1.0)

            # ── Factor 3: Session abandonment ──────────────────────────
            # Did the user end the session early after visiting this site?
            abandonment_count = 0
            for act in acts:
                session = session_map.get(act.get('session_id'))
                if not session:
                    continue

                # Session abandoned = ended in < 10 minutes
                duration = session.get('duration_minutes', 0) or 0
                if duration < 10 and session.get('end_time'):
                    abandonment_count += 1

            abandonment_ratio = (
                abandonment_count / total_visits if total_visits > 0 else 0
            )

            # ── Factor 4: Timing correlation ───────────────────────────
            # Did visits happen right before session ended?
            timing_score = self._calculate_timing_score(acts, session_map)

            # ── Composite distraction score (0–100) ────────────────────
            raw_score = (
                low_focus_ratio  * self.weights['low_focus_frequency'] +
                time_score       * self.weights['time_spent']          +
                abandonment_ratio* self.weights['session_abandonment'] +
                timing_score     * self.weights['timing_correlation']
            )

            distraction_score = round(raw_score * 100, 2)

            # ── Confidence level ───────────────────────────────────────
            confidence = self._get_confidence(total_visits)

            # ── Human-readable reason ──────────────────────────────────
            reason = self._generate_reason(
                domain,
                low_focus_ratio,
                total_minutes,
                abandonment_ratio,
                timing_score
            )

            if distraction_score > 20:          # Only suggest meaningful distractors
                scored_domains.append({
                    'domain':            domain,
                    'distraction_score': distraction_score,
                    'confidence':        confidence,
                    'reason':            reason,
                    'total_visits':      total_visits,
                    'total_minutes':     round(total_minutes, 1),
                    'low_focus_visits':  low_focus_visits,
                    'abandonment_count': abandonment_count,
                    'factors': {
                        'low_focus_ratio':   round(low_focus_ratio, 2),
                        'time_score':        round(time_score, 2),
                        'abandonment_ratio': round(abandonment_ratio, 2),
                        'timing_score':      round(timing_score, 2)
                    }
                })

        # Sort by distraction score descending
        scored_domains.sort(key=lambda x: x['distraction_score'], reverse=True)
        return scored_domains

    # ── Private helpers ────────────────────────────────────────────────

    def _calculate_timing_score(
        self,
        activities: List[Dict],
        session_map: Dict
    ) -> float:
        """
        Score based on whether visits happen near the END of sessions.
        High score = user visits this site then stops studying.
        """
        timing_scores = []

        for act in activities:
            session = session_map.get(act.get('session_id'))
            if not session or not session.get('end_time'):
                continue

            try:
                act_time     = datetime.fromisoformat(
                    act['timestamp'].replace('Z', '+00:00')
                )
                session_end  = datetime.fromisoformat(
                    session['end_time'].replace('Z', '+00:00')
                )
                session_start = datetime.fromisoformat(
                    session['start_time'].replace('Z', '+00:00')
                )

                total_duration = (session_end - session_start).total_seconds()
                if total_duration <= 0:
                    continue

                # How far into the session was this visit? (0 = start, 1 = end)
                time_into_session = (
                    (act_time - session_start).total_seconds() / total_duration
                )

                # Visits in the last 20% of a session are suspicious
                if time_into_session > 0.8:
                    timing_scores.append(1.0)
                elif time_into_session > 0.6:
                    timing_scores.append(0.5)
                else:
                    timing_scores.append(0.0)

            except Exception:
                continue

        return (
            sum(timing_scores) / len(timing_scores)
            if timing_scores else 0.0
        )

    def _get_confidence(self, visit_count: int) -> str:
        if visit_count >= 10:
            return 'high'
        elif visit_count >= 5:
            return 'medium'
        else:
            return 'low'

    def _generate_reason(
        self,
        domain: str,
        low_focus_ratio: float,
        total_minutes: float,
        abandonment_ratio: float,
        timing_score: float
    ) -> str:
        """Generate a human-readable explanation for the suggestion."""

        reasons = []

        if low_focus_ratio > 0.6:
            pct = round(low_focus_ratio * 100)
            reasons.append(
                f"You visit {domain} during {pct}% of your low-focus sessions"
            )

        if total_minutes > 30:
            reasons.append(
                f"You spend {round(total_minutes)} minutes on it during study time"
            )

        if abandonment_ratio > 0.3:
            pct = round(abandonment_ratio * 100)
            reasons.append(
                f"{pct}% of sessions end shortly after visiting {domain}"
            )

        if timing_score > 0.5:
            reasons.append(
                f"You tend to visit {domain} right before stopping your sessions"
            )

        if reasons:
            return '. '.join(reasons) + '.'

        return f"{domain} appears frequently during your study sessions."
