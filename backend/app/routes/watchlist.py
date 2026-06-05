"""Watchlist management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db import (
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
)

router = APIRouter(tags=["watchlist"])

USER_ID = "default"


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("/watchlist")
async def get_watchlist_endpoint(request: Request) -> dict:
    """Return all watchlist tickers enriched with latest price data."""
    cache = request.app.state.price_cache
    entries = get_watchlist(USER_ID)

    tickers_with_prices = []
    for entry in entries:
        ticker = entry["ticker"]
        update = cache.get(ticker)
        if update is not None:
            tickers_with_prices.append(
                {
                    "ticker": ticker,
                    "price": update.price,
                    "previous_price": update.previous_price,
                    "change": update.change,
                    "change_percent": update.change_percent,
                    "direction": update.direction,
                    "added_at": entry["added_at"],
                }
            )
        else:
            tickers_with_prices.append(
                {
                    "ticker": ticker,
                    "price": None,
                    "previous_price": None,
                    "change": None,
                    "change_percent": None,
                    "direction": "flat",
                    "added_at": entry["added_at"],
                }
            )

    return {"tickers": tickers_with_prices}


@router.post("/watchlist", status_code=201)
async def add_ticker(body: AddTickerRequest, request: Request) -> dict:
    """Add a ticker to the watchlist."""
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty")

    try:
        result = add_to_watchlist(USER_ID, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Tell the market source to start tracking this ticker
    market_source = request.app.state.market_source
    await market_source.add_ticker(ticker)

    return {"ticker": result["ticker"], "added_at": result["added_at"]}


@router.delete("/watchlist/{ticker}")
async def remove_ticker(ticker: str, request: Request) -> dict:
    """Remove a ticker from the watchlist."""
    ticker = ticker.strip().upper()
    removed = remove_from_watchlist(USER_ID, ticker)
    if not removed:
        raise HTTPException(
            status_code=404, detail=f"Ticker '{ticker}' not found in watchlist"
        )

    # Tell the market source to stop tracking this ticker
    market_source = request.app.state.market_source
    await market_source.remove_ticker(ticker)

    return {"success": True}
