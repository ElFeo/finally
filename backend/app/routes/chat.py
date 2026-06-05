"""Chat endpoint — LLM-powered trading assistant."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.db import (
    add_chat_message,
    add_to_watchlist,
    delete_position,
    get_cash_balance,
    get_chat_messages,
    get_position,
    get_positions,
    get_watchlist_tickers,
    record_snapshot,
    record_trade,
    remove_from_watchlist,
    update_cash_balance,
    upsert_position,
)
from app.llm import get_chat_response

router = APIRouter(tags=["chat"])

USER_ID = "default"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Portfolio context builder
# ---------------------------------------------------------------------------

def _build_portfolio_context(price_cache) -> dict:
    """Build the portfolio context dict passed to the LLM."""
    cash = get_cash_balance(USER_ID)
    positions = get_positions(USER_ID)
    watchlist_tickers = get_watchlist_tickers(USER_ID)

    # Enrich positions with current prices and P&L
    enriched_positions = []
    positions_value = 0.0
    for pos in positions:
        ticker = pos["ticker"]
        current_price = price_cache.get_price(ticker)
        if current_price is None:
            current_price = pos["avg_cost"]  # Fallback to avg cost if no price

        market_value = pos["quantity"] * current_price
        cost_basis = pos["quantity"] * pos["avg_cost"]
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis else 0.0

        positions_value += market_value
        enriched_positions.append(
            {
                "ticker": ticker,
                "quantity": pos["quantity"],
                "avg_cost": pos["avg_cost"],
                "current_price": round(current_price, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 4),
            }
        )

    total_value = cash + positions_value

    # Collect current watchlist prices
    watchlist_prices = {}
    for ticker in watchlist_tickers:
        price = price_cache.get_price(ticker)
        if price is not None:
            watchlist_prices[ticker] = round(price, 2)

    return {
        "cash_balance": round(cash, 2),
        "total_value": round(total_value, 2),
        "positions": enriched_positions,
        "watchlist": watchlist_tickers,
        "watchlist_prices": watchlist_prices,
    }


# ---------------------------------------------------------------------------
# Trade execution helper
# ---------------------------------------------------------------------------

def _execute_trade(ticker: str, side: str, quantity: float, price_cache) -> dict:
    """Execute a single trade and return a result dict."""
    ticker = ticker.upper().strip()
    price = price_cache.get_price(ticker)

    if price is None:
        return {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "price": None,
            "success": False,
            "error": f"No price available for {ticker}",
        }

    cash = get_cash_balance(USER_ID)

    if side == "buy":
        cost = price * quantity
        if cost > cash:
            return {
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "price": price,
                "success": False,
                "error": f"Insufficient cash: need ${cost:.2f}, have ${cash:.2f}",
            }

        # Update position
        existing = get_position(USER_ID, ticker)
        if existing:
            new_qty = existing["quantity"] + quantity
            new_avg = (existing["avg_cost"] * existing["quantity"] + price * quantity) / new_qty
        else:
            new_qty = quantity
            new_avg = price

        upsert_position(USER_ID, ticker, new_qty, new_avg)
        update_cash_balance(USER_ID, cash - cost)
        record_trade(USER_ID, ticker, "buy", quantity, price)

        return {
            "ticker": ticker,
            "side": "buy",
            "quantity": quantity,
            "price": price,
            "success": True,
        }

    elif side == "sell":
        existing = get_position(USER_ID, ticker)
        if not existing:
            return {
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "price": price,
                "success": False,
                "error": f"No position in {ticker}",
            }

        if quantity > existing["quantity"]:
            return {
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "price": price,
                "success": False,
                "error": (
                    f"Cannot sell {quantity} shares; only {existing['quantity']} owned"
                ),
            }

        proceeds = price * quantity
        new_qty = existing["quantity"] - quantity

        if new_qty == 0:
            delete_position(USER_ID, ticker)
        else:
            upsert_position(USER_ID, ticker, new_qty, existing["avg_cost"])

        update_cash_balance(USER_ID, cash + proceeds)
        record_trade(USER_ID, ticker, "sell", quantity, price)

        return {
            "ticker": ticker,
            "side": "sell",
            "quantity": quantity,
            "price": price,
            "success": True,
        }

    else:
        return {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "price": price,
            "success": False,
            "error": f"Invalid trade side '{side}'",
        }


# ---------------------------------------------------------------------------
# Watchlist change helper
# ---------------------------------------------------------------------------

async def _apply_watchlist_change(ticker: str, action: str, market_source) -> dict:
    """Apply a single watchlist add/remove and return a result dict."""
    ticker = ticker.upper().strip()
    action = action.lower()

    if action == "add":
        try:
            add_to_watchlist(USER_ID, ticker)
            await market_source.add_ticker(ticker)
            return {"ticker": ticker, "action": "add", "success": True}
        except ValueError as exc:
            return {"ticker": ticker, "action": "add", "success": False, "error": str(exc)}

    elif action == "remove":
        removed = remove_from_watchlist(USER_ID, ticker)
        if removed:
            await market_source.remove_ticker(ticker)
            return {"ticker": ticker, "action": "remove", "success": True}
        else:
            return {
                "ticker": ticker,
                "action": "remove",
                "success": False,
                "error": f"'{ticker}' not found in watchlist",
            }

    else:
        return {
            "ticker": ticker,
            "action": action,
            "success": False,
            "error": f"Invalid watchlist action '{action}'",
        }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> dict:
    """Send a message to the AI trading assistant.

    The assistant may execute trades and/or modify the watchlist automatically.
    All actions are recorded in the database.
    """
    user_message = body.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    price_cache = request.app.state.price_cache
    market_source = request.app.state.market_source

    # 1. Build portfolio context for the LLM
    portfolio_context = _build_portfolio_context(price_cache)

    # 2. Load recent chat history (last 50 messages → trimmed to 20 inside client)
    raw_history = get_chat_messages(USER_ID, limit=50)
    chat_history = [{"role": m["role"], "content": m["content"]} for m in raw_history]

    # 3. Call the LLM
    llm_response = get_chat_response(user_message, portfolio_context, chat_history)

    # 4. Auto-execute trades
    trades_executed = []
    for trade in llm_response.trades:
        result = _execute_trade(trade.ticker, trade.side, trade.quantity, price_cache)
        trades_executed.append(result)

    # 5. Apply watchlist changes
    watchlist_results = []
    for change in llm_response.watchlist_changes:
        result = await _apply_watchlist_change(change.ticker, change.action, market_source)
        watchlist_results.append(result)

    # 6. Record a portfolio snapshot after any trades
    if trades_executed:
        updated_context = _build_portfolio_context(price_cache)
        record_snapshot(USER_ID, updated_context["total_value"])

    # 7. Persist user message and assistant response
    actions_payload = None
    if trades_executed or watchlist_results:
        actions_payload = {
            "trades": trades_executed,
            "watchlist_changes": watchlist_results,
        }

    add_chat_message(USER_ID, "user", user_message)
    add_chat_message(USER_ID, "assistant", llm_response.message, actions=actions_payload)

    # 8. Return the full response
    return {
        "message": llm_response.message,
        "trades_executed": trades_executed,
        "watchlist_changes": watchlist_results,
    }
