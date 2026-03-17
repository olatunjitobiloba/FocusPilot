# tests/conftest.py
"""
Shared test fixtures and configuration.
conftest.py is automatically loaded by pytest before any test file.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
import uuid


# ── Disable background workers ─────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def disable_background_workers():
    """
    Prevent the orchestrator and action scheduler from starting during tests.
    Their background threads make real network calls to Supabase which can
    interfere with the Supabase client used by test fixtures.
    """
    with (
        patch("app.main.orchestrator.start"),
        patch("app.main.orchestrator.stop"),
        patch("app.main.action_scheduler.start"),
        patch("app.main.action_scheduler.stop"),
    ):
        yield

# ── Test client ────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def client():
    """
    Create a test client for the FastAPI app.
    scope="module" means one client per test file (faster).
    """
    with TestClient(app) as c:
        yield c


# ── Test user ──────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def test_user():
    """
    Return test user credentials.
    Uses a unique email so tests don't conflict.
    """
    unique_id = str(uuid.uuid4())[:8]
    return {
        "email":     f"test_{unique_id}@focuspilot.dev",
        "password":  "TestPassword123!",
        "full_name": "Test User"
    }


# ── Auth token ─────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def auth_token(client, test_user):
    """
    Create a test user and return their JWT token.
    All protected endpoint tests use this.
    """
    response = client.post("/auth/signup", json=test_user)
    if response.status_code == 200:
        token = response.json()["access_token"]
    elif response.status_code == 400 and "already" in response.text.lower():
        login_response = client.post("/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["access_token"]
    else:
        assert response.status_code == 200, f"Signup failed: {response.text}"

    return token


# ── Auth headers ───────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """
    Return headers dict with Authorization token.
    Use this in every protected endpoint test.
    """
    return {"Authorization": f"Bearer {auth_token}"}
