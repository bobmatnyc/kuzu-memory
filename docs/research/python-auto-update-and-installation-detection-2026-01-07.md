# Python Auto-Update Packages and Installation Detection Methods

**Research Date:** 2026-01-07
**Researcher:** AI Research Agent
**Context:** KuzuMemory auto-update enhancement

## Executive Summary

This research evaluates Python auto-update packages and installation method detection techniques for CLI tools. KuzuMemory already has a solid `VersionChecker` class that handles PyPI version checking, but lacks installation method detection to provide intelligent upgrade commands.

**Key Findings:**
1. **No comprehensive auto-update library exists** - Most tools implement custom solutions
2. **Installation detection requires path analysis** - Check `sys.executable` and `__file__` patterns
3. **Custom implementation recommended** - Extend existing `VersionChecker` rather than add dependencies
4. **Popular tools use simple pip upgrades** - Poetry/pipx/uv handle their own tool updates separately

## 1. Existing Python Auto-Update Packages

### 1.1 Available Packages

#### **auto-update** (PyPI)
- **URL:** https://pypi.org/project/auto-update/
- **Latest Version:** 0.1.1 (September 9, 2024)
- **GitHub:** https://github.com/shaiksamad/auto-update
- **Stars/Activity:** Not visible (low activity indicator)
- **Python Support:** 3.6 - 3.9+
- **License:** MIT

**Features:**
- Retrieves latest release from GitHub repository
- Compares with currently installed version
- Updates project automatically on systems without Git
- Writes activity logs to `updater.log`

**Limitations:**
- No GitHub stars/metrics visible (suggests low adoption)
- Limited to GitHub releases (not PyPI)
- No documentation for advanced use cases
- Last updated September 2024 (recent but minimal activity)

**Example Usage:**
```python
from auto_update import Updater

# Create _auto_update.py with GitHub repo details
# Updater class handles version checking and installation
```

**Assessment:** ❌ **Not recommended** - Low adoption, GitHub-only, no PyPI integration

---

#### **gh-update**
- **URL:** https://github.com/n0samu/gh-update
- **Type:** Standalone Python script (not a library)
- **GitHub Stars:** Not specified
- **Purpose:** Auto-update portable programs from GitHub releases

**Features:**
- Regex-based asset matching for release artifacts
- Supports ZIP and TAR archive extraction
- Version tracking via `installed_name` and `installed_date`
- Backup capability before updates
- Configurable pre-release downloads

**Limitations:**
- Not a library - requires integration as a script
- Configuration file-driven (not programmatic API)
- GitHub releases only (not PyPI)
- Requires `requests` library

**Example Usage:**
```bash
pip install requests
python gh_update.py ruffle.ini win64
```

**Assessment:** ❌ **Not recommended** - Script-based, no library API, GitHub-only

---

#### **selfupdate**
- **URL:** https://github.com/erfantkerfan/selfupdate
- **Type:** Git repository update library
- **Status:** Alpha
- **GitHub Stars:** Not specified

**Features:**
- Auto-update for scripts within Git repositories
- Pulls changes from remote repositories
- Bidirectional sync (merge remote + push local changes)
- Development environment detection (`.devenv` file)
- Conflict handling with `force` parameter

**Example Usage:**
```python
from selfupdate import update

# Simple one-line update
update()

# With parameters
update(force=True, check_dev=True, verbose=True)
```

**Limitations:**
- **Git-based only** (not suitable for PyPI packages)
- Alpha status
- Limited authentication support
- Primarily for development workflows, not production updates

**Assessment:** ❌ **Not recommended** - Git-only, alpha status, not for PyPI packages

---

#### **pip-check** and **pip-check-updates**
- **pip-check URL:** https://pypi.org/project/pip-check/
- **pip-check-updates URL:** https://pypi.org/project/pip-check-updates/
- **Latest:** v0.28.0 (December 16, 2025)

**Features:**
- Displays installed pip packages and update status
- Transforms `pip list --outdated` into user-friendly table
- Supports uv and custom pip locations (`--cmd` option)
- Filter and target options for selective updates

**Example Usage:**
```bash
pip-check  # Show all outdated packages
pip-check-updates -u  # Upgrade packages
```

**Limitations:**
- CLI tool, not a library for programmatic use
- Designed for checking all packages, not self-update
- npm-check-updates inspired (project-wide dependency management)

**Assessment:** ❌ **Not recommended** - CLI tool for all packages, not self-update library

---

#### **lastversion**
- **URL:** https://pypi.org/project/lastversion/
- **Purpose:** Check versions of projects on PyPI

**Features:**
- Query PyPI for latest versions
- Can be used in cron jobs for auto-updaters
- Simple version checking

**Limitations:**
- Only version checking, no update mechanism
- Would still need custom upgrade logic

**Assessment:** ⚠️ **Partial solution** - Good for version checking, but KuzuMemory already has this

---

### 1.2 Summary: No Comprehensive Auto-Update Library

