"""
E2E test fixtures: uses FastAPI's TestClient with the full app (lifespan enabled)
to run integration tests in-process without network isolation issues.
"""
from __future__ import annotations

import os
import sys

import pytest

# Add backend to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, BACKEND_DIR)

# Set environment variables before importing the app
os.environ["LLM_MOCK"] = "true"
os.environ["MASSIVE_API_KEY"] = ""  # Use simulator
os.environ["DB_PATH"] = os.path.join(
    os.environ.get("TMPDIR", "/tmp"), "finally_e2e.db"
)


@pytest.fixture(scope="session")
def app():
    """Create and return the FastAPI app with a fresh test database."""
    # Remove existing test DB so each test run starts clean
    db_path = os.environ["DB_PATH"]
    if os.path.exists(db_path):
        os.remove(db_path)

    from app.main import app as _app
    return _app


@pytest.fixture(scope="session")
def client(app):
    """Return a TestClient for the full app (lifespan runs: DB init, market simulator)."""
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
