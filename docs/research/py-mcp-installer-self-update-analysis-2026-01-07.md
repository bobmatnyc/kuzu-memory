# py-mcp-installer-service Self-Update Feature Analysis

**Research Date**: 2026-01-07
**Repository**: `/Users/masa/Projects/kuzu-memory/vendor/py-mcp-installer-service/`
**Package Name**: `py-mcp-installer` (PyPI)
**Current Version**: 0.1.4
**Goal**: Add self-update capability with installation method detection

---

## Executive Summary

The py-mcp-installer-service is a well-architected library following strict type safety and service-oriented design principles. Adding a self-update feature would fit naturally into the existing architecture as a new utility module or service class.

**Key Finding**: The repository already has excellent patterns for command detection (`detect_install_method()` in `utils.py`) and safe operations (atomic writes, backups) that can be leveraged for self-update functionality.

---

## 1. Current Repository Structure

### Package Organization

```
py-mcp-installer-service/
├── src/py_mcp_installer/          # Main package (import: py_mcp_installer)
│   ├── __init__.py                # Public API exports
│   ├── types.py                   # Pydantic models and type definitions
│   ├── exceptions.py              # Custom exception hierarchy
│   ├── utils.py                   # Utility functions (file ops, command resolution)
│   ├── cli.py                     # CLI entry point (argparse-based)
│   ├── installer.py               # Main MCPInstaller facade class
│   ├── platform_detector.py       # Platform detection logic
│   ├── config_manager.py          # Configuration management
│   ├── command_builder.py         # Command string builders
│   ├── installation_strategy.py   # Strategy pattern for installations
│   ├── mcp_inspector.py           # Configuration validation/inspection
│   ├── mcp_doctor.py              # Diagnostic and health checks
│   └── platforms/                 # Platform-specific implementations
│       ├── __init__.py
│       ├── claude_code.py
│       ├── cursor.py
│       └── codex.py
├── tests/                         # pytest test suite
├── docs/                          # Comprehensive documentation
├── scripts/                       # Build/release automation
├── pyproject.toml                 # Package metadata and dependencies
└── VERSION                        # Version file (0.1.4)
```

### Architecture Patterns

1. **Service-Oriented Design**
   - Facades: `MCPInstaller` provides unified API
   - Strategies: Platform-specific installation strategies
   - Utilities: Shared functions in `utils.py`
   - Validators: `MCPInspector` and `MCPDoctor`

2. **Type Safety (mypy --strict)**
   - All functions have complete type annotations
   - Pydantic models for data validation
   - Type aliases in `types.py` (JsonDict, EnvDict, ArgsList)

3. **Error Handling**
   - Custom exception hierarchy (all inherit from `PyMCPInstallerError`)
   - Recovery suggestions in error messages
   - Atomic operations with backup/restore

4. **CLI Architecture**
   - Entry point: `py-mcp-installer` command
   - Current subcommands: `doctor` (diagnostics)
   - argparse-based (not Click)
   - Supports `--version`, `--json`, `--verbose`

---

## 2. Existing Patterns for Self-Update

### Installation Method Detection (Already Implemented!)

**Location**: `src/py_mcp_installer/utils.py:318-358`

```python
def detect_install_method(package: str) -> str:
    """Detect how a Python package is installed.

    Checks in order:
    1. pipx (in ~/.local/bin or ~/.local/pipx/venvs/)
    2. pip (via pip show)
    3. Not installed

    Returns: "pipx", "pip", or "not_installed"
    """
```

**Key Insight**: This function can be extended to detect:
- `uv` installations (check `uv pip list` or UV_CACHE)
- Development mode (`pip show -e` or `*.egg-link`)
- Homebrew installations (check `/opt/homebrew/Cellar/` or `brew list`)

### Command Resolution

**Location**: `src/py_mcp_installer/utils.py:300-316`

```python
def resolve_command_path(command: str) -> Path | None:
    """Find command in PATH using shutil.which()"""
```

**Usage**: Can be used to check for `uv`, `pipx`, `brew`, `pip` availability.

### Safe File Operations

The package already has production-ready patterns for:
- **Atomic writes**: `atomic_write()` with temp file + fsync + rename
- **Backups**: `backup_file()` with timestamped backups
- **Restore**: `restore_backup()` for error recovery

