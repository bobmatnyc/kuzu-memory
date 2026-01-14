# PyPI Package Investigation: Broken Vendored Dependency

**Research Date**: 2025-01-13
**Package Version**: kuzu-memory 1.6.14
**Issue**: ModuleNotFoundError: No module named 'py_mcp_installer'

## Executive Summary

The kuzu-memory 1.6.14 PyPI package is broken because it attempts to import from `py_mcp_installer`, which is vendored as a git submodule but **not included in the published wheel/sdist**. The vendored dependency approach is fundamentally incompatible with standard Python packaging.

## Root Cause Analysis

### 1. Vendoring Strategy vs. PyPI Distribution

**Current Architecture**:
- `vendor/py-mcp-installer-service/` exists as a git submodule
- Code attempts to import via: `from py_mcp_installer.self_updater import ...`
- Fallback mechanism adds vendor path to sys.path: `sys.path.insert(0, str(vendor_path))`

**The Problem**:
Git submodules are **NOT** included when building Python packages for PyPI distribution. The `vendor/` directory exists only in the git repository, not in the published wheel or source distribution.

### 2. Package Structure Evidence

**Git Repository Structure** (development):
```
kuzu-memory/
├── vendor/
│   └── py-mcp-installer-service/  # Git submodule
│       └── src/
│           └── py_mcp_installer/  # The actual Python package
│               ├── __init__.py
│               ├── self_updater.py
│               ├── installer.py
│               └── ...
└── src/
    └── kuzu_memory/
        ├── cli/
        │   └── setup_commands.py  # Imports py_mcp_installer
        └── installers/
            └── mcp_installer_adapter.py  # Also imports py_mcp_installer
```

**Published Wheel Structure** (PyPI):
```
kuzu_memory-1.6.14-py3-none-any.whl
├── kuzu_memory/
│   ├── __init__.py
│   ├── cli/
│   │   └── setup_commands.py  # ❌ Still tries to import py_mcp_installer
│   └── installers/
│       └── mcp_installer_adapter.py  # ❌ Still tries to import
└── kuzu_memory-1.6.14.dist-info/
    └── ...
# ❌ NO vendor/ directory
# ❌ NO py_mcp_installer/ package
```

### 3. Import Failure Point

**File**: `src/kuzu_memory/cli/setup_commands.py` (lines 24-33)
```python
# Import SelfUpdater from vendored py-mcp-installer-service
try:
    from py_mcp_installer.self_updater import InstallMethod, SelfUpdater
except ImportError:
    # Fallback to vendored version if not installed
    vendor_path = (
        Path(__file__).parent.parent.parent.parent / "vendor" / "py-mcp-installer-service" / "src"
    )
    sys.path.insert(0, str(vendor_path))
    from py_mcp_installer.self_updater import InstallMethod, SelfUpdater
```

**Why it fails in published package**:
1. First import attempt fails: `py_mcp_installer` is not installed as a dependency
2. Fallback calculates path: `Path(__file__).parent.parent.parent.parent / "vendor" / ...`
3. In published wheel, `vendor/` directory doesn't exist
4. Second import attempt also fails → `ModuleNotFoundError`

### 4. Packaging Configuration Issues

**pyproject.toml analysis**:
```toml
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-dir]
"" = "src"

[tool.setuptools.package-data]
kuzu_memory = [
    "installers/templates/**/*.py",
    "installers/templates/**/*.sh"
]
```

**Problems**:
- ✅ Correctly finds packages in `src/`
- ❌ No configuration to include `vendor/` directory
- ❌ No `MANIFEST.in` to explicitly include vendored code
- ❌ `vendor/` is not under `src/`, so it's automatically excluded
- ❌ Git submodules are never included by setuptools anyway

### 5. py-mcp-installer is Available on PyPI

**Key Finding**: `py-mcp-installer` is **published on PyPI**!

**PyPI Package Details**:
- **Package Name**: `py-mcp-installer`
- **Current Version**: 0.1.5 (released 2025-12-18)
- **Python Support**: >=3.10 (3.10, 3.11, 3.12)
- **License**: MIT
- **Maintainer**: bobmatnyc (Bob Matlack)
- **Repository**: https://github.com/bobmatnyc/py-mcp-installer-service

**This is the same author/maintainer as kuzu-memory**, meaning there's no external dependency risk.

## Recommended Fix Approach

### Option 1: Use PyPI Dependency (RECOMMENDED)

**Advantages**:
- ✅ Follows standard Python packaging practices
- ✅ Automatic version management via PyPI
- ✅ Works immediately for all users
- ✅ No complex vendoring or path manipulation
- ✅ Package is already published and maintained by same author

**Implementation**:
```toml
# pyproject.toml
dependencies = [
    # ... existing dependencies ...
    "py-mcp-installer>=0.1.5",  # Add this
]
```

**Code changes required**:
```python
# src/kuzu_memory/cli/setup_commands.py
# REMOVE fallback mechanism, just import directly:
from py_mcp_installer.self_updater import InstallMethod, SelfUpdater

# src/kuzu_memory/installers/mcp_installer_adapter.py
# REMOVE sys.path manipulation, just import directly:
from py_mcp_installer import (
    DiagnosticReport,
    MCPInstaller,
    Platform,
    # ... etc
)
```

