# app/ml/agent/pipeline.py
"""
Agent Pipeline — the unified entry point for the full agent system.

This class connects:
    MonitoringAgent → DecisionEngine → ExecutionAgent

Instead of calling each agent separately, call pipeline.run_cycle()
and the entire system executes in the correct order.

Usage:
    pipeline = AgentPipeline(user_id="abc-123")
    result   = pipeline.run_cycle()
"""

from datetime import datetime
from typing  import Dict, Any, Optional
import re

from app.ml.agent.observer        import Observer
from app.ml.agent.assessor        import Assessor
from app.ml.agent.states          import AgentState, StateMachine
from app.ml.agent.alert_system    import AlertSystem
from app.ml.agent.decision_engine import DecisionEngine
from app.ml.agent.execution_agent import ExecutionAgent
from app.database                 import get_supabase


class AgentPipeline:
    """
    Unified agent pipeline for one user.

    Replaces the separate MonitoringAgent class.
    Cleaner, more testable, easier to debug.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id

        # ── Components ─────────────────────────────────────────────────
        self.observer        = Observer(user_id)
        self.assessor        = Assessor(user_id)
        self.state_machine   = StateMachine(AgentState.IDLE)
        self.alert_system    = AlertSystem(user_id)
        self.decision_engine = DecisionEngine(user_id)
        self.execution_agent = ExecutionAgent(user_id)

        # ── State ──────────────────────────────────────────────────────
        self.cycle_count           = 0
        self.interventions_today   = 0
        self.last_observation      = None
        self.last_assessment       = None
        self.last_decision         = None
        self.last_execution        = None

        self.supabase = get_supabase()

    # ── Main cycle ─────────────────────────────────────────────────────

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one complete pipeline cycle.

        Steps:
        1. Observe  — collect current user state
        2. Assess   — score procrastination risk
        3. Transition state machine
        4. Decide   — choose intervention (if needed)
        5. Execute  — take autonomous action (if decided)
        6. Persist  — save everything to DB

        Returns complete cycle result.
        """
        self.cycle_count += 1
        cycle_start = datetime.utcnow()

        print(f"\n{'─'*55}")
        print(
            f"🔄 Pipeline Cycle {self.cycle_count} | "
            f"User {self.user_id[:8]} | "
            f"State: {self.state_machine.current_state.value}"
        )
        print(f"{'─'*55}")

        # ── Step 1: Observe ────────────────────────────────────────────
        observation          = self.observer.observe()
        self.last_observation = observation

        has_session = bool(observation.get('active_session'))
        print(f"   👁  Observed | Session: {has_session}")

        # ── Step 2: Assess ─────────────────────────────────────────────
        assessment          = self.assessor.assess(observation)
        self.last_assessment = assessment

        print(
            f"   📊 Assessed | "
            f"Risk: {assessment['risk_score']:.3f} "
            f"({assessment['risk_level']}) | "
            f"Signals: {len(assessment['signals'])}"
        )

        # ── Step 3: Transition state ───────────────────────────────────
        state_changed = self._update_state(assessment)

        if state_changed:
            print(
                f"   🔄 State → "
                f"{self.state_machine.current_state.value}"
            )

        # ── Step 4: Decide ─────────────────────────────────────────────
        decision          = None
        self.last_decision = None

        current_state = self.state_machine.current_state

        if current_state in [AgentState.AT_RISK, AgentState.INTERVENING]:
            decision           = self.decision_engine.decide(
                assessment=assessment,
                observation=observation
            )
            self.last_decision = decision

            print(
                f"   🎯 Decision | "
                f"Intervene: {decision['should_intervene']} | "
                f"Type: {decision.get('intervention_type', 'none')}"
            )

        # ── Step 5: Execute ────────────────────────────────────────────
        execution          = None
        self.last_execution = None

        if decision and decision.get('should_intervene'):
            # Send alert notification
            self.alert_system.send_intervention(
                risk_score=assessment['risk_score'],
                signals=assessment['signals'],
                observation=observation,
                message=decision.get('message', ''),
                intervention_type=decision.get('intervention_type', '')
            )

            # Execute autonomous action
            execution           = self.execution_agent.execute(
                decision=decision,
                observation=observation
            )
            self.last_execution  = execution
            self.interventions_today += 1

            print(
                f"   ⚡ Executed | "
                f"Action: {execution.get('action_type', 'none')} | "
                f"Success: {execution.get('executed', False)}"
            )

        elif current_state == AgentState.ACTIVE:
            # Check if recovering from risk
            if self.state_machine.history:
                prev = self.state_machine.history[-1].get('from')
                if prev in [
                    AgentState.AT_RISK.value,
                    AgentState.INTERVENING.value
                ]:
                    self.alert_system.send_recovery(
                        risk_score=assessment['risk_score']
                    )
                    print("   ✅ Recovery detected — sent positive reinforcement")

        # ── Step 6: Persist ────────────────────────────────────────────
        self._persist_cycle(
            observation=observation,
            assessment=assessment,
            decision=decision,
            execution=execution
        )

        # ── Build result ───────────────────────────────────────────────
        cycle_ms = round(
            (datetime.utcnow() - cycle_start).total_seconds() * 1000
        )

        result = {
            'cycle':        self.cycle_count,
            'user_id':      self.user_id,
            'state':        self.state_machine.current_state.value,
            'has_session':  has_session,
            'risk_score':   assessment['risk_score'],
            'risk_level':   assessment['risk_level'],
            'signals':      assessment['signals'],
            'state_changed': state_changed,
            'decision':     decision,
            'execution':    execution,
            'cycle_ms':     cycle_ms,
            'timestamp':    cycle_start.isoformat()
        }

        print(f"   ✅ Cycle complete in {cycle_ms}ms")
        return result

    # ── State management ───────────────────────────────────────────────

    def _update_state(self, assessment: Dict) -> bool:
        """Update state machine based on assessment. Returns True if changed."""
        current     = self.state_machine.current_state
        recommended = assessment['recommended_state']

        if current == AgentState.PAUSED:
            return False

        if current == recommended:
            return False

        reason = (
            f"Risk={assessment['risk_score']:.3f}, "
            f"Level={assessment['risk_level']}"
        )

        # Allow escalations from IDLE when a session exists by walking
        # through valid intermediate states in one cycle.
        if current == AgentState.IDLE and recommended in {
            AgentState.AT_RISK,
            AgentState.INTERVENING
        }:
            path = [AgentState.ACTIVE]
            if recommended == AgentState.AT_RISK:
                path.append(AgentState.AT_RISK)
            else:
                path.extend([
                    AgentState.AT_RISK,
                    AgentState.INTERVENING
                ])

            changed = False
            for next_state in path:
                changed = (
                    self.state_machine.transition(next_state, reason)
                    or changed
                )
            return changed

        return self.state_machine.transition(recommended, reason)

    # ── Persistence ────────────────────────────────────────────────────

    def _persist_cycle(
        self,
        observation: Dict,
        assessment:  Dict,
        decision:    Optional[Dict],
        execution:   Optional[Dict]
    ):
        """Persist full cycle data to Supabase."""
        try:
            # ── Update agent_state ─────────────────────────────────────
            agent_state_payload = {
                'user_id':     self.user_id,
                'state':       self.state_machine.current_state.value,
                'risk_score':  assessment['risk_score'],
                'last_cycle':  datetime.utcnow().isoformat(),
                'cycle_count': self.cycle_count
            }

            while True:
                try:
                    self.supabase.table('agent_state').upsert(
                        agent_state_payload
                    ).execute()
                    break
                except Exception as e:
                    error_msg = str(e)
                    missing_column = re.search(
                        r"Could not find the '([^']+)' column of 'agent_state'",
                        error_msg
                    )

                    if not missing_column:
                        raise

                    missing_key = missing_column.group(1)
                    if missing_key not in agent_state_payload:
                        raise

                    # Keep required fields and strip optional legacy-incompatible fields.
                    if missing_key in {'user_id', 'state'}:
                        raise

                    agent_state_payload.pop(missing_key, None)

            # ── Log to agent_events ────────────────────────────────────
            event_data = {
                'risk_score':  assessment['risk_score'],
                'risk_level':  assessment['risk_level'],
                'signals':     assessment['signals'],
                'cycle':       self.cycle_count
            }

            if decision:
                event_data['decision'] = {
                    'should_intervene':  decision.get('should_intervene'),
                    'intervention_type': decision.get('intervention_type'),
                    'reason':            decision.get('reason')
                }

            if execution:
                event_data['execution'] = {
                    'action_type': execution.get('action_type'),
                    'executed':    execution.get('executed')
                }

            self.supabase.table('agent_events').insert({
                'user_id':     self.user_id,
                'event_type':  'pipeline_cycle',
                'event_data':  event_data,
                'state_before': (
                    self.state_machine.history[-1]['from'].value
                    if self.state_machine.history
                    else 'idle'
                ),
                'state_after': self.state_machine.current_state.value
            }).execute()

            # ── Save risk to history ───────────────────────────────────
            self.supabase.table('risk_history').insert({
                'user_id':     self.user_id,
                'risk_score':  assessment['risk_score'],
                'assessed_at': datetime.utcnow().isoformat()
            }).execute()

        except Exception as e:
            print(f"   ⚠️  Persist error: {e}")

    # ── Control ────────────────────────────────────────────────────────

    def pause(self):
        self.state_machine.transition(AgentState.PAUSED, "User paused")

    def resume(self):
        self.state_machine.transition(AgentState.IDLE, "User resumed")

    def get_status(self) -> Dict:
        return {
            'user_id':             self.user_id,
            'state':               self.state_machine.current_state.value,
            'state_description':   self.state_machine.get_state_description(),
            'cycle_count':         self.cycle_count,
            'interventions_today': self.interventions_today,
            'last_risk_score': (
                self.last_assessment['risk_score']
                if self.last_assessment else None
            ),
            'last_cycle': (
                self.last_assessment['assessed_at']
                if self.last_assessment else None
            ),
            'last_decision':  self.last_decision,
            'last_execution': self.last_execution
        }
