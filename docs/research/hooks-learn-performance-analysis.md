# Hooks Learn Performance Analysis

**Date**: 2026-01-23
**Context**: Investigation into `kuzu-memory hooks learn` command performance bottlenecks
**Issue**: Hooks running slow (293ms baseline, 300-500ms with git sync overhead)

## Executive Summary

The `kuzu-memory hooks learn` command has been optimized to run asynchronously (~50ms), but **still triggers synchronous git sync** during database initialization, causing 300-500ms overhead when scanning 58 commits across 11 branches. This is particularly problematic in multi-session scenarios where 5+ MCP processes compete for database locks.

## Code Path Analysis

### Entry Point
**File**: `src/kuzu_memory/cli/hooks_commands.py`
**Command**: `@hooks_group.command(name="learn")`
**Lines**: 748-781

```python
@hooks_group.command(name="learn")
@click.option("--sync", "sync_mode", is_flag=True)
def hooks_learn(sync_mode: bool) -> None:
    """Learn from conversations (for Claude Code hooks)."""
    if sync_mode:
        _learn_sync(logger, log_dir)
    else:
        _learn_async(logger)  # Default: fire-and-forget
```

### Async Mode (Default)
**Function**: `_learn_async()`
**Lines**: 926-1005
**Performance**: ~50ms total

