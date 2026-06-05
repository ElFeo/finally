"""Tests for the /api/portfolio endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.portfolio import router

USER_ID = "default"

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_POSITIONS = [
    {
        "ticker": "AAPL",
        "quantity": 10.0,
        "avg_cost": 190.0,
        "updated_at": "2024-01-01T00:00:00.000000Z",
    }
]

_SNAPSHOTS = [
    {"total_value": 10000.0, "recorded_at": "2024-01-01T00:00:00.000000Z"},
    {"total_value": 10500.0, "recorded_at": "2024-01-01T00:30:00.000000Z"},
]


def _make_cache(price: float | None = 192.50) -> MagicMock:
    cache = MagicMock()
    cache.get_price.return_value = price
    return cache


def _make_app(cache=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.price_cache = cache or _make_cache()
    app.state.market_source = AsyncMock()
    return app


# ---------------------------------------------------------------------------
# GET /api/portfolio
# ---------------------------------------------------------------------------

class TestGetPortfolio:
    def test_returns_200(self):
        with (
            patch("app.routes.portfolio.get_positions", return_value=_POSITIONS),
            patch("app.routes.portfolio.get_cash_balance", return_value=10000.0),
        ):
            client = TestClient(_make_app())
            response = client.get("/api/portfolio")
        assert response.status_code == 200

    def test_response_has_required_keys(self):
        with (
            patch("app.routes.portfolio.get_positions", return_value=_POSITIONS),
            patch("app.routes.portfolio.get_cash_balance", return_value=10000.0),
        ):
            client = TestClient(_make_app())
            data = client.get("/api/portfolio").json()
        for key in ("cash_balance", "total_value", "positions", "unrealized_pnl", "unrealized_pnl_pct"):
            assert key in data, f"Missing key: {key}"

    def test_cash_balance_matches(self):
        with (
            patch("app.routes.portfolio.get_positions", return_value=[]),
            patch("app.routes.portfolio.get_cash_balance", return_value=9876.54),
        ):
            client = TestClient(_make_app(_make_cache(None)))
            data = client.get("/api/portfolio").json()
        assert data["cash_balance"] == 9876.54

    def test_total_value_includes_positions(self):
        """total_value = cash + market value of positions (10 * 192.50 = 1925)."""
        with (
            patch("app.routes.portfolio.get_positions", return_value=_POSITIONS),
            patch("app.routes.portfolio.get_cash_balance", return_value=8075.0),
        ):
            client = TestClient(_make_app(_make_cache(192.50)))
            data = client.get("/api/portfolio").json()
        assert data["total_value"] == pytest.approx(8075.0 + 1925.0, rel=1e-4)

    def test_position_pnl_calculation(self):
        """unrealized_pnl = (192.50 - 190.00) * 10 = 25.0"""
        with (
            patch("app.routes.portfolio.get_positions", return_value=_POSITIONS),
            patch("app.routes.portfolio.get_cash_balance", return_value=8075.0),
        ):
            client = TestClient(_make_app(_make_cache(192.50)))
            data = client.get("/api/portfolio").json()
        pos = data["positions"][0]
        assert pos["unrealized_pnl"] == pytest.approx(25.0, rel=1e-4)

    def test_empty_positions(self):
        with (
            patch("app.routes.portfolio.get_positions", return_value=[]),
            patch("app.routes.portfolio.get_cash_balance", return_value=10000.0),
        ):
            client = TestClient(_make_app())
            data = client.get("/api/portfolio").json()
        assert data["positions"] == []
        assert data["total_value"] == 10000.0
        assert data["unrealized_pnl"] == 0.0

    def test_price_fallback_to_avg_cost_when_unavailable(self):
        """When cache returns None, avg_cost is used to value the position."""
        with (
            patch("app.routes.portfolio.get_positions", return_value=_POSITIONS),
            patch("app.routes.portfolio.get_cash_balance", return_value=8100.0),
        ):
            client = TestClient(_make_app(_make_cache(None)))
            data = client.get("/api/portfolio").json()
        pos = data["positions"][0]
        assert pos["current_price"] == 190.0
        assert pos["unrealized_pnl"] == 0.0


# ---------------------------------------------------------------------------
# GET /api/portfolio/history
# ---------------------------------------------------------------------------

class TestGetPortfolioHistory:
    def test_returns_200(self):
        with patch("app.routes.portfolio.get_snapshots", return_value=_SNAPSHOTS):
            client = TestClient(_make_app())
            response = client.get("/api/portfolio/history")
        assert response.status_code == 200

    def test_response_has_snapshots_key(self):
        with patch("app.routes.portfolio.get_snapshots", return_value=_SNAPSHOTS):
            client = TestClient(_make_app())
            data = client.get("/api/portfolio/history").json()
        assert "snapshots" in data

    def test_snapshots_content(self):
        with patch("app.routes.portfolio.get_snapshots", return_value=_SNAPSHOTS):
            client = TestClient(_make_app())
            data = client.get("/api/portfolio/history").json()
        assert len(data["snapshots"]) == 2
        assert data["snapshots"][0]["total_value"] == 10000.0

    def test_empty_history(self):
        with patch("app.routes.portfolio.get_snapshots", return_value=[]):
            client = TestClient(_make_app())
            data = client.get("/api/portfolio/history").json()
        assert data["snapshots"] == []


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade  — buy
# ---------------------------------------------------------------------------

_TRADE_RECORD = {
    "id": "trade-uuid",
    "user_id": USER_ID,
    "ticker": "AAPL",
    "side": "buy",
    "quantity": 10.0,
    "price": 192.50,
    "executed_at": "2024-01-01T01:00:00.000000Z",
}


class TestBuyTrade:
    def _run_buy(self, cash=10000.0, position=None, price=192.50):
        with (
            patch("app.routes.portfolio.get_cash_balance", return_value=cash),
            patch("app.routes.portfolio.get_position", return_value=position),
            patch("app.routes.portfolio.update_cash_balance"),
            patch("app.routes.portfolio.upsert_position"),
            patch("app.routes.portfolio.record_trade", return_value=_TRADE_RECORD),
            patch("app.routes.portfolio.get_positions", return_value=[]),
            patch("app.routes.portfolio.record_snapshot"),
        ):
            client = TestClient(_make_app(_make_cache(price)))
            return client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
            )

    def test_buy_success_returns_200(self):
        response = self._run_buy()
        assert response.status_code == 200

    def test_buy_success_response_shape(self):
        data = self._run_buy().json()
        assert data["success"] is True
        assert "trade" in data
        assert "new_cash_balance" in data
        assert "position" in data

    def test_buy_success_cash_deducted(self):
        """new_cash_balance = 10000 - (10 * 192.50) = 8075"""
        data = self._run_buy(cash=10000.0, price=192.50).json()
        assert data["new_cash_balance"] == pytest.approx(8075.0, rel=1e-4)

    def test_buy_insufficient_cash_returns_error(self):
        """Only $100 available, trade costs $1925."""
        data = self._run_buy(cash=100.0, price=192.50).json()
        assert data["success"] is False
        assert "Insufficient cash" in data["error"]

    def test_buy_price_unavailable_returns_error(self):
        with (
            patch("app.routes.portfolio.get_cash_balance", return_value=10000.0),
        ):
            client = TestClient(_make_app(_make_cache(None)))
            data = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
            ).json()
        assert data["success"] is False
        assert "Price unavailable" in data["error"]

    def test_buy_weighted_avg_cost_with_existing_position(self):
        """Existing 10 @ $190; buying 5 more @ $192.50 → avg = (1900 + 962.5) / 15 ≈ 190.833"""
        existing = {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 190.0}
        with (
            patch("app.routes.portfolio.get_cash_balance", return_value=10000.0),
            patch("app.routes.portfolio.get_position", return_value=existing),
            patch("app.routes.portfolio.update_cash_balance"),
            patch("app.routes.portfolio.upsert_position") as mock_upsert,
            patch("app.routes.portfolio.record_trade", return_value={**_TRADE_RECORD, "quantity": 5}),
            patch("app.routes.portfolio.get_positions", return_value=[]),
            patch("app.routes.portfolio.record_snapshot"),
        ):
            client = TestClient(_make_app(_make_cache(192.50)))
            client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
            )
        _qty, _avg = mock_upsert.call_args[0][2], mock_upsert.call_args[0][3]
        assert _qty == pytest.approx(15.0)
        expected_avg = (10 * 190.0 + 5 * 192.50) / 15
        assert _avg == pytest.approx(expected_avg, rel=1e-6)

    def test_buy_trade_details_in_response(self):
        data = self._run_buy().json()
        trade = data["trade"]
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 10
        assert trade["price"] == 192.50


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade  — sell
# ---------------------------------------------------------------------------

_SELL_TRADE_RECORD = {**_TRADE_RECORD, "side": "sell"}

_POSITION_10 = {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 190.0}


class TestSellTrade:
    def _run_sell(self, quantity=5, position=_POSITION_10, cash=8075.0, price=192.50):
        with (
            patch("app.routes.portfolio.get_cash_balance", return_value=cash),
            patch("app.routes.portfolio.get_position", return_value=position),
            patch("app.routes.portfolio.update_cash_balance"),
            patch("app.routes.portfolio.upsert_position"),
            patch("app.routes.portfolio.delete_position"),
            patch("app.routes.portfolio.record_trade", return_value=_SELL_TRADE_RECORD),
            patch("app.routes.portfolio.get_positions", return_value=[]),
            patch("app.routes.portfolio.record_snapshot"),
        ):
            client = TestClient(_make_app(_make_cache(price)))
            return client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": quantity, "side": "sell"},
            )

    def test_sell_success_returns_200(self):
        assert self._run_sell().status_code == 200

    def test_sell_success_response_shape(self):
        data = self._run_sell().json()
        assert data["success"] is True
        assert "trade" in data
        assert "new_cash_balance" in data

    def test_sell_cash_increases(self):
        """Selling 5 @ 192.50 adds $962.50 → new cash = 8075 + 962.5"""
        data = self._run_sell(quantity=5, cash=8075.0, price=192.50).json()
        assert data["new_cash_balance"] == pytest.approx(8075.0 + 962.5, rel=1e-4)

    def test_sell_insufficient_shares_returns_error(self):
        """Trying to sell 20 shares when only 10 are held."""
        data = self._run_sell(quantity=20).json()
        assert data["success"] is False
        assert "Insufficient shares" in data["error"]

    def test_sell_no_position_returns_error(self):
        """Trying to sell a ticker not held."""
        data = self._run_sell(quantity=1, position=None).json()
        assert data["success"] is False
        assert "Insufficient shares" in data["error"]

    def test_sell_all_shares_deletes_position(self):
        """Selling the entire position should call delete_position."""
        with (
            patch("app.routes.portfolio.get_cash_balance", return_value=8075.0),
            patch("app.routes.portfolio.get_position", return_value=_POSITION_10),
            patch("app.routes.portfolio.update_cash_balance"),
            patch("app.routes.portfolio.upsert_position"),
            patch("app.routes.portfolio.delete_position") as mock_delete,
            patch("app.routes.portfolio.record_trade", return_value=_SELL_TRADE_RECORD),
            patch("app.routes.portfolio.get_positions", return_value=[]),
            patch("app.routes.portfolio.record_snapshot"),
        ):
            client = TestClient(_make_app(_make_cache(192.50)))
            data = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
            ).json()
        assert data["success"] is True
        mock_delete.assert_called_once()
        assert data["position"]["quantity"] == 0.0

    def test_sell_partial_keeps_position(self):
        """Selling 5 of 10 should upsert remaining 5 shares."""
        with (
            patch("app.routes.portfolio.get_cash_balance", return_value=8075.0),
            patch("app.routes.portfolio.get_position", return_value=_POSITION_10),
            patch("app.routes.portfolio.update_cash_balance"),
            patch("app.routes.portfolio.upsert_position") as mock_upsert,
            patch("app.routes.portfolio.delete_position"),
            patch("app.routes.portfolio.record_trade", return_value=_SELL_TRADE_RECORD),
            patch("app.routes.portfolio.get_positions", return_value=[]),
            patch("app.routes.portfolio.record_snapshot"),
        ):
            client = TestClient(_make_app(_make_cache(192.50)))
            data = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
            ).json()
        assert data["success"] is True
        assert data["position"]["quantity"] == 5.0
        mock_upsert.assert_called_once()
        assert mock_upsert.call_args[0][2] == pytest.approx(5.0)

    def test_sell_price_unavailable_returns_error(self):
        with (
            patch("app.routes.portfolio.get_cash_balance", return_value=8075.0),
        ):
            client = TestClient(_make_app(_make_cache(None)))
            data = client.post(
                "/api/portfolio/trade",
                json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
            ).json()
        assert data["success"] is False
        assert "Price unavailable" in data["error"]
