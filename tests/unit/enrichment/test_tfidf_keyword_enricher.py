"""
Unit tests for TFIDFKeywordEnricher.

Coverage:
- tokenize() helper: stopwords, short words, case normalisation
- TF-IDF score computation correctness on a known corpus
- Keyword node MERGE calls
- HAS_KEYWORD edge MERGE calls
- Empty memory set (no-op, no error)
- Batch processing for large datasets
- EnrichmentRunner has 5 enrichers, fifth is TFIDFKeywordEnricher
"""

from __future__ import annotations

import math
from typing import Any
from unittest.mock import MagicMock

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.enrichment import EnrichmentRunner, TFIDFKeywordEnricher
from kuzu_memory.enrichment.tfidf_keyword import _BATCH_SIZE, tokenize

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> KuzuMemoryConfig:
    return KuzuMemoryConfig.default()


def _make_adapter(memory_rows: list[dict[str, Any]] | None = None) -> MagicMock:
    """Return a mock KuzuAdapter.

    Memory fetch returns *memory_rows*; all other queries (MERGE) return [].
    """
    adapter = MagicMock()
    adapter.config = _make_config()

    rows = memory_rows if memory_rows is not None else []

    def _execute(query: str, _params: dict | None = None) -> list[dict]:
        # Memory fetch query contains "m.content AS content"
        if "m.content AS content" in query:
            return list(rows)
        # MERGE queries return empty list (side-effect only)
        return []

    adapter.execute_query.side_effect = _execute
    return adapter


# ---------------------------------------------------------------------------
# tokenize()
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_removes_stopwords(self) -> None:
        tokens = tokenize("the quick brown fox")
        assert "the" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_removes_short_words(self) -> None:
        # Words shorter than 3 characters should be excluded.
        tokens = tokenize("a an it is ok go run")
        # "run" is 3 chars -> included; "go" is 2 -> excluded; "ok" is 2 -> excluded
        assert "run" in tokens
        assert "go" not in tokens
        assert "ok" not in tokens

    def test_lowercase(self) -> None:
        tokens = tokenize("Python ASYNC FastAPI")
        assert "python" in tokens
        assert "async" in tokens
        assert "fastapi" in tokens
        # Original-case strings must not appear.
        assert "Python" not in tokens
        assert "FastAPI" not in tokens

    def test_digits_and_punctuation_excluded(self) -> None:
        tokens = tokenize("version 3.12 release-notes: breaking!")
        assert "version" in tokens
        assert "release" in tokens
        assert "notes" in tokens
        # Digits and punctuation should not appear as tokens
        for tok in tokens:
            assert tok.isalpha(), f"Non-alpha token found: {tok!r}"

    def test_empty_string(self) -> None:
        assert tokenize("") == []

    def test_returns_duplicates_for_tf(self) -> None:
        # Repeated words should be preserved (needed for TF computation).
        tokens = tokenize("python python python")
        assert tokens.count("python") == 3


# ---------------------------------------------------------------------------
# TF-IDF score correctness
# ---------------------------------------------------------------------------


