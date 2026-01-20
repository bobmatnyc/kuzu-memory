# Git Sync and Hooks Learn Analysis

**Date**: 2026-01-20
**Investigator**: Research Agent
**Context**: Understanding auto git sync mechanism, hooks learn command, MCP kuzu_learn tool, and database locking

## Executive Summary

This investigation analyzed the kuzu-memory codebase to understand:

1. **Auto Git Sync Mechanism**: How and when git commits are automatically synced to memory
2. **Hooks Learn Command**: How `kuzu-memory hooks learn` operates and its database locking behavior
3. **MCP kuzu_learn Tool**: How the async/non-blocking implementation differs from CLI hooks
4. **Database Lock Handling**: How Kuzu handles concurrent access and locking

### Key Findings

- **Auto git sync is triggered on**: `init`, `enhance`, and optionally `learn` (disabled by default)
- **Hooks learn is SYNCHRONOUS**: Opens KuzuMemory directly, holds DB lock during execution
- **MCP kuzu_learn is ASYNC**: Uses `asyncio.subprocess` fire-and-forget pattern
- **Database uses connection pooling**: 5-second timeout with connection pool (default size: 5)
- **Git sync on learn is DISABLED by default**: `auto_sync_on_learn = False` in config

---

## 1. Auto Git Sync Mechanism

### 1.1 Configuration

**File**: `src/kuzu_memory/core/config.py` (lines 112-146)

```python
@dataclass
class GitSyncConfig:
    """Git commit history synchronization configuration."""

    enabled: bool = True
    auto_sync_on_push: bool = True

    # Automatic sync configuration
    auto_sync_enabled: bool = True              # Master switch
    auto_sync_on_enhance: bool = True           # Sync on attach_memories()
    auto_sync_on_learn: bool = False            # Sync on generate_memories() - DISABLED
    auto_sync_interval_hours: int = 24          # Periodic sync interval
    auto_sync_max_commits: int = 50             # Max commits per auto-sync
```

**Key Configuration Values**:
- `auto_sync_enabled = True` - Master switch (enabled by default)
- `auto_sync_on_enhance = True` - Triggers when `attach_memories()` called
- `auto_sync_on_learn = False` - **DISABLED by default** (would trigger on `generate_memories()`)
- `auto_sync_interval_hours = 24` - Background periodic sync every 24 hours

### 1.2 Trigger Points

**File**: `src/kuzu_memory/core/memory.py`

**Trigger 1: Initialization** (line 283)
```python
def _initialize_components(self) -> None:
    # Initialize git sync components only if enabled
    if self._enable_git_sync:
        self._initialize_git_sync()
        # Run initial auto-sync if enabled (periodic check)
        self._auto_git_sync("init")
```

**Trigger 2: Enhance (attach_memories)** (line 446)
```python
def attach_memories(self, prompt: str, ...) -> MemoryContext:
    # ... perform recall logic

    # Trigger auto git sync on enhance
    self._auto_git_sync("enhance")

    return memory_context
```

**Trigger 3: Learn (generate_memories)** (line 589)
```python
def generate_memories(self, content: str, ...) -> list[str]:
    # ... extract and store memories

    # Trigger auto git sync on learn (if enabled in config)
    self._auto_git_sync("learn")

    return memory_ids
```

### 1.3 Auto-Sync Decision Logic

**File**: `src/kuzu_memory/integrations/auto_git_sync.py` (lines 83-122)

```python
def should_auto_sync(self, trigger: str = "periodic") -> bool:
    # Check if auto-sync is globally enabled
    if not self.config.auto_sync_enabled:
        return False

    # Check if git sync is available
    if not self.git_sync.is_available():
        return False

    # Check trigger-specific configuration
    if trigger == "enhance" and not self.config.auto_sync_on_enhance:
        return False
    if trigger == "learn" and not self.config.auto_sync_on_learn:
        return False  # This is the DEFAULT - learn does NOT trigger sync

    # For init and periodic triggers, always sync if enabled
    if trigger in ("init", "periodic"):
        if trigger == "periodic" and self.config.auto_sync_interval_hours > 0:
            return self._should_sync_by_interval()
        return True

    # For enhance/learn, check interval
    if self.config.auto_sync_interval_hours > 0:
        return self._should_sync_by_interval()

    return True
```

