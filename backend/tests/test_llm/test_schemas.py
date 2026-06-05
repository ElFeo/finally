"""Tests for LLM Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.llm.schemas import ChatResponse, TradeAction, WatchlistAction


# ---------------------------------------------------------------------------
# TradeAction
# ---------------------------------------------------------------------------

class TestTradeAction:
    def test_basic_buy(self):
        t = TradeAction(ticker="aapl", side="buy", quantity=10)
        assert t.ticker == "AAPL"
        assert t.side == "buy"
        assert t.quantity == 10.0

    def test_basic_sell(self):
        t = TradeAction(ticker="TSLA", side="sell", quantity=3.5)
        assert t.ticker == "TSLA"
        assert t.side == "sell"
        assert t.quantity == 3.5

    def test_ticker_normalized_to_uppercase(self):
        t = TradeAction(ticker="googl", side="buy", quantity=1)
        assert t.ticker == "GOOGL"

    def test_ticker_strips_whitespace(self):
        t = TradeAction(ticker="  MSFT  ", side="buy", quantity=1)
        assert t.ticker == "MSFT"

    def test_side_normalized_to_lowercase(self):
        t = TradeAction(ticker="AAPL", side="BUY", quantity=5)
        assert t.side == "buy"

    def test_invalid_side_raises(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="hold", quantity=5)

    def test_zero_quantity_raises(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=0)

    def test_negative_quantity_raises(self):
        with pytest.raises(ValidationError):
            TradeAction(ticker="AAPL", side="buy", quantity=-1)

    def test_fractional_quantity_allowed(self):
        t = TradeAction(ticker="AAPL", side="buy", quantity=0.5)
        assert t.quantity == 0.5

    def test_serialization_roundtrip(self):
        t = TradeAction(ticker="NVDA", side="sell", quantity=2)
        data = t.model_dump()
        t2 = TradeAction(**data)
        assert t == t2


# ---------------------------------------------------------------------------
# WatchlistAction
# ---------------------------------------------------------------------------

class TestWatchlistAction:
    def test_add_action(self):
        w = WatchlistAction(ticker="PYPL", action="add")
        assert w.ticker == "PYPL"
        assert w.action == "add"

    def test_remove_action(self):
        w = WatchlistAction(ticker="META", action="remove")
        assert w.action == "remove"

    def test_ticker_normalized(self):
        w = WatchlistAction(ticker="nflx", action="add")
        assert w.ticker == "NFLX"

    def test_action_normalized_to_lowercase(self):
        w = WatchlistAction(ticker="AAPL", action="ADD")
        assert w.action == "add"

    def test_invalid_action_raises(self):
        with pytest.raises(ValidationError):
            WatchlistAction(ticker="AAPL", action="toggle")

    def test_serialization_roundtrip(self):
        w = WatchlistAction(ticker="JPM", action="remove")
        data = w.model_dump()
        w2 = WatchlistAction(**data)
        assert w == w2


# ---------------------------------------------------------------------------
# ChatResponse
# ---------------------------------------------------------------------------

class TestChatResponse:
    def test_message_only(self):
        r = ChatResponse(message="Hello!")
        assert r.message == "Hello!"
        assert r.trades == []
        assert r.watchlist_changes == []

    def test_with_trades(self):
        r = ChatResponse(
            message="Buying AAPL.",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        )
        assert len(r.trades) == 1
        assert r.trades[0].ticker == "AAPL"

    def test_with_watchlist_changes(self):
        r = ChatResponse(
            message="Added PYPL.",
            watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
        )
        assert len(r.watchlist_changes) == 1

    def test_full_response(self):
        r = ChatResponse(
            message="Done!",
            trades=[
                {"ticker": "AAPL", "side": "buy", "quantity": 10},
                {"ticker": "TSLA", "side": "sell", "quantity": 2},
            ],
            watchlist_changes=[
                {"ticker": "PYPL", "action": "add"},
                {"ticker": "META", "action": "remove"},
            ],
        )
        assert len(r.trades) == 2
        assert len(r.watchlist_changes) == 2

    def test_json_roundtrip(self):
        r = ChatResponse(
            message="Test",
            trades=[{"ticker": "AAPL", "side": "buy", "quantity": 1}],
            watchlist_changes=[{"ticker": "PYPL", "action": "add"}],
        )
        json_str = r.model_dump_json()
        r2 = ChatResponse.model_validate_json(json_str)
        assert r2.message == r.message
        assert r2.trades[0].ticker == "AAPL"
        assert r2.watchlist_changes[0].ticker == "PYPL"

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            ChatResponse()

    def test_empty_trades_list(self):
        r = ChatResponse(message="Nothing to trade.", trades=[])
        assert r.trades == []

    def test_empty_watchlist_changes(self):
        r = ChatResponse(message="No changes.", watchlist_changes=[])
        assert r.watchlist_changes == []
