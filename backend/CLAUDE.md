# Backend — Developer Guide

## Project Setup

```bash
cd backend
uv sync --dev   # Install all dependencies including test/lint tools
```

## Market Data API

The market data subsystem lives in `app/market/`. Use these imports:

```python
from app.market import PriceCache, PriceUpdate, MarketDataSource, create_market_data_source
```

### Core Types

- **`PriceUpdate`** — Immutable dataclass: `ticker`, `price`, `previous_price`, `timestamp`, plus properties `change`, `change_percent`, `direction` ("up"/"down"/"flat"), and `to_dict()` for JSON serialization.

- **`PriceCache`** — Thread-safe in-memory store. Key methods:
  - `update(ticker, price, timestamp=None) -> PriceUpdate`
  - `get(ticker) -> PriceUpdate | None`
  - `get_price(ticker) -> float | None`
  - `get_all() -> dict[str, PriceUpdate]`
  - `remove(ticker)`
  - `version` property — monotonic counter, increments on every update (for SSE change detection)

- **`MarketDataSource`** — Abstract interface implemented by `SimulatorDataSource` and `MassiveDataSource`. Lifecycle: `start(tickers)` → `add_ticker()` / `remove_ticker()` → `stop()`.

- **`create_market_data_source(cache)`** — Factory. Returns `MassiveDataSource` if `MASSIVE_API_KEY` is set, otherwise `SimulatorDataSource`.

### SSE Streaming

```python
from app.market import create_stream_router

router = create_stream_router(price_cache)  # Returns FastAPI APIRouter
# Endpoint: GET /api/stream/prices (text/event-stream)
```

## Database API

All DB operations are in `app/db/queries.py`. The connection is managed in `app/db/database.py`.

```python
from app.db import (
    init_db, get_cash_balance, update_cash_balance,
    get_watchlist, get_watchlist_tickers, add_to_watchlist, remove_from_watchlist,
    get_positions, get_position, upsert_position, delete_position,
    record_trade, record_snapshot, get_snapshots,
    get_chat_messages, add_chat_message,
)
```

- `init_db()` — Creates tables and seeds default data if the DB is empty. Safe to call on every startup.
- DB path is read from the `DB_PATH` env var; defaults to `db/finally.db` relative to the project root.

## LLM API

```python
from app.llm.client import get_chat_response
from app.llm.schemas import ChatResponse, TradeAction, WatchlistAction

response: ChatResponse = get_chat_response(
    user_message="Buy 5 shares of AAPL",
    portfolio_context={"cash": 9000, "positions": [...]},
    chat_history=[{"role": "user", "content": "..."}, ...],
)
# response.message — text to show user
# response.trades — list of TradeAction to auto-execute
# response.watchlist_changes — list of WatchlistAction to apply
```

- Set `LLM_MOCK=true` to get deterministic responses without an API key.
- Model: `openrouter/openai/gpt-oss-120b` routed through Cerebras for fast inference.

## Testing

```bash
uv run pytest -v              # All tests
uv run pytest --cov=app       # With coverage
uv run ruff check app/ tests/ # Lint
```

### SSE Tests

Do **not** use `httpx.ASGITransport` to test SSE endpoints — it never sends a disconnect event, causing the infinite generator to hang. Instead, test `_generate_events()` directly by passing a mock request whose `is_disconnected()` coroutine returns `True` after N calls. See `tests/market/test_stream.py` for the pattern.

## Seed Data

Default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX. Seed prices and per-ticker volatility/drift parameters are in `app/market/seed_prices.py`.

## Demo

```bash
uv run market_data_demo.py   # Live terminal dashboard with simulated prices
```
