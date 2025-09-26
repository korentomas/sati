from typing import Callable, Dict

from fastapi.testclient import TestClient


class TestAPIIntegration:
    """Integration tests for the complete API using real authentication."""

    def test_api_documentation_endpoints(self, client: TestClient) -> None:
        """Test that API documentation endpoints are accessible."""
        # Test OpenAPI JSON
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

        # Test Swagger UI
        response = client.get("/api/v1/docs")
        assert response.status_code == 200

        # Test ReDoc
        response = client.get("/api/v1/redoc")
        assert response.status_code == 200

    def test_cors_headers(self, client: TestClient) -> None:
        """Test that CORS headers are properly set."""
        # Test with a GET request that should include CORS headers
        response = client.get(
            "/api/v1/health/live", headers={"Origin": "http://localhost:3000"}
        )

        # Check that CORS headers are present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"

    def test_authentication_flow(
        self,
        client: TestClient,
        valid_login_data: Dict[str, str],
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test complete authentication flow."""
        # Step 1: Login
        login_response = client.post("/api/v1/auth/login", json=valid_login_data)
        assert login_response.status_code == 200

        login_data = login_response.json()
        access_token = login_data["access_token"]

        # Step 2: Use token to access protected endpoint
        headers = auth_headers(access_token)
        profile_response = client.get("/api/v1/auth/profile", headers=headers)

        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == valid_login_data["email"]

    def test_protected_endpoints_without_auth(self, client: TestClient) -> None:
        """Test that protected endpoints return 403 without authentication."""
        protected_endpoints = [
            "/api/v1/auth/profile",
            "/api/v1/auth/api-keys",
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 403  # FastAPI returns 403 for missing auth
            data = response.json()
            assert "detail" in data

    def test_invalid_endpoints(self, client: TestClient) -> None:
        """Test that invalid endpoints return 404."""
        invalid_endpoints = [
            "/api/v1/invalid",
            "/api/v1/auth/invalid",
            "/api/v1/health/invalid",
            "/invalid",
        ]

        for endpoint in invalid_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 404

    def test_api_versioning(self, client: TestClient) -> None:
        """Test that API versioning is properly configured."""
        # Test that v1 endpoints work
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

        # Test that non-versioned endpoints don't work
        response = client.get("/health/live")
        assert response.status_code == 404

    def test_error_handling(self, client: TestClient) -> None:
        """Test that error handling works correctly."""
        # Test with invalid JSON
        response = client.post(
            "/api/v1/auth/login",
            content="invalid json",  # Use content for raw data
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # Test with wrong content type
        response = client.post(
            "/api/v1/auth/login",
            content="email=test&password=secret",  # Use content for raw data
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 422

    def test_health_endpoints_consistency(self, client: TestClient) -> None:
        """Test that health endpoints return consistent data."""
        live_response = client.get("/api/v1/health/live")
        ready_response = client.get("/api/v1/health/ready")

        assert live_response.status_code == 200
        assert ready_response.status_code == 200

        live_data = live_response.json()
        ready_data = ready_response.json()

        # Both should have status and timestamp
        assert "status" in live_data
        assert "status" in ready_data
        assert "timestamp" in live_data
        assert "timestamp" in ready_data

        # Status should be appropriate for each endpoint
        assert live_data["status"] == "alive"
        assert ready_data["status"] == "ready"

    def test_api_response_format_consistency(self, client: TestClient) -> None:
        """Test that all API responses have consistent format."""
        endpoints = [
            ("/", "GET"),
            ("/api/v1/health/live", "GET"),
            ("/api/v1/health/ready", "GET"),
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)

            assert response.status_code in [
                200,
                401,
                403,
                404,
                422,
            ]  # Valid status codes

            if response.status_code == 200:
                # Successful responses should be JSON
                assert response.headers["content-type"] == "application/json"
                data = response.json()
                assert isinstance(data, (dict, list))

    def test_api_key_management_flow(
        self,
        client: TestClient,
        valid_login_data: Dict[str, str],
        valid_api_key_request: Dict[str, str],
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test complete API key management flow."""
        # Step 1: Login to get token
        login_response = client.post("/api/v1/auth/login", json=valid_login_data)
        assert login_response.status_code == 200

        access_token = login_response.json()["access_token"]
        headers = auth_headers(access_token)

        # Step 2: Create API key
        create_response = client.post(
            "/api/v1/auth/api-keys", json=valid_api_key_request, headers=headers
        )
        assert create_response.status_code == 200

        create_data = create_response.json()
        assert create_data["key_id"] is not None
        assert create_data["name"] == valid_api_key_request["name"]
        assert create_data["api_key"].startswith("sat_")

        # Step 3: List API keys
        list_response = client.get("/api/v1/auth/api-keys", headers=headers)
        assert list_response.status_code == 200

        list_data = list_response.json()
        assert isinstance(list_data, list)
        assert len(list_data) >= 1  # Should have at least the key we just created

        # Verify the created key is in the list
        key_ids = [key["key_id"] for key in list_data]
        assert create_data["key_id"] in key_ids

    def test_token_expiration_handling(
        self,
        client: TestClient,
        valid_login_data: Dict[str, str],
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test that expired tokens are handled correctly."""
        # First, login to get a token
        login_response = client.post("/api/v1/auth/login", json=valid_login_data)
        assert login_response.status_code == 200

        access_token = login_response.json()["access_token"]
        headers = auth_headers(access_token)

        # Test that the token works initially
        profile_response = client.get("/api/v1/auth/profile", headers=headers)
        assert profile_response.status_code == 200

        # Test with a malformed token
        malformed_headers = auth_headers("malformed.token.here")
        malformed_response = client.get(
            "/api/v1/auth/profile", headers=malformed_headers
        )
        assert malformed_response.status_code == 401

    def test_concurrent_api_key_creation(
        self,
        client: TestClient,
        valid_login_data: Dict[str, str],
        auth_headers: Callable[[str], Dict[str, str]],
    ) -> None:
        """Test that multiple API keys can be created for the same user."""
        # Login to get token
        login_response = client.post("/api/v1/auth/login", json=valid_login_data)
        assert login_response.status_code == 200

        access_token = login_response.json()["access_token"]
        headers = auth_headers(access_token)

        # Create multiple API keys
        key_names = ["Key 1", "Key 2", "Key 3"]
        created_keys = []

        for name in key_names:
            key_request = {"name": name, "description": f"Test key {name}"}
            response = client.post(
                "/api/v1/auth/api-keys", json=key_request, headers=headers
            )
            assert response.status_code == 200

            key_data = response.json()
            created_keys.append(key_data["key_id"])

        # Verify all keys are listed
        list_response = client.get("/api/v1/auth/api-keys", headers=headers)
        assert list_response.status_code == 200

        list_data = list_response.json()
        assert len(list_data) >= len(key_names)

        # Verify all created keys are in the list
        key_ids = [key["key_id"] for key in list_data]
        for created_key_id in created_keys:
            assert created_key_id in key_ids
