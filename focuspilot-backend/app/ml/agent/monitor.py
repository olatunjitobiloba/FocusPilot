# app/ml/agent/monitor.py
"""
Monitoring Agent — the main agent loop.

This is the brain of FocusFlow.
It runs continuously, watching every user who has an active session.

Architecture:
    MonitoringAgent
        ├── Observer    (what is happening?)
        ├── Assessor    (how risky is it?)
        ├── StateMachine(what state are we in?)
        └── AlertSystem (what should we do?)

The agent runs as a background task in FastAPI.
It checks all active users every 60 seconds.
"""

import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from app.database              import get_supabase, upsert_agent_state
from app.ml.agent.observer     import Observer
from app.ml.agent.assessor     import Assessor
from app.ml.agent.states       import AgentState, StateMachine
from app.ml.agent.alert_system import AlertSystem
from app.ml.agent.decision_engine import DecisionEngine
from app.ml.agent.execution_agent import ExecutionAgent


class MonitoringAgent:
    """
    The core monitoring agent for a single user.

    One MonitoringAgent instance per user.
    Managed by AgentOrchestrator (below).
    """

    def __init__(self, user_id: str):
        self.user_id       = user_id
        self.observer      = Observer(user_id)
        self.assessor      = Assessor(user_id)
        self.state_machine = StateMachine(AgentState.IDLE)
        self.alert_system  = AlertSystem(user_id)
        self.decision_engine = DecisionEngine(user_id)
        self.execution_agent = ExecutionAgent(user_id)
        self.supabase      = get_supabase()

        # Agent memory
        self.last_observation  = None
        self.last_assessment   = None
        self.cycle_count       = 0
        self.interventions_today = 0

    # ── Main loop ──────────────────────────────────────────────────────

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one monitoring cycle.
        Called every 60 seconds by the orchestrator.

        Returns:
            Cycle result with observation, assessment, actions taken
        """
        self.cycle_count += 1
        cycle_start = datetime.utcnow()

        print(f"\nCycle {self.cycle_count} | "
              f"User {self.user_id[:8]} | "
              f"State: {self.state_machine.current_state}")

        # ── Step 1: Observe ────────────────────────────────────────────
        observation = self.observer.observe()
        self.last_observation = observation

        # ── Step 2: Assess ─────────────────────────────────────────────
        assessment = self.assessor.assess(observation)
        self.last_assessment = assessment

        print(f"   Risk: {assessment['risk_score']:.2f} "
              f"({assessment['risk_level']}) | "
              f"Recommended: {assessment['recommended_state']}")

        # ── Step 3: Transition state ───────────────────────────────────
        state_changed = self._update_state(assessment, observation)

        # ── Step 4: Act if needed ──────────────────────────────────────
        actions_taken = []

        if state_changed:
            action = self._act_on_state_change(
                assessment,
                observation
            )
            if action:
                actions_taken.append(action)

        # ── Step 5: Persist to database ────────────────────────────────
        self._persist_cycle(
            observation,
            assessment,
            actions_taken
        )

        cycle_duration = (
            datetime.utcnow() - cycle_start
        ).total_seconds()

        return {
            'cycle':          self.cycle_count,
            'state':          self.state_machine.current_state,
            'risk_score':     assessment['risk_score'],
            'risk_level':     assessment['risk_level'],
            'actions_taken':  actions_taken,
            'signals':        assessment['signals'],
            'cycle_duration': round(cycle_duration, 2),
            'timestamp':      cycle_start.isoformat()
        }

    # ── State management ───────────────────────────────────────────────

    def _update_state(
        self,
        assessment: Dict,
        observation: Dict
    ) -> bool:
        """
        Update agent state based on assessment.
        Returns True if state changed.
        """
        current    = self.state_machine.current_state
        recommended = assessment['recommended_state']

        # If agent is paused, do nothing
        if current == AgentState.PAUSED:
            return False

        # If state matches recommendation, no change needed
        if current == recommended:
            return False

        # Attempt transition
        reason = (
            f"Risk={assessment['risk_score']:.2f}, "
            f"Level={assessment['risk_level']}"
        )
        return self.state_machine.transition(recommended, reason)

    def _act_on_state_change(
        self,
        assessment: Dict,
        observation: Dict
    ) -> Optional[Dict]:
        """
        Use Decision Engine to decide what action to take.
        """
        new_state = self.state_machine.current_state

        if new_state in [AgentState.AT_RISK, AgentState.INTERVENING]:
            # Decision Engine decides what to do.
            decision = self.decision_engine.decide(
                assessment=assessment,
                observation=observation
            )

            if decision['should_intervene']:
                self.interventions_today += 1

                # Alert system notifies user.
                self.alert_system.send_intervention(
                    risk_score=assessment['risk_score'],
                    signals=assessment['signals'],
                    observation=observation,
                    message=decision['message'],
                    intervention_type=decision['intervention_type']
                )

                # Execution Agent acts autonomously.
                execution = self.execution_agent.execute(
                    decision=decision,
                    observation=observation
                )

                return {
                    'decision': decision,
                    'execution': execution
                }

        elif new_state == AgentState.ACTIVE:
            if self.state_machine.history:
                prev = self.state_machine.history[-1]['from']
                if prev in [AgentState.AT_RISK, AgentState.INTERVENING]:
                    return self.alert_system.send_recovery(
                        risk_score=assessment['risk_score']
                    )

        return None

    # ── Persistence ────────────────────────────────────────────────────

    def _persist_cycle(
        self,
        observation: Dict,
        assessment: Dict,
        actions: list
    ):
        """Save cycle data to database."""
        try:
            # Update agent state in DB
            upsert_agent_state({
                'user_id':    self.user_id,
                'state':      self.state_machine.current_state.value,
                'risk_score': assessment['risk_score'],
                'last_cycle': datetime.utcnow().isoformat(),
                'cycle_count': self.cycle_count
            })

            # Log event
            self.supabase.table('agent_events').insert({
                'user_id':    self.user_id,
                'event_type': 'monitoring_cycle',
                'event_data': {
                    'risk_score':  assessment['risk_score'],
                    'risk_level':  assessment['risk_level'],
                    'signals':     assessment['signals'],
                    'actions':     actions,
                    'cycle':       self.cycle_count
                },
                'state_before': (
                    self.state_machine.history[-1]['from'].value
                    if self.state_machine.history else 'idle'
                ),
                'state_after': self.state_machine.current_state.value
            }).execute()

            # Save risk score to history
            self.supabase.table('risk_history').insert({
                'user_id':     self.user_id,
                'risk_score':  assessment['risk_score'],
                'assessed_at': datetime.utcnow().isoformat()
            }).execute()

        except Exception as e:
            print(f"WARNING Persist error: {e}")

    # ── Control ────────────────────────────────────────────────────────

    def pause(self):
        """Pause the agent."""
        self.state_machine.transition(AgentState.PAUSED, "User paused")

    def resume(self):
        """Resume the agent."""
        self.state_machine.transition(AgentState.IDLE, "User resumed")

    def get_status(self) -> Dict:
        """Get current agent status."""
        return {
            'user_id':             self.user_id,
            'state':               self.state_machine.current_state.value,
            'state_description':   self.state_machine.get_state_description(),
            'cycle_count':         self.cycle_count,
            'interventions_today': self.interventions_today,
            'last_risk_score':     (
                self.last_assessment['risk_score']
                if self.last_assessment else None
            ),
            'last_cycle':          (
                self.last_assessment['assessed_at']
                if self.last_assessment else None
            )
        }
