# Circular Import Analysis: services → diagnostic_service → mcp → services

**Date**: 2026-03-10
**Project**: kuzu-memory
**Severity**: Blocker (prevents all unit tests that touch services/)

---

## 1. The Exact Cycle

```
kuzu_memory.services.__init__
  line 11: from kuzu_memory.services.diagnostic_service import DiagnosticService
    ↓
kuzu_memory.services.diagnostic_service
  line 10: from kuzu_memory.mcp.testing.diagnostics import MCPDiagnostics
  line 11: from kuzu_memory.mcp.testing.health_checker import MCPHealthChecker
    ↓
  Importing kuzu_memory.mcp.testing.* requires Python to initialize
  the parent package kuzu_memory.mcp first
    ↓
kuzu_memory.mcp.__init__
  line 15: from .server import MCP_AVAILABLE, KuzuMemoryMCPServer, SimplifiedMCPServer, main
    ↓
kuzu_memory.mcp.server
  line 20: from kuzu_memory.services import MemoryService
    ↓ BOOM: kuzu_memory.services is partially initialized
      (Python is still executing its __init__.py at line 11)
      MemoryService (defined at line 14) has NOT been added yet
```

### Step-by-step with file:line notation

| Step | File | Line | Symbol imported |
|------|------|------|-----------------|
| 1 | `services/__init__.py` | 11 | triggers load of `diagnostic_service.py` |
| 2 | `services/diagnostic_service.py` | 10 | `MCPDiagnostics` from `mcp.testing.diagnostics` |
| 3 | `mcp/testing/diagnostics.py` is a subpackage — Python must init `mcp/` first | — | — |
| 4 | `mcp/__init__.py` | 15 | `MCP_AVAILABLE, KuzuMemoryMCPServer, SimplifiedMCPServer, main` from `.server` |
| 5 | `mcp/server.py` | 20 | `MemoryService` from `kuzu_memory.services` |
| 6 | `kuzu_memory.services` is in `sys.modules` but its `__init__.py` is still executing at step 1 | — | `MemoryService` is not yet defined → `ImportError` |

The cycle-closing import is **`mcp/server.py` line 20**:
```python
from kuzu_memory.services import MemoryService
```

---

## 2. Why This Particular Import Closes the Cycle

Python's import system marks a module as "in sys.modules" the moment it begins executing, but its namespace is only partially populated until execution completes. When `services/__init__.py` is at line 11 (importing `DiagnosticService`), the `kuzu_memory.services` module object exists in `sys.modules` but only lines 1–10 have run. `MemoryService` (line 14) does not exist yet.

The chain then goes `diagnostic_service → mcp.testing.diagnostics → mcp/__init__ → mcp/server`, which asks for `MemoryService` from the half-built `services` module. Python finds the module in `sys.modules` (so no infinite recursion), but the name lookup fails.

---

## 3. What the SOA Migration (Batch 2) Did

The commit `4561a2a` ("refactor: complete SOA migration") only reformatted the import block in `diagnostic_service.py` (black formatting, no semantic change). The two cycle-creating lines were already present before that commit.

The actual introduction of the cycle happened in an earlier commit that added `DiagnosticService` to `services/__init__.py` (line 11) while keeping the `from kuzu_memory.mcp.testing...` top-level imports in `diagnostic_service.py`. The SOA migration did not introduce or worsen the cycle — it was pre-existing.

---

## 4. Additional Cycles

No additional cycles were found. The comprehensive grep of all `from kuzu_memory.(services|mcp)` imports shows:

- All other `services` imports inside `mcp/` are confined to `mcp/server.py` line 20 (the one in the cycle).
- All other `mcp` imports inside `services/` are confined to `diagnostic_service.py` lines 10–11.
- `cli/service_manager.py` imports `from kuzu_memory.services` but does so at function-call time (inside methods), not at module level — no cycle risk.
- `mcp/testing/__init__.py`, `diagnostics.py`, `health_checker.py`, and `connection_tester.py` do NOT import from `kuzu_memory.services` — they are clean.

---

## 5. Fix Recommendation

### Option A — Make mcp/server.py use a lazy import (BEST: minimal change, no restructuring)

Change `mcp/server.py` line 20 from a top-level import to an import inside `__init__` and any other method that needs it:

```python
# BEFORE (mcp/server.py line 20 — module level)
from kuzu_memory.services import MemoryService

# AFTER — move into KuzuMemoryMCPServer.__init__ and any other method that uses it
class KuzuMemoryMCPServer:
    def __init__(self, project_root: Path | None = None) -> None:
        from kuzu_memory.services import MemoryService  # lazy, breaks cycle
        ...
```

`MemoryService` is only needed when an instance is constructed, never at import time. Moving it inside `__init__` is safe and idiomatic. This is a 2-line change.

### Option B — Use TYPE_CHECKING guard in diagnostic_service.py (ALTERNATIVE)

If the concern is the other direction (diagnostic_service pulling in mcp at import time), move the `mcp.testing` imports to be lazy too:

```python
# BEFORE (diagnostic_service.py lines 10-11 — module level)
from kuzu_memory.mcp.testing.diagnostics import MCPDiagnostics
from kuzu_memory.mcp.testing.health_checker import MCPHealthChecker

# AFTER — move into DiagnosticService methods that actually call them
class DiagnosticService(BaseService):
    async def run_diagnostics(self, ...):
        from kuzu_memory.mcp.testing.diagnostics import MCPDiagnostics  # lazy
        ...
```

This keeps `mcp/server.py` clean but requires touching more methods in `DiagnosticService`.

### Option C — Remove DiagnosticService from services/__init__.py (RISKY)

Remove line 11 from `services/__init__.py` and import `DiagnosticService` directly from its module in callers. This hides the problem rather than fixing it and would break any code using `from kuzu_memory.services import DiagnosticService`.

### Recommended Fix: Option A

**File**: `src/kuzu_memory/mcp/server.py`
**Change**: Move `from kuzu_memory.services import MemoryService` from line 20 (module-level) into `KuzuMemoryMCPServer.__init__`.

Rationale:
- `mcp/server.py` is the correct place to fix because `mcp` legitimately depends on `services`, not the other way around — `services` should not know about `mcp`.
- It is the smallest possible change (one import, moved ~40 lines down).
- It follows the existing pattern in `cli/service_manager.py` where all service imports are inside methods.
- No API surface changes.
- After the fix: `services/__init__.py` loads cleanly; `mcp/__init__.py` loads cleanly; and `mcp/server.py` only resolves `MemoryService` when an MCP server instance is actually constructed.

---

## 6. Files Involved (Summary)

| File | Role in Cycle |
|------|--------------|
| `src/kuzu_memory/services/__init__.py:11` | Triggers load of `DiagnosticService` |
| `src/kuzu_memory/services/diagnostic_service.py:10-11` | Imports from `mcp.testing` at module level, forcing `mcp/` package init |
| `src/kuzu_memory/mcp/__init__.py:15` | Eagerly imports from `.server` |
| `src/kuzu_memory/mcp/server.py:20` | **Cycle-closing import** — imports `MemoryService` from partially-initialized `services` |
