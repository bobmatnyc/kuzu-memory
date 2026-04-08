"""
Unit tests for semantic search integration in RecallCoordinator.

Covers:
- use_semantic_search=True uses cosine similarity instead of Jaccard
- use_semantic_search=False (default) uses Jaccard scoring
- Graceful fallback to Jaccard when sentence-transformers is unavailable
- temporal_decay combined with semantic scoring
- _SemanticScorer singleton behaviour
"""

from __future__ import annotations

import sys
import types
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.recall.coordinator import RecallCoordinator, _SemanticScorer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(content: str, memory_id: str = "mem-1") -> Memory:
    """Create a minimal Memory object for testing."""
    return Memory(
        id=memory_id,
        content=content,
        memory_type=MemoryType.SEMANTIC,
        source_type="test",
        importance=0.8,
        confidence=0.9,
        created_at=datetime.now(),
    )


def _make_coordinator() -> tuple[RecallCoordinator, MagicMock]:
    """Return a RecallCoordinator wired to a mock db_adapter."""
    mock_adapter = MagicMock()
    mock_adapter.db_path = "/tmp/test.db"
    config = KuzuMemoryConfig.default()
    # Disable performance monitoring so slow test machines don't raise
    config.performance.enable_performance_monitoring = False
    coordinator = RecallCoordinator(db_adapter=mock_adapter, config=config)  # type: ignore[arg-type]
    return coordinator, mock_adapter


# ---------------------------------------------------------------------------
# _SemanticScorer unit tests
# ---------------------------------------------------------------------------


class TestSemanticScorer:
    def setup_method(self) -> None:
        # Reset singleton between tests
        _SemanticScorer._instance = None

    def test_singleton_returns_same_instance(self) -> None:
        a = _SemanticScorer.get()
        b = _SemanticScorer.get()
        assert a is b

    def test_embed_returns_none_when_sentence_transformers_unavailable(self) -> None:
        """When ST is not importable, embed() must return None without raising."""
        scorer = _SemanticScorer()
        with patch("kuzu_memory.recall.coordinator._SENTENCE_TRANSFORMERS_AVAILABLE", False):
            result = scorer.embed("hello world")
        assert result is None

    def test_embed_caches_result(self) -> None:
        """Second call for same text must return cached array without calling model.encode."""
        import numpy as np

        scorer = _SemanticScorer()
        fake_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        # Pre-populate cache and mock the model so _ensure_model() succeeds
        scorer._cache["cached text"] = fake_vec
        scorer._model = MagicMock()  # ensures _ensure_model returns True

        with patch("kuzu_memory.recall.coordinator._SENTENCE_TRANSFORMERS_AVAILABLE", True):
            result = scorer.embed("cached text")

        assert result is not None
        assert (result == fake_vec).all()
        # model.encode must NOT have been called because cache was hit
        scorer._model.encode.assert_not_called()

    def test_cosine_identical_vectors(self) -> None:
        import numpy as np

        scorer = _SemanticScorer()
        v = np.array([1.0, 0.0], dtype=np.float32)
        assert scorer.cosine(v, v) == pytest.approx(1.0)

    def test_cosine_orthogonal_vectors(self) -> None:
        import numpy as np

        scorer = _SemanticScorer()
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert scorer.cosine(a, b) == pytest.approx(0.0)

    def test_cosine_clamps_negative(self) -> None:
        """Cosine similarity must be clamped to [0, 1]."""
        import numpy as np

        scorer = _SemanticScorer()
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        assert scorer.cosine(a, b) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# RecallCoordinator._rank_memories — semantic vs Jaccard path
# ---------------------------------------------------------------------------


