import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def valid_login_data():
    """Valid login credentials for testing."""
    return {
        "email": "email@example.com",
        "password": "secret"
    }


@pytest.fixture
def valid_api_key_request():
    """Valid API key request for testing."""
    return {
        "name": "Test API Key",
        "description": "Test API key for testing purposes"
    }


@pytest.fixture
def auth_headers():
    """Get authentication headers for protected endpoints."""
    def _get_auth_headers(access_token: str):
        return {"Authorization": f"Bearer {access_token}"}
    return _get_auth_headers
