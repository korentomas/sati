import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from tests.mocks.mock_supabase import create_mock_supabase_auth


@pytest.fixture
def mock_supabase_auth():
    """Create a mock Supabase authentication instance for testing."""
    return create_mock_supabase_auth()


@pytest.fixture
def client(mock_supabase_auth):
    """Create a test client for the FastAPI application with mocked Supabase."""
    # Patch the supabase_auth module to use our mock
    with patch(
        "app.api.v1.features.authentication.handler.supabase_auth", mock_supabase_auth
    ):
        with patch("app.api.v1.shared.auth.deps.supabase_auth", mock_supabase_auth):
            yield TestClient(app)


@pytest.fixture
def valid_login_data():
    """Valid login credentials for testing."""
    return {"email": "email@example.com", "password": "secret"}


@pytest.fixture
def valid_api_key_request():
    """Valid API key request for testing."""
    return {"name": "Test API Key", "description": "Test API key for testing purposes"}


@pytest.fixture
def auth_headers():
    """Get authentication headers for protected endpoints."""

    def _get_auth_headers(access_token: str):
        return {"Authorization": f"Bearer {access_token}"}

    return _get_auth_headers