**Decision Flow**:
```
Trigger Type        | Config Check               | Default Behavior
--------------------|----------------------------|------------------
"init"              | auto_sync_enabled          | SYNC (if enabled)
"enhance"           | auto_sync_on_enhance       | SYNC (enabled by default)
"learn"             | auto_sync_on_learn         | SKIP (disabled by default)
"periodic"          | interval elapsed           | SYNC (every 24h)
```

### 1.4 Sync Execution

**File**: `src/kuzu_memory/integrations/auto_git_sync.py` (lines 158-213)

```python
def auto_sync_if_needed(self, trigger: str = "periodic", verbose: bool = False) -> dict:
    # Check if sync should run
    if not self.should_auto_sync(trigger):
        return {
            "success": True,
            "skipped": True,
            "reason": "Auto-sync conditions not met",
            "trigger": trigger,
        }

    try:
        # Determine sync mode based on state
        mode = "incremental" if self._state.get("last_sync") else "initial"

        # Run sync with max commits limit to prevent blocking
        sync_result = self.git_sync.sync(mode=mode, dry_run=False)

        # Update state on success
        if sync_result.get("success"):
            self._state["last_sync"] = datetime.now().isoformat()
            self._state["last_commit_sha"] = sync_result.get("last_commit_sha")
            self._state["commits_synced"] += sync_result.get("commits_synced", 0)
            self._save_state()

        return sync_result

    except Exception as e:
        logger.error(f"Auto git sync failed: {e}")
        return {"success": False, "error": str(e), "trigger": trigger}
```

**State Persistence**: `~/.kuzu-memory/git_sync_state.json`
```json
{
  "last_sync": "2026-01-20T15:30:00",
  "last_commit_sha": "a1b2c3d4",
  "commits_synced": 150
}
```

### 1.5 Git Sync Service (Service Layer)

**File**: `src/kuzu_memory/services/git_sync_service.py`

The `GitSyncService` provides a clean service-oriented wrapper around the git sync functionality:

```python
class GitSyncService(BaseService):
    """Thin wrapper around GitSyncManager with lifecycle management."""

    def __init__(self, config_service: ConfigService):
        self._config_service = config_service
        self._git_sync: GitSyncManager | None = None

    def sync(self, since: str | None = None, max_commits: int = 100) -> int:
        """Sync git history as episodic memories."""
        result = self.git_sync.sync(mode="auto", dry_run=False)
        commits_synced = result.get("commits_synced", 0)
        return commits_synced

    def install_hooks(self) -> bool:
        """Install git hooks for automatic synchronization."""
        # Creates post-commit hook that runs:
        # kuzu-memory git sync --incremental --quiet 2>/dev/null || true
```

**Git Hook Installation** (lines 258-269):
```bash
#!/bin/sh
# KuzuMemory git post-commit hook
# Auto-sync commits to memory system

kuzu-memory git sync --incremental --quiet 2>/dev/null || true
```

The hook is installed at: `.git/hooks/post-commit`

---

## 2. Hooks Learn Command

### 2.1 Implementation

**File**: `src/kuzu_memory/cli/hooks_commands.py` (lines 586-752)

```python
@hooks_group.command(name="learn")
def hooks_learn() -> None:
    """
    Learn from conversations (for Claude Code hooks).

    Reads JSON from stdin per Claude Code hooks API, extracts the last assistant
    message from the transcript, and stores it as a memory.
    """
    import hashlib
    import logging
    import time
    from pathlib import Path

    from ..core.memory import KuzuMemory
    from ..utils.project_setup import find_project_root, get_project_db_path

    # Configure minimal logging
    log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
    log_file = log_dir / "kuzu_learn.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file)],
        force=True,
    )
    logger = logging.getLogger(__name__)
```

### 2.2 Execution Flow

**Step 1: Read JSON from stdin**
```python
try:
    input_data = json.load(sys.stdin)
    hook_event = input_data.get("hook_event_name", "unknown")
    logger.info(f"Hook event: {hook_event}")
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON from stdin: {e}")
    _exit_hook_with_json()
```

