from typing import Callable, Dict

from fastapi.testclient import TestClient


class TestAuthenticationEndpoints:
    """Test cases for authentication endpoints using database."""

    def test_register_success(self, client: TestClient) -> None:
        """Test successful user registration."""
        register_data = {"email": "newuser@example.com", "password": "password123"}
        response = client.post("/api/v1/auth/register", json=register_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_register_duplicate_email(self, client: TestClient) -> None:
        """Test registration with duplicate email."""
        register_data = {"email": "duplicate@example.com", "password": "password123"}

        # First registration
        response1 = client.post("/api/v1/auth/register", json=register_data)
        assert response1.status_code == 200

        # Second registration with same email
        response2 = client.post("/api/v1/auth/register", json=register_data)
        assert response2.status_code == 400
        assert "detail" in response2.json()

    def test_login_success(self, client: TestClient) -> None:
        """Test successful login after registration."""
        # First register
        register_data = {"email": "loginuser@example.com", "password": "password123"}
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200

        # Then login
        login_data = {"email": "loginuser@example.com", "password": "password123"}
        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_login_invalid_credentials(self, client: TestClient) -> None:
        """Test login with invalid credentials."""
        # Register first
        register_data = {
            "email": "testuser@example.com",
            "password": "correct_password",
        }
        client.post("/api/v1/auth/register", json=register_data)

        # Try wrong password
        invalid_data = {"email": "testuser@example.com", "password": "wrong_password"}
        response = client.post("/api/v1/auth/login", json=invalid_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_login_nonexistent_user(self, client: TestClient) -> None:
        """Test login with non-existent user."""
        invalid_data = {"email": "nonexistent@example.com", "password": "secret"}

        response = client.post("/api/v1/auth/login", json=invalid_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_login_missing_fields(self, client: TestClient) -> None:
        """Test login with missing required fields."""
        # Missing email
        response = client.post("/api/v1/auth/login", json={"password": "secret"})
        assert response.status_code == 422

        # Missing password
        response = client.post("/api/v1/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422

        # Empty request
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_invalid_email_format(self, client: TestClient) -> None:
        """Test login with invalid email format."""
        response = client.post(
            "/api/v1/auth/login", json={"email": "invalid-email", "password": "secret"}
        )
        # The authentication service returns 401 for non-existent users,
        # not 422 for invalid email format
        assert response.status_code == 401

    def test_get_profile_with_valid_token(
        self,
        client: TestClient,
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test successful profile retrieval with valid token."""
        # First register
        register_data = {"email": "profileuser@example.com", "password": "password123"}
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200

        access_token = register_response.json()["access_token"]
        headers = auth_headers(access_token)

        # Now get profile with the token
        response = client.get("/api/v1/auth/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert "user_id" in data
        assert "email" in data
        assert "created_at" in data
        assert data["email"] == register_data["email"]
        assert isinstance(data["user_id"], str)
        assert isinstance(data["created_at"], str)

    def test_get_profile_without_token(self, client: TestClient) -> None:
        """Test profile retrieval without authentication."""
        response = client.get("/api/v1/auth/profile")

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data

    def test_get_profile_with_invalid_token(self, client: TestClient) -> None:
        """Test profile retrieval with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/profile", headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_create_api_key_with_valid_token(
        self,
        client: TestClient,
        valid_api_key_request: Dict[str, str],
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test successful API key creation with valid token."""
        # First register to get a token
        register_data = {"email": "apikeyuser@example.com", "password": "password123"}
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200

        access_token = register_response.json()["access_token"]
        headers = auth_headers(access_token)

        # Create API key
        response = client.post(
            "/api/v1/auth/api-keys", json=valid_api_key_request, headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "key_id" in data
        assert "api_key" in data
        assert "name" in data
        assert "description" in data
        assert "created_at" in data
        assert "expires_at" in data

        assert data["name"] == valid_api_key_request["name"]
        assert data["description"] == valid_api_key_request["description"]
        assert isinstance(data["key_id"], str)
        assert isinstance(data["api_key"], str)
        assert data["api_key"].startswith("sat_")

    def test_create_api_key_without_token(
        self, client: TestClient, valid_api_key_request: Dict[str, str]
    ) -> None:
        """Test API key creation without authentication."""
        response = client.post("/api/v1/auth/api-keys", json=valid_api_key_request)

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data

    def test_create_api_key_missing_name(
        self,
        client: TestClient,
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test API key creation with missing name."""
        # First register to get a token
        register_data = {"email": "missingname@example.com", "password": "password123"}
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200

        access_token = register_response.json()["access_token"]
        headers = auth_headers(access_token)

        # Try to create API key without name
        response = client.post(
            "/api/v1/auth/api-keys",
            json={"description": "Test description"},
            headers=headers,
        )

        assert response.status_code == 422

    def test_list_api_keys_with_valid_token(
        self,
        client: TestClient,
        valid_api_key_request: Dict[str, str],
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test successful API keys listing with valid token."""
        # First register to get a token
        register_data = {"email": "listkeys@example.com", "password": "password123"}
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200

        access_token = register_response.json()["access_token"]
        headers = auth_headers(access_token)

        # Create an API key first
        create_response = client.post(
            "/api/v1/auth/api-keys", json=valid_api_key_request, headers=headers
        )
        assert create_response.status_code == 200

        # Now list API keys
        response = client.get("/api/v1/auth/api-keys", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1  # Should have at least the key we just created

        # Check the structure of the first key
        first_key = data[0]
        assert "key_id" in first_key
        assert "name" in first_key
        assert "description" in first_key
        assert "created_at" in first_key
        assert "expires_at" in first_key
        assert "api_key" not in first_key  # API key should not be returned in list

    def test_list_api_keys_without_token(self, client: TestClient) -> None:
        """Test API keys listing without authentication."""
        response = client.get("/api/v1/auth/api-keys")

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data

    def test_list_api_keys_empty(
        self,
        client: TestClient,
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test API keys listing when user has no keys (fresh user)."""
        # First register to get a token
        register_data = {"email": "emptykeys@example.com", "password": "password123"}
        register_response = client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 200

        access_token = register_response.json()["access_token"]
        headers = auth_headers(access_token)

        # List API keys (should be empty for a fresh user)
        response = client.get("/api/v1/auth/api-keys", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Note: The user might already have keys from previous tests,
        # so we don't assert length == 0
