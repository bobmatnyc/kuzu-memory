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
from pathlib import Path
from typing import Any

from .base import BaseInstaller, InstallationError, InstallationResult

logger = logging.getLogger(__name__)


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
        self._kuzu_command_path = None  # Cache for kuzu-memory command path

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
            ".claude/config.local.json",
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

        Uses shutil.which() to find the exact executable that will be invoked,
        supporting all installation methods (local, source, pip, pipx, etc.).

        Priority order:
        1. pipx installation (supports MCP server)
        2. Local development installation (supports MCP server)
        3. System-wide installation (may not support MCP server)

        Returns:
            Full path to kuzu-memory executable, or 'kuzu-memory' if not found
        """
        if self._kuzu_command_path is not None:
            return self._kuzu_command_path

        # Priority 1: Check for pipx installation (most reliable for MCP server)
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

        # Priority 2: Check for local development installation
        dev_paths = [
            self.project_root / "venv" / "bin" / "kuzu-memory",
            self.project_root / ".venv" / "bin" / "kuzu-memory",
        ]

        for dev_path in dev_paths:
            if dev_path.exists() and self._verify_mcp_support(dev_path):
                self._kuzu_command_path = str(dev_path)
                logger.info(f"Using development installation at: {dev_path}")
                return str(dev_path)

        # Priority 3: Use shutil.which to find any kuzu-memory in PATH
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

    def _create_claude_code_config(self) -> dict[str, Any]:
        """
        Create Claude Code configuration with hooks and MCP server.

        Returns:
            Claude Code configuration dict with hooks and MCP server
        """
        db_path = self._get_project_db_path()
        kuzu_cmd = self._get_kuzu_memory_command_path()

        config = {
            "hooks": {
                "user_prompt_submit": [
                    {
                        "handler": "kuzu_memory_enhance",
                        "command": f'{kuzu_cmd} memory enhance "{{{{prompt}}}}"',
                        "enabled": True,
                    }
                ],
                "assistant_response": [
                    {
                        "handler": "kuzu_memory_learn",
                        "command": f'{kuzu_cmd} memory learn "{{{{response}}}}" --quiet',
                        "enabled": True,
                    }
                ],
            },
            "mcpServers": {
                "kuzu-memory": {
                    "command": kuzu_cmd,
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
        info = {
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

    def install(
        self, force: bool = False, dry_run: bool = False, verbose: bool = False
    ) -> InstallationResult:
        """
        Install Claude Code hooks for KuzuMemory.

        Args:
            force: If True, overwrite existing files
            dry_run: If True, show what would be done without making changes
            verbose: If True, enable verbose output

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

            # Create CLAUDE.md only if it doesn't exist (or force is True)
            claude_md_path = self.project_root / "CLAUDE.md"
            if claude_md_path.exists() and not force:
                logger.info(
                    f"CLAUDE.md already exists at {claude_md_path}, skipping creation"
                )
                self.warnings.append(
                    "CLAUDE.md already exists, preserved existing file (use --force to overwrite)"
                )
            else:
                if claude_md_path.exists() and force:
                    if not dry_run:
                        backup_path = self.create_backup(claude_md_path)
                        if backup_path:
                            self.backup_files.append(backup_path)
                    self.files_modified.append(claude_md_path)
                    logger.info(
                        f"{'Would overwrite' if dry_run else 'Overwriting'} CLAUDE.md at {claude_md_path} (forced)"
                    )
                else:
                    self.files_created.append(claude_md_path)
                    logger.info(
                        f"{'Would create' if dry_run else 'Created'} CLAUDE.md at {claude_md_path}"
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

            # Create or update config.local.json with hooks and MCP server
            local_config_path = claude_dir / "config.local.json"
            existing_config = {}

            if local_config_path.exists():
                try:
                    with open(local_config_path) as f:
                        existing_config = json.load(f)
                    if not dry_run:
                        backup_path = self.create_backup(local_config_path)
                        if backup_path:
                            self.backup_files.append(backup_path)
                    self.files_modified.append(local_config_path)
                    logger.info(
                        f"{'Would merge with' if dry_run else 'Merging with'} existing config.local.json"
                    )
                except Exception as e:
                    logger.warning(f"Failed to read existing config.local.json: {e}")
                    self.warnings.append(
                        f"Could not read existing config.local.json: {e}"
                    )
            else:
                self.files_created.append(local_config_path)
                logger.info(
                    f"{'Would create' if dry_run else 'Creating'} config.local.json at {local_config_path}"
                )

            # Merge kuzu-memory config with existing config
            kuzu_config = self._create_claude_code_config()

            # Merge hooks
            if "hooks" not in existing_config:
                existing_config["hooks"] = {}
            for hook_type, handlers in kuzu_config["hooks"].items():
                if hook_type not in existing_config["hooks"]:
                    existing_config["hooks"][hook_type] = []
                # Remove existing kuzu-memory handlers
                existing_config["hooks"][hook_type] = [
                    h
                    for h in existing_config["hooks"][hook_type]
                    if "kuzu_memory" not in h.get("handler", "")
                ]
                # Add new kuzu-memory handlers
                existing_config["hooks"][hook_type].extend(handlers)

            # Merge MCP servers
            if "mcpServers" not in existing_config:
                existing_config["mcpServers"] = {}
            existing_config["mcpServers"]["kuzu-memory"] = kuzu_config["mcpServers"][
                "kuzu-memory"
            ]

            if not dry_run:
                with open(local_config_path, "w") as f:
                    json.dump(existing_config, f, indent=2)
            logger.info(
                f"{'Would configure' if dry_run else 'Configured'} Claude Code hooks and MCP server in config.local.json"
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

            # Create project-specific config.yaml
            config_path = self._get_project_config_path()
            config_dir = config_path.parent
            if not dry_run:
                config_dir.mkdir(parents=True, exist_ok=True)

            if config_path.exists() and not force:
                logger.info(
                    f"Config file already exists at {config_path}, skipping creation"
                )
                self.warnings.append(
                    "config.yaml already exists, preserved existing file (use --force to overwrite)"
                )
            else:
                if config_path.exists() and force:
                    if not dry_run:
                        backup_path = self.create_backup(config_path)
                        if backup_path:
                            self.backup_files.append(backup_path)
                    self.files_modified.append(config_path)
                    logger.info(
                        f"{'Would overwrite' if dry_run else 'Overwriting'} config.yaml at {config_path} (forced)"
                    )
                else:
                    self.files_created.append(config_path)
                    logger.info(
                        f"{'Would create' if dry_run else 'Created'} config.yaml at {config_path}"
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

    def uninstall(self) -> InstallationResult:
        """
        Uninstall Claude Code hooks.

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

            # Claude Desktop MCP server registration not supported, nothing to remove
            if self.mcp_config_path and self.mcp_config_path.exists():
                logger.debug(
                    "Claude Desktop MCP server removal skipped (not supported)"
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
        status = {
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

        local_config = self.project_root / ".claude" / "config.local.json"
        status["files"]["config.local.json"] = local_config.exists()

        config_file = self._get_project_config_path()
        status["files"]["config_yaml"] = config_file.exists()
        status["config_exists"] = config_file.exists()

        # Check if installed
        status["installed"] = all(
            [
                status["files"]["CLAUDE.md"],
                status["files"]["mpm_config"],
                status["files"]["config.local.json"],
                status["files"]["config_yaml"],
            ]
        )

        # Check MCP configuration
        if self.mcp_config_path and self.mcp_config_path.exists():
            try:
                with open(self.mcp_config_path) as f:
                    global_config = json.load(f)
                project_key = f"kuzu-memory-{self.project_root.name}"
                status["mcp_configured"] = project_key in global_config.get(
                    "mcpServers", {}
                )
            except Exception:
                pass

        # Check kuzu initialization (project-specific path)
        db_path = self._get_project_db_path() / "memories.db"
        status["kuzu_initialized"] = db_path.exists()
        status["database_path"] = str(db_path)

        return status
