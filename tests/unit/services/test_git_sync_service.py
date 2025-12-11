"""Tests for GitSyncService."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.core.config import GitSyncConfig
from kuzu_memory.integrations.git_sync import GitSyncManager
from kuzu_memory.protocols.services import IConfigService
from kuzu_memory.services.git_sync_service import GitSyncService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config_service():
    """Create mock config service."""
    # Don't use spec since we need BaseService methods (initialize, is_initialized)
    mock = Mock()
    mock.is_initialized = False
    mock.initialize = Mock()
    mock.get_project_root.return_value = Path("/fake/project")
    return mock


@pytest.fixture
def mock_git_sync_manager():
    """Create mock GitSyncManager."""
    mock = Mock(spec=GitSyncManager)
    mock.is_available.return_value = True
    mock.sync.return_value = {"commits_synced": 5, "success": True}
    mock.get_sync_status.return_value = {
        "available": True,
        "enabled": True,
        "last_sync_timestamp": "2024-01-01T00:00:00",
        "repo_path": "/fake/project",
    }
    return mock


@pytest.fixture
def service(mock_config_service):
    """Create GitSyncService instance."""
    return GitSyncService(config_service=mock_config_service)


# ============================================================================
# 1. Lifecycle Tests (5 tests)
# ============================================================================


def test_initialization_creates_git_sync_manager(mock_config_service):
    """Test that initialization creates GitSyncManager instance."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager"
    ) as mock_manager_class:
        service = GitSyncService(config_service=mock_config_service)
        service.initialize()

        # Verify config service was initialized
        mock_config_service.initialize.assert_called_once()

        # Verify GitSyncManager was created with correct args
        mock_manager_class.assert_called_once()
        call_args = mock_manager_class.call_args
        assert call_args[1]["repo_path"] == Path("/fake/project")
        assert isinstance(call_args[1]["config"], GitSyncConfig)
        assert call_args[1]["memory_store"] is None

        # Verify service is marked as initialized
        assert service.is_initialized


def test_cleanup_nullifies_manager(service, mock_config_service):
    """Test that cleanup nullifies GitSyncManager."""
    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service.initialize()
        assert service._git_sync is not None

        service.cleanup()
        assert service._git_sync is None
        assert not service.is_initialized


def test_context_manager_lifecycle(mock_config_service):
    """Test context manager handles initialization and cleanup."""
    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service = GitSyncService(config_service=mock_config_service)

        assert not service.is_initialized

        with service as svc:
            assert svc.is_initialized
            assert svc is service

        # After context exit, should be cleaned up
        assert not service.is_initialized


def test_double_initialization_is_safe(service, mock_config_service):
    """Test that double initialization is safe (no-op)."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager"
    ) as mock_manager_class:
        service.initialize()
        first_manager = service._git_sync

        service.initialize()  # Second initialization
        second_manager = service._git_sync

        # Should be same instance (no re-initialization)
        assert first_manager is second_manager
        # GitSyncManager constructor should only be called once
        assert mock_manager_class.call_count == 1


def test_double_cleanup_is_safe(service):
    """Test that double cleanup is safe (no-op)."""
    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service.initialize()
        service.cleanup()

        # Second cleanup should not raise
        service.cleanup()

        assert not service.is_initialized


# ============================================================================
# 2. Delegation Tests (6 tests - one per method)
# ============================================================================


def test_initialize_sync_delegates_to_manager(service, mock_git_sync_manager):
    """Test initialize_sync checks manager availability."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        service.initialize()

        result = service.initialize_sync()

        # Should check availability
        mock_git_sync_manager.is_available.assert_called_once()
        assert result is True


def test_sync_delegates_to_manager(service, mock_git_sync_manager):
    """Test sync delegates to GitSyncManager.sync()."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        service.initialize()

        result = service.sync(since="2024-01-01", max_commits=50)

        # Should call manager sync with auto mode
        mock_git_sync_manager.sync.assert_called_once_with(mode="auto", dry_run=False)
        # Should return commits_synced count
        assert result == 5


def test_is_available_delegates_to_manager(service, mock_git_sync_manager):
    """Test is_available delegates to GitSyncManager.is_available()."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        service.initialize()

        result = service.is_available()

        mock_git_sync_manager.is_available.assert_called_once()
        assert result is True


def test_get_sync_status_delegates_to_manager(service, mock_git_sync_manager):
    """Test get_sync_status delegates to manager and adds hooks status."""
    with (
        patch(
            "kuzu_memory.services.git_sync_service.GitSyncManager",
            return_value=mock_git_sync_manager,
        ),
        patch.object(service, "_check_hooks_installed", return_value=True),
    ):
        service.initialize()

        status = service.get_sync_status()

        mock_git_sync_manager.get_sync_status.assert_called_once()
        # Should include base status from manager
        assert status["available"] is True
        assert status["enabled"] is True
        # Should add hooks_installed
        assert "hooks_installed" in status
        assert status["hooks_installed"] is True


