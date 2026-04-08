"""
Unit tests for TF-IDF multiplicative boost in RecallCoordinator.

Covers:
- test_boost_raises_score_for_keyword_match
- test_boost_zero_weight_is_noop
- test_boost_no_keyword_match_unchanged
- test_boost_normalized_per_query
- test_boost_graceful_on_db_error
- test_boost_empty_memory_list
- test_boost_reorders_by_boosted_score
- test_tfidf_boost_weight_env_var
"""

from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig, RecallConfig
from kuzu_memory.core.models import KnowledgeType, Memory, MemoryType
from kuzu_memory.recall.coordinator import RecallCoordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(
    memory_id: str = "mem-1",
    content: str = "test content",
    importance: float = 0.6,
    confidence: float = 0.8,
) -> Memory:
    """Return a minimal Memory object suitable for ranking tests.

    Uses MemoryType.EPISODIC whose default importance (0.7) differs from the
    test default (0.6) so the Pydantic validator does not silently override
    the importance we pass in.  The validator only fires when importance==0.5
    (the Pydantic field default), so any other value passes through unchanged.
    """
    return Memory(
        id=memory_id,
        content=content,
        memory_type=MemoryType.EPISODIC,
        knowledge_type=KnowledgeType.NOTE,
        importance=importance,
        confidence=confidence,
        created_at=datetime.now(),
        valid_to=None,
        user_id=None,
        session_id=None,
    )


def _make_coordinator(
    tfidf_boost_weight: float = 0.3,
    db_return_value: list[dict] | None = None,
    db_raise: Exception | None = None,
) -> tuple[RecallCoordinator, MagicMock]:
    """Return (coordinator, mock_adapter) for testing _apply_tfidf_boost."""
    mock_adapter = MagicMock()
    mock_adapter.db_path = "/tmp/test_tfidf.db"

    if db_raise is not None:
        mock_adapter.execute_query.side_effect = db_raise
    elif db_return_value is not None:
        mock_adapter.execute_query.return_value = db_return_value
    else:
        mock_adapter.execute_query.return_value = []

    config = KuzuMemoryConfig.default()
    config.recall.tfidf_boost_weight = tfidf_boost_weight
    config.performance.enable_performance_monitoring = False

    coordinator = RecallCoordinator(db_adapter=mock_adapter, config=config)  # type: ignore[arg-type]
    return coordinator, mock_adapter


# ---------------------------------------------------------------------------
# _apply_tfidf_boost unit tests
# ---------------------------------------------------------------------------


