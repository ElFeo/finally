"""Portfolio management endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.db import (
    delete_position,
    get_cash_balance,
    get_position,
    get_positions,
    get_snapshots,
    record_snapshot,
    record_trade,
    update_cash_balance,
    upsert_position,
)

router = APIRouter(tags=["portfolio"])

USER_ID = "default"


class TradeRequest(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    side: Literal["buy", "sell"]


@router.get("/portfolio")
def get_portfolio(request: Request) -> dict:
    """Return current portfolio state including positions and cash balance."""
    cache = request.app.state.price_cache
    positions_raw = get_positions(USER_ID)
    cash = get_cash_balance(USER_ID)

    positions = []
    total_unrealized_pnl = 0.0
    total_market_value = 0.0

    for pos in positions_raw:
        ticker = pos["ticker"]
        qty = pos["quantity"]
        avg_cost = pos["avg_cost"]

        current_price = cache.get_price(ticker)
        if current_price is None:
            current_price = avg_cost  # Fallback to avg cost if price unavailable

        market_value = qty * current_price
        cost_basis = qty * avg_cost
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0.0

        positions.append(
            {
                "ticker": ticker,
                "quantity": qty,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": round(market_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 4),
            }
        )
        total_unrealized_pnl += unrealized_pnl
        total_market_value += market_value

    total_value = cash + total_market_value
    total_pnl_pct = (
        (total_unrealized_pnl / (total_value - total_unrealized_pnl) * 100)
        if (total_value - total_unrealized_pnl) != 0
        else 0.0
    )

    return {
        "cash_balance": round(cash, 2),
        "total_value": round(total_value, 2),
        "positions": positions,
        "unrealized_pnl": round(total_unrealized_pnl, 2),
        "unrealized_pnl_pct": round(total_pnl_pct, 4),
    }


@router.get("/portfolio/history")
def get_portfolio_history() -> dict:
    """Return portfolio value snapshots over time."""
    snapshots = get_snapshots(USER_ID)
    return {"snapshots": snapshots}


@router.post("/portfolio/trade")
async def execute_trade(body: TradeRequest, request: Request) -> dict:
    """Execute a market order (buy or sell)."""
    cache = request.app.state.price_cache
    ticker = body.ticker.strip().upper()
    quantity = body.quantity
    side = body.side

    # Fetch current price
    price = cache.get_price(ticker)
    if price is None:
        return {"success": False, "error": f"Price unavailable for {ticker}"}

    if side == "buy":
        cash = get_cash_balance(USER_ID)
        cost = quantity * price
        if cash < cost:
            return {
                "success": False,
                "error": f"Insufficient cash (need ${cost:.2f}, have ${cash:.2f})",
            }

        # Compute new weighted average cost
        existing = get_position(USER_ID, ticker)
        if existing:
            total_qty = existing["quantity"] + quantity
            new_avg = (existing["quantity"] * existing["avg_cost"] + quantity * price) / total_qty
        else:
            total_qty, new_avg = quantity, price

        # Persist changes
        new_cash = cash - cost
        update_cash_balance(USER_ID, new_cash)
        upsert_position(USER_ID, ticker, total_qty, new_avg)
        trade = record_trade(USER_ID, ticker, "buy", quantity, price)
        _record_portfolio_snapshot(request, USER_ID)

        return {
            "success": True,
            "trade": {
                "ticker": trade["ticker"],
                "side": trade["side"],
                "quantity": trade["quantity"],
                "price": trade["price"],
                "executed_at": trade["executed_at"],
            },
            "new_cash_balance": round(new_cash, 2),
            "position": {
                "ticker": ticker,
                "quantity": total_qty,
                "avg_cost": round(new_avg, 4),
            },
        }

    else:  # sell
        existing = get_position(USER_ID, ticker)
        if existing is None or existing["quantity"] < quantity:
            held = existing["quantity"] if existing else 0
            return {
                "success": False,
                "error": f"Insufficient shares (trying to sell {quantity}, have {held})",
            }

        proceeds = quantity * price
        cash = get_cash_balance(USER_ID)
        new_cash = cash + proceeds

        remaining_qty = existing["quantity"] - quantity
        update_cash_balance(USER_ID, new_cash)

        if remaining_qty <= 0:
            delete_position(USER_ID, ticker)
            new_position = {"ticker": ticker, "quantity": 0.0, "avg_cost": existing["avg_cost"]}
        else:
            upsert_position(USER_ID, ticker, remaining_qty, existing["avg_cost"])
            new_position = {
                "ticker": ticker,
                "quantity": remaining_qty,
                "avg_cost": existing["avg_cost"],
            }

        trade = record_trade(USER_ID, ticker, "sell", quantity, price)
        _record_portfolio_snapshot(request, USER_ID)

        return {
            "success": True,
            "trade": {
                "ticker": trade["ticker"],
                "side": trade["side"],
                "quantity": trade["quantity"],
                "price": trade["price"],
                "executed_at": trade["executed_at"],
            },
            "new_cash_balance": round(new_cash, 2),
            "position": new_position,
        }


def _record_portfolio_snapshot(request: Request, user_id: str) -> None:
    """Record a portfolio snapshot immediately after a trade."""
    try:
        cache = request.app.state.price_cache
        positions = get_positions(user_id)
        cash = get_cash_balance(user_id)
        market_value = sum(
            p["quantity"] * (cache.get_price(p["ticker"]) or p["avg_cost"])
            for p in positions
        )
        record_snapshot(user_id, cash + market_value)
    except Exception:
        pass  # Snapshot failure should not fail the trade
