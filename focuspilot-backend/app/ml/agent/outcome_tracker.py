# app/ml/agent/outcome_tracker.py
"""
Outcome Tracker — measures whether interventions worked.

After an intervention, the tracker:
1. Waits 5-10 minutes
2. Checks if risk score dropped
3. Records the outcome
4. Updates user behavior profile

This is how the agent LEARNS over time.
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.database import get_supabase
from app.ml.agent.history_analyzer import HistoryAnalyzer


class OutcomeTracker:

    # How long to wait before measuring outcome
    MEASUREMENT_DELAY_MINS = 8

    # What counts as a successful intervention
    SUCCESS_RISK_DROP = 0.15   # Risk must drop by at least 15%

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()
        self.analyzer = HistoryAnalyzer(user_id)

    def schedule_outcome_check(
        self,
        intervention_id: str,
        risk_score_before: float,
        intervention_type: str
    ):
        """
        Schedule an outcome check in the background.
        Runs after MEASUREMENT_DELAY_MINS minutes.
        """
        def _check():
            import time
            time.sleep(self.MEASUREMENT_DELAY_MINS * 60)

            self._measure_and_record(
                intervention_id=intervention_id,
                risk_score_before=risk_score_before,
                intervention_type=intervention_type
            )

        thread = threading.Thread(
            target=_check,
            daemon=True,
            name=f"OutcomeTracker-{intervention_id[:8]}"
        )
        thread.start()

    def _measure_and_record(
        self,
        intervention_id: str,
        risk_score_before: float,
        intervention_type: str
    ):
        """
        Measure current risk and compare to pre-intervention risk.
        Record outcome and update user profile.
        """
        try:
            # Get current risk from risk_history
            result = (
                self.supabase
                .table('risk_history')
                .select("risk_score")
                .eq('user_id', self.user_id)
                .order('assessed_at', desc=True)
                .limit(1)
                .execute()
            )

            if not result.data:
                return

            risk_score_after = result.data[0]['risk_score']
            risk_drop        = risk_score_before - risk_score_after

            # Determine outcome
            if risk_drop >= self.SUCCESS_RISK_DROP:
                outcome = 'success'
            elif risk_drop >= 0:
                outcome = 'partial'
            else:
                outcome = 'ignored'   # Risk went UP after intervention

            print(
                f"Outcome for {intervention_type}: "
                f"{outcome} "
                f"(before={risk_score_before:.2f}, "
                f"after={risk_score_after:.2f}, "
                f"drop={risk_drop:.2f})"
            )

            # Record outcome
            self.supabase.table('intervention_outcomes').insert({
                'user_id':            self.user_id,
                'intervention_type':  intervention_type,
                'risk_score_before':  risk_score_before,
                'risk_score_after':   risk_score_after,
                'outcome':            outcome,
                'time_to_refocus_mins': self.MEASUREMENT_DELAY_MINS
            }).execute()

            # Update intervention record
            self.supabase.table('agent_interventions').update({
                'outcome':     outcome,
                'resolved_at': datetime.utcnow().isoformat()
            }).eq('id', intervention_id).execute()

            # Update user behavior profile
            self.analyzer.update_profile({
                'intervention_type': intervention_type,
                'outcome':           outcome,
                'risk_drop':         risk_drop
            })

        except Exception as e:
            print(f"WARNING Outcome tracking error: {e}")

    def get_outcome_stats(self) -> Dict:
        """Get overall intervention effectiveness stats."""
        result = (
            self.supabase
            .table('intervention_outcomes')
            .select("outcome, intervention_type")
            .eq('user_id', self.user_id)
            .execute()
        )

        outcomes = result.data or []

        if not outcomes:
            return {
                'total':       0,
                'success_rate': 0,
                'by_type':     {}
            }

        total   = len(outcomes)
        success = sum(1 for o in outcomes if o['outcome'] == 'success')

        # Group by type
        by_type: Dict[str, Dict] = {}
        for o in outcomes:
            t = o['intervention_type']
            if t not in by_type:
                by_type[t] = {'total': 0, 'success': 0}
            by_type[t]['total'] += 1
            if o['outcome'] == 'success':
                by_type[t]['success'] += 1

        for t in by_type:
            by_type[t]['rate'] = round(
                by_type[t]['success'] / by_type[t]['total'], 2
            )

        return {
            'total':        total,
            'success_rate': round(success / total, 2),
            'by_type':      by_type
        }
