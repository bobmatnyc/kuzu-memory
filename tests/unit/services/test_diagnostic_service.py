"""Tests for DiagnosticService."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from kuzu_memory.mcp.testing.diagnostics import (
    DiagnosticReport,
    DiagnosticResult,
    DiagnosticSeverity,
)
from kuzu_memory.mcp.testing.health_checker import (
    ComponentHealth,
    HealthCheckResult,
    HealthStatus,
    SystemHealth,
)
from kuzu_memory.protocols.services import IConfigService, IMemoryService
from kuzu_memory.services.diagnostic_service import DiagnosticService

# Use anyio for async test support (asyncio backend only)
pytestmark = pytest.mark.anyio

# Configure anyio to only use asyncio backend (not trio)
pytest.register_assert_rewrite("anyio")
anyio_backends = ("asyncio",)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    mock = Mock(spec=IConfigService)
    mock.is_initialized = False
    mock.initialize = Mock()
    mock.get_project_root.return_value = Path("/fake/project")
    return mock


@pytest.fixture
def mock_memory_service():
    """Create mock memory service."""
    mock = Mock(spec=IMemoryService)
    mock.is_initialized = False
    mock.initialize = Mock()
    mock.get_memory_count.return_value = 42
    mock.get_database_size.return_value = 1024 * 1024  # 1MB
    return mock


@pytest.fixture
def mock_diagnostics():
    """Create mock MCPDiagnostics."""
    mock = Mock()

    # Mock run_full_diagnostics to return a DiagnosticReport
    report = DiagnosticReport(
        report_name="Test Report",
        timestamp="2024-01-01 12:00:00",
        platform="Test",
        results=[
            DiagnosticResult(
                check_name="test_check",
                success=True,
                severity=DiagnosticSeverity.SUCCESS,
                message="Test passed",
            )
        ],
        total_duration_ms=100.0,
    )
    mock.run_full_diagnostics = AsyncMock(return_value=report)
    mock.check_configuration = AsyncMock(
        return_value=[
            DiagnosticResult(
                check_name="config_check",
                success=True,
                severity=DiagnosticSeverity.SUCCESS,
                message="Config valid",
            )
        ]
    )

    return mock


@pytest.fixture
def mock_health_checker():
    """Create mock MCPHealthChecker."""
    mock = Mock()

    # Create healthy components
    db_component = ComponentHealth(
        name="database",
        status=HealthStatus.HEALTHY,
        message="Database accessible",
        latency_ms=50.0,
        metadata={"size_bytes": 1024},
    )

    protocol_component = ComponentHealth(
        name="protocol",
        status=HealthStatus.HEALTHY,
        message="Protocol compliant",
        latency_ms=100.0,
    )

    system_health = SystemHealth(
        status=HealthStatus.HEALTHY,
        components=[db_component, protocol_component],
    )

    health_result = HealthCheckResult(
        health=system_health,
        duration_ms=200.0,
    )

    mock.check_health = AsyncMock(return_value=health_result)

    return mock


@pytest.fixture
def service(mock_config_service):
    """Create DiagnosticService instance."""
    return DiagnosticService(config_service=mock_config_service)


@pytest.fixture
def service_with_memory(mock_config_service, mock_memory_service):
    """Create DiagnosticService with memory service."""
    return DiagnosticService(
        config_service=mock_config_service,
        memory_service=mock_memory_service,
    )


# ============================================================================
# 1. Lifecycle Tests (5 tests)
# ============================================================================


def test_initialization_creates_diagnostics_and_health_checker(mock_config_service):
    """Test that initialization creates diagnostics and health checker."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics") as mock_diag_class,
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker") as mock_health_class,
    ):
        service = DiagnosticService(config_service=mock_config_service)
        service.initialize()

        # Verify config service was initialized
        mock_config_service.initialize.assert_called_once()

        # Verify MCPDiagnostics was created
        mock_diag_class.assert_called_once_with(project_root=Path("/fake/project"))

        # Verify MCPHealthChecker was created
        mock_health_class.assert_called_once_with(project_root=Path("/fake/project"))

        # Verify service is marked as initialized
        assert service.is_initialized


