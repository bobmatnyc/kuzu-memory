"""
Unit tests for InstallerService with mocked dependencies.

Tests the InstallerService implementation using mock objects to verify
correct delegation to installer registry and config service.

Test Strategy:
- Mock IConfigService and InstallerRegistry
- Verify method delegation with correct parameters
- Verify lifecycle management (initialize/cleanup)
- Verify error handling and edge cases
- Verify installer discovery and health checking

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Task: 1M-422 (Implement InstallerService)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest
from kuzu_memory.installers.base import InstallationResult, InstalledSystem
from kuzu_memory.services.installer_service import InstallerService


@pytest.fixture
def mock_config_service():
    """Mock IConfigService implementation."""
    mock = MagicMock()
    mock.get_project_root.return_value = Path("/test/project")
    return mock


@pytest.fixture
def mock_installer():
    """Mock BaseInstaller implementation."""
    mock = MagicMock()
    mock.ai_system_name = "test-integration"
    mock.description = "Test integration installer"
    return mock


@pytest.fixture
def mock_registry(mock_installer):
    """Mock InstallerRegistry."""
    mock = MagicMock()
    mock.get_installer_names.return_value = ["test-integration", "another-integration"]
    mock.get_installer.return_value = mock_installer
    mock.list_installers.return_value = [
        {
            "name": "test-integration",
            "ai_system": "TestAI",
            "description": "Test integration",
            "class": "TestInstaller",
        }
    ]
    return mock


@pytest.fixture
def installer_service(mock_config_service):
    """InstallerService instance with mocked dependencies."""
    service = InstallerService(config_service=mock_config_service)
    service.initialize()
    yield service
    service.cleanup()


class TestInstallerServiceLifecycle:
    """Test lifecycle management (initialize/cleanup)."""

    def test_initialization_creates_registry(self, mock_config_service):
        """Test initialization creates InstallerRegistry."""
        service = InstallerService(config_service=mock_config_service)
        assert not service.is_initialized

        service.initialize()
        assert service.is_initialized
        assert service._registry is not None

        service.cleanup()

    def test_cleanup_clears_registry(self, installer_service):
        """Test cleanup clears registry reference."""
        # Access registry to ensure it's initialized
        _ = installer_service.registry

        installer_service.cleanup()

        assert not installer_service.is_initialized
        assert installer_service._registry is None

    def test_double_initialization_is_safe(self, mock_config_service):
        """Test that double initialization is safe and idempotent."""
        service = InstallerService(config_service=mock_config_service)

        service.initialize()
        first_registry = service._registry

        service.initialize()  # Should be no-op
        second_registry = service._registry

        assert first_registry is second_registry
        service.cleanup()

    def test_registry_property_before_initialization_raises(self, mock_config_service):
        """Test accessing registry before initialization raises RuntimeError."""
        service = InstallerService(config_service=mock_config_service)

        with pytest.raises(RuntimeError, match="not initialized"):
            _ = service.registry

    def test_registry_property_returns_registry(self, installer_service):
        """Test registry property returns InstallerRegistry instance."""
        registry = installer_service.registry
        assert registry is not None


class TestInstallerServiceDiscovery:
    """Test installer discovery."""

    def test_discover_installers_returns_names(self, installer_service, mock_registry):
        """Test discover_installers returns list of installer names."""
        with patch.object(installer_service, "_registry", mock_registry):
            names = installer_service.discover_installers()

        assert names == ["test-integration", "another-integration"]
        mock_registry.get_installer_names.assert_called_once()

    def test_list_all_installers_returns_metadata(self, installer_service, mock_registry):
        """Test list_all_installers returns installer metadata."""
        with patch.object(installer_service, "_registry", mock_registry):
            installers = installer_service.list_all_installers()

        assert len(installers) == 1
        assert installers[0]["name"] == "test-integration"
        assert installers[0]["ai_system"] == "TestAI"
        mock_registry.list_installers.assert_called_once()


class TestInstallerServiceInstall:
    """Test installation operations."""

    def test_install_success(
        self, installer_service, mock_registry, mock_installer, mock_config_service
    ):
        """Test successful installation."""
        # Mock successful installation result
        success_result = InstallationResult(
            success=True,
            ai_system="test-integration",
            files_created=[Path("/test/file")],
            files_modified=[],
            backup_files=[],
            message="Installation successful",
            warnings=[],
        )
        mock_installer.install.return_value = success_result

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.install("test-integration", force=True, verbose=True)

        assert result is True
        mock_config_service.get_project_root.assert_called()
        mock_registry.get_installer.assert_called_once_with(
            "test-integration", Path("/test/project")
        )
        mock_installer.install.assert_called_once_with(force=True, dry_run=False, verbose=True)

    def test_install_failure(self, installer_service, mock_registry, mock_installer):
        """Test failed installation."""
        # Mock failed installation result
        failure_result = InstallationResult(
            success=False,
            ai_system="test-integration",
            files_created=[],
            files_modified=[],
            backup_files=[],
            message="Installation failed",
            warnings=["Error occurred"],
        )
        mock_installer.install.return_value = failure_result

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.install("test-integration")

        assert result is False

    def test_install_unknown_integration(self, installer_service, mock_registry):
        """Test installation with unknown integration."""
        mock_registry.get_installer.return_value = None

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.install("unknown-integration")

        assert result is False

    def test_install_with_exception(self, installer_service, mock_registry, mock_installer):
        """Test installation handles exceptions gracefully."""
        mock_installer.install.side_effect = Exception("Installation error")

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.install("test-integration")

        assert result is False

    def test_install_with_dry_run(self, installer_service, mock_registry, mock_installer):
        """Test installation with dry_run flag."""
        success_result = InstallationResult(
            success=True,
            ai_system="test-integration",
            files_created=[],
            files_modified=[],
            backup_files=[],
            message="Dry run successful",
            warnings=[],
        )
        mock_installer.install.return_value = success_result

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.install("test-integration", dry_run=True)

        assert result is True
        mock_installer.install.assert_called_once_with(force=False, dry_run=True, verbose=False)

    def test_install_with_kwargs(self, installer_service, mock_registry, mock_installer):
        """Test installation with additional kwargs."""
        success_result = InstallationResult(
            success=True,
            ai_system="test-integration",
            files_created=[],
            files_modified=[],
            backup_files=[],
            message="Installation successful",
            warnings=[],
        )
        mock_installer.install.return_value = success_result

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.install("test-integration", custom_arg="value")

        assert result is True
        mock_installer.install.assert_called_once_with(
            force=False, dry_run=False, verbose=False, custom_arg="value"
        )


class TestInstallerServiceUninstall:
    """Test uninstallation operations."""

    def test_uninstall_success(
        self, installer_service, mock_registry, mock_installer, mock_config_service
    ):
        """Test successful uninstallation."""
        success_result = InstallationResult(
            success=True,
            ai_system="test-integration",
            files_created=[],
            files_modified=[Path("/test/restored")],
            backup_files=[],
            message="Uninstallation successful",
            warnings=[],
        )
        mock_installer.uninstall.return_value = success_result

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.uninstall("test-integration")

        assert result is True
        mock_config_service.get_project_root.assert_called()
        mock_registry.get_installer.assert_called_once_with(
            "test-integration", Path("/test/project")
        )
        mock_installer.uninstall.assert_called_once()

    def test_uninstall_failure(self, installer_service, mock_registry, mock_installer):
        """Test failed uninstallation."""
        failure_result = InstallationResult(
            success=False,
            ai_system="test-integration",
            files_created=[],
            files_modified=[],
            backup_files=[],
            message="Uninstallation failed",
            warnings=["Error occurred"],
        )
        mock_installer.uninstall.return_value = failure_result

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.uninstall("test-integration")

        assert result is False

    def test_uninstall_unknown_integration(self, installer_service, mock_registry):
        """Test uninstallation with unknown integration."""
        mock_registry.get_installer.return_value = None

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.uninstall("unknown-integration")

        assert result is False

    def test_uninstall_with_exception(self, installer_service, mock_registry, mock_installer):
        """Test uninstallation handles exceptions gracefully."""
        mock_installer.uninstall.side_effect = Exception("Uninstallation error")

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.uninstall("test-integration")

        assert result is False

    def test_uninstall_with_kwargs(self, installer_service, mock_registry, mock_installer):
        """Test uninstallation with additional kwargs."""
        success_result = InstallationResult(
            success=True,
            ai_system="test-integration",
            files_created=[],
            files_modified=[],
            backup_files=[],
            message="Uninstallation successful",
            warnings=[],
        )
        mock_installer.uninstall.return_value = success_result

        with patch.object(installer_service, "_registry", mock_registry):
            result = installer_service.uninstall("test-integration", custom_arg="value")

        assert result is True
        mock_installer.uninstall.assert_called_once_with(custom_arg="value")


class TestInstallerServiceHealthCheck:
    """Test health checking operations."""

    def test_check_health_healthy_installation(
        self, installer_service, mock_registry, mock_installer
    ):
        """Test health check for healthy installation."""
        detected = InstalledSystem(
            name="test-integration",
            ai_system="TestAI",
            is_installed=True,
            health_status="healthy",
            files_present=[Path("/test/file1")],
            files_missing=[],
            has_mcp=True,
            details={"total_files": 1, "present_count": 1, "missing_count": 0},
        )
        mock_installer.detect_installation.return_value = detected

        with patch.object(installer_service, "_registry", mock_registry):
            health = installer_service.check_health("test-integration")

        assert health["installed"] is True
        assert health["healthy"] is True
        assert health["details"]["health_status"] == "healthy"
        assert health["details"]["has_mcp"] is True

    def test_check_health_needs_repair(self, installer_service, mock_registry, mock_installer):
        """Test health check for installation needing repair."""
        detected = InstalledSystem(
            name="test-integration",
            ai_system="TestAI",
            is_installed=True,
            health_status="needs_repair",
            files_present=[Path("/test/file1")],
            files_missing=[Path("/test/file2")],
            has_mcp=False,
            details={"total_files": 2, "present_count": 1, "missing_count": 1},
        )
        mock_installer.detect_installation.return_value = detected

        with patch.object(installer_service, "_registry", mock_registry):
            health = installer_service.check_health("test-integration")

        assert health["installed"] is True
        assert health["healthy"] is False
        assert health["details"]["health_status"] == "needs_repair"
        assert health["details"]["files_missing"] == 1

    def test_check_health_not_installed(self, installer_service, mock_registry, mock_installer):
        """Test health check for not installed integration."""
        detected = InstalledSystem(
            name="test-integration",
            ai_system="TestAI",
            is_installed=False,
            health_status="not_installed",
            files_present=[],
            files_missing=[Path("/test/file1")],
            has_mcp=False,
            details={"total_files": 1, "present_count": 0, "missing_count": 1},
        )
        mock_installer.detect_installation.return_value = detected

        with patch.object(installer_service, "_registry", mock_registry):
            health = installer_service.check_health("test-integration")

        assert health["installed"] is False
        assert health["healthy"] is False

    def test_check_health_unknown_integration(self, installer_service, mock_registry):
        """Test health check for unknown integration."""
        mock_registry.get_installer.return_value = None

        with patch.object(installer_service, "_registry", mock_registry):
            health = installer_service.check_health("unknown-integration")

        assert health["installed"] is False
        assert health["healthy"] is False
        assert "Unknown integration" in health["details"]["error"]

    def test_check_health_with_exception(self, installer_service, mock_registry, mock_installer):
        """Test health check handles exceptions gracefully."""
        mock_installer.detect_installation.side_effect = Exception("Detection error")

        with patch.object(installer_service, "_registry", mock_registry):
            health = installer_service.check_health("test-integration")

        assert health["installed"] is False
        assert health["healthy"] is False
        assert "error" in health["details"]


class TestInstallerServiceMCPRepair:
    """Test MCP configuration repair."""

    @patch("kuzu_memory.services.installer_service.load_json_config")
    @patch("kuzu_memory.services.installer_service.save_json_config")
    @patch("kuzu_memory.services.installer_service.fix_broken_mcp_args")
    def test_repair_mcp_config_with_fixes(
        self, mock_fix_args, mock_save, mock_load, installer_service
    ):
        """Test MCP config repair when fixes are needed."""
        original_config = {"mcpServers": {"server1": {"args": ["broken"]}}}
        fixed_config = {"mcpServers": {"server1": {"args": ["fixed"]}}}
        fixes = ["Fixed broken args for server1"]

        mock_load.return_value = original_config
        mock_fix_args.return_value = (fixed_config, fixes)

        with patch.object(Path, "exists", return_value=True):
            result = installer_service.repair_mcp_config()

        assert result is True
        mock_load.assert_called_once()
        mock_fix_args.assert_called_once_with(original_config)
        mock_save.assert_called_once()

    @patch("kuzu_memory.services.installer_service.load_json_config")
    @patch("kuzu_memory.services.installer_service.fix_broken_mcp_args")
    def test_repair_mcp_config_no_fixes_needed(self, mock_fix_args, mock_load, installer_service):
        """Test MCP config repair when no fixes needed."""
        config = {"mcpServers": {"server1": {"args": ["correct"]}}}
        mock_load.return_value = config
        mock_fix_args.return_value = (config, [])  # No fixes

        with patch.object(Path, "exists", return_value=True):
            result = installer_service.repair_mcp_config()

        assert result is True
        mock_load.assert_called_once()
        mock_fix_args.assert_called_once()

    def test_repair_mcp_config_file_not_exists(self, installer_service):
        """Test MCP config repair when config file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            result = installer_service.repair_mcp_config()

        assert result is True  # Not an error if file doesn't exist

    @patch("kuzu_memory.services.installer_service.load_json_config")
    def test_repair_mcp_config_with_exception(self, mock_load, installer_service):
        """Test MCP config repair handles exceptions gracefully."""
        mock_load.side_effect = Exception("Load error")

        with patch.object(Path, "exists", return_value=True):
            result = installer_service.repair_mcp_config()

        assert result is False


