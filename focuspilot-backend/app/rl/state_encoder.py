# app/rl/state_encoder.py
"""
State Encoder — converts raw session context into a discrete state key.

The Q-table uses discrete states (strings) as keys.
We encode continuous values into buckets.

State dimensions:
    1. risk_level:    low | medium | high | critical
    2. time_of_day:   morning | afternoon | evening | night
    3. day_type:      weekday | weekend
    4. session_phase: early | mid | late
       (how far into the session we are)
    5. distraction:   low | medium | high
    6. prev_outcome:  none | success | failure
       (did the last intervention work?)

Total states: 4 × 4 × 2 × 3 × 3 × 3 = 864 possible states
Each user gets their own Q-table over these 864 states.
"""

from datetime import datetime
from typing import Dict, Any, Optional


# All possible actions the agent can take
ACTIONS = [
    'send_warning',
    'block_sites',
    'start_break',
    'send_motivation',
    'do_nothing'
]


class StateEncoder:

    def encode(
        self,
        risk_score: float,
        session_start: datetime,
        session_duration_mins: float,
        planned_duration_mins: float,
        distraction_ratio: float,
        prev_intervention_outcome: Optional[str] = None
    ) -> str:
        """
        Encode session context into a discrete state key.

        Args:
            risk_score:                 0.0 - 1.0
            session_start:              When the session started
            session_duration_mins:      How long the session has run
            planned_duration_mins:      How long the session was planned for
            distraction_ratio:          0.0 - 1.0
            prev_intervention_outcome:  'success' | 'failure' | None

        Returns:
            State key string e.g. "high_morning_weekday_mid_medium_success"
        """
        risk_level    = self._encode_risk(risk_score)
        time_of_day   = self._encode_time(session_start)
        day_type      = self._encode_day(session_start)
        session_phase = self._encode_phase(
            session_duration_mins,
            planned_duration_mins
        )
        distraction   = self._encode_distraction(distraction_ratio)
        prev_outcome  = self._encode_prev_outcome(
            prev_intervention_outcome
        )

        return (
            f"{risk_level}_"
            f"{time_of_day}_"
            f"{day_type}_"
            f"{session_phase}_"
            f"{distraction}_"
            f"{prev_outcome}"
        )

    def decode(self, state_key: str) -> Dict[str, str]:
        """Decode a state key back into its components."""
        parts = state_key.split('_')
        if len(parts) != 6:
            return {}
        return {
            'risk_level':    parts[0],
            'time_of_day':   parts[1],
            'day_type':      parts[2],
            'session_phase': parts[3],
            'distraction':   parts[4],
            'prev_outcome':  parts[5]
        }

    # ── Encoders ───────────────────────────────────────────────────────

    def _encode_risk(self, risk_score: float) -> str:
        if risk_score < 0.30:   return 'low'
        if risk_score < 0.55:   return 'medium'
        if risk_score < 0.75:   return 'high'
        return 'critical'

    def _encode_time(self, dt: datetime) -> str:
        h = dt.hour
        if 6  <= h < 12:  return 'morning'
        if 12 <= h < 17:  return 'afternoon'
        if 17 <= h < 22:  return 'evening'
        return 'night'

    def _encode_day(self, dt: datetime) -> str:
        return 'weekend' if dt.weekday() >= 5 else 'weekday'

    def _encode_phase(
        self,
        elapsed: float,
        planned: float
    ) -> str:
        if planned <= 0:
            return 'mid'
        ratio = elapsed / planned
        if ratio < 0.33:  return 'early'
        if ratio < 0.66:  return 'mid'
        return 'late'

    def _encode_distraction(self, ratio: float) -> str:
        if ratio < 0.20:  return 'low'
        if ratio < 0.50:  return 'medium'
        return 'high'

    def _encode_prev_outcome(
        self,
        outcome: Optional[str]
    ) -> str:
        if outcome is None:      return 'none'
        if outcome == 'success': return 'success'
        return 'failure'


# Singleton
state_encoder = StateEncoder()