class TestTFIDFComputed:
    """Verify TF-IDF scores against hand-computed values for a small corpus."""

    def test_tfidf_computed_correctly(self) -> None:
        """Known corpus: 2 docs, one unique word each + one shared word.

        doc1: "python async python"  -> tokens: ["python", "async", "python"]
        doc2: "python memory"        -> tokens: ["python", "memory"]

        TF("python", doc1) = 2/3
        TF("async", doc1) = 1/3
        TF("python", doc2) = 1/2
        TF("memory", doc2) = 1/2

        N=2, df("python")=2, df("async")=1, df("memory")=1
        IDF("python") = log(2 / (1+2)) = log(2/3) < 0  -> tfidf(python,doc1) = (2/3)*log(2/3)
        IDF("async")  = log(2 / (1+1)) = log(1.0) = 0.0
        IDF("memory") = log(2 / (1+1)) = log(1.0) = 0.0

        The enricher uses UNWIND bulk queries: one call with {"keywords": [...]}
        for keyword nodes and one call with {"edges": [...]} for HAS_KEYWORD edges.
        """
        memory_rows = [
            {"id": "doc1", "content": "python async python"},
            {"id": "doc2", "content": "python memory"},
        ]
        adapter = _make_adapter(memory_rows)
        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, f"Enricher failed: {result.error}"

        # Find the UNWIND bulk keyword MERGE call: params={"keywords": [...]}
        keyword_bulk_calls = [
            c
            for c in adapter.execute_query.call_args_list
            if c.args
            and "MERGE (k:Keyword" in c.args[0]
            and c.args[1] is not None
            and "keywords" in c.args[1]
        ]
        assert keyword_bulk_calls, "Expected at least one UNWIND bulk Keyword MERGE call"

        # Flatten the list-of-dicts into a lookup by word.
        keyword_params: dict[str, Any] = {}
        for call_obj in keyword_bulk_calls:
            for kw in call_obj.args[1]["keywords"]:
                keyword_params[kw["word"]] = kw

        assert "python" in keyword_params
        assert "async" in keyword_params
        assert "memory" in keyword_params

        expected_idf_python = math.log(2 / (1 + 2))
        expected_idf_async = math.log(2 / (1 + 1))
        assert keyword_params["python"]["idf"] == pytest.approx(expected_idf_python, abs=1e-9)
        assert keyword_params["async"]["idf"] == pytest.approx(expected_idf_async, abs=1e-9)
        assert keyword_params["memory"]["idf"] == pytest.approx(expected_idf_async, abs=1e-9)

        # total_mentions: df counts.
        assert keyword_params["python"]["total_mentions"] == 2
        assert keyword_params["async"]["total_mentions"] == 1
        assert keyword_params["memory"]["total_mentions"] == 1


# ---------------------------------------------------------------------------
# Keyword node MERGE calls
# ---------------------------------------------------------------------------


class TestMergeKeywordNodes:
    def test_merge_keyword_nodes_created(self) -> None:
        """MERGE (k:Keyword ...) must be called for each distinct token.

        The enricher uses a single UNWIND bulk query with params={"keywords": [...]}.
        """
        memory_rows = [
            {"id": "m1", "content": "python async programming"},
            {"id": "m2", "content": "memory graph database"},
        ]
        adapter = _make_adapter(memory_rows)
        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, result.error

        # The UNWIND bulk call has params={"keywords": [{"word": ..., "idf": ..., ...}, ...]}
        keyword_bulk_calls = [
            c
            for c in adapter.execute_query.call_args_list
            if c.args
            and "MERGE (k:Keyword" in c.args[0]
            and c.args[1] is not None
            and "keywords" in c.args[1]
        ]
        assert keyword_bulk_calls, "Expected at least one UNWIND bulk Keyword MERGE call"

        merged_words = {
            kw["word"] for call_obj in keyword_bulk_calls for kw in call_obj.args[1]["keywords"]
        }

        # Expected tokens after tokenisation and stopword removal
        assert "python" in merged_words
        assert "async" in merged_words
        assert "programming" in merged_words
        assert "memory" in merged_words
        assert "graph" in merged_words
        assert "database" in merged_words

    def test_nodes_updated_count_matches_unique_keywords(self) -> None:
        memory_rows = [{"id": "m1", "content": "python database testing"}]
        adapter = _make_adapter(memory_rows)
        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success
        # Each unique keyword gets exactly one MERGE Keyword call.
        assert result.nodes_updated == 3  # python, database, testing


# ---------------------------------------------------------------------------
# HAS_KEYWORD edge MERGE calls
# ---------------------------------------------------------------------------