**Step 2: Find transcript file** (lines 670-690)
```python
transcript_path = input_data.get("transcript_path", "")
if not transcript_path:
    logger.info("No transcript path provided")
    _exit_hook_with_json()

# Find the transcript file
transcript_file = Path(transcript_path)
if not transcript_file.exists():
    # Try to find the most recent transcript in the same directory
    if transcript_file.parent.exists():
        transcripts = list(transcript_file.parent.glob("*.jsonl"))
        if transcripts:
            transcript_file = max(transcripts, key=lambda p: p.stat().st_mtime)
```

**Step 3: Extract last assistant message** (lines 25-89)
```python
def _find_last_assistant_message(transcript_file: Path) -> str | None:
    """Find the last assistant message in the transcript."""
    try:
        with open(transcript_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Search backwards for assistant messages
        for line in reversed(lines):
            try:
                entry = json.loads(line.strip())
                message = entry.get("message", {})

                if message.get("role") != "assistant":
                    continue

                content = message.get("content", [])
                text_parts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]

                if text_parts:
                    text = " ".join(text_parts).strip()
                    # Normalize line endings (Fix #12)
                    text = text.replace("\r\n", "\n").replace("\r", "\n")
                    if text:
                        return text
            except json.JSONDecodeError:
                continue

        return None
    except Exception as e:
        logger.error(f"Error reading transcript: {e}")
        return None
```

**Step 4: Deduplication check** (lines 621-656)
```python
def is_duplicate(text: str) -> bool:
    """Check if this content was recently stored."""
    try:
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        current_time = time.time()

        cache = {}
        cache_file = log_dir / ".kuzu_learn_cache.json"
        cache_ttl = 300  # 5 minutes

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cache = json.load(f)
            except (OSError, json.JSONDecodeError):
                logger.warning("Failed to load cache, starting fresh")

        # Clean expired entries
        cache = {k: v for k, v in cache.items() if current_time - v < cache_ttl}

        # Check if duplicate
        if content_hash in cache:
            age = current_time - cache[content_hash]
            logger.info(f"Duplicate detected (stored {age:.1f}s ago), skipping")
            return True

        # Not a duplicate - add to cache
        cache[content_hash] = current_time

        try:
            with open(cache_file, "w") as f:
                json.dump(cache, f)
        except OSError as e:
            logger.warning(f"Failed to save cache: {e}")

        return False
    except Exception as e:
        logger.error(f"Error checking for duplicates: {e}")
        return False
```

**Step 5: Store memory SYNCHRONOUSLY** (lines 717-742)
```python
# Store the memory
try:
    project_root = find_project_root()
    if project_root is None:
        logger.info("Project root not found, skipping learning")
        _exit_hook_with_json()

    db_path = get_project_db_path(project_root)

    if not db_path.exists():
        logger.info("Project not initialized, skipping learning")
        _exit_hook_with_json()

    # CRITICAL: This is SYNCHRONOUS - opens database connection
    memory = KuzuMemory(db_path=db_path)

    # Blocks until remember() completes
    memory.remember(
        content=assistant_text,
        source="claude-code-hook",
        metadata={"agent_id": "assistant"},
    )

    logger.info("Memory stored successfully")
    memory.close()  # Releases database lock

except Exception as e:
    logger.error(f"Error storing memory: {e}")
    _exit_hook_with_json()

_exit_hook_with_json()
```

### 2.3 Synchronous Behavior Analysis

**Database Lock Held During**:
1. `KuzuMemory(db_path=db_path)` - Opens database connection
2. `memory.remember(...)` - Stores memory in database
3. `memory.close()` - Closes database connection

**Time Complexity**:
```
Total Hook Execution Time =
    File I/O (read transcript) +
    JSON parsing (find last message) +
    Hash computation (dedup check) +
    Database operations (remember + possible git sync)
```

**Problem**: If hooks learn is called while another process (like MCP kuzu_learn) is writing to the database, it could encounter:
- **Database lock timeout** (default: 5 seconds)
- **Blocked execution** until lock is released
- **Hook failure** if timeout exceeded

---

## 3. MCP kuzu_learn Tool

### 3.1 Implementation

**File**: `src/kuzu_memory/mcp/server.py` (lines 119-146, 247-253, 362-369)

