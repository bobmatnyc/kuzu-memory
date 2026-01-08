# Auto-Update Infinite Loop Bug Analysis

**Date**: 2026-01-07
**Researcher**: Claude (Research Agent)
**Issue**: `kuzu-memory setup` triggers infinite update loop
**Status**: Root cause identified

---

## Executive Summary

The auto-update feature in kuzu-memory has a critical bug that causes an infinite loop during `kuzu-memory setup`. After successfully upgrading from version 1.6.10 to 1.6.13, the system restarts setup but immediately detects the same update again, creating an endless cycle.

**Root Cause**: Version mismatch between source code (`__version__.py`) and package metadata (`pyproject.toml`, `VERSION` file) causes the version checker to read stale version information after upgrade.

---

## Problem Description

### User Report
- Running `kuzu-memory setup` triggers auto-update detection
- Shows "Update available: 1.6.10 → 1.6.13"
- After upgrade completes, setup restarts
- **Bug**: Still detects update as available (should show 1.6.13 as current)
- Loops infinitely through upgrade → restart → detect update → upgrade cycle

### Expected Behavior
1. Detect update: 1.6.10 → 1.6.13
2. Upgrade package via pip/uv
3. Restart setup with new version
4. **Should see current version as 1.6.13** (no more updates)
5. Continue with normal setup

### Actual Behavior
1. Detect update: 1.6.10 → 1.6.13
2. Upgrade package via pip/uv ✅
3. Restart setup with new version ✅
4. **Still sees current version as 1.6.10** ❌
5. Detects update again → infinite loop

---

## Root Cause Analysis

### Version Source Files

The project has **three version sources** that can get out of sync:

1. **`src/kuzu_memory/__version__.py`** (Current: `1.6.10`)
   ```python
   __version__ = "1.6.10"
   ```

2. **`pyproject.toml`** (Current: `1.6.13`)
   ```toml
   [project]
   version = "1.6.13"
   ```

3. **`VERSION` file** (Current: `1.6.13`)
   ```
   1.6.13
   ```

### How Version Detection Works

**Location**: `src/kuzu_memory/cli/update_commands.py`

```python
class VersionChecker:
    def __init__(self) -> None:
        self.current_version = __version__  # Line 32
```

The `VersionChecker` imports and reads from `__version__.py`:

```python
from ..__version__ import __version__  # Line 19
```

### The Bug Sequence

1. **Initial State**:
   - `__version__.py` contains `1.6.10`
   - PyPI has `1.6.13`
   - Installed package is `1.6.10`

2. **First Update Check** (`_check_and_upgrade_if_needed()`):
   - Reads current version from `__version__.py` → `1.6.10` ✅
   - Fetches PyPI latest → `1.6.13` ✅
   - Comparison: `1.6.13 > 1.6.10` → Update available ✅

3. **Upgrade Process** (`_run_auto_upgrade()`):
   - Runs: `uv pip install --upgrade kuzu-memory` ✅
   - Downloads and installs version `1.6.13` from PyPI ✅
   - **Package metadata updated** (pyproject.toml shows 1.6.13) ✅
   - **But**: Running Python process still imports from OLD source files ❌

4. **Restart** (`_restart_setup_after_upgrade()`):
   - Executes: `os.execvp("kuzu-memory", ["kuzu-memory", "setup"])` ✅
   - Starts NEW Python process with kuzu-memory entry point ✅
   - **Should load new version**, but...

5. **Second Update Check** (after restart):
   - ❌ **BUG**: Still reads `__version__.py` containing `1.6.10`
   - ❌ Why? Because the **source file wasn't updated during pip install**
   - Fetches PyPI latest → `1.6.13`
   - Comparison: `1.6.13 > 1.6.10` → Update available again ❌
   - **Infinite loop begins**

### Why the Source File Isn't Updated

When `pip install --upgrade kuzu-memory` runs:

1. **Downloads**: Fetches `kuzu-memory-1.6.13.tar.gz` or `.whl` from PyPI
2. **Installs**: Extracts to site-packages (e.g., `.venv/lib/python3.12/site-packages/kuzu_memory/`)
3. **Overwrites**: Package files in site-packages are replaced with version 1.6.13
4. **Problem**: The `__version__.py` **in the source tree** (`src/kuzu_memory/__version__.py`) is **not touched**

**Key Insight**: When running from source (editable install with `pip install -e .` or `uv sync`), Python imports from the **local source directory**, not from site-packages. The local `__version__.py` remains at `1.6.10` even after upgrading the package on PyPI.

---

## Code Locations

### 1. Auto-Update Logic
**File**: `src/kuzu_memory/cli/setup_commands.py`

**Function**: `_check_and_upgrade_if_needed()` (Lines 28-94)
```python
def _check_and_upgrade_if_needed() -> bool:
    """
    Check for newer version and auto-upgrade if available.

    Returns:
        True if upgraded successfully, False otherwise
    """
    try:
        checker = VersionChecker()

        # Check for updates (non-blocking)
        check_result = checker.get_latest_version(include_pre=False)

        if check_result.get("error"):
            return False

        # Compare versions
        comparison = checker.compare_versions(check_result["version"])

        # No update available
        if not comparison["update_available"]:
            return False

        # Update available - show notification
        current = comparison["current"]
        latest = comparison["latest"]
        version_type = comparison["version_type"]

        rich_print(f"\n{emoji} Update available: {current} → {latest} ({version_type})",
                   style="cyan")
        rich_print("   Upgrading kuzu-memory automatically...", style="dim")

        # Attempt upgrade
        upgrade_result = _run_auto_upgrade()

        if upgrade_result["success"]:
            rich_print("   ✅ Successfully upgraded to latest version!", style="green")
            rich_print("   🔄 Restarting setup with new version...\n", style="dim")
            return True  # Signal that restart is needed
        else:
            rich_print(f"   ⚠️  Auto-upgrade failed: {upgrade_result.get('error')}",
                       style="yellow")
            return False

    except Exception:
        return False  # Silently fail - don't block setup
```

**Trigger**: Called in `setup()` command (Lines 275-289)
```python
# PHASE 0: VERSION CHECK & AUTO-UPGRADE
if not dry_run and not skip_version_check:
    upgraded = _check_and_upgrade_if_needed()

    if upgraded:
        # Successfully upgraded - restart setup with new version
        _restart_setup_after_upgrade(ctx)
        # If we reach here, restart failed - continue with new version
        rich_print("⚠️  Setup restart failed, but upgrade was successful.",
                   style="yellow")
```

### 2. Upgrade Execution
**File**: `src/kuzu_memory/cli/setup_commands.py`

**Function**: `_run_auto_upgrade()` (Lines 97-138)
```python
def _run_auto_upgrade() -> dict[str, bool | str | None]:
    """
    Execute upgrade using uv or pip (with uv preferred).

    Returns:
        dict with keys:
            - success: bool
            - error: str | None
    """
    try:
        # Check if uv is available
        uv_available = shutil.which("uv") is not None

        if uv_available:
            # Use uv pip install --upgrade
            result = subprocess.run(
                ["uv", "pip", "install", "--upgrade", "kuzu-memory"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        else:
            # Fallback to pip
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "kuzu-memory"],
                capture_output=True,
                text=True,
                timeout=60,
            )

        if result.returncode == 0:
            return {"success": True, "error": None}
        else:
            return {"success": False, "error": result.stderr.strip() or "Upgrade failed"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Upgrade timed out after 60 seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 3. Restart Logic
**File**: `src/kuzu_memory/cli/setup_commands.py`

**Function**: `_restart_setup_after_upgrade()` (Lines 141-160)
```python
def _restart_setup_after_upgrade(ctx: click.Context) -> None:
    """
    Re-execute setup command after successful upgrade.

    Preserves all command-line flags from original invocation.
    """
    try:
        # Get original command line arguments
        args = sys.argv[1:]  # Skip script name

        # Re-execute kuzu-memory with same arguments
        os.execvp("kuzu-memory", ["kuzu-memory", *args])

    except Exception as e:
        # If re-execution fails, just continue with current version
        rich_print(f"⚠️  Could not restart setup: {e}", style="yellow")
        rich_print("   Continuing with newly installed version...\n", style="dim")