def test_install_hooks_handles_git_directory(service, tmp_path):
    """Test install_hooks creates git hook file."""
    # Create fake git directory
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    mock_config_service = Mock()
    mock_config_service.is_initialized = False
    mock_config_service.initialize = Mock()
    mock_config_service.get_project_root.return_value = tmp_path

    service = GitSyncService(config_service=mock_config_service)

    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service.initialize()

        result = service.install_hooks()

        assert result is True
        hook_file = hooks_dir / "post-commit"
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111  # Executable
        content = hook_file.read_text()
        assert "KuzuMemory" in content


def test_uninstall_hooks_removes_hook_file(service, tmp_path):
    """Test uninstall_hooks removes git hook file."""
    # Create fake git directory with hook
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)
    hook_file = hooks_dir / "post-commit"
    hook_file.write_text("#!/bin/sh\n# KuzuMemory git post-commit hook\n")

    mock_config_service = Mock()
    mock_config_service.is_initialized = False
    mock_config_service.initialize = Mock()
    mock_config_service.get_project_root.return_value = tmp_path

    service = GitSyncService(config_service=mock_config_service)

    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service.initialize()

        result = service.uninstall_hooks()

        assert result is True
        assert not hook_file.exists()


# ============================================================================
# 3. Dependency Injection Tests (4 tests)
# ============================================================================


def test_requires_config_service():
    """Test that GitSyncService requires IConfigService dependency."""
    # Should be able to create with config service
    mock_config = Mock()
    mock_config.is_initialized = False
    mock_config.initialize = Mock()
    mock_config.get_project_root.return_value = Path("/fake/project")
    service = GitSyncService(config_service=mock_config)
    assert service._config_service is mock_config


def test_initializes_config_service(mock_config_service):
    """Test that service initializes config service if not initialized."""
    mock_config_service.is_initialized = False

    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service = GitSyncService(config_service=mock_config_service)
        service.initialize()

        # Should initialize config service
        mock_config_service.initialize.assert_called_once()


def test_uses_config_service_for_project_root(mock_config_service):
    """Test that service uses config service to get project root."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager"
    ) as mock_manager_class:
        service = GitSyncService(config_service=mock_config_service)
        service.initialize()

        # Should have called get_project_root
        mock_config_service.get_project_root.assert_called()
        # Should pass project root to GitSyncManager
        call_args = mock_manager_class.call_args
        assert call_args[1]["repo_path"] == Path("/fake/project")


def test_handles_config_service_errors(mock_config_service):
    """Test that service handles config service errors."""
    mock_config_service.initialize.side_effect = Exception("Config error")

    service = GitSyncService(config_service=mock_config_service)

    with pytest.raises(Exception, match="Config error"):
        service.initialize()

    # Service should not be marked as initialized
    assert not service.is_initialized


# ============================================================================
# 4. Error Handling Tests (4 tests)
# ============================================================================


def test_methods_before_initialization_raise(service):
    """Test that calling methods before initialization raises RuntimeError."""
    # Should raise for all protocol methods
    with pytest.raises(RuntimeError, match="not initialized"):
        service.initialize_sync()

    with pytest.raises(RuntimeError, match="not initialized"):
        service.sync()

    with pytest.raises(RuntimeError, match="not initialized"):
        service.is_available()

    with pytest.raises(RuntimeError, match="not initialized"):
        service.get_sync_status()

    with pytest.raises(RuntimeError, match="not initialized"):
        service.install_hooks()

    with pytest.raises(RuntimeError, match="not initialized"):
        service.uninstall_hooks()


def test_invalid_project_root_handling(mock_config_service):
    """Test handling of invalid project root."""
    # Simulate config service returning invalid path
    mock_config_service.get_project_root.return_value = Path("/nonexistent/path")

    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager"
    ) as mock_manager_class:
        service = GitSyncService(config_service=mock_config_service)
        service.initialize()

        # GitSyncManager should still be created (it will check git availability)
        assert mock_manager_class.called


def test_git_not_available_handling(service, mock_git_sync_manager):
    """Test handling when git is not available."""
    mock_git_sync_manager.is_available.return_value = False

    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        service.initialize()

        # initialize_sync should return False
        result = service.initialize_sync()
        assert result is False

        # is_available should return False
        assert service.is_available() is False


def test_sync_failure_handling(service, mock_git_sync_manager):
    """Test handling of sync failures."""
    # Simulate sync failure
    mock_git_sync_manager.sync.return_value = {
        "commits_synced": 0,
        "success": False,
        "error": "Sync failed",
    }

    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        service.initialize()

        # Should return 0 commits synced
        result = service.sync()
        assert result == 0


# ============================================================================
# 5. Integration Tests (3 tests)
# ============================================================================


def test_full_sync_workflow(service, mock_git_sync_manager):
    """Test full sync workflow from initialization to sync."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        # Initialize service
        service.initialize()
        assert service.is_initialized

        # Check availability
        assert service.is_available() is True

        # Initialize sync
        assert service.initialize_sync() is True

        # Perform sync
        commits = service.sync(since="2024-01-01", max_commits=100)
        assert commits == 5

        # Check status
        status = service.get_sync_status()
        assert status["available"] is True
        assert "hooks_installed" in status