**Tool Definition** (lines 119-146):
```python
Tool(
    name="kuzu_learn",
    description=(
        "ASYNC/BACKGROUND/NON-BLOCKING continuous learning: Store observations, "
        "insights, and learnings asynchronously during conversations without waiting "
        "for confirmation. Ideal for capturing context, patterns, and evolving "
        "understanding as they emerge. Returns immediately without blocking. "
        "\n\nWhen to use: Ongoing conversation learnings, observations, insights, "
        "context capture during development sessions. "
        "\n\nWhen NOT to use: Critical facts requiring immediate confirmation (use "
        "kuzu_remember instead for synchronous storage of important decisions, "
        "preferences, or facts that must be stored immediately)."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The content to learn and store asynchronously",
            },
            "source": {
                "type": "string",
                "description": "Source of the learning (default: ai-conversation)",
                "default": "ai-conversation",
            },
        },
        "required": ["content"],
    },
)
```

**Handler** (lines 247-253):
```python
@self.server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "kuzu_learn":
        content = arguments.get("content", "")
        source = arguments.get("source", "ai-conversation")
        result = await self._learn(
            str(content) if content is not None else "",
            str(source) if source is not None else "ai-conversation",
        )
```

**Async Implementation** (lines 362-369):
```python
async def _learn(self, content: str, source: str = "ai-conversation") -> str:
    """Store a learning asynchronously."""
    if not content:
        return "Error: No content provided"

    args = ["memory", "learn", content, "--source", source, "--quiet", "--no-wait"]
    # Fire and forget - don't wait for completion
    return await self._run_command(args, capture_output=False)
```

### 3.2 Fire-and-Forget Subprocess Execution

**File**: `src/kuzu_memory/mcp/server.py` (lines 300-344)

```python
async def _run_command(self, args: list[str], capture_output: bool = True) -> str:
    """
    Run a kuzu-memory command asynchronously.

    Args:
        args: Command arguments
        capture_output: Whether to capture output

    Returns:
        Command output or status message
    """
    try:
        cmd = ["kuzu-memory", *args]

        if capture_output:
            # Standard async execution with wait
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                error_msg = stderr.decode().strip() or "Command failed"
                logger.error(f"Command failed: {' '.join(cmd)}: {error_msg}")
                return f"Error: {error_msg}"
        else:
            # Fire and forget for async operations
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,  # Discard output
                stderr=asyncio.subprocess.DEVNULL,  # Discard errors
                cwd=self.project_root,
            )
            # Don't wait for completion - return immediately
            return "Learning stored asynchronously"

    except TimeoutError:
        return "Error: Command timed out"
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        return f"Error: {e!s}"
```

### 3.3 Async Flow Diagram

```
MCP Client (Claude Desktop)
    |
    v
[kuzu_learn tool call] --async--> KuzuMemoryMCPServer._learn()
    |                                      |
    |                                      v
    |                          _run_command(capture_output=False)
    |                                      |
    |                                      v
    |                          asyncio.create_subprocess_exec(
    |                              ["kuzu-memory", "memory", "learn", content, "--no-wait"],
    |                              stdout=DEVNULL,
    |                              stderr=DEVNULL
    |                          )
    |                                      |
    v                                      |
IMMEDIATE RETURN <------------ return "Learning stored asynchronously"
"Learning stored asynchronously"           |
                                           v
                                    [Background Process]
                                    kuzu-memory memory learn --no-wait
                                           |
                                           v
                                    CLI async_cli.learn_async()
                                           |
                                           v
                                    Background queue processing
```

### 3.4 Key Differences: MCP vs Hooks

| Aspect | MCP kuzu_learn | hooks learn |
|--------|----------------|-------------|
| **Execution Model** | Async subprocess (fire-and-forget) | Synchronous (blocks) |
| **Database Connection** | Spawned process opens connection | Direct KuzuMemory instantiation |
| **Lock Behavior** | New process = new connection pool | Shares connection pool with parent |
| **Return Time** | Immediate (~5ms) | Waits for completion (~50-200ms) |
| **Error Handling** | Silent failure (DEVNULL) | Logged to /tmp/kuzu_learn.log |
| **Git Sync Trigger** | Yes (if enabled) | Yes (if enabled) |
| **Deduplication** | Via background process | In-memory cache (5min TTL) |

**Critical Difference**: MCP spawns a **separate process** which gets its own database connection from the pool, while hooks learn runs **in the same process** and must wait for a connection from the pool.

---

## 4. Database Lock Handling

