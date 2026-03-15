# app/ml/agent/history_analyzer.py
"""
History Analyzer — learns what works for each specific user.

Every user is different:
- Some respond to gentle reminders
- Some need aggressive blocking
- Some prefer motivational messages
- Some ignore everything (need different approach)

The history analyzer reads past intervention outcomes
and builds a preference profile for the user.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from app.database import get_supabase


class HistoryAnalyzer:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    def get_best_intervention(
        self,
        available_types: List[str]
    ) -> str:
        """
        Return the intervention type most likely to work
        for this user, from the available options.

        Args:
            available_types: List of intervention types to choose from

        Returns:
            Best intervention type ID
        """
        success_rates = self._get_success_rates()

        if not success_rates:
            # No history — use default
            return 'focus_reminder'

        # Find best from available types
        best_type = None
        best_rate = -1

        for iv_type in available_types:
            rate = success_rates.get(iv_type, 0.5)  # Default 50%
            if rate > best_rate:
                best_rate = rate
                best_type = iv_type

        return best_type or available_types[0]

    def _get_success_rates(self) -> Dict[str, float]:
        """
        Calculate success rate per intervention type.

        Success = risk score dropped after intervention.
        Returns dict: {intervention_type: success_rate}
        """
        result = (
            self.supabase
            .table('intervention_outcomes')
            .select("intervention_type, outcome")
            .eq('user_id', self.user_id)
            .execute()
        )

        outcomes = result.data or []

        if not outcomes:
            return {}

        # Count successes and totals per type
        counts: Dict[str, Dict[str, int]] = {}

        for outcome in outcomes:
            iv_type = outcome['intervention_type']
            result_val = outcome['outcome']

            if iv_type not in counts:
                counts[iv_type] = {'success': 0, 'total': 0}

            counts[iv_type]['total'] += 1

            if result_val == 'success':
                counts[iv_type]['success'] += 1

        # Compute rates
        rates = {}
        for iv_type, data in counts.items():
            if data['total'] > 0:
                rates[iv_type] = round(
                    data['success'] / data['total'], 3
                )

        return rates

    def get_user_profile(self) -> Dict:
        """
        Build a behavioral profile for the user.
        Used to personalize intervention messages.
        """
        # Get from DB (pre-computed)
        result = (
            self.supabase
            .table('user_behavior_profile')
            .select("*")
            .eq('user_id', self.user_id)
            .execute()
        )

        if result.data:
            return result.data[0]

        # Build default profile
        return {
            'user_id':                   self.user_id,
            'best_intervention':         'focus_reminder',
            'worst_intervention':        None,
            'avg_refocus_time_mins':     5.0,
            'total_interventions':       0,
            'successful_interventions':  0,
            'preferred_message_tone':    'neutral'
        }

    def update_profile(self, outcome: Dict):
        """
        Update user behavior profile after an intervention outcome.
        Called by OutcomeTracker after measuring result.
        """
        profile       = self.get_user_profile()
        success_rates = self._get_success_rates()

        # Find best and worst intervention types
        if success_rates:
            best  = max(success_rates, key=success_rates.get)
            worst = min(success_rates, key=success_rates.get)
        else:
            best  = 'focus_reminder'
            worst = None

        # Update totals
        total      = profile.get('total_interventions', 0) + 1
        successful = profile.get('successful_interventions', 0)

        if outcome.get('outcome') == 'success':
            successful += 1

        # Determine preferred tone based on what works
        tone = 'neutral'
        if success_rates.get('motivational_message', 0) > 0.6:
            tone = 'motivational'
        elif success_rates.get('accountability_check', 0) > 0.6:
            tone = 'direct'
        elif success_rates.get('break_suggestion', 0) > 0.6:
            tone = 'gentle'

        # Upsert profile
        self.supabase.table('user_behavior_profile').upsert({
            'user_id':                  self.user_id,
            'best_intervention':        best,
            'worst_intervention':       worst,
            'total_interventions':      total,
            'successful_interventions': successful,
            'preferred_message_tone':   tone,
            'updated_at':               datetime.utcnow().isoformat()
        }).execute()
