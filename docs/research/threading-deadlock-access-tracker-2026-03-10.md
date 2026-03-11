# Threading Deadlock: AccessTracker + KuzuConnectionPool

**Date**: 2026-03-10
**Severity**: Critical (blocks release test gate)
**Status**: Analyzed, fix identified

---

## Summary

`pytest tests/unit/` hangs indefinitely during test teardown due to a classic
lock re-entrancy deadlock between the `AccessTracker` background worker thread
and the `KuzuConnectionPool` initialization lock.

---

## 1. Exact Deadlock

### Thread A — Main test thread (pytest teardown / `tracker.shutdown()`)

| Step | Location | Action |
|------|----------|--------|
| 1 | `access_tracker.py:286` | calls `self._worker_thread.join(timeout=10.0)` |
| 2 | (blocked) | **waits** for Thread B to exit |

Thread A holds nothing — but it is _waiting_ for Thread B to finish before it
can release the pytest fixture and allow any subsequent teardown steps.

### Thread B — AccessTracker background worker thread (`_worker_loop`)

| Step | Location | Action |
|------|----------|--------|
| 1 | `access_tracker.py:111` | calls `self._write_batch(pending_events)` |
| 2 | `access_tracker.py:161` | creates a fresh `KuzuAdapter(self.db_path, config)` |
| 3 | `access_tracker.py:174` | calls `adapter.initialize()` → `pool.initialize()` |
| 4 | `kuzu_adapter.py:107` | **acquires `KuzuConnectionPool._lock`** (outer) |
| 5 | `kuzu_adapter.py:114` | inside `initialize()`, calls `self._create_connection()` |
| 6 | `kuzu_adapter.py:93`  | **tries to acquire `KuzuConnectionPool._lock` again** (inner) |
| 7 | (deadlock) | **`_lock` is non-reentrant (`threading.Lock`), so Thread B blocks on itself** |

Thread B is permanently blocked waiting for a lock it already holds.
Thread A is permanently blocked waiting for Thread B to finish.
Neither can proceed.

### The re-entrant lock call chain (exact lines)

```
kuzu_adapter.py:107  KuzuConnectionPool.initialize()
                         with self._lock:           <-- acquires _lock
kuzu_adapter.py:114          conn = self._create_connection()
kuzu_adapter.py:93               with self._lock:   <-- tries to re-acquire _lock
                                     DEADLOCK
```

`threading.Lock` is **not** reentrant. The second `with self._lock:` inside
`_create_connection()` blocks forever waiting for `initialize()` to release it,
which never happens because `initialize()` is waiting for `_create_connection()`
to return.

---

## 2. Root Cause

Two independent design decisions combined to produce the deadlock:

**Decision 1 — Lock is used at both the outer and inner level of the same call
path.**
`initialize()` acquires `_lock` at line 107, then calls `_create_connection()`
at line 114, which also acquires `_lock` at line 93. The comment on line 90
explains the intent (prevent TOCTOU on `_database`), but the author did not
notice that `initialize()` already holds the lock before calling
`_create_connection()`.

**Decision 2 — The AccessTracker background worker creates a brand-new
`KuzuAdapter` on every batch write.**
`_write_batch()` (line 161) calls `KuzuAdapter(self.db_path, config)` and then
`adapter.initialize()` every time it writes a batch. This means the
initialization code path (and its nested lock acquisition) is exercised
repeatedly from a daemon background thread that is completely separate from any
test-controlled lifecycle.

**Decision 3 — Global singleton tracker with a daemon thread that is never
registered for cleanup.**
`get_access_tracker()` stores trackers in a module-level dict `_trackers`
guarded by `_trackers_lock`. Tests that call `tracker.shutdown()` explicitly
are fine, but any code path that obtains a tracker via `get_access_tracker()`
(recall coordinator, MCP server, diagnostic service) leaves the daemon running
across test boundaries. The `reset_dependency_container()` fixture in
`conftest.py` resets the DI container but does NOT flush `_trackers`, so old
background threads accumulate and race with new test teardown.

---

## 3. Lock Inventory

### `access_tracker.py`

| Symbol | Type | Line | Protects |
|--------|------|------|----------|
| `_trackers_lock` | `threading.Lock` | 31 | module-level `_trackers` dict |
| `self._stats_lock` | `threading.Lock` | 81 | `self._stats` dict |
| `self._shutdown_event` | `threading.Event` | 70 | worker loop exit signal |
| `self._worker_thread` | `threading.Thread` | 69 | (daemon=True) |

### `kuzu_adapter.py` (`KuzuConnectionPool`)

