"""Tests for the /api/watchlist endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.watchlist import router

USER_ID = "default"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WATCHLIST_DB = [
    {"id": "1", "ticker": "AAPL", "added_at": "2024-01-01T00:00:00.000000Z"},
    {"id": "2", "ticker": "GOOGL", "added_at": "2024-01-01T00:00:01.000000Z"},
]

_AAPL_UPDATE = MagicMock(
    price=192.50,
    previous_price=191.00,
    change=1.50,
    change_percent=0.79,
    direction="up",
)

_GOOGL_UPDATE = MagicMock(
    price=175.00,
    previous_price=175.00,
    change=0.0,
    change_percent=0.0,
    direction="flat",
)


def _make_cache(ticker_map: dict | None = None) -> MagicMock:
    """Build a mock PriceCache that returns PriceUpdate mocks."""
    cache = MagicMock()
    defaults = {"AAPL": _AAPL_UPDATE, "GOOGL": _GOOGL_UPDATE}
    mapping = {**defaults, **(ticker_map or {})}

    def _get(ticker):
        return mapping.get(ticker)

    cache.get.side_effect = _get
    return cache


def _make_market_source() -> AsyncMock:
    source = AsyncMock()
    return source


def _make_app(cache=None, source=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.price_cache = cache or _make_cache()
    app.state.market_source = source or _make_market_source()
    return app


# ---------------------------------------------------------------------------
# GET /api/watchlist
# ---------------------------------------------------------------------------

class TestGetWatchlist:
    def test_returns_200(self):
        with patch("app.routes.watchlist.get_watchlist", return_value=_WATCHLIST_DB):
            client = TestClient(_make_app())
            response = client.get("/api/watchlist")
        assert response.status_code == 200

    def test_response_has_tickers_key(self):
        with patch("app.routes.watchlist.get_watchlist", return_value=_WATCHLIST_DB):
            client = TestClient(_make_app())
            data = client.get("/api/watchlist").json()
        assert "tickers" in data

    def test_tickers_have_price_data(self):
        with patch("app.routes.watchlist.get_watchlist", return_value=_WATCHLIST_DB):
            client = TestClient(_make_app())
            data = client.get("/api/watchlist").json()
        ticker_data = data["tickers"]
        assert len(ticker_data) == 2
        aapl = next(t for t in ticker_data if t["ticker"] == "AAPL")
        assert aapl["price"] == 192.50
        assert aapl["direction"] == "up"
        assert aapl["change"] == 1.50

    def test_ticker_without_price_returns_none_values(self):
        """Tickers not yet in the cache should return None for price fields."""
        db = [{"id": "3", "ticker": "TSLA", "added_at": "2024-01-01T00:00:02.000000Z"}]
        cache = _make_cache({"TSLA": None})
        with patch("app.routes.watchlist.get_watchlist", return_value=db):
            client = TestClient(_make_app(cache=cache))
            data = client.get("/api/watchlist").json()
        tsla = data["tickers"][0]
        assert tsla["price"] is None
        assert tsla["direction"] == "flat"

    def test_empty_watchlist_returns_empty_list(self):
        with patch("app.routes.watchlist.get_watchlist", return_value=[]):
            client = TestClient(_make_app())
            data = client.get("/api/watchlist").json()
        assert data["tickers"] == []


# ---------------------------------------------------------------------------
# POST /api/watchlist
# ---------------------------------------------------------------------------

class TestAddTicker:
    def _add_result(self, ticker="PYPL"):
        return {"id": "abc", "ticker": ticker, "added_at": "2024-01-02T00:00:00.000000Z"}

    def test_add_new_ticker_returns_201(self):
        with patch("app.routes.watchlist.add_to_watchlist", return_value=self._add_result()):
            client = TestClient(_make_app())
            response = client.post("/api/watchlist", json={"ticker": "PYPL"})
        assert response.status_code == 201

    def test_add_new_ticker_response_shape(self):
        with patch("app.routes.watchlist.add_to_watchlist", return_value=self._add_result()):
            client = TestClient(_make_app())
            data = client.post("/api/watchlist", json={"ticker": "PYPL"}).json()
        assert data["ticker"] == "PYPL"
        assert "added_at" in data

    def test_add_ticker_uppercases(self):
        """Ticker should be stored uppercased."""
        with patch(
            "app.routes.watchlist.add_to_watchlist",
            return_value=self._add_result("PYPL"),
        ) as mock_add:
            client = TestClient(_make_app())
            client.post("/api/watchlist", json={"ticker": "pypl"})
        mock_add.assert_called_once_with(USER_ID, "PYPL")

    def test_add_duplicate_ticker_returns_400(self):
        with patch(
            "app.routes.watchlist.add_to_watchlist",
            side_effect=ValueError("Ticker 'AAPL' is already in the watchlist"),
        ):
            client = TestClient(_make_app())
            response = client.post("/api/watchlist", json={"ticker": "AAPL"})
        assert response.status_code == 400

    def test_add_ticker_calls_market_source(self):
        source = _make_market_source()
        with patch("app.routes.watchlist.add_to_watchlist", return_value=self._add_result()):
            client = TestClient(_make_app(source=source))
            client.post("/api/watchlist", json={"ticker": "PYPL"})
        source.add_ticker.assert_called_once_with("PYPL")

    def test_add_empty_ticker_returns_400(self):
        client = TestClient(_make_app())
        response = client.post("/api/watchlist", json={"ticker": "  "})
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/watchlist/{ticker}
# ---------------------------------------------------------------------------

class TestRemoveTicker:
    def test_remove_existing_ticker_returns_200(self):
        with patch("app.routes.watchlist.remove_from_watchlist", return_value=True):
            client = TestClient(_make_app())
            response = client.delete("/api/watchlist/AAPL")
        assert response.status_code == 200

    def test_remove_existing_ticker_response(self):
        with patch("app.routes.watchlist.remove_from_watchlist", return_value=True):
            client = TestClient(_make_app())
            data = client.delete("/api/watchlist/AAPL").json()
        assert data["success"] is True

    def test_remove_missing_ticker_returns_404(self):
        with patch("app.routes.watchlist.remove_from_watchlist", return_value=False):
            client = TestClient(_make_app())
            response = client.delete("/api/watchlist/UNKNOWN")
        assert response.status_code == 404

    def test_remove_ticker_calls_market_source(self):
        source = _make_market_source()
        with patch("app.routes.watchlist.remove_from_watchlist", return_value=True):
            client = TestClient(_make_app(source=source))
            client.delete("/api/watchlist/AAPL")
        source.remove_ticker.assert_called_once_with("AAPL")

    def test_remove_ticker_lowercased_path_uppercases(self):
        """Path param should be normalised to uppercase before DB lookup."""
        with patch(
            "app.routes.watchlist.remove_from_watchlist", return_value=True
        ) as mock_rm:
            client = TestClient(_make_app())
            client.delete("/api/watchlist/aapl")
        mock_rm.assert_called_once_with(USER_ID, "AAPL")