```

**Note**: `os.execvp()` replaces the current process with a new one, so if successful, code after this line never runs.

### 4. Version Checker
**File**: `src/kuzu_memory/cli/update_commands.py`

**Class**: `VersionChecker` (Lines 25-165)
```python
class VersionChecker:
    """Handles version checking against PyPI."""

    PYPI_API_URL = "https://pypi.org/pypi/kuzu-memory/json"
    TIMEOUT = 10  # seconds

    def __init__(self) -> None:
        self.current_version = __version__  # ← BUG: Reads from __version__.py

    def get_latest_version(self, include_pre: bool = False) -> dict[str, Any]:
        """Fetch latest version from PyPI."""
        # Fetches from PyPI API
        # Returns {"version": "1.6.13", "release_date": "...", ...}

    def compare_versions(self, latest: str) -> dict[str, Any]:
        """Compare current vs latest version."""
        from packaging.version import Version

        current_ver = Version(self.current_version)  # 1.6.10
        latest_ver = Version(latest)                  # 1.6.13

        update_available = latest_ver > current_ver   # True (BUG!)

        return {
            "current": self.current_version,
            "latest": latest,
            "update_available": update_available,
            "version_type": "patch"  # or "major"/"minor"
        }
```

### 5. Version Definition
**File**: `src/kuzu_memory/__version__.py`
```python
__version__ = "1.6.10"  # ← Source of truth (STALE!)
__version_info__ = tuple(int(i) for i in __version__.split("."))

# Database schema version for migration support
DB_SCHEMA_VERSION = "1.0"
```

**Import Chain**:
```
update_commands.py (Line 19)
  → from ..__version__ import __version__
    → reads from src/kuzu_memory/__version__.py
      → contains "1.6.10" (STALE!)
```

---

## Why This Happens

### Development vs Production Version Management

The project uses a **hybrid version management approach**:

1. **Development (Source)**: Version stored in `__version__.py`
2. **Distribution (Package)**: Version stored in `pyproject.toml`
3. **Version File**: `VERSION` file (likely for CI/CD)

### The Disconnect

When developing locally with `uv sync` or `pip install -e .` (editable install):

- Python imports from **source directory**: `src/kuzu_memory/__version__.py`
- Package manager reads from **pyproject.toml** for metadata
- Upgrading via pip **doesn't update source files**

### When the Bug Occurs

The infinite loop happens when:

1. ✅ User is running from **source** (development mode)
2. ✅ `__version__.py` is **behind** published version on PyPI
3. ✅ Auto-update is **enabled** (not `--skip-version-check`)
4. ✅ Upgrade **succeeds** but source file remains stale

---

## Solutions

### Immediate Fix Options

#### Option 1: Update `__version__.py` to Match Package Version (Quick Fix)
**Action**: Update source file to current version

```bash
# Update __version__.py
echo '__version__ = "1.6.13"' > src/kuzu_memory/__version__.py
echo '__version_info__ = tuple(int(i) for i in __version__.split("."))\n' >> src/kuzu_memory/__version__.py
echo '# Database schema version for migration support' >> src/kuzu_memory/__version__.py
echo 'DB_SCHEMA_VERSION = "1.0"' >> src/kuzu_memory/__version__.py