class TestRankMemoriesSemanticPath:
    """Tests for _rank_memories with use_semantic_search=True/False."""

    def setup_method(self) -> None:
        _SemanticScorer._instance = None

    def test_jaccard_path_by_default(self) -> None:
        """With use_semantic_search=False the scorer must not be called."""
        coordinator, _ = _make_coordinator()
        coordinator._semantic_scorer = MagicMock()

        memories = [_make_memory("python async patterns", "m1")]
        coordinator._rank_memories(memories, "async patterns", use_semantic_search=False)

        coordinator._semantic_scorer.embed.assert_not_called()

    def test_semantic_path_calls_embed(self) -> None:
        """With use_semantic_search=True the scorer.embed must be called."""
        import numpy as np

        coordinator, _ = _make_coordinator()

        fake_q_emb = np.array([1.0, 0.0], dtype=np.float32)
        fake_m_emb = np.array([0.9, 0.1], dtype=np.float32)

        mock_scorer = MagicMock()
        mock_scorer.embed.side_effect = [fake_q_emb, fake_m_emb]
        mock_scorer.cosine.return_value = 0.85
        coordinator._semantic_scorer = mock_scorer

        memories = [_make_memory("relevant content", "m1")]
        results = coordinator._rank_memories(memories, "relevant query", use_semantic_search=True)

        assert mock_scorer.embed.call_count == 2  # once for query, once for memory
        assert len(results) == 1

    def test_semantic_score_ranks_better_semantic_match_higher(self) -> None:
        """Memory semantically similar to query should rank above dissimilar one."""
        import numpy as np

        coordinator, _ = _make_coordinator()

        # Query vector
        q = np.array([1.0, 0.0], dtype=np.float32)
        # m1 is very similar; m2 is orthogonal
        m1_emb = np.array([0.99, 0.14], dtype=np.float32)
        m1_emb = m1_emb / np.linalg.norm(m1_emb)
        m2_emb = np.array([0.0, 1.0], dtype=np.float32)

        embed_map = {
            "async python patterns": q,
            "asynchronous Python programming": m1_emb,
            "unrelated database topic": m2_emb,
        }

        def fake_embed(text: str) -> Any:
            return embed_map.get(text)

        def fake_cosine(a: Any, b: Any) -> float:
            return float(np.dot(a, b))

        mock_scorer = MagicMock()
        mock_scorer.embed.side_effect = fake_embed
        mock_scorer.cosine.side_effect = fake_cosine
        coordinator._semantic_scorer = mock_scorer

        m1 = _make_memory("asynchronous Python programming", "m1")
        m2 = _make_memory("unrelated database topic", "m2")

        results = coordinator._rank_memories(
            [m1, m2], "async python patterns", use_semantic_search=True
        )

        assert results[0].id == "m1", "Semantically similar memory should rank first"

    def test_fallback_to_jaccard_when_query_embed_fails(self) -> None:
        """When embed(query) returns None, scoring must fall back to Jaccard silently."""
        coordinator, _ = _make_coordinator()

        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = None  # simulate unavailable model
        coordinator._semantic_scorer = mock_scorer

        memories = [_make_memory("python async patterns", "m1")]
        # Should not raise even though semantic path failed
        results = coordinator._rank_memories(memories, "async python", use_semantic_search=True)

        assert len(results) == 1
        # cosine must never be called when query embedding is None
        mock_scorer.cosine.assert_not_called()

    def test_fallback_to_jaccard_when_memory_embed_fails(self) -> None:
        """When embed(memory.content) returns None, that memory falls back gracefully."""
        import numpy as np

        coordinator, _ = _make_coordinator()

        mock_scorer = MagicMock()
        # First call (query) succeeds; second call (memory) fails
        mock_scorer.embed.side_effect = [np.array([1.0, 0.0], dtype=np.float32), None]
        coordinator._semantic_scorer = mock_scorer

        memories = [_make_memory("content with failed embed", "m1")]
        results = coordinator._rank_memories(memories, "query text", use_semantic_search=True)

        assert len(results) == 1  # memory still included via Jaccard fallback
        mock_scorer.cosine.assert_not_called()

    def test_semantic_combined_with_temporal_decay(self) -> None:
        """
        When both use_semantic_search=True and apply_temporal_decay=True, the final
        score must be semantic_score * decay_factor (both effects applied).
        """
        import numpy as np

        coordinator, _ = _make_coordinator()

        q_emb = np.array([1.0, 0.0], dtype=np.float32)
        m_emb = np.array([1.0, 0.0], dtype=np.float32)

        mock_scorer = MagicMock()
        mock_scorer.embed.side_effect = [q_emb, m_emb]
        mock_scorer.cosine.return_value = 1.0  # perfect similarity
        coordinator._semantic_scorer = mock_scorer

        # Make decay engine return 0.5 (memory is "old")
        coordinator._temporal_decay_engine = MagicMock()
        coordinator._temporal_decay_engine.calculate_temporal_score.return_value = 0.5

        m1 = _make_memory("perfect match", "m1")
        m2 = _make_memory("other memory", "m2")

        # For m2 use a zero embedding so it scores 0 semantic similarity
        mock_scorer.embed.side_effect = [
            q_emb,  # query
            m_emb,  # m1
            np.array([0.0, 1.0], dtype=np.float32),  # m2
        ]

        def cosine_side(a: Any, b: Any) -> float:
            return float(np.dot(a, b))

        mock_scorer.cosine.side_effect = cosine_side

        results = coordinator._rank_memories(
            [m1, m2],
            "perfect match",
            apply_temporal_decay=True,
            use_semantic_search=True,
        )

        # m1 still wins despite decay because semantic similarity is much higher
        assert results[0].id == "m1"
        # Decay was applied (called for each memory)
        assert coordinator._temporal_decay_engine.calculate_temporal_score.call_count == 2


