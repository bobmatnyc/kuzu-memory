"""
Unit tests for MCPInstallerAdapter.

Tests the adapter layer between py-mcp-installer-service and kuzu-memory's
BaseInstaller interface.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.installers.mcp_installer_adapter import (
    HAS_MCP_INSTALLER,
    MCPInstallerAdapter,
    create_mcp_installer_adapter,
    is_mcp_installer_available,
)


@pytest.mark.skipif(
    not HAS_MCP_INSTALLER, reason="py-mcp-installer-service not available"
)
class TestMCPInstallerAdapter:
    """Test suite for MCPInstallerAdapter."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create temporary project root."""
        return tmp_path / "test_project"

    @pytest.fixture
    def mock_platform_info(self) -> Mock:
        """Create mock PlatformInfo."""
        from py_mcp_installer import Platform, Scope

        mock_info = Mock()
        mock_info.platform = Platform.CLAUDE_CODE
        mock_info.confidence = 1.0
        mock_info.config_path = Path.home() / ".config" / "claude" / "mcp.json"
        mock_info.cli_available = True
        mock_info.scope_support = Scope.BOTH
        return mock_info

    @pytest.fixture
    def mock_installer(self, mock_platform_info: Mock) -> Mock:
        """Create mock MCPInstaller."""
        mock = Mock()
        mock.platform_info = mock_platform_info
        mock.install_server = Mock()
        mock.uninstall_server = Mock()
        return mock

    def test_initialization_auto_detect(self, project_root: Path) -> None:
        """Test adapter initialization with auto-detection."""
        adapter = MCPInstallerAdapter(project_root=project_root)

        assert adapter.project_root == project_root
        assert adapter.ai_system_name is not None
        assert isinstance(adapter.installer, object)

    def test_initialization_forced_platform(self, project_root: Path) -> None:
        """Test adapter initialization with forced platform."""
        from py_mcp_installer import Platform

        adapter = MCPInstallerAdapter(
            project_root=project_root, platform=Platform.CURSOR
        )

        assert adapter.ai_system_name == "cursor"

    def test_initialization_string_platform(self, project_root: Path) -> None:
        """Test adapter initialization with string platform name."""
        adapter = MCPInstallerAdapter(project_root=project_root, platform="cursor")

        assert adapter.ai_system_name == "cursor"

    def test_initialization_invalid_platform(self, project_root: Path) -> None:
        """Test adapter initialization with invalid platform string."""
        with pytest.raises(ValueError, match="Invalid platform"):
            MCPInstallerAdapter(project_root=project_root, platform="invalid-platform")

    def test_ai_system_name(self, project_root: Path) -> None:
        """Test ai_system_name property."""
        from py_mcp_installer import Platform

        adapter = MCPInstallerAdapter(
            project_root=project_root, platform=Platform.CLAUDE_CODE
        )

        assert adapter.ai_system_name == "claude-code"

    def test_required_files_with_config_path(
        self, project_root: Path, mock_platform_info: Mock
    ) -> None:
        """Test required_files when config_path exists."""
        with patch(
            "kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"
        ) as mock_installer_class:
            mock_installer_class.return_value.platform_info = mock_platform_info

            adapter = MCPInstallerAdapter(project_root=project_root)
            files = adapter.required_files

            # Config path should be included
            assert len(files) > 0
            assert isinstance(files[0], str)

    def test_description(self, project_root: Path) -> None:
        """Test description property."""
        adapter = MCPInstallerAdapter(project_root=project_root)

        description = adapter.description
        assert "py-mcp-installer-service" in description
        assert adapter.ai_system_name in description

    def test_install_success(self, project_root: Path) -> None:
        """Test successful installation."""
        from py_mcp_installer import InstallationResult as PyMCPResult
        from py_mcp_installer import Platform

        mock_result = Mock(spec=PyMCPResult)
        mock_result.success = True
        mock_result.platform = Platform.CLAUDE_CODE
        mock_result.server_name = "kuzu-memory"
        mock_result.message = "Successfully installed"
        mock_result.config_path = Path.home() / ".config" / "claude" / "mcp.json"
        mock_result.error = None

        with patch(
            "kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"
        ) as mock_installer_class:
            mock_installer = mock_installer_class.return_value
            mock_installer.install_server.return_value = mock_result

            adapter = MCPInstallerAdapter(project_root=project_root)
            result = adapter.install(force=False, dry_run=True)

            assert result.success is True
            assert result.ai_system == "claude-code"
            assert result.message == "Successfully installed"

    def test_install_with_custom_args(self, project_root: Path) -> None:
        """Test installation with custom arguments."""
        from py_mcp_installer import InstallationResult as PyMCPResult
        from py_mcp_installer import Platform

        mock_result = Mock(spec=PyMCPResult)
        mock_result.success = True
        mock_result.platform = Platform.CURSOR
        mock_result.server_name = "kuzu-memory"
        mock_result.message = "Installed"
        mock_result.config_path = Path.cwd() / ".cursor" / "mcp.json"
        mock_result.error = None

        with patch(
            "kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"
        ) as mock_installer_class:
            mock_installer = mock_installer_class.return_value
            mock_installer.install_server.return_value = mock_result

            adapter = MCPInstallerAdapter(project_root=project_root)
            adapter.install(
                server_name="custom-server",
                command="python",
                args=["-m", "custom_server"],
                env={"API_KEY": "test"},
                description="Custom server",
                scope="global",
                method="python_module",
            )

            # Verify install_server was called with correct arguments
            mock_installer.install_server.assert_called_once()
            call_args = mock_installer.install_server.call_args
            assert call_args.kwargs["name"] == "custom-server"
            assert call_args.kwargs["command"] == "python"

    def test_install_failure(self, project_root: Path) -> None:
        """Test installation failure."""
        with patch(
            "kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"
        ) as mock_installer_class:
            mock_installer = mock_installer_class.return_value
            mock_installer.install_server.side_effect = Exception("Installation error")

            adapter = MCPInstallerAdapter(project_root=project_root)
            result = adapter.install()

            assert result.success is False
            assert "Installation failed" in result.message

    def test_uninstall_success(self, project_root: Path) -> None:
        """Test successful uninstallation."""
        from py_mcp_installer import InstallationResult as PyMCPResult
        from py_mcp_installer import Platform

        mock_result = Mock(spec=PyMCPResult)
        mock_result.success = True
        mock_result.platform = Platform.CLAUDE_CODE
        mock_result.server_name = "kuzu-memory"
        mock_result.message = "Successfully uninstalled"
        mock_result.config_path = None
        mock_result.error = None

        with patch(
            "kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"
        ) as mock_installer_class:
            mock_installer = mock_installer_class.return_value
            mock_installer.uninstall_server.return_value = mock_result

            adapter = MCPInstallerAdapter(project_root=project_root)
            result = adapter.uninstall()

            assert result.success is True
            assert result.message == "Successfully uninstalled"

    def test_detect_installation_installed(self, project_root: Path) -> None:
        """Test detection of installed system."""
        from py_mcp_installer import InspectionReport, Platform

        # Create mock inspection report
        mock_report = Mock(spec=InspectionReport)
        mock_report.is_valid = True
        mock_report.server_names = ["kuzu-memory", "other-server"]

        with (
            patch(
                "kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"
            ) as mock_installer_class,
            patch(
                "kuzu_memory.installers.mcp_installer_adapter.MCPInspector"
            ) as mock_inspector_class,
        ):
            # Set up platform info properly
            mock_platform_info = Mock()
            mock_platform_info.platform = Platform.CLAUDE_CODE
            mock_platform_info.config_path = (
                project_root / ".config" / "claude" / "mcp.json"
            )
            mock_platform_info.cli_available = True
            mock_platform_info.confidence = 1.0

            mock_installer = mock_installer_class.return_value
            mock_installer.platform_info = mock_platform_info

            mock_inspector = mock_inspector_class.return_value
            mock_inspector.inspect_installation.return_value = mock_report

            adapter = MCPInstallerAdapter(project_root=project_root)
            installed_system = adapter.detect_installation()

            # Should detect installation
            assert isinstance(installed_system.ai_system, str)
            assert installed_system.ai_system == "claude-code"

    def test_run_diagnostics(self, project_root: Path) -> None:
        """Test running diagnostics."""
        from py_mcp_installer import DiagnosticReport, DiagnosticStatus

        # Create mock diagnostic report
        mock_report = Mock(spec=DiagnosticReport)
        mock_report.status = DiagnosticStatus.HEALTHY
        mock_report.platform = Mock()
        mock_report.platform.value = "claude_code"
        mock_report.checks_total = 10
        mock_report.checks_passed = 10
        mock_report.checks_failed = 0
        mock_report.issues = []
        mock_report.server_reports = {}
        mock_report.recommendations = []

        with (
            patch("kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"),
            patch(
                "kuzu_memory.installers.mcp_installer_adapter.MCPDoctor"
            ) as mock_doctor_class,
        ):
            mock_doctor = mock_doctor_class.return_value
            mock_doctor.diagnose.return_value = mock_report

            adapter = MCPInstallerAdapter(project_root=project_root)
            diagnostics = adapter.run_diagnostics(full=True)

            assert diagnostics["success"] is True
            assert diagnostics["status"] == "healthy"
            assert diagnostics["checks_total"] == 10

    def test_inspect_config(self, project_root: Path) -> None:
        """Test configuration inspection."""
        from py_mcp_installer import InspectionReport

        # Create mock inspection report
        mock_report = Mock(spec=InspectionReport)
        mock_report.platform = Mock()
        mock_report.platform.value = "cursor"
        mock_report.config_path = Path.cwd() / ".cursor" / "mcp.json"
        mock_report.is_valid = True
        mock_report.server_count = 2
        mock_report.server_names = ["kuzu-memory", "other-server"]
        mock_report.issues = []
        mock_report.summary = "All servers configured correctly"

        with (
            patch("kuzu_memory.installers.mcp_installer_adapter.MCPInstaller"),
            patch(
                "kuzu_memory.installers.mcp_installer_adapter.MCPInspector"
            ) as mock_inspector_class,
        ):
            mock_inspector = mock_inspector_class.return_value
            mock_inspector.inspect_installation.return_value = mock_report

            adapter = MCPInstallerAdapter(project_root=project_root)
            inspection = adapter.inspect_config()

            assert inspection["success"] is True
            assert inspection["is_valid"] is True
            assert inspection["server_count"] == 2


