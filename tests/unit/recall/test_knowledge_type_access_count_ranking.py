"""
Unit tests for knowledge_type boost and access_count factor in graph recall ranking.

Covers:
- knowledge_type boost values are correct for every KnowledgeType value
- access_count log-scaling at representative counts (0, 1, 10, 100, 1000)
- NOTE type produces no boost (0.0)
- missing/None knowledge_type defaults to 0 boost
- missing access_count defaults to 0 boost
- boosts are additive with existing score components
- RecallCoordinator._calculate_relevance_score integrates both boosts
- MemoryRanker._calculate_knowledge_type_boost / _calculate_access_count_boost
"""

from __future__ import annotations

import math
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.core.models import KnowledgeType, Memory, MemoryType
from kuzu_memory.recall.coordinator import RecallCoordinator
from kuzu_memory.recall.ranking import MemoryRanker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(
    content: str = "test content",
    knowledge_type: KnowledgeType = KnowledgeType.NOTE,
    access_count: int = 0,
    importance: float = 0.5,
    confidence: float = 1.0,
    memory_id: str = "mem-1",
) -> Memory:
    """Create a Memory with controllable knowledge_type and access_count."""
    return Memory(
        id=memory_id,
        content=content,
        memory_type=MemoryType.SEMANTIC,
        knowledge_type=knowledge_type,
        access_count=access_count,
        importance=importance,
        confidence=confidence,
        created_at=datetime.now(),
        valid_to=None,
        user_id=None,
        session_id=None,
    )


def _make_coordinator() -> RecallCoordinator:
    """Return a RecallCoordinator wired to a mock db_adapter."""
    mock_adapter = MagicMock()
    mock_adapter.db_path = "/tmp/test.db"
    config = KuzuMemoryConfig.default()
    config.performance.enable_performance_monitoring = False
    return RecallCoordinator(db_adapter=mock_adapter, config=config)  # type: ignore[arg-type]


def _make_ranker() -> MemoryRanker:
    """Return a MemoryRanker with default configuration."""
    return MemoryRanker()


# ---------------------------------------------------------------------------
# RecallCoordinator._knowledge_type_boost
# ---------------------------------------------------------------------------


class TestCoordinatorKnowledgeTypeBoost:
    """Verify _knowledge_type_boost returns the correct value for every type."""

    coordinator: RecallCoordinator

    @pytest.fixture(autouse=True)
    def _setup_coordinator(self) -> RecallCoordinator:
        self.coordinator = _make_coordinator()
        return self.coordinator

    @pytest.mark.parametrize(
        "kt, expected",
        [
            (KnowledgeType.RULE, 0.25),
            (KnowledgeType.GOTCHA, 0.20),
            (KnowledgeType.ARCHITECTURE, 0.20),
            (KnowledgeType.PATTERN, 0.15),
            (KnowledgeType.CONVENTION, 0.10),
            (KnowledgeType.NOTE, 0.00),
        ],
    )
    def test_boost_values(self, kt: KnowledgeType, expected: float) -> None:
        memory = _make_memory(knowledge_type=kt)
        assert self.coordinator._knowledge_type_boost(memory) == pytest.approx(expected)

    def test_missing_knowledge_type_attribute_returns_zero(self) -> None:
        """Memory-like object without knowledge_type attribute must return 0.0."""
        # Simulate absence by using a mock with no attributes in spec
        # (Pydantic models disallow delattr, so we use MagicMock instead)
        mock_mem = MagicMock(spec=[])  # no attributes in spec
        assert self.coordinator._knowledge_type_boost(mock_mem) == pytest.approx(0.0)

    def test_none_knowledge_type_returns_zero(self) -> None:
        """getattr fallback: if knowledge_type is None-ish, boost must be 0.0."""
        mock_mem = MagicMock()
        mock_mem.knowledge_type = None
        assert self.coordinator._knowledge_type_boost(mock_mem) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# RecallCoordinator._access_count_boost
# ---------------------------------------------------------------------------


