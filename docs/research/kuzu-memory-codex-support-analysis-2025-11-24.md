# KuzuMemory Install Command - Codex Support Analysis

**Date**: 2025-11-24
**Researcher**: Research Agent
**Project**: kuzu-memory
**Version**: v1.4.49

---

## Executive Summary

**Status**: ❌ **CODEX IS NOT SUPPORTED** in the KuzuMemory install command.

While the user has successfully configured mcp-ticketer for Codex manually (verified in previous research), KuzuMemory itself does NOT have built-in support for Codex installation. Codex is completely absent from all installer registries, CLI command choices, and documentation.

### Key Findings

❌ **No Codex Installer**: No installer class exists for Codex
❌ **Not in Registry**: Codex not registered in `InstallerRegistry`
❌ **Not in CLI**: Codex not listed in install command choices
❌ **No Documentation**: No mention of Codex support in README
❌ **No TODOs**: No planned work for Codex support found

✅ **Working Pattern**: Auggie MCP installer provides TOML reference
✅ **Similar Use Case**: Auggie uses global config like Codex would

---

## Current Platform Support

### Supported Platforms (Install Command)

**From `install_unified.py` line 23-31:**
```python
AVAILABLE_INTEGRATIONS = [
    "claude-code",
    "claude-desktop",
    "cursor",
    "vscode",
    "windsurf",
    "auggie",
    "auggie-mcp",
]
```

**From `setup_commands.py` line 32-36:**
```python
type=click.Choice(
    ["claude-code", "claude-desktop", "cursor", "vscode", "windsurf", "auggie"],
    case_sensitive=False,
)
```

**Missing**: `codex`, `codex-mcp`, or any Codex-related integration

### Registered Installers (Registry)

**From `registry.py` line 39-63:**
```python
def _register_builtin_installers(self):
    """Register built-in installers."""
    # AI System Installers (ONE PATH per system)
    self.register("auggie", AuggieInstaller)
    self.register("auggie-mcp", AuggieMCPInstaller)
    self.register("claude-code", ClaudeHooksInstaller)
    self.register("claude-desktop", SmartClaudeDesktopInstaller)
    self.register("universal", UniversalInstaller)

    # MCP-specific installers (Priority 1)
    self.register("cursor", CursorInstaller)
    self.register("vscode", VSCodeInstaller)
    self.register("windsurf", WindsurfInstaller)

    # Legacy aliases (DEPRECATED - will show warnings)
    self.register("claude", ClaudeHooksInstaller)
    self.register("claude-mcp", ClaudeHooksInstaller)
    self.register("claude-desktop-pipx", ClaudeDesktopPipxInstaller)
    self.register("claude-desktop-home", ClaudeDesktopHomeInstaller)
    self.register("generic", UniversalInstaller)
```

**Missing**: No `CodexInstaller`, `CodexMCPInstaller`, or Codex aliases

### Available Installer Files

**From glob `src/kuzu_memory/installers/*_installer.py`:**
- `auggie_mcp_installer.py` ✅ (TOML reference implementation)
- `cursor_installer.py`
- `vscode_installer.py`
- `windsurf_installer.py`

**Missing**: No `codex_installer.py` or similar

---

## Codex Configuration Requirements

### Known Codex Config Format (from previous research)

**Location**: `~/.codex/config.toml`

**Format** (TOML, not JSON like other installers):
```toml
[mcp_servers.kuzu-memory]
command = "kuzu-memory"
args = ["mcp"]
env = { KUZU_MEMORY_PROJECT_ROOT = "/path/to/project" }
```

**Key Differences from Other Platforms:**
1. **TOML format** (not JSON like Claude Desktop, Auggie, etc.)
2. **Global configuration** (like Auggie MCP, not project-specific)
3. **Location**: `~/.codex/config.toml` (standardized path)

---

## Reference Implementation: Auggie MCP Installer

**Why Auggie MCP is relevant:**
- Also uses **global configuration** (not project-specific)
- Modifies home directory config: `~/.augment/settings.json`
- Similar pattern to what Codex would need: `~/.codex/config.toml`

**From `auggie_mcp_installer.py`:**

### Key Patterns for Codex Implementation

**1. Config Path Detection** (line 51-53):
```python
def _get_config_path(self) -> Path:
    """Get path to Auggie settings configuration file."""
    return Path.home() / ".augment" / "settings.json"
```

**For Codex, this would be:**
```python
def _get_config_path(self) -> Path:
    """Get path to Codex configuration file."""
    return Path.home() / ".codex" / "config.toml"
```

