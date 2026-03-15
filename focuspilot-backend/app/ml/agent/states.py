# app/ml/agent/states.py
"""
Agent State Machine — defines all states and valid transitions.

States:
    IDLE        → No active session. Agent is watching passively.
    ACTIVE      → Session running. Risk is low. User is focused.
    AT_RISK     → Session running. Risk is rising. Agent is alert.
    INTERVENING → Risk is critical. Agent is taking action.
    PAUSED      → User manually paused the agent.

Transitions:
    IDLE        → ACTIVE      (session starts)
    ACTIVE      → AT_RISK     (risk score > 0.60)
    ACTIVE      → IDLE        (session ends)
    AT_RISK     → ACTIVE      (risk drops below 0.40)
    AT_RISK     → INTERVENING (risk score > 0.75)
    AT_RISK     → IDLE        (session ends)
    INTERVENING → ACTIVE      (intervention worked, risk dropped)
    INTERVENING → IDLE        (session ends)
    ANY         → PAUSED      (user pauses agent)
    PAUSED      → IDLE        (user resumes agent)
"""

from enum import Enum
from typing import Dict, Set


class AgentState(str, Enum):
    IDLE        = "idle"
    ACTIVE      = "active"
    AT_RISK     = "at_risk"
    INTERVENING = "intervening"
    PAUSED      = "paused"


# Valid transitions: state → set of states it can move to
VALID_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
    AgentState.IDLE:        {AgentState.ACTIVE, AgentState.PAUSED},
    AgentState.ACTIVE:      {AgentState.AT_RISK, AgentState.IDLE, AgentState.PAUSED},
    AgentState.AT_RISK:     {AgentState.ACTIVE, AgentState.INTERVENING,
                             AgentState.IDLE, AgentState.PAUSED},
    AgentState.INTERVENING: {AgentState.ACTIVE, AgentState.IDLE, AgentState.PAUSED},
    AgentState.PAUSED:      {AgentState.IDLE}
}

# Risk thresholds
RISK_THRESHOLD_AT_RISK     = 0.60   # Enter AT_RISK above this
RISK_THRESHOLD_INTERVENING = 0.75   # Enter INTERVENING above this
RISK_THRESHOLD_RECOVERY    = 0.40   # Return to ACTIVE below this


class StateMachine:
    """
    Manages agent state transitions.
    Validates that only legal transitions happen.
    """

    def __init__(self, initial_state: AgentState = AgentState.IDLE):
        self.current_state = initial_state
        self.history       = []

    def can_transition(self, new_state: AgentState) -> bool:
        """Check if transition from current state to new state is valid."""
        return new_state in VALID_TRANSITIONS.get(self.current_state, set())

    def transition(
        self,
        new_state: AgentState,
        reason: str = ""
    ) -> bool:
        """
        Attempt a state transition.

        Returns True if transition succeeded, False if invalid.
        """
        if not self.can_transition(new_state):
            print(
                f"⚠️  Invalid transition: "
                f"{self.current_state} → {new_state}"
            )
            return False

        old_state          = self.current_state
        self.current_state = new_state

        self.history.append({
            'from':   old_state,
            'to':     new_state,
            'reason': reason
        })

        print(f"🔄 Agent: {old_state} → {new_state} ({reason})")
        return True

    def get_state_description(self) -> str:
        """Human-readable description of current state."""
        descriptions = {
            AgentState.IDLE:        "Watching passively. No active session.",
            AgentState.ACTIVE:      "Session active. User is focused. Risk is low.",
            AgentState.AT_RISK:     "Risk rising. Monitoring closely.",
            AgentState.INTERVENING: "High risk detected. Taking action.",
            AgentState.PAUSED:      "Agent paused by user."
        }
        return descriptions.get(self.current_state, "Unknown state")
