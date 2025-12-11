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
            r.severity == DiagnosticSeverity.CRITICAL and not r.success for r in self.results
        )

    @property
    def actionable_failures(self) -> int:
        """Count failures that require action (CRITICAL, ERROR, WARNING only, excluding INFO)."""
        return sum(
            1
            for r in self.results
            if not r.success
            and r.severity
            in (
                DiagnosticSeverity.CRITICAL,
                DiagnosticSeverity.ERROR,
                DiagnosticSeverity.WARNING,
            )
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
    """
    PROJECT-LEVEL MCP diagnostic and troubleshooting framework.

    Focuses exclusively on project-scoped diagnostics:
    - Project memory database (kuzu-memories/)
    - Claude Code MCP configuration (.claude/settings.local.json)
    - Claude Code hooks (if configured)

    Does NOT check user-level configurations:
    - Claude Desktop (use install commands instead)
    - Global home directory configurations
    """

    def __init__(
        self,
        project_root: Path | None = None,
        verbose: bool = False,
    ) -> None:
        """
        Initialize MCP diagnostics.

        Args:
            project_root: Project root directory
            verbose: Enable verbose output
        """
        self.project_root = project_root or Path.cwd()
        self.verbose = verbose
        # PROJECT-LEVEL CONFIG ONLY
        self.claude_code_config_path = self.project_root / ".claude" / "settings.local.json"
        self.memory_db_path = self.project_root / "kuzu-memories"

    async def check_configuration(self) -> list[DiagnosticResult]:
        """
        Check PROJECT-LEVEL MCP configuration validity.

        Checks ONLY:
        - Project memory database directory (kuzu-memories/)
        - Claude Code MCP config (.claude/settings.local.json)
        - Claude Code hooks (if configured)

        Does NOT check Claude Desktop (user-level) configuration.

        Returns:
            List of diagnostic results for configuration checks
        """
        results = []

        # 1. CHECK PROJECT MEMORY DATABASE DIRECTORY
        start = time.time()
        if self.memory_db_path.exists():
            # Check directory is accessible and writable
            if os.access(self.memory_db_path, os.R_OK | os.W_OK):
                results.append(
                    DiagnosticResult(
                        check_name="memory_database_directory",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message=f"Memory database directory accessible: {self.memory_db_path}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="memory_database_directory",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Memory database directory not accessible",
                        error=f"No read/write permission for {self.memory_db_path}",
                        fix_suggestion=f"Run: chmod u+rw {self.memory_db_path}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        else:
            results.append(
                DiagnosticResult(
                    check_name="memory_database_directory",
                    success=False,
                    severity=DiagnosticSeverity.WARNING,
                    message="Memory database directory does not exist",
                    error=f"Directory not found: {self.memory_db_path}",
                    fix_suggestion="Run: kuzu-memory init",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 2. CHECK DATABASE FILE (from kuzu-memory init)
        start = time.time()
        db_file_path = self.memory_db_path / "memories.db"
        if db_file_path.exists():
            results.append(
                DiagnosticResult(
                    check_name="memory_database_file",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"Database file exists: {db_file_path}",
                    metadata={"size_bytes": db_file_path.stat().st_size},
                    duration_ms=(time.time() - start) * 1000,
                )
            )

            # 3. VERIFY DATABASE CAN BE OPENED
            start = time.time()
            try:
                # Import here to avoid circular dependencies
                from ...core.memory import KuzuMemory

                with KuzuMemory(db_path=db_file_path):
                    # Try opening database to verify it is functional
                    pass
                results.append(
                    DiagnosticResult(
                        check_name="memory_database_initialization",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="Database can be opened and is properly initialized",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            except Exception as e:
                results.append(
                    DiagnosticResult(
                        check_name="memory_database_initialization",
                        success=False,
                        severity=DiagnosticSeverity.CRITICAL,
                        message="Database exists but cannot be opened",
                        error=str(e),
                        fix_suggestion="Run: kuzu-memory init --force",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        else:
            results.append(
                DiagnosticResult(
                    check_name="memory_database_file",
                    success=False,
                    severity=DiagnosticSeverity.CRITICAL,
                    message="Database file does not exist",
                    error=f"File not found: {db_file_path}",
                    fix_suggestion="Run: kuzu-memory init",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 4. CHECK README.md (from kuzu-memory init)
        start = time.time()
        readme_path = self.memory_db_path / "README.md"
        if readme_path.exists():
            results.append(
                DiagnosticResult(
                    check_name="memory_readme_file",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"README.md exists: {readme_path}",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="memory_readme_file",
                    success=False,
                    severity=DiagnosticSeverity.WARNING,
                    message="README.md missing from kuzu-memories directory",
                    error=f"File not found: {readme_path}",
                    fix_suggestion="Run: kuzu-memory init --force",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 5. CHECK project_info.md (from kuzu-memory init)
        start = time.time()
        project_info_path = self.memory_db_path / "project_info.md"
        if project_info_path.exists():
            results.append(
                DiagnosticResult(
                    check_name="project_info_file",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"project_info.md exists: {project_info_path}",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="project_info_file",
                    success=False,
                    severity=DiagnosticSeverity.WARNING,
                    message="project_info.md missing from kuzu-memories directory",
                    error=f"File not found: {project_info_path}",
                    fix_suggestion="Run: kuzu-memory init --force",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 6. CHECK .claude/kuzu-memory.sh (from install add claude-code)
        start = time.time()
        hook_script_path = self.project_root / ".claude" / "kuzu-memory.sh"
        if hook_script_path.exists():
            # Check if executable
            if os.access(hook_script_path, os.X_OK):
                results.append(
                    DiagnosticResult(
                        check_name="claude_hook_script",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message=f"Hook script exists and is executable: {hook_script_path}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="claude_hook_script",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Hook script exists but is not executable",
                        error=f"Missing execute permission: {hook_script_path}",
                        fix_suggestion=f"Run: chmod +x {hook_script_path}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        else:
            results.append(
                DiagnosticResult(
                    check_name="claude_hook_script",
                    success=False,
                    severity=DiagnosticSeverity.INFO,
                    message="Claude hook script not found (optional for Claude Code integration)",
                    error=f"File not found: {hook_script_path}",
                    fix_suggestion="Optional: Run: kuzu-memory install add claude-code",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 7. CHECK CLAUDE.md (from install add claude-code) - INFO severity (optional)
        start = time.time()
        claude_md_path = self.project_root / "CLAUDE.md"
        if claude_md_path.exists():
            results.append(
                DiagnosticResult(
                    check_name="claude_instructions_file",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"CLAUDE.md exists: {claude_md_path}",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="claude_instructions_file",
                    success=False,
                    severity=DiagnosticSeverity.INFO,
                    message="CLAUDE.md not found (optional)",
                    error=f"File not found: {claude_md_path}",
                    fix_suggestion="Optional: Run: kuzu-memory install add claude-code to create instructions file",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 8. CHECK .claude-mpm/config.json (from install add claude-code)
        start = time.time()
        claude_mpm_config_path = self.project_root / ".claude-mpm" / "config.json"
        if claude_mpm_config_path.exists():
            try:
                with open(claude_mpm_config_path) as f:
                    json.load(f)
                results.append(
                    DiagnosticResult(
                        check_name="claude_mpm_config",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message=f"Claude MPM config is valid: {claude_mpm_config_path}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            except json.JSONDecodeError as e:
                results.append(
                    DiagnosticResult(
                        check_name="claude_mpm_config",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Claude MPM config contains invalid JSON",
                        error=str(e),
                        fix_suggestion="Run: kuzu-memory install add claude-code --force",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        else:
            results.append(
                DiagnosticResult(
                    check_name="claude_mpm_config",
                    success=False,
                    severity=DiagnosticSeverity.INFO,
                    message="Claude MPM config not found (optional for Claude Code integration)",
                    error=f"File not found: {claude_mpm_config_path}",
                    fix_suggestion="Optional: Run: kuzu-memory install add claude-code",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 9. CHECK .kuzu-memory/config.yaml (from install add claude-code)
        start = time.time()
        kuzu_config_path = self.project_root / ".kuzu-memory" / "config.yaml"
        if kuzu_config_path.exists():
            results.append(
                DiagnosticResult(
                    check_name="kuzu_memory_config",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"KuzuMemory config exists: {kuzu_config_path}",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="kuzu_memory_config",
                    success=False,
                    severity=DiagnosticSeverity.INFO,
                    message="KuzuMemory config not found (optional for Claude Code integration)",
                    error=f"File not found: {kuzu_config_path}",
                    fix_suggestion="Optional: Run: kuzu-memory install add claude-code",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 10. CHECK CLAUDE CODE MCP CONFIG (if exists)
        start = time.time()
        if self.claude_code_config_path.exists():
            try:
                with open(self.claude_code_config_path) as f:
                    config = json.load(f)

                results.append(
                    DiagnosticResult(
                        check_name="claude_code_config_valid",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message=f"Claude Code config is valid JSON: {self.claude_code_config_path}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )

                # Check if kuzu-memory MCP server is configured
                start = time.time()
                if "mcpServers" in config and "kuzu-memory" in config["mcpServers"]:
                    mcp_config = config["mcpServers"]["kuzu-memory"]
                    results.append(
                        DiagnosticResult(
                            check_name="mcp_server_configured",
                            success=True,
                            severity=DiagnosticSeverity.SUCCESS,
                            message="kuzu-memory MCP server configured in Claude Code",
                            metadata={"config": mcp_config},
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )

                    # Check environment variables in MCP config
                    start = time.time()
                    env_vars = mcp_config.get("env", {})
                    required_vars = ["KUZU_MEMORY_DB"]
                    missing_vars = [var for var in required_vars if var not in env_vars]

                    if not missing_vars:
                        results.append(
                            DiagnosticResult(
                                check_name="mcp_environment_variables",
                                success=True,
                                severity=DiagnosticSeverity.SUCCESS,
                                message="Required MCP environment variables configured",
                                metadata={"env_vars": env_vars},
                                duration_ms=(time.time() - start) * 1000,
                            )
                        )
                    else:
                        results.append(
                            DiagnosticResult(
                                check_name="mcp_environment_variables",
                                success=False,
                                severity=DiagnosticSeverity.WARNING,
                                message="Missing MCP environment variables",
                                error=f"Missing: {', '.join(missing_vars)}",
                                fix_suggestion="Run: kuzu-memory install add claude-code --force",
                                duration_ms=(time.time() - start) * 1000,
                            )
                        )
                else:
                    results.append(
                        DiagnosticResult(
                            check_name="mcp_server_configured",
                            success=False,
                            severity=DiagnosticSeverity.INFO,
                            message="kuzu-memory MCP server not configured in Claude Code",
                            error="mcpServers section missing or kuzu-memory not configured",
                            fix_suggestion="Run: kuzu-memory install add claude-code",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )

                # 3. CHECK CLAUDE CODE HOOKS (if configured)
                start = time.time()
                if "hooks" in config:
                    hooks = config["hooks"]
                    # Check for correct camelCase event names
                    has_enhance_hook = "UserPromptSubmit" in hooks
                    has_learn_hook = "Stop" in hooks
                    # Check for old incorrect snake_case event names
                    has_old_enhance = "user_prompt_submit" in hooks
                    has_old_learn = "assistant_response" in hooks

                    if has_enhance_hook or has_learn_hook:
                        hook_info = []
                        if has_enhance_hook:
                            hook_info.append("UserPromptSubmit (enhance)")
                        if has_learn_hook:
                            hook_info.append("Stop (learn)")

                        results.append(
                            DiagnosticResult(
                                check_name="claude_code_hooks",
                                success=True,
                                severity=DiagnosticSeverity.SUCCESS,
                                message=f"Claude Code hooks configured: {', '.join(hook_info)}",
                                metadata={"hooks": hooks},
                                duration_ms=(time.time() - start) * 1000,
                            )
                        )
                    elif has_old_enhance or has_old_learn:
                        # Old incorrect event names detected
                        old_hooks = []
                        if has_old_enhance:
                            old_hooks.append("user_prompt_submit")
                        if has_old_learn:
                            old_hooks.append("assistant_response")

                        results.append(
                            DiagnosticResult(
                                check_name="claude_code_hooks",
                                success=False,
                                severity=DiagnosticSeverity.ERROR,
                                message=f"Incorrect hook event names detected: {', '.join(old_hooks)}",
                                error="Using snake_case event names instead of camelCase",
                                fix_suggestion="Run: kuzu-memory install add claude-code --force to update hook event names",
                                duration_ms=(time.time() - start) * 1000,
                            )
                        )
                    else:
                        results.append(
                            DiagnosticResult(
                                check_name="claude_code_hooks",
                                success=False,
                                severity=DiagnosticSeverity.INFO,
                                message="No Claude Code hooks configured",
                                fix_suggestion="Run: kuzu-memory install add claude-code to enable hooks",
                                duration_ms=(time.time() - start) * 1000,
                            )
                        )

            except json.JSONDecodeError as e:
                results.append(
                    DiagnosticResult(
                        check_name="claude_code_config_valid",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Claude Code config contains invalid JSON",
                        error=str(e),
                        fix_suggestion="Fix JSON syntax errors in .claude/settings.local.json",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        else:
            results.append(
                DiagnosticResult(
                    check_name="claude_code_config_exists",
                    success=False,
                    severity=DiagnosticSeverity.INFO,
                    message="Claude Code config not found (optional)",
                    error=f"File not found: {self.claude_code_config_path}",
                    fix_suggestion="Run: kuzu-memory install add claude-code to create config",
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
                        "Check server logs and process status" if not stdio_result.success else None
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
                        # Note: Tool names do NOT have kuzu_ prefix
                        test_params: dict[str, Any]
                        if tool_name == "enhance":
                            test_params = {"prompt": "test"}
                        elif tool_name == "learn":
                            test_params = {"content": "test"}
                        elif tool_name == "recall":
                            test_params = {"query": "test", "limit": 5}
                        elif tool_name == "stats":
                            test_params = {}
                        elif tool_name == "remember":
                            test_params = {"content": "test memory"}
                        elif tool_name == "recent":
                            test_params = {}
                        elif tool_name == "cleanup":
                            test_params = {"dry_run": True}  # Safe test mode
                        elif tool_name == "project":
                            test_params = {}
                        elif tool_name == "init":
                            test_params = {"path": None}
                        else:
                            # Default empty params for unknown tools
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
                                    tool_response.get("error", {}).get("message", "Unknown error")
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
        Attempt to automatically fix PROJECT-LEVEL configuration issues.

        Fixes:
        - Missing memory database directory
        - Missing Claude Code MCP configuration

        Does NOT fix Claude Desktop (user-level) configuration.

        Returns:
            Diagnostic result for auto-fix attempt
        """
        start = time.time()

        try:
            # Fix 1: Initialize memory database if missing
            if not self.memory_db_path.exists():
                init_result = subprocess.run(
                    ["kuzu-memory", "init"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(self.project_root),
                )

                if init_result.returncode != 0:
                    return DiagnosticResult(
                        check_name="auto_fix_configuration",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Failed to initialize memory database",
                        error=init_result.stderr,
                        duration_ms=(time.time() - start) * 1000,
                    )

            # Fix 2: Install Claude Code configuration if missing
            if not self.claude_code_config_path.exists():
                install_result = subprocess.run(
                    ["kuzu-memory", "install", "add", "claude-code"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self.project_root),
                )

                if install_result.returncode != 0:
                    return DiagnosticResult(
                        check_name="auto_fix_configuration",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Failed to install Claude Code configuration",
                        error=install_result.stderr,
                        duration_ms=(time.time() - start) * 1000,
                    )

            duration = (time.time() - start) * 1000
            return DiagnosticResult(
                check_name="auto_fix_configuration",
                success=True,
                severity=DiagnosticSeverity.SUCCESS,
                message="Project configuration auto-fixed successfully",
                metadata={
                    "memory_db_initialized": not self.memory_db_path.exists(),
                    "claude_code_config_created": not self.claude_code_config_path.exists(),
                },
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

    async def check_hooks(self) -> list[DiagnosticResult]:
        """
        Check Claude Code hooks configuration and execution.

        Tests:
        1. Hook configuration validation
        2. Hook execution tests
        3. Hook environment
        4. Diagnostic results

        Returns:
            List of diagnostic results for hooks checks
        """
        results = []

        # 1. Hook Configuration Validation
        settings_path = self.project_root / ".claude" / "settings.local.json"
        start = time.time()

        if not settings_path.exists():
            results.append(
                DiagnosticResult(
                    check_name="hooks_config_exists",
                    success=False,
                    severity=DiagnosticSeverity.INFO,
                    message="Hooks configuration file not found (optional)",
                    error=f"File not found: {settings_path}",
                    fix_suggestion="Run: kuzu-memory install add claude-code to create hooks configuration",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
            return results

        try:
            with open(settings_path) as f:
                config = json.load(f)

            results.append(
                DiagnosticResult(
                    check_name="hooks_config_valid",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"Hooks configuration file is valid JSON: {settings_path}",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

            # Validate hook events
            start = time.time()
            hooks = config.get("hooks", {})
            valid_events = {
                "UserPromptSubmit",
                "Stop",
                "PostToolUse",
                "SessionStart",
                "PreToolUse",
                "SubagentStop",
                "Notification",
                "SessionEnd",
                "PreCompact",
            }
            invalid_events = set(hooks.keys()) - valid_events

            if invalid_events:
                results.append(
                    DiagnosticResult(
                        check_name="hooks_event_names",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"Invalid hook event names detected: {invalid_events}",
                        error=f"Invalid events: {', '.join(invalid_events)}",
                        fix_suggestion="Run: kuzu-memory install add claude-code --force to fix event names",
                        metadata={"invalid_events": list(invalid_events)},
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="hooks_event_names",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message=f"Hook event names are valid ({len(hooks)} events)",
                        metadata={"events": list(hooks.keys())},
                        duration_ms=(time.time() - start) * 1000,
                    )
                )

            # Check for duplicate hook entries
            start = time.time()
            duplicates_found = False
            for _event_name, handlers in hooks.items():
                if not isinstance(handlers, list):
                    continue
                seen_commands = set()
                for handler_group in handlers:
                    for hook in handler_group.get("hooks", []):
                        command = hook.get("command", "")
                        if "kuzu" in command.lower():
                            if command in seen_commands:
                                duplicates_found = True
                            seen_commands.add(command)

            if duplicates_found:
                results.append(
                    DiagnosticResult(
                        check_name="hooks_no_duplicates",
                        success=False,
                        severity=DiagnosticSeverity.WARNING,
                        message="Duplicate hook entries detected",
                        error="Multiple identical hook commands found",
                        fix_suggestion="Run: kuzu-memory install add claude-code --force to remove duplicates",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="hooks_no_duplicates",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="No duplicate hook entries found",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )

            # Validate hook command paths are absolute
            start = time.time()
            non_absolute_paths = []
            missing_executables = []

            for event_name, handlers in hooks.items():
                if not isinstance(handlers, list):
                    continue
                for handler_group in handlers:
                    for hook in handler_group.get("hooks", []):
                        command = hook.get("command", "")
                        if "kuzu" in command.lower():
                            cmd_parts = command.split()
                            if cmd_parts:
                                cmd_path = cmd_parts[0]
                                # Check if path is absolute
                                if not cmd_path.startswith("/"):
                                    non_absolute_paths.append((event_name, cmd_path))
                                # Check if executable exists
                                elif not Path(cmd_path).exists():
                                    missing_executables.append((event_name, cmd_path))

            if non_absolute_paths:
                results.append(
                    DiagnosticResult(
                        check_name="hooks_absolute_paths",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Hook commands use relative paths (should be absolute)",
                        error=f"Relative paths found in {len(non_absolute_paths)} hook(s)",
                        fix_suggestion="Run: kuzu-memory install add claude-code --force to fix paths",
                        metadata={"non_absolute": [f"{e}: {p}" for e, p in non_absolute_paths]},
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            elif missing_executables:
                results.append(
                    DiagnosticResult(
                        check_name="hooks_executable_exists",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Hook command executables not found",
                        error=f"Missing executables in {len(missing_executables)} hook(s)",
                        fix_suggestion="Run: kuzu-memory install add claude-code --force to fix paths",
                        metadata={"missing": [f"{e}: {p}" for e, p in missing_executables]},
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="hooks_command_paths",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="Hook command paths are absolute and executables exist",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )

        except json.JSONDecodeError as e:
            results.append(
                DiagnosticResult(
                    check_name="hooks_config_valid",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Hooks configuration contains invalid JSON",
                    error=str(e),
                    fix_suggestion="Fix JSON syntax errors in .claude/settings.local.json",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
            return results

        # 2. Hook Execution Tests
        # Test session-start hook
        start = time.time()
        try:
            test_input = {"hook_event_name": "SessionStart"}
            result = subprocess.run(
                ["kuzu-memory", "hooks", "session-start"],
                input=json.dumps(test_input),
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.project_root),
            )

            if result.returncode == 0:
                results.append(
                    DiagnosticResult(
                        check_name="hook_session_start_execution",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="session-start hook executes successfully",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="hook_session_start_execution",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="session-start hook execution failed",
                        error=f"Exit code {result.returncode}: {result.stderr[:200]}",
                        fix_suggestion="Check hook script and permissions",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        except subprocess.TimeoutExpired:
            results.append(
                DiagnosticResult(
                    check_name="hook_session_start_execution",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="session-start hook execution timeout",
                    error="Command took longer than 5 seconds",
                    fix_suggestion="Check hook implementation for performance issues",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="hook_session_start_execution",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="session-start hook execution error",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # Test enhance hook
        start = time.time()
        try:
            test_input = {"prompt": "test prompt", "context": "test context"}
            result = subprocess.run(
                ["kuzu-memory", "hooks", "enhance"],
                input=json.dumps(test_input),
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.project_root),
            )

            if result.returncode == 0:
                results.append(
                    DiagnosticResult(
                        check_name="hook_enhance_execution",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="enhance hook executes successfully",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="hook_enhance_execution",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="enhance hook execution failed",
                        error=f"Exit code {result.returncode}: {result.stderr[:200]}",
                        fix_suggestion="Check hook script and database initialization",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        except subprocess.TimeoutExpired:
            results.append(
                DiagnosticResult(
                    check_name="hook_enhance_execution",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="enhance hook execution timeout",
                    error="Command took longer than 5 seconds",
                    fix_suggestion="Check hook implementation for performance issues",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="hook_enhance_execution",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="enhance hook execution error",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # Test learn hook
        start = time.time()
        try:
            # Create a temporary transcript file for testing
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
                transcript_path = tf.name
                # Write a test transcript entry
                test_transcript = {
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Test assistant response"}],
                    }
                }
                tf.write(json.dumps(test_transcript) + "\n")

            test_input = {"transcript_path": transcript_path}
            result = subprocess.run(
                ["kuzu-memory", "hooks", "learn"],
                input=json.dumps(test_input),
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.project_root),
            )

            # Clean up temp file
            try:
                Path(transcript_path).unlink()
            except Exception:
                pass

            if result.returncode == 0:
                results.append(
                    DiagnosticResult(
                        check_name="hook_learn_execution",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="learn hook executes successfully",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="hook_learn_execution",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="learn hook execution failed",
                        error=f"Exit code {result.returncode}: {result.stderr[:200]}",
                        fix_suggestion="Check hook script and database initialization",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        except subprocess.TimeoutExpired:
            results.append(
                DiagnosticResult(
                    check_name="hook_learn_execution",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="learn hook execution timeout",
                    error="Command took longer than 5 seconds",
                    fix_suggestion="Check hook implementation for performance issues",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="hook_learn_execution",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="learn hook execution error",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 3. Hook Environment Checks
        # Check log directory
        start = time.time()
        log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
        if log_dir.exists() and os.access(log_dir, os.W_OK):
            results.append(
                DiagnosticResult(
                    check_name="hook_log_directory",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message=f"Hook log directory exists and is writable: {log_dir}",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        else:
            results.append(
                DiagnosticResult(
                    check_name="hook_log_directory",
                    success=False,
                    severity=DiagnosticSeverity.WARNING,
                    message="Hook log directory not writable",
                    error=f"Directory: {log_dir}",
                    fix_suggestion=f"Ensure {log_dir} exists and is writable, or set KUZU_HOOK_LOG_DIR",
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # Check cache directory
        start = time.time()
        cache_file = log_dir / ".kuzu_learn_cache.json"
        cache_dir_ok = log_dir.exists() and os.access(log_dir, os.W_OK)
        results.append(
            DiagnosticResult(
                check_name="hook_cache_directory",
                success=cache_dir_ok,
                severity=(
                    DiagnosticSeverity.SUCCESS if cache_dir_ok else DiagnosticSeverity.WARNING
                ),
                message=f"Hook cache directory {'is' if cache_dir_ok else 'is not'} accessible",
                metadata={"cache_file": str(cache_file)},
                duration_ms=(time.time() - start) * 1000,
            )
        )

        # Verify PROJECT_ROOT detection
        start = time.time()
        try:
            from ...utils.project_setup import find_project_root

            detected_root = find_project_root()
            if detected_root == self.project_root:
                results.append(
                    DiagnosticResult(
                        check_name="hook_project_root_detection",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message=f"PROJECT_ROOT correctly detected: {detected_root}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="hook_project_root_detection",
                        success=False,
                        severity=DiagnosticSeverity.WARNING,
                        message="PROJECT_ROOT detection mismatch",
                        error=f"Expected: {self.project_root}, Detected: {detected_root}",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="hook_project_root_detection",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="PROJECT_ROOT detection failed",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        return results

    async def check_server_lifecycle(self) -> list[DiagnosticResult]:
        """
        Check MCP server lifecycle (startup, health, shutdown).

        Tests:
        1. Server startup
        2. Server health during operation
        3. Server shutdown
        4. Error recovery

        Returns:
            List of diagnostic results for server lifecycle checks
        """
        results = []

        # Use MCPConnectionTester for server lifecycle testing
        tester = MCPConnectionTester(project_root=self.project_root, timeout=10.0)

        # 1. Server Startup Test
        start = time.time()
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
                metadata=start_result.metadata,
                duration_ms=(time.time() - start) * 1000,
            )
        )

        if not start_result.success:
            return results  # Cannot proceed without server

        # 2. Server Health During Operation
        # Test ping requests
        start = time.time()
        try:
            ping_msg = {"jsonrpc": "2.0", "method": "ping", "id": 1}
            response = await asyncio.wait_for(tester._send_request(ping_msg), timeout=5.0)

            if response:
                results.append(
                    DiagnosticResult(
                        check_name="server_ping_response",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="Server responds to ping within timeout",
                        metadata={"response_time_ms": (time.time() - start) * 1000},
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="server_ping_response",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Server ping timeout",
                        error="No response received within 5 seconds",
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        except TimeoutError:
            results.append(
                DiagnosticResult(
                    check_name="server_ping_response",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Server ping timeout",
                    error="Request timed out after 5 seconds",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="server_ping_response",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Server ping error",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # Test protocol initialization
        start = time.time()
        try:
            init_msg = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 2,
                "params": {"protocolVersion": "2024-11-05"},
            }
            response = await asyncio.wait_for(tester._send_request(init_msg), timeout=5.0)

            if response and "result" in response:
                results.append(
                    DiagnosticResult(
                        check_name="server_protocol_init",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="Server protocol initialization successful",
                        metadata={"protocol_version": response["result"].get("protocolVersion")},
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="server_protocol_init",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Server protocol initialization failed",
                        error=(
                            response.get("error", "Unknown error") if response else "No response"
                        ),
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        except TimeoutError:
            results.append(
                DiagnosticResult(
                    check_name="server_protocol_init",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Protocol initialization timeout",
                    error="Request timed out after 5 seconds",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="server_protocol_init",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Protocol initialization error",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # List available tools
        start = time.time()
        try:
            tools_msg = {"jsonrpc": "2.0", "method": "tools/list", "id": 3}
            response = await asyncio.wait_for(tester._send_request(tools_msg), timeout=5.0)

            if response and "result" in response:
                tools = response["result"].get("tools", [])
                results.append(
                    DiagnosticResult(
                        check_name="server_tools_list",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message=f"Server tools list successful ({len(tools)} tools)",
                        metadata={
                            "tool_count": len(tools),
                            "tools": [t.get("name") for t in tools],
                        },
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            else:
                results.append(
                    DiagnosticResult(
                        check_name="server_tools_list",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Server tools list failed",
                        error=(
                            response.get("error", "Unknown error") if response else "No response"
                        ),
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
        except TimeoutError:
            results.append(
                DiagnosticResult(
                    check_name="server_tools_list",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Tools list timeout",
                    error="Request timed out after 5 seconds",
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="server_tools_list",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Tools list error",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        # 3. Server Shutdown Test
        start = time.time()
        try:
            # Send graceful shutdown
            if tester.process:
                tester.process.terminate()
                await asyncio.sleep(0.5)

                # Check if process terminated
                if tester.process.poll() is not None:
                    exit_code = tester.process.returncode
                    if exit_code == 0 or exit_code == -15:  # 0 = clean exit, -15 = SIGTERM
                        results.append(
                            DiagnosticResult(
                                check_name="server_shutdown_graceful",
                                success=True,
                                severity=DiagnosticSeverity.SUCCESS,
                                message="Server shutdown graceful (clean exit)",
                                metadata={"exit_code": exit_code},
                                duration_ms=(time.time() - start) * 1000,
                            )
                        )
                    else:
                        results.append(
                            DiagnosticResult(
                                check_name="server_shutdown_graceful",
                                success=False,
                                severity=DiagnosticSeverity.WARNING,
                                message="Server shutdown with non-zero exit code",
                                error=f"Exit code: {exit_code}",
                                metadata={"exit_code": exit_code},
                                duration_ms=(time.time() - start) * 1000,
                            )
                        )
                else:
                    # Process didn't terminate - force kill
                    tester.process.kill()
                    await asyncio.sleep(0.5)
                    results.append(
                        DiagnosticResult(
                            check_name="server_shutdown_graceful",
                            success=False,
                            severity=DiagnosticSeverity.WARNING,
                            message="Server required force kill",
                            error="Process did not respond to SIGTERM within 0.5 seconds",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )

                # Check for zombie processes
                await asyncio.sleep(0.5)
                zombie_check = subprocess.run(
                    ["ps", "-ef"], capture_output=True, text=True, timeout=2
                )
                if str(tester.process.pid) not in zombie_check.stdout:
                    results.append(
                        DiagnosticResult(
                            check_name="server_cleanup_resources",
                            success=True,
                            severity=DiagnosticSeverity.SUCCESS,
                            message="No zombie processes detected after shutdown",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )
                else:
                    results.append(
                        DiagnosticResult(
                            check_name="server_cleanup_resources",
                            success=False,
                            severity=DiagnosticSeverity.WARNING,
                            message="Zombie process detected after shutdown",
                            error=f"Process {tester.process.pid} still in process table",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )
        except Exception as e:
            results.append(
                DiagnosticResult(
                    check_name="server_shutdown",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Server shutdown test error",
                    error=str(e),
                    duration_ms=(time.time() - start) * 1000,
                )
            )
        finally:
            # Ensure cleanup
            await tester.stop_server()

        # 4. Error Recovery Test
        start = time.time()
        restart_result = await tester.start_server()
        if restart_result.success:
            # Test that server responds after restart
            try:
                test_msg = {"jsonrpc": "2.0", "method": "ping", "id": 99}
                response = await asyncio.wait_for(tester._send_request(test_msg), timeout=5.0)

                if response:
                    results.append(
                        DiagnosticResult(
                            check_name="server_restart_recovery",
                            success=True,
                            severity=DiagnosticSeverity.SUCCESS,
                            message="Server successfully restarted and responds to requests",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )
                else:
                    results.append(
                        DiagnosticResult(
                            check_name="server_restart_recovery",
                            success=False,
                            severity=DiagnosticSeverity.WARNING,
                            message="Server restarted but does not respond to requests",
                            error="No response to ping after restart",
                            duration_ms=(time.time() - start) * 1000,
                        )
                    )
            except Exception as e:
                results.append(
                    DiagnosticResult(
                        check_name="server_restart_recovery",
                        success=False,
                        severity=DiagnosticSeverity.ERROR,
                        message="Server restart recovery test failed",
                        error=str(e),
                        duration_ms=(time.time() - start) * 1000,
                    )
                )
            finally:
                await tester.stop_server()
        else:
            results.append(
                DiagnosticResult(
                    check_name="server_restart_recovery",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Server failed to restart",
                    error=restart_result.error,
                    duration_ms=(time.time() - start) * 1000,
                )
            )

        return results

    async def run_full_diagnostics(
        self,
        auto_fix: bool = False,
        check_hooks: bool = True,
        check_server_lifecycle: bool = True,
    ) -> DiagnosticReport:
        """
        Run complete diagnostic suite.

        Args:
            auto_fix: Attempt to automatically fix issues
            check_hooks: Run hooks diagnostic checks
            check_server_lifecycle: Run server lifecycle diagnostic checks

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

        # Run hooks checks if requested
        if check_hooks:
            hooks_results = await self.check_hooks()
            for result in hooks_results:
                report.add_result(result)

        # Run server lifecycle checks if requested
        if check_server_lifecycle:
            lifecycle_results = await self.check_server_lifecycle()
            for result in lifecycle_results:
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
        lines.append(f"Results: {report.passed}/{report.total} passed ({report.success_rate:.1f}%)")
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
