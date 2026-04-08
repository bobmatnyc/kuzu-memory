"""
Unit tests for UserMemoryService.

Tests promotion, deduplication, batch operations, pattern retrieval, stats,
and context manager lifecycle — all with mocked KuzuMemory to avoid real I/O.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig, UserConfig
from kuzu_memory.core.models import KnowledgeType, Memory, MemoryType
from kuzu_memory.services.user_memory_service import UserMemoryService

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_memory(
    content: str = "Test content",
    knowledge_type: KnowledgeType = KnowledgeType.PATTERN,
    importance: float = 0.9,
    project_tag: str = "",
) -> Memory:
    """Create a minimal Memory with deterministic hash."""
    return Memory(
        content=content,
        memory_type=MemoryType.SEMANTIC,
        knowledge_type=knowledge_type,
        importance=importance,
        project_tag=project_tag,
        source_type="test",
        agent_id="test-agent",
    )


def _make_config(mode: str = "user") -> KuzuMemoryConfig:
    cfg = KuzuMemoryConfig()
    cfg.user.mode = mode
    cfg.user.user_db_path = "/tmp/test-user.db"
    return cfg


@pytest.fixture
def mock_kuzu_memory() -> MagicMock:
    """Mock KuzuMemory instance returned by context manager."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=None)
    mock.db_adapter = MagicMock()
    mock.db_adapter.execute_query = Mock(return_value=[])
    mock.get_memory_count = Mock(return_value=0)
    return mock


@pytest.fixture
def user_service(mock_kuzu_memory: MagicMock) -> UserMemoryService:
    """UserMemoryService with mocked KuzuMemory."""
    config = _make_config()
    svc = UserMemoryService(config)

    # KuzuMemory is imported lazily inside __enter__, so patch the source module
    with (
        patch("kuzu_memory.core.memory.KuzuMemory", return_value=mock_kuzu_memory),
        patch.object(Path, "mkdir", return_value=None),
    ):
        # Enter the context manager to set up svc._memory
        svc.__enter__()
        yield svc
        svc.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Context manager lifecycle
# ---------------------------------------------------------------------------


class TestContextManagerLifecycle:
    def test_context_manager_opens_and_closes(self, mock_kuzu_memory: MagicMock) -> None:
        """UserMemoryService context manager enters and exits correctly."""
        config = _make_config()
        svc = UserMemoryService(config)

        # KuzuMemory is a lazy import inside __enter__; patch the source module
        with (
            patch(
                "kuzu_memory.core.memory.KuzuMemory",
                return_value=mock_kuzu_memory,
            ),
            patch.object(Path, "mkdir", return_value=None),
        ):
            assert svc._memory is None
            result = svc.__enter__()
            assert result is svc
            assert svc._memory is not None

            svc.__exit__(None, None, None)
            assert svc._memory is None

    def test_context_manager_via_with_statement(self, mock_kuzu_memory: MagicMock) -> None:
        """with UserMemoryService(...) pattern works end-to-end."""
        config = _make_config()

        with (
            patch(
                "kuzu_memory.core.memory.KuzuMemory",
                return_value=mock_kuzu_memory,
            ),
            patch.object(Path, "mkdir", return_value=None),
        ):
            with UserMemoryService(config) as svc:
                assert svc._memory is not None
            assert svc._memory is None


# ---------------------------------------------------------------------------
# promote()
# ---------------------------------------------------------------------------