class TestMergeHasKeywordEdges:
    def test_merge_has_keyword_edges_created(self) -> None:
        """MERGE (m)-[hk:HAS_KEYWORD]->(k) must produce one edge per (memory, word) pair.

        The enricher uses a single UNWIND bulk query with params={"edges": [...]},
        where each element is {"memory_id": ..., "word": ..., "tf": ..., "tfidf": ...}.
        """
        memory_rows = [{"id": "m1", "content": "python async programming"}]
        adapter = _make_adapter(memory_rows)
        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, result.error

        # The UNWIND bulk call has params={"edges": [...]}
        edge_bulk_calls = [
            c
            for c in adapter.execute_query.call_args_list
            if c.args
            and "MERGE (m)-[hk:HAS_KEYWORD]" in c.args[0]
            and c.args[1] is not None
            and "edges" in c.args[1]
        ]
        assert edge_bulk_calls, "Expected at least one UNWIND bulk HAS_KEYWORD MERGE call"

        # Collect all edge dicts across all bulk calls.
        all_edges = [e for call_obj in edge_bulk_calls for e in call_obj.args[1]["edges"]]

        # One edge per (memory, word) pair: python, async, programming
        assert len(all_edges) == 3

        for edge in all_edges:
            assert edge["memory_id"] == "m1"
            assert "word" in edge
            assert "tf" in edge
            assert "tfidf" in edge
            assert isinstance(edge["tf"], float)
            assert isinstance(edge["tfidf"], float)

    def test_edges_created_count(self) -> None:
        memory_rows = [
            {"id": "m1", "content": "python database"},
            {"id": "m2", "content": "python testing"},
        ]
        adapter = _make_adapter(memory_rows)
        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success
        # m1: python, database (2 edges)
        # m2: python, testing (2 edges)
        assert result.edges_created == 4


# ---------------------------------------------------------------------------
# Edge case: empty memory set
# ---------------------------------------------------------------------------


class TestEmptyMemorySet:
    def test_empty_memory_set_no_error(self) -> None:
        """Enricher must succeed (no error) when there are no active memories."""
        adapter = _make_adapter(memory_rows=[])
        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, f"Expected success, got error: {result.error}"
        assert result.nodes_updated == 0
        assert result.edges_created == 0

    def test_empty_memory_set_no_merge_calls(self) -> None:
        adapter = _make_adapter(memory_rows=[])
        enricher = TFIDFKeywordEnricher()
        enricher.enrich(adapter, _make_config())

        merge_calls = [
            c for c in adapter.execute_query.call_args_list if c.args and "MERGE" in c.args[0]
        ]
        assert merge_calls == [], "Expected no MERGE calls for empty memory set"

    def test_fetch_failure_captured_as_error(self) -> None:
        """If the memory fetch query raises, result.error must be set (not raised)."""
        adapter = MagicMock()
        adapter.config = _make_config()
        adapter.execute_query.side_effect = RuntimeError("db failure")

        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert not result.success
        assert "db failure" in (result.error or "")


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


class TestBatchProcessing:
    def test_batch_processing_large_dataset(self) -> None:
        """Memories above _BATCH_SIZE must all be processed correctly."""
        n = _BATCH_SIZE + 10  # Just over one full batch.
        memory_rows = [
            {"id": f"m{i}", "content": f"unique token word{i} database python"} for i in range(n)
        ]
        adapter = _make_adapter(memory_rows)
        enricher = TFIDFKeywordEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, result.error
        # All n memories must produce edges.
        assert result.edges_created > 0
        # Verify we processed all batches: edge_count >= n (each doc has multiple tokens).
        assert result.edges_created >= n


# ---------------------------------------------------------------------------
# EnrichmentRunner integration
# ---------------------------------------------------------------------------


class TestRunnerIntegration:
    def test_runner_has_five_enrichers(self) -> None:
        adapter = MagicMock()
        adapter.config = _make_config()
        runner = EnrichmentRunner(adapter, _make_config())

        assert len(runner._enrichers) == 5

    def test_runner_fifth_enricher_is_tfidf(self) -> None:
        adapter = MagicMock()
        adapter.config = _make_config()
        runner = EnrichmentRunner(adapter, _make_config())

        assert isinstance(runner._enrichers[4], TFIDFKeywordEnricher)

    def test_runner_includes_tfidf_name_in_results(self) -> None:
        """run_all() result set must contain 'tfidf_keyword'."""
        adapter = MagicMock()
        adapter.config = _make_config()

        def _execute(query: str, _params: dict | None = None) -> list[dict]:
            if "m.content AS content" in query:
                return []
            if "CO_OCCURS_WITH]->()":
                return [{"cnt": 0}]
            if "COUNT(m)":
                return [{"cnt": 0}]
            return []

        adapter.execute_query.side_effect = _execute

        runner = EnrichmentRunner(adapter, _make_config())
        results = runner.run_all()

        names = {r.name for r in results}
        assert "tfidf_keyword" in names
