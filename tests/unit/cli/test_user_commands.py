"""
Unit tests for the `kuzu-memory user` CLI subcommand group.

Tests basic invocation of each subcommand using Click's CliRunner,
with all service/DB operations mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from kuzu_memory.cli.user_commands import user

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    """Click CliRunner for isolated invocations."""
    return CliRunner()


def _mock_ctx_obj(mode: str = "user") -> dict:
    """Build a mock ctx.obj dict like commands.py creates."""
    from kuzu_memory.core.config import KuzuMemoryConfig

    config = KuzuMemoryConfig()
    config.user.mode = mode
    config.user.user_db_path = "/tmp/test-user-cli.db"
    return {"config": config, "debug": False, "project_root": Path("/tmp/fake-project")}


def _make_user_svc_mock(total_memories: int = 3) -> MagicMock:
    """Create a mock UserMemoryService usable as a context manager."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    mock.get_stats = Mock(
        return_value={
            "db_path": "/tmp/test-user-cli.db",
            "total_memories": total_memories,
            "by_knowledge_type": {"pattern": 2, "rule": 1},
            "by_project": {"fake-project": total_memories},
        }
    )
    mock.promote_batch = Mock(return_value=total_memories)
    return mock


# ---------------------------------------------------------------------------
# user setup
# ---------------------------------------------------------------------------


class TestUserSetupCommand:
    def test_setup_exits_zero_on_success(self, runner: CliRunner) -> None:
        """user setup exits 0 when user DB is successfully initialised."""
        ctx_obj = _mock_ctx_obj()
        mock_svc = _make_user_svc_mock()

        with patch(
            "kuzu_memory.services.user_memory_service.UserMemoryService", return_value=mock_svc
        ), patch("kuzu_memory.core.config.KuzuMemoryConfig.save_to_file"), patch(
            "kuzu_memory.cli.user_commands._install_user_hooks", return_value="ok"
        ), patch("kuzu_memory.cli.user_commands._write_mpm_skill", return_value="ok"), patch.object(
            Path, "mkdir", return_value=None
        ), patch(
            "kuzu_memory.core.memory.KuzuMemory",
            return_value=mock_svc,
        ):
            result = runner.invoke(user, ["setup"], obj=ctx_obj)

        assert result.exit_code == 0, result.output

    def test_setup_shows_db_path(self, runner: CliRunner) -> None:
        """user setup output mentions the DB path."""
        ctx_obj = _mock_ctx_obj()
        mock_svc = _make_user_svc_mock()

        with patch(
            "kuzu_memory.services.user_memory_service.UserMemoryService", return_value=mock_svc
        ), patch("kuzu_memory.core.config.KuzuMemoryConfig.save_to_file"), patch(
            "kuzu_memory.cli.user_commands._install_user_hooks", return_value="ok"
        ), patch("kuzu_memory.cli.user_commands._write_mpm_skill", return_value="ok"), patch.object(
            Path, "mkdir", return_value=None
        ), patch(
            "kuzu_memory.core.memory.KuzuMemory",
            return_value=mock_svc,
        ):
            result = runner.invoke(user, ["setup"], obj=ctx_obj)

        assert result.exit_code == 0
        # Should mention some path or DB-related info
        assert "user" in result.output.lower() or "db" in result.output.lower()


# ---------------------------------------------------------------------------
# user status
# ---------------------------------------------------------------------------


class TestUserStatusCommand:
    def test_status_exits_zero_with_existing_db(self, runner: CliRunner) -> None:
        """user status exits 0 when user DB exists."""
        ctx_obj = _mock_ctx_obj()
        mock_svc = _make_user_svc_mock(total_memories=5)

        with patch("kuzu_memory.core.memory.KuzuMemory", return_value=mock_svc), patch.object(
            Path, "exists", return_value=True
        ), patch.object(Path, "mkdir", return_value=None):
            result = runner.invoke(user, ["status"], obj=ctx_obj)

        assert result.exit_code == 0, result.output

    def test_status_shows_memory_count(self, runner: CliRunner) -> None:
        """user status output includes total memory count."""
        ctx_obj = _mock_ctx_obj()
        mock_svc = _make_user_svc_mock(total_memories=7)

        # Patch UserMemoryService at its definition site so the with-block uses our mock
        with patch(
            "kuzu_memory.services.user_memory_service.UserMemoryService", return_value=mock_svc
        ), patch.object(Path, "exists", return_value=True), patch.object(
            Path, "mkdir", return_value=None
        ), patch("kuzu_memory.core.memory.KuzuMemory", return_value=mock_svc):
            result = runner.invoke(user, ["status"], obj=ctx_obj)

        assert result.exit_code == 0
        assert "7" in result.output

    def test_status_warns_when_db_not_found(self, runner: CliRunner) -> None:
        """user status warns and exits cleanly when user DB doesn't exist."""
        ctx_obj = _mock_ctx_obj()

        with patch.object(Path, "exists", return_value=False):
            result = runner.invoke(user, ["status"], obj=ctx_obj)

        assert result.exit_code == 0
        assert "setup" in result.output.lower() or "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# user promote
