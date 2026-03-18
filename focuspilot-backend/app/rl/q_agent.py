# app/rl/q_agent.py
"""
Q-Learning Agent — learns which interventions work best per user.

Core methods:
    select_action(state_key)  → picks best action (with exploration)
    update(state, action, reward, next_state) → updates Q-table
    get_q_table(user_id)      → returns full Q-table for a user
    get_policy_summary()      → human-readable policy summary

Uses epsilon-greedy exploration:
    With probability ε  → explore (random action)
    With probability 1-ε → exploit (best known action)
    ε decays over time as the agent gains confidence
"""

import random
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from app.database import get_supabase
from app.rl.state_encoder import ACTIONS


# Hyperparameters
ALPHA   = 0.1    # Learning rate
GAMMA   = 0.9    # Discount factor
EPSILON_START = 0.3   # Initial exploration rate
EPSILON_MIN   = 0.05  # Minimum exploration rate
EPSILON_DECAY = 0.995 # Decay per episode


class QLearningAgent:

    def __init__(self, user_id: str):
        self.user_id  = user_id
        self.supabase = get_supabase()

    # ── Action selection ───────────────────────────────────────────────

    def select_action(
        self,
        state_key: str,
        force_exploit: bool = False
    ) -> Tuple[str, str, float]:
        """
        Select action using epsilon-greedy policy.

        Args:
            state_key:     Encoded state string
            force_exploit: If True, always pick best action (no exploration)

        Returns:
            (action, selection_mode, q_value)
            selection_mode: 'exploit' or 'explore'
        """
        q_values = self._get_q_values(state_key)
        epsilon  = self._get_epsilon()

        # Explore: random action
        if not force_exploit and random.random() < epsilon:
            action   = random.choice(ACTIONS)
            q_value  = q_values.get(action, 0.0)
            return action, 'explore', q_value

        # Exploit: best known action
        best_action = max(q_values, key=q_values.get)
        best_q      = q_values[best_action]
        return best_action, 'exploit', best_q

    # ── Q-Table update ─────────────────────────────────────────────────

    def update(
        self,
        state_key: str,
        action: str,
        reward: float,
        next_state_key: str,
        episode_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Update Q-value using the Bellman equation.

        Q(s,a) ← Q(s,a) + α·[r + γ·max Q(s',a') - Q(s,a)]

        Args:
            state_key:      State where action was taken
            action:         Action that was taken
            reward:         Reward received
            next_state_key: State after action
            episode_id:     RL episode ID for logging

        Returns:
            {'q_before': float, 'q_after': float, 'td_error': float}
        """
        # Get current Q-value
        q_before = self._get_q_value(state_key, action)

        # Get max Q-value for next state
        next_q_values = self._get_q_values(next_state_key)
        max_next_q    = max(next_q_values.values())

        # Bellman update
        td_error = reward + GAMMA * max_next_q - q_before
        q_after  = q_before + ALPHA * td_error

        # Save updated Q-value
        self._save_q_value(state_key, action, q_after)

        # Update episode record if provided
        if episode_id:
            self._update_episode(episode_id, q_before, q_after)

        print(
            f"   🧠 Q-Update: {action} in {state_key[:20]}... | "
            f"Q: {q_before:.3f} → {q_after:.3f} | "
            f"reward: {reward} | TD: {td_error:.3f}"
        )

        return {
            'q_before': round(q_before, 4),
            'q_after':  round(q_after, 4),
            'td_error': round(td_error, 4)
        }

    # ── Episode logging ────────────────────────────────────────────────

    def log_episode(
        self,
        session_id: str,
        state_key: str,
        action: str,
        q_value: float
    ) -> str:
        """
        Log the start of an RL episode (before outcome is known).
        Returns the episode ID.
        """
        result = self.supabase.table('rl_episodes').insert({
            'user_id':        self.user_id,
            'session_id':     session_id,
            'state_key':      state_key,
            'action':         action,
            'q_value_before': q_value,
            'created_at':     datetime.utcnow().isoformat()
        }).execute()

        return result.data[0]['id'] if result.data else None

    def complete_episode(
        self,
        episode_id: str,
        reward: float,
        outcome: str,
        next_state_key: str
    ):
        """
        Complete an episode — record reward and trigger Q-update.
        Called when we know the outcome of an intervention.
        """
        # Get episode details
        result = (
            self.supabase
            .table('rl_episodes')
            .select("*")
            .eq('id', episode_id)
            .execute()
        )

        if not result.data:
            print(f"⚠️  Episode {episode_id} not found")
            return

        episode = result.data[0]

        # Update Q-table
        update_result = self.update(
            state_key=episode['state_key'],
            action=episode['action'],
            reward=reward,
            next_state_key=next_state_key,
            episode_id=episode_id
        )

        # Update episode record
        self.supabase.table('rl_episodes').update({
            'reward':         reward,
            'outcome':        outcome,
            'next_state_key': next_state_key,
            'q_value_after':  update_result['q_after']
        }).eq('id', episode_id).execute()

    # ── Policy inspection ──────────────────────────────────────────────

    def get_policy_summary(self) -> List[Dict[str, Any]]:
        """
        Get a human-readable summary of the learned policy.

        Returns list of states with their best action and Q-value.
        Sorted by visit count (most visited states first).
        """
        result = (
            self.supabase
            .table('q_table')
            .select("state_key, action, q_value, visit_count")
            .eq('user_id', self.user_id)
            .order('visit_count', desc=True)
            .execute()
        )

        if not result.data:
            return []

        # Group by state_key, find best action per state
        states: Dict[str, Dict] = {}
        for row in result.data:
            sk = row['state_key']
            if sk not in states:
                states[sk] = {
                    'state_key':   sk,
                    'best_action': row['action'],
                    'best_q':      row['q_value'],
                    'visit_count': row['visit_count'],
                    'all_actions': {}
                }
            states[sk]['all_actions'][row['action']] = row['q_value']
            if row['q_value'] > states[sk]['best_q']:
                states[sk]['best_action'] = row['action']
                states[sk]['best_q']      = row['q_value']

        # Sort by visit count
        summary = sorted(
            states.values(),
            key=lambda x: x['visit_count'],
            reverse=True
        )

        return summary[:20]   # Top 20 most visited states

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the agent's learning progress."""
        result = (
            self.supabase
            .table('rl_episodes')
            .select("reward, outcome, action, created_at")
            .eq('user_id', self.user_id)
            .not_.is_('reward', 'null')
            .order('created_at', desc=False)
            .execute()
        )

        episodes = result.data or []

        if not episodes:
            return {
                'total_episodes':  0,
                'avg_reward':      0.0,
                'success_rate':    0.0,
                'most_used_action': None,
                'reward_trend':    []
            }

        rewards  = [e['reward'] for e in episodes]
        outcomes = [e['outcome'] for e in episodes]

        # Action frequency
        action_counts: Dict[str, int] = {}
        for e in episodes:
            a = e['action']
            action_counts[a] = action_counts.get(a, 0) + 1

        most_used = max(action_counts, key=action_counts.get)

        # Success rate
        successes    = sum(1 for o in outcomes if o == 'focused_more')
        success_rate = round(successes / len(outcomes) * 100, 1)

        # Reward trend (rolling average over last 10 episodes)
        reward_trend = []
        window = 10
        for i in range(len(rewards)):
            start  = max(0, i - window + 1)
            window_rewards = rewards[start:i + 1]
            reward_trend.append({
                'episode': i + 1,
                'avg_reward': round(
                    sum(window_rewards) / len(window_rewards), 3
                )
            })

        return {
            'total_episodes':   len(episodes),
            'avg_reward':       round(sum(rewards) / len(rewards), 3),
            'success_rate':     success_rate,
            'most_used_action': most_used,
            'action_counts':    action_counts,
            'reward_trend':     reward_trend[-30:]   # Last 30 points
        }

    # ── Internal helpers ───────────────────────────────────────────────

    def _get_q_values(self, state_key: str) -> Dict[str, float]:
        """Get Q-values for all actions in a state."""
        result = (
            self.supabase
            .table('q_table')
            .select("action, q_value")
            .eq('user_id', self.user_id)
            .eq('state_key', state_key)
            .execute()
        )

        # Start with 0.0 for all actions (optimistic initialization)
        q_values = {action: 0.0 for action in ACTIONS}

        for row in (result.data or []):
            q_values[row['action']] = row['q_value']

        return q_values

    def _get_q_value(
        self,
        state_key: str,
        action: str
    ) -> float:
        """Get Q-value for a specific state-action pair."""
        result = (
            self.supabase
            .table('q_table')
            .select("q_value")
            .eq('user_id', self.user_id)
            .eq('state_key', state_key)
            .eq('action', action)
            .execute()
        )

        if result.data:
            return result.data[0]['q_value']
        return 0.0   # Default Q-value

    def _save_q_value(
        self,
        state_key: str,
        action: str,
        q_value: float
    ):
        """Save/update Q-value in the database."""
        self.supabase.table('q_table').upsert({
            'user_id':      self.user_id,
            'state_key':    state_key,
            'action':       action,
            'q_value':      round(q_value, 6),
            'last_updated': datetime.utcnow().isoformat()
        }).execute()

        # Increment visit count
        self.supabase.rpc('increment_visit_count', {
            'p_user_id':   self.user_id,
            'p_state_key': state_key,
            'p_action':    action
        }).execute()

    def _get_epsilon(self) -> float:
        """
        Get current epsilon (exploration rate).
        Decays based on number of episodes completed.
        """
        result = (
            self.supabase
            .table('rl_episodes')
            .select("id", count='exact')
            .eq('user_id', self.user_id)
            .execute()
        )

        n_episodes = result.count or 0

        epsilon = max(
            EPSILON_MIN,
            EPSILON_START * (EPSILON_DECAY ** n_episodes)
        )

        return epsilon

    def _update_episode(
        self,
        episode_id: str,
        q_before: float,
        q_after: float
    ):
        """Update episode with Q-values after update."""
        self.supabase.table('rl_episodes').update({
            'q_value_before': q_before,
            'q_value_after':  q_after
        }).eq('id', episode_id).execute()
