# KuzuMemory Deep Code Review
**Date:** 2026-03-10
**Scope:** Full codebase — best practices, code reuse, performance, DI, SOA
**Codebase version:** 1.6.42

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Dependency Injection (DI) Patterns](#dependency-injection-di-patterns)
4. [Service-Oriented Architecture (SOA) Compliance](#service-oriented-architecture-soa-compliance)
5. [Code Duplication and Reuse](#code-duplication-and-reuse)
6. [Error Handling Patterns](#error-handling-patterns)
7. [Type Annotations](#type-annotations)
8. [Performance Patterns](#performance-patterns)
9. [Context Manager Usage](#context-manager-usage)
10. [Testing Patterns](#testing-patterns)
11. [Technology & Configuration](#technology--configuration)
12. [Critical Findings Summary](#critical-findings-summary)
13. [Recommendations by Priority](#recommendations-by-priority)

---

## Executive Summary

KuzuMemory is a mature, well-structured codebase with a thoughtfully designed SOA/DI architecture documented through epic references (1M-415). The architecture shows clear intent and has made real progress, but the migration is visibly incomplete: a significant portion of CLI commands still bypass the service layer and instantiate `KuzuMemory` directly. This creates a two-tier system that undermines the SOA guarantees the architecture is working toward.

Key strengths: strong `BaseService` lifecycle pattern, `Protocol`-based interfaces, well-formed `DependencyContainer`, and excellent test coverage structure. Key weaknesses: SOA bypass in CLI commands, `limit=10000`/`100000` unbounded-in-practice queries, 582 bare `except Exception` clauses across the codebase, missing exception chaining (B904 suppressed), and a homegrown `cached_method` decorator applied to mutable-input methods.

---

## Architecture Overview

### Module Map

```
src/kuzu_memory/
  core/           - KuzuMemory class, models, config, DI container, validators
  services/       - BaseService + 7 concrete services (SOA layer)
  protocols/      - typing.Protocol interfaces (IMemoryService, etc.)
  cli/            - Click commands (thin wrappers - partially achieved)
  storage/        - MemoryStore, KuzuAdapter, QueryBuilder, cache
  recall/         - RecallCoordinator + recall strategies
  extraction/     - Pattern/entity/relationship extraction
  async_memory/   - BackgroundLearner, QueueManager, StatusReporter
  mcp/            - JSON-RPC 2.0 MCP server + queue processor
  installers/     - BaseInstaller + per-platform adapters
  integrations/   - Auggie, git sync, auto-sync
  caching/        - LRUCache, EmbeddingsCache, MemoryCache
  connection_pool/- KuzuConnectionPool
  monitoring/     - AccessTracker, MetricsCollector, TimingDecorators
  nlp/            - NLP classifier (optional dependency)
  utils/          - project_setup, exceptions, git_user, file_lock, etc.
  migrations/     - versioned schema migrations
```

### Layering Diagram

```
CLI Commands
    |  (should always go through)
ServiceManager -> Services (BaseService subclasses)
    |  (delegate to)
Core (KuzuMemory)
    |  (uses)
Storage Layer (MemoryStore -> QueryBuilder -> KuzuAdapter)
    |
Kuzu DB
```

---

## Dependency Injection (DI) Patterns

### 1. DependencyContainer (core/dependencies.py)

**Pattern:** Manual service-locator with Protocol-typed accessors.

```python
# core/dependencies.py, lines 149-239
class DependencyContainer:
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Any] = {}

    def register(self, name: str, service: Any, singleton: bool = True) -> None: ...
    def get(self, name: str) -> Any: ...
    def has(self, name: str) -> bool: ...

    # Typed accessors
    def get_memory_store(self) -> MemoryStoreProtocol: ...
    def get_recall_coordinator(self) -> RecallCoordinatorProtocol: ...
    def get_database_adapter(self) -> DatabaseAdapterProtocol: ...
```

**Strengths:**
- Clean registration/resolution with singleton support
- Typed accessor methods add type safety over raw `get()`
- `reset_container()` enables clean test isolation (used in conftest.py autouse fixture)

**Issues:**
- Container is a module-level global singleton (`_container = DependencyContainer()`). This means all `KuzuMemory` instances share the same container unless explicitly passed a different one.
- `KuzuMemory.__init__` uses `container or get_container()` — if tests create two `KuzuMemory` instances without resetting, they will share adapters pointing to different `db_path` values. The `conftest.py` autouse `reset_dependency_container` fixture mitigates this for tests, but it is fragile in production multi-instance scenarios.
- Registration is string-keyed (`"memory_store"`, `"database_adapter"`), not type-keyed, losing IDE support and risking typo bugs.

### 2. BaseService + ServiceManager (services/base.py, cli/service_manager.py)

**Pattern:** Abstract lifecycle management via `BaseService`, context-manager factory via `ServiceManager`.

```python
# services/base.py, lines 33-263
class BaseService(ABC):
    def initialize(self) -> None: ...      # idempotent
    def cleanup(self) -> None: ...         # idempotent, swallows cleanup errors
    def __enter__(self) -> Self: ...
    def __exit__(self, ...) -> None: ...
    def _check_initialized(self) -> None: ...

# cli/service_manager.py, lines 49-93
@staticmethod
@contextmanager
def memory_service(db_path, enable_git_sync, config) -> Iterator[IMemoryService]:
    service = MemoryService(...)
    service.initialize()
    try:
        yield service
    finally:
        service.cleanup()
```

**Strengths:**
- `initialize()` is idempotent and guards against double-init
- `cleanup()` swallows exceptions and always sets `_initialized = False` — this is the correct pattern for cleanup
- `Self` return type on `__enter__` is correct Python 3.11+ usage
- `ServiceManager` creates services as needed — simple and effective

**Issues:**
- `ServiceManager.git_sync_service` and `diagnostic_service` contain `type: ignore[assignment]` casts from Protocol to concrete type at lines 143 and 213 respectively. This is a smell: the service constructors require concrete types but accept protocol types at the call site, creating a hidden contract that mypy cannot verify.
- `MemoryService._do_cleanup` calls `self._kuzu_memory.__exit__(None, None, None)` directly (line 128). This works but is unconventional — `__exit__` is not a public API. Prefer calling `self._kuzu_memory.close()`.

### 3. Protocol Interfaces (protocols/services.py)

**Pattern:** `typing.Protocol` for structural subtyping of service interfaces.

```python
# protocols/services.py
class IMemoryService(Protocol):
    def add_memory(...) -> Memory: ...
    def get_memory(...) -> Memory | None: ...
    def list_memories(...) -> list[Memory]: ...
    def remember(...) -> str: ...
    def attach_memories(...) -> MemoryContext: ...
    def get_recent_memories(...) -> list[Memory]: ...
    def get_memory_count(...) -> int: ...
    def get_database_size(...) -> int: ...
```

**Strengths:**
- Protocols enable duck-typing without inheritance — correct choice for DI interfaces
- Good separation from `BaseService` (ABC for concrete impl, Protocol for interface)

**Issues:**
- `MemoryStoreProtocol` in `core/dependencies.py` (line 43) declares `_store_memory_in_database` as an `@abstractmethod` on a Protocol. Private/internal methods should not be part of a public protocol. This leaks implementation detail into the interface contract.
- `RecallCoordinatorProtocol.attach_memories` returns `Any` (line 99) with comment "Returns MemoryContext". The return type should be `MemoryContext` to preserve type safety.

---

## Service-Oriented Architecture (SOA) Compliance

### Compliant Commands (use ServiceManager)

The following CLI commands correctly delegate through `ServiceManager`:

- `memory store` — uses `ServiceManager.memory_service()`
- `init` — uses `ConfigService` + `SetupService` directly (correct multi-service orchestration)
- `doctor diagnose/hooks` — uses `ServiceManager.diagnostic_service()`
- `git sync` — uses `ServiceManager.git_sync_service()`

### SOA Violations (direct KuzuMemory instantiation in CLI)

The following files bypass the service layer by calling `KuzuMemory(...)` directly. This was detected by grep on CLI files:

| File | Line(s) | Context |
|------|---------|---------|
| `cli/project_commands.py` | 76, 179, 249, 296, 414 | `init`, `project`, `status`, `stats`, `cleanup` |
| `cli/memory_commands.py` | 259 | `learn` (fallback path) |
| `cli/hooks_commands.py` | 492, 723, 926, 1156 | `enhance`, session hooks |
| `cli/doctor_commands.py` | 1187 | `auto-tune` subcommand |
| `cli/git_commands.py` | 119 | `git sync` |
| `cli/auggie_cli.py` | 24, 69, 108, 152, 177, 194, 211, 267 | All auggie subcommands |
| `cli/_deprecated/*` | various | (deprecated, lower priority) |

**Most significant violation — `project_commands.py`:**

```python
# cli/project_commands.py, line 76
config = KuzuMemoryConfig()
with KuzuMemory(db_path=db_path, config=config) as memory:
    project_context = get_project_context_summary(project_root)
    memory.remember(context_str, source="project-initialization", ...)
```

This is a medium-complexity init command that should use `ServiceManager.memory_service()`. The direct use means no DI, no service lifecycle logging, and harder testing.

**Most significant violation — `hooks_commands.py`:**

```python
# cli/hooks_commands.py, lines 492-496
memory = KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False)
memory_context = memory.attach_memories(prompt, max_memories=5, strategy=strategy)
memories = memory_context.memories
memory.close()
```

The hooks path has special performance requirements (zero-latency path for Claude Code hooks) so direct instantiation here may be intentional to avoid `ServiceManager` overhead, but it should be documented as a deliberate exception.

**`memory_commands.py` learn fallback:**

```python
# cli/memory_commands.py, lines 258-261
with KuzuMemory(db_path=db_path) as memory:
    memory_id = memory.remember(content, source=source, metadata=parsed_metadata)
```

This is inside an `except ImportError` block as a sync fallback. The fallback is understandable but the primary path should still use `ServiceManager` consistently.

---

## Code Duplication and Reuse

### 1. Duplicate MemoryStore Files

There are two files implementing similar memory store functionality:

- `storage/memory_store.py` — current implementation, coordinates `QueryBuilder` + `MemoryEnhancer`
- `storage/memory_store_backup.py` — backup/legacy implementation, imports from `extraction/` directly

The backup file (30+ lines seen) imports `PatternExtractor`, `EntityExtractor`, `RelationshipDetector`, `DeduplicationEngine` which are not imported by the active `memory_store.py`. This is a dead code risk and creates maintenance confusion about which is canonical.

**Recommendation:** Delete `memory_store_backup.py` or clearly mark it `# DEAD CODE - kept for reference`.

### 2. `cached_method` Decorator (core/memory.py lines 72-138)

A custom caching decorator is defined inline in `core/memory.py`:

```python
def cached_method(maxsize=..., ttl_seconds=...) -> Callable:
    def decorator(func):
        cache: dict[str, R] = {}
        cache_times: dict[str, float] = {}
        # ... LRU eviction + TTL logic
```

This is:
- A reimplementation of functionality already available in `caching/lru_cache.py` and `storage/cache.py`
- Applied to `attach_memories` and `batch_store_memories` — the latter being a **write operation**, where caching is semantically wrong (caching writes returns stale IDs)
- The `cache_key_from_args` function (line 58-69) uses `hashlib.md5()` for internal cache keys — `md5` is fine for non-security use, but the comment in `pyproject.toml` bandit config skips B324 (md5) already

**Issue with caching `batch_store_memories`:**

```python
# core/memory.py, line 730-731
@cached_method(maxsize=MEMORY_BY_ID_CACHE_SIZE * 10, ttl_seconds=MEMORY_BY_ID_CACHE_TTL)
def batch_store_memories(self, memories: list[Memory]) -> list[str]:
```

Caching a storage (write) operation is a logic error. If `memories` is a list, the cache key is based on `str(arg)` of the list, meaning the same list content will return cached IDs without actually storing anything. This could silently drop data.

**Recommendation:** Remove `@cached_method` from `batch_store_memories`. Use the existing `LRUCache` in `caching/lru_cache.py` for read-side caching.

### 3. Repeated `uuid` Import at Function Scope

```python
# core/memory.py, line 489
import uuid   # inside KuzuMemory.remember()

# core/models.py, line 113
id: str = Field(default_factory=lambda: str(uuid4()), ...)  # uses module-level uuid4
```

`uuid` is imported at function scope in `remember()` rather than at module level. This is a minor style inconsistency — move it to the top of the file alongside `hashlib`, `time`, etc.

### 4. `list_memories` Pagination Anti-Pattern (services/memory_service.py lines 401-439)

```python
def list_memories(self, memory_type=None, limit=100, offset=0) -> list[Memory]:
    all_memories = self.kuzu_memory.memory_store.get_recent_memories(
        limit=10000  # Large limit to get all memories
    )
    # Apply filters manually
    if memory_type:
        all_memories = [m for m in all_memories if m.memory_type == memory_type]
    # Apply pagination
    return all_memories[start:end]
```

This loads up to 10,000 memories into Python memory to simulate pagination. This should be pushed down into a `MATCH ... WHERE ... SKIP $offset LIMIT $limit` Cypher query. Same pattern appears in `cleanup_commands.py` with `limit=100000`.

### 5. Repeated `db_path` Resolution Logic

Multiple CLI commands independently call `get_project_db_path()` or check `ctx.obj["db_path"]`:

```python
# analytics_commands.py, lines 63-71
if db_path:
    db_path_obj = Path(db_path)
else:
    if not ctx.obj or "db_path" not in ctx.obj:
        rich_print("❌ No database path configured")
        sys.exit(1)
    db_path_obj = ctx.obj["db_path"]
```

This pattern is repeated in `analytics_commands.py`, `status_commands.py`, `doctor_commands.py`, and others. A shared utility function like `resolve_db_path(db_path_str, ctx)` would eliminate this repetition.

---

## Error Handling Patterns

### 1. Bare `except Exception` (582 occurrences across 105 files)

The codebase has 582 bare `except Exception` catches. While many are correct (e.g., `BaseService.cleanup()` deliberately swallows exceptions), many others suppress legitimate errors:

```python
# services/memory_service.py, lines 459-468
def delete_memory(self, memory_id: str) -> bool:
    try:
        memory_store = cast(MemoryStore, self.kuzu_memory.memory_store)
        return memory_store.delete_memory(memory_id)
    except Exception:       # <-- no logging, returns False silently
        return False
```

This silently returns `False` without logging the error or its type. Callers cannot distinguish "not found" from "database error."

```python
# core/memory.py, lines 514-519
try:
    self.memory_store._store_memory_in_database(memory)
    return memory.id
except Exception as e:
    logger.error(f"Failed to store memory: {e}")
    return ""           # <-- empty string as error sentinel
```

Returning `""` instead of raising is a silent failure. The caller (`MemoryService.remember()`) propagates the empty string back to the CLI which then prints it as a memory ID.

### 2. Missing Exception Chaining (B904 suppressed)

`pyproject.toml` line 209 explicitly suppresses `B904`:
```toml
"B904",  # exception chaining - requires extensive refactoring
```

This means code like this is permitted:
```python
except Exception as e:
    raise DatabaseError(f"Failed to ...: {e}")  # loses original traceback
```

The correct form is `raise DatabaseError(...) from e`. The suppression is acknowledged as "requires extensive refactoring" — this should be a tracked backlog item.

### 3. Inconsistent Exception Hierarchy

Custom exceptions are defined in `utils/exceptions.py`:
- `KuzuMemoryError` (base)
- `DatabaseError`, `ValidationError`, `ConfigurationError`
- `PerformanceError`, `PerformanceThresholdError`
- `ExtractionError`, `DatabaseLockError`, `CorruptedDatabaseError`

But the `backup/memory_store_backup.py` also imports `PerformanceThresholdError` (a different exception) while `memory_store.py` uses `PerformanceError`. Callers cannot reliably `except PerformanceError` and catch all performance issues.

### 4. `ValidationError` in `core/memory.py`

```python
# core/memory.py, line 560-561
if len(content) > 100000:
    raise ValidationError("Content exceeds maximum length", "content", content[:100])
```

The `ValidationError` constructor signature here is `(message, field_name, value)` but Pydantic's `ValidationError` has a different signature. This is a custom exception but the argument order is inconsistent with how it's raised elsewhere:

```python
# core/memory.py, line 412-415
if strategy not in [...]:
    raise ValidationError(
        "strategy", strategy, "must be one of: auto, keyword, entity, temporal"
    )
```

The argument order differs between these two call sites (`message, field, value` vs `field, value, message`). This should be standardized.

---

## Type Annotations

### 1. `type: ignore` Usage (57 occurrences across 22 files)

Common patterns:

```python
# core/memory.py
return context  # type: ignore[no-any-return]
return memory_ids  # type: ignore

# cli/service_manager.py, lines 143, 213
concrete_config = config_service  # type: ignore[assignment]
concrete_memory = memory_service  # type: ignore[assignment]
```

The `service_manager.py` ignores reflect a real design tension: `ServiceManager` accepts Protocol types but passes them to constructors that need concrete types. This should be resolved by either accepting concrete types at the `ServiceManager` level or by providing protocol-compatible constructors.

### 2. `Any` in Protocol Return Types

```python
# core/dependencies.py, line 99
def attach_memories(self, ...) -> Any:  # Returns MemoryContext
```

The comment documents what the type should be. Change to `MemoryContext` and import it.

### 3. `mypy` Excludes Migrations and Deprecated

```toml
# pyproject.toml, lines 139-142
exclude = [
    "src/kuzu_memory/cli/_deprecated/.*\\.py$",
    "src/kuzu_memory/migrations/.*\\.py$",
]
```

Excluding deprecated code from mypy is reasonable, but excluding migrations means migration bugs can cause runtime type errors. Migrations should at minimum have basic type annotations.

### 4. `KuzuMemory` Class-Level Attribute Declarations Without Init

```python
# core/memory.py, lines 149-163
class KuzuMemory:
    db_path: Path
    config: KuzuMemoryConfig
    container: DependencyContainer
    db_adapter: DatabaseAdapterProtocol
    ...
```

These are declared at class level but assigned in `__init__` (partially via `_initialize_components`). Mypy will not flag access before assignment in all cases. `auto_git_sync` is declared as `Any | None` but set in `_initialize_git_sync` via `self.auto_git_sync = None` in the else branch — this is fine but uses `hasattr` checks later (`if not hasattr(self, "auto_git_sync") or self.auto_git_sync is None`), which suggests incomplete initialization tracking.

---

## Performance Patterns

### 1. `attach_memories` Cache Key Ignores `self`

```python
# core/memory.py, lines 58-69
def cache_key_from_args(*args, **kwargs) -> str:
    for arg in args:
        if hasattr(arg, "__dict__"):
            continue  # Skip self/cls arguments
```

Skipping `self` means all `KuzuMemory` instances share the same in-closure cache dictionary for `attach_memories`. In a scenario with multiple `KuzuMemory` instances pointing to different databases (e.g., multi-project use), instance A could return cached results from instance B's database.

The cache is defined in the closure per-decorator-application, so it is per-method but not per-instance. This is a correctness bug in multi-instance scenarios.

### 2. `list_memories` loads 10,000 rows (memory_service.py line 429)

```python
all_memories = self.kuzu_memory.memory_store.get_recent_memories(limit=10000)
```

This should be a database-level paginated query. 10,000 `Memory` objects each with embedded JSON fields can easily consume hundreds of MB.

### 3. `cleanup_commands.py` loads 100,000 rows

```python
# cli/cleanup_commands.py, lines 292, 757
all_memories = mem_service.get_recent_memories(limit=100000)
```

Same pattern, worse magnitude. This is a memory exhaustion risk for large databases.

### 4. `get_daily_activity_stats` Placeholder

```python
# core/memory.py, lines 708-711
def get_daily_activity_stats(self, days: int = 7) -> dict[str, int]:
    """Get daily activity statistics (placeholder)."""
    recent_count = len(self.get_recent_memories(limit=days * 10))
    return {"recent_days": recent_count}
```

This is a placeholder that returns wrong semantics (`days * 10` memories is not daily activity), and it loads memories into memory just to count them. Both `get_daily_activity_stats` and `get_average_memory_length` are documented as placeholders — they should either be properly implemented or removed to avoid misleading callers.

### 5. Connection Pool Thread Safety

```python
# storage/kuzu_adapter.py, lines 62-99
class KuzuConnectionPool:
    def __init__(self, db_path, pool_size=5):
        self._pool: Queue[Any] = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._initialized = False
        self._database: Any = None
```

The `_database` creation in `_create_connection` (line 90):
```python
if self._database is None:
    self._database = kuzu.Database(str(self.db_path))
```

This is a classic TOCTOU race: two threads could both see `_database is None` and create two `kuzu.Database` instances. The `_lock` is defined but not used around this check. The check should be inside `with self._lock:`.

### 6. `HookQueueProcessor` Uses `/tmp` Hardcoded Path

```python
# mcp/queue_processor.py, line 27
def __init__(self, queue_dir: str = "/tmp/kuzu-memory-queue") -> None:
```

Hardcoded `/tmp` path: not portable to Windows, and shared across users on multi-user systems. Should use `tempfile.gettempdir()` or an app-specific user directory.

---

## Context Manager Usage

### 1. Correct Pattern (ServiceManager)

```python
# cli/service_manager.py
@contextmanager
def memory_service(...) -> Iterator[IMemoryService]:
    service = MemoryService(...)
    service.initialize()
    try:
        yield service
    finally:
        service.cleanup()
```

This is the correct pattern. Cleanup is guaranteed even on exceptions.

### 2. Antipattern — Manual `__exit__` Call

```python
# services/memory_service.py, lines 111, 128
self._kuzu_memory.__enter__()
...
self._kuzu_memory.__exit__(None, None, None)
```

Calling `__enter__`/`__exit__` directly is fragile and bypasses Python's exception handling machinery. If `_do_initialize` raises after `__enter__`, the `__exit__` won't be called automatically. The correct approach is:

```python
self._kuzu_memory = KuzuMemory(...)
# Don't call __enter__; track it manually and call close() in _do_cleanup
```

Or alternatively use a `contextlib.ExitStack`:
```python
self._exit_stack = contextlib.ExitStack()
self._kuzu_memory = self._exit_stack.enter_context(KuzuMemory(...))
```

### 3. `KuzuMemory.close()` vs `__exit__`

`KuzuMemory.__exit__` calls `self.close()` (line 968), but `close()` only closes `db_adapter`. There is no cleanup of background tasks, caches, or git sync objects in `close()`. If `KuzuMemory` is used as a context manager, exit will be incomplete.

---

## Testing Patterns

### 1. Test Organization — Strong

```
tests/
  unit/services/       - MemoryService, BaseService, ConfigService, etc.
  unit/cli/            - ServiceManager, async_utils, setup_commands
  unit/core/           - (present but sparse)
  integration/         - kuzu_memory, git_sync, MCP installation
  mcp/                 - compliance, performance, e2e, integration
  benchmarks/          - performance benchmarks
  e2e/                 - complete workflow tests
```

This is excellent structure. The test tree mirrors the source tree and separates concerns clearly.

### 2. conftest.py `reset_dependency_container` — Critical Fix

```python
# tests/conftest.py, lines 27-39
@pytest.fixture(autouse=True)
def reset_dependency_container():
    reset_container()
    yield
    reset_container()
```

This is a necessary mitigation for the global container singleton. It's correctly marked `autouse=True`. Without this, tests that create `KuzuMemory` instances would share the container and could see stale adapters.

### 3. MemoryService Test Pattern — Good

```python
# tests/unit/services/test_memory_service.py, lines 28-52
@pytest.fixture
def mock_kuzu_memory(mock_memory_store):
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    mock.memory_store = mock_memory_store
    return mock

@pytest.fixture
def memory_service(mock_kuzu_memory):
    with patch("kuzu_memory.services.memory_service.KuzuMemory", ...):
        service = MemoryService(db_path=Path("/tmp/test.db"))
        service.initialize()
        yield service
        service.cleanup()
```

Correctly patches `KuzuMemory` at the import site of the module under test. Proper fixture teardown. This is the correct pattern for unit testing with mocks.

### 4. Missing Tests

Observed gaps:
- No unit tests for `cached_method` decorator behavior
- No tests for `DependencyContainer` multi-instance isolation (the shared-container bug)
- No tests for `KuzuConnectionPool` thread safety
- `cli/hooks_commands.py` has minimal unit test coverage (hooks are integration-tested)
- `storage/memory_store_backup.py` appears untested

---

## Technology & Configuration

### 1. pyproject.toml — Strong Configuration

```toml
[tool.mypy]
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_equality = true
warn_unreachable = true
```

Strict mypy settings are correct for a production library. The exclusion of `_deprecated/` and `migrations/` is acceptable.

### 2. Ruff Suppressed Rules

```toml
ignore = [
    "B904",  # exception chaining - requires extensive refactoring
    "C901",  # too complex
    "RUF006", # store task reference - fire-and-forget tasks are intentional
]
```

- `B904` suppression is a known debt — schedule a cleanup sprint
- `C901` (too complex): suppressing McCabe complexity warnings hides functions that are too long. The `max-complexity = 10` setting is then effectively disabled for all files
- `RUF006`: fire-and-forget asyncio tasks are genuinely intentional in hooks

### 3. `bandit` Skip List

```toml
skips = ["B101", "B108", "B110", "B112", "B310", "B311", "B324", "B404", "B601", "B603", "B607"]
```

`B603` (subprocess without shell=True) and `B607` (start_process_with_partial_path) are skipped. These appear in installer code that runs platform-specific commands. Each should have an inline comment explaining why the skip is safe.

### 4. `setup.py` Missing — Build-System Only

The project uses `setuptools` via `pyproject.toml`. No `setup.py` is present, which is the modern standard. `tomli-w` is a runtime dependency (for TOML writing) — this is unusual and should be reviewed to confirm it cannot be replaced with `tomllib` (stdlib, read-only) plus JSON.

---

## Critical Findings Summary

| Priority | Finding | File | Impact |
|----------|---------|------|--------|
| **P0** | `cached_method` on `batch_store_memories` (write op) | `core/memory.py:730` | Data loss risk — same list returns cached IDs without storing |
| **P0** | Race condition in `KuzuConnectionPool._create_connection` | `storage/kuzu_adapter.py:90` | Double DB initialization under concurrent load |
| **P0** | `attach_memories` cache not instance-scoped | `core/memory.py:58-69` | Cross-instance cache pollution in multi-project use |
| **P1** | SOA bypass: 15+ direct `KuzuMemory()` calls in CLI | `cli/project_commands.py`, `hooks_commands.py`, etc. | Defeats DI/SOA migration goal |
| **P1** | `list_memories` loads 10,000 rows in Python | `services/memory_service.py:429` | Memory exhaustion for large databases |
| **P1** | `cleanup_commands.py` loads 100,000 rows | `cli/cleanup_commands.py:292,757` | Severe memory exhaustion risk |
| **P1** | `delete_memory` silently swallows all exceptions | `services/memory_service.py:459-468` | Silent data operation failures |
| **P1** | `remember()` returns `""` on failure | `core/memory.py:514-519` | Callers cannot detect storage failure |
| **P2** | `_store_memory_in_database` in public Protocol | `core/dependencies.py:43` | Private API in public contract |
| **P2** | `RecallCoordinatorProtocol.attach_memories` returns `Any` | `core/dependencies.py:99` | Lost type safety |
| **P2** | `MemoryService._do_cleanup` calls `__exit__` directly | `services/memory_service.py:128` | Unconventional, fragile teardown |
| **P2** | `uuid` imported at function scope | `core/memory.py:489` | Minor style inconsistency |
| **P2** | `ValidationError` inconsistent arg order | `core/memory.py:412,560` | Confusing API |
| **P2** | `memory_store_backup.py` dead code | `storage/memory_store_backup.py` | Maintenance confusion |
| **P2** | B904 exception chaining suppressed globally | `pyproject.toml:209` | Lost tracebacks in 100+ `raise X from e` patterns |
| **P3** | 582 bare `except Exception` clauses | entire codebase | Difficult debugging |
| **P3** | `/tmp` hardcoded in `HookQueueProcessor` | `mcp/queue_processor.py:27` | Not portable to Windows |
| **P3** | `get_daily_activity_stats` placeholder with wrong semantics | `core/memory.py:708` | Misleading statistics |
| **P3** | String-keyed DI container | `core/dependencies.py:159` | Typo-prone, no IDE completion |

---

## Recommendations by Priority

### P0 — Fix Immediately (correctness/safety)

1. **Remove `@cached_method` from `batch_store_memories`** (`core/memory.py:730`). Write operations must not be cached. Also audit `attach_memories` caching to ensure the cache is instance-scoped.

2. **Fix `KuzuConnectionPool._create_connection` race condition** (`storage/kuzu_adapter.py:88-91`). Wrap `if self._database is None:` inside `with self._lock:`.

3. **Scope `cached_method` cache to `self`** by including `id(self)` in the cache key, or replace the custom decorator with per-instance `LRUCache` initialized in `__init__`.

### P1 — Fix in Next Sprint (reliability/scalability)

4. **Complete SOA migration for `project_commands.py`** — replace the 5 direct `KuzuMemory()` calls with `ServiceManager.memory_service()`. Explicitly document `hooks_commands.py` as a deliberate performance exception.

5. **Implement database-level pagination in `list_memories`** — add `SKIP $offset LIMIT $limit` to the Cypher query in `QueryBuilder`. Remove `limit=10000` and `limit=100000` workarounds.

6. **Make `delete_memory` raise or log properly** — at minimum log the exception type and message. Consider returning a typed result instead of `bool`.

7. **Make `remember()` raise on empty string return** — or change the signature to return `str | None` and have callers check for `None`.

### P2 — Fix in Near Term (architecture hygiene)

8. **Remove `_store_memory_in_database` from `MemoryStoreProtocol`** — keep private methods out of public protocols.

9. **Fix `RecallCoordinatorProtocol.attach_memories` return type** from `Any` to `MemoryContext`.

10. **Replace `__exit__` direct call in `MemoryService._do_cleanup`** with `self._kuzu_memory.close()`.

11. **Standardize `ValidationError` constructor call signature** across all call sites.

12. **Delete or clearly mark `memory_store_backup.py`** as dead code.

13. **Create `resolve_db_path(db_path_str, ctx)` utility** to eliminate the repeated `ctx.obj["db_path"]` resolution pattern.

14. **Add `# noqa: B603` inline comments** in installer code with explanation, rather than blanket `pyproject.toml` skips.

### P3 — Address in Backlog

15. **Schedule B904 exception chaining cleanup sprint** — add `from e` to all `raise X(...)` in `except` blocks.

16. **Replace `/tmp` with `tempfile.gettempdir()`** in `HookQueueProcessor`.

17. **Implement or remove placeholder analytics methods** (`get_daily_activity_stats`, `get_average_memory_length`, `get_oldest_memory_date`).

18. **Consider type-keyed DI container** using `type[T]` keys instead of string keys for better IDE support.

19. **Add unit test for `DependencyContainer` multi-instance isolation**.

20. **Add unit test for `cached_method` correctness** including TTL expiration and LRU eviction.

---

## File Reference Index

| File | Key Finding |
|------|-------------|
| `src/kuzu_memory/core/memory.py` | `cached_method` applied to write op (L730); cache key not instance-scoped (L58); `uuid` import at function scope (L489); `remember()` returns `""` on failure (L519) |
| `src/kuzu_memory/core/dependencies.py` | `_store_memory_in_database` in Protocol (L43); `attach_memories` returns `Any` (L99); global container singleton (L228) |
| `src/kuzu_memory/services/memory_service.py` | `list_memories` loads 10K rows (L429); `delete_memory` silently swallows exceptions (L459-468); `__exit__` called directly (L128) |
| `src/kuzu_memory/cli/service_manager.py` | `type: ignore` casts (L143, L213); correct context-manager pattern |
| `src/kuzu_memory/cli/project_commands.py` | SOA violations at L76, 179, 249, 296, 414 |
| `src/kuzu_memory/cli/hooks_commands.py` | Direct `KuzuMemory()` at L492, 723, 926, 1156 (may be intentional) |
| `src/kuzu_memory/cli/cleanup_commands.py` | `limit=100000` (L292, 757) |
| `src/kuzu_memory/cli/doctor_commands.py` | Direct `KuzuMemory()` at L1187 |
| `src/kuzu_memory/storage/kuzu_adapter.py` | Connection pool TOCTOU race (L90) |
| `src/kuzu_memory/storage/memory_store_backup.py` | Dead code / legacy file |
| `src/kuzu_memory/mcp/queue_processor.py` | Hardcoded `/tmp` (L27) |
| `src/kuzu_memory/services/base.py` | Well-implemented lifecycle pattern (reference implementation) |
| `src/kuzu_memory/protocols/services.py` | Well-structured Protocol interfaces |
| `src/kuzu_memory/core/models.py` | Strong Pydantic v2 usage, good validators |
| `tests/conftest.py` | Correct `reset_dependency_container` autouse fixture |
| `tests/unit/services/test_memory_service.py` | Correct mock/patch pattern for service tests |
| `pyproject.toml` | B904 suppressed (L209); strict mypy settings (L125-142) |

---

*Generated by Research Agent. Saved to `docs/research/code-review-2026-03-10.md`.*
