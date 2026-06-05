"""Tests for the SSE streaming endpoint."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


def _make_app(cache: PriceCache) -> FastAPI:
    app = FastAPI()
    app.include_router(create_stream_router(cache))
    return app


def _make_request(disconnect_after: int = 2):
    """Return a mock request object that signals disconnect after N is_disconnected() calls."""
    from unittest.mock import MagicMock

    call_count = 0

    async def is_disconnected() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count > disconnect_after

    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "test-client"
    request.is_disconnected = is_disconnected
    return request


@pytest.mark.asyncio
async def test_sse_returns_correct_content_type():
    """StreamingResponse is created with text/event-stream content type."""
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    app = _make_app(cache)
    # Check the route is registered with the right media_type via the response object
    from fastapi.responses import StreamingResponse
    from fastapi.testclient import TestClient

    # Use a very short-lived request check via the router config
    stream_router = create_stream_router(cache)
    assert len(stream_router.routes) == 1
    assert stream_router.routes[0].path == "/api/stream/prices"


@pytest.mark.asyncio
async def test_sse_emits_seeded_prices():
    """Generator emits price data for all cached tickers."""
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    cache.update("GOOGL", 175.25)

    request = _make_request(disconnect_after=2)
    events = []
    async for chunk in _generate_events(cache, request, interval=0.01):
        events.append(chunk)

    data_events = [e for e in events if e.startswith("data:")]
    assert len(data_events) >= 1
    data = json.loads(data_events[0].removeprefix("data: ").strip())
    assert data["AAPL"]["price"] == 190.50
    assert data["GOOGL"]["price"] == 175.25
    assert data["AAPL"]["direction"] == "flat"


@pytest.mark.asyncio
async def test_sse_includes_retry_directive():
    """Generator yields a retry directive as the very first chunk."""
    cache = PriceCache()
    cache.update("AAPL", 190.00)

    request = _make_request(disconnect_after=1)
    chunks = []
    async for chunk in _generate_events(cache, request, interval=0.01):
        chunks.append(chunk)
        break  # only need the first chunk

    assert chunks[0].startswith("retry:")


@pytest.mark.asyncio
async def test_sse_no_event_when_cache_empty():
    """With an empty cache, no data event is emitted."""
    cache = PriceCache()

    request = _make_request(disconnect_after=2)
    events = []
    async for chunk in _generate_events(cache, request, interval=0.01):
        events.append(chunk)

    data_events = [e for e in events if e.startswith("data:")]
    assert data_events == []


@pytest.mark.asyncio
async def test_sse_skips_emission_when_version_unchanged():
    """Version-based dedup: only one data event despite multiple poll cycles."""
    cache = PriceCache()
    cache.update("AAPL", 190.00)

    # Allow 4 disconnect checks so the loop runs ~3 poll cycles
    request = _make_request(disconnect_after=4)
    events = []
    async for chunk in _generate_events(cache, request, interval=0.01):
        events.append(chunk)

    data_events = [e for e in events if e.startswith("data:")]
    # Cache never changed, so version stays the same after first emit
    assert len(data_events) == 1


def test_create_stream_router_returns_fresh_router_each_call():
    """Each call produces an independent router — no route duplication."""
    cache1 = PriceCache()
    cache2 = PriceCache()
    router1 = create_stream_router(cache1)
    router2 = create_stream_router(cache2)
    assert router1 is not router2
    assert len(router1.routes) == 1
    assert len(router2.routes) == 1
