# app/ml/agent/action_logger.py
"""
Action Logger — logs every autonomous action the agent takes.

Every action is logged with:
- What was done
- Why it was done
- The result
- Whether it can be undone
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import time
from app.database import get_supabase
from app.ml.agent.actions import get_action


class ActionLogger:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    def log_action(
        self,
        action_type: str,
        action_data: Dict,
        trigger_reason: str,
        risk_score: float
    ) -> str:
        """
        Log an action BEFORE it executes.
        Returns the action ID for later updates.
        """
        action_def = get_action(action_type)
        is_undoable = action_def.is_undoable if action_def else False

        payload = {
            'user_id':               self.user_id,
            'action_type':           action_type,
            'action_data':           action_data,
            'trigger_reason':        trigger_reason,
            'risk_score_at_trigger': risk_score,
            'status':                'executing',
            'is_undoable':           is_undoable
        }

        for attempt in range(3):
            try:
                result = (
                    self.supabase
                    .table('agent_actions')
                    .insert(payload)
                    .execute()
                )
                if result.data:
                    return result.data[0]['id']
                return 'unknown'
            except Exception as e:
                if attempt == 2:
                    print(f"WARNING Action log failed for {self.user_id[:8]}: {e}")
                    return 'unknown'
                time.sleep(0.3)

    def mark_completed(
        self,
        action_id: str,
        result: Dict
    ):
        """Mark action as successfully completed."""
        self.supabase.table('agent_actions').update({
            'status':       'completed',
            'result':       result,
            'completed_at': datetime.utcnow().isoformat()
        }).eq('id', action_id).execute()

    def mark_failed(
        self,
        action_id: str,
        error: str
    ):
        """Mark action as failed."""
        self.supabase.table('agent_actions').update({
            'status': 'failed',
            'result': {'error': error},
            'completed_at': datetime.utcnow().isoformat()
        }).eq('id', action_id).execute()

    def mark_undone(self, action_id: str):
        """Mark action as undone by user."""
        self.supabase.table('agent_actions').update({
            'status':    'undone',
            'undone_at': datetime.utcnow().isoformat()
        }).eq('id', action_id).execute()

    def get_recent_actions(
        self,
        limit: int = 20
    ) -> List[Dict]:
        """Get recent actions for this user."""
        result = (
            self.supabase
            .table('agent_actions')
            .select("*")
            .eq('user_id', self.user_id)
            .order('created_at', desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def get_undoable_actions(self) -> List[Dict]:
        """Get actions that can still be undone."""
        result = (
            self.supabase
            .table('agent_actions')
            .select("*")
            .eq('user_id', self.user_id)
            .eq('is_undoable', True)
            .eq('status', 'completed')
            .execute()
        )
        return result.data or []