# Or use version bump script if available
./scripts/manage_version.py set 1.6.13
```

**Pros**:
- Immediate resolution
- Stops infinite loop right away

**Cons**:
- Manual fix, doesn't prevent future occurrences
- Doesn't address root cause

#### Option 2: Disable Auto-Update Temporarily
**Action**: Use `--skip-version-check` flag

```bash
kuzu-memory setup --skip-version-check
```

**Pros**:
- Bypasses broken update logic
- Allows setup to proceed

**Cons**:
- Disables a useful feature
- Doesn't fix the bug

### Long-Term Solutions

#### Solution A: Single Source of Truth for Version
**Implementation**: Use `pyproject.toml` as the only version source

**Changes Required**:

1. **Remove `__version__.py`** or make it dynamic:
   ```python
   # src/kuzu_memory/__version__.py
   from importlib.metadata import version

   try:
       __version__ = version("kuzu-memory")
   except Exception:
       __version__ = "0.0.0.dev"  # Fallback for development

   __version_info__ = tuple(int(i) for i in __version__.split("."))
   DB_SCHEMA_VERSION = "1.0"
   ```

2. **Update imports**:
   ```python
   # src/kuzu_memory/cli/update_commands.py
   from importlib.metadata import version

   class VersionChecker:
       def __init__(self) -> None:
           self.current_version = version("kuzu-memory")
   ```

**Pros**:
- Single source of truth (pyproject.toml)
- Automatically reflects installed version
- No manual sync needed

**Cons**:
- Requires changes across codebase
- May break if package not installed
- Need fallback for development mode

#### Solution B: Sync Version Files During Build
**Implementation**: Automated version synchronization in build process

**Changes Required**:

1. **Add version sync script**:
   ```python
   # scripts/sync_versions.py
   import tomli
   from pathlib import Path

   def sync_versions():
       # Read version from pyproject.toml
       with open("pyproject.toml", "rb") as f:
           data = tomli.load(f)
           version = data["project"]["version"]

       # Update __version__.py
       version_file = Path("src/kuzu_memory/__version__.py")
       version_file.write_text(f'__version__ = "{version}"\n'
                               f'__version_info__ = tuple(int(i) for i in __version__.split("."))\n'
                               f'DB_SCHEMA_VERSION = "1.0"\n')

       # Update VERSION file
       Path("VERSION").write_text(f"{version}\n")

       print(f"✅ Synced version to {version}")
   ```

2. **Add to pre-publish checks**:
   ```makefile
   # Makefile
   pre-publish:
       python scripts/sync_versions.py
       ruff check
       pytest
       mypy
   ```

3. **Add to CI/CD**:
   ```yaml
   # .github/workflows/publish.yml
   - name: Sync versions
     run: python scripts/sync_versions.py

   - name: Build package
     run: uv build
   ```

**Pros**:
- Prevents version drift
- Automated in release process
- Maintains existing structure

**Cons**:
- Requires discipline to run script
- Can still get out of sync during development

#### Solution C: Detect Stale Version and Skip Update
**Implementation**: Add staleness check before upgrade

**Changes Required**:

```python
# src/kuzu_memory/cli/setup_commands.py

def _is_version_file_stale() -> bool:
    """
    Check if __version__.py is behind installed package version.

    Returns:
        True if __version__.py is stale, False otherwise
    """
    try:
        from importlib.metadata import version as get_installed_version
        from ..__version__ import __version__ as source_version

        installed = get_installed_version("kuzu-memory")

        # If source version is behind installed version, it's stale
        from packaging.version import Version
        return Version(source_version) < Version(installed)

    except Exception:
        return False

def _check_and_upgrade_if_needed() -> bool:
    """Check for newer version and auto-upgrade if available."""
    try:
        # Check if source version is stale (already upgraded)
        if _is_version_file_stale():
            rich_print(
                "\n⚠️  Version mismatch detected (source file stale)",
                style="yellow"
            )
            rich_print(
                "   Skipping auto-update to prevent infinite loop.",
                style="dim"
            )
            rich_print(
                "   Run 'kuzu-memory update --check-only' to verify version.",
                style="dim"
            )
            return False

        checker = VersionChecker()
        # ... rest of existing logic
```

**Pros**:
- Defensive fix - prevents infinite loop
- Doesn't require version management changes
- Provides user feedback about issue

**Cons**:
- Doesn't fix root cause
- Band-aid solution
- User still sees confusing warnings

#### Solution D: Invalidate Python Cache After Upgrade
**Implementation**: Force Python to reload modules after upgrade

**Changes Required**:

```python
def _restart_setup_after_upgrade(ctx: click.Context) -> None:
    """Re-execute setup command after successful upgrade."""
    try:
        # Get original command line arguments
        args = sys.argv[1:]

        # Set environment variable to invalidate Python cache
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"  # Disable .pyc files
        env["KUZU_MEMORY_UPGRADED"] = "1"     # Flag to skip update check

        # Re-execute with clean environment
        os.execvpe("kuzu-memory", ["kuzu-memory", *args], env)

    except Exception as e:
        rich_print(f"⚠️  Could not restart setup: {e}", style="yellow")

