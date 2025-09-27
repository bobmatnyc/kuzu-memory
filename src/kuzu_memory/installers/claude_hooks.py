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
            ".claude/kuzu-memory-mcp.json",
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

    def _create_mcp_server_config(self) -> dict[str, Any]:
        """
        Create MCP server configuration for kuzu-memory.

        Returns:
            MCP server configuration dict
        """
        config = {
            "mcpServers": {
                "kuzu-memory": {
                    "command": "python",
                    "args": ["-m", "kuzu_memory.integrations.mcp_server"],
                    "env": {
                        "KUZU_MEMORY_PROJECT": str(self.project_root),
                        "KUZU_MEMORY_MODE": "mcp",
                    },
                }
            }
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

    def _create_mpm_config(self) -> dict[str, Any]:
        """
        Create MPM (Model Package Manager) configuration.

        Returns:
            MPM configuration dict
        """
        return {
            "version": "1.0",
            "memory": {
                "provider": "kuzu-memory",
                "auto_enhance": True,
                "async_learning": True,
                "project_root": str(self.project_root),
            },
            "hooks": {
                "pre_response": ["kuzu-memory enhance"],
                "post_response": ["kuzu-memory learn --quiet"],
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
        return """#!/bin/bash
# KuzuMemory wrapper for Claude integration

set -e

# Ensure we're in the project directory
cd "$(dirname "$0")/.."

# Execute kuzu-memory with all arguments
exec kuzu-memory "$@"
"""

    def install(self, force: bool = False) -> InstallationResult:
        """
        Install Claude Code hooks for KuzuMemory.

        Args:
            force: If True, overwrite existing files

        Returns:
            InstallationResult with details of the installation
        """
        try:
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
                    backup_path = self.create_backup(claude_md_path)
                    if backup_path:
                        self.backup_files.append(backup_path)
                    self.files_modified.append(claude_md_path)
                    logger.info(f"Overwriting CLAUDE.md at {claude_md_path} (forced)")
                else:
                    self.files_created.append(claude_md_path)
                    logger.info(f"Created CLAUDE.md at {claude_md_path}")
                claude_md_path.write_text(self._create_claude_md())

            # Create .claude-mpm directory and config
            mpm_dir = self.project_root / ".claude-mpm"
            mpm_dir.mkdir(exist_ok=True)

            mpm_config_path = mpm_dir / "config.json"
            if mpm_config_path.exists():
                backup_path = self.create_backup(mpm_config_path)
                if backup_path:
                    self.backup_files.append(backup_path)
                    self.files_modified.append(mpm_config_path)
            else:
                self.files_created.append(mpm_config_path)

            with open(mpm_config_path, "w") as f:
                json.dump(self._create_mpm_config(), f, indent=2)
            logger.info(f"Created MPM config at {mpm_config_path}")

            # Create .claude directory for local MCP config
            claude_dir = self.project_root / ".claude"
            claude_dir.mkdir(exist_ok=True)

            local_mcp_config = claude_dir / "kuzu-memory-mcp.json"
            with open(local_mcp_config, "w") as f:
                json.dump(self._create_mcp_server_config(), f, indent=2)
            self.files_created.append(local_mcp_config)
            logger.info(f"Created local MCP config at {local_mcp_config}")

            # Create shell wrapper
            wrapper_path = claude_dir / "kuzu-memory.sh"
            wrapper_path.write_text(self._create_shell_wrapper())
            wrapper_path.chmod(0o755)  # Make executable
            self.files_created.append(wrapper_path)

            # Note: Claude Desktop MCP server registration is not supported
            # This installer focuses on Claude Code hooks only
            if self.mcp_config_path and self.mcp_config_path.exists():
                logger.debug(
                    "Claude Desktop MCP server registration skipped (not supported)"
                )
                self.warnings.append(
                    "Claude Desktop MCP integration not supported - using Claude Code hooks only"
                )

            # Initialize kuzu-memory if not already done
            db_path = self.project_root / "kuzu-memories" / "kuzu_memory.db"
            if not db_path.exists():
                try:
                    subprocess.run(
                        ["kuzu-memory", "init"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    logger.info("Initialized kuzu-memory database")
                except subprocess.SubprocessError as e:
                    self.warnings.append(f"Failed to initialize kuzu-memory: {e}")

            # Test the installation
            test_results = self._test_installation()
            if test_results:
                self.warnings.extend(test_results)

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message="Claude Code hooks installed successfully",
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
                ["kuzu-memory", "stats", "--format", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                warnings.append("kuzu-memory stats command failed")
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
        }

        # Check files
        claude_md = self.project_root / "CLAUDE.md"
        status["files"]["CLAUDE.md"] = claude_md.exists()

        mpm_config = self.project_root / ".claude-mpm" / "config.json"
        status["files"]["mpm_config"] = mpm_config.exists()

        local_mcp = self.project_root / ".claude" / "kuzu-memory-mcp.json"
        status["files"]["local_mcp"] = local_mcp.exists()

        # Check if installed
        status["installed"] = all(
            [status["files"]["CLAUDE.md"], status["files"]["mpm_config"]]
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

        # Check kuzu initialization
        db_path = self.project_root / "kuzu-memories" / "kuzu_memory.db"
        status["kuzu_initialized"] = db_path.exists()

        return status
