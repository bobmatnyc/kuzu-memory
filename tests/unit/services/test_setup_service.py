"""Tests for SetupService."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from kuzu_memory.services.setup_service import SetupService

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
def service(mock_config_service):
    """Create SetupService instance."""
    return SetupService(config_service=mock_config_service)


# ============================================================================
# 1. Lifecycle Tests (5 tests)
# ============================================================================


def test_initialization_sets_project_root(mock_config_service):
    """Test that initialization sets project root from config service."""
    service = SetupService(config_service=mock_config_service)
    service.initialize()

    # Verify config service was initialized
    mock_config_service.initialize.assert_called_once()

    # Verify project root was set
    assert service._project_root == Path("/fake/project")

    # Verify service is marked as initialized
    assert service.is_initialized


def test_cleanup_nullifies_project_root(service, mock_config_service):
    """Test that cleanup nullifies project root."""
    service.initialize()
    assert service._project_root is not None

    service.cleanup()
    assert service._project_root is None
    assert not service.is_initialized


def test_context_manager_lifecycle(mock_config_service):
    """Test context manager handles initialization and cleanup."""
    service = SetupService(config_service=mock_config_service)

    assert not service.is_initialized

    with service as svc:
        assert svc.is_initialized
        assert svc is service
        assert svc._project_root == Path("/fake/project")

    # After context exit, should be cleaned up
    assert not service.is_initialized
    assert service._project_root is None


def test_double_initialization_safety(service, mock_config_service):
    """Test that double initialization is safe."""
    service.initialize()
    first_root = service._project_root

    service.initialize()
    second_root = service._project_root

    # Should have same root (idempotent)
    assert first_root == second_root
    assert service.is_initialized


def test_double_cleanup_safety(service, mock_config_service):
    """Test that double cleanup is safe."""
    service.initialize()
    service.cleanup()

    # Second cleanup should not raise
    service.cleanup()

    assert not service.is_initialized
    assert service._project_root is None


# ============================================================================
# 2. Path Utilities Tests (4 tests)
# ============================================================================


def test_find_project_root_delegation():
    """Test that find_project_root delegates to project_setup utility."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.find_project_root.return_value = Path("/found/project")

        # Note: This method doesn't require initialization
        service = SetupService(config_service=Mock())
        result = service.find_project_root(Path("/start/path"))

        mock_ps.find_project_root.assert_called_once_with(Path("/start/path"))
        assert result == Path("/found/project")


def test_get_project_db_path_delegation(service, mock_config_service):
    """Test that get_project_db_path delegates to project_setup utility."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.get_project_db_path.return_value = Path(
            "/fake/project/kuzu-memories/memories.db"
        )

        service.initialize()
        result = service.get_project_db_path()

        # Should use initialized project root
        mock_ps.get_project_db_path.assert_called_once_with(Path("/fake/project"))
        assert result == Path("/fake/project/kuzu-memories/memories.db")


def test_path_utilities_work_without_init():
    """Test that static path utilities work before initialization."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.find_project_root.return_value = Path("/found/project")

        service = SetupService(config_service=Mock())

        # find_project_root should work without initialization
        result = service.find_project_root()
        assert result == Path("/found/project")


def test_get_project_db_path_with_custom_root(service, mock_config_service):
    """Test get_project_db_path with custom project root."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.get_project_db_path.return_value = Path(
            "/custom/project/kuzu-memories/memories.db"
        )

        service.initialize()
        result = service.get_project_db_path(Path("/custom/project"))

        # Should use provided root, not initialized root
        mock_ps.get_project_db_path.assert_called_once_with(Path("/custom/project"))
        assert result == Path("/custom/project/kuzu-memories/memories.db")


# ============================================================================
# 3. Project Initialization Tests (5 tests)
# ============================================================================


def test_initialize_project_creates_structure(service, mock_config_service):
    """Test that initialize_project creates project structure."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.return_value = {
            "created": True,
            "project_root": "/fake/project",
            "memories_dir": "/fake/project/kuzu-memories",
            "db_path": "/fake/project/kuzu-memories/memories.db",
            "files_created": [
                "/fake/project/kuzu-memories",
                "/fake/project/kuzu-memories/README.md",
            ],
        }

        service.initialize()
        result = service.initialize_project()

        # Verify structure creation was called
        mock_ps.create_project_memories_structure.assert_called_once_with(
            project_root=Path("/fake/project"), force=False
        )

        # Verify result
        assert result["success"] is True
        assert "initialized successfully" in result["summary"]
        assert len(result["steps_completed"]) > 0
        assert "Created project memories structure" in result["steps_completed"]