def _check_and_upgrade_if_needed() -> bool:
    """Check for newer version and auto-upgrade if available."""
    # Skip if we just upgraded (detected by env var)
    if os.environ.get("KUZU_MEMORY_UPGRADED"):
        return False

    # ... rest of existing logic
```

**Pros**:
- Prevents immediate re-check after upgrade
- Simple environment variable check
- Minimal code changes

**Cons**:
- Doesn't fix version source issue
- Only prevents one iteration of loop
- Could still loop if env var not passed correctly

---

## Recommended Solution

**Primary Recommendation**: **Solution A + Solution B** (Single Source of Truth + Build Automation)

### Implementation Plan

1. **Immediate Fix** (Stop the bleeding):
   - Update `__version__.py` to `1.6.13` manually
   - Add environment variable check (Solution D) to prevent immediate loops

2. **Short-Term Fix** (Next release):
   - Implement Solution C (staleness detection) as defensive measure
   - Add warning in documentation about version file management

3. **Long-Term Fix** (v2.0):
   - Migrate to `importlib.metadata` for version detection (Solution A)
   - Add version sync script to CI/CD pipeline (Solution B)
   - Remove manual version management entirely

### Migration Steps

**Phase 1: Immediate (v1.6.14)**
```bash
# 1. Sync version files
echo '__version__ = "1.6.13"' > src/kuzu_memory/__version__.py

# 2. Add staleness check
# (Implement Solution C in setup_commands.py)

# 3. Release patch
./scripts/manage_version.py bump patch  # 1.6.14
make safe-release-build
make release-pypi
```

**Phase 2: Next Minor (v1.7.0)**
```python
# 1. Add importlib.metadata fallback
# src/kuzu_memory/__version__.py
from importlib.metadata import version

try:
    __version__ = version("kuzu-memory")
except Exception:
    __version__ = "1.7.0"  # Fallback

# 2. Add version sync script
# scripts/sync_versions.py

# 3. Update CI/CD
# .github/workflows/publish.yml
```

**Phase 3: Major Release (v2.0.0)**
```python
# 1. Remove __version__.py entirely
# 2. Use importlib.metadata everywhere
# 3. pyproject.toml as single source of truth
```

---

## Testing Strategy

### Reproduce the Bug

```bash
# 1. Set source version to old version
echo '__version__ = "1.6.10"' > src/kuzu_memory/__version__.py

# 2. Run setup (should trigger auto-update)
kuzu-memory setup

# Expected: Infinite loop (update → restart → update → restart)
# Actual: Infinite loop confirmed
```

### Verify Fix (Solution C - Staleness Detection)

```bash
# 1. Apply staleness check patch
# (Add _is_version_file_stale() function)

# 2. Set source version to old version
echo '__version__ = "1.6.10"' > src/kuzu_memory/__version__.py

# 3. Install newer version via pip
pip install --upgrade kuzu-memory

# 4. Run setup
kuzu-memory setup

# Expected: Warning about stale version, skip auto-update, continue setup
# Should NOT loop infinitely
```

### Verify Fix (Solution A - importlib.metadata)

```bash
# 1. Apply importlib.metadata patch
# (Update __version__.py to use importlib.metadata)

# 2. Install package
pip install -e .

# 3. Verify version detection
python -c "from kuzu_memory.__version__ import __version__; print(__version__)"
# Expected: Should print installed version from package metadata

# 4. Run setup
kuzu-memory setup

