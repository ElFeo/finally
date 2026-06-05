"""LLM client for FinAlly — calls OpenRouter/Cerebras via LiteLLM."""

from __future__ import annotations

import json
import os

from litellm import completion

from .schemas import ChatResponse

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are FinAlly, an AI trading assistant for a simulated trading platform.
The user has $10,000 starting capital (simulated money, no real risk).

You help users:
- Analyze their portfolio composition, risk, and P&L
- Suggest and execute trades when asked
- Manage their watchlist proactively
- Provide concise, data-driven market insights

When the user asks you to buy/sell or you recommend a trade and they agree,
include it in the "trades" array. For watchlist changes, use "watchlist_changes".

Always respond with valid JSON matching the required schema.
Be concise and actionable. This is a demo — be enthusiastic and helpful.
"""


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def get_chat_response(
    user_message: str,
    portfolio_context: dict,
    chat_history: list[dict],  # [{"role": "user"|"assistant", "content": "..."}]
) -> ChatResponse:
    """Get LLM response for a chat message.

    Uses the mock implementation when LLM_MOCK=true (no real API call).

    Args:
        user_message: The latest message from the user.
        portfolio_context: Dict with cash, positions, watchlist, prices.
        chat_history: Recent conversation history (list of role/content dicts).

    Returns:
        Parsed ChatResponse with message, optional trades, optional watchlist changes.
    """
    if os.environ.get("LLM_MOCK", "false").lower() == "true":
        from .mock import get_mock_response
        return get_mock_response(user_message)

    # Build the messages list
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Current portfolio context:\n{json.dumps(portfolio_context, indent=2)}",
        },
    ]

    # Append recent conversation history (cap at 20 messages to control context size)
    for msg in chat_history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Append the new user message
    messages.append({"role": "user", "content": user_message})

    response = completion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )

    raw_content = response.choices[0].message.content
    return ChatResponse.model_validate_json(raw_content)
