# tests/test_integration.py
"""
Integration tests for the full agent pipeline.

These tests verify that all three agents work together correctly:
Monitor → Decision → Execution

Run with: pytest tests/test_integration.py -v
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for all tests."""
    mock = MagicMock()

    # Default responses
    mock.table.return_value.select.return_value\
        .eq.return_value.execute.return_value.data = []

    mock.table.return_value.select.return_value\
        .eq.return_value.is_.return_value\
        .execute.return_value.data = []

    mock.table.return_value.insert.return_value\
        .execute.return_value.data = [{'id': 'test-id-123'}]

    mock.table.return_value.upsert.return_value\
        .execute.return_value.data = [{'id': 'test-id-123'}]

    mock.table.return_value.update.return_value\
        .eq.return_value.execute.return_value.data = []

    return mock


@pytest.fixture
def sample_observation():
    """Sample observation with active session."""
    return {
        'user_id':      'test-user-123',
        'observed_at':  datetime.utcnow().isoformat(),
        'active_session': {
            'id':         'session-456',
            'user_id':    'test-user-123',
            'start_time': datetime.utcnow().isoformat(),
            'end_time':   None
        },
        'recent_activity': [
            {
                'domain':           'youtube.com',
                'duration_seconds': 600,
                'session_id':       'session-456'
            },
            {
                'domain':           'twitter.com',
                'duration_seconds': 300,
                'session_id':       'session-456'
            }
        ],
        'session_metrics': {
            'elapsed_minutes':          25.0,
            'recent_distraction_ratio': 0.75,
            'recent_distraction_count': 8,
            'last_domain':              'youtube.com',
            'is_on_distraction_site':   True,
            'activity_count_10min':     10
        },
        'context': {
            'current_hour':           21,
            'is_typical_study_hour':  True,
            'sessions_this_week':     5,
            'avg_focus_score_week':   6.2
        }
    }