---

## 3. Dependencies Analysis

### Current Dependencies

```toml
dependencies = [
    "pydantic>=2.0.0",           # Data validation
    "typing-extensions>=4.0.0",   # Type hints
    "tomli-w>=1.0.0",            # TOML writing
    "tomli>=2.0.0; python_version < '3.11'",  # TOML reading
]
```

### Additional Dependencies for Self-Update

**Option 1: Zero Dependencies (Recommended)**
- Use `urllib.request` (stdlib) for PyPI API calls
- Use `subprocess` (stdlib) for running upgrade commands
- Minimal external dependencies align with project philosophy

**Option 2: Add requests (Optional)**
```toml
self-update = [
    "requests>=2.31.0",  # Simpler PyPI API interaction
]
```

**Trade-offs**:
- Zero deps: More code, but aligns with "zero external dependencies" principle
- With requests: Cleaner code, but adds dependency

**Recommendation**: Start with stdlib-only approach (urllib), add `requests` as optional extra if needed.

---

## 4. Recommended Implementation Approach

### New Module: `src/py_mcp_installer/self_updater.py`

**Why a new module**:
- Clear separation of concerns
- Follows existing pattern (`mcp_doctor.py`, `mcp_inspector.py`)
- Can be independently tested
- Easy to import and use from CLI

### Class Structure

```python
# src/py_mcp_installer/self_updater.py

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

InstallMethod = Literal["pipx", "pip", "uv", "homebrew", "development"]

@dataclass(frozen=True)
class UpdateCheckResult:
    """Result of checking for updates."""
    current_version: str
    latest_version: str
    update_available: bool
    install_method: InstallMethod
    upgrade_command: str
    package_url: str = "https://pypi.org/project/py-mcp-installer/"

@dataclass(frozen=True)
class UpdateResult:
    """Result of performing an update."""
    success: bool
    previous_version: str
    new_version: str
    method: InstallMethod
    message: str
    error: Exception | None = None

class SelfUpdater:
    """Manages self-update operations for py-mcp-installer.

    Features:
    - Detects installation method (pipx, pip, uv, homebrew, development)
    - Checks PyPI for latest version
    - Provides correct upgrade command
    - Optionally executes upgrade with user confirmation
    """

    def __init__(
        self,
        package_name: str = "py-mcp-installer",
        pypi_url: str = "https://pypi.org/pypi/py-mcp-installer/json",
        verbose: bool = False,
    ) -> None:
        """Initialize updater."""
        ...

    def check_for_updates(self) -> UpdateCheckResult:
        """Check if updates are available on PyPI."""
        ...

    def get_upgrade_command(self) -> str:
        """Get the appropriate upgrade command for detected install method."""
        ...

    def update(
        self,
        dry_run: bool = False,
        confirm: bool = True,
    ) -> UpdateResult:
        """Perform self-update (with optional dry-run and confirmation)."""
        ...

    def _detect_install_method(self) -> InstallMethod:
        """Detect how py-mcp-installer is currently installed."""
        ...

    def _fetch_latest_version(self) -> str:
        """Fetch latest version from PyPI JSON API."""
        ...

    def _run_upgrade_command(self, command: str) -> bool:
        """Execute upgrade command safely."""
        ...
```

### Integration Points

#### 1. CLI Integration (`cli.py`)

Add new subcommand: `py-mcp-installer update`

```python
# Add to cli.py

def cmd_update(args: argparse.Namespace) -> int:
    """Run self-update command."""
    from .self_updater import SelfUpdater

    updater = SelfUpdater(verbose=args.verbose)

    if args.check_only:
        # Just check for updates
        result = updater.check_for_updates()
        if args.json:
            print(json.dumps({
                "current": result.current_version,
                "latest": result.latest_version,
                "available": result.update_available,
                "method": result.install_method,
                "command": result.upgrade_command
            }, indent=2))
        else:
            if result.update_available:
                print(f"Update available: {result.current_version} → {result.latest_version}")
                print(f"Run: {result.upgrade_command}")
            else:
                print(f"Already up to date: {result.current_version}")
        return 0

    else:
        # Perform update
        update_result = updater.update(
            dry_run=args.dry_run,
            confirm=not args.yes
        )

        if update_result.success:
            print(f"✅ Updated: {update_result.previous_version} → {update_result.new_version}")
            return 0
        else:
            print(f"❌ Update failed: {update_result.message}")
            return 1
```

