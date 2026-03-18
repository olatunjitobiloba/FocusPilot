# app/routes/rl.py
"""
RL endpoints — Q-learning agent interaction.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.auth import get_current_user_id
from app.rl.q_agent          import QLearningAgent
from app.rl.state_encoder     import state_encoder
from app.rl.reward_calculator import reward_calculator
from app.database import get_supabase
from datetime import datetime

router = APIRouter(prefix="/rl", tags=["Reinforcement Learning"])


# ── Request models ─────────────────────────────────────────────────────

class SelectActionRequest(BaseModel):
    session_id:              str
    risk_score:              float
    session_start:           str
    session_duration_mins:   float
    planned_duration_mins:   float
    distraction_ratio:       float
    prev_intervention_outcome: Optional[str] = None
    force_exploit:           bool = False


class CompleteEpisodeRequest(BaseModel):
    episode_id:                  str
    focus_before:                float
    focus_after:                 float
    distraction_before:          float
    distraction_after:           float
    session_continued:           bool
    minutes_after_intervention:  float
    next_risk_score:             float
    next_session_start:          str
    next_session_duration_mins:  float
    next_planned_duration_mins:  float
    next_distraction_ratio:      float


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/select-action")
def select_action(
    body: SelectActionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Ask the Q-learning agent which action to take.

    The agent:
    1. Encodes the current state
    2. Looks up Q-values for all actions
    3. Picks best action (or explores randomly)
    4. Logs the episode
    5. Returns action + episode_id

    The episode_id must be sent back when completing the episode.
    """
    # Encode state
    session_start = datetime.fromisoformat(
        body.session_start.replace('Z', '+00:00')
    ).replace(tzinfo=None)

    state_key = state_encoder.encode(
        risk_score=body.risk_score,
        session_start=session_start,
        session_duration_mins=body.session_duration_mins,
        planned_duration_mins=body.planned_duration_mins,
        distraction_ratio=body.distraction_ratio,
        prev_intervention_outcome=body.prev_intervention_outcome
    )

    # Select action
    agent  = QLearningAgent(user_id)
    action, mode, q_value = agent.select_action(
        state_key,
        force_exploit=body.force_exploit
    )

    # Log episode
    episode_id = agent.log_episode(
        session_id=body.session_id,
        state_key=state_key,
        action=action,
        q_value=q_value
    )

    print(
        f"🎯 RL action: {action} ({mode}) | "
        f"state: {state_key[:30]}... | Q: {q_value:.3f}"
    )

    return {
        'action':     action,
        'mode':       mode,
        'q_value':    round(q_value, 4),
        'state_key':  state_key,
        'episode_id': episode_id
    }


@router.post("/complete-episode")
def complete_episode(
    body: CompleteEpisodeRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Complete an RL episode — record outcome and update Q-table.

    Call this endpoint after measuring the outcome of an intervention
    (typically 15-20 minutes after the intervention was taken).
    """
    # Calculate reward
    reward_result = reward_calculator.calculate(
        focus_before=body.focus_before,
        focus_after=body.focus_after,
        distraction_before=body.distraction_before,
        distraction_after=body.distraction_after,
        session_continued=body.session_continued,
        minutes_after_intervention=body.minutes_after_intervention
    )

    # Encode next state
    next_start = datetime.fromisoformat(
        body.next_session_start.replace('Z', '+00:00')
    ).replace(tzinfo=None)

    next_state_key = state_encoder.encode(
        risk_score=body.next_risk_score,
        session_start=next_start,
        session_duration_mins=body.next_session_duration_mins,
        planned_duration_mins=body.next_planned_duration_mins,
        distraction_ratio=body.next_distraction_ratio,
        prev_intervention_outcome=reward_result['outcome']
    )

    # Complete episode + update Q-table
    agent = QLearningAgent(user_id)
    agent.complete_episode(
        episode_id=body.episode_id,
        reward=reward_result['reward'],
        outcome=reward_result['outcome'],
        next_state_key=next_state_key
    )

    return {
        'reward':          reward_result['reward'],
        'outcome':         reward_result['outcome'],
        'outcome_label':   reward_calculator.outcome_label(
            reward_result['outcome']
        ),
        'reward_label':    reward_calculator.reward_label(
            reward_result['reward']
        ),
        'explanation':     reward_result['explanation'],
        'next_state_key':  next_state_key
    }


@router.get("/policy")
def get_policy(user_id: str = Depends(get_current_user_id)):
    """Get the agent's learned policy summary."""
    agent = QLearningAgent(user_id)
    return {
        'policy': agent.get_policy_summary()
    }


@router.get("/stats")
def get_learning_stats(user_id: str = Depends(get_current_user_id)):
    """Get learning statistics and reward trend."""
    agent = QLearningAgent(user_id)
    return agent.get_learning_stats()


@router.get("/episodes")
def get_episodes(user_id: str = Depends(get_current_user_id)):
    """Get all RL episodes for the user."""
    supabase = get_supabase()
    result   = (
        supabase
        .table('rl_episodes')
        .select("*")
        .eq('user_id', user_id)
        .order('created_at', desc=True)
        .limit(100)
        .execute()
    )
    return {
        'episodes': result.data or [],
        'total':    len(result.data or [])
    }