class TestCoordinatorAccessCountBoost:
    """Verify _access_count_boost log-scaling behaviour."""

    coordinator: RecallCoordinator

    @pytest.fixture(autouse=True)
    def _setup_coordinator(self) -> RecallCoordinator:
        self.coordinator = _make_coordinator()
        return self.coordinator

    @pytest.mark.parametrize(
        "count, expected",
        [
            (0, 0.0),
            (1, math.log1p(1) * 0.05),
            (10, math.log1p(10) * 0.05),
            (100, min(0.15, math.log1p(100) * 0.05)),
            (1000, 0.15),  # capped at 0.15
        ],
    )
    def test_access_count_values(self, count: int, expected: float) -> None:
        memory = _make_memory(access_count=count)
        assert self.coordinator._access_count_boost(memory) == pytest.approx(expected, abs=1e-9)

    def test_cap_at_0_15(self) -> None:
        """Very large access counts must never exceed 0.15."""
        memory = _make_memory(access_count=1_000_000)
        assert self.coordinator._access_count_boost(memory) == pytest.approx(0.15)

    def test_missing_access_count_attribute_returns_zero(self) -> None:
        """Memory-like object without access_count attribute must return 0.0."""
        mock_mem = MagicMock(spec=[])
        assert self.coordinator._access_count_boost(mock_mem) == pytest.approx(0.0)

    def test_none_access_count_returns_zero(self) -> None:
        """access_count=None must not raise and must return 0.0."""
        mock_mem = MagicMock()
        mock_mem.access_count = None
        assert self.coordinator._access_count_boost(mock_mem) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# RecallCoordinator._calculate_relevance_score — integration
# ---------------------------------------------------------------------------


