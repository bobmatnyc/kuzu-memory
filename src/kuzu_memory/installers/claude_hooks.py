"""
Claude Code hooks installer for KuzuMemory.

Provides seamless integration with Claude Desktop through MCP (Model Context Protocol)
and project-specific hooks for intelligent memory enhancement.
"""

from __future__ import annotations

import json
import logging
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseInstaller, InstallationError, InstallationResult
from .json_utils import (
    fix_broken_mcp_args,
    load_json_config,
    save_json_config,
)

logger = logging.getLogger(__name__)

# Valid Claude Code hook events (camelCase format)
# Reference: Claude Code uses camelCase event names, not snake_case
VALID_CLAUDE_CODE_EVENTS = {
    "UserPromptSubmit",  # Fires when user submits a prompt
    "PreToolUse",  # Fires before a tool is used
    "PostToolUse",  # Fires after a tool is used
    "Stop",  # Fires when Claude finishes responding
    "SubagentStop",  # Fires when a subagent stops
    "Notification",  # Fires on notifications
    "SessionStart",  # Fires at session start
    "SessionEnd",  # Fires at session end
    "PreCompact",  # Fires before compaction
}


class ClaudeHooksInstaller(BaseInstaller):
    """
    Installer for Claude Code integration with KuzuMemory.

    Sets up:
    1. MCP server configuration for Claude Desktop
    2. Project-specific CLAUDE.md file
    3. Shell script wrappers for compatibility
    4. Environment detection and validation
    """

    def __init__(self, project_root: Path) -> None:
        """Initialize Claude hooks installer."""
        super().__init__(project_root)
        self.claude_config_dir = self._get_claude_config_dir()
        self.mcp_config_path = (
            self.claude_config_dir / "claude_desktop_config.json"
            if self.claude_config_dir
            else None
        )
        self._kuzu_command_path: str | None = None  # Cache for kuzu-memory command path

    def _update_global_mcp_config(self) -> None:
        """Update MCP server config in ~/.claude.json under projects[<path>].mcpServers."""
        global_config_path = Path.home() / ".claude.json"

        # Load or create config
        config: dict[str, Any]
        if global_config_path.exists():
            try:
                with open(global_config_path) as f:
                    config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read ~/.claude.json: {e}")
                raise InstallationError(f"Cannot read global config file: {e}")
        else:
            config = {}

        # Auto-fix broken MCP configurations
        config, fixes = fix_broken_mcp_args(config)
        if fixes:
            logger.info(f"Auto-fixed {len(fixes)} broken MCP configuration(s)")
            for fix in fixes:
                logger.debug(fix)

        # Ensure projects structure exists
        if "projects" not in config:
            config["projects"] = {}

        project_key = str(self.project_root.resolve())
        if project_key not in config["projects"]:
            config["projects"][project_key] = {}

        # Add MCP server config
        if "mcpServers" not in config["projects"][project_key]:
            config["projects"][project_key]["mcpServers"] = {}

        db_path = self._get_project_db_path()
        config["projects"][project_key]["mcpServers"]["kuzu-memory"] = {
            "type": "stdio",
            "command": "kuzu-memory",
            "args": ["mcp"],
            "env": {
                "KUZU_MEMORY_PROJECT_ROOT": str(self.project_root),
                "KUZU_MEMORY_DB": str(db_path),
            },
        }

        # Backup and write
        if global_config_path.exists():
            backup_path = global_config_path.with_suffix(".json.backup")
            shutil.copy(global_config_path, backup_path)
            logger.debug(f"Backed up global config to {backup_path}")

        try:
            with open(global_config_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(
                f"✓ Configured MCP server in ~/.claude.json for project: {self.project_root.name}"
            )
        except Exception as e:
            logger.error(f"Failed to write ~/.claude.json: {e}")
            raise InstallationError(f"Cannot write global config file: {e}")

    def _update_mcp_local_config(self, mcp_local_path: Path) -> None:
        """Update MCP server config in .claude/mcp.local.json for project-level configuration."""
        # Load existing or create new config
        config: dict[str, Any]
        if mcp_local_path.exists():
            try:
                with open(mcp_local_path) as f:
                    config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read {mcp_local_path}: {e}")
                raise InstallationError(f"Cannot read mcp.local.json: {e}")
        else:
            config = {}

        # Auto-fix broken MCP configurations
        config, fixes = fix_broken_mcp_args(config)
        if fixes:
            logger.info(f"Auto-fixed {len(fixes)} broken MCP configuration(s) in mcp.local.json")
            for fix in fixes:
                logger.debug(fix)

        # Ensure mcpServers structure exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Get kuzu-memory command path (prefer Homebrew installation)
        kuzu_cmd = self._get_kuzu_memory_command_path()

        # Add kuzu-memory MCP server configuration
        config["mcpServers"]["kuzu-memory"] = {
            "type": "stdio",
            "command": kuzu_cmd,
            "args": ["mcp"],
            "env": {
                "KUZU_MEMORY_PROJECT": str(self.project_root),
            },
        }

        # Create parent directory if needed
        mcp_local_path.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing file if present
        if mcp_local_path.exists():
            backup_path = mcp_local_path.with_suffix(".json.backup")
            shutil.copy(mcp_local_path, backup_path)
            logger.debug(f"Backed up mcp.local.json to {backup_path}")

        # Write configuration
        try:
            with open(mcp_local_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(
                f"✓ Configured MCP server in {mcp_local_path.relative_to(self.project_root)}"
            )
        except Exception as e:
            logger.error(f"Failed to write {mcp_local_path}: {e}")
            raise InstallationError(f"Cannot write mcp.local.json: {e}")

    def _clean_legacy_mcp_locations(self) -> list[str]:
        """Remove MCP config from incorrect locations. Returns warnings."""
        warnings = []

        # Clean from top-level ~/.claude.json (wrong location)
        global_config_path = Path.home() / ".claude.json"
        if global_config_path.exists():
            try:
                with open(global_config_path) as f:
                    config = json.load(f)

                # Only remove from top-level mcpServers (not from projects)
                if "mcpServers" in config and "kuzu-memory" in config.get("mcpServers", {}):
                    del config["mcpServers"]["kuzu-memory"]

                    # Backup and write
                    backup_path = global_config_path.with_suffix(".json.backup")
                    shutil.copy(global_config_path, backup_path)

                    with open(global_config_path, "w") as f:
                        json.dump(config, f, indent=2)

                    warnings.append(
                        "Moved MCP config from top-level ~/.claude.json to projects section"
                    )
                    logger.info("Cleaned top-level MCP config from ~/.claude.json")
            except Exception as e:
                logger.warning(f"Failed to clean top-level MCP config: {e}")

        # Clean from settings.local.json
        local_settings = self.project_root / ".claude" / "settings.local.json"
        if local_settings.exists():
            try:
                with open(local_settings) as f:
                    settings = json.load(f)

                if "mcpServers" in settings and "kuzu-memory" in settings.get("mcpServers", {}):
                    del settings["mcpServers"]["kuzu-memory"]
                    if not settings["mcpServers"]:
                        del settings["mcpServers"]

                    with open(local_settings, "w") as f:
                        json.dump(settings, f, indent=2)

                    warnings.append("Moved MCP config from settings.local.json to ~/.claude.json")
                    logger.info("Cleaned MCP config from settings.local.json")
            except Exception as e:
                logger.warning(f"Failed to clean settings.local.json MCP config: {e}")

        return warnings

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system."""
        return "claude"

    @property
    def required_files(self) -> list[str]:
        """List of files that will be created/modified."""
        files = [
            "CLAUDE.md",
            ".claude-mpm/config.json",
            ".claude/settings.local.json",
            ".kuzu-memory/config.yaml",
        ]
        return files

    @property
    def description(self) -> str:
        """Description of what this installer does."""
        return "Installs Claude Code hooks with MCP server integration for intelligent memory enhancement"

    def _get_claude_config_dir(self) -> Path | None:
        """
        Get Claude Desktop configuration directory based on platform.

        Returns:
            Path to config directory or None if not found
        """
        system = platform.system()

        if system == "Darwin":  # macOS
            config_dir = Path.home() / "Library" / "Application Support" / "Claude"
        elif system == "Windows":
            config_dir = Path.home() / "AppData" / "Roaming" / "Claude"
        elif system == "Linux":
            config_dir = Path.home() / ".config" / "claude"
        else:
            logger.warning(f"Unsupported platform: {system}")
            return None

        if config_dir.exists():
            return config_dir

        # Alternative locations
        alt_locations = [
            Path.home() / ".claude",
            Path.home() / ".config" / "Claude",
            Path.home() / "Library" / "Application Support" / "Claude Desktop",
        ]

        for loc in alt_locations:
            if loc.exists():
                return loc

        logger.debug("Claude config directory not found in any location")
        return None

    def check_prerequisites(self) -> list[str]:
        """Check if prerequisites are met for installation."""
        errors = super().check_prerequisites()

        # Check for kuzu-memory installation
        try:
            result = subprocess.run(
                ["kuzu-memory", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                errors.append("kuzu-memory CLI is not properly installed")
        except (subprocess.SubprocessError, FileNotFoundError):
            errors.append("kuzu-memory is not installed or not in PATH")

        # Warn about Claude Desktop (but don't fail)
        if not self.claude_config_dir:
            logger.info("Claude Desktop not detected - will create local configuration only")

        return errors

    def _get_project_db_path(self) -> Path:
        """
        Get the project-specific database path.

        Returns:
            Path to project database directory
        """
        return self.project_root / "kuzu-memories"

    def _get_project_config_path(self) -> Path:
        """
        Get the project-specific config file path.

        Returns:
            Path to project config.yaml
        """
        return self.project_root / ".kuzu-memory" / "config.yaml"

    def _get_kuzu_memory_command_path(self) -> str:
        """
        Get the actual kuzu-memory command path.

        Finds the kuzu-memory executable that's running this installer by using sys.executable.
        This ensures hooks always use the correct installation regardless of method
        (pipx, homebrew, pip, source, etc.).

        Priority order:
        1. Same bin directory as the Python running this installer (HIGHEST PRIORITY)
        2. pipx installation (supports MCP server)
        3. Local development installation (supports MCP server)
        4. System-wide installation (may not support MCP server)

        Returns:
            Full path to kuzu-memory executable, or 'kuzu-memory' if not found
        """
        if self._kuzu_command_path is not None:
            return self._kuzu_command_path

        # Priority 1: Use the kuzu-memory from the same bin directory as sys.executable
        # This ensures we use the installation that's actually running the installer
        python_exe = Path(sys.executable)
        installer_kuzu_path = python_exe.parent / "kuzu-memory"

        if installer_kuzu_path.exists() and self._verify_mcp_support(installer_kuzu_path):
            self._kuzu_command_path = str(installer_kuzu_path)
            logger.info(f"Using kuzu-memory from installer environment at: {installer_kuzu_path}")
            return str(installer_kuzu_path)

        # Priority 2: Check for pipx installation (most reliable for MCP server)
        pipx_paths = [
            Path.home() / ".local" / "pipx" / "venvs" / "kuzu-memory" / "bin" / "kuzu-memory",
            Path.home() / ".local" / "bin" / "kuzu-memory",  # pipx ensurepath location
        ]

        for pipx_path in pipx_paths:
            if pipx_path.exists() and self._verify_mcp_support(pipx_path):
                self._kuzu_command_path = str(pipx_path)
                logger.info(f"Using pipx installation at: {pipx_path}")
                return str(pipx_path)

        # Priority 3: Check for local development installation
        dev_paths = [
            self.project_root / "venv" / "bin" / "kuzu-memory",
            self.project_root / ".venv" / "bin" / "kuzu-memory",
        ]

        for dev_path in dev_paths:
            if dev_path.exists() and self._verify_mcp_support(dev_path):
                self._kuzu_command_path = str(dev_path)
                logger.info(f"Using development installation at: {dev_path}")
                return str(dev_path)

        # Priority 4: Use shutil.which to find any kuzu-memory in PATH
        try:
            command_path = shutil.which("kuzu-memory")
            if command_path:
                # Verify MCP support before using
                if self._verify_mcp_support(command_path):
                    self._kuzu_command_path = command_path
                    logger.info(f"Found kuzu-memory with MCP support at: {command_path}")
                    return command_path
                else:
                    logger.warning(
                        f"Found kuzu-memory at {command_path} but it doesn't support MCP server. "
                        "Please reinstall with: pip uninstall kuzu-memory && pipx install kuzu-memory"
                    )
        except Exception as e:
            logger.debug(f"Failed to locate kuzu-memory: {e}")

        # Fallback to plain command (will likely fail if MCP server is needed)
        self._kuzu_command_path = "kuzu-memory"
        logger.warning("Using plain 'kuzu-memory' command - MCP server may not work")
        return "kuzu-memory"

    def _verify_mcp_support(self, command_path: str | Path) -> bool:
        """
        Verify that the kuzu-memory installation supports MCP server.

        Args:
            command_path: Path to kuzu-memory executable

        Returns:
            True if MCP server is supported, False otherwise
        """
        try:
            result = subprocess.run(
                [str(command_path), "--help"], capture_output=True, text=True, timeout=5
            )
            # Check if "mcp" command is in the help output
            return "mcp" in result.stdout.lower()
        except Exception as e:
            logger.debug(f"Failed to verify MCP support for {command_path}: {e}")
            return False

    def _is_kuzu_hook(self, hook_entry: dict[str, Any]) -> bool:
        """
        Check if a hook entry is a kuzu-memory hook.

        Handles multiple formats:
        1. Direct handler format: {"handler": "kuzu_memory_...", ...}
        2. Direct command format: {"command": "...kuzu-memory hooks..."}

        Args:
            hook_entry: Hook configuration entry

        Returns:
            True if this is a kuzu-memory hook, False otherwise
        """
        # Check direct handler format
        handler = hook_entry.get("handler", "")
        if "kuzu_memory" in handler or "kuzu-memory" in handler:
            return True

        # Check script-based format (nested hooks array with matcher)
        if "hooks" in hook_entry and isinstance(hook_entry["hooks"], list):
            for nested_hook in hook_entry["hooks"]:
                command = nested_hook.get("command", "")
                if "kuzu" in command.lower():
                    return True

        # Check direct command format
        command = hook_entry.get("command", "")
        if "kuzu" in command.lower():
            return True

        return False

    def _validate_hook_events(self, config: dict[str, Any]) -> None:
        """
        Validate hook event names against Claude Code specification.

        Logs warnings for any invalid event names that won't work in Claude Code.

        Args:
            config: Configuration dictionary containing 'hooks' section
        """
        if "hooks" not in config:
            return

        invalid_events = set(config["hooks"].keys()) - VALID_CLAUDE_CODE_EVENTS
        if invalid_events:
            logger.warning(
                f"Invalid Claude Code hook events detected: {invalid_events}. "
                f"Valid events are: {VALID_CLAUDE_CODE_EVENTS}. "
                "These hooks will not fire in Claude Code."
            )

    def _create_claude_code_hooks_config(self) -> dict[str, Any]:
        """
        Create Claude Code hooks configuration (for settings.local.json) using CLI entry points.

        Configures two hooks:
        - UserPromptSubmit: Enhances prompts with project context
        - PostToolUse: Learns from conversations asynchronously

        Uses absolute path to the kuzu-memory executable to avoid PATH resolution issues.

        Returns:
            Claude Code hooks configuration dict
        """
        # Get package version for comment
        try:
            from importlib.metadata import version

            pkg_version = version("kuzu-memory")
        except Exception:
            pkg_version = "1.3.3+"

        # Use absolute path to avoid PATH resolution issues
        # Find the kuzu-memory that's running this installer
        kuzu_memory_path = self._get_kuzu_memory_command_path()

        config = {
            "_comment": f"Generated by KuzuMemory v{pkg_version} - Claude Code hooks configuration",
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"{kuzu_memory_path} hooks session-start",
                            }
                        ],
                    }
                ],
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"{kuzu_memory_path} hooks enhance",
                            }
                        ],
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"{kuzu_memory_path} hooks learn",
                            }
                        ],
                    }
                ],
            },
        }
        return config

    def _create_claude_code_mcp_config(self) -> dict[str, Any]:
        """
        Create Claude Code MCP server configuration (for settings.local.json).

        Uses the Python executable from the same installation as kuzu-memory
        to ensure MCP server runs with the correct environment.

        Returns:
            Claude Code MCP server configuration dict
        """
        db_path = self._get_project_db_path()

        # Get package version for comment
        try:
            from importlib.metadata import version

            pkg_version = version("kuzu-memory")
        except Exception:
            pkg_version = "1.3.3+"

        config = {
            "_comment": f"Generated by KuzuMemory v{pkg_version} - MCP server configuration",
            "mcpServers": {
                "kuzu-memory": {
                    "type": "stdio",
                    "command": "kuzu-memory",
                    "args": ["mcp"],
                    "env": {
                        "KUZU_MEMORY_PROJECT_ROOT": str(self.project_root),
                        "KUZU_MEMORY_DB": str(db_path),
                    },
                }
            },
        }
        return config

    def _create_claude_md(self) -> str:
        """
        Create CLAUDE.md content for the project.

        Returns:
            CLAUDE.md file content
        """
        # Analyze project to generate context
        project_info = self._analyze_project()

        content = f"""# Project Memory Configuration

This project uses KuzuMemory for intelligent context management.

## Project Information
- **Path**: {self.project_root}
- **Language**: {project_info.get("language", "Unknown")}
- **Framework**: {project_info.get("framework", "Unknown")}

## Memory Integration

KuzuMemory is configured to enhance all AI interactions with project-specific context.

### Available Commands:
- `kuzu-memory enhance <prompt>` - Enhance prompts with project context
- `kuzu-memory learn <content>` - Store learning from conversations (async)
- `kuzu-memory recall <query>` - Query project memories
- `kuzu-memory stats` - View memory statistics

### MCP Tools Available:
When interacting with Claude Desktop, the following MCP tools are available:
- **kuzu_enhance**: Enhance prompts with project memories
- **kuzu_learn**: Store new learnings asynchronously
- **kuzu_recall**: Query specific memories
- **kuzu_stats**: Get memory system statistics

## Project Context

{project_info.get("description", "Add project description here")}

## Key Technologies
{self._format_list(project_info.get("technologies", []))}

## Development Guidelines
{self._format_list(project_info.get("guidelines", []))}

## Memory Guidelines

- Store project decisions and conventions
- Record technical specifications and API details
- Capture user preferences and patterns
- Document error solutions and workarounds

---

*Generated by KuzuMemory Claude Hooks Installer*
"""
        return content

    def _analyze_project(self) -> dict[str, Any]:
        """
        Analyze project to generate initial context.

        Returns:
            Project analysis dictionary
        """
        info: dict[str, Any] = {
            "language": "Unknown",
            "framework": "Unknown",
            "technologies": [],
            "guidelines": [],
            "description": "",
        }

        # Detect Python project
        if (self.project_root / "pyproject.toml").exists():
            info["language"] = "Python"
            info["technologies"].append("Python")

            # Try to parse pyproject.toml
            try:
                import tomllib

                with open(self.project_root / "pyproject.toml", "rb") as f:
                    pyproject = tomllib.load(f)
                    if "project" in pyproject:
                        proj = pyproject["project"]
                        info["description"] = proj.get("description", "")
                        deps = proj.get("dependencies", [])
                        # Detect frameworks
                        for dep in deps:
                            if "fastapi" in dep.lower():
                                info["framework"] = "FastAPI"
                                info["technologies"].append("FastAPI")
                            elif "django" in dep.lower():
                                info["framework"] = "Django"
                                info["technologies"].append("Django")
                            elif "flask" in dep.lower():
                                info["framework"] = "Flask"
                                info["technologies"].append("Flask")
            except Exception as e:
                logger.debug(f"Failed to parse pyproject.toml: {e}")

        # Detect JavaScript/TypeScript project
        elif (self.project_root / "package.json").exists():
            info["language"] = "JavaScript/TypeScript"
            info["technologies"].append("Node.js")

            try:
                with open(self.project_root / "package.json") as f:
                    package = json.load(f)
                    info["description"] = package.get("description", "")
                    deps = {
                        **package.get("dependencies", {}),
                        **package.get("devDependencies", {}),
                    }

                    if "react" in deps:
                        info["framework"] = "React"
                        info["technologies"].append("React")
                    elif "vue" in deps:
                        info["framework"] = "Vue"
                        info["technologies"].append("Vue")
                    elif "express" in deps:
                        info["framework"] = "Express"
                        info["technologies"].append("Express")
            except Exception as e:
                logger.debug(f"Failed to parse package.json: {e}")

        # Add common guidelines
        info["guidelines"] = [
            "Use kuzu-memory enhance for all AI interactions",
            "Store important decisions with kuzu-memory learn",
            "Query context with kuzu-memory recall when needed",
            "Keep memories project-specific and relevant",
        ]

        return info

    def _format_list(self, items: list[str]) -> str:
        """Format a list for markdown."""
        if not items:
            return "- No items specified"
        return "\n".join(f"- {item}" for item in items)

    def _create_project_config(self) -> str:
        """
        Create project-specific configuration file content.

        Returns:
            YAML configuration content
        """
        db_path = self._get_project_db_path()
        return f"""# KuzuMemory Project Configuration
# Generated by Claude Hooks Installer

version: "1.0"
debug: false
log_level: "INFO"

# Database location (project-specific)
database:
  path: {db_path}

# Storage configuration
storage:
  max_size_mb: 50.0
  auto_compact: true
  backup_on_corruption: true
  connection_pool_size: 5
  query_timeout_ms: 5000

# Memory recall configuration
recall:
  max_memories: 10
  default_strategy: "auto"
  strategies:
    - "keyword"
    - "entity"
    - "temporal"
  strategy_weights:
    keyword: 0.4
    entity: 0.4
    temporal: 0.2
  min_confidence_threshold: 0.1
  enable_caching: true
  cache_size: 1000
  cache_ttl_seconds: 300

# Memory extraction configuration
extraction:
  min_memory_length: 5
  max_memory_length: 1000
  enable_entity_extraction: true
  enable_pattern_compilation: true
  enable_nlp_classification: true

# Performance monitoring
performance:
  max_recall_time_ms: 200.0
  max_generation_time_ms: 1000.0
  enable_performance_monitoring: true
  log_slow_operations: true
  enable_metrics_collection: false

# Memory retention
retention:
  enable_auto_cleanup: true
  cleanup_interval_hours: 24
  max_total_memories: 100000
  cleanup_batch_size: 1000
"""

    def _create_mpm_config(self) -> dict[str, Any]:
        """
        Create MPM (Model Package Manager) configuration.

        Returns:
            MPM configuration dict
        """
        kuzu_cmd = self._get_kuzu_memory_command_path()

        return {
            "version": "1.0",
            "memory": {
                "provider": "kuzu-memory",
                "auto_enhance": True,
                "async_learning": True,
                "project_root": str(self.project_root),
            },
            "hooks": {
                "pre_response": [f"{kuzu_cmd} enhance"],
                "post_response": [f"{kuzu_cmd} learn --quiet"],
            },
            "settings": {
                "max_context_size": 5,
                "similarity_threshold": 0.7,
                "temporal_decay": True,
            },
        }

    def _create_shell_wrapper(self) -> str:
        """
        Create shell wrapper script for kuzu-memory.

        Returns:
            Shell script content
        """
        kuzu_cmd = self._get_kuzu_memory_command_path()

        return f"""#!/bin/bash
# KuzuMemory wrapper for Claude integration

set -e

# Ensure we're in the project directory
cd "$(dirname "$0")/.."

# Execute kuzu-memory with all arguments
exec {kuzu_cmd} "$@"
"""

    def _detect_broken_mcp_installations(self) -> list[dict[str, Any]]:
        """
        Detect kuzu-memory MCP servers in broken location.

        Scans ~/.claude.json for MCP servers configured in the unsupported
        projects[path].mcpServers location. Claude Code ignores this location.

        Returns:
            List of broken installations with metadata:
            [
                {
                    "project_path": "/absolute/path",
                    "config": {"type": "stdio", "command": "...", ...},
                    "has_local_mcp_json": bool,
                    "project_exists": bool
                }
            ]
        """
        claude_json = Path.home() / ".claude.json"
        if not claude_json.exists():
            return []

        try:
            config = load_json_config(claude_json)
        except Exception as e:
            logger.warning(f"Failed to read ~/.claude.json: {e}")
            return []

        broken_installs: list[Any] = []

        for project_path, project_config in config.get("projects", {}).items():
            if not isinstance(project_config, dict):
                continue

            if "mcpServers" not in project_config:
                continue

            kuzu_config = project_config["mcpServers"].get("kuzu-memory")
            if not kuzu_config:
                continue

            project_dir = Path(project_path)
            mcp_json = project_dir / ".mcp.json"

            broken_installs.append(
                {
                    "project_path": project_path,
                    "config": kuzu_config,
                    "has_local_mcp_json": mcp_json.exists(),
                    "project_exists": project_dir.exists(),
                }
            )

        return broken_installs

    def _migrate_to_local_mcp_json(
        self,
        project_path: Path,
        kuzu_config: dict[str, Any],
        force: bool = False,
    ) -> tuple[bool, str]:
        """
        Migrate MCP config from ~/.claude.json to .mcp.json.

        Creates or updates the project-local .mcp.json file with the kuzu-memory
        MCP server configuration. Preserves any existing MCP servers in .mcp.json.

        Args:
            project_path: Absolute path to project directory
            kuzu_config: MCP server configuration to migrate
            force: If True, overwrite existing kuzu-memory in .mcp.json

        Returns:
            (success: bool, message: str)
        """
        mcp_json = project_path / ".mcp.json"

        # Load or create .mcp.json
        if mcp_json.exists():
            try:
                existing = load_json_config(mcp_json)
            except Exception as e:
                return False, f"Cannot read existing .mcp.json: {e}"

            # Check if kuzu-memory already exists
            if "kuzu-memory" in existing.get("mcpServers", {}):
                if not force:
                    return (
                        True,
                        "already configured",
                    )
        else:
            existing = {"mcpServers": {}}

        # Add/update kuzu-memory
        if "mcpServers" not in existing:
            existing["mcpServers"] = {}
        existing["mcpServers"]["kuzu-memory"] = kuzu_config

        # Write to .mcp.json
        try:
            save_json_config(mcp_json, existing, indent=2)
            return True, f"Migrated to {mcp_json.name}"
        except Exception as e:
            return False, f"Failed to write .mcp.json: {e}"

    def _cleanup_broken_configs(self, project_paths: list[str]) -> tuple[bool, str]:
        """
        Remove kuzu-memory from projects[path].mcpServers in ~/.claude.json.

        Creates a timestamped backup before modifying ~/.claude.json.
        Removes kuzu-memory entries from the unsupported location and cleans
        up empty structures.

        Args:
            project_paths: List of project paths to clean up (absolute path strings)

        Returns:
            (success: bool, message: str)
        """
        claude_json = Path.home() / ".claude.json"
        if not claude_json.exists():
            return True, "~/.claude.json does not exist"

        try:
            config = load_json_config(claude_json)
        except Exception as e:
            return False, f"Failed to read ~/.claude.json: {e}"

        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = claude_json.with_suffix(f".json.backup.{timestamp}")
        try:
            shutil.copy(claude_json, backup_path)
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            return False, f"Failed to create backup: {e}"

        # Remove kuzu-memory from each project
        modified = False
        for project_path in project_paths:
            if "projects" not in config or project_path not in config["projects"]:
                continue

            project_config = config["projects"][project_path]
            if not isinstance(project_config, dict):
                continue

            if "mcpServers" not in project_config:
                continue

            if "kuzu-memory" not in project_config["mcpServers"]:
                continue

            # Remove kuzu-memory
            del project_config["mcpServers"]["kuzu-memory"]
            modified = True

            # Clean up empty structures
            if not project_config["mcpServers"]:
                del project_config["mcpServers"]
            if not config["projects"][project_path]:
                del config["projects"][project_path]

        # Remove empty projects section
        if "projects" in config and not config["projects"]:
            del config["projects"]

        # Write updated config if modified
        if modified:
            try:
                save_json_config(claude_json, config, indent=2)
                return True, f"Cleaned up ~/.claude.json (backup: {backup_path.name})"
            except Exception as e:
                return False, f"Failed to write ~/.claude.json: {e}"
        else:
            return True, "No cleanup needed"

    def _migrate_broken_mcp_configs(self, force: bool = False) -> dict[str, Any]:
        """
        Migrate all broken MCP installations to .mcp.json.

        This is the main orchestration method that:
        1. Detects broken installations in ~/.claude.json
        2. Migrates each to project-local .mcp.json
        3. Cleans up broken entries from ~/.claude.json

        Args:
            force: If True, overwrite existing kuzu-memory in .mcp.json files

        Returns:
            Migration results dictionary:
            {
                "detected": int,
                "migrated": int,
                "failed": int,
                "skipped": int,
                "details": [...]
            }
        """
        broken = self._detect_broken_mcp_installations()
        results: dict[str, Any] = {
            "detected": len(broken),
            "migrated": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        if not broken:
            return results

        logger.info(f"🔧 Detected {len(broken)} broken MCP installation(s)")
        print("\n🔧 Migrating MCP configurations...")

        migrated_projects: list[Any] = []

        for install in broken:
            project_path = Path(install["project_path"])

            # Skip if project directory doesn't exist
            if not install["project_exists"]:
                results["skipped"] += 1
                results["details"].append(
                    {
                        "project": str(project_path),
                        "status": "skipped",
                        "reason": "Project directory does not exist",
                    }
                )
                logger.debug(f"Skipping {project_path.name}: directory not found")
                continue

            # Migrate to .mcp.json
            success, message = self._migrate_to_local_mcp_json(
                project_path,
                install["config"],
                force=force,
            )

            if success:
                if message == "already configured":
                    # Project already has kuzu-memory in .mcp.json - this is good!
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "project": str(project_path),
                            "status": "skipped",
                            "reason": "Already configured",
                        }
                    )
                    logger.debug(f"Skipped {project_path.name}: already configured")
                    print(f"  ✓ Already configured: {project_path.name}")
                else:
                    # Successfully migrated
                    results["migrated"] += 1
                    migrated_projects.append(install["project_path"])
                    results["details"].append(
                        {
                            "project": str(project_path),
                            "status": "success",
                            "message": message,
                        }
                    )
                    print(f"  ✓ Migrated {project_path.name} to local .mcp.json")
            else:
                results["failed"] += 1
                results["details"].append(
                    {
                        "project": str(project_path),
                        "status": "failed",
                        "reason": message,
                    }
                )
                logger.warning(f"Failed to migrate {project_path.name}: {message}")
                print(f"  ⚠ Failed to migrate {project_path.name}: {message}")

        # Clean up broken location for successfully migrated projects
        if migrated_projects:
            cleanup_success, cleanup_msg = self._cleanup_broken_configs(migrated_projects)
            if cleanup_success:
                logger.info(cleanup_msg)
                print(f"\n💾 {cleanup_msg}")
            else:
                logger.warning(f"Cleanup failed: {cleanup_msg}")
                print(f"\n⚠ Cleanup warning: {cleanup_msg}")

        # Print summary
        if results["migrated"] > 0:
            print(f"\n📦 Migration complete: {results['migrated']} project(s) migrated")
        if results["failed"] > 0:
            print(f"⚠ Failed to migrate {results['failed']} project(s)")

        # Count different types of skipped projects
        already_configured = sum(
            1
            for detail in results["details"]
            if detail["status"] == "skipped" and detail["reason"] == "Already configured"
        )
        dir_not_found = results["skipped"] - already_configured

        if already_configured > 0:
            print(f"Info: {already_configured} project(s) already configured")
        if dir_not_found > 0:
            print(f"⏭ Skipped {dir_not_found} project(s) (directory not found)")

        return results

    def _get_template_path(self, filename: str) -> Path:
        """Get path to hook template file."""
        template_dir = Path(__file__).parent / "templates" / "claude_hooks"
        return template_dir / filename

    def _load_template(self, filename: str) -> str:
        """
        Load hook template and replace placeholders.

        Args:
            filename: Name of the template file

        Returns:
            Template content with placeholders replaced

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = self._get_template_path(filename)
        if not template_path.exists():
            raise FileNotFoundError(f"Hook template not found: {template_path}")

        content = template_path.read_text()

        # Replace placeholders
        kuzu_cmd = self._get_kuzu_memory_command_path()
        content = content.replace("{KUZU_COMMAND}", str(kuzu_cmd))
        # The shebang replacement is handled by the template already having the correct shebang

        return content

    def install(
        self,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
        **kwargs: Any,
    ) -> InstallationResult:
        """
        Install Claude Code hooks for KuzuMemory.

        Automatically updates existing installations (no force flag needed).
        Previous versions are backed up before updating.

        Args:
            dry_run: If True, show what would be done without making changes
            verbose: If True, enable verbose output
            **kwargs: Additional arguments (for compatibility)

        Returns:
            InstallationResult with details of the installation
        """
        try:
            if dry_run:
                logger.info("DRY RUN MODE - No changes will be made")

            # Check prerequisites
            errors = self.check_prerequisites()
            if errors:
                raise InstallationError(f"Prerequisites not met: {'; '.join(errors)}")

            # Migrate broken MCP configurations BEFORE installing new config
            # This ensures all projects use the supported .mcp.json location
            if not dry_run:
                migration_results = self._migrate_broken_mcp_configs(force=force)
                if migration_results["detected"] > 0:
                    # Add migration info to warnings for reporting
                    if migration_results["migrated"] > 0:
                        self.warnings.append(
                            f"Migrated {migration_results['migrated']} project(s) from broken MCP location"
                        )
                    if migration_results["failed"] > 0:
                        self.warnings.append(
                            f"Failed to migrate {migration_results['failed']} project(s) - see logs for details"
                        )
            else:
                # In dry-run mode, just detect and report
                broken = self._detect_broken_mcp_installations()
                if broken:
                    print(f"\n🔧 Would migrate {len(broken)} broken MCP installation(s):")
                    for install in broken[:5]:  # Show first 5
                        project_path = Path(install["project_path"])
                        print(f"  - {project_path.name}")
                    if len(broken) > 5:
                        print(f"  ... and {len(broken) - 5} more")

            # Create or update CLAUDE.md (always update if exists)
            claude_md_path = self.project_root / "CLAUDE.md"
            if claude_md_path.exists():
                # Update existing file
                if not dry_run:
                    backup_path = self.create_backup(claude_md_path)
                    if backup_path:
                        self.backup_files.append(backup_path)
                self.files_modified.append(claude_md_path)
                logger.info(
                    f"{'Would update' if dry_run else 'Updating'} CLAUDE.md at {claude_md_path}"
                )
            else:
                # Create new file
                self.files_created.append(claude_md_path)
                logger.info(
                    f"{'Would create' if dry_run else 'Creating'} CLAUDE.md at {claude_md_path}"
                )

            if not dry_run:
                claude_md_path.write_text(self._create_claude_md())

            # Create .claude-mpm directory and config
            mpm_dir = self.project_root / ".claude-mpm"
            if not dry_run:
                mpm_dir.mkdir(exist_ok=True)

            mpm_config_path = mpm_dir / "config.json"
            if mpm_config_path.exists():
                if not dry_run:
                    backup_path = self.create_backup(mpm_config_path)
                    if backup_path:
                        self.backup_files.append(backup_path)
                self.files_modified.append(mpm_config_path)
            else:
                self.files_created.append(mpm_config_path)

            if not dry_run:
                with open(mpm_config_path, "w") as f:
                    json.dump(self._create_mpm_config(), f, indent=2)
            logger.info(
                f"{'Would create' if dry_run else 'Created'} MPM config at {mpm_config_path}"
            )

            # Create .claude directory for local config
            claude_dir = self.project_root / ".claude"
            if not dry_run:
                claude_dir.mkdir(exist_ok=True)

            # NOTE: Legacy hook scripts (kuzu_enhance.py, kuzu_learn.py) are no longer created.
            # The hooks configuration now calls CLI entry points directly:
            # - UserPromptSubmit: kuzu-memory hooks enhance
            # - PostToolUse: kuzu-memory hooks learn

            # Clean up legacy hook files from previous installations to prevent duplicate execution
            legacy_hook_files = [
                "kuzu_enhance.py",
                "kuzu_learn.py",
                "post_tool_use.py",
                "user_prompt_submit.py",
            ]
            hooks_dir = claude_dir / "hooks"
            if hooks_dir.exists():
                for hook_file in legacy_hook_files:
                    legacy_hook_path = hooks_dir / hook_file
                    if legacy_hook_path.exists():
                        if not dry_run:
                            backup_path = self.create_backup(legacy_hook_path)
                            if backup_path:
                                self.backup_files.append(backup_path)
                            legacy_hook_path.unlink()
                            logger.info(f"Removed legacy hook file: {hook_file}")
                        self.files_modified.append(legacy_hook_path)

            # NOTE: config.local.json is legacy and not used by Claude Code
            # We now merge MCP server config into settings.local.json instead
            # Clean up legacy config.local.json if it exists
            legacy_config_path = claude_dir / "config.local.json"
            if legacy_config_path.exists():
                if not dry_run:
                    backup_path = self.create_backup(legacy_config_path)
                    if backup_path:
                        self.backup_files.append(backup_path)
                    legacy_config_path.unlink()
                    logger.info(
                        "Removed legacy config.local.json (merged into settings.local.json)"
                    )
                    print(
                        "✓ Removed legacy .claude/config.local.json (config merged into settings.local.json)"
                    )
                self.files_modified.append(legacy_config_path)

            # Create or update settings.local.json with hooks AND MCP server config
            settings_path = claude_dir / "settings.local.json"
            existing_settings: dict[str, Any] = {}

            if settings_path.exists():
                try:
                    with open(settings_path) as f:
                        existing_settings = json.load(f)
                    if not dry_run:
                        backup_path = self.create_backup(settings_path)
                        if backup_path:
                            self.backup_files.append(backup_path)
                    self.files_modified.append(settings_path)
                    logger.info(
                        f"{'Would merge with' if dry_run else 'Merging with'} existing settings.local.json"
                    )
                except Exception as e:
                    logger.warning(f"Failed to read existing settings.local.json: {e}")
                    self.warnings.append(f"Could not read existing settings.local.json: {e}")
            else:
                self.files_created.append(settings_path)
                logger.info(
                    f"{'Would create' if dry_run else 'Creating'} settings.local.json at {settings_path}"
                )

            # Merge kuzu-memory hooks config with existing settings
            kuzu_hooks_config = self._create_claude_code_hooks_config()

            # Add version comment if creating new settings
            if not existing_settings and "_comment" in kuzu_hooks_config:
                existing_settings["_comment"] = kuzu_hooks_config["_comment"]

            # Remove old lowercase event names that are no longer valid
            OLD_EVENT_NAMES = {
                "user_prompt_submit",
                "assistant_response",
                "post_tool_use",
                "pre_tool_use",
                "session_start",
                "session_end",
            }

            # Merge hooks
            if "hooks" not in existing_settings:
                existing_settings["hooks"] = {}

            # Clean up old deprecated event names
            for old_event in OLD_EVENT_NAMES:
                if old_event in existing_settings["hooks"]:
                    logger.info(f"Removing deprecated hook event: {old_event}")
                    del existing_settings["hooks"][old_event]

            for hook_type, handlers in kuzu_hooks_config["hooks"].items():
                if hook_type not in existing_settings["hooks"]:
                    existing_settings["hooks"][hook_type] = []
                # Remove existing kuzu-memory handlers (both direct and script-based)
                existing_settings["hooks"][hook_type] = [
                    h for h in existing_settings["hooks"][hook_type] if not self._is_kuzu_hook(h)
                ]
                # Add new kuzu-memory handlers
                existing_settings["hooks"][hook_type].extend(handlers)

            # Validate hook events before writing
            self._validate_hook_events(existing_settings)

            # Write hooks configuration to settings.local.json
            # (MCP servers will be configured in ~/.claude.json separately)
            if not dry_run:
                with open(settings_path, "w") as f:
                    json.dump(existing_settings, f, indent=2)
            logger.info(
                f"{'Would configure' if dry_run else 'Configured'} Claude Code hooks in settings.local.json"
            )

            # Clean up legacy MCP server locations (before writing to correct location)
            if not dry_run:
                legacy_warnings = self._clean_legacy_mcp_locations()
                if legacy_warnings:
                    self.warnings.extend(legacy_warnings)

            # Update MCP server configuration in ~/.claude.json (correct location for Claude Code)
            if not dry_run:
                self._update_global_mcp_config()
            else:
                logger.info("Would update MCP server configuration in ~/.claude.json")
                print(
                    f"  Would add MCP server to: ~/.claude.json -> projects[{self.project_root}].mcpServers"
                )

            # Create or update .claude/mcp.local.json for project-level MCP configuration
            mcp_local_path = claude_dir / "mcp.local.json"
            if not dry_run:
                self._update_mcp_local_config(mcp_local_path)
            else:
                logger.info(f"Would create/update MCP config at {mcp_local_path}")
                print(f"  Would add MCP server to: {mcp_local_path}")

            # Create shell wrapper
            wrapper_path = claude_dir / "kuzu-memory.sh"
            if wrapper_path.exists():
                if not dry_run:
                    backup_path = self.create_backup(wrapper_path)
                    if backup_path:
                        self.backup_files.append(backup_path)
                self.files_modified.append(wrapper_path)
            else:
                self.files_created.append(wrapper_path)

            if not dry_run:
                wrapper_path.write_text(self._create_shell_wrapper())
                wrapper_path.chmod(0o755)  # Make executable

            # Note: Claude Desktop MCP server registration is not supported
            # This installer focuses on Claude Code hooks only
            if self.mcp_config_path and self.mcp_config_path.exists():
                logger.debug("Claude Desktop MCP server registration skipped (not supported)")
                self.warnings.append(
                    "Claude Desktop MCP integration not supported - using Claude Code hooks only"
                )

            # Create or update project-specific config.yaml
            config_path = self._get_project_config_path()
            config_dir = config_path.parent
            if not dry_run:
                config_dir.mkdir(parents=True, exist_ok=True)

            if config_path.exists():
                # Update existing config
                if not dry_run:
                    backup_path = self.create_backup(config_path)
                    if backup_path:
                        self.backup_files.append(backup_path)
                self.files_modified.append(config_path)
                logger.info(
                    f"{'Would update' if dry_run else 'Updating'} config.yaml at {config_path}"
                )
            else:
                # Create new config
                self.files_created.append(config_path)
                logger.info(
                    f"{'Would create' if dry_run else 'Creating'} config.yaml at {config_path}"
                )

            if not dry_run:
                config_path.write_text(self._create_project_config())

            # Initialize kuzu-memory database if not already done
            db_path = self._get_project_db_path()
            if not db_path.exists():
                try:
                    logger.info(
                        f"{'Would initialize' if dry_run else 'Initializing'} kuzu-memory database at {db_path}"
                    )
                    if not dry_run:
                        # Create database directory
                        db_path.mkdir(parents=True, exist_ok=True)

                        # Initialize database using Python API
                        from ..core.memory import KuzuMemory

                        memory = KuzuMemory(db_path=db_path / "memories.db")
                        memory.close()

                        logger.info(f"Initialized kuzu-memory database at {db_path}")
                    self.files_created.append(db_path / "memories.db")
                except Exception as e:
                    self.warnings.append(f"Failed to initialize kuzu-memory database: {e}")

            # Test the installation (skip in dry-run mode)
            if not dry_run:
                test_results = self._test_installation()
                if test_results:
                    self.warnings.extend(test_results)

            message = (
                "Claude Code hooks would be installed (dry-run)"
                if dry_run
                else "Claude Code hooks installed successfully"
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

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            raise InstallationError(f"Failed to install Claude hooks: {e}")

    def _test_installation(self) -> list[str]:
        """
        Test the installation and auto-repair any issues.

        Performs comprehensive verification of the Claude Code hooks installation:
        1. Tests kuzu-memory CLI availability and basic functionality
        2. Validates hooks configuration in settings.local.json
        3. Auto-repairs common configuration issues
        4. Tests that hook commands execute successfully with sample inputs

        This method is called automatically during installation to catch
        configuration errors early and provide actionable warnings.

        Returns:
            List of warning messages if any tests fail. Empty list if all tests pass.
        """
        warnings = []

        # Test 1: CLI availability
        try:
            result = subprocess.run(
                ["kuzu-memory", "status", "--format", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                warnings.append("kuzu-memory status command failed")
        except subprocess.SubprocessError as e:
            warnings.append(f"kuzu-memory test failed: {e}")

        # Test 2: Validate and repair configuration
        initial_warnings = self._validate_hooks_config()
        if initial_warnings:
            # Attempt auto-repair
            success, repair_messages = self._repair_hooks_config()
            if success:
                # Re-validate after repair
                remaining_warnings = self._validate_hooks_config()
                if not remaining_warnings:
                    # Repair succeeded - show what was fixed
                    for msg in repair_messages:
                        if "✓" in msg or "Updated" in msg or "Migrated" in msg:
                            logger.info(msg)
                else:
                    # Some issues remain after repair
                    warnings.extend(remaining_warnings)
            else:
                # Repair failed
                warnings.extend(initial_warnings)
                warnings.extend([f"Auto-repair: {msg}" for msg in repair_messages])

        # Test 3: Test hook commands
        hook_warnings = self._test_hook_commands()
        if hook_warnings:
            # Could add hook execution auto-repair here in future
            warnings.extend(hook_warnings)

        # MCP server testing skipped (Claude Desktop not supported)
        logger.debug("MCP server testing skipped (Claude Desktop not supported)")

        return warnings

    def _validate_hooks_config(self) -> list[str]:
        """
        Validate hooks configuration file.

        Checks settings.local.json for common configuration issues:
        - JSON syntax errors
        - Invalid hook event names (must be valid Claude Code events)
        - Missing or non-absolute command paths
        - Non-existent command executables

        This validation catches configuration errors before they cause
        runtime failures during Claude Code hook execution.

        Returns:
            List of warning messages for any configuration issues
        """
        warnings = []
        settings_path = self.project_root / ".claude" / "settings.local.json"

        if not settings_path.exists():
            warnings.append("settings.local.json not found")
            return warnings

        try:
            with open(settings_path) as f:
                config = json.load(f)

            hooks = config.get("hooks", {})
            for event_name in hooks.keys():
                if event_name not in VALID_CLAUDE_CODE_EVENTS:
                    warnings.append(f"Invalid hook event: {event_name}")

            # Validate command paths
            for _event_name, handlers in hooks.items():
                for handler_group in handlers:
                    for hook in handler_group.get("hooks", []):
                        command = hook.get("command", "")
                        if "kuzu" in command.lower():
                            cmd_parts = command.split()
                            cmd_path = cmd_parts[0] if cmd_parts else ""
                            if cmd_path and not Path(cmd_path).exists():
                                warnings.append(f"Hook command not found: {cmd_path}")
                            elif cmd_path and not cmd_path.startswith("/"):
                                warnings.append(f"Hook command path not absolute: {cmd_path}")

        except json.JSONDecodeError as e:
            warnings.append(f"Invalid JSON in settings.local.json: {e}")
        except Exception as e:
            warnings.append(f"Failed to validate hooks config: {e}")

        return warnings

    def _repair_hooks_config(self) -> tuple[bool, list[str]]:
        """
        Attempt to repair hooks configuration issues.

        Returns:
            (success: bool, messages: list[str]) - Whether repair succeeded and log messages
        """
        messages: list[Any] = []
        settings_path = self.project_root / ".claude" / "settings.local.json"

        if not settings_path.exists():
            messages.append("Settings file doesn't exist yet (will be created)")
            return True, messages

        try:
            # Read current config
            with open(settings_path) as f:
                config = json.load(f)

            # Create backup
            backup_path = settings_path.with_suffix(".json.backup")
            with open(backup_path, "w") as f:
                json.dump(config, f, indent=2)
            messages.append(f"Created backup: {backup_path.name}")

            # Apply fixes
            modified = False

            # Fix 1: Update command paths
            fixed_paths, path_messages = self._fix_command_paths(config)
            modified = modified or fixed_paths
            messages.extend(path_messages)

            # Fix 2: Migrate legacy event names
            fixed_events, event_messages = self._migrate_legacy_events(config)
            modified = modified or fixed_events
            messages.extend(event_messages)

            # Fix 3: Fix legacy command syntax
            fixed_syntax, syntax_messages = self._fix_legacy_command_syntax(config)
            modified = modified or fixed_syntax
            messages.extend(syntax_messages)

            # Write repaired config if modified
            if modified:
                with open(settings_path, "w") as f:
                    json.dump(config, f, indent=2)
                messages.append("✓ Configuration repaired successfully")
                return True, messages
            else:
                messages.append("Configuration is correct, no repairs needed")
                return True, messages

        except Exception as e:
            messages.append(f"Failed to repair config: {e}")
            return False, messages

    def _fix_command_paths(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Fix incorrect or relative command paths."""
        messages: list[Any] = []
        modified = False
        correct_path = self._get_kuzu_memory_command_path()

        hooks = config.get("hooks", {})
        for event_name, handlers in hooks.items():
            for handler_group in handlers:
                for hook in handler_group.get("hooks", []):
                    command = hook.get("command", "")
                    if "kuzu" in command.lower():
                        cmd_parts = command.split()
                        if cmd_parts:
                            old_path = cmd_parts[0]
                            # Check if path is wrong or relative
                            if old_path != correct_path or not old_path.startswith("/"):
                                # Update to correct path
                                cmd_parts[0] = correct_path
                                hook["command"] = " ".join(cmd_parts)
                                messages.append(f"Updated command path in {event_name}")
                                modified = True

        return modified, messages

    def _migrate_legacy_events(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Migrate legacy event names to current format."""
        messages: list[Any] = []
        modified = False

        # Event name migration map
        legacy_to_new = {
            "user_prompt_submit": "UserPromptSubmit",
            "post_tool_use": "PostToolUse",
            "session_start": "SessionStart",
            "stop": "Stop",
            "subagent_stop": "SubagentStop",
        }

        hooks = config.get("hooks", {})
        for old_name, new_name in legacy_to_new.items():
            if old_name in hooks:
                hooks[new_name] = hooks.pop(old_name)
                messages.append(f"Migrated event: {old_name} → {new_name}")
                modified = True

        # Remove invalid event names
        valid_events = VALID_CLAUDE_CODE_EVENTS
        invalid_events = [name for name in hooks.keys() if name not in valid_events]
        for invalid_name in invalid_events:
            hooks.pop(invalid_name)
            messages.append(f"Removed invalid event: {invalid_name}")
            modified = True

        return modified, messages

    def _fix_legacy_command_syntax(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Fix legacy command syntax (add 'hooks' subcommand)."""
        messages: list[Any] = []
        modified = False

        hooks = config.get("hooks", {})
        for _event_name, handlers in hooks.items():
            for handler_group in handlers:
                for hook in handler_group.get("hooks", []):
                    command = hook.get("command", "")

                    # Check for legacy syntax patterns
                    legacy_patterns = [
                        ("kuzu-memory enhance", "kuzu-memory hooks enhance"),
                        ("kuzu-memory learn", "kuzu-memory hooks learn"),
                        (
                            "kuzu-memory session-start",
                            "kuzu-memory hooks session-start",
                        ),
                    ]

                    for old_pattern, new_pattern in legacy_patterns:
                        if old_pattern in command and "hooks" not in command:
                            hook["command"] = command.replace(old_pattern, new_pattern)
                            messages.append(f"Updated syntax: {old_pattern} → {new_pattern}")
                            modified = True

        return modified, messages

    def _test_hook_commands(self) -> list[str]:
        """
        Test that hook commands execute successfully.

        Executes each hook command with sample test inputs to verify:
        - Commands are executable and accessible
        - Commands accept JSON input via stdin
        - Commands complete within timeout (5 seconds)
        - Commands exit with code 0 (success)

        Tested hooks:
        - session-start: Tests SessionStart hook handler
        - enhance: Tests UserPromptSubmit enhancement hook
        - learn: Tests PostToolUse learning hook

        Returns:
            List of warning messages for any hook execution failures
        """
        warnings = []

        # Get kuzu-memory command path
        kuzu_cmd = self._get_kuzu_memory_command_path()

        # Define hook tests
        hook_tests = [
            ("session-start", {"hook_event_name": "SessionStart"}),
            ("enhance", {"prompt": "test prompt"}),
            ("learn", {"content": "test learning content"}),
        ]

        for hook_name, test_input in hook_tests:
            try:
                result = self._run_hook_test(f"{kuzu_cmd} hooks {hook_name}", test_input)
                if result.returncode != 0:
                    stderr_preview = result.stderr[:100] if result.stderr else "no stderr"
                    warnings.append(
                        f"Hook 'hooks {hook_name}' failed with exit code "
                        f"{result.returncode}: {stderr_preview}"
                    )
            except subprocess.TimeoutExpired:
                warnings.append(f"Hook 'hooks {hook_name}' timed out after 5 seconds")
            except Exception as e:
                warnings.append(f"Hook 'hooks {hook_name}' test failed: {e}")

        return warnings

    def _run_hook_test(
        self, hook_cmd: str, test_input: dict[str, Any]
    ) -> subprocess.CompletedProcess[str]:
        """
        Run a single hook command test.

        Args:
            hook_cmd: Full command to execute (space-separated string)
            test_input: Dictionary to send as JSON input via stdin

        Returns:
            CompletedProcess result from subprocess.run
        """
        return subprocess.run(
            hook_cmd.split(),
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(self.project_root),
        )

    def uninstall(self, **kwargs: Any) -> InstallationResult:
        """
        Uninstall Claude Code hooks.

        Args:
            **kwargs: Additional arguments (for compatibility)

        Returns:
            InstallationResult with details of the uninstallation
        """
        try:
            removed_files: list[Any] = []

            # Remove CLAUDE.md if it was created by us
            claude_md_path = self.project_root / "CLAUDE.md"
            if claude_md_path.exists():
                content = claude_md_path.read_text()
                if "KuzuMemory Claude Hooks Installer" in content:
                    claude_md_path.unlink()
                    removed_files.append(claude_md_path)

            # Remove .claude-mpm directory
            mpm_dir = self.project_root / ".claude-mpm"
            if mpm_dir.exists():
                shutil.rmtree(mpm_dir)
                removed_files.append(mpm_dir)

            # Remove .claude directory
            claude_dir = self.project_root / ".claude"
            if claude_dir.exists():
                shutil.rmtree(claude_dir)
                removed_files.append(claude_dir)

            # Remove MCP server configuration from ~/.claude.json
            global_config_path = Path.home() / ".claude.json"
            if global_config_path.exists():
                try:
                    with open(global_config_path) as f:
                        config = json.load(f)

                    project_key = str(self.project_root.resolve())
                    if "projects" in config and project_key in config["projects"]:
                        project_config = config["projects"][project_key]
                        if (
                            "mcpServers" in project_config
                            and "kuzu-memory" in project_config["mcpServers"]
                        ):
                            # Backup before modifying
                            backup_path = global_config_path.with_suffix(".json.backup")
                            shutil.copy(global_config_path, backup_path)

                            # Remove kuzu-memory MCP server
                            del project_config["mcpServers"]["kuzu-memory"]

                            # Clean up empty structures
                            if not project_config["mcpServers"]:
                                del project_config["mcpServers"]
                            if not config["projects"][project_key]:
                                del config["projects"][project_key]

                            # Write updated config
                            with open(global_config_path, "w") as f:
                                json.dump(config, f, indent=2)

                            logger.info(
                                f"Removed MCP server from ~/.claude.json for project: {self.project_root.name}"
                            )
                except Exception as e:
                    logger.warning(f"Failed to remove MCP config from ~/.claude.json: {e}")
                    self.warnings.append(f"Could not remove MCP config from global file: {e}")

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=self.files_modified,
                backup_files=[],
                message="Claude Code hooks uninstalled successfully",
                warnings=self.warnings,
            )

        except Exception as e:
            logger.error(f"Uninstallation failed: {e}")
            raise InstallationError(f"Failed to uninstall Claude hooks: {e}")

    def status(self) -> dict[str, Any]:
        """
        Check the status of Claude hooks installation.

        Returns:
            Status information dictionary
        """
        status: dict[str, Any] = {
            "installed": False,
            "claude_desktop_detected": self.claude_config_dir is not None,
            "files": {},
            "mcp_configured": False,
            "kuzu_initialized": False,
            "config_exists": False,
        }

        # Check files
        claude_md = self.project_root / "CLAUDE.md"
        status["files"]["CLAUDE.md"] = claude_md.exists()

        mpm_config = self.project_root / ".claude-mpm" / "config.json"
        status["files"]["mpm_config"] = mpm_config.exists()

        settings_config = self.project_root / ".claude" / "settings.local.json"
        status["files"]["settings.local.json"] = settings_config.exists()

        config_file = self._get_project_config_path()
        status["files"]["config_yaml"] = config_file.exists()
        status["config_exists"] = config_file.exists()

        # Check if installed
        status["installed"] = all(
            [
                status["files"]["CLAUDE.md"],
                status["files"]["mpm_config"],
                status["files"]["settings.local.json"],
                status["files"]["config_yaml"],
            ]
        )

        # Check if MCP server is configured in ~/.claude.json (correct location)
        status["mcp_configured"] = self._check_mcp_configured()

        # Warn if MCP config is in legacy location (settings.local.json)
        if settings_config.exists():
            try:
                with open(settings_config) as f:
                    settings = json.load(f)
                    if "mcpServers" in settings and "kuzu-memory" in settings["mcpServers"]:
                        status["legacy_mcp_location"] = True
                        logger.warning(
                            "MCP config found in legacy location (settings.local.json). "
                            "Run 'kuzu-memory install claude-code --force' to migrate."
                        )
            except Exception:
                pass

        # Check kuzu initialization (project-specific path)
        db_path = self._get_project_db_path() / "memories.db"
        status["kuzu_initialized"] = db_path.exists()
        status["database_path"] = str(db_path)

        return status

    def _check_mcp_configured(self) -> bool:
        """
        Check if MCP server is configured in ~/.claude.json.

        Returns:
            True if MCP is configured, False otherwise
        """
        global_config_path = Path.home() / ".claude.json"
        if not global_config_path.exists():
            return False

        try:
            with open(global_config_path) as f:
                config = json.load(f)
            project_key = str(self.project_root.resolve())
            return (
                "projects" in config
                and project_key in config["projects"]
                and "mcpServers" in config["projects"][project_key]
                and "kuzu-memory" in config["projects"][project_key]["mcpServers"]
            )
        except Exception:
            return False
