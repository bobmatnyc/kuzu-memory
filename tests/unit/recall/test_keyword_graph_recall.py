"""
Unit tests for KeywordRecallStrategy graph-based path.

Coverage:
- Graph path is used when HAS_KEYWORD edges exist (returns results)
- Falls back to content scan when graph returns no results (empty Keyword table)
- Falls back to content scan when graph query raises an exception
- Results from graph path are ordered by TF-IDF relevance (descending)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.recall.strategies import KeywordRecallStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> KuzuMemoryConfig:
    return KuzuMemoryConfig.default()


def _make_memory_row(mem_id: str, content: str = "test content") -> dict[str, Any]:
    """Return a fake row dict that mimics what execute_query returns for a Memory node."""
    return {
        "id": mem_id,
        "content": content,
        "content_hash": "",
        "created_at": "2024-01-01T00:00:00",
        "valid_from": None,
        "valid_to": None,
        "accessed_at": None,
        "access_count": 0,
        "memory_type": "working",
        "knowledge_type": "note",
        "project_tag": "",
        "importance": 0.5,
        "confidence": 1.0,
        "source_type": "conversation",
        "agent_id": "default",
        "user_id": None,
        "session_id": None,
        "metadata": "{}",
        "embedding": None,
    }


def _make_strategy(
    graph_rows: list[dict[str, Any]],
    scan_rows: list[dict[str, Any]],
) -> tuple[KeywordRecallStrategy, dict[str, int]]:
    """Build a KeywordRecallStrategy with a mock adapter.

    The adapter distinguishes graph vs. scan calls by query content:
    - Graph query contains "HAS_KEYWORD"
    - Scan query contains "LOWER(m.content)"

    Returns (strategy, call_count_dict).
    """
    call_count: dict[str, int] = {"graph": 0, "scan": 0}

    def _execute(query: str, params: dict | None = None) -> list[dict]:
        if "HAS_KEYWORD" in query:
            call_count["graph"] += 1
            return list(graph_rows)
        else:
            call_count["scan"] += 1
            return list(scan_rows)

    adapter = MagicMock()
    adapter.execute_query.side_effect = _execute

    strategy = KeywordRecallStrategy(adapter, _make_config())
    strategy._call_count = call_count
    return strategy, call_count


# ---------------------------------------------------------------------------
# Test: graph path used when keywords exist
# ---------------------------------------------------------------------------


class TestGraphPathUsed:
    def test_graph_path_used_when_keywords_exist(self) -> None:
        """When the graph query returns results, the graph path should be used."""
        memory_data = _make_memory_row("m1", "python async programming")
        graph_rows = [{"m": memory_data, "relevance": 0.75}]

        strategy, call_count = _make_strategy(
            graph_rows=graph_rows,
            scan_rows=[],
        )

        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            mock_memory = MagicMock()
            MockQB.return_value._convert_db_result_to_memory.return_value = mock_memory

            strategy._execute_recall(
                prompt="python programming",
                max_memories=5,
                user_id=None,
                session_id=None,
                agent_id="default",
            )

        assert call_count["graph"] >= 1, "Graph path was not attempted"
        assert call_count["scan"] == 0, "Content scan should not run when graph returns results"

    def test_scan_not_called_when_graph_succeeds(self) -> None:
        """Content scan must be skipped entirely when the graph path returns memories."""
        memory_data = _make_memory_row("m1")
        graph_rows = [{"m": memory_data, "relevance": 0.5}]

        strategy, call_count = _make_strategy(graph_rows=graph_rows, scan_rows=[])

        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            MockQB.return_value._convert_db_result_to_memory.return_value = MagicMock()
            strategy._execute_recall("test query", 5, None, None, "default")

        assert call_count["scan"] == 0


# ---------------------------------------------------------------------------
# Test: fall back to content scan when no keywords in graph
# ---------------------------------------------------------------------------


class TestFallbackWhenNoKeywords:
    def test_falls_back_to_content_scan_when_no_keywords(self) -> None:
        """When graph returns empty (Keyword table unpopulated), content scan runs."""
        memory_data = _make_memory_row("m2", "fallback content")
        scan_rows = [{"m": memory_data}]

        strategy, call_count = _make_strategy(graph_rows=[], scan_rows=scan_rows)

        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            MockQB.return_value._convert_db_result_to_memory.return_value = MagicMock()

            strategy._execute_recall(
                prompt="fallback content",
                max_memories=5,
                user_id=None,
                session_id=None,
                agent_id="default",
            )

        assert call_count["graph"] >= 1, "Graph path should be attempted first"
        assert call_count["scan"] >= 1, "Content scan should run when graph returns nothing"

    def test_content_scan_results_returned_on_empty_graph(self) -> None:
        """Results from content scan are returned when graph path yields nothing."""
        memory_data = _make_memory_row("m3", "python database")
        scan_rows = [{"m": memory_data}]

        strategy, _ = _make_strategy(graph_rows=[], scan_rows=scan_rows)

        fake_memory = MagicMock()
        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            MockQB.return_value._convert_db_result_to_memory.return_value = fake_memory

            memories = strategy._execute_recall("python", 5, None, None, "default")

        assert len(memories) == 1
        assert memories[0] is fake_memory


# ---------------------------------------------------------------------------
# Test: fall back on query error
# ---------------------------------------------------------------------------


class TestFallbackOnQueryError:
    def test_falls_back_on_query_error(self) -> None:
        """If the graph query raises, strategy must fall back to content scan silently."""
        memory_data = _make_memory_row("m4")
        scan_rows = [{"m": memory_data}]
        call_count: dict[str, int] = {"graph": 0, "scan": 0}

        def _execute(query: str, params: dict | None = None) -> list[dict]:
            if "HAS_KEYWORD" in query:
                call_count["graph"] += 1
                raise RuntimeError("HAS_KEYWORD table does not exist")
            else:
                call_count["scan"] += 1
                return list(scan_rows)

        adapter = MagicMock()
        adapter.execute_query.side_effect = _execute

        strategy = KeywordRecallStrategy(adapter, _make_config())

        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            MockQB.return_value._convert_db_result_to_memory.return_value = MagicMock()
            # Must not raise.
            memories = strategy._execute_recall("database python", 5, None, None, "default")

        assert call_count["graph"] >= 1, "Graph path should have been attempted"
        assert call_count["scan"] >= 1, "Content scan should have been used as fallback"
        assert isinstance(memories, list)

    def test_no_results_returned_on_both_paths_empty(self) -> None:
        """When both paths return empty, result is an empty list (no error)."""
        strategy, _ = _make_strategy(graph_rows=[], scan_rows=[])

        memories = strategy._execute_recall("something", 5, None, None, "default")
        assert memories == []


# ---------------------------------------------------------------------------
# Test: relevance ordering by TF-IDF
# ---------------------------------------------------------------------------


class TestRelevanceOrdering:
    def test_relevance_ordering_by_tfidf(self) -> None:
        """Memories returned from graph path should be in descending relevance order."""
        # The adapter returns rows sorted by relevance DESC (as the query requests).
        # We verify the strategy preserves that ordering.
        rows = [
            {"m": _make_memory_row("high", "python async"), "relevance": 1.5},
            {"m": _make_memory_row("mid", "python database"), "relevance": 0.8},
            {"m": _make_memory_row("low", "database"), "relevance": 0.2},
        ]

        strategy, call_count = _make_strategy(graph_rows=rows, scan_rows=[])

        # Track order of convert calls.
        converted_ids: list[str] = []

        def _convert(mem_data: dict) -> MagicMock:
            mem_id = mem_data.get("id", "unknown")
            converted_ids.append(str(mem_id))
            m = MagicMock()
            m.id = mem_id
            return m

        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            MockQB.return_value._convert_db_result_to_memory.side_effect = _convert

            memories = strategy._execute_recall("python async", 5, None, None, "default")

        assert call_count["graph"] >= 1
        # The order from the graph query (highest relevance first) must be preserved.
        assert converted_ids == ["high", "mid", "low"]
        assert [m.id for m in memories] == ["high", "mid", "low"]