class TestApplyTfidfBoost:
    """Direct unit tests for RecallCoordinator._apply_tfidf_boost."""

    def test_boost_raises_score_for_keyword_match(self) -> None:
        """A memory with a matching keyword should have its importance raised."""
        mem = _make_memory("m1", importance=0.6)
        original_importance = mem.importance

        db_rows = [{"memory_id": "m1", "tfidf_sum": 1.0}]
        coordinator, _ = _make_coordinator(tfidf_boost_weight=0.3, db_return_value=db_rows)

        result = coordinator._apply_tfidf_boost([mem], "matching keyword query", weight=0.3)

        assert len(result) == 1
        # max_tfidf = 1.0, normalised = 1.0, boost_factor = 1.3
        expected = min(1.0, original_importance * 1.3)
        assert result[0].importance == pytest.approx(expected)

    def test_boost_zero_weight_is_noop(self) -> None:
        """weight=0 should return the original list without querying the DB."""
        mem = _make_memory("m1", importance=0.6)
        coordinator, mock_adapter = _make_coordinator(
            tfidf_boost_weight=0.0,
            db_return_value=[{"memory_id": "m1", "tfidf_sum": 1.0}],
        )

        result = coordinator._apply_tfidf_boost([mem], "some query", weight=0.0)

        # No DB query should have been made
        mock_adapter.execute_query.assert_not_called()
        assert result is not None
        assert len(result) == 1
        assert result[0].importance == pytest.approx(0.6)

    def test_boost_no_keyword_match_unchanged(self) -> None:
        """Memory with no keyword match (DB returns empty) keeps original importance."""
        mem = _make_memory("m1", importance=0.6)
        coordinator, _ = _make_coordinator(tfidf_boost_weight=0.3, db_return_value=[])

        result = coordinator._apply_tfidf_boost([mem], "query with stopwords", weight=0.3)

        assert result is not None
        assert len(result) == 1
        assert result[0].importance == pytest.approx(0.6)

    def test_boost_normalized_per_query(self) -> None:
        """Different queries produce different normalisations.

        With two memories having the same importance but different tfidf sums:
        - mem-high: tfidf_sum=2.0 → normalised=1.0 → boost_factor=1.4 → 0.6*1.4=0.84
        - mem-low:  tfidf_sum=1.0 → normalised=0.5 → boost_factor=1.2 → 0.6*1.2=0.72
        """
        mem_high = _make_memory("m-high", importance=0.6)
        mem_low = _make_memory("m-low", importance=0.6)

        db_rows = [
            {"memory_id": "m-high", "tfidf_sum": 2.0},
            {"memory_id": "m-low", "tfidf_sum": 1.0},
        ]
        coordinator, _ = _make_coordinator(tfidf_boost_weight=0.4, db_return_value=db_rows)

        result = coordinator._apply_tfidf_boost([mem_high, mem_low], "test query", weight=0.4)

        assert len(result) == 2
        # m-high: boost_factor = 1 + 0.4 * 1.0 = 1.4; importance = 0.6 * 1.4 = 0.84
        # m-low:  boost_factor = 1 + 0.4 * 0.5 = 1.2; importance = 0.6 * 1.2 = 0.72
        high_mem = next(m for m in result if m.id == "m-high")
        low_mem = next(m for m in result if m.id == "m-low")
        assert high_mem.importance == pytest.approx(0.84)
        assert low_mem.importance == pytest.approx(0.72)
        assert high_mem.importance > low_mem.importance

    def test_boost_graceful_on_db_error(self) -> None:
        """DB query failure must return the original list unchanged (graceful fallback)."""
        mem = _make_memory("m1", importance=0.6)
        coordinator, _ = _make_coordinator(
            tfidf_boost_weight=0.3,
            db_raise=RuntimeError("kuzu connection closed"),
        )

        result = coordinator._apply_tfidf_boost([mem], "some query", weight=0.3)

        assert result is not None
        # Original list returned; importance not mutated
        assert result[0].importance == pytest.approx(0.6)

    def test_boost_empty_memory_list(self) -> None:
        """Empty input should return empty list without querying the DB."""
        coordinator, mock_adapter = _make_coordinator(tfidf_boost_weight=0.3)

        result = coordinator._apply_tfidf_boost([], "some query", weight=0.3)

        mock_adapter.execute_query.assert_not_called()
        assert result == []

    def test_boost_reorders_by_boosted_score(self) -> None:
        """A memory with lower original importance but strong keyword match can overtake
        one with higher importance but no keyword match (when boost is large enough).
        This test verifies the case where the keyword memory does NOT yet overtake —
        a separate test covers the overtake scenario.

        mem-no-kw: importance=0.8, no keyword match → stays at 0.8
        mem-kw: importance=0.4, strong match → boost_factor=1.5 → 0.4*1.5=0.6
        m-no-kw still leads (0.8 > 0.6).
        """
        mem_strong_semantic = _make_memory("m-no-kw", importance=0.8)
        mem_keyword_match = _make_memory("m-kw", importance=0.4)

        # Only m-kw has a keyword match
        db_rows = [{"memory_id": "m-kw", "tfidf_sum": 3.0}]
        coordinator, _ = _make_coordinator(tfidf_boost_weight=0.5, db_return_value=db_rows)

        result = coordinator._apply_tfidf_boost(
            [mem_strong_semantic, mem_keyword_match], "keyword query", weight=0.5
        )

        assert len(result) == 2
        kw_mem = next(m for m in result if m.id == "m-kw")
        no_kw_mem = next(m for m in result if m.id == "m-no-kw")
        assert kw_mem.importance == pytest.approx(0.6)
        assert no_kw_mem.importance == pytest.approx(0.8)
        # no-kw still leads because 0.8 > 0.6
        assert result[0].id == "m-no-kw"

    def test_boost_reorders_when_keyword_overtakes(self) -> None:
        """Keyword boost sufficient to overtake: mem with lower importance but strong match
        should move to the front."""
        # mem-no-kw: importance=0.7, no keyword match → stays at 0.7
        # mem-kw: importance=0.6, strong match → boost_factor=1.5 → 0.6*1.5=0.9 > 0.7
        mem_no_kw = _make_memory("m-no-kw", importance=0.7)
        mem_kw = _make_memory("m-kw", importance=0.6)

        db_rows = [{"memory_id": "m-kw", "tfidf_sum": 2.0}]
        coordinator, _ = _make_coordinator(tfidf_boost_weight=0.5, db_return_value=db_rows)

        result = coordinator._apply_tfidf_boost([mem_no_kw, mem_kw], "keyword query", weight=0.5)

        assert result[0].id == "m-kw"
        assert result[0].importance == pytest.approx(0.9)

    def test_boost_importance_capped_at_1_0(self) -> None:
        """Boosted importance must never exceed 1.0."""
        mem = _make_memory("m1", importance=0.95)
        db_rows = [{"memory_id": "m1", "tfidf_sum": 10.0}]
        coordinator, _ = _make_coordinator(tfidf_boost_weight=1.0, db_return_value=db_rows)

        result = coordinator._apply_tfidf_boost([mem], "strong keyword match", weight=1.0)

        assert result[0].importance <= 1.0

    def test_boost_empty_query_after_tokenisation_is_noop(self) -> None:
        """Query consisting only of stopwords produces no keywords → no-op."""
        mem = _make_memory("m1", importance=0.6)
        coordinator, mock_adapter = _make_coordinator(tfidf_boost_weight=0.3)

        # All stopwords → tokenize returns []
        result = coordinator._apply_tfidf_boost([mem], "a an the is are", weight=0.3)

        mock_adapter.execute_query.assert_not_called()
        assert result[0].importance == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# Config: env-var override
