# tests/test_analytics.py
"""
Tests for analytics endpoints.
Run with: pytest tests/test_analytics.py -v
"""

import pytest


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
