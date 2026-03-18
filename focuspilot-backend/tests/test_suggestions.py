# tests/test_suggestions.py
"""
Tests for ML site suggestion endpoints.
Run with: pytest tests/test_suggestions.py -v
"""

import pytest
from app.routes.suggestions import normalize_domain


class TestSuggestionDomainNormalization:

    def test_normalize_domain_strips_scheme_www_and_path(self):
        assert normalize_domain('https://www.instagram.com/reel/abc') == 'instagram.com'

    def test_normalize_domain_keeps_typo_domain_distinct(self):
        # Typo domains are intentionally not merged with real domains.
        assert normalize_domain('www.instagtam.com') == 'instagtam.com'
        assert normalize_domain('instagram.com') == 'instagram.com'


class TestGetSuggestions:
    """Test GET /suggestions/"""

    def test_suggestions_structure(self, client, auth_headers):
        """Returns suggestions with correct structure"""
        response = client.get("/suggestions/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "suggestions"       in data
        assert "message"           in data
        assert "data_points"       in data
        assert isinstance(data["suggestions"], list)

    def test_suggestions_have_required_fields(self, client, auth_headers):
        """Each suggestion has domain, score, confidence, reason"""
        response = client.get("/suggestions/", headers=auth_headers)
        data = response.json()

        for suggestion in data["suggestions"]:
            assert "domain"            in suggestion
            assert "distraction_score" in suggestion
            assert "confidence"        in suggestion
            assert "reason"            in suggestion
            assert "total_visits"      in suggestion

            # Score should be 0-100
            assert 0 <= suggestion["distraction_score"] <= 100

            # Confidence should be valid
            assert suggestion["confidence"] in ["high", "medium", "low"]


class TestAcceptSuggestion:
    """Test POST /suggestions/accept"""

    def test_accept_suggestion_success(self, client, auth_headers):
        """Can accept a suggestion to add to blocklist"""
        response = client.post(
            "/suggestions/accept",
            json={"domain": "test-distraction.com"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert data["action"] == "blocked"

    def test_accept_suggestion_missing_domain(self, client, auth_headers):
        """Fails if domain is missing"""
        response = client.post(
            "/suggestions/accept",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 400


class TestDismissSuggestion:
    """Test POST /suggestions/dismiss"""

    def test_dismiss_suggestion_success(self, client, auth_headers):
        """Can dismiss a suggestion"""
        response = client.post(
            "/suggestions/dismiss",
            json={"domain": "some-site.com"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["action"] == "dismissed"


class TestBlocklist:
    """Test blocklist endpoints"""

    def test_get_blocklist(self, client, auth_headers):
        """Can retrieve blocklist"""
        response = client.get("/blocklist/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "blocklist" in data
        assert isinstance(data["blocklist"], list)

    def test_add_to_blocklist(self, client, auth_headers):
        """Can add domain to blocklist"""
        import uuid
        unique_domain = f"test-{uuid.uuid4().hex[:6]}.com"

        response = client.post(
            "/blocklist/",
            json={"domain": unique_domain, "reason": "Test"},
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "added" in response.json()["message"].lower()

    def test_remove_from_blocklist(self, client, auth_headers):
        """Can remove domain from blocklist"""
        import uuid
        unique_domain = f"remove-{uuid.uuid4().hex[:6]}.com"

        # Add first
        client.post(
            "/blocklist/",
            json={"domain": unique_domain},
            headers=auth_headers
        )

        # Then remove
        response = client.delete(
            f"/blocklist/{unique_domain}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "removed" in response.json()["message"].lower()