# ---------------------------------------------------------------------------


class TestTfidfBoostWeightEnvVar:
    """Verify KUZU_MEMORY_TFIDF_BOOST_WEIGHT sets config correctly."""

    def test_env_var_sets_tfidf_boost_weight(self) -> None:
        """KUZU_MEMORY_TFIDF_BOOST_WEIGHT=0.5 must propagate to recall.tfidf_boost_weight."""
        with patch.dict(os.environ, {"KUZU_MEMORY_TFIDF_BOOST_WEIGHT": "0.5"}):
            config = KuzuMemoryConfig.from_dict({})
        assert config.recall.tfidf_boost_weight == pytest.approx(0.5)

    def test_env_var_zero_disables_boost(self) -> None:
        """KUZU_MEMORY_TFIDF_BOOST_WEIGHT=0.0 must set weight to 0.0."""
        with patch.dict(os.environ, {"KUZU_MEMORY_TFIDF_BOOST_WEIGHT": "0.0"}):
            config = KuzuMemoryConfig.from_dict({})
        assert config.recall.tfidf_boost_weight == pytest.approx(0.0)

    def test_malformed_env_var_keeps_default(self) -> None:
        """A non-numeric value must be silently ignored, leaving the default in place."""
        with patch.dict(os.environ, {"KUZU_MEMORY_TFIDF_BOOST_WEIGHT": "not-a-number"}):
            config = KuzuMemoryConfig.from_dict({})
        assert config.recall.tfidf_boost_weight == pytest.approx(0.3)

    def test_default_tfidf_boost_weight(self) -> None:
        """Default tfidf_boost_weight must be 0.3."""
        # Ensure env var is not set
        env = {k: v for k, v in os.environ.items() if k != "KUZU_MEMORY_TFIDF_BOOST_WEIGHT"}
        with patch.dict(os.environ, env, clear=True):
            config = KuzuMemoryConfig.default()
        assert config.recall.tfidf_boost_weight == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Integration: boost wired into attach_memories pipeline
# ---------------------------------------------------------------------------


class TestTfidfBoostIntegration:
    """Verify _apply_tfidf_boost is invoked from the attach_memories pipeline."""

    def test_boost_called_when_weight_positive(self) -> None:
        """With tfidf_boost_weight > 0, _apply_tfidf_boost should be invoked."""
        coordinator, _mock_adapter = _make_coordinator(tfidf_boost_weight=0.3)

        # Make recall strategies return no memories so we stay out of DB paths
        for strategy in coordinator.strategies.values():
            strategy.recall = MagicMock(return_value=[])  # type: ignore[method-assign]

        # Patch _apply_tfidf_boost to verify it is called
        with patch.object(
            coordinator, "_apply_tfidf_boost", wraps=coordinator._apply_tfidf_boost
        ) as mock_boost:
            coordinator.attach_memories("test query", max_memories=5)
            mock_boost.assert_called_once()

    def test_boost_not_called_when_weight_zero(self) -> None:
        """With tfidf_boost_weight=0, _apply_tfidf_boost should NOT be invoked."""
        coordinator, _mock_adapter = _make_coordinator(tfidf_boost_weight=0.0)

        for strategy in coordinator.strategies.values():
            strategy.recall = MagicMock(return_value=[])  # type: ignore[method-assign]

        with patch.object(coordinator, "_apply_tfidf_boost") as mock_boost:
            coordinator.attach_memories("test query", max_memories=5)
            mock_boost.assert_not_called()