def test_cleanup_nullifies_tools(service, mock_config_service):
    """Test that cleanup nullifies diagnostic tools."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service.initialize()
        assert service._diagnostics is not None
        assert service._health_checker is not None

        service.cleanup()
        assert service._diagnostics is None
        assert service._health_checker is None
        assert not service.is_initialized


def test_context_manager_lifecycle(mock_config_service):
    """Test context manager handles initialization and cleanup."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service = DiagnosticService(config_service=mock_config_service)

        assert not service.is_initialized

        with service as svc:
            assert svc.is_initialized
            assert svc is service

        # After context exit, should be cleaned up
        assert not service.is_initialized


def test_initialization_with_memory_service(mock_config_service, mock_memory_service):
    """Test initialization with optional memory service."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service = DiagnosticService(
            config_service=mock_config_service,
            memory_service=mock_memory_service,
        )
        service.initialize()

        # Verify both services were initialized
        mock_config_service.initialize.assert_called_once()
        mock_memory_service.initialize.assert_called_once()

        assert service.is_initialized


def test_initialization_without_memory_service(mock_config_service):
    """Test initialization works without memory service."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service = DiagnosticService(config_service=mock_config_service)
        service.initialize()

        # Should still initialize successfully
        assert service.is_initialized


# ============================================================================
# 2. Async Delegation Tests (7 tests - one per async method)
# ============================================================================


@pytest.mark.asyncio
async def test_run_full_diagnostics_aggregates_results(
    service, mock_diagnostics, mock_health_checker
):
    """Test run_full_diagnostics aggregates results from all checks."""
    with (
        patch(
            "kuzu_memory.services.diagnostic_service.MCPDiagnostics",
            return_value=mock_diagnostics,
        ),
        patch(
            "kuzu_memory.services.diagnostic_service.MCPHealthChecker",
            return_value=mock_health_checker,
        ),
    ):
        service.initialize()

        result = await service.run_full_diagnostics()

        # Verify all sections are present
        assert "all_healthy" in result
        assert "configuration" in result
        assert "database" in result
        assert "mcp_server" in result
        assert "git_integration" in result
        assert "system_info" in result
        assert "dependencies" in result
        assert "timestamp" in result
        assert "total_checks" in result
        assert "passed_checks" in result


@pytest.mark.asyncio
async def test_check_configuration_delegates(service, mock_diagnostics):
    """Test check_configuration delegates to MCPDiagnostics."""
    with (
        patch(
            "kuzu_memory.services.diagnostic_service.MCPDiagnostics",
            return_value=mock_diagnostics,
        ),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service.initialize()

        result = await service.check_configuration()

        # Verify delegation occurred
        mock_diagnostics.check_configuration.assert_called_once()

        # Verify result structure
        assert "valid" in result
        assert "issues" in result
        assert "config_path" in result
        assert "project_root" in result


@pytest.mark.asyncio
async def test_check_database_health_delegates(
    service_with_memory, mock_health_checker, mock_memory_service
):
    """Test check_database_health delegates to MCPHealthChecker."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch(
            "kuzu_memory.services.diagnostic_service.MCPHealthChecker",
            return_value=mock_health_checker,
        ),
    ):
        service_with_memory.initialize()

        result = await service_with_memory.check_database_health()

        # Verify delegation occurred
        mock_health_checker.check_health.assert_called_once()

        # Verify memory service was used
        mock_memory_service.get_memory_count.assert_called_once()
        mock_memory_service.get_database_size.assert_called_once()

        # Verify result structure
        assert "connected" in result
        assert "memory_count" in result
        assert "db_size_bytes" in result
        assert "schema_version" in result
        assert "issues" in result

        # Verify memory service data
        assert result["memory_count"] == 42
        assert result["db_size_bytes"] == 1024 * 1024


@pytest.mark.asyncio
async def test_check_mcp_server_health_delegates(service, mock_health_checker):
    """Test check_mcp_server_health delegates to MCPHealthChecker."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch(
            "kuzu_memory.services.diagnostic_service.MCPHealthChecker",
            return_value=mock_health_checker,
        ),
    ):
        service.initialize()

        result = await service.check_mcp_server_health()

        # Verify delegation occurred
        mock_health_checker.check_health.assert_called_once()

        # Verify result structure
        assert "configured" in result
        assert "config_valid" in result
        assert "server_path" in result
        assert "issues" in result


