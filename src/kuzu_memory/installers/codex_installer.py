"""
Codex installer for KuzuMemory.

Installs MCP server configuration for Codex (global configuration).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base import BaseInstaller, InstallationResult
from .json_utils import expand_variables, get_standard_variables
from .toml_utils import (
    TOMLConfigError,
    load_toml_config,
    merge_toml_configs,
    save_toml_config,
    validate_toml_mcp_config,
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

    def _create_kuzu_server_config(self) -> dict[str, Any]:
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
                    },
                }
            }
        }

    def check_prerequisites(self) -> list[str]:
        """
        Check if prerequisites are met for installation.

        Returns:
            List of error messages, empty if all prerequisites are met
        """
        errors: list[Any] = []

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
        self, force: bool = False, dry_run: bool = False, **kwargs: Any
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
                        "KuzuMemory server exists with different configuration. "
                        "Use --force to update."
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
                    message += (
                        f"\nWould preserve {len(existing_config.get('mcp_servers', {}))} "
                        f"existing server(s)"
                    )
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
