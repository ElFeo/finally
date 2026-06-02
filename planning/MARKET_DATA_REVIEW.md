# Market Data Backend — Code Review

**Reviewed:** `backend/app/market/` (8 modules, ~500 LOC)
**Tests run:** 73 tests, all passing
**Coverage:** 91% overall; stream.py 33% (see §4)
**Linting:** ruff — all checks passed

---

## Test Results

```
============================= test session info ==============================
platform linux, Python 3.12.3, pytest 9.0.2, pytest-asyncio 1.3.0
73 passed in 2.07s

Module                         Stmts   Miss  Cover
--------------------------------------------------
app/market/__init__.py             6      0   100%
app/market/cache.py               39      0   100%
app/market/factory.py             15      0   100%
app/market/interface.py           13      0   100%
app/market/massive_client.py      67      4    94%
app/market/models.py              26      0   100%
app/market/seed_prices.py          8      0   100%
app/market/simulator.py          139      3    98%
app/market/stream.py              36     24    33%
--------------------------------------------------
TOTAL                            349     31    91%
```

All 73 tests pass. The low coverage on `stream.py` is because there is no `test_stream.py` — the SSE endpoint logic (lines 26–87) is completely untested.

---

## Architecture Assessment

The implementation faithfully follows the design: strategy pattern (ABC), shared `PriceCache` as the single point of truth, `asyncio.to_thread()` for the synchronous Massive SDK call, version counter for SSE change detection. The code is clean, well-structured, and easy to follow. Linting passes with zero warnings.

The seven issues below range from real bugs to cleanup items. They are ranked by severity.

---

## Findings

### 1. CRITICAL — `MassiveDataSource` likely never updates the cache in production

**File:** `app/market/massive_client.py`, lines 101–104  
**Severity:** Critical (Massive integration is silently broken)

```python
for snap in snapshots:
    try:
        price = snap.last_trade.price
        ts = snap.last_trade.timestamp / 1000.0     # ← .timestamp may not exist
        self._cache.update(ticker=snap.ticker, price=price, timestamp=ts)
    except (AttributeError, TypeError) as e:
        logger.warning("Skipping snapshot for %s: %s", ...)  # silently swallows
```

The Massive (Polygon.io) Python SDK's `LastTrade` model from the snapshot endpoint exposes the SIP timestamp as **`sip_timestamp`** (nanoseconds), not as `.timestamp`. If this is the case, accessing `snap.last_trade.timestamp` raises `AttributeError` for every ticker, which is caught by the broad `except (AttributeError, TypeError)` handler. Every ticker is then silently skipped with a warning, and the cache is never updated — the MassiveDataSource polls successfully but produces zero cache writes.

The tests do not catch this because they use `MagicMock()`, which auto-creates `.timestamp` as a mock attribute for any attribute access. There is no test that instantiates a real Massive SDK response object.

Additionally, if the field name is `sip_timestamp`, the unit is **nanoseconds** (not milliseconds). Dividing nanoseconds by `1000.0` gives microseconds (~1.78e15), not Unix seconds (~1.78e9). The correct divisor would be `1e9`.

**Action required before using Massive integration:**
1. Verify the correct field name: `python3 -c "from massive.rest.models import LastTrade; help(LastTrade)"` or check the installed SDK source.
2. If `sip_timestamp` is correct, update lines 103–104 to: `ts = snap.last_trade.sip_timestamp / 1e9`
3. Add a real-object integration test (or at minimum, print the actual SDK model in a manual smoke test).

---

### 2. REAL BUG — Falsy timestamp silently ignored in `PriceCache.update()`

**File:** `app/market/cache.py`, line 30  
**Severity:** Low (edge case, but inconsistency with design spec)

```python
ts = timestamp or time.time()
```

The `or` operator treats `timestamp=0.0` as falsy and substitutes `time.time()`. The design doc specifies `timestamp if timestamp is not None else time.time()`. While `timestamp=0.0` (Unix epoch, Jan 1 1970) is an unrealistic market data value, the divergence from the spec is a latent correctness trap and creates an inconsistency: the test `test_custom_timestamp` confirms timestamps work, but it uses `1234567890.0`, not `0.0`.

**Fix:**
```python
ts = time.time() if timestamp is None else timestamp
```

---

### 2. REAL BUG — Module-level `router` singleton accumulates routes on every call to `create_stream_router()`

**File:** `app/market/stream.py`, lines 17–21  
**Severity:** Medium (breaks any test or code that calls the factory more than once)

```python
router = APIRouter(prefix="/api/stream", tags=["streaming"])  # module-level singleton

def create_stream_router(price_cache: PriceCache) -> APIRouter:
    @router.get("/prices")          # ← decorates the singleton each call
    async def stream_prices(...): ...
    return router
```

