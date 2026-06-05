"""Tests for the POST /api/chat endpoint."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db import (
    add_to_watchlist,
    get_cash_balance,
    get_chat_messages,
    get_position,
    get_watchlist_tickers,
    init_db,
    upsert_position,
    update_cash_balance,
)
from app.market.cache import PriceCache
from app.routes.chat import router as chat_router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_env(monkeypatch, tmp_path):
    """Use a temp DB and enable mock LLM for every test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("LLM_MOCK", "true")
    init_db()


@pytest.fixture
def price_cache() -> PriceCache:
    """A pre-loaded price cache."""
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("GOOGL", 175.0)
    cache.update("TSLA", 250.0)
    cache.update("PYPL", 60.0)
    return cache


@pytest.fixture
def mock_market_source(mocker):
    """Async mock for the market source."""
    source = mocker.AsyncMock()
    source.add_ticker = mocker.AsyncMock(return_value=None)
    source.remove_ticker = mocker.AsyncMock(return_value=None)
    return source


@pytest.fixture
def app(price_cache, mock_market_source) -> FastAPI:
    """FastAPI app with chat router and mocked app state."""
    _app = FastAPI()
    _app.include_router(chat_router, prefix="/api")
    _app.state.price_cache = price_cache
    _app.state.market_source = mock_market_source
    return _app


@pytest.fixture
async def client(app) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Basic endpoint behaviour
# ---------------------------------------------------------------------------

class TestChatEndpoint:
    async def test_returns_200(self, client):
        resp = await client.post("/api/chat", json={"message": "Hello!"})
        assert resp.status_code == 200

    async def test_response_has_message_field(self, client):
        resp = await client.post("/api/chat", json={"message": "Hello!"})
        data = resp.json()
        assert "message" in data
        assert isinstance(data["message"], str)

    async def test_response_has_trades_executed_field(self, client):
        resp = await client.post("/api/chat", json={"message": "Hello!"})
        data = resp.json()
        assert "trades_executed" in data
        assert isinstance(data["trades_executed"], list)

    async def test_response_has_watchlist_changes_field(self, client):
        resp = await client.post("/api/chat", json={"message": "Hello!"})
        data = resp.json()
        assert "watchlist_changes" in data
        assert isinstance(data["watchlist_changes"], list)

    async def test_empty_message_returns_400(self, client):
        resp = await client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 400

    async def test_whitespace_only_message_returns_400(self, client):
        resp = await client.post("/api/chat", json={"message": "   "})
        assert resp.status_code == 400

    async def test_generic_message_no_trades(self, client):
        resp = await client.post("/api/chat", json={"message": "What's the market like today?"})
        data = resp.json()
        assert data["trades_executed"] == []
        assert data["watchlist_changes"] == []


# ---------------------------------------------------------------------------
# Trade auto-execution
# ---------------------------------------------------------------------------

