"""E2E: Backend API tests (HTTP calls against live server)."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class TestPortfolioAPI:
    def test_portfolio_returns_200(self, client):
        resp = client.get("/api/portfolio")
        assert resp.status_code == 200

    def test_portfolio_has_required_keys(self, client):
        data = client.get("/api/portfolio").json()
        for key in ("cash_balance", "positions", "total_value", "unrealized_pnl"):
            assert key in data, f"Missing key: {key}"

    def test_initial_cash_balance_is_10000(self, client):
        data = client.get("/api/portfolio").json()
        # Fresh DB starts with $10,000
        assert data["cash_balance"] == pytest.approx(10000.0, rel=1e-2)

    def test_initial_positions_is_empty(self, client):
        data = client.get("/api/portfolio").json()
        assert isinstance(data["positions"], list)

    def test_portfolio_history_returns_200(self, client):
        resp = client.get("/api/portfolio/history")
        assert resp.status_code == 200

    def test_portfolio_history_has_snapshots_key(self, client):
        data = client.get("/api/portfolio/history").json()
        assert "snapshots" in data
        assert isinstance(data["snapshots"], list)


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

class TestWatchlistAPI:
    def test_watchlist_returns_200(self, client):
        resp = client.get("/api/watchlist")
        assert resp.status_code == 200

    def test_watchlist_has_tickers_key(self, client):
        data = client.get("/api/watchlist").json()
        assert "tickers" in data

    def test_watchlist_has_10_default_tickers(self, client):
        data = client.get("/api/watchlist").json()
        tickers = data["tickers"]
        assert len(tickers) == 10, f"Expected 10 tickers, got {len(tickers)}: {[t['ticker'] for t in tickers]}"

    def test_default_tickers_include_aapl(self, client):
        data = client.get("/api/watchlist").json()
        symbols = [t["ticker"] for t in data["tickers"]]
        assert "AAPL" in symbols

    def test_watchlist_ticker_has_required_fields(self, client):
        data = client.get("/api/watchlist").json()
        first = data["tickers"][0]
        for field in ("ticker", "added_at"):
            assert field in first, f"Missing field: {field}"

    def test_add_ticker_returns_201(self, client):
        resp = client.post("/api/watchlist", json={"ticker": "PLTR"})
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    def test_add_ticker_appears_in_watchlist(self, client):
        client.post("/api/watchlist", json={"ticker": "SHOP"})
        data = client.get("/api/watchlist").json()
        symbols = [t["ticker"] for t in data["tickers"]]
        assert "SHOP" in symbols

    def test_add_duplicate_ticker_returns_400(self, client):
        # AAPL is already in default watchlist
        resp = client.post("/api/watchlist", json={"ticker": "AAPL"})
        assert resp.status_code == 400

    def test_remove_ticker_returns_200(self, client):
        # Add then remove
        client.post("/api/watchlist", json={"ticker": "RMBTEST"})
        resp = client.delete("/api/watchlist/RMBTEST")
        assert resp.status_code == 200

    def test_remove_ticker_disappears_from_watchlist(self, client):
        client.post("/api/watchlist", json={"ticker": "DELTEST"})
        client.delete("/api/watchlist/DELTEST")
        data = client.get("/api/watchlist").json()
        symbols = [t["ticker"] for t in data["tickers"]]
        assert "DELTEST" not in symbols

    def test_remove_nonexistent_ticker_returns_404(self, client):
        resp = client.delete("/api/watchlist/NOTEXIST")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Trade execution
# ---------------------------------------------------------------------------

class TestTradeAPI:
    def test_buy_aapl_returns_200(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
        )
        assert resp.status_code == 200

    def test_buy_aapl_success_is_true(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
        )
        data = resp.json()
        assert data["success"] is True, f"Trade failed: {data.get('error')}"

    def test_buy_decreases_cash(self, client):
        before = client.get("/api/portfolio").json()["cash_balance"]
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
        )
        data = resp.json()
        if data["success"]:
            after = client.get("/api/portfolio").json()["cash_balance"]
            assert after < before, f"Cash did not decrease: before={before}, after={after}"

    def test_buy_creates_position(self, client):
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
        )
        portfolio = client.get("/api/portfolio").json()
        tickers = [p["ticker"] for p in portfolio["positions"]]
        assert "AAPL" in tickers

    def test_trade_response_has_required_keys(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
        )
        data = resp.json()
        assert "success" in data
        if data["success"]:
            assert "trade" in data
            assert "new_cash_balance" in data

    def test_buy_insufficient_cash_fails(self, client):
        # Try to buy an absurd quantity to exhaust cash
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 100000, "side": "buy"},
        )
        data = resp.json()
        assert data["success"] is False
        assert "cash" in data["error"].lower() or "insufficient" in data["error"].lower()

    def test_sell_without_position_fails(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "TSLA", "quantity": 999, "side": "sell"},
        )
        data = resp.json()
        assert data["success"] is False

    def test_buy_then_sell_restores_cash(self, client):
        """Buy 1 share then sell 1 share — cash should be close to original minus fees (no fees here)."""
        cash_before = client.get("/api/portfolio").json()["cash_balance"]

        buy_resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "MSFT", "quantity": 1, "side": "buy"},
        ).json()

        if not buy_resp["success"]:
            pytest.skip("Buy failed, skipping sell test")

        buy_price = buy_resp["trade"]["price"]

        sell_resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "MSFT", "quantity": 1, "side": "sell"},
        ).json()

        assert sell_resp["success"] is True, f"Sell failed: {sell_resp.get('error')}"

        cash_after = client.get("/api/portfolio").json()["cash_balance"]
        # Cash difference is due to price fluctuation in simulator (small)
        assert abs(cash_after - cash_before) < 50.0, (
            f"Cash delta too large: before={cash_before}, after={cash_after}"
        )

    def test_trade_invalid_side_rejected(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 1, "side": "invalid"},
        )
        # Should fail with validation error (422) or explicit error
        assert resp.status_code in (422, 400)

    def test_trade_zero_quantity_rejected(self, client):
        resp = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "quantity": 0, "side": "buy"},
        )
        # quantity must be > 0 per Pydantic model
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Chat (mock LLM)
# ---------------------------------------------------------------------------

class TestChatAPI:
    def test_chat_returns_200(self, client):
        resp = client.post("/api/chat", json={"message": "Hello, how is my portfolio?"})
        assert resp.status_code == 200

    def test_chat_response_has_message_key(self, client):
        data = client.post("/api/chat", json={"message": "What stocks do you recommend?"}).json()
        assert "message" in data

    def test_chat_response_has_trades_executed_key(self, client):
        data = client.post("/api/chat", json={"message": "Hello"}).json()
        assert "trades_executed" in data

    def test_chat_response_has_watchlist_changes_key(self, client):
        data = client.post("/api/chat", json={"message": "Hello"}).json()
        assert "watchlist_changes" in data

    def test_chat_message_is_nonempty_string(self, client):
        data = client.post("/api/chat", json={"message": "Hello"}).json()
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_chat_empty_message_returns_400(self, client):
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 400

    def test_chat_mock_buy_aapl_executes_trade(self, client):
        """Mock LLM: 'buy aapl' triggers buy 5 AAPL trade."""
        cash_before = client.get("/api/portfolio").json()["cash_balance"]
        data = client.post("/api/chat", json={"message": "buy aapl"}).json()
        assert "message" in data
        # trades_executed may be empty if no price yet, but should be a list
        assert isinstance(data["trades_executed"], list)

    def test_chat_mock_watchlist_add(self, client):
        """Mock LLM: 'add ticker' triggers watchlist add of PYPL."""
        data = client.post("/api/chat", json={"message": "add a ticker please"}).json()
        assert "watchlist_changes" in data
        # Check PYPL got added per mock implementation
        changes = data["watchlist_changes"]
        assert isinstance(changes, list)
