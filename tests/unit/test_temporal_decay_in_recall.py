"""
Tests that TemporalDecayEngine is wired into the recall scoring path.

Verifies:
- apply_temporal_decay=False (default) → pure Jaccard/importance scoring, no decay
- apply_temporal_decay=True           → recent memories rank above old ones
- Hook-style callers that omit the flag keep default=False behaviour
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.recall.coordinator import RecallCoordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(
    content: str,
    days_old: float,
    importance: float = 0.5,
    confidence: float = 1.0,
    memory_type: MemoryType = MemoryType.EPISODIC,
) -> Memory:
    """Create a Memory with a controlled age."""
    return Memory(
        content=content,
        memory_type=memory_type,
        importance=importance,
        confidence=confidence,
        created_at=datetime.now() - timedelta(days=days_old),
    )


def _make_coordinator() -> RecallCoordinator:
    """Return a RecallCoordinator with all storage dependencies stubbed out."""
    mock_adapter = MagicMock()
    mock_adapter.db_path = "/tmp/test_recall.db"
    config = KuzuMemoryConfig()
    # Disable caching so cache bypasses do not interfere.
    config.recall.enable_caching = False
    return RecallCoordinator(db_adapter=mock_adapter, config=config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTemporalDecayWiredIntoRankMemories:
    """Unit tests for RecallCoordinator._rank_memories with temporal decay."""

    def setup_method(self) -> None:
        self.coordinator = _make_coordinator()

    def _rank(
        self, memories: list[Memory], prompt: str, *, apply_temporal_decay: bool
    ) -> list[Memory]:
        return self.coordinator._rank_memories(
            memories, prompt, apply_temporal_decay=apply_temporal_decay
        )

    # ------------------------------------------------------------------
    # Decay disabled (default / hook path)
    # ------------------------------------------------------------------

    def test_no_decay_returns_same_memories(self) -> None:
        """Without temporal decay the list is returned (possibly reordered by relevance)."""
        memories = [
            _make_memory("database setup", days_old=100),
            _make_memory("database setup", days_old=1),
        ]
        result = self._rank(memories, "database", apply_temporal_decay=False)
        assert len(result) == 2

    def test_no_decay_does_not_apply_temporal_decay_engine(self) -> None:
        """With apply_temporal_decay=False, TemporalDecayEngine.calculate_temporal_score is not called."""
        old_mem = _make_memory("python async patterns", days_old=365, importance=0.95)
        new_mem = _make_memory("python async patterns", days_old=0.1, importance=0.5)

        engine = self.coordinator._temporal_decay_engine
        with patch.object(
            engine, "calculate_temporal_score", wraps=engine.calculate_temporal_score
        ) as mock_decay:
            self._rank([old_mem, new_mem], "python async patterns", apply_temporal_decay=False)
            mock_decay.assert_not_called()

    # ------------------------------------------------------------------
    # Decay enabled (MCP tool path)
    # ------------------------------------------------------------------

    def test_decay_boosts_recent_over_very_old(self) -> None:
        """With temporal decay a recent memory ranks above an identical old one."""
        # Same content and importance — only age differs.
        old_mem = _make_memory("recall scoring test", days_old=120, importance=0.5)
        new_mem = _make_memory("recall scoring test", days_old=0.5, importance=0.5)

        result = self._rank([old_mem, new_mem], "recall scoring test", apply_temporal_decay=True)
        assert (
            result[0] is new_mem
        ), "With temporal decay, a memory < 1 day old should rank above one 120 days old"

    def test_decay_score_ranges(self) -> None:
        """Temporal decay factors should stay in (0, 1] for all age buckets."""
        from kuzu_memory.recall.temporal_decay import TemporalDecayEngine

        engine = TemporalDecayEngine()
        age_scenarios = [0, 0.5, 1, 7, 30, 90, 180]
        for days in age_scenarios:
            mem = _make_memory("content", days_old=days, memory_type=MemoryType.EPISODIC)
            score = engine.calculate_temporal_score(mem)
            assert (
                0.0 < score <= 1.0
            ), f"Decay score {score!r} out of range for {days}-day-old memory"

    def test_decay_decreases_with_age(self) -> None:
        """Older memories must receive a strictly lower decay score than newer ones."""
        from kuzu_memory.recall.temporal_decay import TemporalDecayEngine

        engine = TemporalDecayEngine()
        ages = [0, 1, 7, 30, 90]
        scores = []
        for days in ages:
            mem = _make_memory("content", days_old=days, memory_type=MemoryType.EPISODIC)
            scores.append(engine.calculate_temporal_score(mem))

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Expected decay score to decrease with age: age={ages[i]} score={scores[i]:.4f} "
                f">= age={ages[i + 1]} score={scores[i + 1]:.4f}"
            )

    def test_recent_memories_approximate_expected_range(self) -> None:
        """Spot-check that the decay output broadly matches the task specification."""
        from kuzu_memory.recall.temporal_decay import TemporalDecayEngine

        engine = TemporalDecayEngine()

        def _score(days: float) -> float:
            mem = _make_memory("x", days_old=days, memory_type=MemoryType.EPISODIC)
            return engine.calculate_temporal_score(mem)

        # Very recent (< 1 day) should be close to 1.0 (boosted)
        assert _score(0.1) > 0.9, "Sub-day memory should score > 0.9"

        # Very old (90+ days) should be well below 0.5
        assert _score(90) < 0.5, "90-day-old memory should score < 0.5"

    # ------------------------------------------------------------------
    # Default flag value (hook safety)
    # ------------------------------------------------------------------

    def test_default_apply_temporal_decay_is_false(self) -> None:
        """_rank_memories must default to apply_temporal_decay=False for hook safety."""
        import inspect

        sig = inspect.signature(RecallCoordinator._rank_memories)
        default = sig.parameters["apply_temporal_decay"].default
        assert (
            default is False
        ), "apply_temporal_decay must default to False to keep hook recall paths clean"

    def test_attach_memories_default_apply_temporal_decay_is_false(self) -> None:
        """attach_memories must default to apply_temporal_decay=False."""
        import inspect

        sig = inspect.signature(RecallCoordinator.attach_memories)
        default = sig.parameters["apply_temporal_decay"].default
        assert (
            default is False
        ), "attach_memories must default to apply_temporal_decay=False for hook safety"

    # ------------------------------------------------------------------
    # Deduplication still works when decay is enabled
    # ------------------------------------------------------------------

    def test_deduplication_preserved_with_decay(self) -> None:
        """Duplicate memory IDs should be collapsed even when decay is on."""
        mem = _make_memory("dedup test", days_old=2)
        # Two references to same object → same id
        result = self._rank([mem, mem], "dedup test", apply_temporal_decay=True)
        assert len(result) == 1