| Symbol | Type | Line | Protects |
|--------|------|------|----------|
| `self._lock` | `threading.Lock` | 79 | `_initialized`, `_database`, pool drain in `close()` |
| `self._pool` | `Queue` | 78 | connection objects (thread-safe by design) |

### Acquisition order that causes deadlock

```
Thread B:
  KuzuConnectionPool._lock  (line 107, initialize)
    -> KuzuConnectionPool._lock  (line 93, _create_connection)  *** DEADLOCK ***
```

---

## 4. Minimal Fix

**Make `KuzuConnectionPool._lock` reentrant (`threading.RLock`).**

File: `src/kuzu_memory/storage/kuzu_adapter.py`, line 79.

```python
# Before
self._lock = threading.Lock()

# After
self._lock = threading.RLock()
```

`threading.RLock` (reentrant lock) allows the same thread to acquire it
multiple times. `initialize()` acquires it at line 107; `_create_connection()`
re-acquires it at line 93 from within the same thread — this succeeds with
`RLock`, and both `with` blocks release cleanly in reverse order.

This is a one-line change with no behavior change for any caller that does not
re-enter the lock.

---

## 5. Better Long-Term Fix

The minimal fix cures the symptom. The underlying architecture has three
structural problems that should be addressed:

### Fix A — Remove the nested lock in `_create_connection()`

`_create_connection()` is only ever called from `initialize()` (which already
holds `_lock`) and from the `finally` block in `get_connection()` (which does
NOT hold `_lock`). The safest structural fix is to split the concern:

```python
def _create_connection(self) -> Any:
    """Create connection using already-initialized shared database."""
    # Caller is responsible for ensuring _database is initialized.
    self.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = kuzu.Connection(self._database)
    return connection

def _ensure_database(self) -> None:
    """Initialize shared database object if not already done (caller holds _lock)."""
    if self._database is None:
        self._database = kuzu.Database(str(self.db_path))
```

Then `initialize()` calls `_ensure_database()` (under the lock) and
`_create_connection()` (lock not needed). This makes the locking invariants
explicit and eliminates the re-entrancy requirement entirely.

### Fix B — Stop creating a new KuzuAdapter per batch write

`_write_batch()` in `access_tracker.py` (lines 157-198) creates a new
`KuzuAdapter` + calls `adapter.initialize()` on every batch. This is both
wasteful and the trigger for the nested-lock path. The `AccessTracker` should
accept a pre-initialized adapter (or a connection factory callback) at
construction time:

```python
class AccessTracker:
    def __init__(self, db_path: Path, adapter: KuzuAdapter | None = None, ...):
        self._adapter = adapter  # shared, pre-initialized
```

If `adapter` is provided, `_write_batch()` uses it directly without calling
`initialize()` again.

### Fix C — Register singleton trackers for test cleanup

Add a teardown hook in `conftest.py` that clears `_trackers` between tests to
prevent stale background threads from leaking across test boundaries:

```python
# tests/conftest.py
import kuzu_memory.monitoring.access_tracker as _at

@pytest.fixture(autouse=True)
def reset_access_trackers():
    yield
    with _at._trackers_lock:
        for tracker in _at._trackers.values():
            tracker.shutdown()
        _at._trackers.clear()
```

This is defensive: even with the RLock fix in place, accumulated daemon threads
that hold open database connections across tests can cause other intermittent
failures.

---

## 6. Affected Files and Line Numbers

| File | Lines | Issue |
|------|-------|-------|
| `src/kuzu_memory/storage/kuzu_adapter.py` | 79 | `threading.Lock()` must become `threading.RLock()` |
| `src/kuzu_memory/storage/kuzu_adapter.py` | 107 | `initialize()` acquires `_lock` (outer) |
| `src/kuzu_memory/storage/kuzu_adapter.py` | 93 | `_create_connection()` re-acquires `_lock` (inner — causes deadlock) |
| `src/kuzu_memory/monitoring/access_tracker.py` | 157-174 | `_write_batch()` creates new adapter and calls `initialize()` every batch |
| `src/kuzu_memory/monitoring/access_tracker.py` | 285-286 | `shutdown()` calls `join()` waiting for worker that is stuck in deadlock |
| `tests/conftest.py` | 27-39 | `reset_dependency_container` does not clear `_trackers` singleton |

---

## 7. Verification

After applying the `RLock` fix, confirm with:

```bash
cd /Users/masa/Projects/kuzu-memory
uv run pytest tests/unit/test_access_tracker.py -v --timeout=30
uv run pytest tests/unit/ -x -q --tb=short --timeout=60
```

Both commands should complete and return, rather than hanging indefinitely.