@pytest.mark.asyncio
async def test_check_git_integration_delegates(service):
    """Test check_git_integration checks git availability."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
        patch("subprocess.run") as mock_run,
    ):
        # Mock git being available
        mock_run.return_value = MagicMock(returncode=0)

        service.initialize()

        result = await service.check_git_integration()

        # Verify subprocess was called to check git
        mock_run.assert_called_once()

        # Verify result structure
        assert "available" in result
        assert "hooks_installed" in result
        assert "last_sync" in result
        assert "issues" in result

        # Git should be available
        assert result["available"] is True


@pytest.mark.asyncio
async def test_get_system_info_delegates(service):
    """Test get_system_info collects system information."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service.initialize()

        result = await service.get_system_info()

        # Verify result structure
        assert "version" in result
        assert "python_version" in result
        assert "platform" in result
        assert "kuzu_version" in result
        assert "install_path" in result


@pytest.mark.asyncio
async def test_verify_dependencies_delegates(service):
    """Test verify_dependencies checks required packages."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service.initialize()

        result = await service.verify_dependencies()

        # Verify result structure
        assert "all_satisfied" in result
        assert "missing" in result
        assert "outdated" in result
        assert "suggestions" in result


# ============================================================================
# 3. Sync Formatting Tests (3 tests)
# ============================================================================


def test_format_diagnostic_report_with_success_results(service):
    """Test format_diagnostic_report with successful results."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service.initialize()

        results = {
            "all_healthy": True,
            "configuration": {
                "valid": True,
                "issues": [],
                "config_path": "/path",
                "project_root": "/root",
            },
            "database": {
                "connected": True,
                "memory_count": 100,
                "db_size_bytes": 2048,
                "schema_version": "1.0",
                "issues": [],
            },
            "mcp_server": {
                "configured": True,
                "config_valid": True,
                "server_path": "/server",
                "issues": [],
            },
            "git_integration": {
                "available": True,
                "hooks_installed": True,
                "last_sync": None,
                "issues": [],
            },
            "system_info": {
                "version": "1.0",
                "python_version": "3.11",
                "platform": "Linux",
                "kuzu_version": "0.1",
                "install_path": "/install",
            },
            "dependencies": {
                "all_satisfied": True,
                "missing": [],
                "outdated": [],
                "suggestions": [],
            },
            "timestamp": "2024-01-01 12:00:00",
            "total_checks": 10,
            "passed_checks": 10,
            "failed_checks": 0,
            "success_rate": 100.0,
        }

        report = service.format_diagnostic_report(results)

        # Verify report contains key sections
        assert "KuzuMemory Diagnostic Report" in report
        assert "HEALTHY" in report
        assert "CONFIGURATION" in report
        assert "DATABASE" in report
        assert "MCP SERVER" in report
        assert "GIT INTEGRATION" in report
        assert "SYSTEM INFORMATION" in report
        assert "DEPENDENCIES" in report
        assert "All systems operational" in report


def test_format_diagnostic_report_with_failures(service):
    """Test format_diagnostic_report with failures."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service.initialize()

        results = {
            "all_healthy": False,
            "configuration": {
                "valid": False,
                "issues": ["Config file missing"],
                "config_path": "/path",
                "project_root": "/root",
            },
            "database": {
                "connected": False,
                "memory_count": 0,
                "db_size_bytes": 0,
                "schema_version": "N/A",
                "issues": ["DB not found"],
            },
            "mcp_server": {
                "configured": False,
                "config_valid": False,
                "server_path": "/server",
                "issues": ["Server not configured"],
            },
            "git_integration": {
                "available": False,
                "hooks_installed": False,
                "last_sync": None,
                "issues": ["Git not available"],
            },
            "system_info": {
                "version": "1.0",
                "python_version": "3.11",
                "platform": "Linux",
                "kuzu_version": "0.1",
                "install_path": "/install",
            },
            "dependencies": {
                "all_satisfied": False,
                "missing": ["kuzu"],
                "outdated": [],
                "suggestions": ["Install kuzu"],
            },
            "timestamp": "2024-01-01 12:00:00",
            "total_checks": 10,
            "passed_checks": 5,
            "failed_checks": 5,
            "success_rate": 50.0,
        }

        report = service.format_diagnostic_report(results)

        # Verify report shows issues
        assert "ISSUES DETECTED" in report
        assert "Config file missing" in report
        assert "DB not found" in report
        assert "Server not configured" in report
        assert "Git not available" in report
        assert "Install kuzu" in report
        assert "Action required" in report


def test_format_diagnostic_report_with_mixed_results(service):
    """Test format_diagnostic_report with mixed success/failure."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service.initialize()

        results = {
            "all_healthy": False,
            "configuration": {
                "valid": True,
                "issues": [],
                "config_path": "/path",
                "project_root": "/root",
            },
            "database": {
                "connected": False,
                "memory_count": 0,
                "db_size_bytes": 0,
                "schema_version": "N/A",
                "issues": ["DB not initialized"],
            },
            "mcp_server": {
                "configured": True,
                "config_valid": True,
                "server_path": "/server",
                "issues": [],
            },
            "git_integration": {
                "available": True,
                "hooks_installed": False,
                "last_sync": None,
                "issues": [],
            },
            "system_info": {
                "version": "1.0",
                "python_version": "3.11",
                "platform": "Linux",
                "kuzu_version": "0.1",
                "install_path": "/install",
            },
            "dependencies": {
                "all_satisfied": True,
                "missing": [],
                "outdated": [],
                "suggestions": [],
            },
            "timestamp": "2024-01-01 12:00:00",
            "total_checks": 10,
            "passed_checks": 7,
            "failed_checks": 3,
            "success_rate": 70.0,
        }

        report = service.format_diagnostic_report(results)

        # Verify mixed results
        assert "ISSUES DETECTED" in report
        assert "✓ Valid" in report  # Config valid
        assert "DB not initialized" in report  # DB issue
        assert "✓ Configured" in report  # MCP configured