class TestConvenienceFunctions:
    """Test convenience factory functions."""

    @pytest.mark.skipif(
        not HAS_MCP_INSTALLER, reason="py-mcp-installer-service not available"
    )
    def test_create_mcp_installer_adapter(self, tmp_path: Path) -> None:
        """Test factory function."""
        adapter = create_mcp_installer_adapter(project_root=tmp_path)

        assert isinstance(adapter, MCPInstallerAdapter)
        assert adapter.project_root == tmp_path

    def test_is_mcp_installer_available(self) -> None:
        """Test availability check function."""
        available = is_mcp_installer_available()

        assert isinstance(available, bool)
        assert available == HAS_MCP_INSTALLER


class TestMCPInstallerNotAvailable:
    """Test behavior when py-mcp-installer-service is not available."""

    @pytest.mark.skipif(
        HAS_MCP_INSTALLER, reason="py-mcp-installer-service is available"
    )
    def test_initialization_without_submodule(self, tmp_path: Path) -> None:
        """Test initialization fails gracefully without submodule."""
        with pytest.raises(
            RuntimeError, match="py-mcp-installer-service is not available"
        ):
            MCPInstallerAdapter(project_root=tmp_path)

    @pytest.mark.skipif(
        HAS_MCP_INSTALLER, reason="py-mcp-installer-service is available"
    )
    def test_is_available_returns_false(self) -> None:
        """Test is_available returns False when submodule missing."""
        assert is_mcp_installer_available() is False