**CLI Usage Examples**:
```bash
# Check for updates only
py-mcp-installer update --check

# Update with confirmation prompt
py-mcp-installer update

# Update without confirmation
py-mcp-installer update --yes

# Dry run (show what would be done)
py-mcp-installer update --dry-run

# JSON output
py-mcp-installer update --check --json
```

#### 2. Public API Export (`__init__.py`)

Add to `__all__`:
```python
from .self_updater import SelfUpdater, UpdateCheckResult, UpdateResult

__all__ = [
    # ... existing exports ...
    "SelfUpdater",
    "UpdateCheckResult",
    "UpdateResult",
]
```

**Programmatic Usage**:
```python
from py_mcp_installer import SelfUpdater

updater = SelfUpdater()
result = updater.check_for_updates()

if result.update_available:
    print(f"Update: {result.current_version} → {result.latest_version}")
    print(f"Command: {result.upgrade_command}")
```

---

## 5. Installation Method Detection Strategy

### Extended `detect_install_method()`

**Location**: Extend existing function in `utils.py` or add to `self_updater.py`

```python
def detect_install_method_extended(package: str = "py-mcp-installer") -> InstallMethod:
    """Detect installation method with additional checks.

    Checks in priority order:
    1. Development mode (editable install)
    2. pipx (in ~/.local/pipx/venvs/)
    3. uv (in UV_CACHE or via uv pip list)
    4. Homebrew (in /opt/homebrew or /usr/local)
    5. pip (system or virtualenv)
    6. not_installed
    """

    # 1. Check for development mode
    try:
        import subprocess
        result = subprocess.run(
            ["pip", "show", "-f", package],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Check for editable-install marker
            if "editable" in result.stdout.lower() or ".egg-link" in result.stdout:
                return "development"
    except Exception:
        pass

    # 2. Check for pipx
    pipx_path = Path.home() / ".local" / "pipx" / "venvs" / package
    if pipx_path.exists():
        return "pipx"

    # 3. Check for uv
    if shutil.which("uv"):
        try:
            result = subprocess.run(
                ["uv", "pip", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if package in result.stdout:
                return "uv"
        except Exception:
            pass

    # 4. Check for Homebrew
    if sys.platform == "darwin":  # macOS only
        brew_paths = [
            Path("/opt/homebrew/Cellar") / package,
            Path("/usr/local/Cellar") / package,
        ]
        if any(p.exists() for p in brew_paths):
            return "homebrew"

    # 5. Check for pip
    try:
        result = subprocess.run(
            ["pip", "show", package],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "pip"
    except Exception:
        pass

    return "not_installed"
```

### Upgrade Command Mapping

```python
UPGRADE_COMMANDS = {
    "pipx": "pipx upgrade py-mcp-installer",
    "pip": "pip install --upgrade py-mcp-installer",
    "uv": "uv pip install --upgrade py-mcp-installer",
    "homebrew": "brew upgrade py-mcp-installer",  # If available
    "development": "(Development mode - pull latest from git and reinstall)",
}
```

---

## 6. PyPI Version Check Implementation

### Using Standard Library (urllib)

```python
import json
import urllib.request
from typing import Optional

def fetch_latest_version_from_pypi(
    package_name: str = "py-mcp-installer",
    timeout: float = 5.0
) -> Optional[str]:
    """Fetch latest version from PyPI JSON API.

    Args:
        package_name: Package name on PyPI
        timeout: Request timeout in seconds

    Returns:
        Latest version string or None if fetch fails

    Raises:
        urllib.error.URLError: If PyPI is unreachable
        json.JSONDecodeError: If response is invalid JSON
    """
    pypi_url = f"https://pypi.org/pypi/{package_name}/json"

    try:
        with urllib.request.urlopen(pypi_url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["info"]["version"]
    except Exception as e:
        logger.warning(f"Failed to check PyPI for updates: {e}")
        return None
```