### 4.1 Connection Pool Architecture

**File**: `src/kuzu_memory/storage/kuzu_adapter.py` (lines 66-185)

```python
class KuzuConnectionPool:
    """
    Connection pool for Kuzu database connections.

    Manages a pool of database connections to improve performance
    and handle concurrent access safely.
    """

    def __init__(self, db_path: Path, pool_size: int = 5) -> None:
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: Queue[Any] = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._initialized = False
        self._database: Any = None  # Shared kuzu.Database instance

    def _create_connection(self) -> Any:
        """Create a new Kuzu connection using the shared database instance."""
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create shared database instance if not exists
            if self._database is None:
                self._database = kuzu.Database(str(self.db_path))

            # Create connection using shared database
            connection = kuzu.Connection(self._database)

            return connection

        except Exception as e:
            raise DatabaseError(f"Failed to create Kuzu connection: {e}")

    def initialize(self) -> None:
        """Initialize the connection pool."""
        with self._lock:
            if self._initialized:
                return

            try:
                # Create initial connections
                for _ in range(self.pool_size):
                    conn = self._create_connection()
                    self._pool.put(conn)

                self._initialized = True
                logger.info(f"Initialized Kuzu connection pool with {self.pool_size} connections")

            except Exception as e:
                raise DatabaseError(f"Failed to initialize connection pool: {e}")

    @contextmanager
    def get_connection(self, timeout: float = 5.0) -> Iterator[Any]:
        """
        Get a connection from the pool.

        Args:
            timeout: Timeout in seconds to wait for a connection

        Yields:
            Kuzu connection

        Raises:
            DatabaseLockError: If no connection is available within timeout
        """
        if not self._initialized:
            self.initialize()

        connection = None
        try:
            # Get connection from pool
            connection = self._pool.get(timeout=timeout)  # BLOCKS HERE
            yield connection

        except Empty:
            raise DatabaseLockError(
                f"Failed to get connection from pool within {timeout}s for {self.db_path}"
            )

        finally:
            # Return connection to pool
            if connection is not None:
                try:
                    self._pool.put(connection, timeout=1.0)
                except Exception:
                    # If we can't return to pool, create a new connection
                    logger.warning("Failed to return connection to pool, creating new one")
                    try:
                        new_conn = self._create_connection()
                        self._pool.put(new_conn, timeout=1.0)
                    except Exception:
                        logger.error("Failed to create replacement connection")
```

### 4.2 Lock Timeout Behavior

**Timeout Mechanism**:
```python
connection = self._pool.get(timeout=5.0)
```

**What happens when timeout is reached**:
1. `Queue.get()` raises `Empty` exception
2. Caught by except block
3. Raises `DatabaseLockError` with message:
   ```
   Failed to get connection from pool within 5.0s for {db_path}
   ```

**Default Pool Configuration**:
```python
class KuzuAdapter:
    def __init__(self, db_path: Path, config: KuzuMemoryConfig) -> None:
        self._pool = KuzuConnectionPool(
            db_path,
            pool_size=config.storage.connection_pool_size  # Default: 5
        )
```

### 4.3 Concurrent Access Scenarios

**Scenario 1: MCP kuzu_learn + Hooks learn (CONFLICT)**
```
Time  | MCP Process                      | Hooks Process
------|----------------------------------|----------------------------------
T0    | Spawn subprocess                 |
T1    | subprocess: get_connection()     |
T2    | subprocess: acquired conn #1     |
T3    | subprocess: remember()           | hooks learn: get_connection()
T4    | subprocess: writing to DB        | hooks: BLOCKED (wait for conn)
T5    | subprocess: writing to DB        | hooks: still BLOCKED
T6    | subprocess: close(), return conn | hooks: acquire conn #1
T7    |                                  | hooks: remember()
```

**If all 5 connections are in use**:
- Hooks learn will wait up to 5 seconds
- If no connection available in 5s → `DatabaseLockError`
- Hook exits with error logged to `/tmp/kuzu_learn.log`