def test_initialize_project_with_force(service, mock_config_service):
    """Test initialize_project with force flag."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.return_value = {
            "created": True,
            "project_root": "/fake/project",
            "memories_dir": "/fake/project/kuzu-memories",
            "db_path": "/fake/project/kuzu-memories/memories.db",
            "files_created": [],
        }

        service.initialize()
        result = service.initialize_project(force=True)

        # Verify force flag was passed
        mock_ps.create_project_memories_structure.assert_called_once_with(
            project_root=Path("/fake/project"), force=True
        )

        assert result["success"] is True


def test_initialize_project_idempotency(service, mock_config_service):
    """Test that initialize_project is idempotent."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.return_value = {
            "existed": True,
            "created": False,
            "project_root": "/fake/project",
            "memories_dir": "/fake/project/kuzu-memories",
            "db_path": "/fake/project/kuzu-memories/memories.db",
        }

        service.initialize()
        result = service.initialize_project()

        # Should succeed even if already exists
        assert result["success"] is True
        assert len(result["warnings"]) > 0
        assert any("already initialized" in w for w in result["warnings"])


def test_initialize_project_error_handling(service, mock_config_service):
    """Test initialize_project handles errors gracefully."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.side_effect = Exception(
            "Permission denied"
        )

        service.initialize()
        result = service.initialize_project()

        # Should return failure result, not raise
        assert result["success"] is False
        assert "Permission denied" in result["summary"]
        assert len(result["warnings"]) > 0


def test_initialize_project_reserved_params(service, mock_config_service):
    """Test initialize_project acknowledges reserved parameters."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.return_value = {
            "created": True,
            "project_root": "/fake/project",
            "memories_dir": "/fake/project/kuzu-memories",
            "db_path": "/fake/project/kuzu-memories/memories.db",
            "files_created": [],
        }

        service.initialize()
        result = service.initialize_project(git_sync=True, claude_desktop=True)

        # Should have warnings about reserved parameters
        assert any("git_sync" in w for w in result["warnings"])
        assert any("claude_desktop" in w for w in result["warnings"])


# ============================================================================
# 4. Integration Setup Tests (3 tests)
# ============================================================================


def test_setup_integrations_placeholder(service, mock_config_service):
    """Test that setup_integrations is a placeholder."""
    service.initialize()
    result = service.setup_integrations(["claude-desktop", "auggie"])

    # Should return False for all integrations (placeholder)
    assert result["claude-desktop"] is False
    assert result["auggie"] is False


def test_setup_integrations_empty_list(service, mock_config_service):
    """Test setup_integrations with empty list."""
    service.initialize()
    result = service.setup_integrations([])

    # Should return empty dict
    assert result == {}


def test_setup_integrations_requires_initialization(service):
    """Test that setup_integrations requires initialization."""
    with pytest.raises(RuntimeError, match="not initialized"):
        service.setup_integrations(["claude-desktop"])


# ============================================================================
# 5. Structure Management Tests (5 tests)
# ============================================================================


def test_ensure_project_structure_creates_dirs(service, mock_config_service):
    """Test that ensure_project_structure creates directories."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.return_value = {
            "created": True,
            "project_root": "/custom/project",
            "memories_dir": "/custom/project/kuzu-memories",
        }

        result = service.ensure_project_structure(Path("/custom/project"))

        mock_ps.create_project_memories_structure.assert_called_once_with(
            project_root=Path("/custom/project"), force=False
        )
        assert result is True


def test_ensure_project_structure_idempotent(service):
    """Test that ensure_project_structure is idempotent."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.return_value = {
            "existed": True,
            "created": False,
        }

        result = service.ensure_project_structure(Path("/custom/project"))

        # Should succeed even if already exists
        assert result is True


def test_initialize_hooks_placeholder(service, mock_config_service):
    """Test that initialize_hooks is a placeholder."""
    service.initialize()
    result = service.initialize_hooks(Path("/fake/project"))

    # Should return False (placeholder)
    assert result is False


def test_validate_project_structure_success(service):
    """Test validate_project_structure when structure is valid."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        # Setup mocks
        mock_memories_dir = Mock()
        mock_memories_dir.exists.return_value = True
        mock_memories_dir.iterdir.return_value = []

        mock_db_path = Mock()
        mock_db_path.exists.return_value = True

        mock_ps.get_project_memories_dir.return_value = mock_memories_dir
        mock_ps.get_project_db_path.return_value = mock_db_path

        result = service.validate_project_structure(Path("/fake/project"))

        assert result is True


def test_validate_project_structure_failure(service):
    """Test validate_project_structure when structure is invalid."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        # Setup mocks - directory doesn't exist
        mock_memories_dir = Mock()
        mock_memories_dir.exists.return_value = False

        mock_ps.get_project_memories_dir.return_value = mock_memories_dir

        result = service.validate_project_structure(Path("/fake/project"))

        assert result is False