class TestInstallerServiceUtilityMethods:
    """Test additional utility methods."""

    def test_get_installer_instance_returns_installer(
        self, installer_service, mock_registry, mock_installer, mock_config_service
    ):
        """Test get_installer_instance returns installer instance."""
        with patch.object(installer_service, "_registry", mock_registry):
            installer = installer_service.get_installer_instance("test-integration")

        assert installer == mock_installer
        mock_config_service.get_project_root.assert_called()
        mock_registry.get_installer.assert_called_once_with(
            "test-integration", Path("/test/project")
        )

    def test_get_installer_instance_unknown_integration(self, installer_service, mock_registry):
        """Test get_installer_instance returns None for unknown integration."""
        mock_registry.get_installer.return_value = None

        with patch.object(installer_service, "_registry", mock_registry):
            installer = installer_service.get_installer_instance("unknown-integration")

        assert installer is None


class TestInstallerServiceContextManager:
    """Test context manager behavior."""

    def test_context_manager_initializes_and_cleans_up(self, mock_config_service):
        """Test context manager properly initializes and cleans up."""
        with InstallerService(config_service=mock_config_service) as service:
            assert service.is_initialized
            assert service._registry is not None

        # After exiting context, should be cleaned up
        assert not service.is_initialized
        assert service._registry is None
