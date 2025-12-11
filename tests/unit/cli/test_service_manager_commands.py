"""
Unit tests for CLI commands using ServiceManager.

Tests Phase 5.1-5.2 migrations: recall, enhance, recent, status, store, init, prune, git sync commands.
Validates that commands correctly use ServiceManager for dependency injection.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kuzu_memory.cli.commands import cli
from kuzu_memory.cli.memory_commands import enhance, recall, recent
from kuzu_memory.cli.status_commands import status
from kuzu_memory.core.models import Memory, MemoryContext, MemoryType


@pytest.fixture
def runner():
    """Provide Click test runner with isolated filesystem."""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def mock_memory_service():
    """Create a mock MemoryService for testing."""
    mock = MagicMock()
    # Configure default return values
    mock.get_memory_count.return_value = 100
    mock.get_database_size.return_value = 1024 * 1024  # 1MB
    mock.get_recent_memories.return_value = []
    mock.attach_memories.return_value = MemoryContext(
        original_prompt="test",
        enhanced_prompt="test enhanced",
        memories=[],
        confidence=0.9,
    )
    return mock


class TestRecallCommand:
    """Test recall command migration to ServiceManager."""

    def test_recall_with_service_manager(self, runner, mock_memory_service):
        """Test recall command uses ServiceManager correctly."""
        # Setup mock memories
        test_memory = Memory(
            id="test-id-123",
            content="Test memory content",
            memory_type=MemoryType.SEMANTIC,
            source_type="test",
        )
        mock_context = MemoryContext(
            original_prompt="test query",
            enhanced_prompt="test query enhanced",
            memories=[test_memory],
            confidence=0.95,
        )
        mock_memory_service.attach_memories.return_value = mock_context

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service
            with patch("kuzu_memory.cli.memory_commands.get_project_db_path") as mock_db:
                mock_db.return_value = Path("/tmp/test.db")

                result = runner.invoke(recall, ["test query", "--format", "simple"], obj={})

                assert result.exit_code == 0, (
                    f"Output: {result.output}\nException: {result.exception}"
                )
                mock_memory_service.attach_memories.assert_called_once()
                assert "test query" in mock_memory_service.attach_memories.call_args[0][0]

    def test_recall_no_memories_found(self, runner, mock_memory_service):
        """Test recall command when no memories found."""
        mock_context = MemoryContext(
            original_prompt="test", enhanced_prompt="test", memories=[], confidence=0.0
        )
        mock_memory_service.attach_memories.return_value = mock_context

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(recall, ["test query"])

            assert result.exit_code == 0
            assert "No memories found" in result.output

    def test_recall_with_filters(self, runner, mock_memory_service):
        """Test recall command with session and agent filters."""
        mock_context = MemoryContext(
            original_prompt="test", enhanced_prompt="test", memories=[], confidence=0.0
        )
        mock_memory_service.attach_memories.return_value = mock_context

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(
                recall,
                [
                    "test query",
                    "--session-id",
                    "test-session",
                    "--agent-id",
                    "test-agent",
                ],
            )

            assert result.exit_code == 0
            # Verify filters were passed
            call_kwargs = mock_memory_service.attach_memories.call_args[1]
            assert call_kwargs.get("session_id") == "test-session"
            assert call_kwargs.get("agent_id") == "test-agent"


class TestEnhanceCommand:
    """Test enhance command migration to ServiceManager."""

    def test_enhance_with_service_manager(self, runner, mock_memory_service):
        """Test enhance command uses ServiceManager correctly."""
        test_memory = Memory(id="test-id", content="Test context", memory_type=MemoryType.SEMANTIC)
        mock_context = MemoryContext(
            original_prompt="test prompt",
            enhanced_prompt="test prompt with context",
            memories=[test_memory],
            confidence=0.9,
        )
        mock_memory_service.attach_memories.return_value = mock_context

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(enhance, ["test prompt", "--format", "plain"])

            assert result.exit_code == 0
            mock_memory_service.attach_memories.assert_called_once()

    def test_enhance_json_output(self, runner, mock_memory_service):
        """Test enhance command with JSON output format."""
        test_memory = Memory(id="test-id", content="Test context", memory_type=MemoryType.SEMANTIC)
        mock_context = MemoryContext(
            original_prompt="test",
            enhanced_prompt="test enhanced",
            memories=[test_memory],
            confidence=0.9,
        )
        mock_memory_service.attach_memories.return_value = mock_context

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(enhance, ["test prompt", "--format", "json"])

            assert result.exit_code == 0
            assert "original_prompt" in result.output
            assert "enhanced_prompt" in result.output


class TestRecentCommand:
    """Test recent command migration to ServiceManager."""

    def test_recent_with_service_manager(self, runner, mock_memory_service):
        """Test recent command uses ServiceManager correctly."""
        test_memories = [
            Memory(id=f"test-{i}", content=f"Memory {i}", memory_type=MemoryType.SEMANTIC)
            for i in range(5)
        ]
        mock_memory_service.get_recent_memories.return_value = test_memories

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(recent, ["--limit", "5", "--format", "list"])

            assert result.exit_code == 0
            mock_memory_service.get_recent_memories.assert_called_once_with(limit=5)

    def test_recent_no_memories(self, runner, mock_memory_service):
        """Test recent command when no memories exist."""
        mock_memory_service.get_recent_memories.return_value = []

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(recent, [])

            assert result.exit_code == 0
            assert "No memories found" in result.output

    def test_recent_json_output(self, runner, mock_memory_service):
        """Test recent command with JSON output."""
        test_memories = [Memory(id="test-1", content="Memory 1", memory_type=MemoryType.SEMANTIC)]
        mock_memory_service.get_recent_memories.return_value = test_memories

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(recent, ["--format", "json"])

            assert result.exit_code == 0
            assert "total_memories" in result.output
            assert "memories" in result.output


class TestStatusCommand:
    """Test status command migration to ServiceManager."""

    def test_status_with_service_manager(self, runner, mock_memory_service):
        """Test status command uses ServiceManager correctly."""
        mock_memory_service.get_memory_count.return_value = 50
        mock_memory_service.get_recent_memories.return_value = [
            Memory(id="test", content="Test", memory_type=MemoryType.SEMANTIC)
        ]

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service
            with patch("kuzu_memory.cli.status_commands.get_project_db_path") as mock_db_path:
                # Mock database path exists
                mock_path = MagicMock(spec=Path)
                mock_path.exists.return_value = True
                mock_db_path.return_value = mock_path

                result = runner.invoke(status, [])

                assert result.exit_code == 0
                mock_memory_service.get_memory_count.assert_called_once()

    def test_status_project_not_initialized(self, runner):
        """Test status command when project not initialized."""
        with patch("kuzu_memory.cli.status_commands.get_project_db_path") as mock_db_path:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_db_path.return_value = mock_path

            result = runner.invoke(status, [])

            assert result.exit_code == 0
            assert "not initialized" in result.output.lower()

    def test_status_json_output(self, runner, mock_memory_service):
        """Test status command with JSON output."""
        mock_memory_service.get_memory_count.return_value = 50
        mock_memory_service.get_recent_memories.return_value = []

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service
            with patch("kuzu_memory.cli.status_commands.get_project_db_path") as mock_db_path:
                mock_path = MagicMock(spec=Path)
                mock_path.exists.return_value = True
                mock_db_path.return_value = mock_path

                result = runner.invoke(status, ["--format", "json"])

                assert result.exit_code == 0
                assert "total_memories" in result.output
                assert "initialized" in result.output


class TestServiceManagerCleanup:
    """Test that ServiceManager properly manages resource lifecycle."""

    def test_service_cleanup_on_success(self, runner, mock_memory_service):
        """Test service cleanup is called on successful execution."""
        mock_memory_service.get_recent_memories.return_value = []

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_enter = MagicMock(return_value=mock_memory_service)
            mock_exit = MagicMock()
            mock_ctx.return_value.__enter__ = mock_enter
            mock_ctx.return_value.__exit__ = mock_exit

            result = runner.invoke(recent, [])

            assert result.exit_code == 0
            # Verify context manager protocol
            mock_enter.assert_called_once()
            mock_exit.assert_called_once()

    def test_service_cleanup_on_error(self, runner, mock_memory_service):
        """Test service cleanup is called even on errors."""
        mock_memory_service.get_recent_memories.side_effect = Exception("Test error")

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_enter = MagicMock(return_value=mock_memory_service)
            mock_exit = MagicMock()
            mock_ctx.return_value.__enter__ = mock_enter
            mock_ctx.return_value.__exit__ = mock_exit

            result = runner.invoke(recent, [])

            # Command should fail but cleanup should still happen
            assert result.exit_code != 0
            mock_exit.assert_called_once()


class TestCustomDbPath:
    """Test --db-path option for all migrated commands."""

    def test_recall_custom_db_path(self, runner, mock_memory_service):
        """Test recall with custom database path."""
        mock_context = MemoryContext(
            original_prompt="test", enhanced_prompt="test", memories=[], confidence=0.0
        )
        mock_memory_service.attach_memories.return_value = mock_context

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(recall, ["test", "--db-path", "/custom/path/db"])

            assert result.exit_code == 0
            # Verify custom path was used
            call_args = mock_ctx.call_args
            assert call_args[1]["db_path"] == Path("/custom/path/db")

    def test_enhance_custom_db_path(self, runner, mock_memory_service):
        """Test enhance with custom database path."""
        mock_context = MemoryContext(
            original_prompt="test", enhanced_prompt="test", memories=[], confidence=0.0
        )
        mock_memory_service.attach_memories.return_value = mock_context

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(enhance, ["test", "--db-path", "/custom/path/db"])

            assert result.exit_code == 0
            call_args = mock_ctx.call_args
            assert call_args[1]["db_path"] == Path("/custom/path/db")

    def test_recent_custom_db_path(self, runner, mock_memory_service):
        """Test recent with custom database path."""
        mock_memory_service.get_recent_memories.return_value = []

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service

            result = runner.invoke(recent, ["--db-path", "/custom/path/db"])

            assert result.exit_code == 0
            call_args = mock_ctx.call_args
            assert call_args[1]["db_path"] == Path("/custom/path/db")

    def test_status_custom_db_path(self, runner, mock_memory_service):
        """Test status with custom database path."""
        mock_memory_service.get_memory_count.return_value = 0
        mock_memory_service.get_recent_memories.return_value = []

        with patch("kuzu_memory.cli.service_manager.ServiceManager.memory_service") as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = mock_memory_service
            with patch("kuzu_memory.cli.status_commands.Path") as mock_path_class:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path_class.return_value = mock_path

                result = runner.invoke(status, ["--db-path", "/custom/path/db"])

                assert result.exit_code == 0
