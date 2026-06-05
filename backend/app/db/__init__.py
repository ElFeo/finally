"""FinAlly database layer — public API."""

from .database import get_db_path, init_db
from .queries import (
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
    record_snapshot,
    record_trade,
    remove_from_watchlist,
    update_cash_balance,
    upsert_position,
)

__all__ = [
    # Initialization
    "init_db",
    "get_db_path",
    # User / Cash
    "get_cash_balance",
    "update_cash_balance",
    # Watchlist
    "get_watchlist",
    "get_watchlist_tickers",
    "add_to_watchlist",
    "remove_from_watchlist",
    # Positions
    "get_positions",
    "get_position",
    "upsert_position",
    "delete_position",
    # Trades
    "record_trade",
    # Portfolio snapshots
    "record_snapshot",
    "get_snapshots",
    # Chat messages
    "get_chat_messages",
    "add_chat_message",
]
