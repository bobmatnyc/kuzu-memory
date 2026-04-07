"""
Unit tests for KeywordRecallStrategy.

The TF-IDF graph path (_recall_via_keyword_graph) is currently disabled because
raw SUM(tfidf) scores are not normalized against semantic similarity scores,
causing a ranking collapse (R@5: 89%→40% in v1.11.0).  The Keyword/HAS_KEYWORD
graph is still populated by TFIDFKeywordEnricher for future use once scoring
normalization is implemented.

All recall now goes through the content scan path (_recall_via_content_scan).

Coverage:
- Content scan is always the primary path (graph path never called)
- Content scan returns results correctly
- Empty content scan returns empty list (no error)
- Results from content scan are returned in created_at/importance order
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
    scan_rows: list[dict[str, Any]],
) -> tuple[KeywordRecallStrategy, dict[str, int]]:
    """Build a KeywordRecallStrategy with a mock adapter.

    The adapter tracks whether graph vs. scan queries are executed.
    Returns (strategy, call_count_dict).
    """
    call_count: dict[str, int] = {"graph": 0, "scan": 0}

    def _execute(query: str, params: dict | None = None) -> list[dict]:
        if "HAS_KEYWORD" in query:
            call_count["graph"] += 1
            return []
        else:
            call_count["scan"] += 1
            return list(scan_rows)

    adapter = MagicMock()
    adapter.execute_query.side_effect = _execute

    strategy = KeywordRecallStrategy(adapter, _make_config())
    strategy._call_count = call_count
    return strategy, call_count


# ---------------------------------------------------------------------------
# Test: graph path is disabled — content scan is always used
# ---------------------------------------------------------------------------


class TestGraphPathDisabled:
    """TF-IDF graph path is disabled; content scan is always the primary path."""

    def test_content_scan_used_not_graph(self) -> None:
        """Graph path must not be called; content scan must always be used."""
        memory_data = _make_memory_row("m1", "python async programming")
        scan_rows = [{"m": memory_data}]

        strategy, call_count = _make_strategy(scan_rows=scan_rows)

        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            mock_memory = MagicMock()
            MockQB.return_value._convert_db_result_to_memory.return_value = mock_memory

            memories = strategy._execute_recall(
                prompt="python programming",
                max_memories=5,
                user_id=None,
                session_id=None,
                agent_id="default",
            )

        assert call_count["graph"] == 0, "Graph path must not be called while disabled"
        assert call_count["scan"] >= 1, "Content scan must be used as primary path"
        assert len(memories) == 1

    def test_graph_path_never_called_regardless_of_keywords(self) -> None:
        """Even with keywords present, graph path must remain dormant."""
        strategy, call_count = _make_strategy(scan_rows=[])

        strategy._execute_recall("python async database", 5, None, None, "default")

        assert call_count["graph"] == 0, "Graph path must remain disabled"


# ---------------------------------------------------------------------------
# Test: content scan always runs as primary path
# ---------------------------------------------------------------------------


class TestContentScanPrimary:
    def test_content_scan_returns_results(self) -> None:
        """Content scan results are returned correctly."""
        memory_data = _make_memory_row("m2", "fallback content")
        scan_rows = [{"m": memory_data}]

        strategy, call_count = _make_strategy(scan_rows=scan_rows)

        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            MockQB.return_value._convert_db_result_to_memory.return_value = MagicMock()

            strategy._execute_recall(
                prompt="fallback content",
                max_memories=5,
                user_id=None,
                session_id=None,
                agent_id="default",
            )

        assert call_count["scan"] >= 1, "Content scan must run as primary path"

    def test_content_scan_results_returned(self) -> None:
        """Results from content scan are correctly returned."""
        memory_data = _make_memory_row("m3", "python database")
        scan_rows = [{"m": memory_data}]

        strategy, _ = _make_strategy(scan_rows=scan_rows)

        fake_memory = MagicMock()
        with patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB:
            MockQB.return_value._convert_db_result_to_memory.return_value = fake_memory

            memories = strategy._execute_recall("python", 5, None, None, "default")

        assert len(memories) == 1
        assert memories[0] is fake_memory


# ---------------------------------------------------------------------------
# Test: empty and error cases
# ---------------------------------------------------------------------------


class TestEmptyAndErrorCases:
    def test_empty_scan_returns_empty_list(self) -> None:
        """When content scan returns nothing, result is an empty list (no error)."""
        strategy, _ = _make_strategy(scan_rows=[])

        memories = strategy._execute_recall("something", 5, None, None, "default")
        assert memories == []

    def test_no_keywords_returns_empty(self) -> None:
        """Prompts with only stop words produce no keywords and return empty list."""
        strategy, call_count = _make_strategy(scan_rows=[])

        # All stop words — _extract_keywords returns []
        memories = strategy._execute_recall("the a an is are", 5, None, None, "default")

        assert memories == []
        assert call_count["scan"] == 0, "Scan must not run when no keywords extracted"
        assert call_count["graph"] == 0


# ---------------------------------------------------------------------------
# Test: content scan ordering
# ---------------------------------------------------------------------------


class TestContentScanOrdering:
    def test_content_scan_results_preserve_order(self) -> None:
        """Results from content scan are returned in the order the DB supplies them
        (created_at DESC, importance DESC — enforced by the query itself)."""
        rows = [
            {"m": _make_memory_row("first", "python async")},
            {"m": _make_memory_row("second", "python database")},
            {"m": _make_memory_row("third", "database")},
        ]

        strategy, call_count = _make_strategy(scan_rows=rows)

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

        assert call_count["graph"] == 0, "Graph path must remain disabled"
        assert call_count["scan"] >= 1
        # Order from content scan must be preserved
        assert converted_ids == ["first", "second", "third"]
        assert [m.id for m in memories] == ["first", "second", "third"]