class TestPromote:
    def test_promote_stores_memory(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """promote() writes the memory to the user DB and returns True."""
        # No duplicate found
        mock_kuzu_memory.db_adapter.execute_query.return_value = []

        mem = _make_memory()
        result = user_service.promote(mem, project_tag="my-project")

        assert result is True
        # CREATE was called (second call after the duplicate check)
        assert mock_kuzu_memory.db_adapter.execute_query.call_count >= 2

    def test_promote_deduplicates_by_content_hash(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """promote() returns False when content_hash already exists."""
        # Simulate duplicate found
        mock_kuzu_memory.db_adapter.execute_query.return_value = [{"m.id": "existing-id"}]

        mem = _make_memory()
        result = user_service.promote(mem, project_tag="my-project")

        assert result is False
        # Only the duplicate-check query should have been called
        assert mock_kuzu_memory.db_adapter.execute_query.call_count == 1

    def test_promote_sets_project_tag(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """promote() passes project_tag in the CREATE statement parameters."""
        mock_kuzu_memory.db_adapter.execute_query.return_value = []

        mem = _make_memory()
        user_service.promote(mem, project_tag="kuzu-memory")

        # Extract the CREATE call's parameters
        calls = mock_kuzu_memory.db_adapter.execute_query.call_args_list
        create_call = calls[-1]  # last call is the CREATE
        params: dict[str, Any] = create_call[0][1]  # positional arg [1]
        assert params["project_tag"] == "kuzu-memory"

    def test_promote_handles_exception_gracefully(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """promote() swallows exceptions and returns False."""
        mock_kuzu_memory.db_adapter.execute_query.side_effect = RuntimeError("DB error")

        mem = _make_memory()
        result = user_service.promote(mem, project_tag="project")
        assert result is False


# ---------------------------------------------------------------------------
# promote_batch()
# ---------------------------------------------------------------------------


class TestPromoteBatch:
    def test_promote_batch_returns_written_count(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """promote_batch() returns the number of successfully written memories."""
        # First memory: no duplicate → write succeeds
        # Second memory: duplicate found → skip
        side_effects = [
            [],  # duplicate check for mem1 → not found
            [{"ignored": True}],  # CREATE for mem1 → (return value unused)
            [{"m.id": "dup"}],  # duplicate check for mem2 → found
        ]
        mock_kuzu_memory.db_adapter.execute_query.side_effect = side_effects

        mem1 = _make_memory(content="Memory one")
        mem2 = _make_memory(content="Memory two")
        count = user_service.promote_batch([mem1, mem2], project_tag="proj")
        assert count == 1

    def test_promote_batch_empty_list(self, user_service: UserMemoryService) -> None:
        """promote_batch() returns 0 for empty list without errors."""
        count = user_service.promote_batch([], project_tag="proj")
        assert count == 0

    def test_promote_batch_all_new(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """promote_batch() returns n for n new memories."""
        # Each memory: not duplicate → write succeeds
        mock_kuzu_memory.db_adapter.execute_query.return_value = []
        memories = [_make_memory(content=f"Memory {i}") for i in range(5)]
        count = user_service.promote_batch(memories, project_tag="proj")
        assert count == 5


# ---------------------------------------------------------------------------
# get_patterns()
# ---------------------------------------------------------------------------


class TestGetPatterns:
    def test_get_patterns_returns_memories(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """get_patterns() returns Memory objects from DB rows."""
        mem = _make_memory(content="Use context manager for DB access")
        row = {"m": mem.to_dict()}
        mock_kuzu_memory.db_adapter.execute_query.return_value = [row]

        results = user_service.get_patterns()
        assert len(results) == 1
        assert isinstance(results[0], Memory)

    def test_get_patterns_filters_by_knowledge_type(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """get_patterns() passes knowledge_type filter to query."""
        mock_kuzu_memory.db_adapter.execute_query.return_value = []

        user_service.get_patterns(knowledge_types=[KnowledgeType.RULE])

        call_args = mock_kuzu_memory.db_adapter.execute_query.call_args
        params: dict[str, Any] = call_args[0][1]
        assert params["types"] == ["rule"]

    def test_get_patterns_default_types_include_key_types(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """get_patterns() default includes rule, pattern, gotcha, architecture."""
        mock_kuzu_memory.db_adapter.execute_query.return_value = []

        user_service.get_patterns()

        call_args = mock_kuzu_memory.db_adapter.execute_query.call_args
        params: dict[str, Any] = call_args[0][1]
        assert set(params["types"]) == {"rule", "pattern", "gotcha", "architecture"}

    def test_get_patterns_returns_empty_on_db_error(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """get_patterns() returns [] when DB raises an exception."""
        mock_kuzu_memory.db_adapter.execute_query.side_effect = RuntimeError("DB unavailable")
        results = user_service.get_patterns()
        assert results == []


# ---------------------------------------------------------------------------
# get_stats()
# ---------------------------------------------------------------------------


class TestGetStats:
    def test_get_stats_returns_dict(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """get_stats() returns a dict with expected keys."""
        mock_kuzu_memory.get_memory_count.return_value = 42
        mock_kuzu_memory.db_adapter.execute_query.side_effect = [
            [{"kt": "pattern", "cnt": 20}, {"kt": "rule", "cnt": 22}],
            [{"pt": "project-a", "cnt": 30}, {"pt": "project-b", "cnt": 12}],
        ]

        stats = user_service.get_stats()

        assert isinstance(stats, dict)
        assert stats["total_memories"] == 42
        assert "by_knowledge_type" in stats
        assert "by_project" in stats
        assert stats["by_knowledge_type"]["pattern"] == 20
        assert stats["by_knowledge_type"]["rule"] == 22
        assert stats["by_project"]["project-a"] == 30

    def test_get_stats_includes_db_path(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """get_stats() includes db_path in result."""
        mock_kuzu_memory.get_memory_count.return_value = 0
        mock_kuzu_memory.db_adapter.execute_query.return_value = []

        stats = user_service.get_stats()
        assert "db_path" in stats

    def test_get_stats_returns_safe_dict_on_error(
        self, user_service: UserMemoryService, mock_kuzu_memory: MagicMock
    ) -> None:
        """get_stats() returns a safe dict (not exception) when DB errors occur."""
        mock_kuzu_memory.get_memory_count.side_effect = RuntimeError("DB error")

        stats = user_service.get_stats()
        assert isinstance(stats, dict)
        assert stats.get("total_memories") == 0
        assert "error" in stats
