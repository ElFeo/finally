"""Tests for database initialization and schema creation."""

import os
import sqlite3

import pytest

from app.db import get_db_path, init_db


@pytest.fixture(autouse=True)
def db_path(tmp_path):
    """Use a temporary database for every test in this module."""
    path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = path
    init_db()
    yield path
    # tmp_path is auto-cleaned by pytest


# ---------------------------------------------------------------------------
# get_db_path
# ---------------------------------------------------------------------------

class TestGetDbPath:
    def test_returns_env_var_when_set(self, tmp_path):
        custom = str(tmp_path / "custom.db")
        os.environ["DB_PATH"] = custom
        assert get_db_path() == custom

    def test_returns_absolute_path(self, tmp_path):
        os.environ["DB_PATH"] = str(tmp_path / "test.db")
        assert os.path.isabs(get_db_path())


# ---------------------------------------------------------------------------
# init_db — schema creation
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_creates_users_profile_table(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_profile'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_watchlist_table(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_positions_table(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='positions'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_trades_table(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_portfolio_snapshots_table(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_snapshots'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_chat_messages_table(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_seeds_default_user(self, db_path):
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT id, cash_balance FROM users_profile WHERE id='default'").fetchone()
        assert row is not None
        assert row[1] == 10000.0
        conn.close()

    def test_seeds_ten_watchlist_tickers(self, db_path):
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM watchlist WHERE user_id='default'").fetchone()[0]
        assert count == 10
        conn.close()

    def test_seeds_expected_tickers(self, db_path):
        expected = {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"}
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT ticker FROM watchlist WHERE user_id='default'").fetchall()
        actual = {r[0] for r in rows}
        assert actual == expected
        conn.close()

    def test_idempotent_on_second_call(self, db_path):
        """Calling init_db() again should not duplicate seed data."""
        init_db()
        conn = sqlite3.connect(db_path)
        user_count = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        watchlist_count = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        assert user_count == 1
        assert watchlist_count == 10
        conn.close()

    def test_wal_mode_enabled(self, db_path):
        """WAL journal mode should be enabled after init."""
        conn = sqlite3.connect(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"
