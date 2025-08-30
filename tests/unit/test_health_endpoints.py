from datetime import datetime

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    def test_liveness_check(self, client: TestClient):
        """Test the liveness probe endpoint."""
        response = client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "alive"
        assert "timestamp" in data

        # Verify timestamp is a valid ISO format
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)

    def test_readiness_check(self, client: TestClient):
        """Test the readiness probe endpoint."""
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "ready"
        assert "timestamp" in data
        assert "services" in data

        # Verify timestamp is a valid ISO format
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)

        # Verify services structure
        services = data["services"]
        assert "database" in services
        assert "redis" in services
        assert services["database"] == "healthy"
        assert services["redis"] == "healthy"

    def test_health_endpoints_content_type(self, client: TestClient):
        """Test that health endpoints return JSON content type."""
        live_response = client.get("/api/v1/health/live")
        ready_response = client.get("/api/v1/health/ready")

        assert live_response.headers["content-type"] == "application/json"
        assert ready_response.headers["content-type"] == "application/json"

    def test_health_endpoints_response_structure(self, client: TestClient):
        """Test that health endpoints have consistent response structure."""
        live_response = client.get("/api/v1/health/live")
        ready_response = client.get("/api/v1/health/ready")

        live_data = live_response.json()
        ready_data = ready_response.json()

        # Both should have status and timestamp
        assert "status" in live_data
        assert "timestamp" in live_data
        assert "status" in ready_data
        assert "timestamp" in ready_data

        # Status should be string
        assert isinstance(live_data["status"], str)
        assert isinstance(ready_data["status"], str)

        # Timestamp should be string
        assert isinstance(live_data["timestamp"], str)
        assert isinstance(ready_data["timestamp"], str)