**Migration steps**:
1. Add `py-mcp-installer>=0.1.5` to `dependencies` in `pyproject.toml`
2. Remove vendor path manipulation from `setup_commands.py`
3. Remove vendor path manipulation from `mcp_installer_adapter.py`
4. Update `CLAUDE.md` to reflect PyPI dependency instead of vendoring
5. Remove git submodule (optional): `git submodule deinit vendor/py-mcp-installer-service`
6. Bump version to 1.6.15
7. Test build and installation
8. Publish to PyPI

### Option 2: Properly Vendor the Code (NOT RECOMMENDED)

This would require copying the code directly into the kuzu-memory source tree, not using git submodules.

**Disadvantages**:
- ❌ Code duplication
- ❌ Manual version updates required
- ❌ Potential license compliance issues
- ❌ Maintenance burden
- ❌ No clear benefit over using PyPI package

**Implementation** (if absolutely necessary):
```
src/kuzu_memory/
└── _vendor/  # Internal vendored packages
    └── py_mcp_installer/  # Direct copy, not submodule
        ├── __init__.py
        ├── self_updater.py
        └── ...
```

Then import as: `from kuzu_memory._vendor.py_mcp_installer import ...`

### Option 3: Make py-mcp-installer Optional (PARTIAL FIX)

Make the import gracefully fail without breaking the package.

**Advantages**:
- ✅ Package installs without error
- ✅ Core functionality remains available

**Disadvantages**:
- ❌ MCP installation features broken
- ❌ User confusion when features don't work
- ❌ Not a real solution

**Implementation**:
```python
# Mark as optional dependency
try:
    from py_mcp_installer.self_updater import InstallMethod, SelfUpdater
    HAS_MCP_INSTALLER = True
except ImportError:
    HAS_MCP_INSTALLER = False

def _check_and_upgrade_if_needed() -> bool:
    if not HAS_MCP_INSTALLER:
        logger.warning("py-mcp-installer not available, skipping upgrade check")
        return False
    # ... rest of implementation
```

## Recommended Solution

**Use Option 1: Add py-mcp-installer as a PyPI dependency**

### Why This is Best:

1. **Same Author**: Both packages maintained by bobmatnyc - no external dependency risk
2. **Already Published**: Package is on PyPI with stable 0.1.5 release
3. **Standard Practice**: This is how Python dependencies should work
4. **Immediate Fix**: Solves the problem with minimal code changes
5. **Better UX**: Users get automatic dependency resolution
6. **Version Pinning**: Can specify minimum version for compatibility
7. **No Complexity**: Removes all sys.path manipulation and fallback logic

### Implementation Checklist:

- [ ] Add `py-mcp-installer>=0.1.5` to `dependencies` in pyproject.toml
- [ ] Remove try/except and vendor path fallback from `setup_commands.py`
- [ ] Remove sys.path manipulation from `mcp_installer_adapter.py`
- [ ] Simplify imports to direct imports only
- [ ] Update CLAUDE.md documentation
- [ ] Remove HAS_MCP_INSTALLER fallback logic (now guaranteed available)
- [ ] Update tests to not mock missing dependency
- [ ] Bump version to 1.6.15
- [ ] Build and test locally: `uv sync && uv run kuzu-memory setup`
- [ ] Build distribution: `python -m build`
- [ ] Test installation from built wheel: `pip install dist/kuzu_memory-1.6.15-py3-none-any.whl`
- [ ] Publish to PyPI: `twine upload dist/kuzu_memory-1.6.15*`

## Technical Details

### Current Dependency Chain

```
kuzu-memory (PyPI)
  ├─ (tries to import py_mcp_installer)
  └─ ❌ NOT FOUND: vendor/ directory missing
      └─ (exists only in git repo as submodule)
```

### Proposed Dependency Chain

```
kuzu-memory (PyPI)
  ├─ py-mcp-installer>=0.1.5 (PyPI)
  │   ├─ pydantic>=2.0.0
  │   ├─ typing-extensions>=4.0.0
  │   ├─ tomli-w>=1.0.0
  │   └─ tomli>=2.0.0 (Python <3.11)
  └─ ✅ WORKS: Standard pip dependency resolution
```

### Compatibility Check

**kuzu-memory requirements**:
- Python >=3.11

**py-mcp-installer requirements**:
- Python >=3.10

✅ **Fully compatible** - py-mcp-installer supports Python 3.10+ including 3.11 and 3.12

### Dependency Overlap Analysis

**py-mcp-installer dependencies**:
- pydantic>=2.0.0 ✅ Already required by kuzu-memory
- typing-extensions>=4.0.0 ✅ Already required by kuzu-memory
- tomli-w>=1.0.0 ✅ Already required by kuzu-memory
- tomli>=2.0.0 (Python <3.11) ✅ N/A for kuzu-memory (requires 3.11+)

**Result**: Zero additional transitive dependencies needed!

## References

- PyPI Package: https://pypi.org/project/py-mcp-installer/
- GitHub Repository: https://github.com/bobmatnyc/py-mcp-installer-service
- Current kuzu-memory version: 1.6.14
- Python Packaging Guide: https://packaging.python.org/

## Conclusion

The issue is a **packaging configuration problem** caused by attempting to vendor code via git submodules. The solution is straightforward: add `py-mcp-installer` as a standard PyPI dependency. This is the correct Python packaging approach and will resolve the issue immediately with minimal code changes and zero additional transitive dependencies.

**Estimated fix time**: 30 minutes + testing
**Risk level**: Low (same author, compatible versions, overlapping dependencies)
**Impact**: Fixes broken package, simplifies codebase, follows best practices
