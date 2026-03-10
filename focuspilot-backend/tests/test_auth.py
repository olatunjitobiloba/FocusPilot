# tests/test_auth.py
"""
Tests for authentication endpoints.
Run with: pytest tests/test_auth.py -v
"""

import pytest


class TestSignup:
    """Test POST /auth/signup"""

    def test_signup_success(self, client):
        """New user can sign up with valid data"""
        import uuid
        unique = str(uuid.uuid4())[:8]

        response = client.post("/auth/signup", json={
            "email":     f"new_{unique}@test.com",
            "password":  "Password123!",
            "full_name": "New User"
        })

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "token_type"   in data
        assert "user"         in data

        # Check user data
        assert data["user"]["email"]     == f"new_{unique}@test.com"
        assert data["user"]["full_name"] == "New User"
        assert "id" in data["user"]

        # Token should be a non-empty string
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 10

    def test_signup_duplicate_email(self, client, test_user):
        """Cannot sign up with an email that already exists"""
        # First signup (already done in fixture, but do it again)
        client.post("/auth/signup", json=test_user)

        # Second signup with same email
        response = client.post("/auth/signup", json=test_user)

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_missing_fields(self, client):
        """Signup fails if required fields are missing"""
        response = client.post("/auth/signup", json={
            "email": "missing@test.com"
            # Missing password and full_name
        })
        assert response.status_code == 422  # Unprocessable Entity

    def test_signup_invalid_email(self, client):
        """Signup fails with invalid email format"""
        response = client.post("/auth/signup", json={
            "email":     "not-an-email",
            "password":  "Password123!",
            "full_name": "Test User"
        })
        assert response.status_code == 422


class TestLogin:
    """Test POST /auth/login"""

    def test_login_success(self, client, test_user, auth_token):
        """Existing user can log in with correct credentials"""
        response = client.post("/auth/login", json={
            "email":    test_user["email"],
            "password": test_user["password"]
        })

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["user"]["email"] == test_user["email"]

    def test_login_wrong_password(self, client, test_user):
        """Login fails with wrong password"""
        response = client.post("/auth/login", json={
            "email":    test_user["email"],
            "password": "WrongPassword!"
        })
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Login fails for email that doesn't exist"""
        response = client.post("/auth/login", json={
            "email":    "ghost@nowhere.com",
            "password": "Password123!"
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Login fails if fields are missing"""
        response = client.post("/auth/login", json={
            "email": "test@test.com"
        })
        assert response.status_code == 422


class TestGetCurrentUser:
    """Test GET /auth/me"""

    def test_get_me_success(self, client, auth_headers, test_user):
        """Authenticated user can get their profile"""
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["email"]     == test_user["email"]
        assert data["full_name"] == test_user["full_name"]
        assert "id" in data

    def test_get_me_no_token(self, client):
        """Cannot access /me without token"""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Cannot access /me with fake token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer fake.token.here"}
        )
        assert response.status_code == 401