# ============================================================================
# 6. Dependency Injection Tests (3 tests)
# ============================================================================


def test_requires_config_service():
    """Test that SetupService requires IConfigService."""
    # Should accept any config service
    mock_config = Mock()
    service = SetupService(config_service=mock_config)

    assert service._config_service is mock_config


def test_initializes_config_service(mock_config_service):
    """Test that SetupService initializes config service."""
    mock_config_service.is_initialized = False

    service = SetupService(config_service=mock_config_service)
    service.initialize()

    # Should initialize config service
    mock_config_service.initialize.assert_called_once()


def test_uses_config_service_for_project_root(mock_config_service):
    """Test that SetupService uses config service for project root."""
    mock_config_service.get_project_root.return_value = Path("/from/config")

    service = SetupService(config_service=mock_config_service)
    service.initialize()

    # Should use config service's project root
    assert service._project_root == Path("/from/config")


# ============================================================================
# 7. Error Handling Tests (4 tests)
# ============================================================================


def test_methods_before_initialization_raise(service):
    """Test that methods raise RuntimeError before initialization."""
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = service.project_root

    with pytest.raises(RuntimeError, match="not initialized"):
        service.initialize_project()

    with pytest.raises(RuntimeError, match="not initialized"):
        service.verify_setup()


def test_verify_setup_handles_missing_structure(service, mock_config_service):
    """Test verify_setup handles missing project structure."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_memories_dir = Mock()
        mock_memories_dir.exists.return_value = False

        mock_db_path = Mock()
        mock_db_path.exists.return_value = False

        mock_ps.get_project_memories_dir.return_value = mock_memories_dir
        mock_ps.get_project_db_path.return_value = mock_db_path
        mock_ps.is_git_repository.return_value = False

        service.initialize()
        result = service.verify_setup()

        # Should detect issues
        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert len(result["suggestions"]) > 0


def test_verify_setup_handles_exceptions(service, mock_config_service):
    """Test verify_setup handles exceptions gracefully."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.get_project_memories_dir.side_effect = Exception("Permission denied")

        service.initialize()
        result = service.verify_setup()

        # Should return invalid result, not raise
        assert result["valid"] is False
        assert any("Permission denied" in i for i in result["issues"])


def test_ensure_structure_handles_exceptions(service):
    """Test ensure_project_structure handles exceptions gracefully."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_ps.create_project_memories_structure.side_effect = Exception("Disk full")

        result = service.ensure_project_structure(Path("/fake/project"))

        # Should return False, not raise
        assert result is False


# ============================================================================
# 8. Verify Setup Tests (Additional Coverage)
# ============================================================================


def test_verify_setup_all_valid(service, mock_config_service):
    """Test verify_setup when everything is valid."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_memories_dir = Mock()
        mock_memories_dir.exists.return_value = True

        mock_db_path = Mock()
        mock_db_path.exists.return_value = True

        mock_ps.get_project_memories_dir.return_value = mock_memories_dir
        mock_ps.get_project_db_path.return_value = mock_db_path
        mock_ps.is_git_repository.return_value = True

        service.initialize()
        result = service.verify_setup()

        # Should be valid with no issues
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["memories_dir_exists"] is True
        assert result["db_exists"] is True


def test_verify_setup_not_git_repo(service, mock_config_service):
    """Test verify_setup detects non-git repository."""
    with patch("kuzu_memory.services.setup_service.project_setup") as mock_ps:
        mock_memories_dir = Mock()
        mock_memories_dir.exists.return_value = True

        mock_db_path = Mock()
        mock_db_path.exists.return_value = True

        mock_ps.get_project_memories_dir.return_value = mock_memories_dir
        mock_ps.get_project_db_path.return_value = mock_db_path
        mock_ps.is_git_repository.return_value = False

        service.initialize()
        result = service.verify_setup()

        # Should have warning about git
        assert result["valid"] is False
        assert any("Not a git repository" in i for i in result["issues"])
        assert any("git init" in s for s in result["suggestions"])


# ============================================================================
# 9. Property Access Tests
# ============================================================================


def test_project_root_property_requires_initialization(service):
    """Test that project_root property requires initialization."""
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = service.project_root


def test_project_root_property_returns_path(service, mock_config_service):
    """Test that project_root property returns Path."""
    service.initialize()
    root = service.project_root

    assert isinstance(root, Path)
    assert root == Path("/fake/project")
