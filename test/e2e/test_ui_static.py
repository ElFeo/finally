"""
E2E: UI static content tests.
Verifies the frontend HTML is served correctly by the FastAPI app
and that the frontend build artifacts are present.
"""
from __future__ import annotations

import os


FRONTEND_OUT = os.path.join(
    os.path.dirname(__file__), "..", "..", "frontend", "out"
)


class TestStaticFrontendServing:
    def test_root_returns_200(self, client):
        """Backend serves the Next.js static export at root."""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_content_type_is_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.headers.get("content-type", "")

    def test_root_contains_finally_title(self, client):
        resp = client.get("/")
        assert "FinAlly" in resp.text

    def test_root_contains_ai_trading_workstation(self, client):
        resp = client.get("/")
        assert "AI Trading Workstation" in resp.text or "trading" in resp.text.lower()

    def test_api_routes_take_priority_over_static(self, client):
        """API routes must be registered before static files."""
        resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_static_css_is_served(self, client):
        """The Next.js CSS bundle should be served."""
        css_dir = os.path.join(FRONTEND_OUT, "_next", "static", "css")
        if not os.path.isdir(css_dir):
            import pytest
            pytest.skip("No CSS directory in build")

        css_files = [f for f in os.listdir(css_dir) if f.endswith(".css")]
        assert len(css_files) > 0, "No CSS files in frontend build"
        css_file = css_files[0]
        resp = client.get(f"/_next/static/css/{css_file}")
        assert resp.status_code == 200
        assert "text/css" in resp.headers.get("content-type", "")

    def test_js_chunk_is_served(self, client):
        """JS chunks from the Next.js build should be served."""
        chunks_dir = os.path.join(FRONTEND_OUT, "_next", "static", "chunks")
        if not os.path.isdir(chunks_dir):
            import pytest
            pytest.skip("No JS chunks directory in build")

        js_files = [f for f in os.listdir(chunks_dir) if f.endswith(".js")]
        assert len(js_files) > 0, "No JS chunk files in build"
        # Try to serve the first chunk
        js_file = js_files[0]
        resp = client.get(f"/_next/static/chunks/{js_file}")
        assert resp.status_code == 200


class TestFrontendBuildArtifacts:
    """Verify frontend build output contains expected files (no server needed)."""

    def test_index_html_exists(self):
        path = os.path.join(FRONTEND_OUT, "index.html")
        assert os.path.exists(path), f"index.html missing at {path}"

    def test_index_html_has_finally_title(self):
        path = os.path.join(FRONTEND_OUT, "index.html")
        with open(path) as f:
            content = f.read()
        assert "FinAlly" in content

    def test_next_static_dir_exists(self):
        path = os.path.join(FRONTEND_OUT, "_next", "static")
        assert os.path.isdir(path), f"_next/static directory missing at {path}"

    def test_js_chunks_exist(self):
        chunks_dir = os.path.join(FRONTEND_OUT, "_next", "static", "chunks")
        assert os.path.isdir(chunks_dir), "No _next/static/chunks directory in build"
        js_files = [f for f in os.listdir(chunks_dir) if f.endswith(".js")]
        assert len(js_files) > 0, "No JS chunk files found in build"

    def test_css_exists(self):
        css_dir = os.path.join(FRONTEND_OUT, "_next", "static", "css")
        assert os.path.isdir(css_dir), "No CSS directory in build"
        css_files = [f for f in os.listdir(css_dir) if f.endswith(".css")]
        assert len(css_files) > 0, "No CSS files in build"

    def test_404_html_exists(self):
        path = os.path.join(FRONTEND_OUT, "404.html")
        assert os.path.exists(path), f"404.html missing at {path}"
