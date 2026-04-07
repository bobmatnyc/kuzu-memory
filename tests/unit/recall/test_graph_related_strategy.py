"""
Unit tests for GraphRelatedRecallStrategy.

Covers:
- Finds related memories via RELATES_TO edges from seeds
- kt_affinity relationship type gets +0.15 confidence bonus
- Falls back gracefully on empty graph (no RELATES_TO edges, no seeds)
- Deduplicates seed IDs so seeds do not appear in related results
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.core.models import KnowledgeType, Memory, MemoryType
from kuzu_memory.recall.strategies import GraphRelatedRecallStrategy

# The QueryBuilder is imported inline inside _execute_recall, so patch it at its
# definition site rather than where strategies.py would import it.
_QB_PATCH_PATH = "kuzu_memory.storage.query_builder.QueryBuilder"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> KuzuMemoryConfig:
    cfg = KuzuMemoryConfig.default()
    cfg.performance.enable_performance_monitoring = False
    return cfg


def _make_memory(
    content: str,
    memory_id: str = "m1",
    knowledge_type: KnowledgeType = KnowledgeType.NOTE,
    importance: float = 0.7,
) -> Memory:
    return Memory(
        id=memory_id,
        content=content,
        memory_type=MemoryType.SEMANTIC,
        source_type="test",
        importance=importance,
        confidence=0.9,
        created_at=datetime.now(),
        knowledge_type=knowledge_type,
    )


def _run_strategy(
    seed_memories: list[Memory],
    traversal_rows: list[dict[str, Any]] | None = None,
    traversal_exception: Exception | None = None,
    max_memories: int = 10,
    prompt: str = "test query",
) -> tuple[list[Memory], MagicMock]:
    """Build and execute a GraphRelatedRecallStrategy with controlled mocks.

    Returns (memories, adapter) so callers can inspect adapter call history.
    """
    adapter = MagicMock()
    adapter.db_path = "/tmp/test.db"
    config = _make_config()

    strategy = GraphRelatedRecallStrategy(adapter, config)
    # Patch keyword strategy seed step
    strategy._keyword_strategy._execute_recall = MagicMock(  # type: ignore[method-assign]
        return_value=seed_memories
    )

    if traversal_exception is not None:
        adapter.execute_query.side_effect = traversal_exception
    else:
        adapter.execute_query.return_value = traversal_rows or []

    # Build a mock QueryBuilder that passes through Memory objects directly.
    mock_qb = MagicMock()
    mock_qb._convert_db_result_to_memory.side_effect = lambda d: (
        d if isinstance(d, Memory) else None
    )

    with patch(_QB_PATCH_PATH, return_value=mock_qb):
        memories = strategy._execute_recall(
            prompt=prompt,
            max_memories=max_memories,
            user_id=None,
            session_id=None,
            agent_id="default",
        )

    return memories, adapter


# ---------------------------------------------------------------------------
# TestFindsRelatedViaRelatesToEdges
# ---------------------------------------------------------------------------


class TestFindsRelatedViaRelatesToEdges:
    def test_finds_related_via_relates_to_edges(self) -> None:
        """Strategy must return memories surfaced via RELATES_TO traversal."""
        seed = _make_memory("seed memory about Python", memory_id="seed1")
        related = _make_memory("related memory about async", memory_id="rel1")

        traversal_rows = [
            {"related": related, "total_weight": 3.0, "rel_type": "shared_entity"},
        ]

        memories, _ = _run_strategy([seed], traversal_rows=traversal_rows)

        assert len(memories) == 1
        assert memories[0].id == "rel1"

    def test_traversal_query_uses_seed_ids(self) -> None:
        """The traversal query must pass seed IDs as a parameter."""
        seed = _make_memory("seed", memory_id="seed1")

        _, adapter = _run_strategy([seed])

        calls = adapter.execute_query.call_args_list
        assert calls, "execute_query was never called"
        traversal_call = calls[0]
        params = (
            traversal_call.args[1]
            if len(traversal_call.args) > 1
            else traversal_call.kwargs.get("params", {})
        )
        assert "seed_ids" in params, f"seed_ids not in traversal params: {params}"
        assert "seed1" in params["seed_ids"]

    def test_confidence_scales_with_weight(self) -> None:
        """Confidence should be 0.5 * (weight / 5.0), capped at 1.0."""
        seed = _make_memory("seed", memory_id="seed1")
        related = _make_memory("related", memory_id="rel1")

        # weight=5.0 → confidence = 0.5 * (5/5) = 0.5
        traversal_rows = [
            {"related": related, "total_weight": 5.0, "rel_type": "shared_entity"},
        ]
        memories, _ = _run_strategy([seed], traversal_rows=traversal_rows)

        assert len(memories) == 1
        assert (
            abs(memories[0].confidence - 0.5) < 0.001
        ), f"Expected confidence ~0.5, got {memories[0].confidence}"

    def test_no_seeds_returns_empty(self) -> None:
        """When keyword search finds no seeds, no traversal should happen."""
        memories, adapter = _run_strategy(seed_memories=[])

        assert memories == []
        # Traversal query should NOT have been called.
        adapter.execute_query.assert_not_called()


# ---------------------------------------------------------------------------
# TestKtAffinityGetsConfidenceBonus
# ---------------------------------------------------------------------------


class TestKtAffinityGetsConfidenceBonus:
    def test_kt_affinity_gets_confidence_bonus(self) -> None:
        """kt_affinity relationship type must receive a +0.15 confidence bonus."""
        seed = _make_memory("seed", memory_id="seed1")
        related = _make_memory("related gotcha-pattern", memory_id="rel1")

        # weight=2.5 → base = 0.5 * (2.5/5.0) = 0.25 → with bonus = 0.40
        traversal_rows = [
            {"related": related, "total_weight": 2.5, "rel_type": "kt_affinity"},
        ]
        memories, _ = _run_strategy([seed], traversal_rows=traversal_rows)

        assert len(memories) == 1
        expected = 0.5 * (2.5 / 5.0) + 0.15
        assert (
            abs(memories[0].confidence - expected) < 0.001
        ), f"Expected confidence ~{expected:.3f}, got {memories[0].confidence:.3f}"

    def test_shared_entity_no_bonus(self) -> None:
        """shared_entity relationship type must NOT receive the kt_affinity bonus."""
        seed = _make_memory("seed", memory_id="seed1")
        related = _make_memory("related", memory_id="rel1")

        # weight=2.5 → base = 0.5 * (2.5/5.0) = 0.25, no bonus
        traversal_rows = [
            {"related": related, "total_weight": 2.5, "rel_type": "shared_entity"},
        ]
        memories, _ = _run_strategy([seed], traversal_rows=traversal_rows)

        assert len(memories) == 1
        expected = 0.5 * (2.5 / 5.0)  # no bonus
        assert (
            abs(memories[0].confidence - expected) < 0.001
        ), f"Expected confidence ~{expected:.3f} (no bonus), got {memories[0].confidence:.3f}"

    def test_high_weight_confidence_capped_at_1(self) -> None:
        """Confidence must be capped at 1.0 even with kt_affinity bonus and high weight."""
        seed = _make_memory("seed", memory_id="seed1")
        related = _make_memory("related", memory_id="rel1")

        # weight=100 → min(100,5)/5 = 1.0 → base 0.5 + bonus 0.15 = 0.65 → cap 1.0
        traversal_rows = [
            {"related": related, "total_weight": 100.0, "rel_type": "kt_affinity"},
        ]
        memories, _ = _run_strategy([seed], traversal_rows=traversal_rows)

        assert len(memories) == 1
        assert memories[0].confidence <= 1.0, f"Confidence exceeded 1.0: {memories[0].confidence}"


# ---------------------------------------------------------------------------
# TestFallsBackGracefullyOnEmptyGraph
# ---------------------------------------------------------------------------


class TestFallsBackGracefullyOnEmptyGraph:
    def test_falls_back_gracefully_on_empty_graph(self) -> None:
        """Returns empty list when traversal finds no related memories."""
        seed = _make_memory("seed", memory_id="seed1")
        memories, _ = _run_strategy([seed], traversal_rows=[])

        assert memories == []

    def test_traversal_exception_returns_empty_not_raises(self) -> None:
        """If the RELATES_TO traversal query raises, return [] not exception."""
        seed = _make_memory("seed", memory_id="seed1")
        memories, _ = _run_strategy(
            [seed],
            traversal_exception=RuntimeError("RELATES_TO table does not exist"),
        )

        assert memories == [], "Expected empty list on traversal failure"

    def test_no_seeds_no_db_query(self) -> None:
        """When keyword step returns no seeds, no DB query should be issued."""
        memories, adapter = _run_strategy(seed_memories=[])

        assert memories == []
        adapter.execute_query.assert_not_called()


# ---------------------------------------------------------------------------
# TestDeduplicatesSeedAndRelated
# ---------------------------------------------------------------------------


class TestDeduplicatesSeedAndRelated:
    def test_deduplicates_seed_and_related(self) -> None:
        """The traversal query must exclude seed IDs from related results."""
        seed = _make_memory("seed", memory_id="seed1")
        _, adapter = _run_strategy([seed])

        calls = adapter.execute_query.call_args_list
        assert calls, "No execute_query calls"

        traversal_call = calls[0]
        params = (
            traversal_call.args[1]
            if len(traversal_call.args) > 1
            else traversal_call.kwargs.get("params", {})
        )
        assert "seed_ids" in params, f"seed_ids not found in params: {params}"
        assert "seed1" in params["seed_ids"], f"seed1 not in seed_ids: {params['seed_ids']}"

    def test_traversal_query_excludes_seed_ids_in_where(self) -> None:
        """The Cypher traversal query must filter out seed IDs via NOT IN $seed_ids."""
        seed = _make_memory("seed", memory_id="seed1")
        _, adapter = _run_strategy([seed])

        queries = [c.args[0] for c in adapter.execute_query.call_args_list]
        traversal_queries = [q for q in queries if "RELATES_TO" in q]
        assert traversal_queries, "No RELATES_TO traversal query issued"

        q = traversal_queries[0]
        assert "NOT IN $seed_ids" in q, f"Expected 'NOT IN $seed_ids' in traversal query, got:\n{q}"
