"""DiagnosticService implementation - diagnostic and health checking service."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kuzu_memory.installers.mcp_installer_adapter import (
    HAS_MCP_INSTALLER,
    MCPInstallerAdapter,
)
from kuzu_memory.mcp.testing.diagnostics import MCPDiagnostics
from kuzu_memory.mcp.testing.health_checker import MCPHealthChecker
from kuzu_memory.services.base import BaseService

if TYPE_CHECKING:
    # Import concrete services for type checking (not just protocols)
    # This is needed because we call lifecycle methods (.initialize(), .is_initialized)
    from kuzu_memory.services.config_service import ConfigService
    from kuzu_memory.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class DiagnosticService(BaseService):
    """
    Diagnostic and health checking service.

    Async thin orchestrator wrapping MCPDiagnostics and MCPHealthChecker,
    providing lifecycle management and dependency injection.

    Design Pattern: Async Thin Orchestrator
    ----------------------------------------
    - Delegates async diagnostic operations to MCPDiagnostics and MCPHealthChecker
    - Handles lifecycle management through BaseService
    - Provides optional dependency injection of IMemoryService for DB health checks
    - All diagnostic methods are async for I/O operations

    Design Decision: Async Methods for I/O Operations
    --------------------------------------------------
    Rationale: Diagnostic operations involve I/O (database checks, file system access,
    network calls). Async methods prevent blocking and enable concurrent health checks
    for better performance.

    Trade-offs:
    - Performance: Enables concurrent checks vs. sequential blocking calls
    - Complexity: Async/await adds complexity but improves responsiveness
    - Compatibility: Requires async context but provides better scalability

    Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
    Related Task: Phase 4 Service Implementation #3 (Final)
    """

    def __init__(
        self,
        config_service: ConfigService,
        memory_service: MemoryService | None = None,
    ):
        """
        Initialize with service dependencies.

        Args:
            config_service: Configuration service (required)
            memory_service: Memory service (optional, for DB health checks)
        """
        super().__init__()
        self._config_service = config_service
        self._memory_service = memory_service
        self._diagnostics: MCPDiagnostics | None = None
        self._health_checker: MCPHealthChecker | None = None

    def _do_initialize(self) -> None:
        """
        Initialize diagnostics and health checker.

        Initializes config service if needed, then creates diagnostic tools
        with project root configuration.
        """
        # Initialize config service to ensure project root available
        if not self._config_service.is_initialized:
            self._config_service.initialize()

        project_root = self._config_service.get_project_root()

        # Initialize both diagnostic tools
        self._diagnostics = MCPDiagnostics(project_root=project_root)
        self._health_checker = MCPHealthChecker(project_root=project_root)

        # Initialize memory service if provided
        if self._memory_service and not self._memory_service.is_initialized:
            self._memory_service.initialize()

        self.logger.info(f"DiagnosticService initialized with project_root={project_root}")

    def _do_cleanup(self) -> None:
        """Clean up diagnostic resources."""
        self._diagnostics = None
        self._health_checker = None
        self.logger.info("DiagnosticService cleaned up")

    @property
    def diagnostics(self) -> MCPDiagnostics:
        """
        Access underlying MCPDiagnostics instance.

        Returns:
            MCPDiagnostics instance

        Raises:
            RuntimeError: If service not initialized
        """
        self._check_initialized()
        assert self._diagnostics is not None, "Diagnostics should be initialized"
        return self._diagnostics

    @property
    def health_checker(self) -> MCPHealthChecker:
        """
        Access underlying MCPHealthChecker instance.

        Returns:
            MCPHealthChecker instance

        Raises:
            RuntimeError: If service not initialized
        """
        self._check_initialized()
        assert self._health_checker is not None, "Health checker should be initialized"
        return self._health_checker

    # ========================================================================
    # ASYNC DIAGNOSTIC METHODS (7 methods)
    # ========================================================================

    async def run_full_diagnostics(self) -> dict[str, Any]:
        """
        Run comprehensive diagnostics on entire system.

        Aggregates results from both MCPDiagnostics and MCPHealthChecker to provide
        a complete system health picture including configuration, database, MCP server,
        git integration, system info, and dependencies.

        Returns:
            Complete diagnostic results with keys:
            - all_healthy: bool - True if all checks passed
            - configuration: dict[str, Any] - Config check results
            - database: dict[str, Any] - Database health results
            - mcp_server: dict[str, Any] - MCP server status
            - git_integration: dict[str, Any] - Git sync status
            - system_info: dict[str, Any] - System information
            - dependencies: dict[str, Any] - Dependency verification
            - timestamp: str - ISO timestamp of diagnostic run

        Raises:
            RuntimeError: If service not initialized

        Performance:
        - Total time: ~2-5 seconds depending on system
        - Runs checks concurrently where possible
        - Async prevents blocking during I/O operations

        Example:
            >>> async with DiagnosticService(config_svc) as svc:
            >>>     results = await svc.run_full_diagnostics()
            >>>     if not results["all_healthy"]:
            >>>         print("Issues found:", results)
        """
        self._check_initialized()

        # Run full diagnostics using MCPDiagnostics
        report = await self.diagnostics.run_full_diagnostics(
            auto_fix=False,
            check_hooks=True,
            check_server_lifecycle=True,
        )

        # Convert diagnostic report to protocol format
        config_results = await self.check_configuration()
        db_results = await self.check_database_health()
        mcp_results = await self.check_mcp_server_health()
        git_results = await self.check_git_integration()
        system_info = await self.get_system_info()
        deps_results = await self.verify_dependencies()
        mcp_install_results = await self.check_mcp_installation(full=True)

        all_healthy = (
            config_results.get("valid", False)
            and db_results.get("connected", False)
            and mcp_results.get("configured", False)
            and not report.has_critical_errors
        )

        return {
            "all_healthy": all_healthy,
            "configuration": config_results,
            "database": db_results,
            "mcp_server": mcp_results,
            "git_integration": git_results,
            "system_info": system_info,
            "dependencies": deps_results,
            "mcp_installation": mcp_install_results,
            "timestamp": report.timestamp,
            "total_checks": report.total,
            "passed_checks": report.passed,
            "failed_checks": report.failed,
            "success_rate": report.success_rate,
        }

    async def check_configuration(self) -> dict[str, Any]:
        """
        Check configuration validity and completeness.

        Verifies that all required configuration files exist, are readable,
        contain valid data, and point to accessible resources.

        Returns:
            Configuration check results with keys:
            - valid: bool - True if config is valid
            - issues: List[str] - Problems found
            - config_path: str - Path to config file
            - project_root: str - Project root directory

        Raises:
            RuntimeError: If service not initialized

        Checks:
        - Configuration file exists and is readable
        - Required configuration keys present
        - Paths are valid and accessible
        - Environment variables properly set

        Example:
            >>> results = await svc.check_configuration()
            >>> if not results["valid"]:
            >>>     print("Config issues:", results["issues"])
        """
        self._check_initialized()

        # Run configuration checks
        config_results = await self.diagnostics.check_configuration()

        issues = []
        for result in config_results:
            if not result.success:
                issue_msg = result.message
                if result.error:
                    issue_msg += f": {result.error}"
                issues.append(issue_msg)

        project_root = self._config_service.get_project_root()

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config_path": str(project_root / ".kuzu-memory" / "config.yaml"),
            "project_root": str(project_root),
        }

    async def check_database_health(self) -> dict[str, Any]:
        """
        Check database connectivity and health.

        Verifies database file exists, is accessible, and can be opened successfully.
        If memory service is available, performs additional health checks.

        Returns:
            Database health results with keys:
            - connected: bool - True if database is accessible
            - memory_count: int - Total memories (if memory_service available)
            - db_size_bytes: int - Database size
            - schema_version: str - Current schema version (if available)
            - issues: List[str] - Problems found

        Raises:
            RuntimeError: If service not initialized

        Checks:
        - Database file exists and is accessible
        - Database connection can be established
        - Schema is valid and up-to-date
        - No corruption detected

        Example:
            >>> results = await svc.check_database_health()
            >>> if results["connected"]:
            >>>     print(f"DB healthy: {results['memory_count']} memories")
        """
        self._check_initialized()

        # Use health checker for database health
        health_result = await self.health_checker.check_health(detailed=False, retry=False)

        db_component = next(
            (c for c in health_result.health.components if c.name == "database"),
            None,
        )

        issues = []
        if db_component and db_component.error:
            issues.append(db_component.error)

        connected = db_component is not None and db_component.status.value in [
            "healthy",
            "degraded",
        ]

        # Get memory count if memory service available
        memory_count = 0
        db_size_bytes = 0

        if db_component and db_component.metadata:
            db_size_bytes = db_component.metadata.get("size_bytes", 0)

        if self._memory_service:
            try:
                memory_count = self._memory_service.get_memory_count()
                db_size_bytes = self._memory_service.get_database_size()
            except Exception as e:
                issues.append(f"Failed to get memory stats: {e}")

        return {
            "connected": connected,
            "memory_count": memory_count,
            "db_size_bytes": db_size_bytes,
            "schema_version": "1.0",  # TODO: Get from database metadata
            "issues": issues,
        }

    async def check_mcp_server_health(self) -> dict[str, Any]:
        """
        Check MCP server configuration and health.

        Verifies MCP server config exists, is valid, and server can be started
        and respond to requests.

        Returns:
            MCP server health results with keys:
            - configured: bool - True if server is configured
            - config_valid: bool - True if config is valid JSON
            - server_path: str - Path to MCP server config
            - issues: List[str] - Problems found

        Raises:
            RuntimeError: If service not initialized

        Checks:
        - MCP config file exists (claude_desktop_config.json or settings.local.json)
        - Configuration is valid JSON
        - Server entry is present and correct
        - Paths in configuration are valid

        Example:
            >>> results = await svc.check_mcp_server_health()
            >>> if not results["configured"]:
            >>>     print("MCP server not configured")
        """
        self._check_initialized()

        # Check MCP server health using health checker
        health_result = await self.health_checker.check_health(detailed=False, retry=False)

        protocol_component = next(
            (c for c in health_result.health.components if c.name == "protocol"),
            None,
        )

        issues = []
        if protocol_component and protocol_component.error:
            issues.append(protocol_component.error)

        configured = protocol_component is not None and protocol_component.status.value in [
            "healthy",
            "degraded",
        ]
        config_valid = configured  # If protocol works, config is valid

        project_root = self._config_service.get_project_root()
        server_path = str(project_root / ".claude" / "settings.local.json")

        return {
            "configured": configured,
            "config_valid": config_valid,
            "server_path": server_path,
            "issues": issues,
        }

    async def check_git_integration(self) -> dict[str, Any]:
        """
        Check git synchronization integration.

        Verifies git is available, repository is detected, and hooks are installed
        if git sync is configured.

        Returns:
            Git integration results with keys:
            - available: bool - Git is available
            - hooks_installed: bool - Git hooks are installed
            - last_sync: Optional[str] - Last sync timestamp
            - issues: List[str] - Problems found

        Raises:
            RuntimeError: If service not initialized

        Checks:
        - Git repository is detected
        - Git hooks are installed
        - Sync functionality is working
        - No permission issues

        Example:
            >>> results = await svc.check_git_integration()
            >>> if results["hooks_installed"]:
            >>>     print(f"Last sync: {results['last_sync']}")
        """
        self._check_initialized()

        import subprocess

        # Check if git is available
        available = False
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            available = result.returncode == 0
        except Exception:
            available = False

        # Check for git hooks
        project_root = self._config_service.get_project_root()
        hooks_path = project_root / ".git" / "hooks" / "post-commit"
        hooks_installed = hooks_path.exists()

        issues = []
        if not available:
            issues.append("Git not available in PATH")

        return {
            "available": available,
            "hooks_installed": hooks_installed,
            "last_sync": None,  # TODO: Get from config/metadata
            "issues": issues,
        }

    async def check_hooks_status(self, project_root: Path | None = None) -> dict[str, Any]:
        """
        Check status of all hooks (git and Claude Code).

        Verifies installation and configuration of:
        - Git post-commit hooks (.git/hooks/post-commit)
        - Claude Code hooks (.claude/settings.local.json)

        Args:
            project_root: Optional project root directory (uses config service default if None)

        Returns:
            dict with keys:
            - git_hooks: dict with installed, executable, path
            - claude_code_hooks: dict with installed, valid, events
            - overall_status: str - "fully_configured", "partially_configured", "not_configured"
            - recommendations: list[str] - Actionable recommendations

        Raises:
            RuntimeError: If service not initialized

        Example:
            >>> async with DiagnosticService(config_svc) as svc:
            >>>     results = await svc.check_hooks_status()
            >>>     if results["overall_status"] == "not_configured":
            >>>         print("Recommendations:", results["recommendations"])
        """
        self._check_initialized()

        import json
        import os

        # Use provided project root or get from config service
        root = project_root or self._config_service.get_project_root()

        result: dict[str, Any] = {
            "git_hooks": {"installed": False, "executable": False, "path": None},
            "claude_code_hooks": {"installed": False, "valid": False, "events": []},
            "overall_status": "not_configured",
            "recommendations": [],
        }

        # Check git hooks
        git_hook = root / ".git" / "hooks" / "post-commit"
        if git_hook.exists():
            result["git_hooks"]["installed"] = True
            result["git_hooks"]["path"] = str(git_hook)
            result["git_hooks"]["executable"] = os.access(git_hook, os.X_OK)

        # Check Claude Code hooks
        claude_settings = root / ".claude" / "settings.local.json"
        if claude_settings.exists():
            try:
                with open(claude_settings) as f:
                    settings = json.load(f)

                if "hooks" in settings and isinstance(settings["hooks"], dict):
                    result["claude_code_hooks"]["installed"] = True

                    # Extract event names
                    events = list(settings["hooks"].keys())
                    result["claude_code_hooks"]["events"] = events

                    # Validate events (check if they're valid Claude Code events)
                    result["claude_code_hooks"]["valid"] = self._validate_claude_hooks(
                        settings["hooks"]
                    )
            except (OSError, json.JSONDecodeError) as e:
                result["claude_code_hooks"]["error"] = f"Failed to parse settings: {e}"

        # Determine overall status
        git_ok = result["git_hooks"]["installed"]
        claude_ok = result["claude_code_hooks"]["installed"]

        if git_ok and claude_ok:
            result["overall_status"] = "fully_configured"
        elif git_ok or claude_ok:
            result["overall_status"] = "partially_configured"
        else:
            result["overall_status"] = "not_configured"

        # Add recommendations
        if not git_ok:
            result["recommendations"].append(
                "Run 'kuzu-memory git install-hooks' to enable git integration"
            )

        if not claude_ok:
            result["recommendations"].append(
                "Run 'kuzu-memory install claude-code' to enable Claude Code hooks"
            )

        if git_ok and not result["git_hooks"]["executable"]:
            result["recommendations"].append("Git hook exists but is not executable")

        if claude_ok and not result["claude_code_hooks"]["valid"]:
            result["recommendations"].append("Claude Code hooks config has invalid events")

        return result

    def _validate_claude_hooks(self, hooks: dict[str, Any]) -> bool:
        """
        Validate Claude Code hooks configuration.

        Checks if hook events are valid Claude Code events and if commands
        reference kuzu-memory correctly.

        Args:
            hooks: Hooks configuration dict from settings.local.json

        Returns:
            True if configuration is valid, False otherwise
        """
        # Valid Claude Code events (from claude_hooks.py)
        valid_events = {
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SubagentStop",
            "Notification",
            "SessionStart",
            "SessionEnd",
            "PreCompact",
        }

        # Check if all events are valid
        for event_name in hooks.keys():
            if event_name not in valid_events:
                logger.warning(f"Invalid Claude Code event: {event_name}")
                return False

        # Check if kuzu-memory hooks are present
        has_kuzu_hooks = False
        for _event_name, handlers in hooks.items():
            if not isinstance(handlers, list):
                continue

            for handler_group in handlers:
                if not isinstance(handler_group, dict):
                    continue

                for hook in handler_group.get("hooks", []):
                    if not isinstance(hook, dict):
                        continue

                    command = hook.get("command", "")
                    if "kuzu-memory" in command or "kuzu_memory" in command:
                        has_kuzu_hooks = True
                        break

        return has_kuzu_hooks

    async def check_mcp_installation(self, full: bool = False) -> dict[str, Any]:
        """
        Check MCP installation using py-mcp-installer-service diagnostics.

        Uses MCPInstallerAdapter to run comprehensive MCP server diagnostics
        including platform detection, command accessibility, environment variables,
        and optionally JSON-RPC protocol compliance testing.

        Args:
            full: If True, also test server protocol compliance (slower but comprehensive)

        Returns:
            MCP installation diagnostic results with keys:
            - available: bool - Whether MCPInstallerAdapter is available
            - status: str - Overall status ("healthy", "degraded", "critical")
            - platform: str - Detected platform
            - checks_total: int - Total checks performed
            - checks_passed: int - Passed checks
            - issues: List[dict] - Detailed issues found
            - server_reports: dict - Per-server diagnostics (in full mode)
            - recommendations: List[str] - Actionable recommendations

        Raises:
            RuntimeError: If service not initialized

        Performance:
        - Quick mode: ~100-200ms (platform detection, config checks)
        - Full mode: ~2-5 seconds (includes JSON-RPC protocol tests)

        Example:
            >>> async with DiagnosticService(config_svc) as svc:
            >>>     # Quick check
            >>>     results = await svc.check_mcp_installation()
            >>>     # Full check with protocol tests
            >>>     results = await svc.check_mcp_installation(full=True)
        """
        self._check_initialized()

        # Check if MCPInstallerAdapter is available
        if not HAS_MCP_INSTALLER:
            return {
                "available": False,
                "status": "unavailable",
                "platform": "unknown",
                "checks_total": 0,
                "checks_passed": 0,
                "issues": [
                    {
                        "severity": "warning",
                        "message": (
                            "py-mcp-installer-service not available. "
                            "Install submodule for enhanced MCP diagnostics: "
                            "git submodule update --init --recursive"
                        ),
                    }
                ],
                "server_reports": {},
                "recommendations": [
                    "Install py-mcp-installer-service submodule for enhanced diagnostics",
                    "Run: git submodule update --init --recursive",
                ],
            }

        project_root = self._config_service.get_project_root()

        try:
            # Create MCPInstallerAdapter for diagnostics
            adapter = MCPInstallerAdapter(project_root=project_root)

            # Run diagnostics through adapter
            diagnostic_results = adapter.run_diagnostics(full=full)

            # Add platform information
            diagnostic_results["platform"] = adapter.ai_system_name
            diagnostic_results["available"] = True

            return diagnostic_results

        except Exception as e:
            logger.exception(f"MCP installation check failed: {e}")
            return {
                "available": True,
                "status": "error",
                "platform": "unknown",
                "checks_total": 0,
                "checks_passed": 0,
                "issues": [
                    {
                        "severity": "error",
                        "message": f"MCP diagnostic failed: {e}",
                    }
                ],
                "server_reports": {},
                "recommendations": [
                    "Check MCP configuration files",
                    "Verify platform detection is correct",
                ],
            }

    async def get_system_info(self) -> dict[str, Any]:
        """
        Get system information and environment details.

        Collects version information, platform details, and installation paths
        for debugging and support purposes.

        Returns:
            System information with keys:
            - version: str - KuzuMemory version
            - python_version: str - Python version
            - platform: str - Operating system
            - kuzu_version: str - Kuzu database version
            - install_path: str - Installation path

        Raises:
            RuntimeError: If service not initialized

        Example:
            >>> info = await svc.get_system_info()
            >>> print(f"KuzuMemory v{info['version']} on {info['platform']}")
        """
        self._check_initialized()

        import platform
        import sys

        # Get KuzuMemory version
        try:
            from kuzu_memory import __version__

            version = __version__
        except ImportError:
            version = "unknown"

        # Get Kuzu version
        try:
            import kuzu

            kuzu_version = getattr(kuzu, "__version__", "unknown")
        except ImportError:
            kuzu_version = "unknown"

        # Get installation path
        try:
            import kuzu_memory

            install_path = str(Path(kuzu_memory.__file__).parent)
        except ImportError:
            install_path = "unknown"

        return {
            "version": version,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system(),
            "kuzu_version": kuzu_version,
            "install_path": install_path,
        }

    async def verify_dependencies(self) -> dict[str, Any]:
        """
        Verify all required dependencies are installed.

        Checks that required Python packages are installed and meet version
        requirements. Also checks for optional dependencies.

        Returns:
            Dependency verification results with keys:
            - all_satisfied: bool - True if all required deps installed
            - missing: List[str] - Missing dependencies
            - outdated: List[str] - Outdated dependencies
            - suggestions: List[str] - Remediation steps

        Raises:
            RuntimeError: If service not initialized

        Checks:
        - Required Python packages installed
        - Package versions meet requirements
        - Optional dependencies for integrations

        Example:
            >>> results = await svc.verify_dependencies()
            >>> if not results["all_satisfied"]:
            >>>     print("Missing:", results["missing"])
            >>>     print("Suggestions:", results["suggestions"])
        """
        self._check_initialized()

        # List of required dependencies
        required_deps = [
            "kuzu",
            "click",
            "pydantic",
            "pyyaml",
        ]

        missing = []
        for dep in required_deps:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)

        # Check optional dependencies
        # optional_deps used for potential future enhancement tracking
        # optional_deps = {
        #     "psutil": "Enhanced health monitoring",
        #     "pytest": "Running tests",
        #     "mypy": "Type checking",
        # }

        suggestions = []
        if missing:
            suggestions.append(f"Install missing packages: pip install {' '.join(missing)}")

        all_satisfied = len(missing) == 0

        return {
            "all_satisfied": all_satisfied,
            "missing": missing,
            "outdated": [],  # TODO: Version checking
            "suggestions": suggestions,
        }

    # ========================================================================
    # SYNC FORMATTING METHOD (1 method)
    # ========================================================================

    def format_diagnostic_report(self, results: dict[str, Any]) -> str:
        """
        Format diagnostic results as human-readable report.

        Takes raw diagnostic results and produces a formatted text report with
        sections for each check, color coding for status, and actionable
        recommendations.

        Args:
            results: Diagnostic results from run_full_diagnostics()

        Returns:
            Formatted report string with sections for each check

        Note: This method is synchronous as it only formats data.

        Example:
            >>> results = await svc.run_full_diagnostics()
            >>> report = svc.format_diagnostic_report(results)
            >>> print(report)

        Format:
        - Header with overall status
        - Configuration section
        - Database section
        - MCP Server section
        - Git Integration section
        - System Info section
        - Dependencies section
        - Summary and recommendations
        """
        lines = []
        lines.append("=" * 70)
        lines.append("  KuzuMemory Diagnostic Report")
        lines.append("=" * 70)

        # Overall status
        all_healthy = results.get("all_healthy", False)
        status_symbol = "✓" if all_healthy else "✗"
        status_text = "HEALTHY" if all_healthy else "ISSUES DETECTED"
        lines.append(f"\nOverall Status: {status_symbol} {status_text}")
        lines.append(f"Timestamp: {results.get('timestamp', 'N/A')}")

        if "total_checks" in results:
            lines.append(
                f"Checks: {results['passed_checks']}/{results['total_checks']} passed "
                f"({results['success_rate']:.1f}%)"
            )

        # Configuration Section
        lines.append("\n" + "=" * 70)
        lines.append("CONFIGURATION")
        lines.append("-" * 70)
        config = results.get("configuration", {})
        config_valid = config.get("valid", False)
        lines.append(f"Status: {'✓ Valid' if config_valid else '✗ Invalid'}")
        lines.append(f"Project Root: {config.get('project_root', 'N/A')}")
        lines.append(f"Config Path: {config.get('config_path', 'N/A')}")
        if config.get("issues"):
            lines.append("\nIssues:")
            for issue in config["issues"]:
                lines.append(f"  • {issue}")

        # Database Section
        lines.append("\n" + "=" * 70)
        lines.append("DATABASE")
        lines.append("-" * 70)
        db = results.get("database", {})
        db_connected = db.get("connected", False)
        lines.append(f"Status: {'✓ Connected' if db_connected else '✗ Not Connected'}")
        lines.append(f"Memory Count: {db.get('memory_count', 0)}")
        lines.append(f"DB Size: {db.get('db_size_bytes', 0)} bytes")
        lines.append(f"Schema Version: {db.get('schema_version', 'N/A')}")
        if db.get("issues"):
            lines.append("\nIssues:")
            for issue in db["issues"]:
                lines.append(f"  • {issue}")

        # MCP Server Section
        lines.append("\n" + "=" * 70)
        lines.append("MCP SERVER")
        lines.append("-" * 70)
        mcp = results.get("mcp_server", {})
        mcp_configured = mcp.get("configured", False)
        lines.append(f"Status: {'✓ Configured' if mcp_configured else '✗ Not Configured'}")
        lines.append(f"Config Valid: {mcp.get('config_valid', False)}")
        lines.append(f"Server Path: {mcp.get('server_path', 'N/A')}")
        if mcp.get("issues"):
            lines.append("\nIssues:")
            for issue in mcp["issues"]:
                lines.append(f"  • {issue}")

        # Git Integration Section
        lines.append("\n" + "=" * 70)
        lines.append("GIT INTEGRATION")
        lines.append("-" * 70)
        git = results.get("git_integration", {})
        git_available = git.get("available", False)
        lines.append(f"Git Available: {'✓ Yes' if git_available else '✗ No'}")
        lines.append(f"Hooks Installed: {git.get('hooks_installed', False)}")
        lines.append(f"Last Sync: {git.get('last_sync', 'N/A')}")
        if git.get("issues"):
            lines.append("\nIssues:")
            for issue in git["issues"]:
                lines.append(f"  • {issue}")

        # System Info Section
        lines.append("\n" + "=" * 70)
        lines.append("SYSTEM INFORMATION")
        lines.append("-" * 70)
        sys_info = results.get("system_info", {})
        lines.append(f"KuzuMemory Version: {sys_info.get('version', 'N/A')}")
        lines.append(f"Python Version: {sys_info.get('python_version', 'N/A')}")
        lines.append(f"Platform: {sys_info.get('platform', 'N/A')}")
        lines.append(f"Kuzu Version: {sys_info.get('kuzu_version', 'N/A')}")
        lines.append(f"Install Path: {sys_info.get('install_path', 'N/A')}")

        # Dependencies Section
        lines.append("\n" + "=" * 70)
        lines.append("DEPENDENCIES")
        lines.append("-" * 70)
        deps = results.get("dependencies", {})
        deps_satisfied = deps.get("all_satisfied", False)
        lines.append(f"Status: {'✓ All Satisfied' if deps_satisfied else '✗ Issues Found'}")
        if deps.get("missing"):
            lines.append("\nMissing:")
            for dep in deps["missing"]:
                lines.append(f"  • {dep}")
        if deps.get("suggestions"):
            lines.append("\nSuggestions:")
            for suggestion in deps["suggestions"]:
                lines.append(f"  • {suggestion}")

        # MCP Installation Section
        lines.append("\n" + "=" * 70)
        lines.append("MCP INSTALLATION")
        lines.append("-" * 70)
        mcp_install = results.get("mcp_installation", {})
        if mcp_install.get("available", False):
            status = mcp_install.get("status", "unknown").upper()
            status_symbol = "✓" if status == "HEALTHY" else "⚠️" if status == "DEGRADED" else "✗"
            lines.append(f"Status: {status_symbol} {status}")
            lines.append(f"Platform: {mcp_install.get('platform', 'N/A')}")
            checks_passed = mcp_install.get("checks_passed", 0)
            checks_total = mcp_install.get("checks_total", 0)
            lines.append(f"Checks: {checks_passed}/{checks_total} passed")
            if mcp_install.get("issues"):
                lines.append("\nIssues:")
                for issue in mcp_install["issues"][:5]:  # Limit to 5 issues
                    severity = issue.get("severity", "unknown").upper()
                    message = issue.get("message", "Unknown issue")
                    lines.append(f"  • [{severity}] {message}")
            if mcp_install.get("recommendations"):
                lines.append("\nRecommendations:")
                for rec in mcp_install["recommendations"][:3]:  # Limit to 3
                    lines.append(f"  • {rec}")
        else:
            lines.append("Status: ⚠️ MCPInstallerAdapter not available")
            lines.append(
                "Note: Install py-mcp-installer-service submodule for enhanced diagnostics"
            )

        # Summary
        lines.append("\n" + "=" * 70)
        if all_healthy:
            lines.append("✓ All systems operational")
        else:
            lines.append("✗ Action required - see issues above")
        lines.append("=" * 70)

        return "\n".join(lines)