def test_hook_installation_workflow(service, tmp_path):
    """Test complete hook installation workflow."""
    # Create fake git directory
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    mock_config_service = Mock()
    mock_config_service.is_initialized = False
    mock_config_service.initialize = Mock()
    mock_config_service.get_project_root.return_value = tmp_path

    service = GitSyncService(config_service=mock_config_service)

    # Create mock GitSyncManager
    mock_manager = Mock()
    mock_manager.get_sync_status.return_value = {
        "available": True,
        "enabled": True,
    }

    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_manager,
    ):
        # Initialize
        service.initialize()

        # Check hooks not installed
        status = service.get_sync_status()
        assert status["hooks_installed"] is False

        # Install hooks
        assert service.install_hooks() is True

        # Check hooks installed
        status = service.get_sync_status()
        assert status["hooks_installed"] is True

        # Uninstall hooks
        assert service.uninstall_hooks() is True

        # Check hooks removed
        status = service.get_sync_status()
        assert status["hooks_installed"] is False


def test_status_checking_workflow(service, mock_git_sync_manager, tmp_path):
    """Test status checking workflow with real paths."""
    # Create fake git directory
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    mock_config_service = Mock()
    mock_config_service.is_initialized = False
    mock_config_service.initialize = Mock()
    mock_config_service.get_project_root.return_value = tmp_path

    service = GitSyncService(config_service=mock_config_service)

    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        service.initialize()

        # Get initial status
        status = service.get_sync_status()
        assert status["available"] is True
        assert status["hooks_installed"] is False

        # Install hooks
        service.install_hooks()

        # Status should reflect installed hooks
        status = service.get_sync_status()
        assert status["hooks_installed"] is True


# ============================================================================
# 6. Property Tests (2 tests)
# ============================================================================


def test_git_sync_property_returns_manager(service, mock_git_sync_manager):
    """Test git_sync property returns GitSyncManager instance."""
    with patch(
        "kuzu_memory.services.git_sync_service.GitSyncManager",
        return_value=mock_git_sync_manager,
    ):
        service.initialize()

        manager = service.git_sync
        assert manager is mock_git_sync_manager


def test_git_sync_property_raises_if_not_initialized(service):
    """Test git_sync property raises if service not initialized."""
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = service.git_sync


# ============================================================================
# 7. Helper Method Tests (3 tests)
# ============================================================================


def test_find_git_directory_finds_in_current(service, tmp_path):
    """Test _find_git_directory finds .git in current directory."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service.initialize()
        found = service._find_git_directory(tmp_path)
        assert found == git_dir


def test_find_git_directory_searches_parents(service, tmp_path):
    """Test _find_git_directory searches parent directories."""
    # Create .git in parent
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Search from subdirectory
    subdir = tmp_path / "sub" / "dir"
    subdir.mkdir(parents=True)

    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service.initialize()
        found = service._find_git_directory(subdir)
        assert found == git_dir


def test_check_hooks_installed_detects_kuzu_hook(service, tmp_path):
    """Test _check_hooks_installed correctly identifies KuzuMemory hooks."""
    git_dir = tmp_path / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True)

    with patch("kuzu_memory.services.git_sync_service.GitSyncManager"):
        service.initialize()

        # No hook
        assert service._check_hooks_installed(tmp_path) is False

        # Non-KuzuMemory hook
        hook_file = hooks_dir / "post-commit"
        hook_file.write_text("#!/bin/sh\necho 'other hook'\n")
        assert service._check_hooks_installed(tmp_path) is False

        # KuzuMemory hook
        hook_file.write_text("#!/bin/sh\n# KuzuMemory git post-commit hook\n")
        assert service._check_hooks_installed(tmp_path) is True
