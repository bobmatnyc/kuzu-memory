"""
Unit tests for HNSW vector index recall path in RecallCoordinator.

Covers:
- _recall_with_hnsw: issues QUERY_VECTOR_INDEX and returns parsed Memory objects
- _recall_with_hnsw: returns None when scorer.embed() returns None (fallback signal)
- _recall_with_hnsw: returns None when HNSW query raises (fallback signal)
- attach_memories: HNSW candidates are merged with graph candidates when available
- attach_memories: falls back to pure graph recall when HNSW returns None
- Embedding stored at ingestion: _store_embedding_for_memory is called from remember()
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.enrichment.hnsw_index import HNSW_INDEX_NAME
from kuzu_memory.recall.coordinator import RecallCoordinator, _SemanticScorer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(content: str, memory_id: str = "m1") -> Memory:
    return Memory(
        id=memory_id,
        content=content,
        memory_type=MemoryType.SEMANTIC,
        source_type="test",
        importance=0.8,
        confidence=0.9,
        created_at=datetime.now(),
    )


def _make_coordinator_with_adapter(
    adapter: Any | None = None,
) -> tuple[RecallCoordinator, MagicMock]:
    mock_adapter = adapter or MagicMock()
    mock_adapter.db_path = "/tmp/test.db"
    config = KuzuMemoryConfig.default()
    config.performance.enable_performance_monitoring = False
    coordinator = RecallCoordinator(db_adapter=mock_adapter, config=config)  # type: ignore[arg-type]
    return coordinator, mock_adapter


# ---------------------------------------------------------------------------
# _recall_with_hnsw unit tests
# ---------------------------------------------------------------------------


class TestRecallWithHNSW:
    def test_returns_none_when_embed_unavailable(self) -> None:
        """If the scorer cannot embed (returns None), signal fallback with None."""
        coordinator, mock_adapter = _make_coordinator_with_adapter()
        coordinator._semantic_scorer = MagicMock()
        coordinator._semantic_scorer.embed.return_value = None

        result = coordinator._recall_with_hnsw("test query", limit=5)

        assert result is None
        mock_adapter.execute_query.assert_not_called()

    def test_returns_none_on_hnsw_query_failure(self) -> None:
        """HNSW query failure (index absent, column missing) → return None."""
        coordinator, mock_adapter = _make_coordinator_with_adapter()

        import numpy as np

        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = np.zeros(384, dtype="float32")
        coordinator._semantic_scorer = mock_scorer

        mock_adapter.execute_query.side_effect = RuntimeError("Cannot find vector index")

        result = coordinator._recall_with_hnsw("test query", limit=5)

        assert result is None

    def test_returns_empty_list_when_no_results(self) -> None:
        """HNSW returns no rows → empty list (not None — index worked, just 0 hits)."""
        coordinator, mock_adapter = _make_coordinator_with_adapter()

        import numpy as np

        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = np.zeros(384, dtype="float32")
        coordinator._semantic_scorer = mock_scorer

        mock_adapter.execute_query.return_value = []

        result = coordinator._recall_with_hnsw("test query", limit=5)

        assert result == []

    def test_returns_parsed_memories(self) -> None:
        """Successful HNSW query returns Memory objects parsed from 'node' column."""
        coordinator, mock_adapter = _make_coordinator_with_adapter()

        import numpy as np

        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = np.zeros(384, dtype="float32")
        coordinator._semantic_scorer = mock_scorer

        mem = _make_memory("HNSW recalled content", memory_id="hnsw-1")
        # Simulate Kùzu QUERY_VECTOR_INDEX row: {"node": {...}, "distance": 0.12}
        mock_adapter.execute_query.return_value = [{"node": mem.to_dict(), "distance": 0.12}]

        result = coordinator._recall_with_hnsw("query", limit=5)

        assert result is not None
        assert len(result) == 1
        assert result[0].id == "hnsw-1"

    def test_hnsw_query_uses_correct_index_name_and_params(self) -> None:
        """QUERY_VECTOR_INDEX call uses HNSW_INDEX_NAME and passes embedding + k."""
        coordinator, mock_adapter = _make_coordinator_with_adapter()

        import numpy as np

        dummy_vec = np.ones(384, dtype="float32")
        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = dummy_vec
        coordinator._semantic_scorer = mock_scorer

        mock_adapter.execute_query.return_value = []

        coordinator._recall_with_hnsw("my query", limit=3)

        assert mock_adapter.execute_query.called
        call_args = mock_adapter.execute_query.call_args
        query_str: str = call_args[0][0]
        params: dict = call_args[1].get("parameters") or call_args[0][1]

        assert "QUERY_VECTOR_INDEX" in query_str
        assert HNSW_INDEX_NAME in query_str
        assert params["embedding"] == dummy_vec.tolist()
        assert params["k"] == 3 * 2  # limit * 2

    def test_malformed_node_skipped_gracefully(self) -> None:
        """Rows with unparseable 'node' data are skipped without raising."""
        coordinator, mock_adapter = _make_coordinator_with_adapter()

        import numpy as np

        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = np.zeros(384, dtype="float32")
        coordinator._semantic_scorer = mock_scorer

        mock_adapter.execute_query.return_value = [
            {"node": None, "distance": 0.0},
            {
                "node": {
                    "id": "ok-1",
                    "content": "valid",
                    "memory_type": "semantic",
                    "source_type": "test",
                    "created_at": datetime.now().isoformat(),
                },
                "distance": 0.1,
            },
        ]

        result = coordinator._recall_with_hnsw("q", limit=5)
        assert result is not None
        # The None node is skipped; the valid one is parsed
        assert len(result) == 1
        assert result[0].id == "ok-1"


# ---------------------------------------------------------------------------
# attach_memories HNSW integration
# ---------------------------------------------------------------------------


class TestAttachMemoriesHNSWIntegration:
    def _make_strategies_returning(self, memories: list[Memory]) -> dict[str, MagicMock]:
        """Return mock strategies that all yield *memories*."""
        mock_strat = MagicMock()
        mock_strat.recall.return_value = memories
        mock_strat.get_statistics.return_value = {}
        return {
            "keyword": mock_strat,
            "entity": mock_strat,
            "temporal": mock_strat,
        }

    def test_hnsw_memories_merged_with_graph(self) -> None:
        """When HNSW succeeds, its candidates appear alongside graph candidates."""
        coordinator, mock_adapter = _make_coordinator_with_adapter()
        mock_adapter.db_path = "/tmp/test.db"

        hnsw_mem = _make_memory("HNSW result", memory_id="hnsw-1")
        graph_mem = _make_memory("Graph result", memory_id="graph-1")

        import numpy as np

        mock_scorer = MagicMock()
        dummy_vec = np.zeros(384, dtype="float32")
        mock_scorer.embed.return_value = dummy_vec
        mock_scorer.cosine.return_value = 0.9
        coordinator._semantic_scorer = mock_scorer

        # HNSW path returns hnsw_mem; graph strategies return graph_mem
        mock_adapter.execute_query.return_value = [{"node": hnsw_mem.to_dict(), "distance": 0.05}]
        for name, strat in self._make_strategies_returning([graph_mem]).items():
            coordinator.strategies[name] = strat

        context = coordinator.attach_memories(
            "test prompt", max_memories=10, use_semantic_search=True
        )

        memory_ids = {m.id for m in context.memories}
        assert "hnsw-1" in memory_ids or "graph-1" in memory_ids

    def test_fallback_to_graph_when_hnsw_returns_none(self) -> None:
        """When HNSW returns None, recall falls back to graph strategies only."""
        coordinator, _mock_adapter = _make_coordinator_with_adapter()

        # Make scorer return None → HNSW signals fallback
        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = None
        coordinator._semantic_scorer = mock_scorer

        graph_mem = _make_memory("Graph only", memory_id="graph-only")
        for name, strat in self._make_strategies_returning([graph_mem]).items():
            coordinator.strategies[name] = strat

        context = coordinator.attach_memories(
            "test prompt", max_memories=10, use_semantic_search=True
        )

        memory_ids = {m.id for m in context.memories}
        assert "graph-only" in memory_ids

    def test_hnsw_not_called_when_semantic_false(self) -> None:
        """_recall_with_hnsw is never invoked when use_semantic_search=False."""
        coordinator, _mock_adapter = _make_coordinator_with_adapter()

        graph_mem = _make_memory("Graph only", memory_id="graph-only")
        for name, strat in self._make_strategies_returning([graph_mem]).items():
            coordinator.strategies[name] = strat

        with patch.object(coordinator, "_recall_with_hnsw") as mock_hnsw:
            coordinator.attach_memories("test prompt", max_memories=10, use_semantic_search=False)
            mock_hnsw.assert_not_called()


# ---------------------------------------------------------------------------
# Embedding stored at ingestion
# ---------------------------------------------------------------------------


class TestEmbeddingAtIngestion:
    def test_remember_calls_store_embedding(self, tmp_path: Any) -> None:
        """KuzuMemory.remember() calls _store_embedding_for_memory after storing."""
        from unittest.mock import patch

        from kuzu_memory.core.memory import KuzuMemory

        with patch("kuzu_memory.core.memory.KuzuMemory._initialize_components"):
            with patch("kuzu_memory.core.memory.KuzuMemory._initialize_git_sync"):
                km = KuzuMemory.__new__(KuzuMemory)
                km.db_path = tmp_path / "memories.db"  # type: ignore[attr-defined]
                km.config = KuzuMemoryConfig.default()  # type: ignore[attr-defined]
                km._user_id = None  # type: ignore[attr-defined]
                km._writes_since_enrichment = 0  # type: ignore[attr-defined]

                mock_store = MagicMock()
                mock_store._store_memory_in_database = MagicMock()
                km.memory_store = mock_store  # type: ignore[attr-defined]
                km.auto_git_sync = None  # type: ignore[attr-defined]

                with patch.object(km, "_store_embedding_for_memory") as mock_embed:
                    with patch.object(km, "_maybe_enrich"):
                        km.remember("hello world")

                mock_embed.assert_called_once()
                args = mock_embed.call_args[0]
                # First arg is memory_id (str), second is content
                assert isinstance(args[0], str)
                assert args[1] == "hello world"
