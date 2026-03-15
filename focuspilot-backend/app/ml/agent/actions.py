# app/ml/agent/actions.py
"""
Action Registry — defines all executable actions.

Each action has:
- An executor function
- Whether it is undoable
- What data it needs
- What it returns
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime


@dataclass
class ActionDefinition:
    """Defines one type of executable action."""
    action_id:   str
    name:        str
    description: str
    is_undoable: bool
    required_data: List[str] = field(default_factory=list)


# ── Action Registry ────────────────────────────────────────────────────

ACTION_REGISTRY: Dict[str, ActionDefinition] = {

    'block_sites': ActionDefinition(
        action_id='block_sites',
        name='Block Distraction Sites',
        description='Tell the browser extension to block distraction sites',
        is_undoable=True,
        required_data=['domains', 'duration_minutes']
    ),

    'unblock_sites': ActionDefinition(
        action_id='unblock_sites',
        name='Unblock Sites',
        description='Remove site blocks',
        is_undoable=False,
        required_data=[]
    ),

    'start_session': ActionDefinition(
        action_id='start_session',
        name='Auto-Start Session',
        description='Automatically start a new focus session',
        is_undoable=True,
        required_data=['duration_minutes']
    ),

    'end_session': ActionDefinition(
        action_id='end_session',
        name='Auto-End Session',
        description='End the current session due to excessive procrastination',
        is_undoable=False,
        required_data=['session_id', 'reason']
    ),

    'send_nudge': ActionDefinition(
        action_id='send_nudge',
        name='Send Nudge',
        description='Send an immediate focus nudge notification',
        is_undoable=False,
        required_data=['message', 'title']
    ),

    'schedule_nudge': ActionDefinition(
        action_id='schedule_nudge',
        name='Schedule Nudge',
        description='Schedule a future nudge at optimal focus time',
        is_undoable=True,
        required_data=['message', 'scheduled_for']
    ),

    'activate_focus_mode': ActionDefinition(
        action_id='activate_focus_mode',
        name='Activate Focus Mode',
        description='Enable full focus mode: block sites + start session',
        is_undoable=True,
        required_data=['duration_minutes']
    )
}


def get_action(action_id: str) -> Optional[ActionDefinition]:
    """Get action definition by ID."""
    return ACTION_REGISTRY.get(action_id)


def list_actions() -> List[Dict]:
    """List all available actions."""
    return [
        {
            'action_id':   a.action_id,
            'name':        a.name,
            'description': a.description,
            'is_undoable': a.is_undoable
        }
        for a in ACTION_REGISTRY.values()
    ]
