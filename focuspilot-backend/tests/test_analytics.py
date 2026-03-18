# tests/test_analytics.py
"""
Tests for analytics endpoints.
Run with: pytest tests/test_analytics.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


def make_mock_sessions(n: int = 10) -> list:
    """Generate mock session data."""
    sessions = []
    base = datetime.utcnow() - timedelta(days=n)

    for i in range(n):
        start = base + timedelta(days=i, hours=9)
        end = start + timedelta(minutes=45)
        sessions.append({
            'id': f'session-{i}',
            'user_id': 'test-user',
            'start_time': start.isoformat(),
            'end_time': end.isoformat(),
            'focus_score': float(5 + (i % 5)),
            'duration_minutes': 45,
            'auto_started': False
        })

    return sessions


class TestDailyStats:
    """Test GET /stats/daily"""

    def test_daily_stats_returns_correct_structure(self, client, auth_headers):
        """Daily stats returns all required fields"""
        response = client.get("/stats/daily", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "date",
            "total_focus_minutes",
            "sessions_count",
            "distraction_count",
            "avg_focus_score",
            "top_distractions"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_daily_stats_no_auth(self, client):
        """Cannot access stats without auth"""
        response = client.get("/stats/daily")
        assert response.status_code == 401

    def test_daily_stats_values_are_non_negative(self, client, auth_headers):
        """All numeric stats should be >= 0"""
        response = client.get("/stats/daily", headers=auth_headers)
        data = response.json()

        assert data["total_focus_minutes"] >= 0
        assert data["sessions_count"]     >= 0
        assert data["distraction_count"]  >= 0
        assert data["avg_focus_score"]    >= 0


class TestWeeklyStats:
    """Test GET /stats/weekly"""

    def test_weekly_stats_structure(self, client, auth_headers):
        """Weekly stats returns correct structure"""
        response = client.get("/stats/weekly", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "week_start"              in data
        assert "week_end"                in data
        assert "total_focus_hours"       in data
        assert "total_sessions"          in data
        assert "avg_session_duration"    in data
        assert "current_streak"          in data
        assert "best_day"                in data
        assert "daily_breakdown"         in data

    def test_weekly_daily_breakdown_is_dict(self, client, auth_headers):
        """Daily breakdown should be a dictionary"""
        response = client.get("/stats/weekly", headers=auth_headers)
        data = response.json()

        assert isinstance(data["daily_breakdown"], dict)


class TestDistractionAnalysis:
    """Test GET /analytics/distractions"""

    def test_distractions_default_period(self, client, auth_headers):
        """Returns distraction data for default 7-day period"""
        response = client.get(
            "/analytics/distractions",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "period_days"              in data
        assert "top_distractions"         in data
        assert "total_distraction_hours"  in data
        assert data["period_days"]        == 7

    def test_distractions_custom_period(self, client, auth_headers):
        """Accepts custom period via query param"""
        response = client.get(
            "/analytics/distractions?days=14",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["period_days"] == 14

    def test_distractions_invalid_period(self, client, auth_headers):
        """Rejects invalid period (> 30 days)"""
        response = client.get(
            "/analytics/distractions?days=100",
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_top_distractions_is_list(self, client, auth_headers):
        """Top distractions should be a list"""
        response = client.get(
            "/analytics/distractions",
            headers=auth_headers
        )
        data = response.json()

        assert isinstance(data["top_distractions"], list)


class TestHourlyPattern:
    """Test GET /analytics/hourly-pattern"""

    def test_hourly_pattern_has_24_hours(self, client, auth_headers):
        """Should return data for all 24 hours"""
        response = client.get(
            "/analytics/hourly-pattern",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "hourly_breakdown" in data
        assert len(data["hourly_breakdown"]) == 24

    def test_hourly_pattern_structure(self, client, auth_headers):
        """Each hour entry has required fields"""
        response = client.get(
            "/analytics/hourly-pattern",
            headers=auth_headers
        )
        data = response.json()

        for hour_entry in data["hourly_breakdown"]:
            assert "hour"            in hour_entry
            assert "hour_label"      in hour_entry
            assert "total_minutes"   in hour_entry
            assert "session_count"   in hour_entry
            assert "avg_focus_score" in hour_entry

            # Hour should be 0-23
            assert 0 <= hour_entry["hour"] <= 23


class TestRecommendations:
    """Test GET /recommendations/"""

    def test_recommendations_structure(self, client, auth_headers):
        """Returns recommendations with correct structure"""
        response = client.get("/recommendations/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "recommendations" in data
        assert "total"           in data
        assert isinstance(data["recommendations"], list)

    def test_recommendations_have_required_fields(self, client, auth_headers):
        """Each recommendation has type, title, message, priority"""
        response = client.get("/recommendations/", headers=auth_headers)
        data = response.json()

        for rec in data["recommendations"]:
            assert "type"     in rec
            assert "title"    in rec
            assert "message"  in rec
            assert "priority" in rec
            assert rec["priority"] in ["high", "medium", "low"]


class TestAnalyticsAggregator:

    def test_compute_summary_empty_sessions(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            summary = agg._compute_summary([], [])
            assert summary['total_sessions'] == 0
            assert summary['total_focused_hours'] == 0.0

    def test_compute_summary_with_sessions(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            sessions = make_mock_sessions(5)
            summary = agg._compute_summary(sessions, [])
            assert summary['total_sessions'] == 5
            assert summary['total_focused_hours'] > 0

    def test_compute_streak_consecutive_days(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            sessions = make_mock_sessions(7)
            streak = agg._compute_streak(sessions)
            assert streak['longest_streak'] >= 1

    def test_compute_streak_empty(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            streak = agg._compute_streak([])
            assert streak['current_streak'] == 0
            assert streak['longest_streak'] == 0

    def test_compute_weekly_trend_groups_by_week(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            sessions = make_mock_sessions(14)
            trend = agg._compute_weekly_trend(sessions)
            assert len(trend) >= 1
            assert 'week_label' in trend[0]
            assert 'avg_score' in trend[0]
            assert 'total_hours' in trend[0]

    def test_compute_best_day_returns_day_name(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            sessions = make_mock_sessions(10)
            best_day = agg._compute_best_day(sessions)
            if best_day:
                assert 'day_name' in best_day
                assert 'avg_score' in best_day

    def test_compute_daily_breakdown_length(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            sessions = make_mock_sessions(10)
            breakdown = agg._compute_daily_breakdown(sessions, 14)
            assert len(breakdown) == 14

    def test_time_breakdown_categories(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            activity = [
                {'domain': 'youtube.com', 'duration_seconds': 600},
                {'domain': 'github.com', 'duration_seconds': 1200},
                {'domain': 'notion.so', 'duration_seconds': 300}
            ]
            breakdown = agg._compute_time_breakdown(activity)
            names = [c['name'] for c in breakdown['categories']]
            assert 'Productive' in names
            assert 'Distraction' in names

    def test_risk_trend_groups_by_date(self):
        with patch('app.analytics.aggregator.get_supabase') as mock_sb:
            mock_sb.return_value = MagicMock()
            from app.analytics.aggregator import AnalyticsAggregator
            agg = AnalyticsAggregator('test-user')
            hist = [
                {'risk_score': 0.4, 'assessed_at': '2026-03-10T09:00:00'},
                {'risk_score': 0.6, 'assessed_at': '2026-03-10T10:00:00'},
                {'risk_score': 0.3, 'assessed_at': '2026-03-11T09:00:00'}
            ]
            trend = agg._compute_risk_trend(hist)
            assert len(trend) == 2
            assert trend[0]['avg_risk'] == pytest.approx(0.5, 0.01)


class TestWeeklyReportGenerator:

    def test_report_has_required_keys(self):
        with patch('app.analytics.report_generator.AnalyticsAggregator') as mock_agg:
            mock_instance = MagicMock()
            mock_instance.compute_all.return_value = {
                'summary': {
                    'total_sessions': 10,
                    'total_focused_hours': 7.5,
                    'avg_focus_score': 7.2,
                    'completion_rate': 80.0,
                    'total_distraction_mins': 20.0,
                    'avg_session_duration': 45.0
                },
                'agent_stats': {
                    'total_interventions': 5,
                    'intervention_success_rate': 60.0,
                    'total_actions': 8
                },
                'streak': {'current_streak': 3, 'longest_streak': 5},
                'best_day': {'day_name': 'Monday', 'avg_score': 8.0},
                'best_hour': {'hour_label': '9:00 AM', 'avg_score': 8.5},
                'daily_breakdown': []
            }
            mock_agg.return_value = mock_instance

            from app.analytics.report_generator import WeeklyReportGenerator
            gen = WeeklyReportGenerator('test-user')
            with patch.object(gen, '_compute_last_week', return_value={
                'total_sessions': 8,
                'total_focused_hours': 6.0,
                'avg_focus_score': 6.5,
                'completion_rate': 70.0
            }):
                report = gen.generate()

            required = [
                'week_label', 'this_week', 'last_week',
                'improvement', 'achievements', 'recommendations'
            ]
            for key in required:
                assert key in report, f"Missing: {key}"

    def test_improvement_positive_when_score_increases(self):
        with patch('app.analytics.report_generator.AnalyticsAggregator'):
            from app.analytics.report_generator import WeeklyReportGenerator
            gen = WeeklyReportGenerator('test-user')
            imp = gen._compute_improvement(
                {
                    'avg_focus_score': 8.0,
                    'total_sessions': 10,
                    'total_focused_hours': 8.0
                },
                {
                    'avg_focus_score': 6.0,
                    'total_sessions': 8,
                    'total_focused_hours': 6.0
                }
            )
            assert imp['is_improving'] is True
            assert imp['score_pct'] > 0

    def test_improvement_negative_when_score_drops(self):
        with patch('app.analytics.report_generator.AnalyticsAggregator'):
            from app.analytics.report_generator import WeeklyReportGenerator
            gen = WeeklyReportGenerator('test-user')
            imp = gen._compute_improvement(
                {
                    'avg_focus_score': 5.0,
                    'total_sessions': 5,
                    'total_focused_hours': 4.0
                },
                {
                    'avg_focus_score': 8.0,
                    'total_sessions': 10,
                    'total_focused_hours': 8.0
                }
            )
            assert imp['is_improving'] is False
            assert imp['score_pct'] < 0
