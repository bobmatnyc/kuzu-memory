"""
Unit tests for MCPConnectionTester class.

Tests the connection testing framework without requiring a live server.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from kuzu_memory.mcp.testing import (
    ConnectionStatus,
    ConnectionTestResult,
    ConnectionTestSuite,
    MCPConnectionTester,
    TestSeverity,
)


class TestConnectionTestResult:
    """Test ConnectionTestResult data class."""

    def test_result_creation(self) -> None:
        """Test creating a test result."""
        result = ConnectionTestResult(
            test_name="test_connection",
            success=True,
            status=ConnectionStatus.CONNECTED,
            duration_ms=123.45,
            severity=TestSeverity.INFO,
            message="Connection successful",
        )

        assert result.test_name == "test_connection"
        assert result.success is True
        assert result.status == ConnectionStatus.CONNECTED
        assert result.duration_ms == 123.45
        assert result.severity == TestSeverity.INFO
        assert result.message == "Connection successful"
        assert result.error is None

    def test_result_with_error(self) -> None:
        """Test result with error information."""
        result = ConnectionTestResult(
            test_name="test_failed",
            success=False,
            status=ConnectionStatus.ERROR,
            duration_ms=50.0,
            severity=TestSeverity.ERROR,
            message="Connection failed",
            error="Connection refused",
        )

        assert result.success is False
        assert result.error == "Connection refused"

    def test_result_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = ConnectionTestResult(
            test_name="test",
            success=True,
            status=ConnectionStatus.CONNECTED,
            duration_ms=10.0,
            severity=TestSeverity.INFO,
            message="Success",
            metadata={"key": "value"},
        )

        result_dict = result.to_dict()

        assert result_dict["test_name"] == "test"
        assert result_dict["success"] is True
        assert result_dict["status"] == "connected"
        assert result_dict["duration_ms"] == 10.0
        assert result_dict["severity"] == "info"
        assert result_dict["message"] == "Success"
        assert result_dict["metadata"] == {"key": "value"}


class TestConnectionTestSuite:
    """Test ConnectionTestSuite data class."""

    def test_suite_creation(self) -> None:
        """Test creating a test suite."""
        suite = ConnectionTestSuite(suite_name="Test Suite")

        assert suite.suite_name == "Test Suite"
        assert suite.total == 0
        assert suite.passed == 0
        assert suite.failed == 0
        assert suite.success_rate == 0.0

    def test_suite_with_results(self) -> None:
        """Test suite with multiple results."""
        suite = ConnectionTestSuite(suite_name="Test Suite")

        # Add passing result
        suite.add_result(
            ConnectionTestResult(
                test_name="test1",
                success=True,
                status=ConnectionStatus.CONNECTED,
                duration_ms=10.0,
                severity=TestSeverity.INFO,
                message="Pass",
            )
        )

        # Add failing result
        suite.add_result(
            ConnectionTestResult(
                test_name="test2",
                success=False,
                status=ConnectionStatus.ERROR,
                duration_ms=20.0,
                severity=TestSeverity.ERROR,
                message="Fail",
            )
        )

        assert suite.total == 2
        assert suite.passed == 1
        assert suite.failed == 1
        assert suite.success_rate == 50.0

    def test_suite_to_dict(self) -> None:
        """Test converting suite to dictionary."""
        suite = ConnectionTestSuite(suite_name="Test Suite")
        suite.add_result(
            ConnectionTestResult(
                test_name="test",
                success=True,
                status=ConnectionStatus.CONNECTED,
                duration_ms=10.0,
                severity=TestSeverity.INFO,
                message="Pass",
            )
        )
        suite.total_duration_ms = 100.0

        suite_dict = suite.to_dict()

        assert suite_dict["suite_name"] == "Test Suite"
        assert suite_dict["passed"] == 1
        assert suite_dict["failed"] == 0
        assert suite_dict["total"] == 1
        assert suite_dict["success_rate"] == 100.0
        assert suite_dict["total_duration_ms"] == 100.0
        assert len(suite_dict["results"]) == 1


class TestMCPConnectionTester:
    """Test MCPConnectionTester initialization and configuration."""

    def test_tester_creation(self) -> None:
        """Test creating a connection tester."""
        tester = MCPConnectionTester(timeout=10.0)

        assert tester.timeout == 10.0
        assert tester.process is None

    def test_tester_with_custom_path(self, tmp_path: Path) -> None:
        """Test tester with custom server path."""
        tester = MCPConnectionTester(
            server_path="/usr/bin/test-server",
            project_root=tmp_path,
            timeout=5.0,
        )

        assert tester.server_path == "/usr/bin/test-server"
        assert tester.project_root == tmp_path
        assert tester.timeout == 5.0

    def test_server_path_resolution(self) -> None:
        """Test server path resolution logic."""
        tester = MCPConnectionTester()

        # Should resolve to some valid path
        assert tester.server_path is not None
        assert len(tester.server_path) > 0


class TestConnectionStatus:
    """Test ConnectionStatus enum."""

    def test_status_values(self) -> None:
        """Test connection status values."""
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.ERROR.value == "error"
        assert ConnectionStatus.TIMEOUT.value == "timeout"


class TestTestSeverity:
    """Test TestSeverity enum."""

    def test_severity_values(self) -> None:
        """Test severity level values."""
        assert TestSeverity.CRITICAL.value == "critical"
        assert TestSeverity.ERROR.value == "error"
        assert TestSeverity.WARNING.value == "warning"
        assert TestSeverity.INFO.value == "info"