# ============================================================================
# 4. Dependency Injection Tests (5 tests)
# ============================================================================


def test_requires_config_service():
    """Test service requires IConfigService."""
    # Should not raise - config service is required
    service = DiagnosticService(config_service=Mock(spec=IConfigService))
    assert service._config_service is not None


def test_optional_memory_service():
    """Test memory service is optional."""
    service = DiagnosticService(config_service=Mock(spec=IConfigService))
    assert service._memory_service is None


def test_initializes_config_service(mock_config_service):
    """Test initializes config service if needed."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service = DiagnosticService(config_service=mock_config_service)
        service.initialize()

        mock_config_service.initialize.assert_called_once()


def test_initializes_memory_service_if_provided(mock_config_service, mock_memory_service):
    """Test initializes memory service if provided."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        service = DiagnosticService(
            config_service=mock_config_service,
            memory_service=mock_memory_service,
        )
        service.initialize()

        mock_memory_service.initialize.assert_called_once()


def test_works_without_memory_service(service):
    """Test service works without memory service."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker") as mock_health_class,
    ):
        # Create health checker with database component
        db_component = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database accessible",
            metadata={"size_bytes": 1024},
        )

        system_health = SystemHealth(
            status=HealthStatus.HEALTHY,
            components=[db_component],
        )

        health_result = HealthCheckResult(
            health=system_health,
            duration_ms=100.0,
        )

        mock_health = Mock()
        mock_health.check_health = AsyncMock(return_value=health_result)
        mock_health_class.return_value = mock_health

        service.initialize()

        # Should work without memory service
        import asyncio

        result = asyncio.run(service.check_database_health())

        assert "connected" in result
        # Memory count should be 0 when memory service not available
        assert result["memory_count"] == 0


# ============================================================================
# 5. Error Handling Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_async_methods_before_initialization_raise(service):
    """Test async methods raise before initialization."""
    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="not initialized"):
        await service.run_full_diagnostics()

    with pytest.raises(RuntimeError, match="not initialized"):
        await service.check_configuration()

    with pytest.raises(RuntimeError, match="not initialized"):
        await service.check_database_health()


@pytest.mark.asyncio
async def test_database_health_without_memory_service(service):
    """Test database health check works without memory service."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker") as mock_health_class,
    ):
        db_component = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database accessible",
        )

        system_health = SystemHealth(
            status=HealthStatus.HEALTHY,
            components=[db_component],
        )

        health_result = HealthCheckResult(
            health=system_health,
            duration_ms=100.0,
        )

        mock_health = Mock()
        mock_health.check_health = AsyncMock(return_value=health_result)
        mock_health_class.return_value = mock_health

        service.initialize()

        result = await service.check_database_health()

        # Should succeed without memory service
        assert result["connected"] is True
        assert result["memory_count"] == 0


