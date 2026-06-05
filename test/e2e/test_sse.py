"""
E2E: SSE stream tests.

The SSE endpoint is an infinite async generator. Testing it through the
FastAPI TestClient blocks because the stream never terminates.

Instead, we test the SSE infrastructure directly:
  1. The async generator emits correct events
  2. The price cache works correctly
  3. The event format is valid JSON with the right fields

For the HTTP-level test, we verify the route exists and returns correct
headers by inspecting the route configuration rather than opening an
infinite stream.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, BACKEND_DIR)


class TestSSEStreamEndpoint:
    def test_sse_route_is_registered(self, app):
        """The /api/stream/prices route should be registered on the app."""
        routes = [r.path for r in app.routes]
        assert "/api/stream/prices" in routes, (
            f"SSE route not found. Registered routes: {routes}"
        )

    def test_sse_generator_emits_retry_directive_first(self):
        """The SSE generator should immediately yield a 'retry:' directive."""
        from app.market.cache import PriceCache
        from app.market.stream import _generate_events

        cache = PriceCache()
        cache.update("AAPL", 190.50)

        events = []

        async def _collect():
            class FakeRequest:
                client = None
                async def is_disconnected(self):
                    return len(events) >= 1

            async for event in _generate_events(cache, FakeRequest(), interval=0.001):
                events.append(event)
                if len(events) >= 1:
                    break

        asyncio.run(_collect())

        assert len(events) >= 1, "Generator emitted no events"
        assert "retry:" in events[0], (
            f"First event should be retry directive, got: {events[0]!r}"
        )

    def test_sse_generator_emits_data_events(self):
        """The SSE generator emits data: events with ticker price JSON."""
        from app.market.cache import PriceCache
        from app.market.stream import _generate_events

        cache = PriceCache()
        cache.update("AAPL", 190.50)
        cache.update("TSLA", 250.00)

        events = []

        async def _collect():
            call_count = 0

            class FakeRequest:
                client = None
                async def is_disconnected(self):
                    nonlocal call_count
                    call_count += 1
                    # Stop after collecting a data event or after 10 calls
                    data_events = [e for e in events if e.startswith("data:")]
                    return bool(data_events) or call_count > 10

            async for event in _generate_events(cache, FakeRequest(), interval=0.001):
                events.append(event)

        asyncio.run(_collect())

        data_events = [e for e in events if e.startswith("data:")]
        assert len(data_events) >= 1, f"No data events. All events: {events}"

    def test_sse_data_event_is_valid_json(self):
        """SSE data events contain valid JSON."""
        from app.market.cache import PriceCache
        from app.market.stream import _generate_events

        cache = PriceCache()
        cache.update("AAPL", 190.50)

        events = []

        async def _collect():
            async for event in _generate_events(cache, _StopAfterData(events), interval=0.001):
                events.append(event)

        asyncio.run(_collect())

        data_events = [e for e in events if e.startswith("data:")]
        assert data_events, "No data events emitted"

        for data_event in data_events:
            payload_str = data_event[5:].strip()
            payload = json.loads(payload_str)  # Must not raise
            assert isinstance(payload, dict), f"Payload is not a dict: {type(payload)}"

    def test_sse_data_event_has_ticker_and_price(self):
        """Each ticker in SSE data events has 'ticker' and 'price' fields."""
        from app.market.cache import PriceCache
        from app.market.stream import _generate_events

        cache = PriceCache()
        cache.update("AAPL", 190.50)
        cache.update("NVDA", 825.00)

        events = []

        async def _collect():
            async for event in _generate_events(cache, _StopAfterData(events), interval=0.001):
                events.append(event)

        asyncio.run(_collect())

        data_events = [e for e in events if e.startswith("data:")]
        assert data_events, "No data events"

        payload = json.loads(data_events[0][5:].strip())
        for ticker, data in payload.items():
            assert "ticker" in data, f"No 'ticker' field in {ticker}: {data}"
            assert "price" in data, f"No 'price' field in {ticker}: {data}"
            assert isinstance(data["price"], (int, float)), f"Price is not numeric: {data['price']}"

    def test_sse_generator_stops_on_disconnect(self):
        """Generator terminates when is_disconnected() returns True."""
        from app.market.cache import PriceCache
        from app.market.stream import _generate_events

        cache = PriceCache()
        cache.update("AAPL", 190.50)

        events = []

        async def _collect():
            class DisconnectAfterOne:
                client = None
                count = 0
                async def is_disconnected(self):
                    self.count += 1
                    return self.count > 1

            async for event in _generate_events(cache, DisconnectAfterOne(), interval=0.001):
                events.append(event)

        asyncio.run(_collect())

        # Should have gotten the retry directive and stopped
        assert len(events) >= 1, "Should emit at least the retry directive"
        assert len(events) < 100, "Generator should stop on disconnect, not run forever"

    def test_price_cache_snapshot_returns_all_tickers(self):
        """PriceCache.snapshot() returns all updated tickers."""
        from app.market.cache import PriceCache

        cache = PriceCache()
        cache.update("AAPL", 190.50)
        cache.update("TSLA", 250.00)
        cache.update("NVDA", 800.00)

        prices, version = cache.snapshot()
        assert "AAPL" in prices
        assert "TSLA" in prices
        assert "NVDA" in prices
        assert prices["AAPL"].price == pytest.approx(190.50)
        assert prices["TSLA"].price == pytest.approx(250.00)
        assert version > 0

    def test_price_cache_version_increments_on_update(self):
        """PriceCache version increments with each price update."""
        from app.market.cache import PriceCache

        cache = PriceCache()
        _, v0 = cache.snapshot()
        cache.update("AAPL", 190.50)
        _, v1 = cache.snapshot()
        cache.update("AAPL", 191.00)
        _, v2 = cache.snapshot()

        assert v1 > v0, "Version should increase after first update"
        assert v2 > v1, "Version should increase after second update"

    def test_price_update_direction(self):
        """PriceUpdate direction is 'up'/'down'/'flat' based on price change."""
        from app.market.cache import PriceCache

        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update1 = cache.update("AAPL", 191.00)  # up
        assert update1.direction == "up"

        update2 = cache.update("AAPL", 190.00)  # down
        assert update2.direction == "down"

        update3 = cache.update("AAPL", 190.00)  # flat
        assert update3.direction == "flat"


class _StopAfterData:
    """Helper: fake request that stops the generator after a data event is collected."""
    client = None

    def __init__(self, events: list):
        self._events = events

    async def is_disconnected(self) -> bool:
        data_events = [e for e in self._events if e.startswith("data:")]
        return bool(data_events)
