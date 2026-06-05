"""Deterministic mock LLM responses for testing and development."""

from .schemas import ChatResponse, TradeAction, WatchlistAction


def get_mock_response(user_message: str) -> ChatResponse:
    """Return deterministic mock responses for testing.

    Patterns checked (case-insensitive):
    - "buy" + "aapl"  → buy 5 AAPL
    - "sell"          → sell 5 AAPL
    - "add" or "watch" → add PYPL to watchlist
    - anything else   → generic portfolio summary
    """
    msg = user_message.lower()

    if "buy" in msg and "aapl" in msg:
        return ChatResponse(
            message="Buying 5 shares of AAPL at market price.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)],
        )

    if "sell" in msg:
        return ChatResponse(
            message="Selling as requested.",
            trades=[TradeAction(ticker="AAPL", side="sell", quantity=5)],
        )

    if "add" in msg or "watch" in msg:
        return ChatResponse(
            message="Added ticker to your watchlist.",
            watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
        )

    return ChatResponse(
        message=(
            "Your portfolio is looking good! You have $10,000 in cash and no open positions. "
            "Consider diversifying across tech, finance, and consumer sectors."
        ),
        trades=[],
        watchlist_changes=[],
    )
