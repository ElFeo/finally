# FinAlly Project - the Finance Ally

All project documentation is in the `planning` directory.

The key document is PLAN.md included in full below. The full platform has been built and is working. Consult `planning/MARKET_DATA_SUMMARY.md` and `planning/archive/` for market data details; all other components are summarized below.

## Project Status: Complete

All components are implemented and tested:

| Component | Status | Location |
|-----------|--------|----------|
| Market data (simulator + Massive API) | Done | `backend/app/market/` |
| SQLite database layer | Done | `backend/app/db/` |
| API routes (portfolio, watchlist, chat, health) | Done | `backend/app/routes/` |
| SSE price streaming | Done | `backend/app/market/stream.py` |
| LLM integration (LiteLLM → OpenRouter/Cerebras) | Done | `backend/app/llm/` |
| FastAPI app entry point + lifespan | Done | `backend/app/main.py` |
| Next.js frontend (all UI components) | Done | `frontend/` |
| Docker container + start/stop scripts | Done | `Dockerfile`, `scripts/` |
| Backend unit tests (125+ tests) | Done | `backend/tests/` |
| Playwright E2E tests | Done | `test/` |

## Backend Structure

```
backend/app/
├── main.py              # FastAPI app, lifespan (DB init, market start, snapshot task)
├── db/
│   ├── database.py      # SQLite connection, WAL mode, lazy init
│   └── queries.py       # All DB operations (watchlist, positions, trades, snapshots, chat)
├── llm/
│   ├── client.py        # LiteLLM → openrouter/openai/gpt-oss-120b via Cerebras
│   ├── schemas.py       # Pydantic: ChatResponse, TradeAction, WatchlistAction
│   └── mock.py          # Deterministic mock responses (LLM_MOCK=true)
├── market/
│   ├── cache.py         # Thread-safe PriceCache
│   ├── simulator.py     # GBM price simulator (default)
│   ├── massive_client.py# Massive/Polygon.io REST client (optional)
│   ├── stream.py        # SSE endpoint GET /api/stream/prices
│   ├── factory.py       # create_market_data_source() — picks source from env
│   ├── interface.py     # MarketDataSource abstract base
│   ├── models.py        # PriceUpdate dataclass
│   └── seed_prices.py   # Default tickers and GBM parameters
└── routes/
    ├── portfolio.py     # GET/POST /api/portfolio, GET /api/portfolio/history
    ├── watchlist.py     # GET/POST/DELETE /api/watchlist
    ├── chat.py          # POST /api/chat
    └── health.py        # GET /api/health
```

## Frontend Structure

```
frontend/
├── app/
│   └── page.tsx         # Root page (dynamic import of TradingWorkstation)
├── components/
│   ├── TradingWorkstation.tsx  # Main layout, SSE connection, shared state
│   ├── Header.tsx              # Portfolio value, cash, connection status
│   ├── WatchlistPanel.tsx      # Ticker grid with sparklines and flash animations
│   ├── MainChart.tsx           # TradingView lightweight-charts price chart
│   ├── PortfolioHeatmap.tsx    # Treemap P&L visualization
│   ├── PnLChart.tsx            # Portfolio value over time (Recharts)
│   ├── PositionsTable.tsx      # Holdings table
│   ├── TradeBar.tsx            # Buy/sell form
│   ├── ChatPanel.tsx           # AI assistant chat UI
│   ├── Sparkline.tsx           # Mini sparkline SVG
│   └── ToastContainer.tsx      # Toast notifications
├── lib/
│   └── api.ts           # Typed API client (all /api/* endpoints)
└── types/
    └── index.ts         # TypeScript types for all API shapes
```

## Key Implementation Notes

- **DB path**: read from `DB_PATH` env var; defaults to `db/finally.db` relative to project root
- **Static files**: served from `STATIC_DIR` env var; defaults to `frontend/out/` (dev) or `/app/static/` (Docker)
- **Null prices**: the SSE cache may not be populated immediately on startup; `WatchlistTicker.price` and related fields are nullable — all `.toFixed()` calls are guarded
- **API response shapes**: watchlist returns `{tickers: [...]}`, portfolio history returns `{snapshots: [...]}`
- **LLM mock**: set `LLM_MOCK=true` for deterministic responses; used in all E2E tests
- **SSE tests**: test the `_generate_events()` generator directly with a mock request; do not use httpx ASGI transport (it never sends disconnect events)
- **Snapshot task**: background asyncio task records portfolio value every 30 seconds and immediately after each trade

@planning/PLAN.md
