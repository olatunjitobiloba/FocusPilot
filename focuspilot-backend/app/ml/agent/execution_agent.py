# app/ml/agent/execution_agent.py
"""
Execution Agent — executes decisions autonomously.

This is the final layer of the agent pipeline:
Monitor → Assess → Decide → EXECUTE

The Execution Agent:
1. Receives a decision from the Decision Engine
2. Maps it to the right executor
3. Logs the action
4. Handles errors gracefully
5. Returns execution result
"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from app.ml.agent.actions      import get_action, ACTION_REGISTRY
from app.ml.agent.action_logger import ActionLogger
from app.ml.agent.executors    import (
    SiteBlockExecutor,
    SessionExecutor,
    NudgeExecutor
)
from app.database import get_supabase


class ExecutionAgent:

    ACTION_ALIAS_TO_TYPE = {
        'block': 'block_sites',
        'session': 'start_session',
        'nudge': 'schedule_nudge',
        'focus': 'activate_focus_mode',
    }

    NUDGE_TITLE_BY_INTERVENTION = {
        'focus_reminder': 'Focus Reminder',
        'motivational_message': 'Motivational Boost',
        'break_suggestion': 'Break Suggestion',
        'accountability_check': 'Accountability Check',
    }

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.logger   = ActionLogger(user_id)
        self.blocker  = SiteBlockExecutor(user_id)
        self.sessions = SessionExecutor(user_id)
        self.nudger   = NudgeExecutor(user_id)
        self.supabase = get_supabase()

    # ── Main execute method ────────────────────────────────────────────

    def execute(
        self,
        decision: Dict[str, Any],
        observation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a decision from the Decision Engine.

        Args:
            decision:    Output from DecisionEngine.decide()
            observation: Current observation context

        Returns:
            Execution result dict
        """
        if not decision.get('should_intervene'):
            return {
                'executed':  False,
                'reason':    decision.get('reason', 'No intervention needed')
            }

        iv_type    = decision.get('intervention_type', 'focus_reminder')
        risk_score = decision.get('risk_score', 0.5)
        message    = decision.get('message', '')

        # Map intervention type to action
        action_type = self._map_intervention_to_action(
            iv_type,
            observation
        )

        # Build action data
        action_data = self._build_action_data(
            action_type,
            iv_type,
            message,
            observation
        )

        # Log action (before execution)
        action_id = self.logger.log_action(
            action_type=action_type,
            action_data=action_data,
            trigger_reason=(
                f"Intervention: {iv_type} | "
                f"Risk: {risk_score:.2f}"
            ),
            risk_score=risk_score
        )

        # Execute
        try:
            result = self._execute_action(
                action_type=action_type,
                action_data=action_data,
                observation=observation
            )

            self.logger.mark_completed(action_id, result)

            print(
                f"   ✅ Executed: {action_type} | "
                f"Result: {result.get('message', 'done')}"
            )

            return {
                'executed':    True,
                'action_type': action_type,
                'action_id':   action_id,
                'result':      result,
                'iv_type':     iv_type
            }

        except Exception as e:
            error_msg = str(e)
            self.logger.mark_failed(action_id, error_msg)

            print(f"   ❌ Execution failed: {action_type} | {error_msg}")

            return {
                'executed':    False,
                'action_type': action_type,
                'action_id':   action_id,
                'error':       error_msg
            }

    # ── Undo ───────────────────────────────────────────────────────────

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        try:
            UUID(str(value))
            return True
        except (TypeError, ValueError):
            return False

    def _resolve_action_id(self, action_ref: str) -> Optional[str]:
        """
        Resolve either an action UUID or a friendly alias (e.g. 'block').
        """
        if self._is_valid_uuid(action_ref):
            return action_ref

        action_type = self.ACTION_ALIAS_TO_TYPE.get(str(action_ref).lower())
        if not action_type:
            return None

        result = (
            self.supabase
            .table('agent_actions')
            .select('id')
            .eq('user_id', self.user_id)
            .eq('action_type', action_type)
            .eq('is_undoable', True)
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        return result.data[0].get('id')

    def _undo_alias_fallback(self, action_ref: str) -> Optional[Dict[str, Any]]:
        """
        Support manual undo flows when no agent_actions row exists.
        """
        ref = str(action_ref).lower()

        if ref in {'block', 'focus'}:
            self.blocker.unblock()
            return {
                'undone': True,
                'action_type': 'unblock_sites',
                'action_id': None,
                'message': 'Sites have been unblocked'
            }

        return None

    def undo(self, action_id: str) -> Dict[str, Any]:
        """
        Undo a previously executed action.

        Supported undos:
        - block_sites → unblock_sites
        - start_session → end_session
        - schedule_nudge → cancel scheduled action
        """
        resolved_action_id = self._resolve_action_id(action_id)
        if not resolved_action_id:
            fallback_result = self._undo_alias_fallback(action_id)
            if fallback_result:
                return fallback_result

            return {
                'undone': False,
                'reason': (
                    "Action not found. Use a valid action UUID "
                    "or alias: block, session, nudge, focus"
                )
            }

        # Get action from DB
        result = (
            self.supabase
            .table('agent_actions')
            .select("*")
            .eq('id', resolved_action_id)
            .eq('user_id', self.user_id)
            .execute()
        )

        if not result.data:
            return {
                'undone':  False,
                'reason':  'Action not found'
            }

        action = result.data[0]

        if not action.get('is_undoable'):
            return {
                'undone': False,
                'reason': 'This action cannot be undone'
            }

        if action.get('status') == 'undone':
            return {
                'undone': False,
                'reason': 'Already undone'
            }

        # Execute undo
        action_type = action['action_type']

        try:
            if action_type == 'block_sites':
                self.blocker.unblock()

            elif action_type == 'start_session':
                session_id = action['result'].get('session_id')
                if session_id:
                    self.sessions.auto_end_session(
                        session_id=session_id,
                        reason="User undid auto-start"
                    )

            elif action_type == 'schedule_nudge':
                schedule_id = action['result'].get('schedule_id')
                if schedule_id:
                    self.supabase.table('scheduled_actions').update({
                        'status': 'cancelled'
                    }).eq('id', schedule_id).execute()

            elif action_type == 'activate_focus_mode':
                self.blocker.unblock()

            self.logger.mark_undone(resolved_action_id)

            return {
                'undone':      True,
                'action_type': action_type,
                'action_id':   resolved_action_id,
                'message':     f'{action_type} has been undone'
            }

        except Exception as e:
            return {
                'undone': False,
                'reason': str(e)
            }

    # ── Action mapping ─────────────────────────────────────────────────

    def _map_intervention_to_action(
        self,
        iv_type: str,
        observation: Dict
    ) -> str:
        """
        Map intervention type to executable action.

        Logic:
        - site_block → block_sites
        - session_restart → end_session + start_session
        - focus_reminder → send_nudge
        - break_suggestion → send_nudge
        - motivational_message → send_nudge
        - accountability_check → send_nudge
        """
        metrics = observation.get('session_metrics', {})
        elapsed = metrics.get('elapsed_minutes', 0)

        mapping = {
            'site_block':           'block_sites',
            'session_restart':      'end_session',
            'focus_reminder':       'send_nudge',
            'break_suggestion':     'send_nudge',
            'motivational_message': 'send_nudge',
            'accountability_check': 'send_nudge'
        }

        return mapping.get(iv_type, 'send_nudge')

    def _build_action_data(
        self,
        action_type: str,
        iv_type: str,
        message: str,
        observation: Dict
    ) -> Dict:
        """Build the data payload for an action."""
        metrics    = observation.get('session_metrics', {})
        session    = observation.get('active_session', {})

        if action_type == 'block_sites':
            return {
                'domains':          SiteBlockExecutor.DEFAULT_BLOCK_DOMAINS,
                'duration_minutes': 25,
                'reason':           f'Intervention: {iv_type}'
            }

        elif action_type == 'end_session':
            return {
                'session_id': session.get('id', ''),
                'reason':     'Excessive procrastination — agent ended session'
            }

        elif action_type == 'start_session':
            return {
                'duration_minutes': 25,
                'reason':           'Agent auto-started recovery session'
            }

        elif action_type == 'send_nudge':
            nudge_title = self.NUDGE_TITLE_BY_INTERVENTION.get(
                iv_type,
                'Focus Reminder'
            )
            return {
                'title':   nudge_title,
                'message': message
            }

        return {'message': message}

    def _execute_action(
        self,
        action_type: str,
        action_data: Dict,
        observation: Dict
    ) -> Dict:
        """Route to the correct executor."""

        if action_type == 'block_sites':
            return self.blocker.block(
                domains=action_data.get('domains'),
                duration_minutes=action_data.get('duration_minutes', 25),
                reason=action_data.get('reason', '')
            )

        elif action_type == 'unblock_sites':
            return self.blocker.unblock()

        elif action_type == 'start_session':
            return self.sessions.auto_start_session(
                duration_minutes=action_data.get('duration_minutes', 25),
                reason=action_data.get('reason', '')
            )

        elif action_type == 'end_session':
            return self.sessions.auto_end_session(
                session_id=action_data.get('session_id', ''),
                reason=action_data.get('reason', '')
            )

        elif action_type == 'send_nudge':
            return self.nudger.send_nudge(
                title=action_data.get('title', '🎯 Focus'),
                message=action_data.get('message', 'Stay focused!')
            )

        elif action_type == 'schedule_nudge':
            return self.nudger.schedule_nudge(
                message=action_data.get('message', ''),
                scheduled_for=action_data.get('scheduled_for', ''),
                title=action_data.get('title', '⏰ Reminder')
            )

        elif action_type == 'activate_focus_mode':
            # Compound action: block sites + start session
            block_result = self.blocker.block(
                duration_minutes=action_data.get('duration_minutes', 25)
            )
            session_result = self.sessions.auto_start_session(
                duration_minutes=action_data.get('duration_minutes', 25)
            )
            return {
                'block_result':   block_result,
                'session_result': session_result,
                'message':        'Focus mode fully activated'
            }

        raise ValueError(f"Unknown action type: {action_type}")