# ---------------------------------------------------------------------------


class TestUserPromoteCommand:
    def test_promote_exits_zero_with_no_candidates(self, runner: CliRunner) -> None:
        """user promote exits 0 when no memories meet criteria."""
        ctx_obj = _mock_ctx_obj()
        mock_mem_svc = MagicMock()
        mock_mem_svc.__enter__ = Mock(return_value=mock_mem_svc)
        mock_mem_svc.__exit__ = Mock(return_value=None)
        mock_mem_svc.kuzu_memory = MagicMock()
        mock_mem_svc.kuzu_memory.db_adapter = MagicMock()
        mock_mem_svc.kuzu_memory.db_adapter.execute_query = Mock(return_value=[])

        # MemoryService and get_project_db_path are lazy imports inside promote()
        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory", return_value=mock_mem_svc
        ), patch(
            "kuzu_memory.utils.project_setup.get_project_db_path",
            return_value=Path("/tmp/fake-project/.kuzu-memory/memories.db"),
        ), patch.object(Path, "exists", return_value=True):
            result = runner.invoke(user, ["promote"], obj=ctx_obj)

        assert result.exit_code == 0, result.output

    def test_promote_dry_run_does_not_write(self, runner: CliRunner) -> None:
        """user promote --dry-run shows candidates without writing."""
        from kuzu_memory.core.models import KnowledgeType, Memory, MemoryType

        ctx_obj = _mock_ctx_obj()
        mem = Memory(
            content="Use RLock for writes",
            memory_type=MemoryType.SEMANTIC,
            knowledge_type=KnowledgeType.RULE,
            importance=0.95,
        )
        mock_mem_svc = MagicMock()
        mock_mem_svc.__enter__ = Mock(return_value=mock_mem_svc)
        mock_mem_svc.__exit__ = Mock(return_value=None)
        mock_mem_svc.kuzu_memory = MagicMock()
        mock_mem_svc.kuzu_memory.db_adapter = MagicMock()
        # Return one candidate
        mock_mem_svc.kuzu_memory.db_adapter.execute_query = Mock(
            return_value=[{"m": mem.to_dict()}]
        )

        mock_user_svc = _make_user_svc_mock()

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory", return_value=mock_mem_svc
        ), patch("kuzu_memory.core.memory.KuzuMemory", return_value=mock_user_svc), patch(
            "kuzu_memory.utils.project_setup.get_project_db_path",
            return_value=Path("/tmp/fake-project/.kuzu-memory/memories.db"),
        ), patch.object(Path, "exists", return_value=True), patch.object(
            Path, "mkdir", return_value=None
        ):
            result = runner.invoke(user, ["promote", "--dry-run"], obj=ctx_obj)

        # Should not call promote_batch in dry-run mode
        mock_user_svc.promote_batch.assert_not_called()
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# user disable
# ---------------------------------------------------------------------------


class TestUserDisableCommand:
    def test_disable_exits_zero(self, runner: CliRunner) -> None:
        """user disable exits 0 and saves config."""
        ctx_obj = _mock_ctx_obj(mode="user")

        with patch(
            "kuzu_memory.core.config.KuzuMemoryConfig.save_to_file"
        ) as mock_save, patch.object(Path, "mkdir", return_value=None):
            result = runner.invoke(user, ["disable"], obj=ctx_obj)

        assert result.exit_code == 0, result.output
        mock_save.assert_called_once()

    def test_disable_sets_mode_to_project(self, runner: CliRunner) -> None:
        """user disable output indicates mode was changed to project."""
        ctx_obj = _mock_ctx_obj(mode="user")

        with patch("kuzu_memory.core.config.KuzuMemoryConfig.save_to_file"), patch.object(
            Path, "mkdir", return_value=None
        ):
            result = runner.invoke(user, ["disable"], obj=ctx_obj)

        assert result.exit_code == 0
        assert "project" in result.output.lower()

    def test_disable_writes_config_to_user_home(self, runner: CliRunner) -> None:
        """user disable saves config to ~/.kuzu-memory/config.yaml."""
        ctx_obj = _mock_ctx_obj(mode="user")
        saved_paths: list[Path] = []

        def capture_save(path: Path) -> None:
            saved_paths.append(Path(path))

        with patch(
            "kuzu_memory.core.config.KuzuMemoryConfig.save_to_file", side_effect=capture_save
        ), patch.object(Path, "mkdir", return_value=None):
            runner.invoke(user, ["disable"], obj=ctx_obj)

        assert len(saved_paths) == 1
        assert saved_paths[0].name == "config.yaml"
        assert ".kuzu-memory" in str(saved_paths[0])