class TestCoordinatorRelevanceScoreIntegration:
    """Verify that the boosts are additive with existing score components."""

    coordinator: RecallCoordinator

    @pytest.fixture(autouse=True)
    def _setup_coordinator(self) -> RecallCoordinator:
        self.coordinator = _make_coordinator()
        return self.coordinator

    def test_rule_scores_higher_than_note_with_same_content(self) -> None:
        """A RULE memory and a NOTE memory with identical content: RULE must score higher."""
        rule_mem = _make_memory(content="important rule", knowledge_type=KnowledgeType.RULE)
        note_mem = _make_memory(content="important rule", knowledge_type=KnowledgeType.NOTE)

        rule_score = self.coordinator._calculate_relevance_score(rule_mem, "important rule")
        note_score = self.coordinator._calculate_relevance_score(note_mem, "important rule")

        assert rule_score > note_score

    def test_high_access_count_increases_score(self) -> None:
        """A memory accessed 100 times must score higher than the same memory at 0 accesses."""
        low_access = _make_memory(content="same content", access_count=0)
        high_access = _make_memory(content="same content", access_count=100)

        prompt = "same content"
        low_score = self.coordinator._calculate_relevance_score(low_access, prompt)
        high_score = self.coordinator._calculate_relevance_score(high_access, prompt)

        assert high_score > low_score

    def test_score_capped_at_1_0(self) -> None:
        """Score must never exceed 1.0 even with maximum boosts."""
        memory = _make_memory(
            content="test prompt words overlap",
            knowledge_type=KnowledgeType.RULE,
            access_count=1000,
            importance=1.0,
            confidence=1.0,
        )
        score = self.coordinator._calculate_relevance_score(memory, "test prompt words overlap")
        assert score <= 1.0

    def test_note_type_no_knowledge_boost(self) -> None:
        """NOTE knowledge_type must not add any knowledge_type boost."""
        note_mem = _make_memory(
            content="content", knowledge_type=KnowledgeType.NOTE, access_count=0
        )
        note_score = self.coordinator._calculate_relevance_score(note_mem, "content")

        # Manually calculate expected score without knowledge_type boost
        expected_boost = 0.0  # NOTE = 0.0
        assert self.coordinator._knowledge_type_boost(note_mem) == pytest.approx(expected_boost)
        # Score should still be positive from other factors
        assert note_score > 0.0

    def test_boosts_are_additive(self) -> None:
        """Knowledge-type boost and access-count boost are additive.

        We verify additivity by checking each boost independently against a NOTE
        memory with zero access_count (the true zero-boost baseline).  The test
        uses a prompt that does NOT overlap with the memory content so the base
        score stays low and the 1.0 cap is not triggered.
        """
        # Unrelated prompt — minimal overlap so base score stays low
        prompt = "completely unrelated query xyz"

        base_mem = _make_memory(
            content="different words abc",
            knowledge_type=KnowledgeType.NOTE,
            access_count=0,
            importance=0.1,
            confidence=0.1,
        )
        kt_only_mem = _make_memory(
            content="different words abc",
            knowledge_type=KnowledgeType.RULE,
            access_count=0,
            importance=0.1,
            confidence=0.1,
        )
        ac_only_mem = _make_memory(
            content="different words abc",
            knowledge_type=KnowledgeType.NOTE,
            access_count=10,
            importance=0.1,
            confidence=0.1,
        )
        both_mem = _make_memory(
            content="different words abc",
            knowledge_type=KnowledgeType.RULE,
            access_count=10,
            importance=0.1,
            confidence=0.1,
        )

        base_score = self.coordinator._calculate_relevance_score(base_mem, prompt)
        kt_score = self.coordinator._calculate_relevance_score(kt_only_mem, prompt)
        ac_score = self.coordinator._calculate_relevance_score(ac_only_mem, prompt)
        both_score = self.coordinator._calculate_relevance_score(both_mem, prompt)

        kt_boost = self.coordinator._knowledge_type_boost(kt_only_mem)
        ac_boost = self.coordinator._access_count_boost(ac_only_mem)

        # Each boost individually adds its value
        assert kt_score == pytest.approx(base_score + kt_boost, abs=1e-9)
        assert ac_score == pytest.approx(base_score + ac_boost, abs=1e-9)
        # Both boosts together are fully additive
        assert both_score == pytest.approx(base_score + kt_boost + ac_boost, abs=1e-9)

    def test_ranking_order_rule_above_note(self) -> None:
        """In _rank_memories, RULE knowledge_type memories should rank above NOTE ones."""
        coordinator = self.coordinator
        rule_mem = _make_memory(
            content="same words here",
            knowledge_type=KnowledgeType.RULE,
            memory_id="rule",
        )
        note_mem = _make_memory(
            content="same words here",
            knowledge_type=KnowledgeType.NOTE,
            memory_id="note",
        )

        results = coordinator._rank_memories([note_mem, rule_mem], "same words here")
        assert results[0].id == "rule", "RULE memory should rank above NOTE memory"


# ---------------------------------------------------------------------------
# MemoryRanker._calculate_knowledge_type_boost
# ---------------------------------------------------------------------------


class TestRankerKnowledgeTypeBoost:
    """Verify MemoryRanker's knowledge_type boost is consistent with coordinator."""

    ranker: MemoryRanker

    @pytest.fixture(autouse=True)
    def _setup_ranker(self) -> MemoryRanker:
        self.ranker = _make_ranker()
        return self.ranker

    @pytest.mark.parametrize(
        "kt, expected",
        [
            (KnowledgeType.RULE, 0.25),
            (KnowledgeType.GOTCHA, 0.20),
            (KnowledgeType.ARCHITECTURE, 0.20),
            (KnowledgeType.PATTERN, 0.15),
            (KnowledgeType.CONVENTION, 0.10),
            (KnowledgeType.NOTE, 0.00),
        ],
    )
    def test_boost_values(self, kt: KnowledgeType, expected: float) -> None:
        memory = _make_memory(knowledge_type=kt)
        assert self.ranker._calculate_knowledge_type_boost(memory) == pytest.approx(expected)

    def test_missing_attribute_returns_zero(self) -> None:
        mock_mem = MagicMock(spec=[])
        assert self.ranker._calculate_knowledge_type_boost(mock_mem) == pytest.approx(0.0)

    def test_none_knowledge_type_returns_zero(self) -> None:
        mock_mem = MagicMock()
        mock_mem.knowledge_type = None
        assert self.ranker._calculate_knowledge_type_boost(mock_mem) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# MemoryRanker._calculate_access_count_boost
