"""Database query functions for FinAlly."""

import json
import uuid

from .database import get_connection, now_iso


# ---------------------------------------------------------------------------
# User / Cash
# ---------------------------------------------------------------------------

def get_cash_balance(user_id: str = "default") -> float:
    """Return the current cash balance for the given user."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"User '{user_id}' not found")
        return float(row["cash_balance"])


def update_cash_balance(user_id: str, new_balance: float) -> None:
    """Set the cash balance for the given user."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (new_balance, user_id),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def get_watchlist(user_id: str = "default") -> list[dict]:
    """Return all watchlist entries for the given user."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at ASC",
            (user_id,),
        ).fetchall()
        return [{"id": r["id"], "ticker": r["ticker"], "added_at": r["added_at"]} for r in rows]


def get_watchlist_tickers(user_id: str = "default") -> list[str]:
    """Return just the ticker symbols in the watchlist for the given user."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at ASC",
            (user_id,),
        ).fetchall()
        return [r["ticker"] for r in rows]


def add_to_watchlist(user_id: str, ticker: str) -> dict:
    """Add a ticker to the watchlist. Raises ValueError if already present."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        # Check for duplicate
        existing = conn.execute(
            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        if existing is not None:
            raise ValueError(f"Ticker '{ticker}' is already in the watchlist for user '{user_id}'")

        row_id = str(uuid.uuid4())
        added_at = now_iso()
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (row_id, user_id, ticker, added_at),
        )
        conn.commit()
        return {"id": row_id, "ticker": ticker, "added_at": added_at}


def remove_from_watchlist(user_id: str, ticker: str) -> bool:
    """Remove a ticker from the watchlist. Returns True if removed, False if not found."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        conn.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

def get_positions(user_id: str = "default") -> list[dict]:
    """Return all open positions for the given user."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? ORDER BY ticker ASC",
            (user_id,),
        ).fetchall()
        return [
            {
                "ticker": r["ticker"],
                "quantity": float(r["quantity"]),
                "avg_cost": float(r["avg_cost"]),
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]


def get_position(user_id: str, ticker: str) -> dict | None:
    """Return a single position or None if not found."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        if row is None:
            return None
        return {
            "ticker": row["ticker"],
            "quantity": float(row["quantity"]),
            "avg_cost": float(row["avg_cost"]),
            "updated_at": row["updated_at"],
        }


def upsert_position(user_id: str, ticker: str, quantity: float, avg_cost: float) -> None:
    """Insert or update a position for the given user and ticker."""
    ticker = ticker.upper().strip()
    updated_at = now_iso()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        if existing is not None:
            conn.execute(
                "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                (quantity, avg_cost, updated_at, user_id, ticker),
            )
        else:
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, ticker, quantity, avg_cost, updated_at),
            )
        conn.commit()


def delete_position(user_id: str, ticker: str) -> None:
    """Delete a position for the given user and ticker."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

def record_trade(
    user_id: str, ticker: str, side: str, quantity: float, price: float
) -> dict:
    """Append a trade record. Returns the trade dict with id and executed_at."""
    ticker = ticker.upper().strip()
    trade_id = str(uuid.uuid4())
    executed_at = now_iso()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, user_id, ticker, side, quantity, price, executed_at),
        )
        conn.commit()
    return {
        "id": trade_id,
        "user_id": user_id,
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": executed_at,
    }


# ---------------------------------------------------------------------------
# Portfolio Snapshots
# ---------------------------------------------------------------------------

def record_snapshot(user_id: str, total_value: float) -> None:
    """Append a portfolio value snapshot."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, total_value, now_iso()),
        )
        conn.commit()


def get_snapshots(user_id: str, limit: int = 500) -> list[dict]:
    """Return the most recent `limit` portfolio snapshots in chronological order."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT total_value, recorded_at
            FROM portfolio_snapshots
            WHERE user_id = ?
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        # Reverse so they are in chronological (ascending) order
        return [
            {"total_value": float(r["total_value"]), "recorded_at": r["recorded_at"]}
            for r in reversed(rows)
        ]


# ---------------------------------------------------------------------------
# Chat Messages
# ---------------------------------------------------------------------------

def get_chat_messages(user_id: str, limit: int = 50) -> list[dict]:
    """Return the most recent `limit` chat messages in chronological order."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, actions, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        result = []
        for r in reversed(rows):
            actions_raw = r["actions"]
            actions = json.loads(actions_raw) if actions_raw is not None else None
            result.append(
                {
                    "id": r["id"],
                    "role": r["role"],
                    "content": r["content"],
                    "actions": actions,
                    "created_at": r["created_at"],
                }
            )
        return result


def add_chat_message(
    user_id: str,
    role: str,
    content: str,
    actions: dict | None = None,
) -> dict:
    """Insert a chat message. Returns the new message dict."""
    msg_id = str(uuid.uuid4())
    created_at = now_iso()
    actions_json = json.dumps(actions) if actions is not None else None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, user_id, role, content, actions_json, created_at),
        )
        conn.commit()
    return {
        "id": msg_id,
        "role": role,
        "content": content,
        "actions": actions,
        "created_at": created_at,
    }