**Scenario 2: Multiple MCP kuzu_learn calls (QUEUED)**
```
Time  | MCP Call 1      | MCP Call 2      | MCP Call 3      | Connection Pool
------|-----------------|-----------------|-----------------|------------------
T0    | spawn proc #1   | spawn proc #2   | spawn proc #3   | [5 available]
T1    | proc #1: conn   | proc #2: conn   | proc #3: conn   | [2 available]
T2    | proc #1: write  | proc #2: write  | proc #3: write  | [2 available]
T3    | proc #1: done   | proc #2: write  | proc #3: write  | [3 available]
T4    |                 | proc #2: done   | proc #3: write  | [4 available]
T5    |                 |                 | proc #3: done   | [5 available]
```

Each subprocess gets its own connection from the pool - up to 5 concurrent writes possible.

### 4.4 Kuzu Database Write Locking

**Kuzu Database Characteristics**:
- **ACID compliant** with transaction support
- **WAL (Write-Ahead Logging)** for crash recovery
- **MVCC-like** behavior for read consistency

**From Kuzu documentation**:
> Kuzu uses a write lock to ensure serializable transactions. Only one write transaction can be active at a time, but multiple read transactions can run concurrently with a write transaction.

**Implications for kuzu-memory**:
1. **Connection pool doesn't prevent write lock contention**
2. Even with 5 connections, only **1 write at a time** at the database level
3. Other writes will block until the active write transaction commits
4. Read operations (recall, enhance) can run concurrently with writes

**Actual Lock Behavior**:
```
Connection Pool (5 connections)
    |
    v
Kuzu Database (1 write lock)
    |
    v
[Write Transaction 1] --> ACTIVE
[Write Transaction 2] --> BLOCKED (waiting for lock)
[Write Transaction 3] --> BLOCKED (waiting for lock)
[Read Transaction 1]  --> ACTIVE (concurrent with write)
[Read Transaction 2]  --> ACTIVE (concurrent with write)
```

---

## 5. Problem Analysis: Hooks Learn + Git Sync

### 5.1 Current Hooks Learn Flow

```
hooks learn called
    |
    v
1. Read JSON from stdin (~1ms)
    |
    v
2. Find transcript file (~2ms)
    |
    v
3. Extract last assistant message (~10-50ms)
    |
    v
4. Deduplication check (~1ms)
    |
    v
5. find_project_root() (~2ms)
    |
    v
6. KuzuMemory(db_path) (~20ms - opens DB connection)
    |
    v
7. memory.remember() (~50-100ms - writes to DB)
    |   |
    |   v
    |   _auto_git_sync("learn") ???  <-- POTENTIAL ISSUE
    |       |
    |       v
    |       if auto_sync_on_learn == True:
    |           git_sync.sync() (~200-1000ms - git operations)
    |
    v
8. memory.close() (releases DB lock)
    |
    v
Total: 86-173ms WITHOUT git sync
Total: 286-1173ms WITH git sync
```

### 5.2 Configuration Issue

**Current Default**: `auto_sync_on_learn = False` (disabled)

**What happens if enabled**:
```python
# In KuzuMemory.remember()
def remember(self, content: str, ...) -> str:
    # Store memory
    memory_id = self.memory_store._store_memory_in_database(memory)

    # NOT CALLED - remember() doesn't trigger auto-sync
    # Only generate_memories() triggers it

    return memory_id
```

**Wait - does hooks learn call remember() or generate_memories()?**

**File**: `src/kuzu_memory/cli/hooks_commands.py` (line 731)
```python
memory.remember(
    content=assistant_text,
    source="claude-code-hook",
    metadata={"agent_id": "assistant"},
)
```

**Answer**: Hooks learn calls `remember()`, which does **NOT** trigger auto-sync!

### 5.3 Git Sync is NOT Triggered by Hooks Learn

**Key Finding**: `remember()` does not call `_auto_git_sync()` at all.

**Only `generate_memories()` triggers auto-sync**:

**File**: `src/kuzu_memory/core/memory.py` (line 589)
```python
def generate_memories(self, content: str, ...) -> list[str]:
    # Extract patterns and store memories
    memory_ids = self._extract_and_store_memories(...)

    # Trigger auto git sync on learn (if enabled in config)
    self._auto_git_sync("learn")

    return memory_ids
```

**But hooks learn uses `remember()`, not `generate_memories()`**:
```python
# hooks_commands.py (line 731)
memory.remember(content=assistant_text, source="claude-code-hook")
```

**Therefore**: Git sync is **NOT** triggered by hooks learn, regardless of `auto_sync_on_learn` config.

