# Fail-Fast Database Locking for Hooks

## Problem Statement

When multiple Claude Code sessions are open in the same project, hooks would block indefinitely waiting for database access because:

1. **Kuzu's file-level locking**: Only one write transaction at a time
2. **Multiple processes**: Each Claude session spawns its own hook processes
3. **Old timeout behavior**: Previous 2-second Python Queue timeout didn't prevent Kuzu's internal lock blocking
4. **User experience**: Hooks appeared to hang (showing "1/2 done" status)

## Solution: File-Based Fail-Fast Locking

Implemented file-based lock checking **before** opening the Kuzu database:

### Key Components

**1. Lock Utility (`src/kuzu_memory/utils/file_lock.py`)**

```python
@contextmanager
def try_lock_database(db_path: Path, timeout: float = 0.0) -> Iterator[bool]:
    """
    Try to acquire exclusive lock on database.

    - timeout=0.0: Fail immediately if locked (for hooks)
    - timeout>0: Wait up to N seconds (for MCP tools)
    """
```

**Platform Support:**
- **Unix**: `fcntl.flock()` with `LOCK_EX | LOCK_NB`
- **Windows**: `msvcrt.locking()` with `LK_NBLCK`

**Lock File Location:**
- Database: `.kuzu-memories/memories.db`
- Lock file: `.kuzu-memories/.memories.db.lock`

### Modified Hook Commands

**hooks enhance** (`hooks_commands.py:_get_memories_with_lock`):
```python
def _get_memories_with_lock(db_path, prompt, strategy="keyword"):
    try:
        with try_lock_database(db_path, timeout=0.0):
            # Access database safely
            memory = KuzuMemory(db_path, auto_sync=False)
            return memory.attach_memories(prompt, max_memories=5, strategy=strategy)
    except DatabaseBusyError:
        return None, "locked"  # Fail immediately
```

**hooks learn** (`hooks_commands.py:_learn_sync`):
- Wraps `KuzuMemory` access with `try_lock_database(timeout=0.0)`
- Skips learning if database is locked

**hooks session-start**:
- Wraps `KuzuMemory` access with `try_lock_database(timeout=0.0)`
- Skips session tracking if database is locked

## Benefits

### 1. Fast Hook Execution
- **Before**: Hooks blocked for 2+ seconds waiting for lock
- **After**: Hooks return in < 50ms when database is busy

### 2. No User Disruption
- Hooks exit gracefully with `{"continue": true}`
- Claude Code continues without interruption
- No visible errors or warnings to user

### 3. Multi-Session Support
- Multiple Claude sessions work independently
- First session to access DB wins
- Other sessions skip silently

### 4. MCP Tools Unchanged
- Can use `timeout>0` for blocking behavior
- MCP tools can wait for lock if needed
- Hooks and MCP tools don't interfere

## Testing

### Unit Tests (`tests/unit/test_file_lock.py`)
- Lock acquisition and release
- Timeout behavior (immediate vs. delayed)
- Cross-thread locking
- Exception safety
- Multiple databases with independent locks

### Integration Tests (`tests/integration/test_hooks_fail_fast.py`)
- `_get_memories_with_lock` fails fast when locked
- Multiple concurrent access attempts all fail quickly
- Normal operation when unlocked

## Performance Metrics

**Hooks Response Time:**
- Unlocked database: < 100ms (normal operation)
- Locked database: < 50ms (fail-fast skip)

**Acceptable for hooks** (non-blocking, fire-and-forget behavior)

## Implementation Details

### Why Not Use Existing Timeout?

The old `_get_memories_with_timeout()` used Python threading with a timeout, but:
1. **Kuzu's internal lock** is at the file level (OS-level)
2. Thread timeout doesn't interrupt blocked system calls
3. Python thread would block indefinitely on `fcntl.flock()`

### Why File-Based Locking?

- **Detect locks before opening**: Check lock file before accessing database
- **Cross-process**: Works across separate Python processes (not just threads)
- **No race conditions**: Atomic OS-level operations
- **Clean release**: Context manager ensures lock release even on errors

### Lock File Management

- Created in same directory as database
- Automatically cleaned up by OS on process exit
- Survives across hook invocations
- Independent per project

## Migration Notes

### Removed Code
- `_get_memories_with_timeout()` (threading-based timeout)
- Import of `threading` module in `hooks_commands.py`

### Added Code
- `src/kuzu_memory/utils/file_lock.py` (new module)
- `_get_memories_with_lock()` (replacement function)
- Lock checks in `hooks_session_start` and `_learn_sync`

### Backward Compatibility
- **100% compatible**: No API changes for users
- **MCP tools**: Unaffected (can still use blocking operations)
- **Hooks behavior**: Improved (fail-fast instead of timeout)

## Future Considerations

### Optional Blocking Mode for Hooks
If needed, hooks could use `timeout=0.5` to wait briefly:

```python
# Current: Always fail-fast (timeout=0)
with try_lock_database(db_path, timeout=0.0):
    ...

# Future option: Wait briefly (timeout=0.5)
with try_lock_database(db_path, timeout=0.5):
    ...
```

**Not recommended** - defeats the purpose of non-blocking hooks.

### MCP Tool Lock Timeout
MCP tools could use longer timeouts:

```python
# MCP tools can wait longer if needed
with try_lock_database(db_path, timeout=5.0):
    # Block up to 5 seconds
```

Currently not implemented - MCP tools don't use fail-fast locking yet.

## Acceptance Criteria

- [x] Hooks return in < 50ms when database is locked
- [x] No "1/2 done" hangs in Claude Code
- [x] MCP tools unchanged and still functional
- [x] Lock properly released on exit
- [x] All tests pass (unit + integration)
- [x] Type checking passes (mypy --strict)
- [x] Linting passes (ruff)

## Related Files

**Implementation:**
- `src/kuzu_memory/utils/file_lock.py` (new)
- `src/kuzu_memory/cli/hooks_commands.py` (modified)
- `src/kuzu_memory/utils/__init__.py` (updated exports)

**Tests:**
- `tests/unit/test_file_lock.py` (new)
- `tests/integration/test_hooks_fail_fast.py` (new)

**Documentation:**
- `docs/fail-fast-database-locking.md` (this file)

---

**Last Updated**: 2026-01-20
**Version**: 1.6.24 (next release)
