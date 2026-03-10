# tests/test_sessions.py
"""
Tests for session endpoints.
Run with: pytest tests/test_sessions.py -v
"""

import pytest
import uuid


class TestStartSession:
    """Test POST /sessions/start"""

    def test_start_session_success(self, client, auth_headers):
        """Authenticated user can start a session"""
        response = client.post(
            "/sessions/start",
            json={"planned_duration": 25},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "session" in data
        assert "id" in data["session"]
        assert "start_time" in data["session"]
        assert data["message"] == "Session started"

        # Save session_id for other tests
        pytest.active_session_id = data["session"]["id"]

    def test_cannot_start_duplicate_session(self, client, auth_headers):
        """Cannot start a session when one is already active"""
        response = client.post(
            "/sessions/start",
            json={"planned_duration": 25},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_start_session_no_auth(self, client):
        """Cannot start session without authentication"""
        response = client.post(
            "/sessions/start",
            json={"planned_duration": 25}
        )
        assert response.status_code == 401


class TestActiveSession:
    """Test GET /sessions/active"""

    def test_get_active_session(self, client, auth_headers):
        """Returns active session when one exists"""
        response = client.get("/sessions/active", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["active"]      == True
        assert "session" in data
        assert "id" in data["session"]
        assert "elapsed_minutes" in data["session"]
        assert data["session"]["elapsed_minutes"] >= 0


class TestLogActivity:
    """Test POST /sessions/{id}/activity"""

    def test_log_activity_success(self, client, auth_headers):
        """Can log browsing activity during a session"""
        session_id = pytest.active_session_id

        response = client.post(
            f"/sessions/{session_id}/activity",
            json={
                "url":              "https://www.youtube.com/watch?v=abc",
                "domain":           "youtube.com",
                "duration_seconds": 120
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Activity logged"

    def test_log_activity_wrong_session(self, client, auth_headers):
        """Cannot log activity for a session that doesn't belong to user"""
        response = client.post(
            f"/sessions/{uuid.uuid4()}/activity",
            json={
                "url":              "https://youtube.com",
                "domain":           "youtube.com",
                "duration_seconds": 60
            },
            headers=auth_headers
        )
        assert response.status_code == 404


class TestEndSession:
    """Test POST /sessions/end"""

    def test_end_session_success(self, client, auth_headers):
        """Can end an active session"""
        session_id = pytest.active_session_id

        response = client.post(
            "/sessions/end",
            json={
                "session_id":  session_id,
                "focus_score": 8
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"]    == session_id
        assert data["focus_score"]   == 8
        assert "duration_minutes"    in data
        assert data["duration_minutes"] >= 0

    def test_no_active_session_after_end(self, client, auth_headers):
        """After ending, no active session should exist"""
        response = client.get("/sessions/active", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["active"] == False


class TestSessionHistory:
    """Test GET /sessions/history"""

    def test_get_history(self, client, auth_headers):
        """Can retrieve session history"""
        response = client.get(
            "/sessions/history?limit=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_get_summary(self, client, auth_headers):
        """Can retrieve session summary stats"""
        response = client.get("/sessions/summary", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "total_sessions"       in data
        assert "total_hours"          in data
        assert "avg_session_minutes"  in data
        assert "avg_focus_score"      in data