**2. Server Config Creation** (line 55-68):
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

**For Codex (TOML format):**
```python
def _create_kuzu_server_config(self) -> dict:
    """Create KuzuMemory MCP server configuration for TOML."""
    return {
        "mcp_servers": {  # Note: snake_case for TOML
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
```

**3. Config Merging** (line 169-179):
```python
# Merge configurations
if existing_config and not force:
    # Preserve existing servers
    merged_config = merge_json_configs(existing_config, kuzu_config)
    if verbose:
        logger.info("Merging with existing configuration")
        logger.info(
            f"Existing servers: {list(existing_config.get('mcpServers', {}).keys())}"
        )
else:
    # Use new config (force mode or no existing config)
    merged_config = kuzu_config
```

**For Codex: Same pattern but with TOML serialization**

---

## Implementation Gap Analysis

### Missing Components for Codex Support

#### 1. **Codex Installer Class**
**Status**: ❌ Missing
**File**: Should be `src/kuzu_memory/installers/codex_installer.py`

**Required Methods:**
```python
class CodexInstaller(BaseInstaller):
    @property
    def ai_system_name(self) -> str:
        return "Codex"

    @property
    def description(self) -> str:
        return "Install MCP server configuration for Codex (global: ~/.codex/config.toml)"

    def _get_config_path(self) -> Path:
        return Path.home() / ".codex" / "config.toml"

    def _create_kuzu_server_config(self) -> dict:
        # Return TOML-compatible dict
        pass

    def install(self, force=False, dry_run=False, **kwargs) -> InstallationResult:
        # Load TOML, merge, save TOML
        pass
```

#### 2. **TOML Utilities**
**Status**: ❌ Missing
**File**: Would need `src/kuzu_memory/installers/toml_utils.py`

**Required Functions:**
```python
def load_toml_config(path: Path) -> dict:
    """Load TOML configuration file."""
    import toml  # or tomli for Python <3.11
    if path.exists():
        return toml.load(path)
    return {}

def save_toml_config(path: Path, config: dict) -> None:
    """Save configuration to TOML file."""
    import toml
    with path.open('w') as f:
        toml.dump(config, f)

def merge_toml_mcp_servers(existing: dict, new: dict) -> dict:
    """Merge TOML mcp_servers sections."""
    # Similar to merge_json_configs but for TOML structure
    pass
```

**Alternative**: Could use existing `json_utils.py` if converting dict to TOML

#### 3. **Registry Registration**
**Status**: ❌ Missing
**File**: `src/kuzu_memory/installers/registry.py`

**Required Changes (line 39-52):**
```python
def _register_builtin_installers(self):
    """Register built-in installers."""
    # AI System Installers (ONE PATH per system)
    self.register("auggie", AuggieInstaller)
    self.register("auggie-mcp", AuggieMCPInstaller)
    self.register("claude-code", ClaudeHooksInstaller)
    self.register("claude-desktop", SmartClaudeDesktopInstaller)
    self.register("codex", CodexInstaller)  # ← ADD THIS
    self.register("universal", UniversalInstaller)
```

**Import Statement:**
```python
from .codex_installer import CodexInstaller
```

#### 4. **CLI Integration**
**Status**: ❌ Missing
**File**: `src/kuzu_memory/cli/install_unified.py`

**Required Changes (line 23-31):**
```python
AVAILABLE_INTEGRATIONS = [
    "claude-code",
    "claude-desktop",
    "codex",  # ← ADD THIS
    "cursor",
    "vscode",
    "windsurf",
    "auggie",
    "auggie-mcp",
]
```

**Setup Command Integration:**
**File**: `src/kuzu_memory/cli/setup_commands.py` (line 32-36)

```python
type=click.Choice(
    ["claude-code", "claude-desktop", "codex", "cursor", "vscode", "windsurf", "auggie"],
    case_sensitive=False,
)
```

#### 5. **Documentation Updates**
**Status**: ❌ Missing
**Files to Update:**
- `README.md` - Add Codex to supported platforms list
- `docs/GETTING_STARTED.md` - Add Codex installation instructions
- `docs/AI_INTEGRATION.md` - Document Codex integration details

**Example Addition to README.md:**
```markdown
# Install Codex integration (MCP only)
kuzu-memory install codex
```

---

## TOML vs JSON Configuration

### Why Codex Needs Different Handling

**Other Platforms (JSON):**
- Claude Desktop: `~/.config/Claude/claude_desktop_config.json`
- Auggie: `~/.augment/settings.json`
- Cursor: `.cursor/mcp_settings.json`

