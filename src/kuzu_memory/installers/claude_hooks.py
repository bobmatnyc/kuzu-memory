"""
Claude Code hooks installer for KuzuMemory.

Provides seamless integration with Claude Desktop through MCP (Model Context Protocol)
and project-specific hooks for intelligent memory enhancement.
"""

import json
import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .base import BaseInstaller, InstallationError, InstallationResult
from .json_utils import fix_broken_mcp_args

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

    def __init__(self, project_root: Path):
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
                if "mcpServers" in config and "kuzu-memory" in config.get(
                    "mcpServers", {}
                ):
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

                if "mcpServers" in settings and "kuzu-memory" in settings.get(
                    "mcpServers", {}
                ):
                    del settings["mcpServers"]["kuzu-memory"]
                    if not settings["mcpServers"]:
                        del settings["mcpServers"]

                    with open(local_settings, "w") as f:
                        json.dump(settings, f, indent=2)

                    warnings.append(
                        "Moved MCP config from settings.local.json to ~/.claude.json"
                    )
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
            logger.info(
                "Claude Desktop not detected - will create local configuration only"
            )

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

        if installer_kuzu_path.exists() and self._verify_mcp_support(
            installer_kuzu_path
        ):
            self._kuzu_command_path = str(installer_kuzu_path)
            logger.info(
                f"Using kuzu-memory from installer environment at: {installer_kuzu_path}"
            )
            return str(installer_kuzu_path)

        # Priority 2: Check for pipx installation (most reliable for MCP server)
        pipx_paths = [
            Path.home()
            / ".local"
            / "pipx"
            / "venvs"
            / "kuzu-memory"
            / "bin"
            / "kuzu-memory",
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
                    logger.info(
                        f"Found kuzu-memory with MCP support at: {command_path}"
                    )
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

    def _validate_hook_events(self, config: dict) -> None:
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
        **kwargs,
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
            existing_settings = {}

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
                    self.warnings.append(
                        f"Could not read existing settings.local.json: {e}"
                    )
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
                    h
                    for h in existing_settings["hooks"][hook_type]
                    if not self._is_kuzu_hook(h)
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
                logger.debug(
                    "Claude Desktop MCP server registration skipped (not supported)"
                )
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
                    self.warnings.append(
                        f"Failed to initialize kuzu-memory database: {e}"
                    )

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
        Test the installation to ensure everything works.

        Returns:
            List of warning messages if any tests fail
        """
        warnings = []

        # Test kuzu-memory CLI
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

        # MCP server testing skipped (Claude Desktop not supported)
        logger.debug("MCP server testing skipped (Claude Desktop not supported)")

        return warnings

    def uninstall(self, **kwargs) -> InstallationResult:
        """
        Uninstall Claude Code hooks.

        Args:
            **kwargs: Additional arguments (for compatibility)

        Returns:
            InstallationResult with details of the uninstallation
        """
        try:
            removed_files = []

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
                    logger.warning(
                        f"Failed to remove MCP config from ~/.claude.json: {e}"
                    )
                    self.warnings.append(
                        f"Could not remove MCP config from global file: {e}"
                    )

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
                    if (
                        "mcpServers" in settings
                        and "kuzu-memory" in settings["mcpServers"]
                    ):
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