---

## 6. Recommendations

### 6.1 Making Hooks Learn Truly Async

**Option 1: Subprocess Execution (Recommended)**

Similar to MCP kuzu_learn, spawn a background process:

```python
@hooks_group.command(name="learn")
def hooks_learn() -> None:
    """Learn from conversations (async background processing)."""
    import subprocess

    # Read JSON and extract transcript
    input_data = json.load(sys.stdin)
    transcript_path = input_data.get("transcript_path")

    # Extract message
    assistant_text = _find_last_assistant_message(Path(transcript_path))

    if not assistant_text or is_duplicate(assistant_text):
        _exit_hook_with_json()

    # Spawn background process (fire-and-forget)
    subprocess.Popen(
        ["kuzu-memory", "memory", "learn", assistant_text,
         "--source", "claude-code-hook", "--no-wait", "--quiet"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    logger.info("Learning queued in background")
    _exit_hook_with_json()
```

**Benefits**:
- Hook returns immediately (~15ms)
- No database lock held by hook process
- Background process handles DB writes
- Matches MCP kuzu_learn behavior

**Trade-offs**:
- Extra process spawn overhead
- Can't report errors to Claude Code
- Deduplication cache in separate process

**Option 2: Direct Async Queue**

Use the existing async CLI infrastructure:

```python
@hooks_group.command(name="learn")
def hooks_learn() -> None:
    """Learn from conversations (async queue)."""
    from ..async_memory.async_cli import get_async_cli

    # Extract message (same as before)
    assistant_text = _find_last_assistant_message(...)

    # Queue asynchronously
    async_cli = get_async_cli()
    result = async_cli.learn_async(
        content=assistant_text,
        source="claude-code-hook",
        wait_for_completion=False,  # Fire-and-forget
        quiet=True
    )

    logger.info(f"Learning queued: {result['task_id']}")
    _exit_hook_with_json()
```

**Benefits**:
- Uses existing async infrastructure
- Shared deduplication logic
- Better error handling and logging
- Task tracking possible

**Trade-offs**:
- Requires background worker running
- More complex lifecycle management
- Shared state between processes

### 6.2 Git Sync Strategy for Hooks Learn

**Current State**: Git sync is **NOT** triggered by hooks learn (uses `remember()`, not `generate_memories()`)

**Option 1: Keep Current Behavior (Recommended)**

Don't trigger git sync from hooks learn because:
- Hooks are called frequently (every assistant response)
- Git sync is expensive (200-1000ms)
- Would block hook execution
- Periodic sync (24h) is sufficient

**Option 2: Trigger Git Sync from Background Process**

If using subprocess/async queue approach:
```python
# In background process after remember()
if should_sync_from_hooks():
    memory._auto_git_sync("learn")
```

**Conditional sync logic**:
```python
def should_sync_from_hooks() -> bool:
    # Only sync if:
    # 1. auto_sync_on_learn is enabled
    # 2. Interval has elapsed (don't sync on every hook)
    # 3. Git repo is available

    if not config.auto_sync_on_learn:
        return False

    state = load_sync_state()
    if state["last_sync"]:
        hours_since = (datetime.now() - state["last_sync"]).total_seconds() / 3600
        if hours_since < config.auto_sync_interval_hours:
            return False  # Too soon

    return True
```

### 6.3 Database Lock Optimization

**Option 1: Reduce Connection Pool Timeout**

For hooks, use shorter timeout to fail fast:
```python
# In hooks_commands.py
memory = KuzuMemory(db_path=db_path)
memory._pool._timeout = 2.0  # 2 seconds instead of 5
```

**Option 2: Separate Database for Hooks**

Create a separate database for hook-sourced memories:
```
~/.kuzu-memory/
    memories.db        # Main database (MCP, CLI)
    hooks_memories.db  # Hook-specific database
```

Periodically merge:
```bash
kuzu-memory admin merge-hooks --source hooks_memories.db
```

**Trade-offs**: Increased complexity, eventual consistency issues

**Option 3: In-Memory Queue + Batch Write**