**Codex (TOML):**
- Location: `~/.codex/config.toml`
- Format: TOML (Tom's Obvious Minimal Language)
- Different nesting conventions

### TOML Format Example

**JSON (Claude Desktop):**
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp"]
    }
  }
}
```

**TOML (Codex):**
```toml
[mcp_servers.kuzu-memory]
command = "kuzu-memory"
args = ["mcp"]

[mcp_servers.kuzu-memory.env]
KUZU_MEMORY_PROJECT_ROOT = "/path/to/project"
```

**Key Differences:**
1. Section headers: `[mcp_servers.name]` vs JSON object nesting
2. Snake_case: `mcp_servers` vs `mcpServers` (camelCase)
3. Environment: Nested `[mcp_servers.name.env]` section
4. No trailing commas (TOML doesn't use them)

---

## Recommended Implementation Plan

### Phase 1: Core Codex Installer (3-5 hours)

**1.1. Create TOML Utilities Module** (1 hour)
- File: `src/kuzu_memory/installers/toml_utils.py`
- Functions: `load_toml_config`, `save_toml_config`, `merge_toml_mcp_servers`
- Add `toml` dependency to `pyproject.toml`
- Tests: `tests/unit/test_toml_utils.py`

**1.2. Create Codex Installer** (2 hours)
- File: `src/kuzu_memory/installers/codex_installer.py`
- Inherit from `BaseInstaller`
- Implement config path detection: `~/.codex/config.toml`
- Implement TOML-based config merging
- Handle global scope (like Auggie MCP)
- Tests: `tests/unit/test_codex_installer.py`

**1.3. Register Codex Installer** (30 minutes)
- Update `src/kuzu_memory/installers/registry.py`
- Add import: `from .codex_installer import CodexInstaller`
- Register: `self.register("codex", CodexInstaller)`
- Update `__init__.py` exports if needed

### Phase 2: CLI Integration (1-2 hours)

**2.1. Update Install Commands** (30 minutes)
- File: `src/kuzu_memory/cli/install_unified.py`
- Add "codex" to `AVAILABLE_INTEGRATIONS`
- Update help text to mention Codex

**2.2. Update Setup Command** (30 minutes)
- File: `src/kuzu_memory/cli/setup_commands.py`
- Add "codex" to `click.Choice` list
- Update examples/help text

**2.3. Update Install Simple Commands** (optional, 15 minutes)
- File: `src/kuzu_memory/cli/install_commands_simple.py`
- Add "codex" to platform choices (line 43)

### Phase 3: Documentation (1 hour)

**3.1. Update README.md**
- Add Codex to "Available Integrations" section
- Add Codex to installation examples
- Document Codex-specific behavior (global config, TOML format)

**3.2. Update AI_INTEGRATION.md**
- Add Codex integration guide
- Document config file location
- Explain TOML format differences

**3.3. Create Codex Setup Guide** (optional)
- New file: `docs/CODEX_SETUP.md`
- Step-by-step Codex installation
- Troubleshooting tips

### Phase 4: Testing (2-3 hours)

**4.1. Unit Tests**
- Test TOML utilities (load, save, merge)
- Test Codex installer (install, uninstall, status)
- Test config path detection
- Test merging existing configs

**4.2. Integration Tests**
- Test end-to-end installation: `kuzu-memory install codex`
- Test with existing Codex configs (preserve other servers)
- Test dry-run mode
- Test force reinstall

**4.3. Manual Testing**
- Test on real Codex installation
- Verify MCP server starts correctly
- Test with multiple projects
- Verify `kuzu-memory setup` detects Codex

---

## Code References

### File Locations for Implementation

**1. Installer Implementation:**
```
src/kuzu_memory/installers/
├── codex_installer.py (NEW - create this)
├── toml_utils.py (NEW - create this)
├── base.py (reference for BaseInstaller)
├── auggie_mcp_installer.py (reference for global config pattern)
└── json_utils.py (reference for config utilities)
```

**2. Registry Updates:**
```
src/kuzu_memory/installers/registry.py
- Line 10: Add import for CodexInstaller
- Line 46: Add registration: self.register("codex", CodexInstaller)
```

**3. CLI Updates:**
```
src/kuzu_memory/cli/
├── install_unified.py (line 23: add "codex" to list)
├── setup_commands.py (line 32: add "codex" to Choice)
└── install_commands_simple.py (line 43: add "codex" to Choice)
```

**4. Tests:**
```
tests/
├── unit/
│   ├── test_codex_installer.py (NEW)
│   └── test_toml_utils.py (NEW)
└── integration/
    └── test_codex_installation.py (NEW)