# Expected: Correct version detected, no false update detection
```

---

## Impact Assessment

### Severity: **HIGH**

**User Impact**:
- ⚠️ **Blocks setup command** - Primary onboarding path broken
- ⚠️ **Infinite loop** - Consumes system resources, confuses users
- ⚠️ **No workaround without documentation** - Users stuck unless they know `--skip-version-check`

### Affected Users

**Who is affected**:
- Users running from **source** (development mode)
- Users with **editable install** (`pip install -e .`)
- Users who **cloned repo** and ran `uv sync`

**Who is NOT affected**:
- Users who installed from **PyPI** (`pip install kuzu-memory`)
- Users running **packaged version** (not editable install)
- Users with `--skip-version-check` flag

### Frequency

**Current State**:
- Affects **any user running from source** when version files are out of sync
- Occurs **on every `kuzu-memory setup` run** until fixed
- **100% reproducible** with stale version file

---

## Related Issues

### Version Management Confusion

The project has multiple version sources that can get out of sync:

1. `src/kuzu_memory/__version__.py` - Source code version
2. `pyproject.toml` - Package metadata version
3. `VERSION` - CI/CD version file

This creates confusion and maintenance burden:
- Developers must remember to update all three
- Easy to forget one during version bump
- No automated verification of sync

### Similar Patterns in Codebase

Search for other areas that might read version incorrectly:

```bash
# Check for direct __version__ imports
grep -r "from.*__version__ import" src/

# Results:
# - cli/update_commands.py (VersionChecker) ← Bug location
# - cli/commands.py (version display) ← Potential issue
# - mcp/server.py (MCP server metadata) ← Potential issue
# - mcp/run_server.py (startup banner) ← Potential issue
```

All these locations read from `__version__.py` and could show stale versions.

---

## References

### Code Files
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/setup_commands.py` (Lines 28-289)
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/update_commands.py` (Lines 25-165)
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/__version__.py` (Lines 1-6)
- `/Users/masa/Projects/kuzu-memory/pyproject.toml` (version field)
- `/Users/masa/Projects/kuzu-memory/VERSION` (version file)

### Related Patterns
- Auto-update pattern in CLI tools
- Python package version management
- Single source of truth principle
- Editable installs vs packaged installs

---

## Next Steps

### For Immediate Resolution
1. ✅ **Document the bug** - This research file
2. 🔲 **Update `__version__.py`** to `1.6.13`
3. 🔲 **Add staleness detection** (Solution C)
4. 🔲 **Release patch version** (v1.6.14)
5. 🔲 **Add user-facing documentation** about `--skip-version-check`

### For Long-Term Fix
1. 🔲 **Create version sync script** (Solution B)
2. 🔲 **Migrate to importlib.metadata** (Solution A)
3. 🔲 **Update CI/CD pipeline** to auto-sync versions
4. 🔲 **Add pre-commit hook** to verify version sync
5. 🔲 **Remove manual version management** from process

### For Testing
1. 🔲 **Add integration test** for update loop scenario
2. 🔲 **Add unit test** for staleness detection
3. 🔲 **Add CI check** for version file sync
4. 🔲 **Document testing procedure** for version-related changes

---

## Appendix: Version Management Best Practices

### Option 1: `importlib.metadata` (Recommended for Python 3.8+)
```python
from importlib.metadata import version
__version__ = version("package-name")
```
**Pros**: Always reflects installed version, no sync needed
**Cons**: Requires package to be installed

### Option 2: `setuptools_scm` (Git-Based)
```toml
[build-system]
requires = ["setuptools>=45", "setuptools_scm[toml]>=6.2"]

[tool.setuptools_scm]
write_to = "src/package/__version__.py"
```
**Pros**: Single source of truth (git tags), automated
**Cons**: Requires git tags, complex setup

### Option 3: `pyproject.toml` Only (Modern Python)
```toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "package.__version__"}
```
**Pros**: Clean, modern, PEP 621 compliant
**Cons**: Still requires sync if using static file

### Option 4: Build-Time Generation
```python
# setup.py or build hook
with open("VERSION") as f:
    version = f.read().strip()

with open("src/package/__version__.py", "w") as f:
    f.write(f'__version__ = "{version}"\n')
```
**Pros**: Single source (VERSION file), generated during build
**Cons**: Manual step, can be forgotten

---

**END OF RESEARCH DOCUMENT**