@pytest.mark.asyncio
async def test_diagnostics_failures_handled_gracefully(service, mock_diagnostics):
    """Test diagnostic failures are handled gracefully."""
    with (
        patch(
            "kuzu_memory.services.diagnostic_service.MCPDiagnostics",
            return_value=mock_diagnostics,
        ),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
    ):
        # Mock check_configuration to return failure
        mock_diagnostics.check_configuration = AsyncMock(
            return_value=[
                DiagnosticResult(
                    check_name="config_check",
                    success=False,
                    severity=DiagnosticSeverity.ERROR,
                    message="Config invalid",
                    error="File not found",
                )
            ]
        )

        service.initialize()

        result = await service.check_configuration()

        # Should return result with issues
        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert "Config invalid" in result["issues"][0]


@pytest.mark.asyncio
async def test_connection_errors(service):
    """Test connection errors are handled."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker") as mock_health_class,
    ):
        # Mock health check to raise exception
        mock_health = Mock()
        mock_health.check_health = AsyncMock(side_effect=ConnectionError("Server unavailable"))
        mock_health_class.return_value = mock_health

        service.initialize()

        # Should raise the connection error
        with pytest.raises(ConnectionError):
            await service.check_database_health()


@pytest.mark.asyncio
async def test_permission_errors(service):
    """Test permission errors are handled."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch("kuzu_memory.services.diagnostic_service.MCPHealthChecker"),
        patch("subprocess.run") as mock_run,
    ):
        # Mock git check to raise PermissionError
        mock_run.side_effect = PermissionError("Access denied")

        service.initialize()

        result = await service.check_git_integration()

        # Should handle permission error gracefully
        assert result["available"] is False


# ============================================================================
# 6. Integration Tests (4 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_full_diagnostic_workflow(service, mock_diagnostics, mock_health_checker):
    """Test complete diagnostic workflow."""
    with (
        patch(
            "kuzu_memory.services.diagnostic_service.MCPDiagnostics",
            return_value=mock_diagnostics,
        ),
        patch(
            "kuzu_memory.services.diagnostic_service.MCPHealthChecker",
            return_value=mock_health_checker,
        ),
    ):
        service.initialize()

        # Run full diagnostics
        results = await service.run_full_diagnostics()

        # Verify all checks ran
        assert results["all_healthy"] is True
        assert results["configuration"]["valid"] is True
        assert results["database"]["connected"] is True

        # Format report
        report = service.format_diagnostic_report(results)

        assert "KuzuMemory Diagnostic Report" in report
        assert "HEALTHY" in report


@pytest.mark.asyncio
async def test_health_check_workflow(service, mock_health_checker):
    """Test health check workflow."""
    with (
        patch("kuzu_memory.services.diagnostic_service.MCPDiagnostics"),
        patch(
            "kuzu_memory.services.diagnostic_service.MCPHealthChecker",
            return_value=mock_health_checker,
        ),
    ):
        service.initialize()

        # Check database health
        db_result = await service.check_database_health()
        assert db_result["connected"] is True

        # Check MCP server health
        mcp_result = await service.check_mcp_server_health()
        assert mcp_result["configured"] is True


@pytest.mark.asyncio
async def test_with_all_dependencies(
    service_with_memory, mock_diagnostics, mock_health_checker, mock_memory_service
):
    """Test with all dependencies provided."""
    with (
        patch(
            "kuzu_memory.services.diagnostic_service.MCPDiagnostics",
            return_value=mock_diagnostics,
        ),
        patch(
            "kuzu_memory.services.diagnostic_service.MCPHealthChecker",
            return_value=mock_health_checker,
        ),
    ):
        service_with_memory.initialize()

        # Run diagnostics with memory service
        db_result = await service_with_memory.check_database_health()

        # Verify memory service data is included
        assert db_result["memory_count"] == 42
        assert db_result["db_size_bytes"] == 1024 * 1024


@pytest.mark.asyncio
async def test_with_minimal_dependencies(service, mock_diagnostics, mock_health_checker):
    """Test with minimal dependencies (no memory service)."""
    with (
        patch(
            "kuzu_memory.services.diagnostic_service.MCPDiagnostics",
            return_value=mock_diagnostics,
        ),
        patch(
            "kuzu_memory.services.diagnostic_service.MCPHealthChecker",
            return_value=mock_health_checker,
        ),
    ):
        service.initialize()

        # Should work with just config service
        config_result = await service.check_configuration()
        assert "valid" in config_result

        mcp_result = await service.check_mcp_server_health()
        assert "configured" in mcp_result
