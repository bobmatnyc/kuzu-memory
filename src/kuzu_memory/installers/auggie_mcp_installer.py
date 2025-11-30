"""
Auggie MCP installer for KuzuMemory.

Installs MCP server configuration for Auggie (global configuration).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base import BaseInstaller, InstallationResult
from .json_utils import (
    create_mcp_server_config,
    expand_variables,
    fix_broken_mcp_args,
    get_standard_variables,
    load_json_config,
    merge_json_configs,
    save_json_config,
    validate_mcp_config,
)

logger = logging.getLogger(__name__)


class AuggieMCPInstaller(BaseInstaller):
    """
    Installer for Auggie MCP integration.

    Creates ~/.augment/settings.json configuration with KuzuMemory MCP server.
    Preserves existing MCP servers in the configuration.

    Note: Auggie uses a global configuration file, not project-specific.
    """

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system this installer supports."""
        return "Auggie (MCP)"

    @property
    def required_files(self) -> list[str]:
        """List of files that will be created/modified by this installer."""
        # Global config, not in project directory
        return []

    @property
    def description(self) -> str:
        """Description of what this installer does."""
        return "Install MCP server configuration for Auggie (global: ~/.augment/settings.json)"

    def _get_config_path(self) -> Path:
        """Get path to Auggie settings configuration file."""
        return Path.home() / ".augment" / "settings.json"

    def _create_kuzu_server_config(self) -> dict[str, Any]:
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

        # Check if .augment directory exists, create if not
        config_path = self._get_config_path()
        augment_dir = config_path.parent

        if not augment_dir.exists():
            try:
                augment_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created Auggie config directory: {augment_dir}")
            except Exception as e:
                errors.append(f"Cannot create Auggie config directory {augment_dir}: {e}")

        return errors

    def install(
        self, force: bool = False, dry_run: bool = False, **kwargs: Any
    ) -> InstallationResult:
        """
        Install MCP configuration for Auggie.

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

            # Load existing configuration
            existing_config = load_json_config(config_path) if config_path.exists() else {}

            # Auto-fix broken MCP configurations
            existing_config, fixes = fix_broken_mcp_args(existing_config)
            if fixes:
                logger.info(f"Auto-fixed {len(fixes)} broken MCP configuration(s)")
                for fix in fixes:
                    logger.debug(fix)

            # Create KuzuMemory server config
            kuzu_config = self._create_kuzu_server_config()

            # Expand variables
            variables = get_standard_variables(self.project_root)
            kuzu_config = expand_variables(kuzu_config, variables)

            # Check if kuzu-memory is already configured
            existing_servers = existing_config.get("mcpServers", {})
            kuzu_already_exists = "kuzu-memory" in existing_servers

            if kuzu_already_exists and not force:
                # Check if configuration is the same
                existing_kuzu = existing_servers["kuzu-memory"]
                new_kuzu = kuzu_config["mcpServers"]["kuzu-memory"]

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
                if force and existing_config:
                    self.warnings.append("Force mode: existing configuration will be backed up")

            # Validate merged configuration
            validation_errors = validate_mcp_config(merged_config)
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

            # Dry run mode - just report what would happen
            if dry_run:
                message = f"[DRY RUN] Would install MCP configuration to {config_path}"
                if config_path.exists():
                    message += f"\nWould preserve {len(existing_config.get('mcpServers', {}))} existing server(s)"
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

            # Track whether file existed before
            file_existed = config_path.exists()

            # Create backup if file exists
            if file_existed:
                backup_path = self.create_backup(config_path)
                if backup_path:
                    if verbose:
                        logger.info(f"Created backup: {backup_path}")
                self.files_modified.append(config_path)
            else:
                self.files_created.append(config_path)

            # Save merged configuration
            save_json_config(config_path, merged_config)

            # Success message
            server_count = len(merged_config.get("mcpServers", {}))
            message = f"Successfully installed MCP configuration for {self.ai_system_name}"
            message += f"\nConfiguration file: {config_path}"
            message += f"\nMCP servers configured: {server_count}"
            message += f"\nProject: {self.project_root}"

            if existing_config:
                preserved_count = len(existing_config.get("mcpServers", {}))
                if preserved_count > 0 and not force:
                    message += f"\nPreserved {preserved_count} existing server(s)"

            # Add note about global configuration
            self.warnings.append(
                "Note: Auggie uses a global configuration file. "
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
