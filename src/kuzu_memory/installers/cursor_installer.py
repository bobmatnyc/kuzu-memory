"""
Cursor IDE MCP installer for KuzuMemory.

Installs MCP server configuration for Cursor IDE.
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


class CursorInstaller(BaseInstaller):
    """
    Installer for Cursor IDE MCP integration.

    Creates .cursor/mcp.json configuration file with KuzuMemory MCP server.
    Preserves existing MCP servers in the configuration.
    """

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system this installer supports."""
        return "Cursor IDE"

    @property
    def required_files(self) -> list[str]:
        """List of files that will be created/modified by this installer."""
        return [".cursor/mcp.json"]

    @property
    def description(self) -> str:
        """Description of what this installer does."""
        return "Install MCP server configuration for Cursor IDE (project-specific)"

    def _get_config_path(self) -> Path:
        """Get path to Cursor MCP configuration file."""
        return self.project_root / ".cursor" / "mcp.json"

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

    def install(
        self, force: bool = False, dry_run: bool = False, **kwargs: Any
    ) -> InstallationResult:
        """
        Install MCP configuration for Cursor IDE.

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

            if existing_config:
                preserved_count = len(existing_config.get("mcpServers", {}))
                if preserved_count > 0:
                    message += f"\nPreserved {preserved_count} existing server(s)"

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
