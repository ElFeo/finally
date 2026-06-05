"""E2E: health endpoint — verifies the live app responds correctly."""
from __future__ import annotations


class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_status_is_ok(self, client):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"

    def test_has_market_data_key(self, client):
        data = client.get("/api/health").json()
        assert "market_data" in data

    def test_market_data_is_simulator(self, client):
        """MASSIVE_API_KEY is empty → should report 'simulator'."""
        data = client.get("/api/health").json()
        assert data["market_data"] == "simulator"
