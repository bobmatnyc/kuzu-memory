# Issue #2 Investigation: ModuleNotFoundError for py_mcp_installer.self_updater

**Investigation Date**: 2026-01-17
**Issue Number**: #2
**Issue State**: OPEN
**Current Version**: 1.6.19

## Executive Summary

**Status**: ❌ **BUG STILL PRESENT**

The bug reported in issue #2 has NOT been fully resolved. While commit `474f54a` attempted to fix the issue by converting py-mcp-installer from a vendored dependency to a PyPI dependency, the `self_updater` module is still not available in the py-mcp-installer package.

## Issue Details

### Original Error Report

**Reporter**: Ray
**Version Affected**: 1.6.14 (after upgrading from 1.6.13)

```
ModuleNotFoundError: No module named 'py_mcp_installer.self_updater'
  File: .../kuzu_memory/cli/setup_commands.py, line 26
  from py_mcp_installer.self_updater import InstallMethod, SelfUpdater
```

### Root Cause Analysis

The py-mcp-installer package (version 0.1.5) **does not include a `self_updater` module**. The package contains:

**Available modules in py_mcp_installer 0.1.5:**
- `__init__.py`
- `cli.py`
- `command_builder.py`
- `config_manager.py`
- `exceptions.py`
- `installation_strategy.py`
- `installer.py`
- `mcp_doctor.py`
- `mcp_inspector.py`
- `platform_detector.py`
- `platforms/` (directory)
- `types.py`
- `utils.py`

**Missing module:**
- ❌ `self_updater.py` - Does not exist in py_mcp_installer 0.1.5

## Current Code State (v1.6.19)

### Location: `src/kuzu_memory/cli/setup_commands.py`

**Lines 24-33** (Problematic import):
```python
# Import SelfUpdater from py-mcp-installer package
try:
    from py_mcp_installer.self_updater import InstallMethod, SelfUpdater

    HAS_SELF_UPDATER = True
except ImportError:
    # Gracefully handle missing dependency (for older installations during upgrade)
    HAS_SELF_UPDATER = False
    InstallMethod = None  # type: ignore[assignment]
    SelfUpdater = None  # type: ignore[assignment]
```

**Line 26 specifically** attempts to import `SelfUpdater` and `InstallMethod` from `py_mcp_installer.self_updater`, which does not exist.

### Dependency Declaration

**File**: `pyproject.toml` (line 40)
```toml
dependencies = [
    ...
    "py-mcp-installer>=0.1.5",  # Universal MCP server installer for AI coding tools
]
```

The dependency is correctly declared, but the expected module is not present in the package.

## Evidence of Bug

### Test Results

```bash
# Import test with uv run (project environment)
$ uv run python -c "from py_mcp_installer.self_updater import SelfUpdater, InstallMethod"
ModuleNotFoundError: No module named 'py_mcp_installer.self_updater'
```

```bash
# Package inspection
$ uv pip show py-mcp-installer
Name: py-mcp-installer
Version: 0.1.5
Location: .venv/lib/python3.12/site-packages
Requires: pydantic, tomli-w, typing-extensions
Required-by: kuzu-memory
```

```bash
# Module contents inspection
$ uv run python -c "import py_mcp_installer; print(dir(py_mcp_installer))"
# Output includes InstallMethod but NO SelfUpdater
['ArgsList', 'AtomicWriteError', ..., 'InstallMethod', 'InstallationError', ...]
# SelfUpdater is NOT in the list
```

### Version Discrepancy

```bash
$ uv run python -c "import py_mcp_installer; print(f'Version: {py_mcp_installer.__version__}')"
Version: 0.1.4  # Module reports 0.1.4

$ uv pip list | grep py-mcp-installer
py-mcp-installer 0.1.5  # Package manager shows 0.1.5
```

There's also a version mismatch where the installed package is 0.1.5 but the module itself reports 0.1.4.

## Attempted Fix (Incomplete)

**Commit**: `474f54a49b67b4040598af40e5dbf2d03695c8a0`
**Date**: 2026-01-13
**Author**: Bob Matsuoka

