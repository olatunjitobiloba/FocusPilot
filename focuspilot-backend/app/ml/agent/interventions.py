# app/ml/agent/interventions.py
"""
Intervention Library — defines all intervention types and their messages.

Each intervention type has:
- A set of messages (rotated to avoid repetition)
- A priority level (higher = more aggressive)
- Conditions for when it should be used
- Expected effectiveness by context
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
import random


@dataclass
class Intervention:
    """Represents one type of intervention."""
    type_id:     str
    name:        str
    priority:    int          # 1=gentle, 5=aggressive
    messages:    List[str]
    description: str
    conditions:  Dict[str, Any] = field(default_factory=dict)


# ── Intervention Library ───────────────────────────────────────────────

INTERVENTIONS: Dict[str, Intervention] = {

    'focus_reminder': Intervention(
        type_id='focus_reminder',
        name='Focus Reminder',
        priority=1,
        description='Gentle reminder to return to work',
        messages=[
            "Hey! You were making great progress. Let's get back to it.",
            "Quick check-in: what's the ONE thing you should be doing right now?",
            "Refocus time! Close the distracting tabs and get back on track.",
            "You've got this! Return to your task and keep the momentum going.",
            "Small distraction? No problem. Refocus now and finish strong."
        ],
        conditions={
            'min_risk':    0.60,
            'max_risk':    0.74,
            'min_elapsed': 0
        }
    ),

    'break_suggestion': Intervention(
        type_id='break_suggestion',
        name='Break Suggestion',
        priority=2,
        description='Suggest a structured break to reset focus',
        messages=[
            "You have been at it for a while. Take a 5-minute break, then come back strong.",
            "Your brain needs rest to focus. Take 5 minutes away from the screen.",
            "Pomodoro check: take a proper break now. Set a 5-minute timer.",
            "Fatigue detected. A short break will actually help you focus better.",
            "Step away for 5 minutes. Stretch, breathe, then return focused."
        ],
        conditions={
            'min_risk':    0.55,
            'min_elapsed': 45   # Only suggest break after 45 mins
        }
    ),

    'motivational_message': Intervention(
        type_id='motivational_message',
        name='Motivational Message',
        priority=2,
        description='Personalized motivation based on user history',
        messages=[
            "You have completed {sessions_today} sessions today. One more push.",
            "Your {streak_days}-day streak is on the line. Don't break it now.",
            "Remember why you started. Your goal is worth more than this distraction.",
            "Every minute you refocus now compounds into results later. Let's go.",
            "The version of you that succeeds is choosing to focus right now. Be that person."
        ],
        conditions={
            'min_risk': 0.60
        }
    ),

    'site_block': Intervention(
        type_id='site_block',
        name='Emergency Site Block',
        priority=4,
        description='Trigger emergency blocking of distraction sites',
        messages=[
            "High distraction detected. Blocking distracting sites for 25 minutes.",
            "Focus mode activated. Distracting sites blocked for this session.",
            "Too many distractions. Emergency block activated. Stay on task.",
            "Agent activated focus shield. Distracting sites blocked for 25 mins.",
            "Distraction overload detected. Sites blocked. Time to focus."
        ],
        conditions={
            'min_risk':              0.75,
            'min_distraction_ratio': 0.60
        }
    ),

    'session_restart': Intervention(
        type_id='session_restart',
        name='Session Restart',
        priority=3,
        description='Suggest ending current session and starting fresh',
        messages=[
            "This session is not going well. End it, take 5 minutes, and restart fresh.",
            "Sometimes a fresh start is the best strategy. End this session and begin again.",
            "Reset time. Close everything, take a breath, and start a new focused session.",
            "Quality over quantity. End this session and start a better one.",
            "A clean restart beats a distracted continuation. Reset now."
        ],
        conditions={
            'min_risk':    0.75,
            'min_elapsed': 20   # Only suggest restart after 20 mins
        }
    ),

    'accountability_check': Intervention(
        type_id='accountability_check',
        name='Accountability Check',
        priority=3,
        description='Ask user to state their intention and commit',
        messages=[
            "What exactly are you working on right now? Type it out and commit.",
            "Accountability moment: what will you complete in the next 25 minutes?",
            "State your intention: what is the ONE task you are doing right now?",
            "Commitment check: what does done look like for the next 30 minutes?",
            "Before continuing: name the specific task you are working on."
        ],
        conditions={
            'min_risk': 0.65
        }
    )
}


def get_intervention(type_id: str) -> Intervention:
    """Get intervention by type ID."""
    return INTERVENTIONS.get(type_id, INTERVENTIONS['focus_reminder'])


def get_message(
    type_id: str,
    context: Dict[str, Any] = None
) -> str:
    """
    Get a random message for an intervention type.
    Fills in context variables if provided.
    """
    intervention = get_intervention(type_id)
    message      = random.choice(intervention.messages)

    # Fill in context variables
    if context:
        try:
            message = message.format(**context)
        except KeyError:
            pass  # Leave unfilled placeholders as-is

    return message


def list_interventions() -> List[Dict]:
    """List all available interventions."""
    return [
        {
            'type_id':     iv.type_id,
            'name':        iv.name,
            'priority':    iv.priority,
            'description': iv.description
        }
        for iv in INTERVENTIONS.values()
    ]
