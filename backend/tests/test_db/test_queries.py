"""Tests for all database query functions."""

import os

import pytest

from app.db import (
    add_chat_message,
    add_to_watchlist,
    delete_position,
    get_cash_balance,
    get_chat_messages,
    get_position,
    get_positions,
    get_snapshots,
    get_watchlist,
    get_watchlist_tickers,
    init_db,
    record_snapshot,
    record_trade,
    remove_from_watchlist,
    update_cash_balance,
    upsert_position,
)


@pytest.fixture(autouse=True)
def db_path(tmp_path):
    """Use a fresh temporary database for every test."""
    path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = path
    init_db()
    yield path


# ---------------------------------------------------------------------------
# Cash balance
# ---------------------------------------------------------------------------

class TestCashBalance:
    def test_get_default_balance(self):
        balance = get_cash_balance("default")
        assert balance == 10000.0

    def test_get_balance_returns_float(self):
        assert isinstance(get_cash_balance("default"), float)

    def test_update_balance(self):
        update_cash_balance("default", 5000.0)
        assert get_cash_balance("default") == 5000.0

    def test_update_balance_to_zero(self):
        update_cash_balance("default", 0.0)
        assert get_cash_balance("default") == 0.0

    def test_update_balance_large_value(self):
        update_cash_balance("default", 999999.99)
        assert get_cash_balance("default") == pytest.approx(999999.99)

    def test_get_balance_missing_user_raises(self):
        with pytest.raises(ValueError):
            get_cash_balance("nonexistent_user")


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

class TestWatchlist:
    def test_get_watchlist_returns_list(self):
        result = get_watchlist("default")
        assert isinstance(result, list)

    def test_get_watchlist_has_ten_entries(self):
        result = get_watchlist("default")
        assert len(result) == 10

    def test_get_watchlist_entry_shape(self):
        result = get_watchlist("default")
        entry = result[0]
        assert "id" in entry
        assert "ticker" in entry
        assert "added_at" in entry

    def test_get_watchlist_tickers_returns_list_of_strings(self):
        tickers = get_watchlist_tickers("default")
        assert isinstance(tickers, list)
        assert all(isinstance(t, str) for t in tickers)

    def test_get_watchlist_tickers_count(self):
        assert len(get_watchlist_tickers("default")) == 10

    def test_get_watchlist_tickers_contains_expected(self):
        tickers = get_watchlist_tickers("default")
        assert "AAPL" in tickers
        assert "NVDA" in tickers

    def test_add_to_watchlist_returns_dict(self):
        result = add_to_watchlist("default", "PLTR")
        assert "id" in result
        assert result["ticker"] == "PLTR"
        assert "added_at" in result

    def test_add_to_watchlist_normalizes_ticker_case(self):
        result = add_to_watchlist("default", "pltr")
        assert result["ticker"] == "PLTR"

    def test_add_to_watchlist_persists(self):
        add_to_watchlist("default", "PLTR")
        tickers = get_watchlist_tickers("default")
        assert "PLTR" in tickers

    def test_add_to_watchlist_duplicate_raises_value_error(self):
        with pytest.raises(ValueError):
            add_to_watchlist("default", "AAPL")

    def test_add_to_watchlist_duplicate_lowercase_raises(self):
        with pytest.raises(ValueError):
            add_to_watchlist("default", "aapl")

    def test_remove_from_watchlist_returns_true(self):
        result = remove_from_watchlist("default", "AAPL")
        assert result is True

    def test_remove_from_watchlist_actually_removes(self):
        remove_from_watchlist("default", "AAPL")
        tickers = get_watchlist_tickers("default")
        assert "AAPL" not in tickers

    def test_remove_from_watchlist_nonexistent_returns_false(self):
        result = remove_from_watchlist("default", "ZZZZ")
        assert result is False

    def test_remove_from_watchlist_case_insensitive(self):
        result = remove_from_watchlist("default", "aapl")
        assert result is True

    def test_watchlist_empty_for_unknown_user(self):
        result = get_watchlist("unknown_user")
        assert result == []

    def test_watchlist_tickers_empty_for_unknown_user(self):
        result = get_watchlist_tickers("unknown_user")
        assert result == []


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