@pytest.fixture
def sample_assessment_high_risk():
    """Sample high-risk assessment."""
    from app.ml.agent.states import AgentState
    return {
        'risk_score':        0.82,
        'risk_level':        'critical',
        'recommended_state': AgentState.INTERVENING,
        'signals': [
            'Currently on youtube.com',
            '75% of last 10 min on distracting sites',
            'ML model: 78% risk'
        ],
        'ml_score':       0.78,
        'rule_overrides': [],
        'assessed_at':    datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_assessment_low_risk():
    """Sample low-risk assessment."""
    from app.ml.agent.states import AgentState
    return {
        'risk_score':        0.25,
        'risk_level':        'low',
        'recommended_state': AgentState.ACTIVE,
        'signals':           ['Low distraction ratio'],
        'ml_score':          0.22,
        'rule_overrides':    [],
        'assessed_at':       datetime.utcnow().isoformat()
    }


# ── State Machine Tests ────────────────────────────────────────────────

class TestStateMachine:

    def test_initial_state_is_idle(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        assert sm.current_state == AgentState.IDLE

    def test_idle_to_active_is_valid(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        result = sm.transition(AgentState.ACTIVE, "session started")
        assert result == True
        assert sm.current_state == AgentState.ACTIVE

    def test_idle_to_intervening_is_invalid(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        result = sm.transition(AgentState.INTERVENING, "skip steps")
        assert result == False
        assert sm.current_state == AgentState.IDLE

    def test_active_to_at_risk(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        sm.transition(AgentState.ACTIVE, "session started")
        result = sm.transition(AgentState.AT_RISK, "risk rising")
        assert result == True
        assert sm.current_state == AgentState.AT_RISK

    def test_at_risk_to_intervening(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        sm.transition(AgentState.ACTIVE, "session started")
        sm.transition(AgentState.AT_RISK, "risk rising")
        result = sm.transition(AgentState.INTERVENING, "risk critical")
        assert result == True
        assert sm.current_state == AgentState.INTERVENING

    def test_any_state_to_paused(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        sm.transition(AgentState.ACTIVE, "session started")
        sm.transition(AgentState.AT_RISK, "risk rising")
        result = sm.transition(AgentState.PAUSED, "user paused")
        assert result == True
        assert sm.current_state == AgentState.PAUSED

    def test_history_records_transitions(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        sm.transition(AgentState.ACTIVE, "session started")
        sm.transition(AgentState.AT_RISK, "risk rising")
        assert len(sm.history) == 2
        assert sm.history[0]['from'] == AgentState.IDLE
        assert sm.history[0]['to']   == AgentState.ACTIVE

    def test_paused_agent_cannot_transition(self):
        from app.ml.agent.states import StateMachine, AgentState
        sm = StateMachine()
        sm.transition(AgentState.ACTIVE, "session")
        sm.transition(AgentState.PAUSED, "paused")
        result = sm.transition(AgentState.AT_RISK, "risk")
        assert result == False
        assert sm.current_state == AgentState.PAUSED


# ── Assessor Tests ─────────────────────────────────────────────────────

class TestAssessor:

    def test_no_session_returns_idle(self, mock_supabase):
        with patch('app.ml.agent.assessor.model_manager') as mock_mm, \
             patch('app.ml.agent.assessor.DatasetBuilder'):

            mock_mm.has_model.return_value = False

            from app.ml.agent.assessor import Assessor
            from app.ml.agent.states   import AgentState

            assessor = Assessor('test-user')
            result   = assessor.assess({'active_session': None})

            assert result['risk_score']        == 0.0
            assert result['recommended_state'] == AgentState.IDLE

    def test_high_distraction_increases_risk(
        self,
        mock_supabase,
        sample_observation
    ):
        with patch('app.ml.agent.assessor.model_manager') as mock_mm, \
             patch('app.ml.agent.assessor.DatasetBuilder'):

            mock_mm.has_model.return_value = False

            from app.ml.agent.assessor import Assessor

            assessor = Assessor('test-user')
            result   = assessor.assess(sample_observation)

            # High distraction ratio should push risk up
            assert result['risk_score'] > 0.30

    def test_active_distraction_site_adds_risk(
        self,
        mock_supabase,
        sample_observation
    ):
        with patch('app.ml.agent.assessor.model_manager') as mock_mm, \
             patch('app.ml.agent.assessor.DatasetBuilder'):

            mock_mm.has_model.return_value = False

            from app.ml.agent.assessor import Assessor

            assessor = Assessor('test-user')

            # Set is_on_distraction_site = True
            sample_observation['session_metrics']['is_on_distraction_site'] = True
            result = assessor.assess(sample_observation)

            signals = result['signals']
            assert any('youtube.com' in s or 'distraction' in s.lower()
                       for s in signals)

    def test_risk_score_bounded_0_to_1(
        self,
        mock_supabase,
        sample_observation
    ):
        with patch('app.ml.agent.assessor.model_manager') as mock_mm, \
             patch('app.ml.agent.assessor.DatasetBuilder'):

            mock_mm.has_model.return_value = False

            from app.ml.agent.assessor import Assessor

            assessor = Assessor('test-user')
            result   = assessor.assess(sample_observation)

            assert 0.0 <= result['risk_score'] <= 1.0

    def test_ml_model_blended_when_available(
        self,
        mock_supabase,
        sample_observation
    ):
        with patch('app.ml.agent.assessor.model_manager') as mock_mm, \
             patch('app.ml.agent.assessor.DatasetBuilder') as mock_db:

            mock_mm.has_model.return_value = True
            mock_mm.predict.return_value   = {
                'risk_score': 0.90
            }

            mock_builder = MagicMock()
            mock_builder.build_inference_row.return_value = (
                np.zeros((1, 15))
            )
            mock_db.return_value = mock_builder

            from app.ml.agent.assessor import Assessor

            assessor = Assessor('test-user')
            result   = assessor.assess(sample_observation)

            # ML score of 0.90 should push final risk high
            assert result['risk_score'] > 0.50
            assert result['ml_score']   == 0.90


# ── Decision Engine Tests ──────────────────────────────────────────────

class TestDecisionEngine:

    def test_low_risk_no_intervention(
        self,
        mock_supabase,
        sample_observation,
        sample_assessment_low_risk
    ):
        with patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase):

            from app.ml.agent.decision_engine import DecisionEngine

            engine   = DecisionEngine('test-user')
            decision = engine.decide(
                sample_assessment_low_risk,
                sample_observation
            )

            assert decision['should_intervene'] == False

    def test_high_risk_triggers_intervention(
        self,
        mock_supabase,
        sample_observation,
        sample_assessment_high_risk
    ):
        with patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.decision_engine.CooldownManager') as mock_cd, \
             patch('app.ml.agent.decision_engine.HistoryAnalyzer') as mock_ha, \
             patch('app.ml.agent.decision_engine.OutcomeTracker'):

            mock_cd.return_value.can_intervene.return_value = {
                'allowed': True
            }
            mock_ha.return_value.get_best_intervention.return_value = (
                'site_block'
            )
            mock_ha.return_value.get_user_profile.return_value = {}

            from app.ml.agent.decision_engine import DecisionEngine

            engine   = DecisionEngine('test-user')
            decision = engine.decide(
                sample_assessment_high_risk,
                sample_observation
            )

            assert decision['should_intervene'] == True
            assert 'intervention_type' in decision
            assert 'message'           in decision

    def test_cooldown_blocks_intervention(
        self,
        mock_supabase,
        sample_observation,
        sample_assessment_high_risk
    ):
        with patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.decision_engine.CooldownManager') as mock_cd:

            mock_cd.return_value.can_intervene.return_value = {
                'allowed': False,
                'reason':  'Cooldown active. Wait 8 more minutes.'
            }

            from app.ml.agent.decision_engine import DecisionEngine

            engine   = DecisionEngine('test-user')
            decision = engine.decide(
                sample_assessment_high_risk,
                sample_observation
            )

            assert decision['should_intervene'] == False
            assert 'Cooldown' in decision['reason']

    def test_decision_contains_required_fields(
        self,
        mock_supabase,
        sample_observation,
        sample_assessment_high_risk
    ):
        with patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.decision_engine.CooldownManager') as mock_cd, \
             patch('app.ml.agent.decision_engine.HistoryAnalyzer') as mock_ha, \
             patch('app.ml.agent.decision_engine.OutcomeTracker'):

            mock_cd.return_value.can_intervene.return_value = {
                'allowed': True
            }
            mock_ha.return_value.get_best_intervention.return_value = (
                'focus_reminder'
            )
            mock_ha.return_value.get_user_profile.return_value = {}

            from app.ml.agent.decision_engine import DecisionEngine

            engine   = DecisionEngine('test-user')
            decision = engine.decide(
                sample_assessment_high_risk,
                sample_observation
            )

            required_fields = [
                'should_intervene',
                'decided_at'
            ]
            for field in required_fields:
                assert field in decision, f"Missing field: {field}"


# ── Execution Agent Tests ──────────────────────────────────────────────

class TestExecutionAgent:

    def test_no_intervention_skips_execution(
        self,
        mock_supabase,
        sample_observation
    ):
        with patch('app.ml.agent.execution_agent.get_supabase',
                   return_value=mock_supabase):

            from app.ml.agent.execution_agent import ExecutionAgent

            agent  = ExecutionAgent('test-user')
            result = agent.execute(
                decision={'should_intervene': False, 'reason': 'low risk'},
                observation=sample_observation
            )

            assert result['executed'] == False

    def test_site_block_decision_triggers_block(
        self,
        mock_supabase,
        sample_observation
    ):
        with patch('app.ml.agent.execution_agent.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.execution_agent.SiteBlockExecutor') as mock_blocker, \
             patch('app.ml.agent.execution_agent.ActionLogger') as mock_logger:

            mock_blocker.return_value.block.return_value = {
                'blocked_domains':  ['youtube.com'],
                'duration_minutes': 25
            }
            mock_logger.return_value.log_action.return_value = 'action-123'

            from app.ml.agent.execution_agent import ExecutionAgent

            agent  = ExecutionAgent('test-user')
            result = agent.execute(
                decision={
                    'should_intervene':  True,
                    'intervention_type': 'site_block',
                    'message':           'Blocking sites',
                    'risk_score':        0.82
                },
                observation=sample_observation
            )

            assert result['executed'] == True
            mock_blocker.return_value.block.assert_called_once()

    def test_nudge_decision_sends_nudge(
        self,
        mock_supabase,
        sample_observation
    ):
        with patch('app.ml.agent.execution_agent.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.execution_agent.NudgeExecutor') as mock_nudger, \
             patch('app.ml.agent.execution_agent.ActionLogger') as mock_logger:

            mock_nudger.return_value.send_nudge.return_value = {
                'sent': True
            }
            mock_logger.return_value.log_action.return_value = 'action-456'

            from app.ml.agent.execution_agent import ExecutionAgent

            agent  = ExecutionAgent('test-user')
            result = agent.execute(
                decision={
                    'should_intervene':  True,
                    'intervention_type': 'focus_reminder',
                    'message':           'Stay focused!',
                    'risk_score':        0.65
                },
                observation=sample_observation
            )

            assert result['executed'] == True
            mock_nudger.return_value.send_nudge.assert_called_once()


# ── Full Pipeline Integration Test ─────────────────────────────────────

class TestAgentPipeline:

    def test_pipeline_runs_without_error(self, mock_supabase):
        """Full pipeline should run without raising exceptions."""
        with patch('app.ml.agent.observer.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.assessor.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.execution_agent.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.alert_system.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.pipeline.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.assessor.model_manager') as mock_mm, \
             patch('app.ml.agent.assessor.DatasetBuilder'):

            mock_mm.has_model.return_value = False

            from app.ml.agent.pipeline import AgentPipeline

            pipeline = AgentPipeline('test-user-123')
            result   = pipeline.run_cycle()

            assert 'cycle'      in result
            assert 'risk_score' in result
            assert 'state'      in result
            assert result['cycle'] == 1

    def test_pipeline_increments_cycle_count(self, mock_supabase):
        """Cycle count should increment on each run."""
        with patch('app.ml.agent.observer.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.assessor.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.execution_agent.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.alert_system.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.pipeline.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.assessor.model_manager') as mock_mm, \
             patch('app.ml.agent.assessor.DatasetBuilder'):

            mock_mm.has_model.return_value = False

            from app.ml.agent.pipeline import AgentPipeline

            pipeline = AgentPipeline('test-user-123')
            pipeline.run_cycle()
            pipeline.run_cycle()
            result = pipeline.run_cycle()

            assert result['cycle'] == 3

    def test_pipeline_state_starts_idle(self, mock_supabase):
        """Pipeline should start in IDLE state."""
        with patch('app.ml.agent.pipeline.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.observer.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.assessor.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.execution_agent.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.alert_system.get_supabase',
                   return_value=mock_supabase):

            from app.ml.agent.pipeline import AgentPipeline

            pipeline = AgentPipeline('test-user-123')
            assert pipeline.state_machine.current_state.value == 'idle'

    def test_pipeline_pause_and_resume(self, mock_supabase):
        """Pause and resume should work correctly."""
        with patch('app.ml.agent.pipeline.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.observer.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.assessor.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.decision_engine.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.execution_agent.get_supabase',
                   return_value=mock_supabase), \
             patch('app.ml.agent.alert_system.get_supabase',
                   return_value=mock_supabase):

            from app.ml.agent.pipeline import AgentPipeline
            from app.ml.agent.states   import AgentState

            pipeline = AgentPipeline('test-user-123')
            pipeline.state_machine.transition(AgentState.ACTIVE, "test")
            pipeline.pause()

            assert pipeline.state_machine.current_state == AgentState.PAUSED

            pipeline.resume()
            assert pipeline.state_machine.current_state == AgentState.IDLE
