# Bug Investigation: "Database path cannot be a directory" Error

**Date**: 2026-03-30
**Affected Project**: `/Users/masa/Duetto/repos/prod-int/`
**Error**: `Runtime exception: Database path cannot be a directory: /Users/masa/Duetto/repos/prod-int/.kuzu-memory`
**Kuzu Version**: 0.11.3

---

## Root Cause (Primary)

The MCP server's OLD `_get_db_path()` method (before commit `9835466`, March 27) returned the `.kuzu-memory` **directory** instead of `.kuzu-memory/memories.db` when that directory existed.

### Old (broken) code in `src/kuzu_memory/mcp/server.py`:
```python
new_path = self.project_root / ".kuzu-memory"
if new_path.exists():
    return new_path  # BUG: Returns directory, not memories.db file
```

### Fixed code (commit 9835466, now in v1.8.7):
```python
from ..utils.project_setup import get_project_db_path, migrate_db_location
migrate_db_location(self.project_root)
alt_legacy = self.project_root / ".kuzu-memories"
if alt_legacy.exists() and not (self.project_root / ".kuzu-memory").exists():
    return alt_legacy / "memories.db"
return get_project_db_path(self.project_root)  # Always returns .../memories.db
```

### Why the error occurs:
Kuzu 0.11.3 uses a single-file database format. When `kuzu.Database(path)` receives a path to an **existing directory**, it throws:
```
Runtime exception: Database path cannot be a directory: <path>
```

The `.kuzu-memory` directory exists in prod-int, and the old code was passing it directly to `kuzu.Database()`.

---

## How to Resolve for the User

The fix is already in v1.8.7. The issue is that the MCP server process is **stale** — it was started before the fix was installed and hasn't been restarted.

**Fix**: Restart the Claude Code session (or the MCP server) to load the updated code.

The `memories.db` file at `/Users/masa/Duetto/repos/prod-int/.kuzu-memory/memories.db` was verified to open correctly with kuzu 0.11.3 — it IS a valid kuzu database file.

---

## Secondary Issues Found

### 1. Missing `is_dir()` guard in tool methods

`_optimize()` has a guard for directory paths but `_recall()`, `_enhance()`, `_remember()`, and `_stats()` do not:

**In `_optimize` (has guard):**
```python
db_path = self._get_db_path()
if db_path.is_dir():
    db_path = db_path / "memories.db"  # Guard exists
```

**In `_recall`, `_enhance`, `_remember`, `_stats` (no guard):**
```python
db_path = self._get_db_path()
with MemoryService(db_path=db_path, ...) as memory:  # No guard
```

**Fix needed**: Add the `is_dir()` guard to all four methods for defensive programming.

### 2. Installer sets `KUZU_MEMORY_DB` to directory path

Multiple installers set `KUZU_MEMORY_DB` to the `.kuzu-memory` DIRECTORY instead of the `memories.db` file:

- `src/kuzu_memory/installers/mcp_installer_adapter.py:260`: `env.setdefault("KUZU_MEMORY_DB", str(self.project_root / ".kuzu-memory"))`
- `src/kuzu_memory/installers/codex_installer.py:69`: `"KUZU_MEMORY_DB": str(self.project_root / ".kuzu-memory")`
- `src/kuzu_memory/installers/auggie_mcp_installer.py:67`: `"KUZU_MEMORY_DB": str(self.project_root / ".kuzu-memory")`
- `src/kuzu_memory/installers/windsurf_installer.py:68`: `"KUZU_MEMORY_DB": str(self.project_root / ".kuzu-memory")`
- `src/kuzu_memory/installers/cursor_installer.py:64`: `"KUZU_MEMORY_DB": str(self.project_root / ".kuzu-memory")`
- `src/kuzu_memory/installers/vscode_installer.py:69`: `"KUZU_MEMORY_DB": str(self.project_root / ".kuzu-memory")`
- `src/kuzu_memory/installers/claude_hooks.py:105,582`: `"KUZU_MEMORY_DB": str(db_path)` where `db_path` = directory

While the MCP server itself doesn't currently use `KUZU_MEMORY_DB` (only `KUZU_MEMORY_PROJECT`), the `health_checker.py` does use it and could receive a directory path from the environment, causing health check failures.

**Fix needed**: Change all installer code to use `.kuzu-memory/memories.db` instead of `.kuzu-memory`.

### 3. `claude_hooks.py` has its own `_get_project_db_path()` that returns directory

In `src/kuzu_memory/installers/claude_hooks.py` (line 311-324):
```python
def _get_project_db_path(self) -> Path:
    """Returns: Path to project database DIRECTORY"""
    new_path = self.project_root / ".kuzu-memory"
    legacy_path = self.project_root / "kuzu-memories"
    if not new_path.exists() and legacy_path.exists():
        return legacy_path
    return new_path  # Returns the DIRECTORY, not memories.db
```

This is a different method from `utils/project_setup.py:get_project_db_path()` which correctly appends `memories.db`. The naming is confusing and the behavior is inconsistent.

**Note**: At line 2086, the code correctly appends `/memories.db` manually:
```python
db_path = self._get_project_db_path() / "memories.db"
```
But at lines 98 and 582, it does NOT:
```python
db_path = self._get_project_db_path()  # Returns directory
"KUZU_MEMORY_DB": str(db_path),  # Sets env to directory
```

---

## File Structure at Affected Project

```
/Users/masa/Duetto/repos/prod-int/
  .kuzu-memory/           <- Directory (correct)
    memories.db           <- Valid kuzu 0.11.3 single-file DB (2.1MB)
    README.md
    project_info.md
    .gitignore
```

- `memories.db` is a valid kuzu database (verified by opening with kuzu 0.11.3)
- The directory format `.kuzu-memory/memories.db` is the correct current format

---

## Recommended Fixes

### Immediate (user action):
Restart Claude Code or the MCP server to pick up the v1.8.7 fix.

### Code fixes needed:

1. **Add `is_dir()` guard to all tool methods** (`_recall`, `_enhance`, `_remember`, `_stats` in `src/kuzu_memory/mcp/server.py`):
   ```python
   db_path = self._get_db_path()
   if db_path.is_dir():
       db_path = db_path / "memories.db"
   ```

2. **Fix all installer `KUZU_MEMORY_DB` settings** to use the file path, not directory:
   ```python
   # Wrong:
   env["KUZU_MEMORY_DB"] = str(self.project_root / ".kuzu-memory")
   # Correct:
   env["KUZU_MEMORY_DB"] = str(self.project_root / ".kuzu-memory" / "memories.db")
   ```

3. **Rename or fix `claude_hooks.py:_get_project_db_path()`** to either:
   - Return the file path (rename to `_get_project_db_dir()` for clarity), OR
   - Fix the method to return `memories.db` like the canonical `utils/project_setup.py:get_project_db_path()`

---

## Code Flow for `kuzu_recall` MCP Tool

```
kuzu_recall("query") [MCP tool call]
  → server.py:_recall()
  → self._get_db_path()
      → get_project_db_path(self.project_root)
          → get_project_memories_dir(project_root)  # Returns .kuzu-memory/
          → memories_dir / "memories.db"             # Returns .kuzu-memory/memories.db
  → MemoryService(db_path=".kuzu-memory/memories.db")
  → KuzuMemory(db_path=".kuzu-memory/memories.db")
  → KuzuConnectionPool(db_path=".kuzu-memory/memories.db")
  → kuzu.Database(".kuzu-memory/memories.db")        # Should succeed
```

With the old code, step 3 returned `.kuzu-memory` (directory), causing the error at the `kuzu.Database()` call.