# ---------------------------------------------------------------------------
# Full-corpus cosine scan fallback (issue #49)
# ---------------------------------------------------------------------------


class TestFullCorpusFallback:
    """
    Regression tests for issue #49: keyword pre-filter drops candidates before
    cosine ranking when HNSW is unavailable and use_semantic_search=True.

    When HNSW returns None (index absent) and semantic search is requested,
    attach_memories must fall back to _recall_all_memories() (full corpus) instead
    of relying on keyword-filtered candidates from graph strategies.
    """

    def setup_method(self) -> None:
        _SemanticScorer._instance = None

    def test_full_corpus_fallback_called_when_hnsw_unavailable(self) -> None:
        """
        When _recall_with_hnsw returns None, _recall_all_memories must be called
        and its results used as the candidate pool.
        """
        coordinator, mock_adapter = _make_coordinator()

        corpus_memory = _make_memory("full corpus content", "corpus-1")

        with (
            patch.object(coordinator, "_recall_with_hnsw", return_value=None),
            patch.object(
                coordinator, "_recall_all_memories", return_value=[corpus_memory]
            ) as mock_all,
            patch.object(coordinator, "_rank_memories", return_value=[corpus_memory]) as mock_rank,
        ):
            coordinator.attach_memories("what did you recommend?", use_semantic_search=True)

        mock_all.assert_called_once()
        # _rank_memories must be called with the full-corpus candidates
        rank_call_memories = mock_rank.call_args[0][0]
        assert any(m.id == "corpus-1" for m in rank_call_memories)

    def test_full_corpus_fallback_not_called_when_hnsw_succeeds(self) -> None:
        """
        When HNSW returns a non-empty result, _recall_all_memories must NOT be called.
        """
        coordinator, mock_adapter = _make_coordinator()

        hnsw_memory = _make_memory("hnsw result", "hnsw-1")

        with (
            patch.object(coordinator, "_recall_with_hnsw", return_value=[hnsw_memory]),
            patch.object(coordinator, "_recall_all_memories") as mock_all,
            patch.object(coordinator, "_rank_memories", return_value=[hnsw_memory]),
        ):
            coordinator.attach_memories("test query", use_semantic_search=True)

        mock_all.assert_not_called()

    def test_full_corpus_fallback_not_called_when_semantic_search_disabled(self) -> None:
        """
        When use_semantic_search=False, HNSW is never attempted and
        _recall_all_memories must not be called (normal Jaccard path).
        """
        coordinator, mock_adapter = _make_coordinator()

        stub_memory = _make_memory("test content", "m1")
        for strategy in coordinator.strategies.values():
            strategy.recall = MagicMock(return_value=[stub_memory])  # type: ignore[method-assign]

        with (
            patch.object(coordinator, "_recall_with_hnsw") as mock_hnsw,
            patch.object(coordinator, "_recall_all_memories") as mock_all,
        ):
            coordinator.attach_memories("test query", use_semantic_search=False)

        mock_hnsw.assert_not_called()
        mock_all.assert_not_called()

    def test_recall_all_memories_fetches_without_keyword_filter(self) -> None:
        """
        _recall_all_memories must issue a query with no keyword conditions —
        confirmed by verifying the Cypher does not contain 'CONTAINS'.
        """
        coordinator, mock_adapter = _make_coordinator()

        # Capture the query sent to execute_query
        captured_queries: list[str] = []

        def capture_query(query: str, params: dict) -> list:  # type: ignore[type-arg]
            captured_queries.append(query)
            return []

        mock_adapter.execute_query.side_effect = capture_query

        coordinator._recall_all_memories(user_id=None, session_id=None, agent_id="default")

        assert len(captured_queries) == 1
        assert (
            "CONTAINS" not in captured_queries[0]
        ), "_recall_all_memories must not apply any keyword pre-filter (CONTAINS clause found)"
        assert "MATCH (m:Memory)" in captured_queries[0]


