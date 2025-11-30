"""
Unit tests for Phase 5.2 write command migrations.

Tests: store, init, prune, git sync commands with ServiceManager.
Validates proper service lifecycle management and multi-service orchestration.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kuzu_memory.cli.git_commands import sync
from kuzu_memory.cli.init_commands import init
from kuzu_memory.cli.memory_commands import prune, store


@pytest.fixture
def runner():
    """Provide Click test runner with isolated filesystem."""
    return CliRunner()


@pytest.fixture
def mock_memory_service():
    """Create a mock MemoryService for testing."""
    mock = MagicMock()
    mock.remember.return_value = "test-memory-id-123"
    mock.get_memory_count.return_value = 1000
    mock.get_database_size.return_value = 10 * 1024 * 1024  # 10MB

    # Mock kuzu_memory property for prune command
    mock.kuzu_memory = MagicMock()
    return mock


@pytest.fixture
def mock_config_service():
    """Create a mock ConfigService for testing."""
    mock = MagicMock()
    mock.get_project_root.return_value = Path("/tmp/test-project")
    mock.get_db_path.return_value = Path("/tmp/test-project/kuzu-memories/memories.db")
    mock.is_initialized = True
    return mock


@pytest.fixture
def mock_setup_service():
    """Create a mock SetupService for testing."""
    mock = MagicMock()
    mock.initialize_project.return_value = {
        "success": True,
        "summary": "Project initialized successfully",
        "steps_completed": ["Created memories directory"],
        "warnings": [],
        "project_root": "/tmp/test-project",
        "memories_dir": "/tmp/test-project/kuzu-memories",
        "db_path": "/tmp/test-project/kuzu-memories/memories.db",
    }
    return mock


@pytest.fixture
def mock_git_sync_service():
    """Create a mock GitSyncService for testing."""
    mock = MagicMock()
    mock.is_available.return_value = True

    # Mock git_sync property that returns GitSyncManager
    mock_manager = MagicMock()
    mock_manager.sync.return_value = {
        "success": True,
        "mode": "auto",
        "commits_found": 10,
        "commits_synced": 10,
        "commits_skipped": 0,
    }
    mock.git_sync = mock_manager
    return mock


class TestStoreCommand:
    """Test store command migration to ServiceManager."""

    def test_store_with_service_manager(self, runner, mock_memory_service):
        """Test store command uses MemoryService correctly."""
        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(
                store,
                ["Test memory content", "--source", "test"],
                obj={},
            )

            assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
            assert "Stored memory" in result.output
            assert "test-memory-id-123" in result.output
            mock_memory_service.remember.assert_called_once()

    def test_store_with_metadata(self, runner, mock_memory_service):
        """Test store command with JSON metadata."""
        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(
                store,
                [
                    "Test content",
                    "--source",
                    "test",
                    "--metadata",
                    '{"key": "value"}',
                    "--session-id",
                    "test-session",
                ],
                obj={},
            )

            assert result.exit_code == 0
            assert "Stored memory" in result.output
            # Verify metadata was parsed and passed
            call_args = mock_memory_service.remember.call_args
            assert call_args is not None
            assert call_args[1]["session_id"] == "test-session"

    def test_store_with_invalid_metadata(self, runner, mock_memory_service):
        """Test store command with invalid JSON metadata."""
        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(
                store,
                ["Test content", "--metadata", "invalid-json"],
                obj={},
            )

            # Should still succeed but warn about invalid metadata
            assert result.exit_code == 0
            assert "Invalid JSON" in result.output or "Stored memory" in result.output


class TestInitCommand:
    """Test init command migration to multi-service orchestration."""

    def test_init_with_services(self, runner, mock_config_service, mock_setup_service):
        """Test init command uses ConfigService and SetupService."""
        with (
            patch("kuzu_memory.cli.init_commands.ConfigService") as MockConfig,
            patch("kuzu_memory.cli.init_commands.SetupService") as MockSetup,
            patch("kuzu_memory.cli.init_commands.find_project_root") as mock_find,
            patch("kuzu_memory.cli.init_commands.get_project_db_path") as mock_db_path,
            patch("kuzu_memory.cli.init_commands.get_project_memories_dir") as mock_mem_dir,
            patch("kuzu_memory.cli.init_commands.KuzuMemory"),
        ):
            # Setup mocks
            MockConfig.return_value = mock_config_service
            MockSetup.return_value = mock_setup_service
            mock_find.return_value = Path("/tmp/test-project")

            mock_db = MagicMock(spec=Path)
            mock_db.exists.return_value = False
            mock_db_path.return_value = mock_db

            mock_mem_dir.return_value = Path("/tmp/test-project/kuzu-memories")

            result = runner.invoke(init, [], obj={})

            assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
            assert (
                "Initialization Complete" in result.output or "initialized" in result.output.lower()
            )

            # Verify services were created and initialized
            MockConfig.assert_called_once()
            mock_config_service.initialize.assert_called_once()
            MockSetup.assert_called_once_with(mock_config_service)
            mock_setup_service.initialize.assert_called_once()

    def test_init_already_initialized(self, runner):
        """Test init command when project already initialized."""
        with (
            patch("kuzu_memory.cli.init_commands.find_project_root") as mock_find,
            patch("kuzu_memory.cli.init_commands.get_project_db_path") as mock_db_path,
            patch("kuzu_memory.cli.init_commands.get_project_memories_dir") as mock_mem_dir,
        ):
            mock_find.return_value = Path("/tmp/test-project")

            # Mock DB already exists
            mock_db = MagicMock(spec=Path)
            mock_db.exists.return_value = True
            mock_db_path.return_value = mock_db

            mock_mem_dir.return_value = Path("/tmp/test-project/kuzu-memories")

            result = runner.invoke(init, [], obj={})

            assert result.exit_code == 1
            assert "already initialized" in result.output


class TestPruneCommand:
    """Test prune command migration to ServiceManager."""

    def test_prune_dry_run(self, runner, mock_memory_service):
        """Test prune command in dry-run mode."""
        # Mock MemoryPruner and its analyze method
        with (
            patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx,
            patch("kuzu_memory.cli.memory_commands.MemoryPruner") as MockPruner,
        ):
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            # Mock pruner stats
            mock_stats = MagicMock()
            mock_stats.total_memories = 1000
            mock_stats.memories_to_prune = 100
            mock_stats.memories_to_keep = 900
            mock_stats.protected_count = 50
            mock_stats.by_age = {}
            mock_stats.by_size = {}
            mock_stats.by_source = {}
            mock_stats.estimated_content_savings_bytes = 1024 * 1024
            mock_stats.estimated_db_savings_bytes = 512 * 1024

            mock_pruner_instance = MockPruner.return_value
            mock_pruner_instance.analyze.return_value = mock_stats

            result = runner.invoke(prune, ["--strategy", "safe"], obj={})

            assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
            assert "DRY-RUN" in result.output or "dry run" in result.output.lower()
            assert "100" in result.output  # memories to prune

            # Verify kuzu_memory property was accessed
            MockPruner.assert_called_once_with(mock_memory_service.kuzu_memory)

    def test_prune_uses_kuzu_memory_property(self, runner, mock_memory_service):
        """Test prune command accesses kuzu_memory property correctly."""
        with (
            patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx,
            patch("kuzu_memory.cli.memory_commands.MemoryPruner") as MockPruner,
        ):
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            # Mock stats
            mock_stats = MagicMock()
            mock_stats.total_memories = 100
            mock_stats.memories_to_prune = 10
            mock_stats.memories_to_keep = 90
            mock_stats.protected_count = 5
            mock_stats.by_age = {}
            mock_stats.by_size = {}
            mock_stats.by_source = {}
            mock_stats.estimated_content_savings_bytes = 1024
            mock_stats.estimated_db_savings_bytes = 512

            mock_pruner = MockPruner.return_value
            mock_pruner.analyze.return_value = mock_stats

            runner.invoke(prune, [], obj={})

            # Verify MemoryPruner was created with kuzu_memory property
            MockPruner.assert_called_once_with(mock_memory_service.kuzu_memory)


class TestGitSyncCommand:
    """Test git sync command migration to GitSyncService."""

    def test_sync_with_git_sync_service(self, runner, mock_git_sync_service, mock_config_service):
        """Test git sync command uses GitSyncService correctly."""
        with (
            patch("kuzu_memory.services.ConfigService") as MockConfig,
            patch(
                "kuzu_memory.cli.service_manager.ServiceManager.git_sync_service"
            ) as mock_git_ctx,
            patch("kuzu_memory.cli.git_commands.get_project_db_path") as mock_db,
            patch("kuzu_memory.cli.git_commands.get_config_loader") as mock_loader,
            patch("kuzu_memory.cli.git_commands.KuzuMemory") as MockMemory,
        ):
            MockConfig.return_value = mock_config_service
            mock_git_ctx.return_value.__enter__.return_value = mock_git_sync_service
            mock_db.return_value = Path("/tmp/test.db")

            # Mock config loader
            mock_config = MagicMock()
            mock_config.git_sync = MagicMock()
            mock_loader.return_value.load_config.return_value = mock_config

            # Mock KuzuMemory context manager
            mock_memory_instance = MagicMock()
            mock_memory_instance.memory_store = MagicMock()
            MockMemory.return_value.__enter__.return_value = mock_memory_instance

            result = runner.invoke(sync, [], obj={"project_root": Path.cwd()})

            assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
            assert "Sync Complete" in result.output or "commits" in result.output.lower()

            # Verify GitSyncService methods were called
            mock_git_sync_service.is_available.assert_called_once()

    def test_sync_not_available(self, runner, mock_config_service):
        """Test git sync command when git sync not available."""
        mock_git_sync = MagicMock()
        mock_git_sync.is_available.return_value = False

        with (
            patch("kuzu_memory.services.ConfigService") as MockConfig,
            patch(
                "kuzu_memory.cli.service_manager.ServiceManager.git_sync_service"
            ) as mock_git_ctx,
            patch("kuzu_memory.cli.git_commands.get_project_db_path"),
            patch("kuzu_memory.cli.git_commands.get_config_loader"),
        ):
            MockConfig.return_value = mock_config_service
            mock_git_ctx.return_value.__enter__.return_value = mock_git_sync

            result = runner.invoke(sync, [], obj={"project_root": Path.cwd()})

            assert result.exit_code == 0  # Exits cleanly but with warning
            assert "not available" in result.output.lower()
