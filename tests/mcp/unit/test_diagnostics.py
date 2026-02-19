"""
Unit tests for MCP diagnostics framework.

Tests for diagnostic checks, result handling, report generation,
and auto-fix functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kuzu_memory.mcp.testing.diagnostics import (
    DiagnosticReport,
    DiagnosticResult,
    DiagnosticSeverity,
    MCPDiagnostics,
)


class TestDiagnosticResult:
    """Tests for DiagnosticResult dataclass."""

    def test_diagnostic_result_creation(self):
        """Test creating a diagnostic result."""
        result = DiagnosticResult(
            check_name="test_check",
            success=True,
            severity=DiagnosticSeverity.SUCCESS,
            message="Test passed",
            duration_ms=10.5,
        )

        assert result.check_name == "test_check"
        assert result.success is True
        assert result.severity == DiagnosticSeverity.SUCCESS
        assert result.message == "Test passed"
        assert result.duration_ms == 10.5
        assert result.error is None
        assert result.fix_suggestion is None

    def test_diagnostic_result_with_error(self):
        """Test diagnostic result with error and fix suggestion."""
        result = DiagnosticResult(
            check_name="failed_check",
            success=False,
            severity=DiagnosticSeverity.ERROR,
            message="Check failed",
            error="Something went wrong",
            fix_suggestion="Try fixing this way",
            duration_ms=5.0,
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.fix_suggestion == "Try fixing this way"

    def test_diagnostic_result_to_dict(self):
        """Test converting result to dictionary."""
        result = DiagnosticResult(
            check_name="test_check",
            success=True,
            severity=DiagnosticSeverity.INFO,
            message="Test message",
            metadata={"key": "value"},
            duration_ms=15.0,
        )

        result_dict = result.to_dict()

        assert result_dict["check_name"] == "test_check"
        assert result_dict["success"] is True
        assert result_dict["severity"] == "info"
        assert result_dict["message"] == "Test message"
        assert result_dict["metadata"] == {"key": "value"}
        assert result_dict["duration_ms"] == 15.0


class TestDiagnosticReport:
    """Tests for DiagnosticReport dataclass."""

    def test_diagnostic_report_creation(self):
        """Test creating a diagnostic report."""
        report = DiagnosticReport(
            report_name="Test Report",
            timestamp="2025-10-01 12:00:00",
            platform="Darwin",
        )

        assert report.report_name == "Test Report"
        assert report.timestamp == "2025-10-01 12:00:00"
        assert report.platform == "Darwin"
        assert len(report.results) == 0
        assert report.total == 0

    def test_add_result(self):
        """Test adding results to report."""
        report = DiagnosticReport(
            report_name="Test",
            timestamp="2025-10-01",
            platform="Darwin",
        )

        result1 = DiagnosticResult(
            check_name="check1",
            success=True,
            severity=DiagnosticSeverity.SUCCESS,
            message="Pass",
        )
        result2 = DiagnosticResult(
            check_name="check2",
            success=False,
            severity=DiagnosticSeverity.ERROR,
            message="Fail",
        )

        report.add_result(result1)
        report.add_result(result2)

        assert report.total == 2
        assert report.passed == 1
        assert report.failed == 1

    def test_success_rate(self):
        """Test success rate calculation."""
        report = DiagnosticReport(
            report_name="Test",
            timestamp="2025-10-01",
            platform="Darwin",
        )

        # Add 3 passed, 1 failed
        for i in range(3):
            report.add_result(
                DiagnosticResult(
                    check_name=f"pass{i}",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="Pass",
                )
            )

        report.add_result(
            DiagnosticResult(
                check_name="fail",
                success=False,
                severity=DiagnosticSeverity.ERROR,
                message="Fail",
            )
        )

        assert report.success_rate == 75.0

    def test_has_critical_errors(self):
        """Test critical error detection."""
        report = DiagnosticReport(
            report_name="Test",
            timestamp="2025-10-01",
            platform="Darwin",
        )

        # Add non-critical error
        report.add_result(
            DiagnosticResult(
                check_name="warning",
                success=False,
                severity=DiagnosticSeverity.WARNING,
                message="Warning",
            )
        )

        assert not report.has_critical_errors

        # Add critical error
        report.add_result(
            DiagnosticResult(
                check_name="critical",
                success=False,
                severity=DiagnosticSeverity.CRITICAL,
                message="Critical",
            )
        )

        assert report.has_critical_errors

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        report = DiagnosticReport(
            report_name="Test Report",
            timestamp="2025-10-01",
            platform="Darwin",
            total_duration_ms=100.0,
        )

        result = DiagnosticResult(
            check_name="test",
            success=True,
            severity=DiagnosticSeverity.SUCCESS,
            message="Pass",
        )
        report.add_result(result)

        report_dict = report.to_dict()

        assert report_dict["report_name"] == "Test Report"
        assert report_dict["passed"] == 1
        assert report_dict["total"] == 1
        assert report_dict["success_rate"] == 100.0
        assert len(report_dict["results"]) == 1


class TestMCPDiagnostics:
    """Tests for MCPDiagnostics class."""

    def test_initialization(self):
        """Test diagnostics initialization."""
        diagnostics = MCPDiagnostics()

        assert diagnostics.project_root == Path.cwd()
        assert diagnostics.verbose is False
        assert diagnostics.claude_code_config_path is not None

    def test_initialization_with_params(self):
        """Test diagnostics with custom parameters."""
        project_root = Path("/tmp/test")
        diagnostics = MCPDiagnostics(project_root=project_root, verbose=True)

        assert diagnostics.project_root == project_root
        assert diagnostics.verbose is True

    @pytest.mark.asyncio
    async def test_check_configuration_no_config(self):
        """Test configuration check when config doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create diagnostics with non-existent config path
            diagnostics = MCPDiagnostics(project_root=Path(tmpdir))

            results = await diagnostics.check_configuration()

            assert len(results) > 0
            # First check is memory_database_directory
            assert results[0].check_name == "memory_database_directory"
            # It should fail since directory doesn't exist
            assert not results[0].success

    @pytest.mark.asyncio
    async def test_check_configuration_invalid_json(self):
        """Test configuration check with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up project structure
            project_root = Path(tmpdir)
            claude_config_path = project_root / ".claude" / "settings.local.json"
            claude_config_path.parent.mkdir(parents=True, exist_ok=True)
            claude_config_path.write_text("{ invalid json }")

            diagnostics = MCPDiagnostics(project_root=project_root)

            results = await diagnostics.check_configuration()

            # Find the Claude Code config check result
            config_check = next(
                (r for r in results if r.check_name == "claude_code_config_valid"),
                None,
            )
            assert config_check is not None
            assert not config_check.success
            assert config_check.severity == DiagnosticSeverity.ERROR

    @pytest.mark.asyncio
    async def test_check_configuration_valid(self):
        """Test configuration check with valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            db_path = Path(tmpdir) / "db"
            db_path.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_path / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))

            diagnostics = MCPDiagnostics()
            diagnostics.claude_config_path = config_path

            results = await diagnostics.check_configuration()

            # Verify no CRITICAL, ERROR, or WARNING failures (INFO failures are acceptable)
            actionable_failures = [
                r
                for r in results
                if not r.success
                and r.severity
                in (
                    DiagnosticSeverity.CRITICAL,
                    DiagnosticSeverity.ERROR,
                    DiagnosticSeverity.WARNING,
                )
            ]
            assert len(actionable_failures) == 0, (
                f"Found {len(actionable_failures)} actionable failures: "
                f"{[r.check_name for r in actionable_failures]}"
            )

    @pytest.mark.asyncio
    async def test_check_connection(self):
        """Test connection diagnostics."""
        diagnostics = MCPDiagnostics()

        # Mock the connection tester
        with patch("kuzu_memory.mcp.testing.diagnostics.MCPConnectionTester") as mock_tester_class:
            mock_tester = MagicMock()
            mock_tester_class.return_value = mock_tester

            # Mock async methods
            from kuzu_memory.mcp.testing.connection_tester import (
                ConnectionStatus,
                ConnectionTestResult,
                TestSeverity,
            )

            mock_tester.start_server = AsyncMock(
                return_value=ConnectionTestResult(
                    test_name="server_startup",
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    duration_ms=10.0,
                    severity=TestSeverity.INFO,
                    message="Server started",
                )
            )

            mock_tester.test_stdio_connection = AsyncMock(
                return_value=ConnectionTestResult(
                    test_name="stdio_connection",
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    duration_ms=5.0,
                    severity=TestSeverity.INFO,
                    message="Connection OK",
                )
            )

            mock_tester.test_protocol_initialization = AsyncMock(
                return_value=ConnectionTestResult(
                    test_name="protocol_init",
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    duration_ms=15.0,
                    severity=TestSeverity.INFO,
                    message="Protocol OK",
                )
            )

            mock_tester.validate_jsonrpc_compliance = AsyncMock(
                return_value=ConnectionTestResult(
                    test_name="jsonrpc",
                    success=True,
                    status=ConnectionStatus.CONNECTED,
                    duration_ms=8.0,
                    severity=TestSeverity.INFO,
                    message="Compliant",
                )
            )

            mock_tester.stop_server = AsyncMock()

            results = await diagnostics.check_connection()

            assert len(results) == 4
            assert all(r.success for r in results)
            mock_tester.stop_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_fix_configuration(self):
        """Test auto-fix configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            diagnostics = MCPDiagnostics(project_root=Path(tmpdir))

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

                result = await diagnostics.auto_fix_configuration()

                assert result.success
                assert result.check_name == "auto_fix_configuration"
                # Should be called twice - once for init, once for install
                assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_auto_fix_database(self):
        """Test auto-fix database."""
        diagnostics = MCPDiagnostics()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

            result = await diagnostics.auto_fix_database()

            assert result.success
            assert result.check_name == "auto_fix_database"
            mock_run.assert_called_once()

    def test_generate_text_report(self):
        """Test text report generation."""
        diagnostics = MCPDiagnostics()
        report = DiagnosticReport(
            report_name="Test Report",
            timestamp="2025-10-01 12:00:00",
            platform="Darwin",
            total_duration_ms=100.0,
        )

        result = DiagnosticResult(
            check_name="test_check",
            success=True,
            severity=DiagnosticSeverity.SUCCESS,
            message="Test passed",
            duration_ms=10.0,
        )
        report.add_result(result)

        text = diagnostics.generate_text_report(report)

        assert "Test Report" in text
        assert "test_check" in text
        assert "Test passed" in text
        assert "SUCCESS" in text

    def test_generate_html_report(self):
        """Test HTML report generation."""
        diagnostics = MCPDiagnostics()
        report = DiagnosticReport(
            report_name="Test Report",
            timestamp="2025-10-01 12:00:00",
            platform="Darwin",
            total_duration_ms=100.0,
        )

        result = DiagnosticResult(
            check_name="test_check",
            success=True,
            severity=DiagnosticSeverity.SUCCESS,
            message="Test passed",
            duration_ms=10.0,
        )
        report.add_result(result)

        html = diagnostics.generate_html_report(report)

        assert "<!DOCTYPE html>" in html
        assert "Test Report" in html
        assert "test_check" in html
        assert "Test passed" in html

    @pytest.mark.asyncio
    async def test_run_full_diagnostics_no_autofix(self):
        """Test running full diagnostics without auto-fix."""
        diagnostics = MCPDiagnostics()

        # Mock all check methods
        with (
            patch.object(diagnostics, "check_configuration") as mock_config,
            patch.object(diagnostics, "check_connection") as mock_connection,
            patch.object(diagnostics, "check_tools") as mock_tools,
            patch.object(diagnostics, "check_performance") as mock_perf,
        ):
            # Setup mocks to return multiple successful results
            # (reflecting expanded diagnostics system)
            mock_config.return_value = [
                DiagnosticResult(
                    check_name="config_check_1",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="config_check_2",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="config_check_3",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
            ]
            mock_connection.return_value = [
                DiagnosticResult(
                    check_name="connection_check_1",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="connection_check_2",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="connection_check_3",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
            ]
            mock_tools.return_value = [
                DiagnosticResult(
                    check_name="tools_check_1",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="tools_check_2",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="tools_check_3",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
            ]
            mock_perf.return_value = [
                DiagnosticResult(
                    check_name="performance_check_1",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="performance_check_2",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
                DiagnosticResult(
                    check_name="performance_check_3",
                    success=True,
                    severity=DiagnosticSeverity.SUCCESS,
                    message="OK",
                ),
            ]

            # Disable extra checks (hooks, lifecycle) to isolate the 4 core diagnostic categories
            report = await diagnostics.run_full_diagnostics(
                auto_fix=False, check_hooks=False, check_server_lifecycle=False
            )

            # Verify report has correct number of results (12 total from 4 categories x 3 each)
            assert report.total == 12
            assert report.passed == 12
            assert not report.has_critical_errors
            mock_config.assert_called_once()
            mock_connection.assert_called_once()
            mock_tools.assert_called_once()
            mock_perf.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_full_diagnostics_with_autofix(self):
        """Test running full diagnostics with auto-fix."""
        diagnostics = MCPDiagnostics()

        # Mock check methods to return failures
        with (
            patch.object(diagnostics, "check_configuration") as mock_config,
            patch.object(diagnostics, "auto_fix_configuration") as mock_fix,
        ):
            # First call fails
            mock_config.side_effect = [
                [
                    DiagnosticResult(
                        check_name="config",
                        success=False,
                        severity=DiagnosticSeverity.CRITICAL,
                        message="Failed",
                    )
                ],
                # Second call (after fix) succeeds
                [
                    DiagnosticResult(
                        check_name="config",
                        success=True,
                        severity=DiagnosticSeverity.SUCCESS,
                        message="OK",
                    )
                ],
            ]

            mock_fix.return_value = DiagnosticResult(
                check_name="auto_fix",
                success=True,
                severity=DiagnosticSeverity.SUCCESS,
                message="Fixed",
            )

            await diagnostics.run_full_diagnostics(auto_fix=True)

            # Should have initial config check + fix + re-check
            assert mock_config.call_count == 2
            mock_fix.assert_called_once()