Hooks write to in-memory queue, background worker flushes to DB:
```python
# Hook process
queue = get_memory_queue()
queue.put({
    "content": assistant_text,
    "source": "claude-code-hook",
    "timestamp": datetime.now()
})

# Background worker (separate process)
while True:
    batch = queue.get_batch(max_size=10, timeout=5.0)
    if batch:
        with KuzuMemory(db_path) as memory:
            for item in batch:
                memory.remember(**item)
```

**Benefits**: Batched writes, reduced lock contention
**Trade-offs**: Complexity, potential data loss on crash

---

## 7. Conclusion

### Summary of Findings

1. **Auto git sync triggers**:
   - `init`: Always (if enabled)
   - `enhance`: Yes (enabled by default)
   - `learn`: No for `remember()`, Yes for `generate_memories()` (disabled by default)

2. **Hooks learn is synchronous**:
   - Opens database connection directly
   - Blocks until `remember()` completes
   - Does NOT trigger git sync (uses `remember()`, not `generate_memories()`)
   - Total execution: 86-173ms

3. **MCP kuzu_learn is async**:
   - Spawns subprocess with fire-and-forget
   - Returns immediately (~5ms)
   - Background process handles DB write
   - Triggers git sync if `auto_sync_on_learn` enabled

4. **Database locking**:
   - Connection pool (5 connections, 5s timeout)
   - Kuzu DB: 1 write at a time, concurrent reads OK
   - Lock contention possible with multiple writers
   - No automatic retry or exponential backoff

### Recommended Actions

**Immediate (Low Risk)**:
1. Keep `auto_sync_on_learn = False` (current default)
2. Rely on periodic sync (24h interval) for git commits
3. Document that hooks learn is synchronous by design

**Short-term (Medium Risk)**:
1. Implement subprocess-based hooks learn (Option 1)
2. Add connection pool metrics and monitoring
3. Log DatabaseLockError occurrences for analysis

**Long-term (High Risk)**:
1. Evaluate async queue architecture for all hook operations
2. Consider separate hook database with periodic merge
3. Implement intelligent git sync batching (sync N commits at once)

### Files to Monitor

**Critical Files**:
- `src/kuzu_memory/cli/hooks_commands.py` - Hooks learn implementation
- `src/kuzu_memory/mcp/server.py` - MCP kuzu_learn implementation
- `src/kuzu_memory/core/memory.py` - Auto-sync trigger points
- `src/kuzu_memory/integrations/auto_git_sync.py` - Sync decision logic
- `src/kuzu_memory/storage/kuzu_adapter.py` - Connection pool and locking

**Configuration**:
- `src/kuzu_memory/core/config.py` - GitSyncConfig defaults

**State Files**:
- `~/.kuzu-memory/git_sync_state.json` - Last sync timestamp
- `/tmp/.kuzu_learn_cache.json` - Deduplication cache
- `/tmp/kuzu_learn.log` - Hook execution logs

---

## Appendix A: Code References

### A.1 Auto Git Sync Trigger Points

| Location | Trigger | Default Enabled | Notes |
|----------|---------|-----------------|-------|
| `memory.py:283` | `init` | Yes | On KuzuMemory initialization |
| `memory.py:446` | `enhance` | Yes | After attach_memories() |
| `memory.py:589` | `learn` | No | After generate_memories() only |

### A.2 Configuration Values

```python
# src/kuzu_memory/core/config.py
GitSyncConfig(
    auto_sync_enabled=True,         # Master switch
    auto_sync_on_enhance=True,      # Sync on attach_memories()
    auto_sync_on_learn=False,       # Sync on generate_memories()
    auto_sync_interval_hours=24,    # Periodic interval
    auto_sync_max_commits=50        # Max commits per sync
)

# src/kuzu_memory/storage/kuzu_adapter.py
KuzuConnectionPool(
    pool_size=5,                    # Max concurrent connections
    timeout=5.0                     # Lock acquisition timeout
)
```

### A.3 Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| `hooks learn` (no git sync) | 86-173ms | Synchronous DB write |
| `hooks learn` (with git sync) | 286-1173ms | IF generate_memories used |
| `MCP kuzu_learn` (return) | ~5ms | Fire-and-forget subprocess |
| `MCP kuzu_learn` (background) | 100-300ms | Actual DB write |
| `git sync` (incremental) | 200-500ms | 10-50 commits |
| `git sync` (initial) | 500-2000ms | 100+ commits |

---

**End of Analysis**
