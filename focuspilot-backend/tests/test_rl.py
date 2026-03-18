# tests/test_rl.py
"""Tests for the Q-Learning system."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.rl.state_encoder     import StateEncoder
from app.rl.reward_calculator import RewardCalculator


class TestStateEncoder:

    def setup_method(self):
        self.encoder = StateEncoder()

    def test_encode_returns_six_parts(self):
        state = self.encoder.encode(
            risk_score=0.6,
            session_start=datetime(2026, 3, 18, 9, 0),
            session_duration_mins=20,
            planned_duration_mins=45,
            distraction_ratio=0.3
        )
        parts = state.split('_')
        assert len(parts) == 6

    def test_high_risk_encodes_correctly(self):
        state = self.encoder.encode(
            risk_score=0.8,
            session_start=datetime(2026, 3, 18, 9, 0),
            session_duration_mins=20,
            planned_duration_mins=45,
            distraction_ratio=0.1
        )
        assert state.startswith('critical')

    def test_low_risk_encodes_correctly(self):
        state = self.encoder.encode(
            risk_score=0.1,
            session_start=datetime(2026, 3, 18, 9, 0),
            session_duration_mins=20,
            planned_duration_mins=45,
            distraction_ratio=0.1
        )
        assert state.startswith('low')

    def test_morning_time_encodes_correctly(self):
        state = self.encoder.encode(
            risk_score=0.5,
            session_start=datetime(2026, 3, 18, 9, 0),
            session_duration_mins=20,
            planned_duration_mins=45,
            distraction_ratio=0.1
        )
        assert 'morning' in state

    def test_weekend_encodes_correctly(self):
        # March 22, 2026 is a Sunday
        state = self.encoder.encode(
            risk_score=0.5,
            session_start=datetime(2026, 3, 22, 10, 0),
            session_duration_mins=20,
            planned_duration_mins=45,
            distraction_ratio=0.1
        )
        assert 'weekend' in state

    def test_decode_reverses_encode(self):
        state = self.encoder.encode(
            risk_score=0.6,
            session_start=datetime(2026, 3, 18, 9, 0),
            session_duration_mins=20,
            planned_duration_mins=45,
            distraction_ratio=0.3,
            prev_intervention_outcome='success'
        )
        decoded = self.encoder.decode(state)
        assert decoded['prev_outcome'] == 'success'
        assert decoded['time_of_day']  == 'morning'

    def test_same_context_same_state(self):
        kwargs = dict(
            risk_score=0.6,
            session_start=datetime(2026, 3, 18, 9, 0),
            session_duration_mins=20,
            planned_duration_mins=45,
            distraction_ratio=0.3
        )
        assert self.encoder.encode(**kwargs) == self.encoder.encode(**kwargs)


class TestRewardCalculator:

    def setup_method(self):
        self.calc = RewardCalculator()

    def test_great_focus_gives_max_reward(self):
        result = self.calc.calculate(
            focus_before=5.0,
            focus_after=8.0,
            distraction_before=0.4,
            distraction_after=0.1,
            session_continued=True,
            minutes_after_intervention=25
        )
        assert result['reward']  == 1.0
        assert result['outcome'] == 'focused_more'

    def test_good_focus_gives_half_reward(self):
        result = self.calc.calculate(
            focus_before=5.0,
            focus_after=6.5,
            distraction_before=0.4,
            distraction_after=0.3,
            session_continued=True,
            minutes_after_intervention=10
        )
        assert result['reward']  == 0.5
        assert result['outcome'] == 'focused_more'

    def test_session_ended_gives_worst_reward(self):
        result = self.calc.calculate(
            focus_before=5.0,
            focus_after=0.0,
            distraction_before=0.4,
            distraction_after=0.0,
            session_continued=False,
            minutes_after_intervention=0
        )
        assert result['reward']  == -1.0
        assert result['outcome'] == 'session_ended'

    def test_increased_distraction_gives_bad_reward(self):
        result = self.calc.calculate(
            focus_before=5.0,
            focus_after=4.5,
            distraction_before=0.2,
            distraction_after=0.5,
            session_continued=True,
            minutes_after_intervention=3
        )
        assert result['reward']  == -0.5
        assert result['outcome'] == 'distracted_more'

    def test_no_change_gives_neutral_reward(self):
        result = self.calc.calculate(
            focus_before=5.0,
            focus_after=5.2,
            distraction_before=0.3,
            distraction_after=0.32,
            session_continued=True,
            minutes_after_intervention=3
        )
        assert result['reward']  == 0.0
        assert result['outcome'] == 'no_change'


class TestQLearningAgent:

    def test_select_action_returns_valid_action(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value\
            .eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.select.return_value\
            .eq.return_value.execute.return_value.count = 0

        with patch(
            'app.rl.q_agent.get_supabase',
            return_value=mock_sb
        ):
            from app.rl.q_agent import QLearningAgent, ACTIONS
            agent  = QLearningAgent('test-user')
            action, mode, q_value = agent.select_action(
                'high_morning_weekday_mid_medium_none'
            )
            assert action   in ACTIONS
            assert mode     in ['exploit', 'explore']
            assert q_value  == 0.0   # No data yet

    def test_bellman_update_increases_good_q_value(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value\
            .eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.select.return_value\
            .eq.return_value.execute.return_value.count = 5
        mock_sb.table.return_value.upsert.return_value\
            .execute.return_value.data = []
        mock_sb.rpc.return_value.execute.return_value.data = []

        with patch(
            'app.rl.q_agent.get_supabase',
            return_value=mock_sb
        ):
            from app.rl.q_agent import QLearningAgent
            agent  = QLearningAgent('test-user')
            result = agent.update(
                state_key='high_morning_weekday_mid_medium_none',
                action='block_sites',
                reward=1.0,
                next_state_key='medium_morning_weekday_mid_low_success'
            )
            # With reward=1.0 and Q_before=0.0:
            # Q_after = 0.0 + 0.1 * [1.0 + 0.9*0.0 - 0.0] = 0.1
            assert result['q_after']  > result['q_before']
            assert result['td_error'] > 0


# Run: pytest tests/test_rl.py -v
# Expected: 13 passed