The factory pattern is documented as preventing "the latent footgun of registering routes twice on a module-level singleton during tests." In fact, the implementation IS that footgun — the `router` is defined at module scope, and every call to `create_stream_router()` registers an additional `/prices` handler on it. A second call (as test fixtures typically do) causes FastAPI to register duplicate routes, leading to routing ambiguity or a startup error.

**Fix:** Move the `APIRouter(...)` instantiation inside the factory:
```python
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/stream", tags=["streaming"])
    @router.get("/prices")
    async def stream_prices(...): ...
    return router
```

---

### 3. REAL BUG — `MassiveDataSource.start()` does not normalize tickers; `add_ticker()`/`remove_ticker()` do

**File:** `app/market/massive_client.py`, line 43  
**Severity:** Medium (produces duplicate cache entries and prevents ticker removal)

```python
async def start(self, tickers: list[str]) -> None:
    self._tickers = list(tickers)            # no normalization

async def add_ticker(self, ticker: str) -> None:
    ticker = ticker.upper().strip()          # normalizes
    if ticker not in self._tickers: ...

async def remove_ticker(self, ticker: str) -> None:
    ticker = ticker.upper().strip()          # normalizes
    self._tickers = [t for t in ...]
```

If the FastAPI app boots the watchlist from the database with lowercase or mixed-case tickers (e.g. `["aapl", "googl"]`), `start()` stores them as-is. A subsequent `add_ticker("AAPL")` normalizes to `"AAPL"`, doesn't find `"aapl"` in the list, and appends a duplicate. `remove_ticker("AAPL")` removes `"AAPL"` but leaves `"aapl"` behind, leaking stale cache entries and duplicate API calls to Massive.

`SimulatorDataSource` has no normalization at all; the problem there depends entirely on callers passing consistent case.

**Fix:** Normalize in `start()`:
```python
self._tickers = [t.upper().strip() for t in tickers]
```
And document in `MarketDataSource.start()` that callers should pass uppercase tickers, or add normalization to the abstract base class.

---

### 4. REAL BUG — `np.linalg.cholesky()` unguarded; a non-positive-definite correlation matrix crashes `add_ticker()` / `remove_ticker()`

**File:** `app/market/simulator.py`, line 172  
**Severity:** Medium (silent crash when user adds certain ticker combinations)

```python
def _rebuild_cholesky(self) -> None:
    ...
    self._cholesky = np.linalg.cholesky(corr)   # raises LinAlgError if not PSD
```

`np.linalg.cholesky` raises `numpy.linalg.LinAlgError: Matrix is not positive definite` when the correlation matrix is singular or near-singular. This can happen with certain combinations of dynamically-added tickers where all pairwise correlations are equal (e.g., all unknown tickers with `CROSS_GROUP_CORR=0.3`), especially with floating-point accumulation. The exception propagates uncaught through `add_ticker()` and `SimulatorDataSource.add_ticker()`, crashing those callers. The background simulation task itself (`_run_loop`) is isolated by its own `try/except`, but the watchlist API would return a 500 error.

**Fix:** Wrap the decomposition:
```python
try:
    self._cholesky = np.linalg.cholesky(corr)
except np.linalg.LinAlgError:
    logger.warning("Correlation matrix not positive-definite; using identity (no correlation)")
    self._cholesky = np.eye(n)
```

---

### 5. PLAUSIBLE RACE — `self._tickers` mutated by event loop while read by worker thread in `MassiveDataSource`

**File:** `app/market/massive_client.py`, line 127  
**Severity:** Low (hard to trigger, but genuine data race)

```python
async def _poll_once(self) -> None:
    snapshots = await asyncio.to_thread(self._fetch_snapshots)   # runs in a thread

def _fetch_snapshots(self) -> list:
    return self._client.get_snapshot_all(
        ...
        tickers=self._tickers,    # read in the thread (line 127)
    )
```

While `_fetch_snapshots` runs in a worker thread, the asyncio event loop continues processing requests. `remove_ticker()` does `self._tickers = [...]` (a list replacement) and `add_ticker()` does `self._tickers.append(...)`. The thread holds a reference to the old `self._tickers` list if replacement happened, meaning it may poll stale tickers. The `append()` call from a different thread is technically unsafe on CPython without the GIL protecting atomic list operations — though CPython's GIL does protect most list operations, this is an undocumented coincidence rather than a deliberate design choice.

**Fix:** Snapshot the ticker list inside the coroutine before handing off to the thread:
```python
async def _poll_once(self) -> None:
    tickers_snapshot = list(self._tickers)   # copy in the event loop
    snapshots = await asyncio.to_thread(self._fetch_snapshots, tickers_snapshot)

def _fetch_snapshots(self, tickers: list[str]) -> list:
    return self._client.get_snapshot_all(market_type=..., tickers=tickers)
```

---

### 6. CLEANUP — `stream.py` has 0% meaningful test coverage

**File:** `app/market/stream.py`  
**Severity:** Medium (the SSE endpoint is the primary data delivery mechanism to the frontend)

