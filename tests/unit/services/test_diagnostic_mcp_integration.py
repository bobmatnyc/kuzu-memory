"""Tests for DiagnosticService MCP installation integration."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kuzu_memory.protocols.services import IConfigService
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


# ============================================================================
# Tests - check_mcp_installation
# ============================================================================


async def test_check_mcp_installation_when_unavailable(mock_config_service):
    """Test check_mcp_installation when MCPInstallerAdapter is unavailable."""
    # Create service
    service = DiagnosticService(mock_config_service)
    service.initialize()

    try:
        # Mock HAS_MCP_INSTALLER to False
        with patch("kuzu_memory.services.diagnostic_service.HAS_MCP_INSTALLER", False):
            result = await service.check_mcp_installation()

            # Verify result structure
            assert result["available"] is False
            assert result["status"] == "unavailable"
            assert result["platform"] == "unknown"
            assert result["checks_total"] == 0
            assert result["checks_passed"] == 0
            assert len(result["issues"]) > 0
            assert len(result["recommendations"]) > 0

            # Verify warning message
            assert any(
                "submodule" in issue["message"].lower() for issue in result["issues"]
            )

    finally:
        service.cleanup()


async def test_check_mcp_installation_when_available(mock_config_service):
    """Test check_mcp_installation when MCPInstallerAdapter is available."""
    # Create service
    service = DiagnosticService(mock_config_service)
    service.initialize()

    try:
        # Mock MCPInstallerAdapter
        mock_adapter = Mock()
        mock_adapter.ai_system_name = "claude-code"
        mock_adapter.run_diagnostics.return_value = {
            "success": True,
            "status": "healthy",
            "checks_total": 5,
            "checks_passed": 5,
            "issues": [],
            "server_reports": {},
            "recommendations": [],
        }

        # Patch both HAS_MCP_INSTALLER and MCPInstallerAdapter
        with (
            patch("kuzu_memory.services.diagnostic_service.HAS_MCP_INSTALLER", True),
            patch(
                "kuzu_memory.services.diagnostic_service.MCPInstallerAdapter",
                return_value=mock_adapter,
            ),
        ):
            result = await service.check_mcp_installation(full=False)

            # Verify result structure
            assert result["available"] is True
            assert result["status"] == "healthy"
            assert result["platform"] == "claude-code"
            assert result["checks_total"] == 5
            assert result["checks_passed"] == 5
            assert len(result["issues"]) == 0

            # Verify adapter was created and called
            mock_adapter.run_diagnostics.assert_called_once_with(full=False)

    finally:
        service.cleanup()


async def test_check_mcp_installation_full_mode(mock_config_service):
    """Test check_mcp_installation with full protocol tests."""
    # Create service
    service = DiagnosticService(mock_config_service)
    service.initialize()

    try:
        # Mock MCPInstallerAdapter
        mock_adapter = Mock()
        mock_adapter.ai_system_name = "claude-code"
        mock_adapter.run_diagnostics.return_value = {
            "success": True,
            "status": "healthy",
            "checks_total": 10,
            "checks_passed": 9,
            "issues": [{"severity": "warning", "message": "Server response time high"}],
            "server_reports": {"kuzu-memory": {"status": "healthy"}},
            "recommendations": ["Consider optimizing server startup"],
        }

        # Patch both HAS_MCP_INSTALLER and MCPInstallerAdapter
        with (
            patch("kuzu_memory.services.diagnostic_service.HAS_MCP_INSTALLER", True),
            patch(
                "kuzu_memory.services.diagnostic_service.MCPInstallerAdapter",
                return_value=mock_adapter,
            ),
        ):
            result = await service.check_mcp_installation(full=True)

            # Verify result structure
            assert result["available"] is True
            assert result["status"] == "healthy"
            assert result["checks_total"] == 10
            assert result["checks_passed"] == 9
            assert len(result["issues"]) == 1
            assert len(result["recommendations"]) == 1

            # Verify full mode was requested
            mock_adapter.run_diagnostics.assert_called_once_with(full=True)

    finally:
        service.cleanup()


async def test_check_mcp_installation_handles_errors(mock_config_service):
    """Test check_mcp_installation handles adapter errors gracefully."""
    # Create service
    service = DiagnosticService(mock_config_service)
    service.initialize()

    try:
        # Mock MCPInstallerAdapter to raise exception
        with (
            patch("kuzu_memory.services.diagnostic_service.HAS_MCP_INSTALLER", True),
            patch(
                "kuzu_memory.services.diagnostic_service.MCPInstallerAdapter",
                side_effect=RuntimeError("Adapter initialization failed"),
            ),
        ):
            result = await service.check_mcp_installation()

            # Verify error handling
            assert result["available"] is True
            assert result["status"] == "error"
            assert result["platform"] == "unknown"
            assert len(result["issues"]) > 0
            assert any(
                "failed" in issue["message"].lower() for issue in result["issues"]
            )

    finally:
        service.cleanup()


# ============================================================================
# Tests - run_full_diagnostics integration
# ============================================================================


async def test_run_full_diagnostics_includes_mcp_installation(mock_config_service):
    """Test that run_full_diagnostics includes MCP installation check."""
    # Create service
    service = DiagnosticService(mock_config_service)
    service.initialize()

    try:
        # Mock MCPInstallerAdapter
        mock_adapter = Mock()
        mock_adapter.ai_system_name = "claude-code"
        mock_adapter.run_diagnostics.return_value = {
            "success": True,
            "status": "healthy",
            "checks_total": 5,
            "checks_passed": 5,
            "issues": [],
            "server_reports": {},
            "recommendations": [],
        }

        # Patch HAS_MCP_INSTALLER and MCPInstallerAdapter
        with (
            patch("kuzu_memory.services.diagnostic_service.HAS_MCP_INSTALLER", True),
            patch(
                "kuzu_memory.services.diagnostic_service.MCPInstallerAdapter",
                return_value=mock_adapter,
            ),
        ):
            # Run full diagnostics
            results = await service.run_full_diagnostics()

            # Verify mcp_installation is included in results
            assert "mcp_installation" in results
            assert results["mcp_installation"]["available"] is True
            assert results["mcp_installation"]["status"] == "healthy"
            assert results["mcp_installation"]["platform"] == "claude-code"

    finally:
        service.cleanup()


# ============================================================================
# Tests - format_diagnostic_report integration
# ============================================================================


def test_format_diagnostic_report_includes_mcp_section(mock_config_service):
    """Test that format_diagnostic_report includes MCP Installation section."""
    # Create service
    service = DiagnosticService(mock_config_service)
    service.initialize()

    try:
        # Create mock results with MCP installation data
        results = {
            "all_healthy": True,
            "timestamp": "2024-01-01 12:00:00",
            "configuration": {"valid": True, "issues": []},
            "database": {"connected": True, "issues": []},
            "mcp_server": {"configured": True, "issues": []},
            "git_integration": {"available": True, "issues": []},
            "system_info": {"version": "1.6.2"},
            "dependencies": {"all_satisfied": True, "missing": []},
            "mcp_installation": {
                "available": True,
                "status": "healthy",
                "platform": "claude-code",
                "checks_total": 5,
                "checks_passed": 5,
                "issues": [],
                "recommendations": [],
            },
            "total_checks": 20,
            "passed_checks": 20,
            "failed_checks": 0,
            "success_rate": 100.0,
        }

        # Format report
        report = service.format_diagnostic_report(results)

        # Verify MCP Installation section exists
        assert "MCP INSTALLATION" in report
        assert "Status: ✓ HEALTHY" in report
        assert "Platform: claude-code" in report
        assert "Checks: 5/5 passed" in report

    finally:
        service.cleanup()


def test_format_diagnostic_report_when_mcp_unavailable(mock_config_service):
    """Test format_diagnostic_report when MCP adapter is unavailable."""
    # Create service
    service = DiagnosticService(mock_config_service)
    service.initialize()

    try:
        # Create mock results with unavailable MCP
        results = {
            "all_healthy": True,
            "timestamp": "2024-01-01 12:00:00",
            "configuration": {"valid": True, "issues": []},
            "database": {"connected": True, "issues": []},
            "mcp_server": {"configured": True, "issues": []},
            "git_integration": {"available": True, "issues": []},
            "system_info": {"version": "1.6.2"},
            "dependencies": {"all_satisfied": True, "missing": []},
            "mcp_installation": {
                "available": False,
                "status": "unavailable",
                "platform": "unknown",
            },
            "total_checks": 15,
            "passed_checks": 15,
            "failed_checks": 0,
            "success_rate": 100.0,
        }

        # Format report
        report = service.format_diagnostic_report(results)

        # Verify MCP Installation section shows unavailable
        assert "MCP INSTALLATION" in report
        assert "MCPInstallerAdapter not available" in report
        assert "submodule" in report

    finally:
        service.cleanup()
