# Codex Installer Implementation Analysis

**Date**: 2025-11-24
**Purpose**: Analyze existing installer patterns for implementing Codex installer
**Status**: Complete

---

## Executive Summary

This analysis examines KuzuMemory's existing installer patterns to guide implementation of a Codex installer. Key findings:

1. **BaseInstaller provides comprehensive framework** with abstract methods, backup/restore, and error handling
2. **AuggieMCPInstaller demonstrates global config pattern** similar to what Codex needs
3. **TOML handling is available via tomllib** (Python 3.11+, already used in claude_hooks.py)
4. **Config merging utilities exist in json_utils.py** and can be adapted for TOML
5. **No TOML utilities exist yet** - need to create toml_utils.py analogous to json_utils.py

---

## 1. BaseInstaller Abstract Class Analysis

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/base.py`

### Required Abstract Properties

```python
@property
@abstractmethod
def ai_system_name(self) -> str:
    """Name of the AI system this installer supports."""
    pass

@property
@abstractmethod
def required_files(self) -> list[str]:
    """List of files that will be created/modified by this installer."""
    pass

@property
@abstractmethod
def description(self) -> str:
    """Description of what this installer does."""
    pass
```

### Required Abstract Method

```python
@abstractmethod
def install(self, force: bool = False, **kwargs) -> InstallationResult:
    """
    Install integration for the AI system.

    Args:
        force: Force installation even if files exist
        **kwargs: Additional installer-specific options

    Returns:
        InstallationResult with details of what was installed
    """
    pass
```

### Optional Methods (with default implementations)

- `check_prerequisites()` - Check if prerequisites are met
- `uninstall()` - Remove integration (base implementation provided)
- `get_status()` - Get installation status
- `detect_installation()` - Detect if system is installed
- `_check_mcp_configured()` - Check if MCP is configured (override for custom checks)

### Utility Methods Available

```python
# Backup and file operations
create_backup(file_path: Path) -> Path | None
write_file(file_path: Path, content: str, backup: bool = True) -> bool
copy_template(template_name: str, destination: Path, replacements: dict) -> bool
```

### Instance Variables

```python
def __init__(self, project_root: Path):
    self.project_root = Path(project_root)
    self.backup_dir = self.project_root / ".kuzu-memory-backups"
    self.files_created = []
    self.files_modified = []
    self.backup_files = []
    self.warnings = []
```

---

## 2. AuggieMCPInstaller Pattern Analysis

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/auggie_mcp_installer.py`

### Key Characteristics (Similar to Codex)

1. **Global Configuration**: Uses `~/.augment/settings.json` (not project-specific)
2. **Config Location Method**: `_get_config_path()` returns global path
3. **Empty required_files**: Returns `[]` since config is global, not in project
4. **Prerequisite Handling**: Creates config directory if missing

### Configuration Path Pattern

```python
def _get_config_path(self) -> Path:
    """Get path to Auggie settings configuration file."""
    return Path.home() / ".augment" / "settings.json"
```

**For Codex**, this would be:
```python
def _get_config_path(self) -> Path:
    """Get path to Codex configuration file."""
    return Path.home() / ".codex" / "config.toml"
```

### MCP Server Config Creation

```python
def _create_kuzu_server_config(self) -> dict:
    """Create KuzuMemory MCP server configuration."""
    return {
        "mcpServers": {
            "kuzu-memory": create_mcp_server_config(
                command="kuzu-memory",
                args=["mcp"],
                env={
                    "KUZU_MEMORY_PROJECT_ROOT": str(self.project_root),
                    "KUZU_MEMORY_DB": str(self.project_root / "kuzu-memories"),
                },
            )
        }
    }
```

### Prerequisite Check Pattern

```python
def check_prerequisites(self) -> list[str]:
    errors = []

    # Check project root exists
    if not self.project_root.exists():
        errors.append(f"Project root does not exist: {self.project_root}")

    # Check/create config directory
    config_path = self._get_config_path()
    config_dir = config_path.parent

    if not config_dir.exists():
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created Auggie config directory: {config_dir}")
        except Exception as e:
            errors.append(f"Cannot create config directory {config_dir}: {e}")

    return errors
```

### Install Method Structure

