# app/routes/execution.py
"""
Execution endpoints — expose execution agent via API.
"""

from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user_id
from app.ml.agent.execution_agent import ExecutionAgent
from app.ml.agent.action_logger   import ActionLogger
from app.ml.agent.executors       import SiteBlockExecutor, NudgeExecutor
from app.ml.agent.actions         import list_actions
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/execution", tags=["Execution"])


class BlockRequest(BaseModel):
    duration_minutes: int = 25
    domains: Optional[list] = None


class NudgeRequest(BaseModel):
    title:         str
    message:       str
    scheduled_for: Optional[str] = None


@router.get("/actions")
def get_recent_actions(
    limit: int = 20,
    user_id: str = Depends(get_current_user_id)
):
    """Get recent autonomous actions taken by the agent."""
    logger = ActionLogger(user_id)
    return {
        'actions': logger.get_recent_actions(limit=limit),
        'total':   limit
    }


@router.get("/undoable")
def get_undoable_actions(user_id: str = Depends(get_current_user_id)):
    """Get actions that can still be undone."""
    logger = ActionLogger(user_id)
    return {
        'undoable_actions': logger.get_undoable_actions()
    }


@router.post("/undo/{action_id}")
def undo_action(
    action_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Undo a previously executed action."""
    agent  = ExecutionAgent(user_id)
    result = agent.undo(action_id)

    if not result.get('undone'):
        raise HTTPException(
            status_code=400,
            detail=result.get('reason', 'Could not undo action')
        )

    return result


@router.get("/block-state")
def get_block_state(user_id: str = Depends(get_current_user_id)):
    """Get current site block state."""
    try:
        blocker = SiteBlockExecutor(user_id)
        state = blocker.get_block_state()
        if isinstance(state, dict):
            return state
    except Exception as exc:
        return {
            'is_blocked': False,
            'blocked_domains': [],
            'unblock_at': None,
            'status': 'degraded',
            'error': str(exc),
        }

    return {
        'is_blocked': False,
        'blocked_domains': [],
        'unblock_at': None,
        'status': 'degraded',
        'error': 'Invalid block state payload',
    }


@router.post("/block")
def manual_block(
    request: BlockRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Manually trigger site blocking."""
    blocker = SiteBlockExecutor(user_id)
    result  = blocker.block(
        domains=request.domains,
        duration_minutes=request.duration_minutes,
        reason="Manual block by user"
    )
    return result


@router.post("/unblock")
def manual_unblock(user_id: str = Depends(get_current_user_id)):
    """Manually unblock all sites."""
    blocker = SiteBlockExecutor(user_id)
    return blocker.unblock()


@router.post("/nudge")
def send_nudge(
    request: NudgeRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Send an immediate or scheduled nudge."""
    nudger = NudgeExecutor(user_id)

    if request.scheduled_for:
        return nudger.schedule_nudge(
            message=request.message,
            scheduled_for=request.scheduled_for,
            title=request.title
        )

    return nudger.send_nudge(
        title=request.title,
        message=request.message
    )


@router.get("/available-actions")
def get_available_actions():
    """List all available action types."""
    return {'actions': list_actions()}
