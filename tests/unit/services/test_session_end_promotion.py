"""
Unit tests for session-end promotion in MemoryService.

Verifies:
- Promotion runs in background thread when mode is "user"
- Promotion does NOT run when mode is "project"
- Promotion exceptions are swallowed (non-fatal)
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.services.memory_service import MemoryService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(mode: str = "user") -> KuzuMemoryConfig:
    cfg = KuzuMemoryConfig()
    cfg.user.mode = mode
    cfg.user.user_db_path = "/tmp/test-user-session.db"
    cfg.user.promotion_min_importance = 0.8
    cfg.user.promotion_knowledge_types = ["rule", "pattern", "gotcha", "architecture"]
    return cfg


@pytest.fixture
def mock_kuzu_memory() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    mock.db_adapter = MagicMock()
    mock.db_adapter.execute_query = Mock(return_value=[])
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSessionEndPromotion:
    def test_promotion_only_when_mode_is_user(self, mock_kuzu_memory: MagicMock) -> None:
        """_promote_eligible_memories() is called only when user.mode == 'user'."""
        config = _make_config(mode="user")

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            service = MemoryService(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=False,
                config=config,
            )
            with patch.object(service, "_promote_eligible_memories") as mock_promote:
                service.initialize()
                service.cleanup()

            mock_promote.assert_called_once()

    def test_promotion_not_called_in_project_mode(self, mock_kuzu_memory: MagicMock) -> None:
        """_promote_eligible_memories() is NOT called when user.mode == 'project'."""
        config = _make_config(mode="project")

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            service = MemoryService(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=False,
                config=config,
            )
            with patch.object(service, "_promote_eligible_memories") as mock_promote:
                service.initialize()
                service.cleanup()

            mock_promote.assert_not_called()

    def test_promotion_runs_in_background_on_exit(self, mock_kuzu_memory: MagicMock) -> None:
        """_do_cleanup() spawns a background thread for promotion."""
        config = _make_config(mode="user")

        # UserMemoryService is a lazy import inside _do_promote, patch source module
        mock_user_svc = MagicMock()
        mock_user_svc.__enter__ = Mock(return_value=mock_user_svc)
        mock_user_svc.__exit__ = Mock(return_value=None)
        mock_user_svc.promote_batch = Mock(return_value=0)

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ), patch(
            "kuzu_memory.services.user_memory_service.UserMemoryService",
            return_value=mock_user_svc,
        ):
            service = MemoryService(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=False,
                config=config,
            )
            service.initialize()

            with patch.object(threading, "Thread", wraps=threading.Thread) as mock_thread_cls:
                service.cleanup()

            # A Thread should have been constructed
            assert mock_thread_cls.called

    def test_promotion_errors_are_swallowed(self, mock_kuzu_memory: MagicMock) -> None:
        """Errors during promotion do not propagate to cleanup caller."""
        config = _make_config(mode="user")

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            service = MemoryService(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=False,
                config=config,
            )

            def explode() -> int:
                raise RuntimeError("Simulated promotion failure")

            with patch.object(service, "_promote_eligible_memories", side_effect=explode):
                service.initialize()
                # Should NOT raise
                try:
                    service.cleanup()
                except RuntimeError:
                    pytest.fail("_promote_eligible_memories exception leaked through cleanup()")

    def test_promote_eligible_memories_returns_zero_immediately(
        self, mock_kuzu_memory: MagicMock
    ) -> None:
        """_promote_eligible_memories() returns 0 (async — count not available)."""
        config = _make_config(mode="user")

        with patch(
            "kuzu_memory.services.memory_service.KuzuMemory",
            return_value=mock_kuzu_memory,
        ):
            service = MemoryService(
                db_path=Path("/tmp/test.db"),
                enable_git_sync=False,
                config=config,
            )
            service.initialize()

            with patch("threading.Thread") as mock_thread_cls:
                mock_thread_inst = MagicMock()
                mock_thread_cls.return_value = mock_thread_inst

                result = service._promote_eligible_memories()

            assert result == 0

            service.cleanup()