There is no `test_stream.py`. The 33% coverage figure comes from the module being imported by other tests, not from any functional test of the SSE endpoint. Lines 26–48 (the `StreamingResponse` handler) and lines 62–87 (the `_generate_events` generator — including the version-based change detection, disconnection handling, and retry directive) are completely untested.

The design doc (section 13.6) includes a `test_sse_emits_seeded_prices` example, but it was never implemented.

**Action needed:** Add `backend/tests/market/test_stream.py` covering at minimum:
- SSE connection returns `200` with `text/event-stream` content type
- Data event includes seeded prices correctly serialized
- Version-change detection — no event emitted when version unchanged
- Client disconnect exits the generator cleanly

---

### 7. CLEANUP — `version` property read without lock, inconsistent with locked writes

**File:** `app/market/cache.py`, line 65  
**Severity:** Low (safe under CPython's GIL, but inconsistent contract)

```python
@property
def version(self) -> int:
    return self._version   # no lock acquired
```

All writes to `_version` are inside `self._lock`, but this read is not. Under CPython's GIL, reading a Python `int` is atomic and this is effectively safe. However, it violates the class's own locking contract and will silently become a real data race on any non-GIL Python runtime (e.g., free-threaded Python 3.13+). It also means the `version` value read in the SSE loop and the subsequent `get_all()` snapshot are not atomically consistent — a write can land between the two reads, causing one spurious extra SSE emission per cycle (harmless but wasteful).

**Fix:** Either acquire the lock in `version`, or have `get_all()` return the version atomically:
```python
def get_all(self) -> tuple[dict[str, PriceUpdate], int]:
    with self._lock:
        return dict(self._prices), self._version
```

---

### 8. MINOR CLEANUP — Duplicate early-return guard in `_add_ticker_internal()`

**File:** `app/market/simulator.py`, line 146  
**Severity:** Low (no functional impact, but misleads future readers)

`add_ticker()` already guards against duplicates (`if ticker in self._prices: return`) before calling `_add_ticker_internal()`. The internal method repeats the same guard, creating confusion about ownership of the invariant. The constructor loop calls `_add_ticker_internal()` directly with no guarantee against duplicates in the input list — so the internal guard is load-bearing for the constructor but redundant for `add_ticker()`.

**Fix:** Document `_add_ticker_internal()` as unchecked and keep the guard only in the callers that need it.

---

## Summary Table

| # | File | Issue | Type | Severity |
|---|------|-------|------|----------|
| 1 | `massive_client.py:103` | Wrong SDK field name / unit — Massive integration never updates cache | Critical bug | Critical |
| 2 | `cache.py:30` | `timestamp or time.time()` silently drops `timestamp=0.0` | Real bug | Low |
| 3 | `stream.py:17` | Module-level router accumulates duplicate routes | Real bug | Medium |
| 4 | `massive_client.py:43` | `start()` doesn't normalize tickers; `add/remove` do | Real bug | Medium |
| 5 | `simulator.py:172` | `np.linalg.cholesky` unguarded — crashes on non-PSD matrix | Real bug | Medium |
| 6 | `massive_client.py:127` | `_tickers` list read in thread while event loop mutates it | Race (plausible) | Low |
| 7 | `stream.py` | Zero test coverage for the SSE endpoint | Missing tests | Medium |
| 8 | `cache.py:65` | `version` property read without lock | Cleanup | Low |
| 9 | `simulator.py:146` | Duplicate guard in `_add_ticker_internal()` | Cleanup | Low |

---

## Overall Assessment

The market data subsystem is well-designed and well-implemented. The strategy pattern, PriceCache decoupling, and asyncio integration are all correct and idiomatic. The 73-test suite with 91% coverage is solid, and linting is clean.

**Priority fixes before downstream agents build on this code:**

1. **Finding #1 (CRITICAL):** Verify the Massive SDK field name (`last_trade.timestamp` vs `last_trade.sip_timestamp`). If wrong, the entire Massive integration silently produces no data. This must be confirmed with a manual smoke test or SDK introspection before any frontend work that depends on real market data.

2. **Finding #3 (MEDIUM):** The duplicate-route bug in `stream.py` will surface the moment any test calls `create_stream_router()` a second time. Move `APIRouter(...)` inside the factory function.

3. **Finding #4 (MEDIUM):** Ticker normalization mismatch between `start()` and `add/remove_ticker()` in `MassiveDataSource` will cause silent data duplication if the database stores tickers in any case other than uppercase.

4. **Finding #5 (MEDIUM):** Wrap `np.linalg.cholesky()` in a try/except. Users adding unusual tickers will get a 500 error from the watchlist API otherwise.

5. **Finding #7 (MEDIUM):** Add `test_stream.py`. The SSE endpoint is the most-used code path in the whole system and has zero coverage.

Findings #2, #6, #8, #9 are low-priority cleanup items that can wait.
