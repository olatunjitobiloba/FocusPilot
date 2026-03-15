# app/ml/agent/orchestrator.py
"""
Agent Orchestrator — manages MonitoringAgent instances for all users.

One orchestrator runs per server instance.
It maintains a pool of agents, one per active user.
It runs the monitoring loop in a background thread.
"""

import threading
import time
from datetime import datetime
from typing import Dict, Optional

from app.ml.agent.monitor import MonitoringAgent
from app.database          import get_supabase


class AgentOrchestrator:
    """
    Singleton orchestrator that manages all user agents.
    """

    _instance = None
    _lock     = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._agents     = {}
                    cls._instance._running    = False
                    cls._instance._thread     = None
                    cls._instance._cycle_interval = 60  # seconds
        return cls._instance

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self):
        """Start the orchestrator background thread."""
        if self._running:
            print("⚠️  Orchestrator already running")
            return

        self._running = True
        self._thread  = threading.Thread(
            target=self._run_loop,
            daemon=True,   # Dies when main process dies
            name="AgentOrchestrator"
        )
        self._thread.start()
        print("🚀 Agent Orchestrator started")

    def stop(self):
        """Stop the orchestrator."""
        self._running = False
        print("🛑 Agent Orchestrator stopped")

    def _run_loop(self):
        """
        Main orchestrator loop.
        Runs every 60 seconds.
        """
        print("🔄 Orchestrator loop running...")

        while self._running:
            try:
                self._run_all_agents()
            except Exception as e:
                print(f"⚠️  Orchestrator error: {e}")

            time.sleep(self._cycle_interval)

    def _run_all_agents(self):
        """
        Find all users with active sessions and run their agents.
        """
        supabase = get_supabase()

        # Find users with active sessions
        result = (
            supabase
            .table('focus_sessions')
            .select("user_id")
            .is_('end_time', 'null')
            .execute()
        )

        active_user_ids = list(set(
            row['user_id'] for row in (result.data or [])
        ))

        if not active_user_ids:
            return

        print(f"🔄 Running agents for {len(active_user_ids)} active users")

        for user_id in active_user_ids:
            try:
                agent = self._get_or_create_agent(user_id)

                # Skip paused agents
                from app.ml.agent.states import AgentState
                if agent.state_machine.current_state == AgentState.PAUSED:
                    continue

                agent.run_cycle()

            except Exception as e:
                print(f"⚠️  Agent error for {user_id[:8]}: {e}")

    # ── Agent management ───────────────────────────────────────────────

    def _get_or_create_agent(self, user_id: str) -> MonitoringAgent:
        """Get existing agent or create new one for user."""
        if user_id not in self._agents:
            self._agents[user_id] = MonitoringAgent(user_id)
            print(f"✅ Created agent for user {user_id[:8]}")
        return self._agents[user_id]

    def get_agent(self, user_id: str) -> Optional[MonitoringAgent]:
        """Get agent for user (None if not active)."""
        return self._agents.get(user_id)

    def run_cycle_for_user(self, user_id: str) -> Dict:
        """
        Manually trigger one cycle for a specific user.
        Used by API endpoints for immediate assessment.
        """
        agent = self._get_or_create_agent(user_id)
        return agent.run_cycle()

    def pause_agent(self, user_id: str):
        """Pause agent for a user."""
        agent = self._get_or_create_agent(user_id)
        agent.pause()

    def resume_agent(self, user_id: str):
        """Resume agent for a user."""
        agent = self._get_or_create_agent(user_id)
        agent.resume()

    def get_all_statuses(self) -> Dict:
        """Get status of all active agents."""
        return {
            uid: agent.get_status()
            for uid, agent in self._agents.items()
        }

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def active_agent_count(self) -> int:
        return len(self._agents)


# Global singleton
orchestrator = AgentOrchestrator()
