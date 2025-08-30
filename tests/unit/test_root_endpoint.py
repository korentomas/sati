from fastapi.testclient import TestClient

from app.core.config import settings


class TestRootEndpoint:
    """Test cases for the root endpoint."""

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint returns correct information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "docs" in data

        assert data["message"] == f"Welcome to {settings.app_name}"
        assert data["version"] == settings.version
        assert data["docs"] == f"{settings.api_v1_prefix}/docs"

    def test_root_endpoint_content_type(self, client: TestClient):
        """Test that root endpoint returns JSON content type."""
        response = client.get("/")

        assert response.headers["content-type"] == "application/json"

    def test_root_endpoint_response_structure(self, client: TestClient):
        """Test that root endpoint has correct response structure."""
        response = client.get("/")
        data = response.json()

        # All fields should be strings
        assert isinstance(data["message"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["docs"], str)

        # Message should contain app name
        assert settings.app_name in data["message"]

        # Docs URL should contain API prefix
        assert settings.api_v1_prefix in data["docs"]
