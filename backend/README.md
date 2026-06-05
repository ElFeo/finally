# FinAlly Backend

FastAPI backend for the FinAlly AI Trading Workstation.

## Structure

```
app/
├── main.py              # FastAPI entry point; lifespan manages DB init, market data, snapshot task
├── db/
│   ├── database.py      # SQLite connection (WAL mode, lazy init from DB_PATH env var)
│   └── queries.py       # All DB operations: watchlist, positions, trades, snapshots, chat messages
├── llm/
│   ├── client.py        # LiteLLM → openrouter/openai/gpt-oss-120b via Cerebras
│   ├── schemas.py       # Pydantic output models: ChatResponse, TradeAction, WatchlistAction
│   └── mock.py          # Deterministic mock responses when LLM_MOCK=true
├── market/
│   ├── cache.py         # Thread-safe PriceCache (ticker → PriceUpdate)
│   ├── simulator.py     # GBM price simulator (default market source)
│   ├── massive_client.py# Massive/Polygon.io REST polling client (optional)
│   ├── stream.py        # SSE endpoint: GET /api/stream/prices
│   ├── factory.py       # create_market_data_source() — picks source based on MASSIVE_API_KEY
│   ├── interface.py     # MarketDataSource abstract base class
│   ├── models.py        # PriceUpdate dataclass
│   └── seed_prices.py   # Default tickers and per-ticker GBM parameters
└── routes/
    ├── portfolio.py     # GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history
    ├── watchlist.py     # GET /api/watchlist, POST /api/watchlist, DELETE /api/watchlist/{ticker}
    ├── chat.py          # POST /api/chat
    └── health.py        # GET /api/health
```

## Running Tests

```bash
# Install dependencies
uv sync --dev

# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific suite
uv run pytest tests/test_db/ -v
uv run pytest tests/test_routes/ -v
uv run pytest tests/test_llm/ -v
uv run pytest tests/market/ -v
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `db/finally.db` (project root) | SQLite file path |
| `STATIC_DIR` | `frontend/out/` | Next.js static export directory |
| `MASSIVE_API_KEY` | _(unset)_ | If set, uses Massive REST API for prices; otherwise uses GBM simulator |
| `OPENROUTER_API_KEY` | _(required for chat)_ | OpenRouter API key |
| `LLM_MOCK` | `false` | Set `true` for deterministic mock LLM responses |

## Development

```bash
# Install dependencies
uv sync --dev

# Run dev server (auto-reload)
uv run uvicorn app.main:app --reload --port 8000

# Lint
uv run ruff check app/ tests/

# Format
uv run ruff format app/ tests/

# Market data demo (terminal dashboard)
uv run market_data_demo.py
```