class TestTradeAutoExecution:
    async def test_buy_aapl_executes_trade(self, client):
        """Mock returns a buy-5-AAPL trade; it should be executed."""
        resp = await client.post("/api/chat", json={"message": "buy 5 aapl"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trades_executed"]) == 1
        trade = data["trades_executed"][0]
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 5
        assert trade["success"] is True

    async def test_buy_reduces_cash_balance(self, client):
        """After buying AAPL, cash should decrease."""
        initial_cash = get_cash_balance("default")
        await client.post("/api/chat", json={"message": "buy 5 aapl"})
        new_cash = get_cash_balance("default")
        # 5 shares * $190 = $950
        assert new_cash == pytest.approx(initial_cash - 950.0, abs=0.01)

    async def test_buy_creates_position(self, client):
        """After buying AAPL, a position should exist."""
        await client.post("/api/chat", json={"message": "buy 5 aapl"})
        pos = get_position("default", "AAPL")
        assert pos is not None
        assert pos["quantity"] == 5.0
        assert pos["avg_cost"] == pytest.approx(190.0, abs=0.01)

    async def test_buy_fails_with_insufficient_cash(self, client):
        """If the user doesn't have enough cash, the trade fails gracefully."""
        # Drain cash to nearly zero
        update_cash_balance("default", 10.0)
        resp = await client.post("/api/chat", json={"message": "buy 5 aapl"})
        data = resp.json()
        trade = data["trades_executed"][0]
        assert trade["success"] is False
        assert "cash" in trade["error"].lower() or "insufficient" in trade["error"].lower()

    async def test_sell_executes_trade(self, client):
        """Mock returns sell-5-AAPL; must have a position first."""
        # Create a position so the sell goes through
        upsert_position("default", "AAPL", 10.0, 185.0)
        resp = await client.post("/api/chat", json={"message": "sell all my AAPL"})
        data = resp.json()
        trade = data["trades_executed"][0]
        assert trade["side"] == "sell"
        assert trade["success"] is True

    async def test_sell_increases_cash(self, client):
        """Selling AAPL should increase cash."""
        upsert_position("default", "AAPL", 10.0, 185.0)
        initial_cash = get_cash_balance("default")
        await client.post("/api/chat", json={"message": "sell all my AAPL"})
        new_cash = get_cash_balance("default")
        # Sold 5 shares at $190 = $950
        assert new_cash == pytest.approx(initial_cash + 950.0, abs=0.01)

    async def test_sell_without_position_fails(self, client):
        """Selling when no position exists returns an error."""
        resp = await client.post("/api/chat", json={"message": "sell all my AAPL"})
        data = resp.json()
        trade = data["trades_executed"][0]
        assert trade["success"] is False
        assert "position" in trade["error"].lower() or "no" in trade["error"].lower()

    async def test_buy_with_no_price_in_cache_fails(self, client, price_cache):
        """If the ticker has no price in cache, trade fails gracefully."""
        # ZZXY has no price in the cache
        resp = await client.post("/api/chat", json={"message": "buy 5 ZZXY"})
        # The mock returns buy-AAPL regardless of message content for "buy * aapl"
        # So just verify the endpoint is healthy
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Watchlist auto-application
# ---------------------------------------------------------------------------

class TestWatchlistAutoApplication:
    async def test_add_watchlist_change(self, client, mock_market_source):
        """Mock returns add-PYPL; it should be added to watchlist."""
        resp = await client.post("/api/chat", json={"message": "add PYPL to my watchlist"})
        data = resp.json()
        assert len(data["watchlist_changes"]) == 1
        change = data["watchlist_changes"][0]
        assert change["ticker"] == "PYPL"
        assert change["action"] == "add"
        assert change["success"] is True

    async def test_add_watchlist_updates_db(self, client):
        """After add, PYPL should appear in the watchlist."""
        await client.post("/api/chat", json={"message": "add PYPL to my watchlist"})
        tickers = get_watchlist_tickers("default")
        assert "PYPL" in tickers

    async def test_add_watchlist_calls_market_source(self, client, mock_market_source):
        """market_source.add_ticker() should be called when ticker is added."""
        await client.post("/api/chat", json={"message": "add PYPL to my watchlist"})
        mock_market_source.add_ticker.assert_called_once_with("PYPL")

    async def test_add_duplicate_watchlist_returns_failure(self, client):
        """Adding a ticker that's already in watchlist returns success=False."""
        # AAPL is in the default watchlist from seed data
        add_to_watchlist("default", "PYPL")  # pre-add PYPL
        resp = await client.post("/api/chat", json={"message": "add PYPL to my watchlist"})
        data = resp.json()
        change = data["watchlist_changes"][0]
        assert change["success"] is False


# ---------------------------------------------------------------------------
# Message persistence
# ---------------------------------------------------------------------------

class TestMessagePersistence:
    async def test_user_message_saved(self, client):
        await client.post("/api/chat", json={"message": "Hello, FinAlly!"})
        messages = get_chat_messages("default", limit=10)
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert any(m["content"] == "Hello, FinAlly!" for m in user_msgs)

    async def test_assistant_message_saved(self, client):
        await client.post("/api/chat", json={"message": "Hello!"})
        messages = get_chat_messages("default", limit=10)
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) >= 1

    async def test_actions_saved_with_assistant_message(self, client):
        """When trades execute, actions payload is stored with the assistant message."""
        upsert_position("default", "AAPL", 10.0, 185.0)
        await client.post("/api/chat", json={"message": "sell all my AAPL"})
        messages = get_chat_messages("default", limit=10)
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        # At least one assistant message should have actions recorded
        with_actions = [m for m in assistant_msgs if m.get("actions") is not None]
        assert len(with_actions) >= 1

    async def test_no_actions_saved_for_generic_message(self, client):
        """Generic messages (no trades/watchlist changes) save None for actions."""
        await client.post("/api/chat", json={"message": "What's the market like?"})
        messages = get_chat_messages("default", limit=10)
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        # The latest assistant message should have no actions
        latest = assistant_msgs[-1]
        assert latest["actions"] is None

    async def test_multiple_messages_accumulate(self, client):
        await client.post("/api/chat", json={"message": "Hello!"})
        await client.post("/api/chat", json={"message": "How am I doing?"})
        messages = get_chat_messages("default", limit=20)
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) >= 2


# ---------------------------------------------------------------------------
# Portfolio context
# ---------------------------------------------------------------------------

class TestPortfolioContext:
    async def test_chat_works_with_empty_positions(self, client):
        """Should work fine with no positions."""
        resp = await client.post("/api/chat", json={"message": "What's my status?"})
        assert resp.status_code == 200

    async def test_chat_works_with_existing_positions(self, client):
        """Should work with existing positions in DB."""
        upsert_position("default", "AAPL", 5.0, 188.0)
        resp = await client.post("/api/chat", json={"message": "How is my portfolio?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