**Conclusion:** There is **no well-maintained, comprehensive auto-update library** for Python CLI tools that:
- ✅ Checks PyPI for latest versions
- ✅ Detects installation method (pip/pipx/uv/homebrew)
- ✅ Provides appropriate upgrade commands
- ✅ Handles user confirmation and execution

**Recommendation:** **Build custom solution** by extending KuzuMemory's existing `VersionChecker` class.

---

## 2. Installation Method Detection

### 2.1 Detection Strategies

Python CLI tools can be installed via multiple methods. Detection requires analyzing paths and environment variables.

#### **Installation Methods to Detect:**
1. **pip** (system-wide or user install)
2. **pipx** (isolated virtual environments)
3. **uv tool install** (isolated tools)
4. **homebrew** (macOS package manager)
5. **Development mode** (`pip install -e .` or `uv sync`)

---

### 2.2 Path Analysis Patterns

#### **Key Python Variables:**

```python
import sys
from pathlib import Path

# Python executable location
sys.executable
# Example (pip): /usr/local/bin/python3
# Example (pipx): ~/.local/pipx/venvs/kuzu-memory/bin/python
# Example (uv): ~/.local/share/uv/tools/kuzu-memory/bin/python
# Example (homebrew): /opt/homebrew/bin/python3

# Package installation location
import kuzu_memory
kuzu_memory.__file__
# Example (pip): /usr/local/lib/python3.12/site-packages/kuzu_memory/__init__.py
# Example (pipx): ~/.local/pipx/venvs/kuzu-memory/lib/python3.12/site-packages/kuzu_memory/__init__.py
# Example (dev): /Users/masa/Projects/kuzu-memory/src/kuzu_memory/__init__.py
```

---

### 2.3 Detection Heuristics

#### **pipx Detection:**

```python
import sys
from pathlib import Path

def detect_pipx_install() -> bool:
    """Detect if installed via pipx."""
    executable = Path(sys.executable)

    # Check for pipx in executable path
    # pipx uses: ~/.local/pipx/venvs/<package>/bin/python
    # or: ~/.local/share/pipx/venvs/<package>/bin/python (newer versions)
    if '.local/pipx/venvs' in str(executable):
        return True

    if '.local/share/pipx/venvs' in str(executable):
        return True

    # Check PIPX_HOME environment variable
    import os
    pipx_home = os.getenv('PIPX_HOME')
    if pipx_home and str(executable).startswith(pipx_home):
        return True

    return False
```

**Key Paths:**
- Default: `~/.local/pipx/venvs/<package>/bin/python`
- Post-v1.2.0: Platform-specific via `platformdirs` library
- Environment variable: `$PIPX_HOME` (override default location)
- Binary symlinks: `~/.local/bin/<tool>` (override via `$PIPX_BIN_DIR`)

