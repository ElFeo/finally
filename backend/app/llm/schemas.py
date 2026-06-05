"""Pydantic schemas for LLM structured outputs."""

from pydantic import BaseModel, field_validator


class TradeAction(BaseModel):
    """A single trade instruction from the LLM."""

    ticker: str
    side: str  # "buy" or "sell"
    quantity: float

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        v = v.lower()
        if v not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got '{v}'")
        return v

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"quantity must be positive, got {v}")
        return v


class WatchlistAction(BaseModel):
    """A single watchlist change instruction from the LLM."""

    ticker: str
    action: str  # "add" or "remove"

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        v = v.lower()
        if v not in ("add", "remove"):
            raise ValueError(f"action must be 'add' or 'remove', got '{v}'")
        return v

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()


class ChatResponse(BaseModel):
    """Structured response from the LLM."""

    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistAction] = []