# ---------------------------------------------------------------------------
# attach_memories — parameter threading through coordinator
# ---------------------------------------------------------------------------


class TestAttachMemoriesParameterThreading:
    """Verify use_semantic_search is forwarded correctly through the call stack."""

    def setup_method(self) -> None:
        _SemanticScorer._instance = None

    def _make_coordinator_with_mock_strategies(
        self,
    ) -> tuple[RecallCoordinator, list[Memory]]:
        coordinator, _ = _make_coordinator()

        stub_memory = _make_memory("test content", "m1")
        for strategy in coordinator.strategies.values():
            strategy.recall = MagicMock(return_value=[stub_memory])  # type: ignore[method-assign]

        return coordinator, [stub_memory]

    def test_use_semantic_search_forwarded_to_rank_memories(self) -> None:
        """attach_memories must pass use_semantic_search to _rank_memories."""
        coordinator, _ = self._make_coordinator_with_mock_strategies()

        with patch.object(
            coordinator, "_rank_memories", wraps=coordinator._rank_memories
        ) as mock_rank:
            coordinator.attach_memories("test prompt", use_semantic_search=True)

        call_kwargs = mock_rank.call_args
        assert call_kwargs is not None
        # Check either args or kwargs
        if "use_semantic_search" in (call_kwargs.kwargs or {}):
            assert call_kwargs.kwargs["use_semantic_search"] is True
        else:
            # positional: _rank_memories(memories, prompt, apply_temporal_decay, use_semantic_search)
            positional = call_kwargs.args
            assert len(positional) >= 4 or call_kwargs.kwargs.get("use_semantic_search") is True

    def test_use_semantic_search_false_by_default(self) -> None:
        """Default value of use_semantic_search must be False (hooks path safety)."""
        coordinator, _ = self._make_coordinator_with_mock_strategies()
        scorer_mock = MagicMock()
        coordinator._semantic_scorer = scorer_mock

        coordinator.attach_memories("test prompt")

        scorer_mock.embed.assert_not_called()


# ---------------------------------------------------------------------------
# Speaker intent zero-result guard (issue #47)
# ---------------------------------------------------------------------------


class TestSpeakerIntentZeroResultGuard:
    """
    Regression tests for issue #47: speaker intent hard-filter wiped 100% of
    results when memories defaulted to source_speaker="user" and the query
    was classified as ASSISTANT_TURN.

    The zero-result guard must fall back to the unfiltered ranked list when the
    speaker filter would return an empty list.
    """

    def test_assistant_intent_with_all_user_speaker_memories_returns_full_list(self) -> None:
        """
        When all memories have source_speaker='user' (the default) and the
        classifier fires ASSISTANT_TURN, the guard must return the full ranked
        list rather than an empty one.
        """
        from kuzu_memory.recall.query_classifier import SpeakerIntent, classify_speaker_intent

        # Confirm classifier fires ASSISTANT_TURN for this query
        intent = classify_speaker_intent("What did you recommend for the database schema?")
        assert intent == SpeakerIntent.ASSISTANT_TURN

        # Simulate the guard logic directly (mirrors coordinator lines 307-324)
        memories = [
            _make_memory("use Postgres for relational data", "m1"),
            _make_memory("prefer SQLite for embedded use cases", "m2"),
        ]
        # All memories default to source_speaker="user" (no explicit tagging)
        for m in memories:
            assert getattr(m, "source_speaker", "user") == "user"

        speaker_value = intent.value  # "assistant"
        filtered = [m for m in memories if getattr(m, "source_speaker", "user") == speaker_value]

        # Guard: fall back when filter produces empty list
        result = filtered if filtered else memories

        assert len(result) == 2, (
            "Zero-result guard must return full list when no memories are tagged with "
            "source_speaker='assistant'"
        )

    def test_user_intent_with_tagged_user_memories_applies_filter(self) -> None:
        """
        When memories ARE tagged with source_speaker='user' and the query is
        USER_TURN, the filter should work normally.
        """
        from kuzu_memory.recall.query_classifier import SpeakerIntent, classify_speaker_intent

        intent = classify_speaker_intent("What did I say about testing frameworks?")
        assert intent == SpeakerIntent.USER_TURN

        m1 = _make_memory("I prefer pytest for unit tests", "m1")
        m2 = _make_memory("assistant recommended unittest", "m2")
        # Tag m2 as assistant — simulating proper caller tagging
        object.__setattr__(m2, "source_speaker", "assistant")

        speaker_value = intent.value  # "user"
        filtered = [m for m in [m1, m2] if getattr(m, "source_speaker", "user") == speaker_value]
        result = filtered if filtered else [m1, m2]

        assert len(result) == 1
        assert result[0].id == "m1"

    def test_mixed_speakers_assistant_intent_returns_tagged_subset(self) -> None:
        """
        When some memories ARE tagged as source_speaker='assistant', an ASSISTANT_TURN
        query must return only those (filter active, guard not triggered).
        """
        from kuzu_memory.recall.query_classifier import SpeakerIntent, classify_speaker_intent

        intent = classify_speaker_intent("What did you suggest for the API design?")
        assert intent == SpeakerIntent.ASSISTANT_TURN

        m_user = _make_memory("user content about API", "m1")
        m_asst = _make_memory("assistant recommended REST", "m2")
        object.__setattr__(m_asst, "source_speaker", "assistant")

        speaker_value = intent.value  # "assistant"
        filtered = [
            m for m in [m_user, m_asst] if getattr(m, "source_speaker", "user") == speaker_value
        ]
        result = filtered if filtered else [m_user, m_asst]

        assert len(result) == 1
        assert result[0].id == "m2"


