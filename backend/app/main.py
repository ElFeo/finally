"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import (
    get_cash_balance,
    get_positions,
    get_watchlist_tickers,
    init_db,
    record_snapshot,
)
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.routes.health import router as health_router
from app.routes.portfolio import router as portfolio_router
from app.routes.watchlist import router as watchlist_router

price_cache = PriceCache()


async def _snapshot_task(app: FastAPI) -> None:
    """Background task: record a portfolio snapshot every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        try:
            positions = get_positions("default")
            cash = get_cash_balance("default")
            cache = app.state.price_cache
            market_value = sum(
                p["quantity"] * (cache.get_price(p["ticker"]) or p["avg_cost"])
                for p in positions
            )
            record_snapshot("default", cash + market_value)
        except Exception:
            pass  # Never crash the background task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB, start market data, start snapshot task."""
    init_db()
    tickers = get_watchlist_tickers("default")
    market_source = create_market_data_source(price_cache)
    await market_source.start(tickers)
    app.state.price_cache = price_cache
    app.state.market_source = market_source

    task = asyncio.create_task(_snapshot_task(app))
    try:
        yield
    finally:
        task.cancel()
        await market_source.stop()


app = FastAPI(title="FinAlly — AI Trading Workstation", lifespan=lifespan)

# SSE streaming router (created with a reference to the shared price cache)
stream_router = create_stream_router(price_cache)
app.include_router(stream_router)

# REST API routers
app.include_router(portfolio_router, prefix="/api")
app.include_router(watchlist_router, prefix="/api")
app.include_router(health_router, prefix="/api")

# Chat router — created by the LLM engineer; import conditionally so the app
# still starts when that module has not been written yet.
try:
    from app.routes.chat import router as chat_router  # noqa: PLC0415

    app.include_router(chat_router, prefix="/api")
except ImportError:
    pass  # Chat route not yet available

# ---------------------------------------------------------------------------
# Serve Next.js static export (must be registered last so API routes win)
# ---------------------------------------------------------------------------
static_dir = os.environ.get(
    "STATIC_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out"),
)
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
