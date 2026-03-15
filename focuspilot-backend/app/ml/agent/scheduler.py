# app/ml/agent/scheduler.py
"""
Action Scheduler — executes scheduled actions at the right time.

Runs as a background thread.
Checks for pending scheduled actions every 60 seconds.
Executes them when their time comes.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Dict
from app.database import get_supabase


class ActionScheduler:
    """Background scheduler for future actions."""

    _instance = None
    _lock     = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._running = False
                    cls._instance._thread  = None
        return cls._instance

    def start(self):
        """Start the scheduler background thread."""
        if self._running:
            return

        self._running = True
        self._thread  = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="ActionScheduler"
        )
        self._thread.start()
        print("⏰ Action Scheduler started")

    def stop(self):
        self._running = False

    def _run_loop(self):
        """Check and execute pending scheduled actions every 60 seconds."""
        while self._running:
            try:
                self._execute_due_actions()
            except Exception as e:
                print(f"⚠️  Scheduler error: {e}")
            time.sleep(60)

    def _execute_due_actions(self):
        """Find and execute all actions that are due."""
        supabase = get_supabase()
        now      = datetime.now(timezone.utc).isoformat()

        # Get all pending actions that are due
        result = (
            supabase
            .table('scheduled_actions')
            .select("*")
            .eq('status', 'pending')
            .lte('scheduled_for', now)
            .execute()
        )

        due_actions = result.data or []

        if not due_actions:
            return

        print(f"⏰ Executing {len(due_actions)} scheduled actions")

        for action in due_actions:
            try:
                self._execute_scheduled(action, supabase)
            except Exception as e:
                print(f"⚠️  Scheduled action error: {e}")

    def _execute_scheduled(self, action: Dict, supabase):
        """Execute one scheduled action."""
        from app.ml.agent.executors import (
            SiteBlockExecutor, NudgeExecutor
        )

        user_id     = action['user_id']
        action_type = action['action_type']
        action_data = action.get('action_data', {})

        if action_type == 'unblock_sites':
            blocker = SiteBlockExecutor(user_id)
            blocker.unblock()

        elif action_type == 'send_nudge':
            nudger = NudgeExecutor(user_id)
            nudger.send_nudge(
                title=action_data.get('title', '⏰ Reminder'),
                message=action_data.get('message', 'Time to focus!')
            )

        # Mark as executed
        supabase.table('scheduled_actions').update({
            'status':      'executed',
            'executed_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', action['id']).execute()

        print(f"   ✅ Executed scheduled: {action_type} for {user_id[:8]}")


# Global singleton
action_scheduler = ActionScheduler()
