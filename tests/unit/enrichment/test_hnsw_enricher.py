"""
Unit tests for HNSWIndexEnricher.

Covers:
- HNSW index creation is attempted via CALL CREATE_VECTOR_INDEX(...)
- "already exists" index error is silently swallowed (idempotent)
- Any error message containing "index" is swallowed (broad compatibility)
- Unexpected errors during index creation are re-raised
- EnrichmentResult.error is set on unexpected failures
- _store_embedding via KuzuMemory._write_embedding runs the correct SET query

NOTE: The embedding column (FLOAT[384]) is now declared directly in the
CREATE NODE TABLE Memory DDL (schema.py) and is present from write #1.
The enricher no longer needs to ALTER TABLE; tests for _ensure_embedding_column
have been removed accordingly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.enrichment.hnsw_index import EMBEDDING_DIM, HNSW_INDEX_NAME, HNSWIndexEnricher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> KuzuMemoryConfig:
    return KuzuMemoryConfig.default()


def _make_adapter(query_side_effects: dict[str, Any] | None = None) -> MagicMock:
    """Return a mock KuzuAdapter whose execute_query raises or returns canned data.

    Keys in *query_side_effects* are matched as substrings of the query string.
    Values may be:
    - An exception instance  → raised when that query is executed.
    - A list                 → returned as the query result.
    - None                   → returns [].
    """
    adapter = MagicMock()
    adapter.config = _make_config()

    effects = query_side_effects or {}

    def _execute(query: str, parameters: dict | None = None) -> list[dict]:
        for key, val in effects.items():
            if key in query:
                if isinstance(val, Exception):
                    raise val
                return list(val) if val is not None else []
        return []

    adapter.execute_query.side_effect = _execute
    return adapter


# ---------------------------------------------------------------------------
# HNSWIndexEnricher._ensure_hnsw_index
# ---------------------------------------------------------------------------


class TestEnsureHNSWIndex:
    def test_create_index_called(self) -> None:
        """CREATE_VECTOR_INDEX is attempted via CALL statement."""
        adapter = _make_adapter()
        enricher = HNSWIndexEnricher()
        enricher._ensure_hnsw_index(adapter)

        calls_made = [str(c.args[0]) for c in adapter.execute_query.call_args_list]
        assert any("CREATE_VECTOR_INDEX" in q for q in calls_made)
        assert any(HNSW_INDEX_NAME in q for q in calls_made)

    def test_already_exists_error_swallowed(self) -> None:
        """An 'already exists' error from Kùzu is silently ignored."""
        already_exists = RuntimeError("index already exists")
        adapter = _make_adapter({"CREATE_VECTOR_INDEX": already_exists})
        enricher = HNSWIndexEnricher()
        # Must not raise
        enricher._ensure_hnsw_index(adapter)

    def test_index_error_swallowed(self) -> None:
        """Any error mentioning 'index' (e.g. 'index not supported') is swallowed."""
        index_err = RuntimeError("vector index creation failed: index type mismatch")
        adapter = _make_adapter({"CREATE_VECTOR_INDEX": index_err})
        enricher = HNSWIndexEnricher()
        enricher._ensure_hnsw_index(adapter)  # should not raise

    def test_unexpected_error_propagates(self) -> None:
        """Unexpected errors (not index-related) ARE re-raised for the caller to log."""
        unexpected = RuntimeError("database locked")
        adapter = _make_adapter({"CREATE_VECTOR_INDEX": unexpected})
        enricher = HNSWIndexEnricher()
        with pytest.raises(RuntimeError, match="database locked"):
            enricher._ensure_hnsw_index(adapter)

    def test_no_alter_table_issued(self) -> None:
        """The enricher never issues ALTER TABLE — the column is in the schema DDL."""
        adapter = _make_adapter()
        enricher = HNSWIndexEnricher()
        enricher.enrich(adapter, _make_config())

        calls_made = [str(c.args[0]) for c in adapter.execute_query.call_args_list]
        assert not any("ALTER" in q for q in calls_made), (
            "HNSWIndexEnricher must not issue ALTER TABLE — "
            "embedding column is declared in schema.py CREATE TABLE"
        )


# ---------------------------------------------------------------------------
# HNSWIndexEnricher.enrich (integration of helper)
# ---------------------------------------------------------------------------


class TestHNSWIndexEnricherEnrich:
    def test_enrich_success(self) -> None:
        """Happy path: enrich() runs _ensure_hnsw_index and returns success result."""
        adapter = _make_adapter()
        enricher = HNSWIndexEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success
        assert result.error is None
        assert result.name == "hnsw_index"
        assert result.duration_ms >= 0.0

    def test_enrich_sets_error_on_failure(self) -> None:
        """If an unexpected exception bubbles up, result.error is set (not raised)."""
        adapter = MagicMock()
        adapter.config = _make_config()
        # Make execute_query always raise an unexpected error
        adapter.execute_query.side_effect = RuntimeError("total failure")

        enricher = HNSWIndexEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert not result.success
        assert result.error is not None

    def test_enrich_success_when_index_already_exists(self) -> None:
        """enrich() returns success even when the index already exists."""
        already_exists = RuntimeError("index already exists")
        adapter = _make_adapter({"CREATE_VECTOR_INDEX": already_exists})
        enricher = HNSWIndexEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success
        assert result.error is None


# ---------------------------------------------------------------------------
# KuzuMemory._write_embedding
# ---------------------------------------------------------------------------


class TestWriteEmbedding:
    def test_write_embedding_calls_set_query(self) -> None:
        """_write_embedding issues a SET m.embedding = $embedding query."""
        from kuzu_memory.core.memory import KuzuMemory

        km = KuzuMemory.__new__(KuzuMemory)
        mock_adapter = MagicMock()
        km.db_adapter = mock_adapter  # type: ignore[attr-defined]

        embedding = [0.1] * EMBEDDING_DIM
        km._write_embedding("mem-123", embedding)

        mock_adapter.execute_query.assert_called_once()
        call_args = mock_adapter.execute_query.call_args
        # query is the first positional arg; params dict is the second positional arg
        query: str = call_args[0][0]
        params: dict = call_args[0][1]

        assert "SET" in query
        assert "m.embedding" in query
        assert params["memory_id"] == "mem-123"
        assert params["embedding"] == embedding

    def test_store_embedding_for_memory_calls_write(self) -> None:
        """_store_embedding_for_memory embeds content and calls _write_embedding."""
        from kuzu_memory.core.memory import KuzuMemory

        km = KuzuMemory.__new__(KuzuMemory)
        mock_adapter = MagicMock()
        km.db_adapter = mock_adapter  # type: ignore[attr-defined]

        dummy_vec = [0.5] * EMBEDDING_DIM

        # Patch the scorer so we don't need sentence-transformers installed in CI
        import numpy as np

        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = np.array(dummy_vec, dtype="float32")

        with patch(
            "kuzu_memory.core.memory._SemanticScorer"
            if False
            else "kuzu_memory.recall.coordinator._SemanticScorer"
        ):
            with patch.object(km, "_write_embedding") as mock_write:
                with patch(
                    "kuzu_memory.core.memory.KuzuMemory._store_embedding_for_memory",
                    wraps=km._store_embedding_for_memory,
                ):
                    # Directly patch the scorer used inside the method
                    import kuzu_memory.recall.coordinator as coord_mod

                    original_get = coord_mod._SemanticScorer.get
                    coord_mod._SemanticScorer.get = staticmethod(lambda: mock_scorer)  # type: ignore[assignment]
                    try:
                        km._store_embedding_for_memory("mem-abc", "test content")
                    finally:
                        coord_mod._SemanticScorer.get = original_get  # type: ignore[method-assign]

                mock_write.assert_called_once_with("mem-abc", dummy_vec)

    def test_store_embedding_noop_when_scorer_unavailable(self) -> None:
        """If scorer.embed() returns None, _write_embedding is NOT called."""
        from kuzu_memory.core.memory import KuzuMemory

        km = KuzuMemory.__new__(KuzuMemory)
        mock_adapter = MagicMock()
        km.db_adapter = mock_adapter  # type: ignore[attr-defined]

        mock_scorer = MagicMock()
        mock_scorer.embed.return_value = None

        import kuzu_memory.recall.coordinator as coord_mod

        original_get = coord_mod._SemanticScorer.get
        coord_mod._SemanticScorer.get = staticmethod(lambda: mock_scorer)  # type: ignore[assignment]
        try:
            km._store_embedding_for_memory("mem-xyz", "some content")
        finally:
            coord_mod._SemanticScorer.get = original_get  # type: ignore[method-assign]

        mock_adapter.execute_query.assert_not_called()
