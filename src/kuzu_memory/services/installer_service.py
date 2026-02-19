"""InstallerService implementation - integration installer management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kuzu_memory.installers.base import BaseInstaller
from kuzu_memory.installers.json_utils import (
    fix_broken_mcp_args,
    load_json_config,
    save_json_config,
)
from kuzu_memory.installers.registry import InstallerRegistry
from kuzu_memory.protocols.services import IConfigService
from kuzu_memory.services.base import BaseService


class InstallerService(BaseService):
    """
    Service layer for installer management.

    Orchestrates installation, uninstallation, and health checking
    of AI integrations (Claude Code, Cursor, VS Code, etc.).

    Design Pattern: Service Orchestrator
    - Owns InstallerRegistry instance
    - Delegates to BaseInstaller implementations
    - Integrates with ConfigService for project context
    - Provides unified installer operations

    Design Decision: Dependency Injection for ConfigService
    --------------------------------------------------------
    Rationale: InstallerService depends on IConfigService (protocol)
    rather than concrete ConfigService. This enables:
    - Testing with mock config services
    - Flexibility to swap implementations
    - Clear dependency declaration

    Trade-offs:
    - Flexibility: Can inject any IConfigService implementation
    - Testability: Easy to mock config for unit tests
    - Complexity: Requires DI container or manual wiring
    - Type Safety: Protocol ensures interface compatibility

    Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
    Related Task: 1M-422 (Implement InstallerService)
    """

    def __init__(self, config_service: IConfigService):
        """
        Initialize InstallerService.

        Args:
            config_service: Configuration service for project context
        """
        super().__init__()
        self._config_service = config_service
        self._registry: InstallerRegistry | None = None

    def _do_initialize(self) -> None:
        """Initialize installer registry."""
        self._registry = InstallerRegistry()
        self.logger.info("InstallerService initialized with registry")

    def _do_cleanup(self) -> None:
        """Cleanup resources."""
        self._registry = None
        self.logger.info("InstallerService cleaned up")

    @property
    def registry(self) -> InstallerRegistry:
        """
        Get installer registry.

        Returns:
            InstallerRegistry instance

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._registry:
            raise RuntimeError("InstallerService not initialized")
        return self._registry

    # IInstallerService protocol implementation

    def discover_installers(self) -> list[str]:
        """
        Discover available installers.

        Returns:
            List of installer names (e.g., ["claude-code", "cursor", "vscode"])

        Example:
            >>> installer_service.discover_installers()
            ["auggie", "auggie-mcp", "claude-code", "codex", "cursor", "vscode", "windsurf"]
        """
        return self.registry.get_installer_names()

    def install(
        self,
        integration: str,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
        **kwargs: Any,
    ) -> bool:
        """
        Install an integration.

        Args:
            integration: Integration name (e.g., "claude-code")
            force: Force reinstallation even if already installed
            dry_run: Simulate installation without making changes
            verbose: Enable verbose output
            **kwargs: Additional installer-specific options

        Returns:
            True if successful, False otherwise

        Error Handling:
        - Logs errors but returns False instead of raising
        - This allows callers to handle failures gracefully
        - Detailed error messages are logged for debugging

        Example:
            >>> success = installer_service.install("claude-code", force=True)
            >>> if success:
            >>>     print("Installation successful")
        """
        try:
            project_root = self._config_service.get_project_root()
            installer = self.registry.get_installer(integration, project_root)

            if not installer:
                self.logger.error(f"Unknown integration: {integration}")
                return False

            result = installer.install(force=force, dry_run=dry_run, verbose=verbose, **kwargs)

            # BaseInstaller.install returns InstallationResult
            # Extract success from result
            if hasattr(result, "success"):
                success = result.success
            else:
                # Fallback for installers that return bool directly
                success = bool(result)

            if success:
                self.logger.info(f"Successfully installed {integration}")
            else:
                self.logger.warning(f"Installation of {integration} failed or skipped")

            return success

        except Exception as e:
            self.logger.error(f"Failed to install {integration}: {e}")
            return False

    def uninstall(self, integration: str, **kwargs: Any) -> bool:
        """
        Uninstall an integration.

        Args:
            integration: Integration name
            **kwargs: Additional installer-specific options

        Returns:
            True if successful, False otherwise

        Error Handling:
        - Returns False for unknown integrations
        - Logs errors but doesn't raise exceptions
        - Some integrations may not support uninstallation

        Example:
            >>> success = installer_service.uninstall("claude-code")
            >>> if success:
            >>>     print("Uninstallation successful")
        """
        try:
            project_root = self._config_service.get_project_root()
            installer = self.registry.get_installer(integration, project_root)

            if not installer:
                self.logger.error(f"Unknown integration: {integration}")
                return False

            result = installer.uninstall(**kwargs)

            # Extract success from result
            if hasattr(result, "success"):
                success = result.success
            else:
                success = bool(result)

            if success:
                self.logger.info(f"Successfully uninstalled {integration}")
            else:
                self.logger.warning(f"Uninstallation of {integration} failed")

            return success

        except Exception as e:
            self.logger.error(f"Failed to uninstall {integration}: {e}")
            return False

    def repair_mcp_config(self) -> bool:
        """
        Repair MCP configuration for all installers.

        Scans ~/.claude.json and fixes any broken MCP server configurations.
        This is particularly useful for fixing malformed JSON or incorrect
        command arguments in MCP server definitions.

        Returns:
            True if all repairs successful, False otherwise

        Implementation Note:
        This delegates to the global MCP repair utility which scans and fixes
        MCP configurations across all projects. The repair logic is centralized
        in installers/json_utils.py to maintain consistency.

        Error Handling:
        - Returns False if repair fails
        - Logs detailed error messages
        - Non-existent config file is not considered an error
        """
        try:
            global_config_path = Path.home() / ".claude.json"

            if not global_config_path.exists():
                self.logger.debug("No ~/.claude.json found, nothing to repair")
                return True

            # Load global config
            config = load_json_config(global_config_path)

            # Fix broken args
            fixed_config, fixes = fix_broken_mcp_args(config)

            # Save if fixes were applied
            if fixes:
                save_json_config(global_config_path, fixed_config)
                self.logger.info(f"Successfully repaired MCP config with {len(fixes)} fix(es)")
                for fix in fixes:
                    self.logger.debug(f"  - {fix}")
                return True
            else:
                self.logger.debug("No MCP config repairs needed")
                return True

        except Exception as e:
            self.logger.error(f"Failed to repair MCP configs: {e}")
            return False

    def check_health(self, integration: str) -> dict[str, Any]:
        """
        Check health of an installation.

        Args:
            integration: Integration name

        Returns:
            Health status dictionary with keys:
            - installed: bool (whether integration is detected)
            - healthy: bool (whether installation is complete and working)
            - details: Dict[str, Any] (additional status information)

        Example:
            >>> health = installer_service.check_health("claude-code")
            >>> if not health["healthy"]:
            >>>     print(f"Issues detected: {health['details']}")
        """
        try:
            project_root = self._config_service.get_project_root()
            installer = self.registry.get_installer(integration, project_root)

            if not installer:
                return {
                    "installed": False,
                    "healthy": False,
                    "details": {"error": f"Unknown integration: {integration}"},
                }

            detected = installer.detect_installation()

            # Map health_status to healthy boolean
            healthy = detected.health_status == "healthy"

            return {
                "installed": detected.is_installed,
                "healthy": healthy,
                "details": {
                    "integration": integration,
                    "project_root": str(project_root),
                    "health_status": detected.health_status,
                    "files_present": len(detected.files_present),
                    "files_missing": len(detected.files_missing),
                    "has_mcp": detected.has_mcp,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to check health of {integration}: {e}")
            return {
                "installed": False,
                "healthy": False,
                "details": {"error": str(e)},
            }

    # Additional utility methods (beyond protocol)

    def list_all_installers(self) -> list[dict[str, str]]:
        """
        List all available installers with metadata.

        Returns:
            List of installer information dictionaries with keys:
            - name: str (installer name)
            - ai_system: str (AI system name)
            - description: str (what the installer does)
            - class: str (installer class name)

        Example:
            >>> installers = installer_service.list_all_installers()
            >>> for info in installers:
            >>>     print(f"{info['name']}: {info['description']}")
        """
        return self.registry.list_installers()

    def get_installer_instance(self, integration: str) -> BaseInstaller | None:
        """
        Get installer instance for an integration.

        This is useful for advanced operations that need direct access
        to the installer implementation.

        Args:
            integration: Integration name

        Returns:
            BaseInstaller instance or None if not found

        Warning:
            Direct installer access bypasses service layer. Prefer using
            service methods (install, uninstall, check_health) when possible.
        """
        project_root = self._config_service.get_project_root()
        return self.registry.get_installer(integration, project_root)
