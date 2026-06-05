"""Tests for LLM client (mock mode and message construction)."""

import pytest

from app.llm.schemas import ChatResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    """Enable mock mode for all tests in this module — no real API calls."""
    monkeypatch.setenv("LLM_MOCK", "true")


PORTFOLIO_CONTEXT = {
    "cash_balance": 10000.0,
    "total_value": 10000.0,
    "positions": [],
    "watchlist": ["AAPL", "GOOGL", "TSLA"],
    "watchlist_prices": {"AAPL": 190.0, "GOOGL": 175.0, "TSLA": 250.0},
}

CHAT_HISTORY: list[dict] = []


# ---------------------------------------------------------------------------
# Mock mode: deterministic responses
# ---------------------------------------------------------------------------

class TestMockMode:
    def test_buy_aapl_message(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("buy 5 aapl", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert isinstance(result, ChatResponse)
        assert len(result.trades) == 1
        assert result.trades[0].ticker == "AAPL"
        assert result.trades[0].side == "buy"
        assert result.trades[0].quantity == 5

    def test_buy_aapl_case_insensitive(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("BUY 10 AAPL please", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert result.trades[0].ticker == "AAPL"
        assert result.trades[0].side == "buy"

    def test_sell_message(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("sell all my AAPL", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert len(result.trades) == 1
        assert result.trades[0].side == "sell"

    def test_add_watchlist_message(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("add PYPL to my watchlist", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert len(result.watchlist_changes) == 1
        assert result.watchlist_changes[0].ticker == "PYPL"
        assert result.watchlist_changes[0].action == "add"

    def test_watch_keyword_triggers_watchlist(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("watch NFLX", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert len(result.watchlist_changes) == 1

    def test_generic_message_returns_portfolio_summary(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("What's my portfolio status?", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert isinstance(result, ChatResponse)
        assert result.trades == []
        assert result.watchlist_changes == []
        assert len(result.message) > 0

    def test_returns_chat_response_type(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("hello", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert isinstance(result, ChatResponse)

    def test_mock_response_has_message(self):
        from app.llm.client import get_chat_response
        result = get_chat_response("buy 5 aapl", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert result.message
        assert isinstance(result.message, str)


# ---------------------------------------------------------------------------
# Mock mode: directly tests the mock module
# ---------------------------------------------------------------------------

class TestGetMockResponse:
    def test_buy_aapl(self):
        from app.llm.mock import get_mock_response
        r = get_mock_response("buy 5 aapl now")
        assert r.trades[0].ticker == "AAPL"
        assert r.trades[0].side == "buy"
        assert r.trades[0].quantity == 5

    def test_sell(self):
        from app.llm.mock import get_mock_response
        r = get_mock_response("sell everything")
        assert r.trades[0].side == "sell"

    def test_add_to_watchlist(self):
        from app.llm.mock import get_mock_response
        r = get_mock_response("add PYPL to my watchlist")
        assert r.watchlist_changes[0].ticker == "PYPL"
        assert r.watchlist_changes[0].action == "add"

    def test_watch_keyword(self):
        from app.llm.mock import get_mock_response
        r = get_mock_response("watch NFLX for me")
        assert len(r.watchlist_changes) == 1

    def test_default_response(self):
        from app.llm.mock import get_mock_response
        r = get_mock_response("how are the markets today?")
        assert r.trades == []
        assert r.watchlist_changes == []
        assert "$10,000" in r.message


# ---------------------------------------------------------------------------
# LLM_MOCK env var controls dispatch
# ---------------------------------------------------------------------------

class TestMockModeDispatch:
    def test_mock_true_uses_mock(self, monkeypatch):
        """When LLM_MOCK=true, get_chat_response uses the mock — no litellm call."""
        monkeypatch.setenv("LLM_MOCK", "true")
        from app.llm.client import get_chat_response

        # Should not raise even though no API key is configured
        result = get_chat_response("hello", PORTFOLIO_CONTEXT, CHAT_HISTORY)
        assert isinstance(result, ChatResponse)

    def test_mock_false_calls_litellm(self, monkeypatch, mocker):
        """When LLM_MOCK=false, get_chat_response calls litellm.completion."""
        monkeypatch.setenv("LLM_MOCK", "false")

        # Build a fake litellm response that returns valid JSON
        fake_resp_json = ChatResponse(
            message="Test response from LLM",
            trades=[],
            watchlist_changes=[],
        ).model_dump_json()

        mock_message = mocker.MagicMock()
        mock_message.content = fake_resp_json
        mock_choice = mocker.MagicMock()
        mock_choice.message = mock_message
        mock_completion = mocker.MagicMock()
        mock_completion.choices = [mock_choice]

        mock_litellm = mocker.patch("app.llm.client.completion", return_value=mock_completion)

        from app.llm import client as llm_client
        # Reload the module function under fresh env
        result = llm_client.get_chat_response("hello", PORTFOLIO_CONTEXT, CHAT_HISTORY)

        assert mock_litellm.called
        assert isinstance(result, ChatResponse)
        assert result.message == "Test response from LLM"

    def test_messages_include_system_prompt(self, monkeypatch, mocker):
        """When not in mock mode, the system prompt is the first message."""
        monkeypatch.setenv("LLM_MOCK", "false")

        fake_resp_json = ChatResponse(message="ok").model_dump_json()
        mock_message = mocker.MagicMock()
        mock_message.content = fake_resp_json
        mock_choice = mocker.MagicMock()
        mock_choice.message = mock_message
        mock_completion = mocker.MagicMock()
        mock_completion.choices = [mock_choice]

        mock_litellm = mocker.patch("app.llm.client.completion", return_value=mock_completion)

        from app.llm import client as llm_client
        llm_client.get_chat_response("tell me about my portfolio", PORTFOLIO_CONTEXT, [])

        call_kwargs = mock_litellm.call_args
        messages = call_kwargs.kwargs["messages"]
        # First message must be the system prompt
        assert messages[0]["role"] == "system"
        assert "FinAlly" in messages[0]["content"]

    def test_messages_include_portfolio_context(self, monkeypatch, mocker):
        """Portfolio context is included as a user message after the system prompt."""
        monkeypatch.setenv("LLM_MOCK", "false")

        fake_resp_json = ChatResponse(message="ok").model_dump_json()
        mock_message = mocker.MagicMock()
        mock_message.content = fake_resp_json
        mock_choice = mocker.MagicMock()
        mock_choice.message = mock_message
        mock_completion = mocker.MagicMock()
        mock_completion.choices = [mock_choice]

        mock_litellm = mocker.patch("app.llm.client.completion", return_value=mock_completion)

        ctx = {**PORTFOLIO_CONTEXT, "cash_balance": 9999.0}
        from app.llm import client as llm_client
        llm_client.get_chat_response("hello", ctx, [])

        call_kwargs = mock_litellm.call_args
        messages = call_kwargs.kwargs["messages"]
        # Second message should contain the portfolio context JSON
        context_msg = messages[1]
        assert context_msg["role"] == "user"
        assert "9999" in context_msg["content"]

    def test_chat_history_truncated_to_20(self, monkeypatch, mocker):
        """Only the last 20 history messages are included."""
        monkeypatch.setenv("LLM_MOCK", "false")

        fake_resp_json = ChatResponse(message="ok").model_dump_json()
        mock_message = mocker.MagicMock()
        mock_message.content = fake_resp_json
        mock_choice = mocker.MagicMock()
        mock_choice.message = mock_message
        mock_completion = mocker.MagicMock()
        mock_completion.choices = [mock_choice]

        mock_litellm = mocker.patch("app.llm.client.completion", return_value=mock_completion)

        # Build 30 history messages
        history = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
        from app.llm import client as llm_client
        llm_client.get_chat_response("final", PORTFOLIO_CONTEXT, history)

        call_kwargs = mock_litellm.call_args
        messages = call_kwargs.kwargs["messages"]
        # system + portfolio_context_user + 20 history + current user message = 23
        assert len(messages) == 23

    def test_current_user_message_is_last(self, monkeypatch, mocker):
        """The user's current message is appended as the last message."""
        monkeypatch.setenv("LLM_MOCK", "false")

        fake_resp_json = ChatResponse(message="ok").model_dump_json()
        mock_message = mocker.MagicMock()
        mock_message.content = fake_resp_json
        mock_choice = mocker.MagicMock()
        mock_choice.message = mock_message
        mock_completion = mocker.MagicMock()
        mock_completion.choices = [mock_choice]

        mock_litellm = mocker.patch("app.llm.client.completion", return_value=mock_completion)

        from app.llm import client as llm_client
        llm_client.get_chat_response("final user message", PORTFOLIO_CONTEXT, [])

        call_kwargs = mock_litellm.call_args
        messages = call_kwargs.kwargs["messages"]
        last = messages[-1]
        assert last["role"] == "user"
        assert last["content"] == "final user message"

    def test_model_and_extra_body_passed(self, monkeypatch, mocker):
        """Correct model name and extra_body are forwarded to litellm."""
        monkeypatch.setenv("LLM_MOCK", "false")

        fake_resp_json = ChatResponse(message="ok").model_dump_json()
        mock_message = mocker.MagicMock()
        mock_message.content = fake_resp_json
        mock_choice = mocker.MagicMock()
        mock_choice.message = mock_message
        mock_completion = mocker.MagicMock()
        mock_completion.choices = [mock_choice]

        mock_litellm = mocker.patch("app.llm.client.completion", return_value=mock_completion)

        from app.llm import client as llm_client
        llm_client.get_chat_response("hello", PORTFOLIO_CONTEXT, [])

        call_kwargs = mock_litellm.call_args
        assert call_kwargs.kwargs["model"] == "openrouter/openai/gpt-oss-120b"
        assert "provider" in call_kwargs.kwargs["extra_body"]