### Version Comparison

```python
from packaging.version import Version, parse

def is_update_available(current: str, latest: str) -> bool:
    """Compare versions using PEP 440 version parsing.

    Args:
        current: Current installed version (e.g., "0.1.4")
        latest: Latest available version (e.g., "0.2.0")

    Returns:
        True if latest > current
    """
    try:
        return parse(latest) > parse(current)
    except Exception:
        # Fallback to string comparison if parsing fails
        return latest != current
```

**Note**: `packaging` is already available as a transitive dependency of `setuptools`.

---

## 7. Error Handling and Safety

### Safeguards

1. **Development Mode Protection**
   - Detect editable installs
   - Refuse to update (inform user to pull from git)
   - Prevent breaking development workflow

2. **Dry-Run Mode**
   - Show exactly what would be executed
   - No actual changes made
   - Preview upgrade command

3. **User Confirmation**
   - Interactive prompt before upgrade
   - Show current → latest version
   - Allow abort with Ctrl+C

4. **Rollback on Failure**
   - Not needed for self-update (package manager handles this)
   - But log previous version for reference

### Error Messages

```python
class UpdateError(PyMCPInstallerError):
    """Raised when self-update fails."""
    pass

class UpdateCheckError(PyMPCInstallerError):
    """Raised when version check fails."""
    pass
```

---

## 8. Testing Strategy

### Unit Tests

**File**: `tests/test_self_updater.py`

```python
import pytest
from py_mcp_installer.self_updater import SelfUpdater, InstallMethod

def test_detect_install_method_pipx(monkeypatch):
    """Test detection of pipx installation."""
    # Mock Path.exists to return True for pipx path
    ...

def test_detect_install_method_development(monkeypatch):
    """Test detection of development mode."""
    # Mock subprocess to return editable install info
    ...

def test_fetch_latest_version_success(monkeypatch):
    """Test successful version fetch from PyPI."""
    # Mock urllib.request.urlopen
    ...

def test_fetch_latest_version_timeout(monkeypatch):
    """Test handling of PyPI timeout."""
    ...

def test_update_dry_run(monkeypatch):
    """Test dry-run mode doesn't execute commands."""
    ...

def test_update_development_mode_refuses(monkeypatch):
    """Test that development mode refuses to update."""
    ...
```

### Integration Tests

```python
@pytest.mark.integration
def test_real_pypi_version_check():
    """Test actual PyPI API call (network required)."""
    updater = SelfUpdater()
    result = updater.check_for_updates()

    assert result.current_version is not None
    assert result.latest_version is not None
    # Don't assert update_available (depends on actual versions)
```

---

## 9. Documentation Requirements

### User Documentation

**Add to `README.md`**:

```markdown
## Self-Update

Check for and install updates to py-mcp-installer:

```bash
# Check for updates
py-mcp-installer update --check

# Update with confirmation
py-mcp-installer update

# Update without confirmation
py-mcp-installer update --yes
```

**Supported installation methods**:
- pipx: `pipx upgrade py-mcp-installer`
- pip: `pip install --upgrade py-mcp-installer`
- uv: `uv pip install --upgrade py-mcp-installer`
- Development mode: Pull from git and reinstall
```

### API Documentation

**Add to `docs/QUICK-REFERENCE.md`**:

```markdown
## Self-Update API

```python
from py_mcp_installer import SelfUpdater

# Check for updates
updater = SelfUpdater()
result = updater.check_for_updates()

if result.update_available:
    print(f"Update: {result.current_version} → {result.latest_version}")
    print(f"Run: {result.upgrade_command}")

# Programmatic update
update_result = updater.update(confirm=False)
```
```

---

## 10. Implementation Checklist

### Phase 1: Core Functionality
- [ ] Create `src/py_mcp_installer/self_updater.py`
- [ ] Implement `detect_install_method_extended()`
- [ ] Implement `fetch_latest_version_from_pypi()`
- [ ] Implement `SelfUpdater` class with `check_for_updates()`
- [ ] Add version comparison logic
- [ ] Add custom exceptions (`UpdateError`, `UpdateCheckError`)