### Changes Made:
1. ✅ Added `py-mcp-installer>=0.1.5` as a PyPI dependency
2. ✅ Removed vendor path fallback in `mcp_installer_adapter.py`
3. ✅ Added try/except for graceful handling of missing SelfUpdater module

### Why the Fix is Incomplete:
The try/except block prevents the import error from **crashing the application**, but it does NOT fix the underlying issue. The `self_updater` module simply doesn't exist in py-mcp-installer 0.1.5.

**Result**: The upgrade functionality in `setup_commands.py` is silently disabled because `HAS_SELF_UPDATER` is always `False`.

## Impact Assessment

### Current Behavior
- ✅ CLI does not crash (graceful degradation works)
- ❌ Auto-upgrade functionality is completely disabled
- ❌ `_check_and_upgrade_if_needed()` always returns `False` immediately
- ❌ Users cannot use the automatic version upgrade feature

### Affected Functionality

**Function**: `_check_and_upgrade_if_needed()` (lines 36-140)
**Status**: **DEAD CODE** - Never executes upgrade logic

The entire auto-upgrade workflow is disabled:
```python
def _check_and_upgrade_if_needed() -> bool:
    try:
        # Skip if py-mcp-installer is not available
        if not HAS_SELF_UPDATER:
            return False  # <-- ALWAYS returns here

        # All code below is unreachable
        ...
```

## Root Cause

The py-mcp-installer package on PyPI does not include a `self_updater` module. This could mean:

1. **Wrong package dependency**: kuzu-memory may be depending on the wrong package
2. **Missing feature**: py-mcp-installer 0.1.5 doesn't include self-update functionality
3. **API mismatch**: The expected API (SelfUpdater class) doesn't exist in the upstream package
4. **Documentation issue**: The package may have a different upgrade mechanism

## Recommendations

### Option 1: Remove Dead Code (Quick Fix)
Remove the non-functional upgrade code entirely and document that users should upgrade manually.

**Pros**: Cleans up codebase, honest about capabilities
**Cons**: Removes upgrade feature

### Option 2: Investigate Upstream Package
Contact py-mcp-installer maintainer to:
- Confirm if `self_updater` module should exist
- Request addition of self-update functionality
- Clarify correct upgrade API

**Pros**: Potentially restores upgrade functionality
**Cons**: Depends on external package changes

### Option 3: Implement Native Upgrade Logic
Build kuzu-memory's own upgrade mechanism without depending on py-mcp-installer.

**Pros**: Full control, no external dependency
**Cons**: Additional maintenance burden

### Option 4: Import from Different Source
Check if `InstallMethod` is available from the main module:

```python
from py_mcp_installer import InstallMethod  # Already works
# Create custom SelfUpdater or use different upgrade approach
```

## Related Commits

- `474f54a` - fix: convert vendored py-mcp-installer to PyPI dependency (2026-01-13)
- Commit claimed to fix issue #3, but issue #2 remains unresolved

## Next Steps

1. **Verify issue #2 is distinct from issue #3** - check GitHub issue tracker
2. **Contact py-mcp-installer maintainer** - clarify expected API
3. **Test alternative import paths** - check if SelfUpdater exists elsewhere
4. **Update issue #2 status** - document that bug persists in 1.6.19
5. **Consider implementing native upgrade logic** - reduce external dependencies

## Conclusion

**Bug Status**: ❌ **NOT FIXED**

While the try/except wrapper prevents crashes (graceful degradation), the core issue remains: the `self_updater` module does not exist in py-mcp-installer 0.1.5. The auto-upgrade feature is completely non-functional in kuzu-memory v1.6.19.

The issue should remain **OPEN** until one of the recommended solutions is implemented.

---

**Researchers**: Claude Opus 4.5 (Research Agent)
**Files Analyzed**:
- `pyproject.toml`
- `src/kuzu_memory/cli/setup_commands.py`
- `.venv/lib/python3.12/site-packages/py_mcp_installer/`
- Git commit history

**Verification Commands**:
```bash
# Test import
uv run python -c "from py_mcp_installer.self_updater import SelfUpdater"

# Inspect package
uv pip show py-mcp-installer
ls -la .venv/lib/python3.12/site-packages/py_mcp_installer/

# Check version
uv run python -c "import py_mcp_installer; print(py_mcp_installer.__version__)"
```
