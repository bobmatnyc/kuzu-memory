"""
MCP Diagnostic Framework.

Comprehensive diagnostic tools for MCP server configuration, connection,
tool discovery, and performance validation with automated troubleshooting.
"""

import asyncio
import json
import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .connection_tester import MCPConnectionTester

logger = logging.getLogger(__name__)


class DiagnosticSeverity(Enum):
    """Diagnostic result severity levels."""

    CRITICAL = "critical"  # System unusable, requires immediate fix
    ERROR = "error"  # Feature broken, requires fix
    WARNING = "warning"  # Degraded functionality, should fix
    INFO = "info"  # Informational, no action needed
    SUCCESS = "success"  # All checks passed


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""

    check_name: str
    success: bool
    severity: DiagnosticSeverity
    message: str
    error: str | None = None
    fix_suggestion: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "check_name": self.check_name,
            "success": self.success,
            "severity": self.severity.value,
            "message": self.message,
            "error": self.error,
            "fix_suggestion": self.fix_suggestion,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }


@dataclass
class DiagnosticReport:
    """Complete diagnostic report with all check results."""

    report_name: str
    timestamp: str
    platform: str
    results: list[DiagnosticResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def passed(self) -> int:
        """Count of passed checks."""
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        """Count of failed checks."""
        return sum(1 for r in self.results if not r.success)

    @property
    def total(self) -> int:
        """Total number of checks."""
        return len(self.results)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    @property
    def has_critical_errors(self) -> bool:
        """Check if any critical errors exist."""
        return any(
            r.severity == DiagnosticSeverity.CRITICAL and not r.success
            for r in self.results
        )

    def add_result(self, result: DiagnosticResult) -> None:
        """Add a diagnostic result to the report."""
        self.results.append(result)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "report_name": self.report_name,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "success_rate": self.success_rate,
            "has_critical_errors": self.has_critical_errors,
            "total_duration_ms": self.total_duration_ms,
            "results": [r.to_dict() for r in self.results],
        }


