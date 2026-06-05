"""Tests for the /api/health endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.health import router


# ---------------------------------------------------------------------------
# Minimal app fixture — no lifespan, no DB, no market source
# ---------------------------------------------------------------------------

def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetHealth:
    def test_returns_200(self):
        client = TestClient(_make_app())
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_response_has_required_keys(self):
        client = TestClient(_make_app())
        data = client.get("/api/health").json()
        assert "status" in data
        assert "market_data" in data

    def test_status_is_ok(self):
        client = TestClient(_make_app())
        data = client.get("/api/health").json()
        assert data["status"] == "ok"

    def test_market_data_simulator_when_no_key(self):
        with patch.dict("os.environ", {}, clear=False):
            # Ensure MASSIVE_API_KEY is absent / empty
            import os
            os.environ.pop("MASSIVE_API_KEY", None)
            client = TestClient(_make_app())
            data = client.get("/api/health").json()
        assert data["market_data"] == "simulator"

    def test_market_data_massive_when_key_set(self):
        with patch.dict("os.environ", {"MASSIVE_API_KEY": "test-key-123"}):
            client = TestClient(_make_app())
            data = client.get("/api/health").json()
        assert data["market_data"] == "massive"