```

---

## Decision: Priority and Scope

### Should Codex Support Be Added?

**Arguments FOR:**
✅ User explicitly requested it (investigating current support)
✅ Clear pattern exists (Auggie MCP installer)
✅ Reasonable effort (5-8 hours total)
✅ Increases platform coverage
✅ TOML utilities could be useful for future platforms

**Arguments AGAINST:**
❌ User already has working manual configuration
❌ Codex may not have large user base (vs Claude Code, Cursor)
❌ Adds maintenance burden (another installer to support)
❌ TOML dependency (extra package)

### Recommendation

**MEDIUM PRIORITY** - Add Codex support if:
1. User confirms they want automated installation (vs manual config)
2. Multiple users request Codex support
3. Team wants to maximize platform coverage

**DEFER** if:
- User's manual config is sufficient
- No other Codex users in community
- Team wants to focus on higher-priority features

### Alternative: Document Manual Configuration

**Lower Effort Option** (1 hour):
Instead of implementing installer, create documentation:
- File: `docs/CODEX_MANUAL_SETUP.md`
- Document manual TOML configuration steps
- Provide template config file
- Explain how to add KuzuMemory to existing Codex config

---

## Appendix: Example Implementation Snippets

### Minimal CodexInstaller (TOML-based)

```python
"""
Codex MCP installer for KuzuMemory.

Installs MCP server configuration for Codex (global configuration).
"""

import logging
from pathlib import Path
try:
    import tomli as toml  # Python <3.11
except ImportError:
    import tomllib as toml  # Python 3.11+

from .base import BaseInstaller, InstallationResult

logger = logging.getLogger(__name__)


class CodexInstaller(BaseInstaller):
    """
    Installer for Codex MCP integration.

    Creates ~/.codex/config.toml configuration with KuzuMemory MCP server.
    Preserves existing MCP servers in the configuration.

    Note: Codex uses a global TOML configuration file, not project-specific.
    """

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system this installer supports."""
        return "Codex"

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
        """Create KuzuMemory MCP server configuration for TOML."""
        return {
            "mcp_servers": {  # Note: snake_case for TOML
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

    def install(self, force: bool = False, dry_run: bool = False, **kwargs) -> InstallationResult:
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
            # Check prerequisites
            codex_dir = config_path.parent
            if not codex_dir.exists():
                codex_dir.mkdir(parents=True, exist_ok=True)

            # Load existing TOML configuration
            if config_path.exists():
                with config_path.open('rb') as f:
                    existing_config = toml.load(f)
            else:
                existing_config = {}

            # Create KuzuMemory server config
            kuzu_config = self._create_kuzu_server_config()

            # Merge configurations (preserve existing servers)
            if "mcp_servers" not in existing_config:
                existing_config["mcp_servers"] = {}

            existing_config["mcp_servers"]["kuzu-memory"] = kuzu_config["mcp_servers"]["kuzu-memory"]

            # Dry run mode
            if dry_run:
                message = f"[DRY RUN] Would install MCP configuration to {config_path}"
                return InstallationResult(
                    success=True,
                    ai_system=self.ai_system_name,
                    files_created=[],
                    files_modified=[config_path] if config_path.exists() else [],
                    backup_files=[],
                    message=message,
                    warnings=[],
                )

            # Create backup if file exists
            if config_path.exists():
                backup_path = self.create_backup(config_path)
                self.files_modified.append(config_path)
            else:
                self.files_created.append(config_path)

            # Save TOML configuration
            import toml as toml_writer  # Use toml for writing (tomli is read-only)
            with config_path.open('w') as f:
                toml_writer.dump(existing_config, f)

            message = f"Successfully installed MCP configuration for {self.ai_system_name}"
            message += f"\nConfiguration file: {config_path}"
            message += f"\nProject: {self.project_root}"

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=message,
                warnings=["Note: Codex uses a global configuration file. This configuration applies to all projects."],
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

## Memory Updates

```json
{
  "remember": [
    "KuzuMemory does NOT currently support Codex in its install command",
    "Codex would require TOML utilities (not JSON like other platforms)",
    "Codex config location is ~/.codex/config.toml (global, like Auggie MCP)",
    "AuggieMCPInstaller provides reference pattern for global config installers",
    "Implementation would require: CodexInstaller class, TOML utils, registry update, CLI update",
    "Estimated effort: 5-8 hours for complete implementation with tests",
    "User has working manual Codex configuration for mcp-ticketer",
    "Decision needed: Implement Codex support vs document manual configuration"
  ]
}
```