class MCPDiagnostics:
    """Comprehensive MCP diagnostic and troubleshooting framework."""

    def __init__(
        self,
        project_root: Path | None = None,
        verbose: bool = False,
    ):
        """
        Initialize MCP diagnostics.

        Args:
            project_root: Project root directory
            verbose: Enable verbose output
        """
        self.project_root = project_root or Path.cwd()
        self.verbose = verbose
        self.claude_config_path = self._get_claude_config_path()

    def _get_claude_config_path(self) -> Path:
        """Get the Claude Desktop configuration file path."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        elif system == "Linux":
            xdg_config = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
            return Path(xdg_config) / "Claude" / "claude_desktop_config.json"
        elif system == "Windows":
            appdata = os.getenv("APPDATA")
            if appdata:
                return Path(appdata) / "Claude" / "claude_desktop_config.json"
            return (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Claude"
                / "claude_desktop_config.json"
            )
        else:
            raise OSError(f"Unsupported operating system: {system}")

    async def check_configuration(self) -> list[DiagnosticResult]:
        """
        Check MCP configuration validity.

        Returns:
            List of diagnostic results for configuration checks
        """
        results = []

        # Check Claude Desktop config exists
        start = time.time()
        if self.claude_config_path.exists():
            results.append(
                DiagnosticResult(
                    check_name="claude_config_exists",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"Claude Desktop config found at {self.claude_config_path}",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="claude_config_exists",
                    success=False,
                    severity=DiagnosticSeverity.CRITICAL,
                    message="Claude Desktop config not found",
                    error=f"File does not exist: {self.claude_config_path}",
                    fix_suggestion="Run: python scripts/install-claude-desktop.py",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
            return results  # Cannot proceed without config

        # Check config is valid JSON
        start = time.time()
        try:
            with open(self.claude_config_path) as f:
                config = json.load(f)

            results.append(
                DiagnosticResult(
                    check_name="claude_config_valid_json",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="Claude Desktop config is valid JSON",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        except json.JSONDecodeError as e:
            results.append(
                DiagnosticResult(
                    check_name="claude_config_valid_json",
                    success=False,
                    severity=DiagnosticSeverity.CRITICAL,
                    message="Claude Desktop config contains invalid JSON",
                    error=str(e),
                    fix_suggestion=(
                        "Fix JSON syntax errors in config file or restore from backup"
                    ),
                    duration_ms=(time.time() - start) * 1000,
                )
            )
            return results  # Cannot proceed with invalid JSON

        # Check kuzu-memory in mcpServers
        start = time.time()
        if "mcpServers" in config and "kuzu-memory" in config["mcpServers"]:
            results.append(
                DiagnosticResult(
                    check_name="kuzu_memory_configured",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="kuzu-memory is configured in Claude Desktop",
                    metadata={"config": config["mcpServers"]["kuzu-memory"]},
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="kuzu_memory_configured",
                    success=False,
                    severity=DiagnosticSeverity.CRITICAL,
                    message="kuzu-memory not found in Claude Desktop config",
                    error="mcpServers section missing or kuzu-memory not configured",
                    fix_suggestion="Run: python scripts/install-claude-desktop.py",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
            return results  # Cannot proceed without kuzu-memory config

        # Check environment variables
        start = time.time()
        env_vars = config["mcpServers"]["kuzu-memory"].get("env", {})
        required_vars = ["KUZU_MEMORY_DB", "KUZU_MEMORY_MODE"]
        missing_vars = [var for var in required_vars if var not in env_vars]

        if not missing_vars:
            results.append(
                DiagnosticResult(
                    check_name="environment_variables",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="All required environment variables configured",
                    metadata={"env_vars": env_vars},
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="environment_variables",
                    success=False,
                    severity=DiagnosticSeverity.WARNING,
                    message="Missing environment variables",
                    error=f"Missing: {', '.join(missing_vars)}",
                    fix_suggestion=(
                        "Add missing variables to config or "
                        "re-run: python scripts/install-claude-desktop.py --force"
                    ),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # Check database directory
        start = time.time()
        db_path_str = env_vars.get("KUZU_MEMORY_DB", "")
        if db_path_str:
            db_path = Path(db_path_str)
            db_dir = db_path.parent

            if db_dir.exists():
                # Check directory is writable
                if os.access(db_dir, os.W_OK):
                    results.append(
                        DiagnosticResult(
                            check_name="database_directory",
                            success=True,
                            severity=DiagnosticSeverity.SUCCESS,
                            message=f"Database directory accessible: {db_dir}",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )
                else:
                    results.append(
                        DiagnosticResult(
                            check_name="database_directory",
                            success=False,
                            severity=DiagnosticSeverity.ERROR,
                            message="Database directory not writable",
                            error=f"No write permission for {db_dir}",
                            fix_suggestion=f"Run: chmod u+w {db_dir}",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="database_directory",
                        success=False,
                        severity=DiagnosticSeverity.WARNING,
                        message="Database directory does not exist",
                        error=f"Directory not found: {db_dir}",
                        fix_suggestion=f"Run: mkdir -p {db_dir}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )

        return results

    async def check_connection(self) -> list[DiagnosticResult]:
        """
        Check MCP server connection and protocol.

        Returns:
            List of diagnostic results for connection checks
        """
        results = []

        # Use MCPConnectionTester for comprehensive connection testing
        tester = MCPConnectionTester(project_root=self.project_root)

        try:
            # Start server
            start_result = await tester.start_server()
            results.append(
                DiagnosticResult(
                    check_name="server_startup",
                    success=start_result.success,
                    severity=(
                        DiagnosticSeverity.SUCCESS
                        if start_result.success
                        else DiagnosticSeverity.CRITICAL
                    ),
                    message=start_result.message,
                    error=start_result.error,
                    fix_suggestion=(
                        "Check server installation: pip show kuzu-memory"
                        if not start_result.success
                        else None
                    ),
                    duration_ms=start_result.duration_ms,
                )
            )

            if not start_result.success:
                return results  # Cannot proceed without server

            # Test stdio connection
            stdio_result = await tester.test_stdio_connection()
            results.append(
                DiagnosticResult(
                    check_name="stdio_connection",
                    success=stdio_result.success,
                    severity=(
                        DiagnosticSeverity.SUCCESS
                        if stdio_result.success
                        else DiagnosticSeverity.ERROR
                    ),
                    message=stdio_result.message,
                    error=stdio_result.error,
                    fix_suggestion=(
                        "Check server logs and process status"
                        if not stdio_result.success
                        else None
                    ),
                    duration_ms=stdio_result.duration_ms,
                )
            )

            # Test protocol initialization
            init_result = await tester.test_protocol_initialization()
            results.append(
                DiagnosticResult(
                    check_name="protocol_initialization",
                    success=init_result.success,
                    severity=(
                        DiagnosticSeverity.SUCCESS
                        if init_result.success
                        else DiagnosticSeverity.ERROR
                    ),
                    message=init_result.message,
                    error=init_result.error,
                    fix_suggestion=(
                        "Check MCP protocol version compatibility"
                        if not init_result.success
                        else None
                    ),
                    metadata=init_result.metadata,
                    duration_ms=init_result.duration_ms,
                )
            )

            # Validate JSON-RPC compliance
            compliance_result = await tester.validate_jsonrpc_compliance()
            results.append(
                DiagnosticResult(
                    check_name="jsonrpc_compliance",
                    success=compliance_result.success,
                    severity=(
                        DiagnosticSeverity.SUCCESS
                        if compliance_result.success
                        else DiagnosticSeverity.WARNING
                    ),
                    message=compliance_result.message,
                    error=compliance_result.error,
                    metadata=compliance_result.metadata,
                    duration_ms=compliance_result.duration_ms,
                )
            )

        finally:
            # Always stop server
            await tester.stop_server()

        return results

    async def check_tools(self) -> list[DiagnosticResult]:
        """
        Check MCP tool discovery and execution.

        Returns:
            List of diagnostic results for tool checks
        """
        results = []

        # Use MCPConnectionTester to establish connection
        tester = MCPConnectionTester(project_root=self.project_root)

        try:
            # Start server
            start_result = await tester.start_server()
            if not start_result.success:
                results.append(
                    DiagnosticResult(
                        check_name="tools_discovery",
                        success=False,
                        severity=DiagnosticSeverity.CRITICAL,
                        message="Cannot discover tools - server not running",
                        error=start_result.error,
                        duration_ms=start_result.duration_ms,
                    )
                )
                return results

            # Initialize protocol
            init_msg = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1,
                "params": {"protocolVersion": "2024-11-05"},
            }
            await tester._send_request(init_msg)

            # Discover tools
            start = time.time()
            tools_msg = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}

            try:
                response = await tester._send_request(tools_msg)
                duration = (time.time() - start) * 1000

                if response and "result" in response:
                    tools = response["result"].get("tools", [])
                    results.append(
                        DiagnosticResult(
                            check_name="tools_discovery",
                            success=True,
                            severity=DiagnosticSeverity.SUCCESS,
                            message=f"Discovered {len(tools)} tools",
                            metadata={"tools": [t.get("name") for t in tools]},
                            duration_ms=duration,
                        )
                    )

                    # Test each tool execution
                    for tool in tools[:3]:  # Test first 3 tools
                        tool_name = tool.get("name", "unknown")
                        start = time.time()

                        # Create minimal valid parameters based on tool
                        test_params = {}
                        if tool_name == "kuzu_enhance":
                            test_params = {"prompt": "test"}
                        elif tool_name == "kuzu_recall":
                            test_params = {"query": "test"}
                        elif tool_name == "kuzu_stats":
                            test_params = {}

                        tool_msg = {
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "id": 3,
                            "params": {"name": tool_name, "arguments": test_params},
                        }

                        try:
                            tool_response = await asyncio.wait_for(
                                tester._send_request(tool_msg), timeout=5.0
                            )
                            tool_duration = (time.time() - start) * 1000

                            if tool_response and "result" in tool_response:
                                results.append(
                                    DiagnosticResult(
                                        check_name=f"tool_execution_{tool_name}",
                                        success=True,
                                        severity=DiagnosticSeverity.SUCCESS,
                                        message=f"Tool {tool_name} executed successfully",
                                        duration_ms=tool_duration,
                                    )
                                )
                            else:
                                error_msg = (
                                    tool_response.get("error", {}).get(
                                        "message", "Unknown error"
                                    )
                                    if tool_response
                                    else "No response"
                                )
                                results.append(
                                    DiagnosticResult(
                                        check_name=f"tool_execution_{tool_name}",
                                        success=False,
                                        severity=DiagnosticSeverity.WARNING,
                                        message=f"Tool {tool_name} execution failed",
                                        error=error_msg,
                                        duration_ms=tool_duration,
                                    )
                                )
                        except TimeoutError:
                            results.append(
                                DiagnosticResult(
                                    check_name=f"tool_execution_{tool_name}",
                                    success=False,
                                    severity=DiagnosticSeverity.WARNING,
                                    message=f"Tool {tool_name} execution timeout",
                                    error="Tool took longer than 5 seconds",
                                    duration_ms=(time.time() - start) * 1000,
                                )
                            )
                else:
                    results.append(
                        DiagnosticResult(
                            check_name="tools_discovery",
                            success=False,
                            severity=DiagnosticSeverity.ERROR,
                            message="Failed to discover tools",
                            error=(
                                response.get("error", "Unknown error")
                                if response
                                else "No response"
                            ),
                            duration_ms=duration,
                        )
                    )

            except Exception as e:
                results.append(
                    DiagnosticResult(
                        check_name="tools_discovery",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Tool discovery error",
                        error=str(e),
                        duration_ms=(time.time() - start) * 1000,
                    )
                )

        finally:
            await tester.stop_server()

        return results

    async def check_performance(self) -> list[DiagnosticResult]:
        """
        Check MCP server performance metrics.

        Returns:
            List of diagnostic results for performance checks
        """
        results = []

        tester = MCPConnectionTester(project_root=self.project_root, timeout=10.0)

        try:
            # Start server and measure startup time
            start = time.time()
            start_result = await tester.start_server()
            startup_time = (time.time() - start) * 1000

            if startup_time < 1000:  # < 1 second
                severity = DiagnosticSeverity.SUCCESS
            elif startup_time < 3000:  # < 3 seconds
                severity = DiagnosticSeverity.INFO
            else:
                severity = DiagnosticSeverity.WARNING

            results.append(
                DiagnosticResult(
                    check_name="startup_performance",
                    success=start_result.success,
                    severity=severity,
                    message=f"Server startup took {startup_time:.2f}ms",
                    metadata={"startup_time_ms": startup_time},
                    duration_ms=startup_time,
                )
            )

            if not start_result.success:
                return results

            # Measure protocol initialization latency
            start = time.time()
            init_msg = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1,
                "params": {"protocolVersion": "2024-11-05"},
            }
            await tester._send_request(init_msg)
            init_latency = (time.time() - start) * 1000

            if init_latency < 100:
                severity = DiagnosticSeverity.SUCCESS
            elif init_latency < 500:
                severity = DiagnosticSeverity.INFO
            else:
                severity = DiagnosticSeverity.WARNING

            results.append(
                DiagnosticResult(
                    check_name="protocol_latency",
                    success=True,
                    severity=severity,
                    message=f"Protocol initialization latency: {init_latency:.2f}ms",
                    metadata={"latency_ms": init_latency},
                    duration_ms=init_latency,
                )
            )

            # Test throughput with multiple rapid requests
            start = time.time()
            request_count = 10
            for i in range(request_count):
                msg = {"jsonrpc": "2.0", "method": "ping", "id": i + 2}
                await tester._send_request(msg)
            throughput_time = (time.time() - start) * 1000
            requests_per_second = (request_count / throughput_time) * 1000

            results.append(
                DiagnosticResult(
                    check_name="request_throughput",
                    success=True,
                    severity=DiagnosticSeverity.INFO,
                    message=(f"Throughput: {requests_per_second:.2f} requests/second"),
                    metadata={
                        "requests_per_second": requests_per_second,
                        "total_time_ms": throughput_time,
                    },
                    duration_ms=throughput_time,
                )
            )

        finally:
            await tester.stop_server()

        return results

    async def auto_fix_configuration(self) -> DiagnosticResult:
        """
        Attempt to automatically fix configuration issues.

        Returns:
            Diagnostic result for auto-fix attempt
        """
        start = time.time()

        try:
            # Run the installer script
            result = subprocess.run(
                ["python", "scripts/install-claude-desktop.py", "--force"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            duration = (time.time() - start) * 1000

            if result.returncode == 0:
                return DiagnosticResult(
                    check_name="auto_fix_configuration",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="Configuration auto-fixed successfully",
                    metadata={"output": result.stdout},
                    duration_ms=duration,
                )
            else:
                return DiagnosticResult(
                    check_name="auto_fix_configuration",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Auto-fix failed",
                    error=result.stderr,
                    duration_ms=duration,
                )

        except Exception as e:
            return DiagnosticResult(
                check_name="auto_fix_configuration",
                success=False,
                severity=DiagnosticSeverity.ERROR,
                message="Auto-fix error",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def auto_fix_database(self) -> DiagnosticResult:
        """
        Attempt to automatically fix database issues.

        Returns:
            Diagnostic result for database auto-fix attempt
        """
        start = time.time()

        try:
            # Reinitialize database
            result = subprocess.run(
                ["kuzu-memory", "init", "--force"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            duration = (time.time() - start) * 1000

            if result.returncode == 0:
                return DiagnosticResult(
                    check_name="auto_fix_database",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="Database reinitialized successfully",
                    duration_ms=duration,
                )
            else:
                return DiagnosticResult(
                    check_name="auto_fix_database",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Database auto-fix failed",
                    error=result.stderr,
                    duration_ms=duration,
                )

        except Exception as e:
            return DiagnosticResult(
                check_name="auto_fix_database",
                success=False,
                severity=DiagnosticSeverity.ERROR,
                message="Database auto-fix error",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def run_full_diagnostics(self, auto_fix: bool = False) -> DiagnosticReport:
        """
        Run complete diagnostic suite.

        Args:
            auto_fix: Attempt to automatically fix issues

        Returns:
            Complete diagnostic report
        """
        start_time = time.time()
        report = DiagnosticReport(
            report_name="MCP Full Diagnostics",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            platform=platform.system(),
        )

        # Run all diagnostic checks
        config_results = await self.check_configuration()
        for result in config_results:
            report.add_result(result)

        # Only run connection checks if config is valid
        if all(r.success for r in config_results):
            connection_results = await self.check_connection()
            for result in connection_results:
                report.add_result(result)

            # Only run tool checks if connection is valid
            if all(r.success for r in connection_results):
                tool_results = await self.check_tools()
                for result in tool_results:
                    report.add_result(result)

                perf_results = await self.check_performance()
                for result in perf_results:
                    report.add_result(result)

        # Auto-fix if requested and there are failures
        if auto_fix and report.failed > 0:
            if report.has_critical_errors:
                fix_result = await self.auto_fix_configuration()
                report.add_result(fix_result)

                if fix_result.success:
                    # Re-run configuration checks
                    config_results = await self.check_configuration()
                    for result in config_results:
                        report.add_result(result)

        report.total_duration_ms = (time.time() - start_time) * 1000
        return report

    def generate_text_report(self, report: DiagnosticReport) -> str:
        """
        Generate human-readable text report.

        Args:
            report: Diagnostic report

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"  {report.report_name}")
        lines.append("=" * 70)
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append(f"Platform: {report.platform}")
        lines.append(
            f"Results: {report.passed}/{report.total} passed "
            f"({report.success_rate:.1f}%)"
        )
        lines.append(f"Duration: {report.total_duration_ms:.2f}ms")
        lines.append("=" * 70)
        lines.append("")

        # Group results by severity
        for severity in DiagnosticSeverity:
            severity_results = [r for r in report.results if r.severity == severity]
            if not severity_results:
                continue

            lines.append(f"\n{severity.value.upper()} ({len(severity_results)}):")
            lines.append("-" * 70)

            for result in severity_results:
                status = "✓" if result.success else "✗"
                lines.append(f"\n{status} {result.check_name}")
                lines.append(f"  {result.message}")
                if result.error:
                    lines.append(f"  Error: {result.error}")
                if result.fix_suggestion:
                    lines.append(f"  Fix: {result.fix_suggestion}")
                lines.append(f"  Duration: {result.duration_ms:.2f}ms")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def generate_html_report(self, report: DiagnosticReport) -> str:
        """
        Generate HTML diagnostic report.

        Args:
            report: Diagnostic report

        Returns:
            HTML formatted report
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{report.report_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .result {{ margin: 10px 0; padding: 10px; border-left: 4px solid; }}
        .success {{ border-color: #28a745; background: #d4edda; }}
        .error {{ border-color: #dc3545; background: #f8d7da; }}
        .warning {{ border-color: #ffc107; background: #fff3cd; }}
        .info {{ border-color: #17a2b8; background: #d1ecf1; }}
        .critical {{ border-color: #dc3545; background: #f8d7da; font-weight: bold; }}
        .metadata {{ font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <h1>{report.report_name}</h1>
    <div class="summary">
        <p><strong>Timestamp:</strong> {report.timestamp}</p>
        <p><strong>Platform:</strong> {report.platform}</p>
        <p><strong>Results:</strong> {report.passed}/{report.total} passed ({report.success_rate:.1f}%)</p>
        <p><strong>Duration:</strong> {report.total_duration_ms:.2f}ms</p>
    </div>
    <h2>Diagnostic Results</h2>
"""

        for result in report.results:
            status = "✓" if result.success else "✗"
            severity_class = result.severity.value
            html += f"""
    <div class="result {severity_class}">
        <h3>{status} {result.check_name}</h3>
        <p>{result.message}</p>
"""
            if result.error:
                html += f"<p><strong>Error:</strong> {result.error}</p>\n"
            if result.fix_suggestion:
                html += f"<p><strong>Fix:</strong> {result.fix_suggestion}</p>\n"
            html += f"<p class='metadata'>Duration: {result.duration_ms:.2f}ms</p>\n"
            html += "    </div>\n"

        html += """
</body>
</html>
"""
        return html