```python
def install(self, force: bool = False, dry_run: bool = False, **kwargs) -> InstallationResult:
    verbose = kwargs.get("verbose", False)
    config_path = self._get_config_path()

    try:
        # 1. Check prerequisites
        prereq_errors = self.check_prerequisites()
        if prereq_errors:
            return InstallationResult(success=False, ...)

        # 2. Load existing configuration
        existing_config = load_json_config(config_path) if config_path.exists() else {}

        # 3. Auto-fix broken MCP configurations
        existing_config, fixes = fix_broken_mcp_args(existing_config)

        # 4. Create KuzuMemory server config
        kuzu_config = self._create_kuzu_server_config()

        # 5. Expand variables
        variables = get_standard_variables(self.project_root)
        kuzu_config = expand_variables(kuzu_config, variables)

        # 6. Check if already configured
        existing_servers = existing_config.get("mcpServers", {})
        kuzu_already_exists = "kuzu-memory" in existing_servers

        if kuzu_already_exists and not force:
            # Check if configuration is identical
            if existing_kuzu == new_kuzu:
                return InstallationResult(success=True, message="Already configured", ...)

        # 7. Merge configurations
        if existing_config and not force:
            merged_config = merge_json_configs(existing_config, kuzu_config)
        else:
            merged_config = kuzu_config

        # 8. Validate merged configuration
        validation_errors = validate_mcp_config(merged_config)
        if validation_errors:
            return InstallationResult(success=False, ...)

        # 9. Handle dry run
        if dry_run:
            return InstallationResult(success=True, message="[DRY RUN] ...", ...)

        # 10. Create backup if file exists
        if config_path.exists():
            backup_path = self.create_backup(config_path)
            self.files_modified.append(config_path)
        else:
            self.files_created.append(config_path)

        # 11. Save merged configuration
        save_json_config(config_path, merged_config)

        # 12. Return success
        return InstallationResult(success=True, ...)

    except Exception as e:
        logger.error(f"Installation failed: {e}", exc_info=True)
        return InstallationResult(success=False, ...)
```

### Config Merging Strategy

Uses `merge_json_configs()` from json_utils.py:

```python
# Preserve existing servers
merged_config = merge_json_configs(existing_config, kuzu_config)

# With preserve_existing=True (default):
# - Existing servers are preserved
# - New server is added
# - Nested dicts are recursively merged
```

### Warning Pattern for Global Configs

```python
# Add note about global configuration
self.warnings.append(
    "Note: Auggie uses a global configuration file. "
    "This configuration applies to all projects."
)
```

---

## 3. TOML Handling Analysis

### Existing TOML Usage

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_hooks.py` (lines 602-605)

```python
import tomllib

