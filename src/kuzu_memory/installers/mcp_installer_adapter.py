"""
MCP Installer Adapter - Bridges py-mcp-installer-service with kuzu-memory.

Provides MCPInstallerAdapter that wraps the vendored py-mcp-installer-service
submodule, exposing it through kuzu-memory's BaseInstaller interface.

This adapter enables kuzu-memory to leverage the comprehensive MCP installation
capabilities from py-mcp-installer while maintaining compatibility with the
existing installer architecture.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from .base import BaseInstaller, InstallationResult, InstalledSystem

logger = logging.getLogger(__name__)

# ============================================================================
# Dynamic Import Handling for Vendored Submodule
# ============================================================================

# Add vendor path to sys.path for submodule imports
_vendor_path = (
    Path(__file__).parent.parent.parent.parent / "vendor" / "py-mcp-installer-service" / "src"
)
if _vendor_path.exists() and str(_vendor_path) not in sys.path:
    sys.path.insert(0, str(_vendor_path))

# Try importing from vendored submodule
try:
    from py_mcp_installer import (
        DiagnosticReport,
        InspectionReport,
        InstallMethod,
        MCPDoctor,
        MCPInspector,
        MCPInstaller,
        Platform,
        PlatformInfo,
        Scope,
    )
    from py_mcp_installer import InstallationResult as PyMCPInstallationResult

    HAS_MCP_INSTALLER = True
except ImportError as e:
    logger.warning(
        f"py-mcp-installer-service not available: {e}. MCPInstallerAdapter will be disabled."
    )
    HAS_MCP_INSTALLER = False

    # Define placeholder types to prevent NameError
    class Platform:  # type: ignore
        """Placeholder Platform enum."""

        pass

    class DiagnosticReport:  # type: ignore
        """Placeholder DiagnosticReport."""

        pass

    class InspectionReport:  # type: ignore
        """Placeholder InspectionReport."""

        pass


# ============================================================================
# Platform Mapping
# ============================================================================

# Map py-mcp-installer Platform to kuzu-memory ai_system names
PLATFORM_MAP: dict[Any, str] = {
    # Will be populated when HAS_MCP_INSTALLER is True
}

if HAS_MCP_INSTALLER:
    PLATFORM_MAP = {
        Platform.CLAUDE_CODE: "claude-code",
        Platform.CLAUDE_DESKTOP: "claude-desktop",
        Platform.CURSOR: "cursor",
        Platform.AUGGIE: "auggie",
        Platform.WINDSURF: "windsurf",
        Platform.CODEX: "codex",
        Platform.GEMINI_CLI: "gemini-cli",
        Platform.ANTIGRAVITY: "antigravity",
    }

# Reverse mapping for ai_system_name -> Platform
REVERSE_PLATFORM_MAP: dict[str, Any] = {v: k for k, v in PLATFORM_MAP.items()}


# ============================================================================
# Main Adapter Class
# ============================================================================


class MCPInstallerAdapter(BaseInstaller):
    """
    Adapter wrapping py-mcp-installer-service in BaseInstaller interface.

    This adapter bridges the external MCP installer service with kuzu-memory's
    existing installer architecture, providing:
    - Auto-detection of AI platforms (Cursor, Claude Code, VS Code, etc.)
    - Smart installation method selection (uv run, pipx, direct)
    - Comprehensive diagnostics via MCPDoctor
    - Configuration inspection via MCPInspector

    Example:
        >>> adapter = MCPInstallerAdapter(project_root=Path.cwd())
        >>> result = adapter.install(force=False, dry_run=True)
        >>> if result.success:
        ...     print(f"Installed to {result.ai_system}")

    Attributes:
        platform: Target platform (auto-detected if None)
        installer: Wrapped MCPInstaller instance
        doctor: MCPDoctor for diagnostics
        inspector: MCPInspector for validation
    """

    def __init__(
        self,
        project_root: Path,
        platform: Platform | str | None = None,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        """
        Initialize MCP installer adapter.

        Args:
            project_root: Root directory of the project
            platform: Force specific platform (Platform enum or string name)
                     None = auto-detect
            dry_run: Preview changes without applying
            verbose: Enable verbose logging

        Raises:
            RuntimeError: If py-mcp-installer-service is not available
            ValueError: If platform string is invalid
        """
        if not HAS_MCP_INSTALLER:
            raise RuntimeError(
                "py-mcp-installer-service is not available. "
                "Please ensure the vendor submodule is initialized: "
                "git submodule update --init --recursive"
            )

        super().__init__(project_root)

        # Convert string platform to enum if needed
        # Note: Platform enum inherits from str, so check type explicitly
        if platform is not None and type(platform) is str:
            platform_enum = REVERSE_PLATFORM_MAP.get(platform)
            if platform_enum is None:
                raise ValueError(
                    f"Invalid platform: {platform}. "
                    f"Valid options: {list(REVERSE_PLATFORM_MAP.keys())}"
                )
            platform = platform_enum

        # Initialize wrapped installer
        self._dry_run = dry_run
        self._verbose = verbose
        self._platform = platform
        self.installer = MCPInstaller(platform=platform, dry_run=dry_run, verbose=verbose)

        # Initialize diagnostic and inspection tools
        self.doctor = MCPDoctor(self.installer.platform_info)
        self.inspector = MCPInspector(self.installer.platform_info)

        # Log initialization (safely handle mock objects in tests)
        try:
            confidence = self.installer.platform_info.confidence
            logger.info(
                f"Initialized MCPInstallerAdapter for {self.ai_system_name} "
                f"(confidence: {confidence:.2f})"
            )
        except (TypeError, AttributeError):
            # In tests with mocks, this might fail - that's okay
            logger.info(f"Initialized MCPInstallerAdapter for {self.ai_system_name}")

    @property
    def platform_info(self) -> PlatformInfo:
        """Get platform detection information."""
        return self.installer.platform_info

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system this installer supports."""
        platform = self.installer.platform_info.platform
        # PLATFORM_MAP returns str, platform.value is str (Platform inherits from str)
        result: str = PLATFORM_MAP.get(platform, platform.value)
        return result

    @property
    def required_files(self) -> list[str]:
        """List of files that will be created/modified by this installer."""
        config_path = self.installer.platform_info.config_path
        if config_path:
            # Make path relative to project root
            try:
                rel_path = config_path.relative_to(self.project_root)
                return [str(rel_path)]
            except ValueError:
                # Config path is not relative to project root (e.g., global config)
                return [str(config_path)]
        return []

    @property
    def description(self) -> str:
        """Description of what this installer does."""
        return (
            f"Install MCP server configuration for {self.ai_system_name} "
            f"using py-mcp-installer-service"
        )

    def install(
        self,
        force: bool = False,
        dry_run: bool | None = None,
        server_name: str = "kuzu-memory",
        command: str = "kuzu-memory",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        description: str = "KuzuMemory - Graph-based memory for AI",
        scope: str = "project",
        method: str | None = None,
        **kwargs: Any,
    ) -> InstallationResult:
        """
        Install MCP server configuration.

        Args:
            force: Force installation (overwrite existing config)
            dry_run: Preview changes without applying (overrides instance setting)
            server_name: MCP server name (default: "kuzu-memory")
            command: Executable command (default: "kuzu-memory")
            args: Command arguments (default: ["mcp"])
            env: Environment variables (auto-populated with project paths)
            description: Server description
            scope: Installation scope ("project" or "global")
            method: Installation method ("uv_run", "pipx", "direct", "python_module")
            **kwargs: Additional installer-specific options

        Returns:
            InstallationResult with installation details
        """
        # Use instance dry_run if not overridden
        is_dry_run = dry_run if dry_run is not None else self._dry_run

        # Set default args if not provided
        if args is None:
            args = ["mcp"]

        # Auto-populate environment variables
        if env is None:
            env = {}

        # Add project root and database path to env
        env.setdefault("KUZU_MEMORY_PROJECT_ROOT", str(self.project_root))
        env.setdefault("KUZU_MEMORY_DB", str(self.project_root / "kuzu-memories"))

        # Convert scope string to Scope enum
        scope_enum = Scope.PROJECT if scope.lower() == "project" else Scope.GLOBAL

        # Convert method string to InstallMethod enum
        method_enum = None
        if method:
            method_map = {
                "uv_run": InstallMethod.UV_RUN,
                "pipx": InstallMethod.PIPX,
                "direct": InstallMethod.DIRECT,
                "python_module": InstallMethod.PYTHON_MODULE,
            }
            method_enum = method_map.get(method.lower())

        logger.info(
            f"Installing {server_name} to {self.ai_system_name} "
            f"(dry_run={is_dry_run}, force={force})"
        )

        try:
            # Perform installation
            result = self.installer.install_server(
                name=server_name,
                command=command,
                args=args,
                env=env,
                description=description,
                scope=scope_enum,
                method=method_enum,
            )

            # Convert to kuzu-memory InstallationResult format
            return self._convert_installation_result(result)

        except Exception as e:
            logger.exception(f"Installation failed: {e}")
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=[],
                backup_files=[],
                message=f"Installation failed: {e}",
                warnings=[str(e)],
            )

    def uninstall(self, server_name: str = "kuzu-memory", **kwargs: Any) -> InstallationResult:
        """
        Uninstall MCP server configuration.

        Args:
            server_name: MCP server name to uninstall (default: "kuzu-memory")
            **kwargs: Additional options

        Returns:
            InstallationResult with uninstallation details
        """
        logger.info(f"Uninstalling {server_name} from {self.ai_system_name}")

        try:
            # Uninstall server
            result = self.installer.uninstall_server(server_name)

            # Convert to kuzu-memory format
            return self._convert_installation_result(result)

        except Exception as e:
            logger.exception(f"Uninstallation failed: {e}")
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=[],
                backup_files=[],
                message=f"Uninstallation failed: {e}",
                warnings=[str(e)],
            )

    def detect_installation(self) -> InstalledSystem:
        """
        Detect if this system is installed and its health status.

        Returns:
            InstalledSystem object with detection details
        """
        files_present = []
        files_missing = []

        # Check required files
        for file_pattern in self.required_files:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                files_present.append(file_path)
            else:
                files_missing.append(file_path)

        is_installed = len(files_present) > 0

        # Use inspector to check configuration validity
        try:
            inspection = self.inspector.inspect_installation()
            has_kuzu_memory = any(
                "kuzu-memory" in server.lower() for server in inspection.server_names
            )

            # Determine health based on validation issues
            if not is_installed:
                health_status = "not_installed"
            elif inspection.is_valid and has_kuzu_memory:
                health_status = "healthy"
            elif has_kuzu_memory:
                health_status = "needs_repair"
            else:
                health_status = "not_installed"

        except Exception as e:
            logger.warning(f"Inspection failed: {e}")
            health_status = "needs_repair" if is_installed else "not_installed"
            has_kuzu_memory = False

        return InstalledSystem(
            name=self.ai_system_name,
            ai_system=self.ai_system_name,
            is_installed=is_installed,
            health_status=health_status,
            files_present=files_present,
            files_missing=files_missing,
            has_mcp=has_kuzu_memory,
            details={
                "platform": self.installer.platform_info.platform.value,
                "confidence": self.installer.platform_info.confidence,
                "cli_available": self.installer.platform_info.cli_available,
                "scope_support": self.installer.platform_info.scope_support.value,
            },
        )

    def run_diagnostics(self, full: bool = False, **kwargs: Any) -> dict[str, Any]:
        """
        Run comprehensive diagnostics on MCP installation.

        Args:
            full: Run full diagnostics (includes server connectivity tests)
            **kwargs: Additional diagnostic options

        Returns:
            Dictionary with diagnostic results
        """
        logger.info(f"Running diagnostics for {self.ai_system_name} (full={full})")

        try:
            # Run diagnostics
            report = self.doctor.diagnose(full=full)

            # Convert to dictionary format
            return self._convert_diagnostic_report(report)

        except Exception as e:
            logger.exception(f"Diagnostics failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "error",
            }

    def inspect_config(self, **kwargs: Any) -> dict[str, Any]:
        """
        Inspect and validate configuration.

        Args:
            **kwargs: Additional inspection options

        Returns:
            Dictionary with inspection results
        """
        logger.info(f"Inspecting configuration for {self.ai_system_name}")

        try:
            # Inspect installation
            report = self.inspector.inspect_installation()

            # Convert to dictionary format
            return self._convert_inspection_report(report)

        except Exception as e:
            logger.exception(f"Inspection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "is_valid": False,
            }

    def fix_issues(self, auto_fix: bool = True, **kwargs: Any) -> list[str]:
        """
        Auto-fix detected issues in MCP installation.

        Args:
            auto_fix: Whether to actually apply fixes (default: True)
            **kwargs: Additional fix options

        Returns:
            List of fix descriptions applied

        Note:
            Currently returns empty list as MCPDoctor does not expose
            auto-fix functionality. Future enhancement will integrate
            with MCPDoctor.fix_issues() when available.
        """
        logger.info(f"Attempting to fix issues for {self.ai_system_name}")

        # Placeholder for future auto-fix functionality
        # When py-mcp-installer-service adds fix_issues method to MCPDoctor,
        # we can integrate it here
        fixes_applied: list[str] = []

        # TODO: Integrate with MCPDoctor.fix_issues() when available
        # Example:
        # try:
        #     fixes = self.doctor.fix_issues(auto_fix=auto_fix)
        #     fixes_applied.extend(fixes)
        # except Exception as e:
        #     logger.warning(f"Auto-fix failed: {e}")

        logger.info(f"Applied {len(fixes_applied)} fix(es)")
        return fixes_applied

    # ========================================================================
    # Conversion Helpers
    # ========================================================================

    def _convert_installation_result(self, result: PyMCPInstallationResult) -> InstallationResult:
        """
        Convert py-mcp-installer InstallationResult to kuzu-memory format.

        Args:
            result: PyMCPInstallationResult from installer

        Returns:
            InstallationResult in kuzu-memory format
        """
        # Determine files affected
        files_created: list[Path] = []
        files_modified: list[Path] = []
        backup_files: list[Path] = []

        if result.config_path:
            # Check if config existed before installation
            # If it did, it was modified; otherwise it was created
            # For simplicity, assume modification if installation succeeded
            if result.success:
                files_modified.append(result.config_path)
                # Backups would be in .backup_* files in same directory
                backup_dir = result.config_path.parent
                if backup_dir.exists():
                    backup_files.extend(backup_dir.glob(f"{result.config_path.name}.backup_*"))

        return InstallationResult(
            success=result.success,
            ai_system=PLATFORM_MAP.get(result.platform, result.platform.value),
            files_created=files_created,
            files_modified=files_modified,
            backup_files=backup_files,
            message=result.message,
            warnings=[str(result.error)] if result.error else [],
        )

    def _convert_diagnostic_report(self, report: DiagnosticReport) -> dict[str, Any]:
        """
        Convert DiagnosticReport to kuzu-memory diagnostic format.

        Args:
            report: DiagnosticReport from MCPDoctor

        Returns:
            Dictionary with diagnostic results
        """
        return {
            "success": True,
            "status": report.status.value,
            "platform": report.platform.value,
            "checks_total": report.checks_total,
            "checks_passed": report.checks_passed,
            "checks_failed": report.checks_failed,
            "issues": [
                {
                    "category": issue.category.value,
                    "severity": issue.severity,
                    "message": issue.message,
                    "server_name": issue.server_name,
                    "fix_suggestion": issue.fix_suggestion,
                }
                for issue in report.issues
            ],
            "server_reports": {
                name: {
                    "status": diag.status.value,
                    "response_time_ms": diag.response_time_ms,
                    "tool_count": diag.tool_count,
                    "error": diag.error,
                }
                for name, diag in report.server_reports.items()
            },
            "recommendations": report.recommendations,
        }

    def _convert_inspection_report(self, report: InspectionReport) -> dict[str, Any]:
        """
        Convert InspectionReport to kuzu-memory inspection format.

        Args:
            report: InspectionReport from MCPInspector

        Returns:
            Dictionary with inspection results
        """
        return {
            "success": True,
            "platform": report.platform.value,
            "config_path": str(report.config_path) if report.config_path else None,
            "is_valid": report.is_valid,
            "server_count": report.server_count,
            "server_names": report.server_names,
            "issues": [
                {
                    "severity": issue.severity,
                    "message": issue.message,
                    "server_name": issue.server_name,
                    "fix_suggestion": issue.fix_suggestion,
                }
                for issue in report.issues
            ],
            "summary": report.summary,
        }

    def _check_mcp_configured(self) -> bool:
        """
        Check if MCP server is configured for this system.

        Returns:
            True if kuzu-memory MCP is configured, False otherwise
        """
        try:
            inspection = self.inspector.inspect_installation()
            return any("kuzu-memory" in server.lower() for server in inspection.server_names)
        except Exception as e:
            logger.debug(f"Failed to check MCP configuration: {e}")
            return False


# ============================================================================
# Convenience Factory Functions
# ============================================================================


def create_mcp_installer_adapter(
    project_root: Path,
    platform: Platform | str | None = None,
    **kwargs: Any,
) -> MCPInstallerAdapter:
    """
    Create MCPInstallerAdapter with auto-detection.

    Args:
        project_root: Root directory of the project
        platform: Force specific platform (None = auto-detect)
        **kwargs: Additional arguments passed to MCPInstallerAdapter

    Returns:
        Configured MCPInstallerAdapter instance

    Raises:
        RuntimeError: If py-mcp-installer-service is not available
    """
    return MCPInstallerAdapter(project_root=project_root, platform=platform, **kwargs)


def is_mcp_installer_available() -> bool:
    """
    Check if py-mcp-installer-service is available.

    Returns:
        True if submodule is available, False otherwise
    """
    return HAS_MCP_INSTALLER
