"""Mock Supabase client for testing."""

from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock


class MockUser:
    """Mock Supabase user object."""

    def __init__(self, email: str, user_id: str = "test-user-123"):
        self.id = user_id
        self.email = email
        self.created_at = datetime.utcnow().isoformat()
        self.identities = [{"provider": "email"}]


class MockAuthResponse:
    """Mock Supabase auth response."""

    def __init__(self, user: Optional[MockUser] = None, session: Optional[Dict] = None):
        self.user = user
        self.session = session


class MockSupabaseAuth:
    """Mock Supabase auth client."""

    # Test user database - matches the test fixtures
    _test_users = {
        "email@example.com": {
            "password": "secret",
            "user_id": "test-user-123",
        }
    }

    def sign_in_with_password(self, credentials: Dict[str, str]) -> MockAuthResponse:
        """Mock sign in with password."""
        email = credentials.get("email")
        password = credentials.get("password")

        # Check if user exists and password matches
        if (
            email in self._test_users
            and self._test_users[email]["password"] == password
        ):
            user = MockUser(email, self._test_users[email]["user_id"])
            return MockAuthResponse(user=user)

        # Return empty response for invalid credentials
        return MockAuthResponse()

    def sign_up(self, credentials: Dict[str, Any]) -> MockAuthResponse:
        """Mock sign up."""
        email = credentials.get("email")
        password = credentials.get("password")

        # Check if user already exists
        if email in self._test_users:
            return MockAuthResponse()

        # Create new user
        user_id = f"test-user-{len(self._test_users) + 1}"
        self._test_users[email] = {
            "password": password,
            "user_id": user_id,
        }

        user = MockUser(email, user_id)
        return MockAuthResponse(user=user)

    def get_user(self, token: str) -> MockAuthResponse:
        """Mock get user from token."""
        # For testing, we'll just return a test user if token is valid
        if token and token.startswith("valid_token"):
            return MockAuthResponse(user=MockUser("email@example.com"))
        return MockAuthResponse()

    def sign_out(self):
        """Mock sign out."""
        pass


class MockSupabaseClient:
    """Mock Supabase client."""

    def __init__(self):
        self.auth = MockSupabaseAuth()


def create_mock_supabase_auth():
    """Create a mock SupabaseAuth instance for testing."""
    mock_auth = MagicMock()
    mock_auth.client = MockSupabaseClient()
    mock_auth.admin_client = MockSupabaseClient()

    async def mock_verify_token(token: str):
        """Mock token verification."""
        if token == "valid_token":
            return MockUser("email@example.com")
        return None

    async def mock_verify_token_by_id(user_id: str):
        """Mock user verification by ID."""
        return None

    mock_auth.verify_token = mock_verify_token
    mock_auth.verify_token_by_id = mock_verify_token_by_id

    return mock_auth