### Phase 2: CLI Integration
- [ ] Add `update` subcommand to `cli.py`
- [ ] Implement `cmd_update()` function
- [ ] Add argparse arguments: `--check`, `--yes`, `--dry-run`, `--json`
- [ ] Add colorized output for terminal
- [ ] Test CLI commands manually

### Phase 3: Update Execution
- [ ] Implement `update()` method with subprocess execution
- [ ] Add dry-run mode
- [ ] Add user confirmation prompt
- [ ] Add development mode protection
- [ ] Handle upgrade failures gracefully

### Phase 4: Testing
- [ ] Write unit tests for `detect_install_method_extended()`
- [ ] Write unit tests for `fetch_latest_version_from_pypi()`
- [ ] Write unit tests for `SelfUpdater` class
- [ ] Write integration test for real PyPI check
- [ ] Test all install methods (pipx, pip, uv, dev)
- [ ] Test error handling and edge cases

### Phase 5: Documentation
- [ ] Update `README.md` with self-update section
- [ ] Add API documentation to `docs/QUICK-REFERENCE.md`
- [ ] Update `CHANGELOG.md` with new feature
- [ ] Add docstrings to all new functions/classes
- [ ] Update `__init__.py` exports and `__all__`

### Phase 6: Release
- [ ] Bump version to 0.2.0 (minor version for new feature)
- [ ] Run full test suite (`pytest`)
- [ ] Run type checking (`mypy --strict`)
- [ ] Run linting (`ruff`, `black`)
- [ ] Build package (`python -m build`)
- [ ] Test on PyPI test server
- [ ] Publish to PyPI
- [ ] Test self-update feature post-release

---

## 11. Potential Challenges and Solutions

### Challenge 1: Version File Location

**Problem**: `VERSION` file is at repo root, may not be packaged.

**Solution**: Use `__version__` from `__init__.py` (already set to `"0.1.4"`)

### Challenge 2: Homebrew Detection on Linux

**Problem**: Homebrew paths differ between macOS and Linux.

**Solution**:
```python
if sys.platform == "darwin":
    brew_paths = ["/opt/homebrew", "/usr/local"]
elif sys.platform == "linux":
    brew_paths = ["/home/linuxbrew/.linuxbrew", f"{os.environ.get('HOME')}/.linuxbrew"]
```

### Challenge 3: Windows Support

**Problem**: Windows has different command patterns and no standard package manager.

**Solution**:
- Detect `pip` and `pipx` on Windows
- Use `py -m pip install --upgrade` as fallback
- Add Windows-specific path checks

### Challenge 4: Network Timeout Handling

**Problem**: PyPI might be slow or unreachable.

**Solution**:
- Use 5-second timeout for PyPI requests
- Cache last check result for 24 hours (optional)
- Graceful degradation if check fails

---

## 12. Alternative Approaches Considered

### Approach 1: Delegate to External Package Manager

**Pros**: Simple, reliable, no subprocess execution
**Cons**: Requires user to run command manually

**Verdict**: ✅ **Use as fallback** - provide upgrade command but let user execute

### Approach 2: Use `pip` as Library (importlib.metadata)

**Pros**: No subprocess calls, pure Python
**Cons**: `pip` doesn't have stable API, might break

**Verdict**: ❌ **Don't use** - pip explicitly recommends subprocess

### Approach 3: Download and Install from PyPI Directly

**Pros**: Works regardless of install method
**Cons**: Bypasses package managers, security concerns, complex

**Verdict**: ❌ **Don't use** - violates package manager principles

---

## 13. Success Criteria

### Functional Requirements
✅ Detects installation method correctly (pipx, pip, uv, homebrew, dev)
✅ Checks PyPI for latest version (with timeout)
✅ Provides correct upgrade command for detected method
✅ Executes upgrade with user confirmation
✅ Supports dry-run mode
✅ Supports JSON output for scripting
✅ Protects development mode from accidental upgrade

### Non-Functional Requirements
✅ Type-safe (mypy --strict passes)
✅ Well-tested (>80% coverage)
✅ Zero breaking changes to existing API
✅ Performance: Version check <5 seconds
✅ Error messages include recovery suggestions
✅ Follows existing code style (black, ruff)

---