class TestPositions:
    def test_get_positions_empty_initially(self):
        result = get_positions("default")
        assert result == []

    def test_upsert_position_insert(self):
        upsert_position("default", "AAPL", 10.0, 190.0)
        positions = get_positions("default")
        assert len(positions) == 1
        pos = positions[0]
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 10.0
        assert pos["avg_cost"] == 190.0

    def test_upsert_position_update(self):
        upsert_position("default", "AAPL", 10.0, 190.0)
        upsert_position("default", "AAPL", 20.0, 195.0)
        positions = get_positions("default")
        # Still only one position
        assert len(positions) == 1
        pos = positions[0]
        assert pos["quantity"] == 20.0
        assert pos["avg_cost"] == 195.0

    def test_upsert_position_normalizes_ticker(self):
        upsert_position("default", "aapl", 5.0, 180.0)
        pos = get_position("default", "AAPL")
        assert pos is not None
        assert pos["ticker"] == "AAPL"

    def test_get_position_returns_none_for_missing(self):
        result = get_position("default", "ZZZZ")
        assert result is None

    def test_get_position_returns_correct_data(self):
        upsert_position("default", "TSLA", 3.5, 250.0)
        pos = get_position("default", "TSLA")
        assert pos is not None
        assert pos["ticker"] == "TSLA"
        assert pos["quantity"] == pytest.approx(3.5)
        assert pos["avg_cost"] == pytest.approx(250.0)
        assert "updated_at" in pos

    def test_get_positions_returns_multiple(self):
        upsert_position("default", "AAPL", 10.0, 190.0)
        upsert_position("default", "MSFT", 5.0, 300.0)
        positions = get_positions("default")
        assert len(positions) == 2
        tickers = {p["ticker"] for p in positions}
        assert tickers == {"AAPL", "MSFT"}

    def test_get_positions_entry_shape(self):
        upsert_position("default", "AAPL", 10.0, 190.0)
        pos = get_positions("default")[0]
        assert "ticker" in pos
        assert "quantity" in pos
        assert "avg_cost" in pos
        assert "updated_at" in pos

    def test_delete_position(self):
        upsert_position("default", "AAPL", 10.0, 190.0)
        delete_position("default", "AAPL")
        assert get_position("default", "AAPL") is None

    def test_delete_position_nonexistent_no_error(self):
        # Should not raise
        delete_position("default", "ZZZZ")

    def test_delete_position_normalizes_ticker(self):
        upsert_position("default", "AAPL", 10.0, 190.0)
        delete_position("default", "aapl")
        assert get_position("default", "AAPL") is None

    def test_upsert_fractional_shares(self):
        upsert_position("default", "AAPL", 0.5, 190.0)
        pos = get_position("default", "AAPL")
        assert pos["quantity"] == pytest.approx(0.5)

    def test_positions_quantities_are_floats(self):
        upsert_position("default", "AAPL", 10, 190)
        pos = get_positions("default")[0]
        assert isinstance(pos["quantity"], float)
        assert isinstance(pos["avg_cost"], float)


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

class TestTrades:
    def test_record_trade_returns_dict(self):
        trade = record_trade("default", "AAPL", "buy", 10.0, 190.0)
        assert isinstance(trade, dict)

    def test_record_trade_shape(self):
        trade = record_trade("default", "AAPL", "buy", 10.0, 190.0)
        assert "id" in trade
        assert "user_id" in trade
        assert "ticker" in trade
        assert "side" in trade
        assert "quantity" in trade
        assert "price" in trade
        assert "executed_at" in trade

    def test_record_trade_correct_values(self):
        trade = record_trade("default", "AAPL", "buy", 10.0, 190.0)
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 10.0
        assert trade["price"] == 190.0
        assert trade["user_id"] == "default"

    def test_record_trade_normalizes_ticker(self):
        trade = record_trade("default", "aapl", "buy", 10.0, 190.0)
        assert trade["ticker"] == "AAPL"

    def test_record_trade_buy_and_sell(self):
        record_trade("default", "AAPL", "buy", 10.0, 190.0)
        record_trade("default", "AAPL", "sell", 5.0, 200.0)
        # Verify both are stored by checking the DB directly
        from app.db.database import get_connection
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE user_id='default' AND ticker='AAPL'"
            ).fetchone()[0]
        assert count == 2

    def test_record_trade_appends_multiple(self):
        for i in range(5):
            record_trade("default", "TSLA", "buy", float(i + 1), 250.0)
        from app.db.database import get_connection
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE ticker='TSLA'"
            ).fetchone()[0]
        assert count == 5

    def test_record_trade_fractional_quantity(self):
        trade = record_trade("default", "AAPL", "buy", 0.25, 190.0)
        assert trade["quantity"] == pytest.approx(0.25)

    def test_record_trade_id_is_unique(self):
        t1 = record_trade("default", "AAPL", "buy", 1.0, 190.0)
        t2 = record_trade("default", "AAPL", "buy", 2.0, 191.0)
        assert t1["id"] != t2["id"]


# ---------------------------------------------------------------------------
# Portfolio Snapshots
# ---------------------------------------------------------------------------