**References:**
- [pipx Installation Documentation](https://pipx.pypa.io/stable/installation/)
- [pipx GitHub](https://github.com/pypa/pipx)

---

#### **uv tool install Detection:**

```python
def detect_uv_tool_install() -> bool:
    """Detect if installed via uv tool install."""
    executable = Path(sys.executable)

    # uv tool install uses:
    # - ~/.local/share/uv/tools/<package>/bin/python (Linux)
    # - ~/Library/Application Support/uv/tools/<package>/bin/python (macOS)
    # - %APPDATA%/uv/tools/<package>/Scripts/python.exe (Windows)

    if '/uv/tools/' in str(executable):
        return True

    if '\\uv\\tools\\' in str(executable):  # Windows
        return True

    return False
```

**Key Features:**
- Tool executables placed in `PATH`
- Isolated environments per tool (like pipx)
- `.python-version` file support for version pinning
- Marker files: `.python-version`, `uv.lock` (project-level)

**References:**
- [uv Using Tools Documentation](https://docs.astral.sh/uv/guides/tools/)
- [uv Python Versions](https://docs.astral.sh/uv/concepts/python-versions/)

---

#### **Homebrew Detection:**

```python
def detect_homebrew_install() -> bool:
    """Detect if installed via Homebrew."""
    executable = Path(sys.executable)

    # Homebrew paths:
    # - Intel: /usr/local/Cellar/kuzu-memory/<version>/...
    # - Apple Silicon: /opt/homebrew/Cellar/kuzu-memory/<version>/...
    # - Linuxbrew: /home/linuxbrew/.linuxbrew/Cellar/...

    if '/Cellar/' in str(executable):
        return True

    # Check common Homebrew prefixes
    homebrew_prefixes = [
        '/usr/local',       # Intel Mac
        '/opt/homebrew',    # Apple Silicon
        '/home/linuxbrew/.linuxbrew'  # Linuxbrew
    ]

    for prefix in homebrew_prefixes:
        if str(executable).startswith(prefix):
            return True

    # Check environment variables
    import os
    if os.getenv('HOMEBREW_PREFIX'):
        return True

    return False
```

**Key Paths:**
- **Main prefix:** `/usr/local` (Intel) or `/opt/homebrew` (Apple Silicon)
- **Cellar:** `<prefix>/Cellar/<package>/<version>/`
- **Symlinks:** `<prefix>/bin/<tool>` and `<prefix>/opt/<package>/`
- **Site-packages:** `<prefix>/lib/python3.y/site-packages/`

**Environment Variables:**
- `$HOMEBREW_PREFIX` - Main installation prefix
- `$HOMEBREW_CELLAR` - Package installation directory
- `$HOMEBREW_REPOSITORY` - Homebrew repository location

**Commands:**
```bash
brew --prefix kuzu-memory  # Get package prefix
brew --cellar             # Get Cellar path
brew info kuzu-memory     # Detailed package info
```

**References:**
- [Homebrew Installation Locations](https://flavor365.com/homebrew-installation-locations-on-macos-explained-2025/)
- [Homebrew Documentation](https://docs.brew.sh/)

---

#### **Development Mode Detection:**

```python
def detect_development_install() -> bool:
    """Detect if running from development/editable install."""
    import kuzu_memory
    package_path = Path(kuzu_memory.__file__).parent

    # Check if in a src/ directory structure
    if 'src/kuzu_memory' in str(package_path):
        return True

    # Check if installed with -e (editable)
    # Look for .egg-link file in site-packages
    try:
        import site
        for site_dir in site.getsitepackages():
            egg_link = Path(site_dir) / 'kuzu-memory.egg-link'
            if egg_link.exists():
                return True
    except:
        pass

    # Check if __file__ is in a git repository
    if (package_path / '../.git').exists():
        return True

    return False
```

---

### 2.4 Comprehensive Detection Function

```python
import sys
import os
from pathlib import Path
from typing import Literal

InstallMethod = Literal["pip", "pipx", "uv", "homebrew", "development", "unknown"]

def detect_installation_method() -> InstallMethod:
    """
    Detect how kuzu-memory was installed.

    Returns:
        Installation method: "pip", "pipx", "uv", "homebrew", "development", or "unknown"
    """
    executable = Path(sys.executable)
    executable_str = str(executable)

    # Check development mode first (highest priority)
    if detect_development_install():
        return "development"

    # Check pipx
    if '.local/pipx/venvs' in executable_str or \
       '.local/share/pipx/venvs' in executable_str or \
       os.getenv('PIPX_HOME') and executable_str.startswith(os.getenv('PIPX_HOME', '')):
        return "pipx"

    # Check uv
    if '/uv/tools/' in executable_str or '\\uv\\tools\\' in executable_str:
        return "uv"

    # Check Homebrew
    if '/Cellar/' in executable_str or \
       executable_str.startswith('/usr/local') or \
       executable_str.startswith('/opt/homebrew') or \
       executable_str.startswith('/home/linuxbrew/.linuxbrew') or \
       os.getenv('HOMEBREW_PREFIX'):
        return "homebrew"

    # Default to pip (system or user install)
    return "pip"

def get_upgrade_command(method: InstallMethod) -> str:
    """
    Get the appropriate upgrade command for the installation method.

    Args:
        method: Installation method detected

    Returns:
        Command string to upgrade kuzu-memory
    """
    commands = {
        "pip": "pip install --upgrade kuzu-memory",
        "pipx": "pipx upgrade kuzu-memory",
        "uv": "uv tool upgrade kuzu-memory",
        "homebrew": "brew upgrade kuzu-memory",
        "development": "cd <project-root> && uv sync && pip install -e .",
    }

    return commands.get(method, "pip install --upgrade kuzu-memory")
```

---

## 3. How Popular CLI Tools Handle Updates

### 3.1 GitHub CLI (`gh`)

**Implementation:** Written in Go, not Python, but useful for patterns

**Update Methods:**
- **Package managers:** Upgrade via original installation method
  - Homebrew: `brew upgrade gh`
  - APT: `sudo apt update && sudo apt upgrade gh`
  - Chocolatey (Windows): `choco upgrade gh`
- **Manual install:** Re-download prebuilt archive from GitHub Releases
- **No built-in auto-update:** Relies on package managers

**Key Insights:**
- ✅ Respects installation method (no cross-method updates)
- ✅ GitHub-hosted runners update weekly automatically
- ❌ Manual installs require re-download (no self-update)

**References:**
- [gh CLI Update Discussion](https://github.com/cli/cli/discussions/4630)
- [GitHub CLI Documentation](https://cli.github.com/manual/)

---

### 3.2 Poetry

**Implementation:** Python package manager with self-update capability

**Update Methods:**
- **Official installer:** `poetry self update` command
- **pipx:** `pipx upgrade poetry`
- **pip:** `pip install --upgrade poetry`

**Self-Update Mechanism:**
```bash
poetry self update          # Update to latest stable
poetry self update 1.2.0   # Update to specific version
poetry self update --preview  # Include pre-releases
```

**Known Issues:**
- Self-update can be problematic on Windows
- Recommends re-installation via official installer for issues
- Version sometimes not updated properly (GitHub issues #4524, #9329)

**Key Insights:**
- ✅ Has `self update` command (only works with official installer)
- ✅ Respects installation method (pipx users must use `pipx upgrade`)
- ⚠️ Self-update has reliability issues (suggests re-install as fallback)

**References:**
- [Poetry Self Update Documentation](https://python-poetry.org/docs/)
- [Poetry Discussion: Update Methods](https://github.com/orgs/python-poetry/discussions/9126)

---

### 3.3 pipx (Self-Updating)

**Implementation:** pipx manages its own updates

**Update Methods:**
- **Homebrew:** `brew upgrade pipx`
- **pip:** `pip install --upgrade pipx`
- **System package managers:** Use respective upgrade commands

**Key Insight:**
- ❌ **No self-update command** - pipx itself doesn't have `pipx self update`
- ✅ Provides `pipx upgrade <package>` for tools it manages
- ✅ Clear separation: pipx updates itself via its installer, tools via pipx

**References:**
- [pipx Documentation](https://pipx.pypa.io/stable/)

---

### 3.4 uv

**Implementation:** Rust-based, extremely fast Python package manager

**Update Methods:**
- **Standalone installer:** Re-run installation script
- **pipx:** `pipx upgrade uv`
- **pip:** `pip install --upgrade uv`
- **Homebrew:** `brew upgrade uv`

**Self-Update Behavior:**
- ❌ **Disabled when installed via package managers** (pip, pipx, homebrew)
- ✅ Use package manager's upgrade method instead
- ✅ Standalone installer supports self-update

**Key Insight:**
- ✅ Detects installation method and disables self-update appropriately
- ✅ Provides clear guidance: "Use <package-manager> upgrade method"

**References:**
- [uv Installation Documentation](https://docs.astral.sh/uv/getting-started/installation/)

---

## 4. Implementation Recommendations for KuzuMemory

### 4.1 Current State Analysis

**Existing Implementation:**

KuzuMemory already has a solid `VersionChecker` class in `src/kuzu_memory/cli/update_commands.py`:

```python
class VersionChecker:
    """Handles version checking against PyPI."""
    PYPI_API_URL = "https://pypi.org/pypi/kuzu-memory/json"

    def get_latest_version(self, include_pre: bool = False) -> dict:
        """Fetch latest version from PyPI."""
        # Already implemented ✅

    def compare_versions(self, latest: str) -> dict:
        """Compare current vs latest version."""
        # Already implemented ✅

    def get_upgrade_command(self) -> str:
        """Return pip command to upgrade."""
        return "pip install --upgrade kuzu-memory"  # ⚠️ Assumes pip
```

**Current Limitation:**
- `get_upgrade_command()` always returns `pip install --upgrade kuzu-memory`
- **Does not detect installation method**
- Users installed via pipx/uv/homebrew get wrong instructions

---

### 4.2 Recommended Solution: Extend VersionChecker

**Option 1: Add Installation Detection to VersionChecker** ⭐ **RECOMMENDED**

**Pros:**
- ✅ No new dependencies
- ✅ Minimal code changes
- ✅ Builds on existing infrastructure
- ✅ Full control over detection logic

**Implementation:**

```python
# Add to src/kuzu_memory/cli/update_commands.py

from typing import Literal

InstallMethod = Literal["pip", "pipx", "uv", "homebrew", "development", "unknown"]

class VersionChecker:
    """Handles version checking against PyPI."""

    PYPI_API_URL = "https://pypi.org/pypi/kuzu-memory/json"
    TIMEOUT = 10

    def __init__(self) -> None:
        self.current_version = __version__
        self.install_method = self._detect_installation_method()

    def _detect_installation_method(self) -> InstallMethod:
        """
        Detect how kuzu-memory was installed.

        Returns:
            Installation method for appropriate upgrade command
        """
        import os
        from pathlib import Path

        executable = Path(sys.executable)
        executable_str = str(executable)

        # Check development mode first
        try:
            import kuzu_memory
            package_path = Path(kuzu_memory.__file__).parent

            # Development indicators
            if 'src/kuzu_memory' in str(package_path):
                return "development"

            # Check for .git directory (development)
            if (package_path.parent.parent / '.git').exists():
                return "development"

            # Check for editable install
            import site
            for site_dir in site.getsitepackages():
                egg_link = Path(site_dir) / 'kuzu-memory.egg-link'
                if egg_link.exists():
                    return "development"
        except:
            pass

        # Check pipx
        if '.local/pipx/venvs' in executable_str or \
           '.local/share/pipx/venvs' in executable_str:
            return "pipx"

        pipx_home = os.getenv('PIPX_HOME', '')
        if pipx_home and executable_str.startswith(pipx_home):
            return "pipx"

        # Check uv tool install
        if '/uv/tools/' in executable_str or '\\uv\\tools\\' in executable_str:
            return "uv"

        # Check Homebrew
        if '/Cellar/' in executable_str:
            return "homebrew"

        homebrew_prefixes = ['/usr/local', '/opt/homebrew', '/home/linuxbrew/.linuxbrew']
        if any(executable_str.startswith(prefix) for prefix in homebrew_prefixes):
            return "homebrew"

        if os.getenv('HOMEBREW_PREFIX'):
            return "homebrew"

        # Default: pip (system or user install)
        return "pip"

    def get_upgrade_command(self) -> str:
        """
        Return appropriate upgrade command based on installation method.

        Returns:
            Command string to upgrade kuzu-memory
        """
        commands = {
            "pip": "pip install --upgrade kuzu-memory",
            "pipx": "pipx upgrade kuzu-memory",
            "uv": "uv tool upgrade kuzu-memory",
            "homebrew": "brew upgrade kuzu-memory",
            "development": "git pull && uv sync",
        }

        return commands.get(self.install_method, "pip install --upgrade kuzu-memory")

    def get_install_method_message(self) -> str:
        """
        Get user-friendly message about installation method.

        Returns:
            Human-readable installation method description
        """
        messages = {
            "pip": "Installed via pip (Python package manager)",
            "pipx": "Installed via pipx (isolated environment)",
            "uv": "Installed via uv tool (isolated tool)",
            "homebrew": "Installed via Homebrew (macOS package manager)",
            "development": "Running from development source",
        }

        return messages.get(self.install_method, "Unknown installation method")
```

**Updated Output in `_format_text_output()`:**

```python
def _format_text_output(
    check_result: dict[str, Any],
    comparison: dict[str, Any],
    upgrade_result: dict[str, Any] | None = None,
) -> None:
    """Format and print text output using rich."""

    # ... existing error handling ...

    if not update_available:
        # Already on latest
        checker = VersionChecker()
        rich_panel(
            f"Current version: {current}\n"
            f"Latest version:  {latest}\n"
            f"Installation:    {checker.get_install_method_message()}\n\n"
            "✅ You are running the latest version!",
            title="📦 Version Check",
            style="green",
        )
        return

    # Update available
    checker = VersionChecker()
    upgrade_cmd = checker.get_upgrade_command()
    install_msg = checker.get_install_method_message()

    message = (
        f"Current version: {current}\n"
        f"Latest version:  {latest}\n"
        f"Update type:     {emoji} {version_type.title()}\n"
        f"Installation:    {install_msg}\n"
        f"Released:        {release_date}"
    )

    # ... rest of function ...

    rich_panel(
        f"{message}\n\n"
        f"To upgrade, run:\n"
        f"  {upgrade_cmd}\n\n"  # Now shows correct command!
        "Or use: kuzu-memory update (without --check-only)",
        title="📦 Update Available",
        style="blue",
    )
```

---

### 4.3 Testing Strategy

**Test Cases:**

```python
# tests/unit/test_installation_detection.py

import pytest
import sys
from pathlib import Path
from unittest.mock import patch
from kuzu_memory.cli.update_commands import VersionChecker

def test_detect_pip_install(monkeypatch):
    """Test detection of pip installation."""
    monkeypatch.setattr(sys, 'executable', '/usr/local/bin/python3')

    checker = VersionChecker()
    assert checker.install_method == "pip"
    assert checker.get_upgrade_command() == "pip install --upgrade kuzu-memory"

def test_detect_pipx_install(monkeypatch):
    """Test detection of pipx installation."""
    monkeypatch.setattr(
        sys,
        'executable',
        '/home/user/.local/pipx/venvs/kuzu-memory/bin/python'
    )

    checker = VersionChecker()
    assert checker.install_method == "pipx"
    assert checker.get_upgrade_command() == "pipx upgrade kuzu-memory"

def test_detect_uv_install(monkeypatch):
    """Test detection of uv tool installation."""
    monkeypatch.setattr(
        sys,
        'executable',
        '/home/user/.local/share/uv/tools/kuzu-memory/bin/python'
    )

    checker = VersionChecker()
    assert checker.install_method == "uv"
    assert checker.get_upgrade_command() == "uv tool upgrade kuzu-memory"

def test_detect_homebrew_install(monkeypatch):
    """Test detection of Homebrew installation."""
    monkeypatch.setattr(
        sys,
        'executable',
        '/opt/homebrew/Cellar/kuzu-memory/1.6.13/bin/python3'
    )

    checker = VersionChecker()
    assert checker.install_method == "homebrew"
    assert checker.get_upgrade_command() == "brew upgrade kuzu-memory"

def test_detect_development_install(monkeypatch):
    """Test detection of development installation."""
    # Mock kuzu_memory.__file__ to point to src/
    import kuzu_memory
    with patch.object(kuzu_memory, '__file__', '/path/to/project/src/kuzu_memory/__init__.py'):
        checker = VersionChecker()
        assert checker.install_method == "development"
        assert "git pull" in checker.get_upgrade_command()
```

---

### 4.4 User Experience Improvements

**Before (Current):**
```bash
$ kuzu-memory update --check-only

📦 Update Available
Current version: 1.6.10
Latest version:  1.6.13
Update type:     🔧 Patch
Released:        2026-01-07

To upgrade, run:
  pip install --upgrade kuzu-memory  # ❌ Wrong for pipx users!

Or use: kuzu-memory update (without --check-only)
```

**After (With Detection):**
```bash
$ kuzu-memory update --check-only

📦 Update Available
Current version: 1.6.10
Latest version:  1.6.13
Update type:     🔧 Patch
Installation:    Installed via pipx (isolated environment)  # ✅ NEW
Released:        2026-01-07

To upgrade, run:
  pipx upgrade kuzu-memory  # ✅ Correct command!

Or use: kuzu-memory update (without --check-only)
```

---

### 4.5 Edge Cases to Handle

1. **Multiple installation methods detected:**
   - Prioritize development > pipx > uv > homebrew > pip
   - Development mode highest priority (active development)

2. **Unknown installation method:**
   - Fall back to `pip install --upgrade kuzu-memory`
   - Show warning: "Could not detect installation method, using pip"

3. **Development mode with uncommitted changes:**
   - Warn user: "Running from development source with local changes"
   - Suggest: `git stash && git pull && uv sync && git stash pop`

4. **Homebrew but kuzu-memory not in Homebrew:**
   - Detect Homebrew Python but package installed via pip
   - Still suggest pip upgrade (Homebrew is just the Python provider)

5. **Virtual environment detection:**
   - If in a project venv (not pipx/uv isolated env), suggest pip
   - Check: `sys.prefix != sys.base_prefix` (in venv)

---

## 5. Alternative Approaches (Not Recommended)

### 5.1 Use External Library (e.g., `auto-update`)

**Pros:**
- ❓ Outsource maintenance (hypothetical)

**Cons:**
- ❌ No suitable library exists for PyPI + installation detection
- ❌ Adds dependency for simple functionality
- ❌ Existing libraries are GitHub-only or Git-only
- ❌ Less control over detection logic
- ❌ KuzuMemory already has version checking implemented

**Verdict:** ❌ **Not Recommended**

---

### 5.2 Implement `kuzu-memory self update` Command

**Pros:**
- ✅ User-friendly command (like `poetry self update`)
- ✅ Single command for all installation methods

**Cons:**
- ⚠️ Requires handling subprocess execution per method
- ⚠️ Risk of breaking installations (Poetry has issues with this)
- ⚠️ Needs extensive testing across all methods
- ⚠️ May conflict with package manager expectations

**Verdict:** ⚠️ **Possible Future Enhancement** (not immediate priority)

**Recommendation:** Start with detection + correct instructions, consider `self update` in v2.0

---

## 6. Implementation Plan

### Phase 1: Add Installation Detection (Immediate)

**Files to Modify:**
1. `src/kuzu_memory/cli/update_commands.py`
   - Add `_detect_installation_method()` to `VersionChecker`
   - Update `get_upgrade_command()` to use detected method
   - Add `get_install_method_message()` for user display

2. `tests/unit/test_update_commands.py` (create if doesn't exist)
   - Add comprehensive tests for all installation methods
   - Mock `sys.executable` for different scenarios
   - Test edge cases (development, unknown methods)

**Estimated Effort:** 2-3 hours

---

### Phase 2: Update CLI Output (Immediate)

**Files to Modify:**
1. `src/kuzu_memory/cli/update_commands.py`
   - Update `_format_text_output()` to show installation method
   - Update `_format_json_output()` to include `install_method` field

**Estimated Effort:** 1 hour

---

### Phase 3: Documentation (Immediate)

**Files to Create/Update:**
1. `docs/user-guide/updating.md` (new)
   - Document update process for each installation method
   - Show examples of `kuzu-memory update` output
   - Explain what to do if detection fails

2. `README.md` (update)
   - Add "Updating KuzuMemory" section
   - Link to detailed update guide

**Estimated Effort:** 1 hour

---

### Phase 4: Future Enhancement - Self-Update (Optional)

**Considerations:**
- Implement `kuzu-memory self update` command
- Execute upgrade automatically with user confirmation
- Handle errors gracefully (fallback to manual instructions)
- Test extensively across all installation methods

**Timeline:** v2.0 release (not immediate)

---

## 7. Code Examples for Implementation

### 7.1 Complete Detection Function

```python
# src/kuzu_memory/cli/update_commands.py

import os
import sys
from pathlib import Path
from typing import Literal

InstallMethod = Literal["pip", "pipx", "uv", "homebrew", "development", "unknown"]

def _detect_installation_method() -> InstallMethod:
    """
    Detect how kuzu-memory was installed.

    Detection priority:
    1. Development mode (highest priority)
    2. pipx (isolated environment)
    3. uv tool (isolated tool)
    4. Homebrew (package manager)
    5. pip (default fallback)

    Returns:
        Installation method identifier
    """
    executable = Path(sys.executable)
    executable_str = str(executable)

    # === Development Mode Detection ===
    try:
        import kuzu_memory
        package_path = Path(kuzu_memory.__file__).parent

        # Check for src/ directory structure
        if 'src/kuzu_memory' in str(package_path):
            logger.debug(f"Development mode detected: src/ structure at {package_path}")
            return "development"

        # Check for .git directory (development clone)
        git_dir = package_path.parent.parent / '.git'
        if git_dir.exists():
            logger.debug(f"Development mode detected: .git directory at {git_dir}")
            return "development"

        # Check for editable install (.egg-link)
        import site
        for site_dir in site.getsitepackages():
            egg_link = Path(site_dir) / 'kuzu-memory.egg-link'
            if egg_link.exists():
                logger.debug(f"Development mode detected: .egg-link at {egg_link}")
                return "development"
    except Exception as e:
        logger.debug(f"Development mode check failed: {e}")

    # === pipx Detection ===
    # Check for pipx venvs directory (old location)
    if '.local/pipx/venvs' in executable_str:
        logger.debug(f"pipx detected: old venvs path at {executable}")
        return "pipx"

    # Check for pipx venvs directory (new location, post-v1.2.0)
    if '.local/share/pipx/venvs' in executable_str:
        logger.debug(f"pipx detected: new venvs path at {executable}")
        return "pipx"

    # Check PIPX_HOME environment variable
    pipx_home = os.getenv('PIPX_HOME', '')
    if pipx_home and executable_str.startswith(pipx_home):
        logger.debug(f"pipx detected: PIPX_HOME={pipx_home}")
        return "pipx"

    # === uv tool install Detection ===
    # Linux: ~/.local/share/uv/tools/<package>/bin/python
    # macOS: ~/Library/Application Support/uv/tools/<package>/bin/python
    # Windows: %APPDATA%/uv/tools/<package>/Scripts/python.exe
    if '/uv/tools/' in executable_str or '\\uv\\tools\\' in executable_str:
        logger.debug(f"uv tool detected: tools path at {executable}")
        return "uv"

    # === Homebrew Detection ===
    # Check for Cellar path (definitive indicator)
    if '/Cellar/' in executable_str:
        logger.debug(f"Homebrew detected: Cellar path at {executable}")
        return "homebrew"

    # Check common Homebrew prefixes
    homebrew_prefixes = [
        '/usr/local',                    # Intel Mac
        '/opt/homebrew',                 # Apple Silicon
        '/home/linuxbrew/.linuxbrew'     # Linuxbrew
    ]

    for prefix in homebrew_prefixes:
        if executable_str.startswith(prefix):
            # Additional check: ensure kuzu-memory is in a Homebrew-managed location
            # (not just using Homebrew's Python for a pip install)
            try:
                import kuzu_memory
                package_path = str(Path(kuzu_memory.__file__))
                if prefix in package_path:
                    logger.debug(f"Homebrew detected: prefix={prefix}")
                    return "homebrew"
            except:
                pass

    # Check HOMEBREW_PREFIX environment variable
    if os.getenv('HOMEBREW_PREFIX'):
        logger.debug("Homebrew detected: HOMEBREW_PREFIX environment variable set")
        return "homebrew"

    # === Default: pip ===
    logger.debug(f"Defaulting to pip: {executable}")
    return "pip"
```

---

### 7.2 Updated VersionChecker Class

```python
class VersionChecker:
    """Handles version checking against PyPI with installation method detection."""

    PYPI_API_URL = "https://pypi.org/pypi/kuzu-memory/json"
    TIMEOUT = 10  # seconds

    def __init__(self) -> None:
        self.current_version = __version__
        self.install_method = _detect_installation_method()
        logger.debug(f"Detected installation method: {self.install_method}")

    # ... existing methods: get_latest_version(), compare_versions() ...

    def get_upgrade_command(self) -> str:
        """
        Return appropriate upgrade command based on installation method.

        Returns:
            Command string to upgrade kuzu-memory
        """
        commands = {
            "pip": "pip install --upgrade kuzu-memory",
            "pipx": "pipx upgrade kuzu-memory",
            "uv": "uv tool upgrade kuzu-memory",
            "homebrew": "brew upgrade kuzu-memory",
            "development": "git pull && uv sync",
        }

        cmd = commands.get(self.install_method, "pip install --upgrade kuzu-memory")
        logger.debug(f"Upgrade command for {self.install_method}: {cmd}")
        return cmd

    def get_install_method_message(self) -> str:
        """
        Get user-friendly message about installation method.

        Returns:
            Human-readable installation method description
        """
        messages = {
            "pip": "Installed via pip",
            "pipx": "Installed via pipx (isolated environment)",
            "uv": "Installed via uv tool (isolated)",
            "homebrew": "Installed via Homebrew",
            "development": "Running from development source",
        }

        return messages.get(self.install_method, "Unknown installation method")
```

---

## 8. Conclusion and Next Steps

### 8.1 Key Findings Summary

1. **No comprehensive auto-update library exists** for Python CLI tools
   - Existing packages are either GitHub-only, Git-only, or unmaintained
   - KuzuMemory's existing `VersionChecker` is already better than most

2. **Installation detection is straightforward** via path analysis
   - Check `sys.executable` for pipx/uv/homebrew patterns
   - Check `__file__` for development mode
   - Default to pip for unknown cases

3. **Popular tools respect installation methods**
   - Poetry, pipx, uv all disable self-update when installed via package managers
   - Clear guidance: "Use the same tool you installed with"

4. **Custom implementation is best approach**
   - Extend existing `VersionChecker` class
   - No new dependencies
   - Full control over detection logic
   - Better user experience with correct upgrade commands

---

### 8.2 Recommended Action Items

**Immediate (This Sprint):**
1. ✅ Implement `_detect_installation_method()` function
2. ✅ Update `VersionChecker.get_upgrade_command()` to use detection
3. ✅ Add `get_install_method_message()` for user display
4. ✅ Update CLI output to show installation method
5. ✅ Write comprehensive unit tests

**Near-term (Next Sprint):**
6. ✅ Document update process for each installation method
7. ✅ Add examples to README.md
8. ✅ Test on real installations (pip, pipx, uv, homebrew, dev)

**Future Enhancements (v2.0):**
9. ⏳ Consider implementing `kuzu-memory self update` command
10. ⏳ Add auto-update check on startup (with opt-out)
11. ⏳ Integrate with CI/CD for automatic version bump detection

---

### 8.3 Success Metrics

**User Experience:**
- ✅ Users get correct upgrade command for their installation method
- ✅ No more "pip upgrade failed" errors from pipx/uv users
- ✅ Clear visibility into how kuzu-memory is installed

**Code Quality:**
- ✅ No new dependencies
- ✅ 100% test coverage for installation detection
- ✅ Graceful fallback for unknown methods

**Adoption:**
- ✅ Reduced support questions about "how to update"
- ✅ Increased successful upgrades (correct commands)

---

## References

### Web Sources

**Auto-Update Packages:**
- [auto-update PyPI Package](https://pypi.org/project/auto-update/)
- [lastversion PyPI Package](https://pypi.org/project/lastversion/)
- [pip-check PyPI Package](https://pypi.org/project/pip-check/)
- [pip-check-updates PyPI Package](https://pypi.org/project/pip-check-updates/)
- [gh-update GitHub Repository](https://github.com/n0samu/gh-update)
- [selfupdate GitHub Repository](https://github.com/erfantkerfan/selfupdate)

**Installation Methods:**
- [pipx Installation Documentation](https://pipx.pypa.io/stable/installation/)
- [pipx GitHub Repository](https://github.com/pypa/pipx)
- [uv Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
- [uv Using Tools Guide](https://docs.astral.sh/uv/guides/tools/)
- [uv Python Versions Documentation](https://docs.astral.sh/uv/concepts/python-versions/)
- [Homebrew Documentation](https://docs.brew.sh/)
- [Homebrew Installation Locations](https://flavor365.com/homebrew-installation-locations-on-macos-explained-2025/)

**Popular CLI Tools:**
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [GitHub CLI Update Discussion](https://github.com/cli/cli/discussions/4630)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Poetry Update Discussion](https://github.com/orgs/python-poetry/discussions/9126)
- [Typer Documentation](https://typer.tiangolo.com/)
- [Click Documentation](https://click.palletsprojects.com/)

**Python Best Practices:**
- [Real Python: Click Tutorial](https://realpython.com/python-click/)
- [Real Python: pipx Guide](https://realpython.com/python-pipx/)
- [Real Python: uv Guide](https://realpython.com/python-uv/)

---

### Codebase References

**KuzuMemory Files Analyzed:**
- `src/kuzu_memory/cli/update_commands.py` - Existing VersionChecker implementation
- `scripts/version.py` - Version management utilities
- `src/kuzu_memory/installers/system_utils.py` - System detection utilities
- `docs/research/auto-update-infinite-loop-bug-2026-01-07.md` - Previous update issues

---

## Appendix: Decision Matrix

| Criterion | External Library | Custom Detection | Status Quo (pip only) |
|-----------|------------------|------------------|----------------------|
| **No new dependencies** | ❌ | ✅ | ✅ |
| **Supports PyPI updates** | ❌ (GitHub only) | ✅ | ✅ |
| **Detects install method** | ❌ | ✅ | ❌ |
| **Correct upgrade commands** | ❌ | ✅ | ❌ |
| **Maintenance burden** | ⚠️ External | ✅ Internal control | ✅ None |
| **Implementation time** | ⏱️ 1-2 days | ⏱️ 2-3 hours | ⏱️ 0 hours |
| **Testing complexity** | ⚠️ High | ✅ Medium | ✅ Low |
| **User experience** | ❌ Poor | ✅ Excellent | ❌ Confusing |

**Winner:** ✅ **Custom Detection** (extends existing VersionChecker)

---

**End of Research Report**