## 14. Recommended Next Steps

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/self-update
   ```

2. **Implement Core Module**
   - Start with `self_updater.py` skeleton
   - Implement `detect_install_method_extended()` first (easiest)
   - Add PyPI version check (with mocked tests)
   - Add `SelfUpdater` class

3. **Add CLI Command**
   - Extend `cli.py` with `update` subcommand
   - Test manually: `py-mcp-installer update --check`

4. **Write Tests**
   - Unit tests for all detection logic
   - Integration test for PyPI (network required)
   - CLI tests using `pytest` fixtures

5. **Update Documentation**
   - README.md (user-facing)
   - QUICK-REFERENCE.md (API reference)
   - CHANGELOG.md (release notes)

6. **Code Review and Release**
   - Run quality gates (mypy, ruff, black, pytest)
   - Bump version to 0.2.0
   - Publish to PyPI
   - Test self-update in production

---

## 15. Code Examples for Implementation

### Minimal Working Example

```python
# src/py_mcp_installer/self_updater.py (minimal)

import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Literal

from . import __version__

InstallMethod = Literal["pipx", "pip", "uv", "development", "unknown"]

class SelfUpdater:
    """Self-update manager for py-mcp-installer."""

    def __init__(self, package_name: str = "py-mcp-installer"):
        self.package_name = package_name
        self.current_version = __version__

    def check_for_updates(self) -> dict:
        """Check PyPI for updates."""
        latest = self._fetch_latest_version()
        method = self._detect_install_method()

        return {
            "current": self.current_version,
            "latest": latest,
            "update_available": latest != self.current_version,
            "install_method": method,
            "upgrade_command": self._get_upgrade_command(method)
        }

    def _fetch_latest_version(self) -> str:
        """Fetch from PyPI."""
        url = f"https://pypi.org/pypi/{self.package_name}/json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["info"]["version"]

    def _detect_install_method(self) -> InstallMethod:
        """Detect how package is installed."""
        # Check pipx
        pipx_path = Path.home() / ".local/pipx/venvs" / self.package_name
        if pipx_path.exists():
            return "pipx"

        # Check pip
        try:
            result = subprocess.run(
                ["pip", "show", self.package_name],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return "pip"
        except Exception:
            pass

        return "unknown"

    def _get_upgrade_command(self, method: InstallMethod) -> str:
        """Get upgrade command for method."""
        commands = {
            "pipx": f"pipx upgrade {self.package_name}",
            "pip": f"pip install --upgrade {self.package_name}",
            "uv": f"uv pip install --upgrade {self.package_name}",
            "development": "git pull && pip install -e .",
            "unknown": f"pip install --upgrade {self.package_name}",
        }
        return commands.get(method, commands["unknown"])
```

---

## Summary and Recommendation

### Recommended Architecture

**Create new module**: `src/py_mcp_installer/self_updater.py`
**Integrate with CLI**: Add `update` subcommand to `cli.py`
**Export in API**: Add `SelfUpdater` to `__init__.py` exports
**Zero new dependencies**: Use stdlib (`urllib.request`, `subprocess`)
**Follow existing patterns**: Type-safe, service-oriented, well-tested

### Integration Points

1. **Utilities** (`utils.py`): Extend `detect_install_method()` or create new function
2. **CLI** (`cli.py`): Add `update` subcommand with `--check`, `--yes`, `--dry-run`, `--json`
3. **Exceptions** (`exceptions.py`): Add `UpdateError` and `UpdateCheckError`
4. **Types** (`types.py`): Optional - add `UpdateCheckResult` dataclass

### Why This Fits Well

✅ Aligns with existing architecture (service classes, utilities)
✅ Follows type safety principles (mypy --strict)
✅ Leverages existing patterns (atomic operations, error handling)
✅ Minimal dependencies (stdlib only)
✅ Non-invasive (doesn't modify existing code)
✅ Well-defined boundaries (single module)
✅ Easy to test (mock PyPI, mock subprocess)

### Estimated Effort

- **Core Implementation**: 4-6 hours
- **CLI Integration**: 2-3 hours
- **Testing**: 3-4 hours
- **Documentation**: 2-3 hours
- **Total**: 11-16 hours (1-2 days)

---

**End of Analysis**