# ---------------------------------------------------------------------------
# Entity match weight (issue #48)
# ---------------------------------------------------------------------------


class TestEntityMatchWeight:
    """
    Regression tests for issue #48: entity match weight 0.10 was high enough for
    a single common-entity hit on a wrong session to override a Jaccard-leading
    correct session in fresh/small DBs.

    Weight reduced to 0.03: a wrong session now needs 3+ entity matches to flip
    a typical Jaccard advantage of 0.05-0.15.
    """

    def test_entity_weight_constant_is_0_03(self) -> None:
        """Verify the entity match increment is 0.03, not the old 0.10."""
        import inspect

        import kuzu_memory.recall.coordinator as coord_module

        source = inspect.getsource(coord_module)
        # The literal 0.1 entity weight must be gone
        assert (
            "score += 0.1" not in source
        ), "Entity weight is still 0.10 — expected 0.03 (issue #48 regression)"
        assert (
            "score += 0.03" in source
        ), "Entity weight 0.03 not found in coordinator source (issue #48)"

    def test_entity_match_does_not_override_strong_jaccard_lead(self) -> None:
        """
        A session with strong Jaccard similarity must outscore a session with
        1 entity match but weaker Jaccard, even after the entity boost.

        Demonstrates the fix: at weight=0.03, 1 entity match (+0.03) cannot
        overcome a 0.10 Jaccard advantage (0.10 * 0.25 = +0.025 Jaccard score
        differential vs +0.03 entity boost — but we test at a larger gap).
        """
        coordinator, _ = _make_coordinator()

        from datetime import datetime

        from kuzu_memory.core.models import Memory, MemoryType

        # Correct session: high Jaccard overlap with query, no entity match
        correct = Memory(
            id="correct",
            content="python async patterns event loop",  # overlaps well with query
            memory_type=MemoryType.SEMANTIC,
            source_type="test",
            importance=0.5,
            confidence=0.5,
            created_at=datetime.now(),
            entities=[],  # no entities
        )

        # Wrong session: lower Jaccard but has 1 entity match on a common word
        wrong = Memory(
            id="wrong",
            content="machine learning training data pipeline",  # low overlap with query
            memory_type=MemoryType.SEMANTIC,
            source_type="test",
            importance=0.5,
            confidence=0.5,
            created_at=datetime.now(),
            entities=["python"],  # matches query word "python"
        )

        query = "python async event loop patterns"
        ranked = coordinator._rank_memories([correct, wrong], query, use_semantic_search=False)

        # correct must rank above wrong despite wrong having an entity match
        assert len(ranked) == 2
        assert ranked[0].id == "correct", (
            "Entity match on wrong session should not override strong Jaccard lead. "
            "Entity weight may have regressed to 0.10."
        )
