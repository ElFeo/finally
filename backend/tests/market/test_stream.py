"""Tests for the SSE streaming endpoint."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.market.cache import PriceCache
from app.market.stream import create_stream_router


def _make_app(cache: PriceCache) -> FastAPI:
    app = FastAPI()
    app.include_router(create_stream_router(cache))
    return app


@pytest.mark.asyncio
async def test_sse_returns_correct_content_type():
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    async with AsyncClient(transport=ASGITransport(_make_app(cache)), base_url="http://test") as client:
        async with client.stream("GET", "/api/stream/prices") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_sse_emits_seeded_prices():
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    cache.update("GOOGL", 175.25)

    async with AsyncClient(transport=ASGITransport(_make_app(cache)), base_url="http://test") as client:
        async with client.stream("GET", "/api/stream/prices") as resp:

            async def first_data_event() -> dict:
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        return json.loads(line[len("data:"):].strip())
                return {}

            data = await asyncio.wait_for(first_data_event(), timeout=2.0)

    assert data["AAPL"]["price"] == 190.50
    assert data["GOOGL"]["price"] == 175.25
    assert data["AAPL"]["direction"] == "flat"


@pytest.mark.asyncio
async def test_sse_includes_retry_directive():
    cache = PriceCache()
    cache.update("AAPL", 190.00)

    async with AsyncClient(transport=ASGITransport(_make_app(cache)), base_url="http://test") as client:
        async with client.stream("GET", "/api/stream/prices") as resp:

            async def first_line() -> str:
                async for line in resp.aiter_lines():
                    if line.strip():
                        return line
                return ""

            line = await asyncio.wait_for(first_line(), timeout=2.0)

    assert line.startswith("retry:")


@pytest.mark.asyncio
async def test_sse_no_event_when_cache_empty():
    """With an empty cache, no data event should be emitted in the first tick."""
    cache = PriceCache()

    async with AsyncClient(transport=ASGITransport(_make_app(cache)), base_url="http://test") as client:
        async with client.stream("GET", "/api/stream/prices") as resp:

            async def collect_lines(timeout: float) -> list[str]:
                lines = []
                try:
                    async with asyncio.timeout(timeout):
                        async for line in resp.aiter_lines():
                            if line.strip():
                                lines.append(line)
                except TimeoutError:
                    pass
                return lines

            lines = await collect_lines(0.8)

    data_lines = [l for l in lines if l.startswith("data:")]
    assert data_lines == []


@pytest.mark.asyncio
async def test_sse_skips_emission_when_version_unchanged():
    """Version-based dedup: only one event emitted despite two poll cycles."""
    cache = PriceCache()
    cache.update("AAPL", 190.00)

    async with AsyncClient(transport=ASGITransport(_make_app(cache)), base_url="http://test") as client:
        async with client.stream("GET", "/api/stream/prices") as resp:

            async def collect_data_events(n: int, timeout: float) -> list[dict]:
                events = []
                try:
                    async with asyncio.timeout(timeout):
                        async for line in resp.aiter_lines():
                            if line.startswith("data:"):
                                events.append(json.loads(line[len("data:"):].strip()))
                            if len(events) >= n:
                                break
                except TimeoutError:
                    pass
                return events

            # Wait ~1.5s (3 poll cycles at 500ms); cache never changes
            events = await collect_data_events(2, timeout=1.5)

    # Should have exactly one event — the version never changed after the first emit
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_stream_router_returns_fresh_router_each_call():
    """Each call produces an independent router — no route duplication."""
    cache1 = PriceCache()
    cache2 = PriceCache()
    router1 = create_stream_router(cache1)
    router2 = create_stream_router(cache2)
    assert router1 is not router2
    # Each router has exactly one route registered
    assert len(router1.routes) == 1
    assert len(router2.routes) == 1