class TestPortfolioSnapshots:
    def test_get_snapshots_empty_initially(self):
        result = get_snapshots("default")
        assert result == []

    def test_record_snapshot_stores_value(self):
        record_snapshot("default", 10500.0)
        snapshots = get_snapshots("default")
        assert len(snapshots) == 1
        assert snapshots[0]["total_value"] == pytest.approx(10500.0)

    def test_get_snapshots_shape(self):
        record_snapshot("default", 10000.0)
        snap = get_snapshots("default")[0]
        assert "total_value" in snap
        assert "recorded_at" in snap

    def test_get_snapshots_chronological_order(self):
        record_snapshot("default", 9000.0)
        record_snapshot("default", 10000.0)
        record_snapshot("default", 11000.0)
        snapshots = get_snapshots("default")
        values = [s["total_value"] for s in snapshots]
        assert values == sorted(values) or values == [9000.0, 10000.0, 11000.0]
        # Verify it is ascending (chronological)
        assert snapshots[0]["recorded_at"] <= snapshots[-1]["recorded_at"]

    def test_get_snapshots_respects_limit(self):
        for i in range(20):
            record_snapshot("default", float(10000 + i))
        snapshots = get_snapshots("default", limit=5)
        assert len(snapshots) == 5

    def test_get_snapshots_returns_most_recent_within_limit(self):
        for i in range(10):
            record_snapshot("default", float(i))
        # With limit=3, we should get the last 3 in ascending order
        snapshots = get_snapshots("default", limit=3)
        assert len(snapshots) == 3
        # The most recent values are 7, 8, 9
        values = {s["total_value"] for s in snapshots}
        assert values == {7.0, 8.0, 9.0}

    def test_get_snapshots_total_value_is_float(self):
        record_snapshot("default", 10000)
        snap = get_snapshots("default")[0]
        assert isinstance(snap["total_value"], float)


# ---------------------------------------------------------------------------
# Chat Messages
# ---------------------------------------------------------------------------

class TestChatMessages:
    def test_get_chat_messages_empty_initially(self):
        result = get_chat_messages("default")
        assert result == []

    def test_add_chat_message_returns_dict(self):
        result = add_chat_message("default", "user", "Hello!")
        assert isinstance(result, dict)

    def test_add_chat_message_shape(self):
        result = add_chat_message("default", "user", "Hello!")
        assert "id" in result
        assert "role" in result
        assert "content" in result
        assert "actions" in result
        assert "created_at" in result

    def test_add_chat_message_user_role(self):
        result = add_chat_message("default", "user", "Hello!")
        assert result["role"] == "user"
        assert result["content"] == "Hello!"
        assert result["actions"] is None

    def test_add_chat_message_assistant_with_actions(self):
        actions = {"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}]}
        result = add_chat_message("default", "assistant", "Bought 5 AAPL.", actions=actions)
        assert result["role"] == "assistant"
        assert result["actions"] == actions

    def test_get_chat_messages_returns_all(self):
        add_chat_message("default", "user", "Message 1")
        add_chat_message("default", "assistant", "Response 1")
        messages = get_chat_messages("default")
        assert len(messages) == 2

    def test_get_chat_messages_chronological_order(self):
        add_chat_message("default", "user", "First")
        add_chat_message("default", "assistant", "Second")
        add_chat_message("default", "user", "Third")
        messages = get_chat_messages("default")
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"

    def test_get_chat_messages_respects_limit(self):
        for i in range(20):
            add_chat_message("default", "user", f"Message {i}")
        messages = get_chat_messages("default", limit=5)
        assert len(messages) == 5

    def test_get_chat_messages_returns_most_recent_within_limit(self):
        for i in range(10):
            add_chat_message("default", "user", f"Message {i}")
        messages = get_chat_messages("default", limit=3)
        # Should be the last 3 in chronological order
        contents = [m["content"] for m in messages]
        assert contents == ["Message 7", "Message 8", "Message 9"]

    def test_get_chat_messages_actions_deserialized(self):
        actions = {"trades": [{"ticker": "TSLA", "side": "sell", "quantity": 2}]}
        add_chat_message("default", "assistant", "Sold 2 TSLA.", actions=actions)
        messages = get_chat_messages("default")
        assert messages[0]["actions"] == actions

    def test_get_chat_messages_null_actions(self):
        add_chat_message("default", "user", "No actions here")
        messages = get_chat_messages("default")
        assert messages[0]["actions"] is None

    def test_get_chat_messages_shape_each_entry(self):
        add_chat_message("default", "user", "Test")
        msg = get_chat_messages("default")[0]
        assert "id" in msg
        assert "role" in msg
        assert "content" in msg
        assert "actions" in msg
        assert "created_at" in msg

    def test_add_chat_message_persists(self):
        add_chat_message("default", "user", "Persistent message")
        messages = get_chat_messages("default")
        assert any(m["content"] == "Persistent message" for m in messages)

    def test_get_chat_messages_empty_for_unknown_user(self):
        add_chat_message("default", "user", "Default user message")
        messages = get_chat_messages("other_user")
        assert messages == []