# ---------------------------------------------------------------------------


class TestRankerAccessCountBoost:
    """Verify MemoryRanker's access_count boost is consistent with coordinator."""

    ranker: MemoryRanker

    @pytest.fixture(autouse=True)
    def _setup_ranker(self) -> MemoryRanker:
        self.ranker = _make_ranker()
        return self.ranker

    @pytest.mark.parametrize(
        "count, expected",
        [
            (0, 0.0),
            (1, math.log1p(1) * 0.05),
            (10, math.log1p(10) * 0.05),
            (100, min(0.15, math.log1p(100) * 0.05)),
            (1000, 0.15),
        ],
    )
    def test_access_count_values(self, count: int, expected: float) -> None:
        memory = _make_memory(access_count=count)
        assert self.ranker._calculate_access_count_boost(memory) == pytest.approx(
            expected, abs=1e-9
        )

    def test_cap_at_0_15(self) -> None:
        memory = _make_memory(access_count=999_999)
        assert self.ranker._calculate_access_count_boost(memory) == pytest.approx(0.15)

    def test_missing_attribute_returns_zero(self) -> None:
        mock_mem = MagicMock(spec=[])
        assert self.ranker._calculate_access_count_boost(mock_mem) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# MemoryRanker.rank_memories — integration
# ---------------------------------------------------------------------------


class TestRankerIntegration:
    """Verify boosts are applied in the full rank_memories pipeline."""

    ranker: MemoryRanker

    @pytest.fixture(autouse=True)
    def _setup_ranker(self) -> MemoryRanker:
        self.ranker = _make_ranker()
        return self.ranker

    def test_rule_ranks_above_note(self) -> None:
        rule_mem = _make_memory(
            content="common content",
            knowledge_type=KnowledgeType.RULE,
            memory_id="rule",
        )
        note_mem = _make_memory(
            content="common content",
            knowledge_type=KnowledgeType.NOTE,
            memory_id="note",
        )
        ranked = self.ranker.rank_memories([note_mem, rule_mem], "common content")
        assert ranked[0][0].id == "rule"

    def test_high_access_count_ranks_higher(self) -> None:
        low_mem = _make_memory(
            content="content",
            knowledge_type=KnowledgeType.NOTE,
            access_count=0,
            memory_id="low",
        )
        high_mem = _make_memory(
            content="content",
            knowledge_type=KnowledgeType.NOTE,
            access_count=100,
            memory_id="high",
        )
        ranked = self.ranker.rank_memories([low_mem, high_mem], "content")
        assert ranked[0][0].id == "high"

    def test_final_score_capped_at_1_0(self) -> None:
        memory = _make_memory(
            content="query words here test",
            knowledge_type=KnowledgeType.RULE,
            access_count=1000,
            importance=1.0,
            confidence=1.0,
        )
        ranked = self.ranker.rank_memories([memory], "query words here test")
        assert ranked[0][1] <= 1.0

    def test_get_ranking_explanation_includes_boost_fields(self) -> None:
        """get_ranking_explanation must include knowledge_type_boost and access_count_boost."""
        memory = _make_memory(
            content="test content", knowledge_type=KnowledgeType.GOTCHA, access_count=5
        )
        explanation = self.ranker.get_ranking_explanation(memory, "test content")
        assert "knowledge_type_boost" in explanation
        assert "access_count_boost" in explanation
        assert explanation["knowledge_type_boost"] == pytest.approx(0.20)
        assert explanation["access_count_boost"] == pytest.approx(
            min(0.15, math.log1p(5) * 0.05), abs=1e-9
        )
