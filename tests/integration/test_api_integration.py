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