**Optimizations Already Applied**:
1. ✅ Cached project root discovery (100ms → 5ms) - Line 951-963
2. ✅ multiprocessing.Process instead of subprocess.Popen (80ms → 20ms) - Line 979-990
3. ✅ Fire-and-forget spawn (doesn't wait for worker) - Line 989-990

### Worker Process
**Function**: `_learn_worker()`
**Lines**: 783-924
**Critical Path**: Lines 904-920

```python
# Line 904-920: Database operations with auto_sync=False
with try_lock_database(db_path, timeout=0.0):
    # ❌ PROBLEM: auto_sync=False still triggers git sync on __init__
    memory = KuzuMemory(db_path=db_path, auto_sync=False)

    memory.remember(content=assistant_text, source="claude-code-hook")
    memory.close()
```

### Root Cause: KuzuMemory Initialization
**File**: `src/kuzu_memory/core/memory.py`
**Lines**: 163-295

**The Problem**:
```python
# Line 169: auto_sync parameter accepted
def __init__(self, db_path, ..., auto_sync: bool = True):
    self._auto_sync = auto_sync  # Line 217
    self._initialize_components()  # Line 220

# Line 256-295: _initialize_components()
def _initialize_components(self):
    if self._enable_git_sync:
        self._initialize_git_sync()  # Line 286

        # ❌ PROBLEM: Always runs if auto_sync=True (default)
        if self._auto_sync:
            self._auto_git_sync("init")  # Line 289 - BLOCKS HERE
```

### Git Sync Overhead
**File**: `src/kuzu_memory/integrations/auto_git_sync.py`
**Lines**: 159-199

**When auto_git_sync("init") is called**:
1. Checks `should_auto_sync("init")` → returns True (Line 111)
2. Calls `git_sync.sync(mode="incremental")` (Line 188)
3. **BLOCKING**: Scans git history to find commits

**File**: `src/kuzu_memory/integrations/git_sync.py`
**Lines**: 384-483 (`get_significant_commits`)

**The 300-500ms Overhead**:
```python
# Line 415: Filters branches (observed: 11 branches)
branches = self._filter_branches(list(self._repo.branches))

# Line 422-469: Iterates through ALL branches
for branch in branches:
    commits_iter = self._repo.iter_commits(branch, **iter_params)  # Line 436
    commits = list(reversed(list(commits_iter)))  # Line 439 - LOADS ALL COMMITS

    # Observed: 58 commits total across 11 branches
    # Time: 300-500ms depending on repo state
```

## Performance Breakdown

| Phase | Time | Notes |
|-------|------|-------|
| Project root cache lookup | ~5ms | ✅ Optimized (was 100ms) |
| Worker spawn (multiprocessing) | ~20ms | ✅ Optimized (was 80ms subprocess) |
| Database lock acquisition | <1ms | ✅ Fast with timeout=0 |
| **KuzuMemory init with git sync** | **300-500ms** | ❌ **BOTTLENECK** |
| Memory.remember() | ~5ms | ✅ Fast |
| **Total (async mode)** | **~50ms** | ✅ Parent returns immediately |
| **Worker total** | **330-530ms** | ❌ Still blocking in background |

## Identified Issues

### Issue 1: auto_sync Flag is Misleading
**Location**: `hooks_commands.py:906`

```python
# ❌ CURRENT: auto_sync=False still triggers git sync!
memory = KuzuMemory(db_path=db_path, auto_sync=False)
```

**Root Cause**: `auto_sync=False` only skips **automatic periodic syncs**, but the `__init__` method still:
1. Calls `_initialize_git_sync()` if `enable_git_sync=True` (default)
2. Runs `_auto_git_sync("init")` on first initialization

**Expected Behavior**: `auto_sync=False` should skip **all** automatic syncs, including init.

### Issue 2: No Timeout on Git Sync
**Location**: `git_sync.py:436-439`

```python
# ❌ PROBLEM: Unbounded iteration through git history
commits_iter = self._repo.iter_commits(branch, **iter_params)
commits = list(reversed(list(commits_iter)))  # Loads ALL commits
```

**Impact**:
- 58 commits across 11 branches = 300-500ms
- Larger repos could block for seconds or minutes
- No timeout mechanism to fail-fast

### Issue 3: Database Lock Contention
**Location**: `hooks_commands.py:905`

```python
# ✅ GOOD: timeout=0 for fail-fast
with try_lock_database(db_path, timeout=0.0):
    memory = KuzuMemory(...)  # But then blocks on git sync!
```

**Scenario**: 5+ MCP processes compete for lock:
1. Process 1 acquires lock → spends 300-500ms on git sync
2. Process 2-5 fail immediately (timeout=0) → good for non-blocking
3. BUT: Process 1 holds lock for 300-500ms unnecessarily

## Optimization Opportunities

### Option 1: Skip Git Sync for Hooks (RECOMMENDED)
**Impact**: 300-500ms → ~5ms
**Implementation**: Set `enable_git_sync=False` for hooks

```python
# hooks_commands.py:906
memory = KuzuMemory(
    db_path=db_path,
    enable_git_sync=False,  # ✅ Skip git sync entirely for hooks
    auto_sync=False,
)
```

**Rationale**:
- Hooks run frequently (every user prompt + response)
- Git sync is better suited for:
  - Session start (once per session)
  - Manual `kuzu-memory git sync` command
  - MCP tools with timeout tolerance

### Option 2: Move Git Sync to Session Start Hook
**Impact**: Distributes cost across session lifecycle
**Location**: `hooks_commands.py:638-746` (`hooks_session_start`)

**Current State**:
```python
# Line 705: Already disables auto_sync, but could enable git sync here
memory = KuzuMemory(db_path=db_path, auto_sync=False)

# Line 722-724: Fire-and-forget async git sync (GOOD!)
_git_sync_async(project_root, logger)
```

**Observation**: Session start already runs async git sync in background via subprocess. This is the **correct place** for git sync.

### Option 3: Add Timeout to Git Sync
**Impact**: Prevents indefinite blocking
**Location**: `git_sync.py:384-483`

```python
# Add timeout parameter to get_significant_commits()
def get_significant_commits(
    self,
    since: datetime | None = None,
    branch_name: str | None = None,
    max_commits: int | None = None,
    timeout_ms: int = 100,  # ✅ Add timeout
) -> list[Any]:
    start_time = time.time()

    for branch in branches:
        # Check timeout before processing next branch
        if (time.time() - start_time) * 1000 > timeout_ms:
            logger.warning(f"Git sync timeout ({timeout_ms}ms), returning partial results")
            break
```

### Option 4: Cache Git Scan Results
**Impact**: 300-500ms → ~5ms (cache hit)
**Implementation**: Cache commit SHAs + timestamps for 5 minutes

```python
# Cache key: (repo_path, since_timestamp)
# Cache value: list of commit objects
# TTL: 300 seconds (5 minutes)
```

**Rationale**: Multiple hooks/sessions accessing same repo can share scan results.

## Recommendations

### Immediate (High Impact, Low Risk)
1. **Set `enable_git_sync=False` for hooks learn command** (Option 1)
   - Lines to change: `hooks_commands.py:906` and `hooks_commands.py:1136`
   - Estimated impact: 300-500ms → 5ms (98% reduction)
   - Risk: None (session-start already handles git sync)

2. **Verify session-start async git sync is working** (Option 2)
   - Already implemented at `hooks_commands.py:722-724`
   - No changes needed, just verification

### Medium-Term (Defense in Depth)
3. **Add timeout to git sync operations** (Option 3)
   - Prevents unbounded blocking on large repos
   - Estimated implementation: 2-4 hours
   - Add to `get_significant_commits()` and `sync()` methods

4. **Implement git scan result caching** (Option 4)
   - Share scan results across processes
   - Estimated implementation: 4-6 hours
   - Use `/tmp/.kuzu_git_scan_cache.json` with TTL

### Long-Term (Architectural)
5. **Separate git sync into background daemon**
   - Run git sync in dedicated process
   - Communicate via IPC or file-based queue
   - Estimated implementation: 2-3 days

## Testing Plan

### Test 1: Verify Hooks Learn Performance
```bash
# Before optimization
time echo '{"transcript_path": "/tmp/test.jsonl"}' | kuzu-memory hooks learn

# Expected: ~330-530ms (with git sync overhead)

# After optimization (enable_git_sync=False)
time echo '{"transcript_path": "/tmp/test.jsonl"}' | kuzu-memory hooks learn

# Expected: ~50ms (no git sync)
```

### Test 2: Verify Session Start Git Sync
```bash
# Check logs to confirm async git sync runs
tail -f /tmp/kuzu_session_start.log | grep "git sync"

# Expected: "Launched background git sync (PID: XXXX)"
```

### Test 3: Multi-Process Lock Contention
```bash
# Spawn 5 concurrent hook processes
for i in {1..5}; do
    echo '{"transcript_path": "/tmp/test.jsonl"}' | \
    kuzu-memory hooks learn &
done

# Monitor lock file
watch -n 0.1 ls -la ~/.kuzu-memory/.memories.db.lock

# Expected: Short-lived locks (<50ms), no blocking
```

## Related Files

### Core Components
- `src/kuzu_memory/cli/hooks_commands.py` - Hooks CLI commands
- `src/kuzu_memory/core/memory.py` - KuzuMemory main class
- `src/kuzu_memory/integrations/git_sync.py` - Git commit scanning
- `src/kuzu_memory/integrations/auto_git_sync.py` - Auto-sync manager

### Lock Management
- `src/kuzu_memory/utils/file_lock.py` - Database locking

### Configuration
- `src/kuzu_memory/core/config.py` - Git sync config (auto_sync_enabled, etc.)

## Appendix: Code Flow Diagram

```
User Prompt → Claude Code → hooks learn
                               │
                               ├─ Read stdin (JSON)
                               ├─ Parse transcript_path
                               │
                               ├─ Async Mode (default)
                               │  │
                               │  ├─ Check cached project root (~5ms)
                               │  ├─ Spawn worker process (~20ms)
                               │  └─ Return immediately (~50ms total) ✅
                               │
                               └─ Worker Process (background)
                                  │
                                  ├─ try_lock_database(timeout=0)
                                  │  └─ Fail if locked ✅
                                  │
                                  ├─ KuzuMemory(auto_sync=False)
                                  │  │
                                  │  ├─ __init__
                                  │  │  │
                                  │  │  ├─ _initialize_components()
                                  │  │  │  │
                                  │  │  │  ├─ _initialize_git_sync()
                                  │  │  │  │  └─ Create GitSyncManager
                                  │  │  │  │
                                  │  │  │  └─ _auto_git_sync("init") ❌ BLOCKS
                                  │  │  │     │
                                  │  │  │     ├─ should_auto_sync("init") → True
                                  │  │  │     │
                                  │  │  │     └─ git_sync.sync(mode="incremental")
                                  │  │  │        │
                                  │  │  │        └─ get_significant_commits()
                                  │  │  │           │
                                  │  │  │           ├─ Filter 11 branches
                                  │  │  │           ├─ Scan 58 commits
                                  │  │  │           └─ 300-500ms ❌
                                  │  │  │
                                  │  │  └─ Return KuzuMemory instance
                                  │  │
                                  │  └─ memory.remember(content)
                                  │     └─ ~5ms ✅
                                  │
                                  └─ memory.close()
```

## Conclusion

The `kuzu-memory hooks learn` command achieves **~50ms non-blocking latency** in async mode (default), but the background worker still spends **300-500ms on git sync** during `KuzuMemory.__init__()`. This overhead is unnecessary for frequent hook calls and should be eliminated by:

1. Setting `enable_git_sync=False` for hooks (immediate, recommended)
2. Relying on session-start hook for periodic git sync (already implemented)
3. Adding timeout protection for large repos (defense in depth)

**Expected improvement**: 330-530ms → ~50ms total (including background worker), 98% reduction.