with open(self.project_root / "pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)
```

**Key Points**:
1. Uses `tomllib` from Python 3.11+ standard library
2. Opens file in **binary mode** (`"rb"`) - TOML requires binary
3. Read-only library (cannot write TOML)

### TOML Reading vs Writing

**Reading TOML**:
- Python 3.11+: `import tomllib` (standard library, read-only)
- Python <3.11: `import tomli` (requires dependency)

**Writing TOML**:
- Need third-party library: `toml` or `tomli_w`
- Not in standard library
- Codex installer will need to **add dependency**

### Dependencies Required

Current `pyproject.toml` dependencies:
- No TOML writing library present
- Need to add: `tomli-w>=1.0.0` for TOML writing

**Recommendation**: Add to dependencies:
```toml
dependencies = [
    # ... existing ...
    "tomli-w>=1.0.0",     # TOML writing (tomllib is read-only)
]
```

---

## 4. JSON Utils Analysis (Adaptable to TOML)

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/json_utils.py`

### Utility Functions to Adapt for TOML

1. **expand_variables(config, variables)** - ✅ Format-agnostic (works on dicts)
2. **merge_configs(existing, new, preserve_existing)** - ✅ Format-agnostic
3. **load_config(file_path)** - ❌ Needs TOML version (binary read)
4. **save_config(file_path, config)** - ❌ Needs TOML version (use tomli_w)
5. **validate_mcp_config(config)** - ✅ Format-agnostic (works on dicts)
6. **get_standard_variables(project_root)** - ✅ Format-agnostic
7. **create_mcp_server_config(command, args, env)** - ✅ Format-agnostic

### Required New TOML Utilities

Create `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/toml_utils.py`:

```python
"""
TOML utility functions for MCP configuration management.

Provides TOML loading, saving, merging, and validation for MCP configs.
"""

import logging
from pathlib import Path
from typing import Any

# Python 3.11+ has tomllib built-in (read-only)
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Fallback for Python <3.11

# TOML writing requires third-party library
try:
    import tomli_w
except ImportError:
    raise ImportError(
        "tomli_w is required for TOML writing. "
        "Install with: pip install tomli-w"
    )

logger = logging.getLogger(__name__)


class TOMLConfigError(Exception):
    """Raised when TOML configuration operations fail."""
    pass


def load_toml_config(file_path: Path) -> dict[str, Any]:
    """
    Load TOML configuration from file.

    Args:
        file_path: Path to TOML file

    Returns:
        Configuration dictionary

    Raises:
        TOMLConfigError: If file cannot be loaded or parsed
    """
    try:
        if not file_path.exists():
            return {}

        # TOML requires binary mode
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise TOMLConfigError(f"Invalid TOML in {file_path}: {e}")
    except Exception as e:
        raise TOMLConfigError(f"Failed to load {file_path}: {e}")


def save_toml_config(file_path: Path, config: dict[str, Any]) -> None:
    """
    Save TOML configuration to file.

    Args:
        file_path: Path to save to
        config: Configuration dictionary

    Raises:
        TOMLConfigError: If file cannot be saved
    """
    try:
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write TOML with tomli_w
        with open(file_path, "wb") as f:
            tomli_w.dump(config, f)

        logger.info(f"Saved TOML configuration to {file_path}")
    except Exception as e:
        raise TOMLConfigError(f"Failed to save {file_path}: {e}")


def merge_toml_configs(
    existing: dict[str, Any],
    new: dict[str, Any],
    preserve_existing: bool = True
) -> dict[str, Any]:
    """
    Merge two TOML configurations, preserving existing MCP servers.

    Delegates to merge_json_configs since logic is format-agnostic.
    """
    from .json_utils import merge_json_configs
    return merge_json_configs(existing, new, preserve_existing)


def validate_toml_mcp_config(config: dict[str, Any]) -> list[str]:
    """
    Validate MCP server configuration from TOML.

    Delegates to validate_mcp_config since logic is format-agnostic.
    """
    from .json_utils import validate_mcp_config
    return validate_mcp_config(config)
```

---

## 5. Codex Configuration Structure

### Codex Config File Location

**Path**: `~/.codex/config.toml`

### Expected TOML Structure

Based on research (docs/research/kuzu-memory-codex-support-analysis-2025-11-24.md):

```toml
[mcp_servers.kuzu-memory]
command = "kuzu-memory"
args = ["mcp"]

[mcp_servers.kuzu-memory.env]
KUZU_MEMORY_PROJECT_ROOT = "/path/to/project"
KUZU_MEMORY_DB = "/path/to/project/kuzu-memories"
```

### Equivalent Python Dict

```python
{
    "mcp_servers": {
        "kuzu-memory": {
            "command": "kuzu-memory",
            "args": ["mcp"],
            "env": {
                "KUZU_MEMORY_PROJECT_ROOT": "/path/to/project",
                "KUZU_MEMORY_DB": "/path/to/project/kuzu-memories"
            }
        }
    }
}
```

**Note**: Codex uses `mcp_servers` (snake_case) not `mcpServers` (camelCase)

---

## 6. Implementation Template for CodexInstaller

```python
"""
Codex installer for KuzuMemory.

Installs MCP server configuration for Codex (global configuration).
"""

import logging
from pathlib import Path

from .base import BaseInstaller, InstallationResult
from .toml_utils import (
    load_toml_config,
    save_toml_config,
    merge_toml_configs,
    validate_toml_mcp_config,
    TOMLConfigError,
)
from .json_utils import (
    expand_variables,
    get_standard_variables,
)

logger = logging.getLogger(__name__)


class CodexInstaller(BaseInstaller):
    """
    Installer for Codex MCP integration.

    Creates ~/.codex/config.toml configuration with KuzuMemory MCP server.
    Preserves existing MCP servers in the configuration.

    Note: Codex uses a global configuration file, not project-specific.
    """

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system this installer supports."""
        return "Codex (MCP)"

    @property
    def required_files(self) -> list[str]:
        """List of files that will be created/modified by this installer."""
        # Global config, not in project directory
        return []

    @property
    def description(self) -> str:
        """Description of what this installer does."""
        return "Install MCP server configuration for Codex (global: ~/.codex/config.toml)"

    def _get_config_path(self) -> Path:
        """Get path to Codex configuration file."""
        return Path.home() / ".codex" / "config.toml"

    def _create_kuzu_server_config(self) -> dict:
        """
        Create KuzuMemory MCP server configuration for Codex.

        Note: Codex uses snake_case 'mcp_servers' not camelCase 'mcpServers'
        """
        return {
            "mcp_servers": {  # Codex uses snake_case
                "kuzu-memory": {
                    "command": "kuzu-memory",
                    "args": ["mcp"],
                    "env": {
                        "KUZU_MEMORY_PROJECT_ROOT": str(self.project_root),
                        "KUZU_MEMORY_DB": str(self.project_root / "kuzu-memories"),
                    }
                }
            }
        }

    def check_prerequisites(self) -> list[str]:
        """
        Check if prerequisites are met for installation.

        Returns:
            List of error messages, empty if all prerequisites are met
        """
        errors = []

        # Check if project root exists
        if not self.project_root.exists():
            errors.append(f"Project root does not exist: {self.project_root}")

        # Check if .codex directory exists, create if not
        config_path = self._get_config_path()
        codex_dir = config_path.parent

        if not codex_dir.exists():
            try:
                codex_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created Codex config directory: {codex_dir}")
            except Exception as e:
                errors.append(f"Cannot create Codex config directory {codex_dir}: {e}")

        return errors

    def install(
        self,
        force: bool = False,
        dry_run: bool = False,
        **kwargs
    ) -> InstallationResult:
        """
        Install MCP configuration for Codex.

        Args:
            force: Force installation even if config exists
            dry_run: Preview changes without modifying files
            **kwargs: Additional options (verbose, etc.)

        Returns:
            InstallationResult with installation details
        """
        verbose = kwargs.get("verbose", False)
        config_path = self._get_config_path()

        try:
            # 1. Check prerequisites
            prereq_errors = self.check_prerequisites()
            if prereq_errors:
                return InstallationResult(
                    success=False,
                    ai_system=self.ai_system_name,
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    message=f"Prerequisites not met: {', '.join(prereq_errors)}",
                    warnings=[],
                )

            # 2. Load existing configuration
            existing_config = load_toml_config(config_path) if config_path.exists() else {}

            # 3. Create KuzuMemory server config
            kuzu_config = self._create_kuzu_server_config()

            # 4. Expand variables
            variables = get_standard_variables(self.project_root)
            kuzu_config = expand_variables(kuzu_config, variables)

            # 5. Check if kuzu-memory is already configured
            existing_servers = existing_config.get("mcp_servers", {})  # snake_case for Codex
            kuzu_already_exists = "kuzu-memory" in existing_servers

            if kuzu_already_exists and not force:
                # Check if configuration is the same
                existing_kuzu = existing_servers["kuzu-memory"]
                new_kuzu = kuzu_config["mcp_servers"]["kuzu-memory"]

                if existing_kuzu == new_kuzu:
                    return InstallationResult(
                        success=True,
                        ai_system=self.ai_system_name,
                        files_created=[],
                        files_modified=[],
                        backup_files=[],
                        message=f"KuzuMemory MCP server already configured for this project in {config_path}",
                        warnings=["Configuration unchanged. Use --force to reinstall."],
                    )
                else:
                    self.warnings.append(
                        "KuzuMemory server exists with different configuration. Use --force to update."
                    )

            # 6. Merge configurations
            if existing_config and not force:
                # Preserve existing servers
                merged_config = merge_toml_configs(existing_config, kuzu_config)
                if verbose:
                    logger.info("Merging with existing configuration")
                    logger.info(
                        f"Existing servers: {list(existing_config.get('mcp_servers', {}).keys())}"
                    )
            else:
                # Use new config (force mode or no existing config)
                merged_config = kuzu_config
                if force and existing_config:
                    self.warnings.append("Force mode: existing configuration will be backed up")

            # 7. Validate merged configuration
            validation_errors = validate_toml_mcp_config(merged_config)
            if validation_errors:
                return InstallationResult(
                    success=False,
                    ai_system=self.ai_system_name,
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    message=f"Configuration validation failed: {', '.join(validation_errors)}",
                    warnings=[],
                )

            # 8. Dry run mode - just report what would happen
            if dry_run:
                message = f"[DRY RUN] Would install MCP configuration to {config_path}"
                if config_path.exists():
                    message += f"\nWould preserve {len(existing_config.get('mcp_servers', {}))} existing server(s)"
                if kuzu_already_exists and not force:
                    message += "\nWould update existing kuzu-memory server configuration"
                else:
                    message += "\nWould add new kuzu-memory server configuration"
                return InstallationResult(
                    success=True,
                    ai_system=self.ai_system_name,
                    files_created=[] if config_path.exists() else [config_path],
                    files_modified=[config_path] if config_path.exists() else [],
                    backup_files=[],
                    message=message,
                    warnings=self.warnings,
                )

            # 9. Track whether file existed before
            file_existed = config_path.exists()

            # 10. Create backup if file exists
            if file_existed:
                backup_path = self.create_backup(config_path)
                if backup_path:
                    if verbose:
                        logger.info(f"Created backup: {backup_path}")
                self.files_modified.append(config_path)
            else:
                self.files_created.append(config_path)

            # 11. Save merged configuration
            save_toml_config(config_path, merged_config)

            # 12. Success message
            server_count = len(merged_config.get("mcp_servers", {}))
            message = f"Successfully installed MCP configuration for {self.ai_system_name}"
            message += f"\nConfiguration file: {config_path}"
            message += f"\nMCP servers configured: {server_count}"
            message += f"\nProject: {self.project_root}"

            if existing_config:
                preserved_count = len(existing_config.get("mcp_servers", {}))
                if preserved_count > 0 and not force:
                    message += f"\nPreserved {preserved_count} existing server(s)"

            # Add note about global configuration
            self.warnings.append(
                "Note: Codex uses a global configuration file. "
                "This configuration applies to all projects."
            )

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=message,
                warnings=self.warnings,
            )

        except TOMLConfigError as e:
            logger.error(f"TOML configuration error: {e}", exc_info=True)
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=[],
                backup_files=[],
                message=f"TOML configuration error: {e}",
                warnings=[],
            )
        except Exception as e:
            logger.error(f"Installation failed: {e}", exc_info=True)
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=[],
                backup_files=[],
                message=f"Installation failed: {e}",
                warnings=[],
            )
```

---

## 7. Key Differences: Codex vs AuggieMCP

| Aspect | AuggieMCP | Codex |
|--------|-----------|-------|
| **Config Format** | JSON | TOML |
| **Config Path** | `~/.augment/settings.json` | `~/.codex/config.toml` |
| **Server Key** | `mcpServers` (camelCase) | `mcp_servers` (snake_case) |
| **Load Function** | `load_json_config()` | `load_toml_config()` |
| **Save Function** | `save_json_config()` | `save_toml_config()` |
| **Read Library** | `json` (stdlib) | `tomllib` (stdlib 3.11+) |
| **Write Library** | `json` (stdlib) | `tomli_w` (requires dependency) |
| **File Mode** | Text (`"r"`, `"w"`) | Binary (`"rb"`, `"wb"`) |
| **Merge Function** | `merge_json_configs()` | `merge_toml_configs()` (delegates to json version) |

---

## 8. Implementation Checklist

### Phase 1: Dependencies
- [ ] Add `tomli-w>=1.0.0` to pyproject.toml dependencies
- [ ] Test TOML reading with `tomllib` (already in Python 3.11+)
- [ ] Test TOML writing with `tomli_w` after adding dependency

### Phase 2: Utilities
- [ ] Create `src/kuzu_memory/installers/toml_utils.py`
- [ ] Implement `load_toml_config(file_path)`
- [ ] Implement `save_toml_config(file_path, config)`
- [ ] Implement `merge_toml_configs()` (delegate to json_utils)
- [ ] Implement `validate_toml_mcp_config()` (delegate to json_utils)
- [ ] Add unit tests for TOML utilities

### Phase 3: Installer
- [ ] Create `src/kuzu_memory/installers/codex_installer.py`
- [ ] Implement `CodexInstaller` class (inherit from `BaseInstaller`)
- [ ] Implement required properties (`ai_system_name`, `required_files`, `description`)
- [ ] Implement `_get_config_path()` → `~/.codex/config.toml`
- [ ] Implement `_create_kuzu_server_config()` with snake_case `mcp_servers`
- [ ] Implement `check_prerequisites()` to create `~/.codex/` directory
- [ ] Implement `install()` method following AuggieMCP pattern
- [ ] Add error handling for `TOMLConfigError`

### Phase 4: Integration
- [ ] Add `CodexInstaller` to installer registry
- [ ] Update installer detection to recognize Codex
- [ ] Add Codex to `kuzu-memory setup` command options
- [ ] Update documentation with Codex installation instructions

### Phase 5: Testing
- [ ] Unit tests for `CodexInstaller`
- [ ] Integration tests for TOML config merging
- [ ] Test backup/restore functionality
- [ ] Test dry-run mode
- [ ] Test force reinstall mode
- [ ] Test preservation of existing MCP servers

---

## 9. Example Codex Config Output

### Before Installation (Empty File)
```toml
# Empty or non-existent file
```

### After Installation (New Config)
```toml
[mcp_servers.kuzu-memory]
command = "kuzu-memory"
args = ["mcp"]

[mcp_servers.kuzu-memory.env]
KUZU_MEMORY_PROJECT_ROOT = "/Users/masa/Projects/my-project"
KUZU_MEMORY_DB = "/Users/masa/Projects/my-project/kuzu-memories"
```

### After Installation (Existing Servers Preserved)
```toml
# Existing server preserved
[mcp_servers.other-mcp-server]
command = "other-server"
args = ["serve"]

# KuzuMemory server added
[mcp_servers.kuzu-memory]
command = "kuzu-memory"
args = ["mcp"]

[mcp_servers.kuzu-memory.env]
KUZU_MEMORY_PROJECT_ROOT = "/Users/masa/Projects/my-project"
KUZU_MEMORY_DB = "/Users/masa/Projects/my-project/kuzu-memories"
```

---

## 10. Error Handling Patterns

### TOML Parse Errors
```python
try:
    config = load_toml_config(config_path)
except TOMLConfigError as e:
    return InstallationResult(
        success=False,
        message=f"Failed to parse TOML config: {e}",
        warnings=["Config file may be corrupted. Backup available if you used --force"]
    )
```

### Missing TOML Writer Dependency
```python
try:
    import tomli_w
except ImportError:
    return InstallationResult(
        success=False,
        message="tomli-w is required for Codex installation. Install with: pip install tomli-w",
        warnings=["Codex installer requires TOML writing support"]
    )
```

### Config Directory Creation Failure
```python
def check_prerequisites(self) -> list[str]:
    errors = []
    codex_dir = Path.home() / ".codex"

    if not codex_dir.exists():
        try:
            codex_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            errors.append(f"Permission denied creating {codex_dir}")
        except Exception as e:
            errors.append(f"Failed to create {codex_dir}: {e}")

    return errors
```

---

## 11. References

### Files Analyzed
1. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/base.py`
2. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/auggie_mcp_installer.py`
3. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_desktop.py`
4. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/json_utils.py`
5. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_hooks.py` (TOML reading)

### Related Research
- `/Users/masa/Projects/kuzu-memory/docs/research/kuzu-memory-codex-support-analysis-2025-11-24.md`

### Python TOML Libraries
- **tomllib**: Python 3.11+ stdlib, read-only
- **tomli**: Python <3.11 fallback, read-only
- **tomli_w**: TOML writing (required dependency)

---

## 12. Next Steps

1. **Add TOML dependency**: Update pyproject.toml with `tomli-w>=1.0.0`
2. **Create toml_utils.py**: Implement TOML utility functions
3. **Create codex_installer.py**: Implement CodexInstaller class
4. **Test TOML operations**: Verify reading, writing, merging
5. **Register installer**: Add to installer registry and detection
6. **Update documentation**: Add Codex installation instructions
7. **Test end-to-end**: Install, uninstall, dry-run, force modes

---

## Appendix A: Complete File Paths

```
Base Classes:
- /Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/base.py

Reference Installers:
- /Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/auggie_mcp_installer.py
- /Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_desktop.py

Utilities:
- /Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/json_utils.py

To Be Created:
- /Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/toml_utils.py
- /Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/codex_installer.py
```

---

## Appendix B: Abstract Methods Summary

**From BaseInstaller that MUST be implemented:**

```python
@property
@abstractmethod
def ai_system_name(self) -> str:
    """Example: return "Codex (MCP)" """

@property
@abstractmethod
def required_files(self) -> list[str]:
    """Example: return []  # Global config, not in project"""

@property
@abstractmethod
def description(self) -> str:
    """Example: return "Install MCP server configuration for Codex" """

@abstractmethod
def install(self, force: bool = False, **kwargs) -> InstallationResult:
    """Full installation logic - see implementation template"""
```

**Optional overrides (have default implementations):**
- `check_prerequisites()` - Recommended to override for directory creation
- `uninstall()` - Base implementation works, but can customize
- `get_status()` - Base implementation works, but can enhance
- `_check_mcp_configured()` - Override for Codex-specific MCP checks

---

*End of Analysis*
