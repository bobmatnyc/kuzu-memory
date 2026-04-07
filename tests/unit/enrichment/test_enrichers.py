"""
Unit tests for the graph enrichment subsystem.

Tests cover:
- EntityCoOccurrenceEnricher: MERGE query pattern and edge counting
- CentralityEnricher: ALTER TABLE probe + graph_score SET query
- EnrichmentRunner: result aggregation and per-enricher exception handling
- RecallCoordinator._graph_score_boost: correct boost values and None safety
- EntityRecallStrategy 2-hop expansion: CO_OCCURS_WITH query issued when sparse
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.enrichment import CentralityEnricher, EnrichmentRunner, EntityCoOccurrenceEnricher
from kuzu_memory.recall.coordinator import RecallCoordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> KuzuMemoryConfig:
    return KuzuMemoryConfig.default()


def _make_adapter(query_responses: dict[str, Any] | None = None) -> MagicMock:
    """Return a mock KuzuAdapter whose execute_query returns canned responses."""
    adapter = MagicMock()
    adapter.config = _make_config()

    responses = query_responses or {}

    def _execute_query(query: str, params: dict | None = None) -> list[dict]:
        # Match by substring to handle whitespace variations.
        for key, value in responses.items():
            if key in query:
                if isinstance(value, Exception):
                    raise value
                return list(value)
        return []

    adapter.execute_query.side_effect = _execute_query
    return adapter


# ---------------------------------------------------------------------------
# EntityCoOccurrenceEnricher
# ---------------------------------------------------------------------------


class TestEntityCoOccurrenceEnricher:
    def test_enrich_issues_merge_query(self) -> None:
        """Enricher must issue a MERGE query containing CO_OCCURS_WITH."""
        adapter = _make_adapter(
            {
                "CO_OCCURS_WITH]->()": [{"cnt": 3}],
            }
        )
        enricher = EntityCoOccurrenceEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, f"Expected success, got error: {result.error}"
        # At least one call should contain the MERGE / CO_OCCURS_WITH pattern.
        all_queries = [c.args[0] for c in adapter.execute_query.call_args_list]
        merge_queries = [q for q in all_queries if "MERGE" in q and "CO_OCCURS_WITH" in q]
        assert merge_queries, "No MERGE query with CO_OCCURS_WITH found"

    def test_enrich_respects_direction_normalisation(self) -> None:
        """The MERGE query must use e1.name < e2.name to prevent bidirectional duplicates."""
        adapter = _make_adapter()
        enricher = EntityCoOccurrenceEnricher()
        enricher.enrich(adapter, _make_config())

        all_queries = [c.args[0] for c in adapter.execute_query.call_args_list]
        normalised = [q for q in all_queries if "e1.name < e2.name" in q]
        assert normalised, "Direction normalisation (e1.name < e2.name) not found in MERGE query"

    def test_enrich_returns_edge_count_from_count_query(self) -> None:
        """edges_created should reflect the COUNT(r) result."""
        adapter = _make_adapter({"CO_OCCURS_WITH]->()": [{"cnt": 7}]})
        enricher = EntityCoOccurrenceEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.edges_created == 7

    def test_enrich_captures_merge_failure_as_error(self) -> None:
        """If the MERGE query raises, EnrichmentResult.error must be set (not raised)."""
        adapter = _make_adapter({"MERGE": RuntimeError("kuzu error")})
        enricher = EntityCoOccurrenceEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert not result.success
        assert "kuzu error" in (result.error or "")

    def test_enrich_name_is_entity_cooccurrence(self) -> None:
        assert EntityCoOccurrenceEnricher().name == "entity_cooccurrence"


# ---------------------------------------------------------------------------
# CentralityEnricher
# ---------------------------------------------------------------------------


class TestCentralityEnricher:
    def test_enrich_probes_column_then_runs_set(self) -> None:
        """Enricher should first probe for graph_score column, then run SET."""
        # Probe succeeds (column exists) — no ALTER TABLE needed.
        adapter = _make_adapter({"COUNT(m)": [{"cnt": 5}]})
        enricher = CentralityEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success
        # SET query must contain graph_score.
        all_queries = [c.args[0] for c in adapter.execute_query.call_args_list]
        set_queries = [q for q in all_queries if "graph_score" in q and "SET" in q]
        assert set_queries, "No SET m.graph_score query found"

    def test_enrich_runs_alter_table_when_column_missing(self) -> None:
        """When probe raises 'cannot find property', ALTER TABLE should be issued."""
        call_count = {"n": 0}

        def _execute(query: str, params: dict | None = None) -> list[dict]:
            call_count["n"] += 1
            if "RETURN m.graph_score" in query:
                raise Exception("cannot find property graph_score")
            if "COUNT(m)" in query:
                return [{"cnt": 2}]
            return []

        adapter = MagicMock()
        adapter.config = _make_config()
        adapter.execute_query.side_effect = _execute

        enricher = CentralityEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success
        all_queries = [c.args[0] for c in adapter.execute_query.call_args_list]
        alter_queries = [q for q in all_queries if "ALTER TABLE" in q and "graph_score" in q]
        assert alter_queries, "ALTER TABLE for graph_score not issued when column missing"

    def test_enrich_nodes_updated_from_count(self) -> None:
        """nodes_updated should match the COUNT(m) result."""
        adapter = _make_adapter({"COUNT(m)": [{"cnt": 12}]})
        enricher = CentralityEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.nodes_updated == 12

    def test_enrich_captures_set_failure_as_error(self) -> None:
        """If the SET query raises, error should be captured, not propagated."""

        def _execute(query: str, params: dict | None = None) -> list[dict]:
            if "RETURN m.graph_score" in query:
                return []  # Probe succeeds
            if "SET m.graph_score" in query:
                raise RuntimeError("write failed")
            return []

        adapter = MagicMock()
        adapter.config = _make_config()
        adapter.execute_query.side_effect = _execute

        enricher = CentralityEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert not result.success
        assert "write failed" in (result.error or "")

    def test_enrich_name_is_centrality(self) -> None:
        assert CentralityEnricher().name == "centrality"


# ---------------------------------------------------------------------------
# EnrichmentRunner
# ---------------------------------------------------------------------------


class TestEnrichmentRunner:
    def test_run_all_returns_result_per_enricher(self) -> None:
        """run_all() must return exactly one result per enricher."""
        adapter = _make_adapter(
            {
                "CO_OCCURS_WITH]->()": [{"cnt": 0}],
                "COUNT(m)": [{"cnt": 0}],
            }
        )
        runner = EnrichmentRunner(adapter, _make_config())
        results = runner.run_all()

        assert len(results) == 2
        names = {r.name for r in results}
        assert "entity_cooccurrence" in names
        assert "centrality" in names

    def test_run_all_captures_enricher_exception_per_item(self) -> None:
        """A failure in one enricher must not prevent others from running."""
        adapter = MagicMock()
        adapter.config = _make_config()
        # All queries raise — both enrichers fail, but results are still returned.
        adapter.execute_query.side_effect = RuntimeError("db down")

        runner = EnrichmentRunner(adapter, _make_config())
        results = runner.run_all()

        # Should get 2 results (one per enricher), both failed.
        assert len(results) == 2
        assert all(not r.success for r in results)

    def test_run_all_partial_failure_captured_separately(self) -> None:
        """First enricher fails, second succeeds — each result is independent."""
        call_count = {"n": 0}

        def _execute(query: str, params: dict | None = None) -> list[dict]:
            call_count["n"] += 1
            # Fail only on CO_OCCURS_WITH queries.
            if "CO_OCCURS_WITH" in query and "MERGE" in query:
                raise RuntimeError("co-occurrence merge failed")
            if "COUNT(m)" in query:
                return [{"cnt": 3}]
            return []

        adapter = MagicMock()
        adapter.config = _make_config()
        adapter.execute_query.side_effect = _execute

        runner = EnrichmentRunner(adapter, _make_config())
        results = runner.run_all()

        cooc_result = next(r for r in results if r.name == "entity_cooccurrence")
        cent_result = next(r for r in results if r.name == "centrality")

        assert not cooc_result.success
        assert cent_result.success

    def test_run_background_returns_future(self) -> None:
        """run_background() must return a Future without blocking."""
        adapter = _make_adapter(
            {
                "CO_OCCURS_WITH]->()": [{"cnt": 0}],
                "COUNT(m)": [{"cnt": 0}],
            }
        )
        runner = EnrichmentRunner(adapter, _make_config())
        future = runner.run_background()

        # Resolve the future (waits for background thread).
        results = future.result(timeout=10)
        assert isinstance(results, list)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# RecallCoordinator._graph_score_boost
# ---------------------------------------------------------------------------


class TestGraphScoreBoost:
    """Tests for RecallCoordinator._graph_score_boost()."""

    def _coordinator(self) -> RecallCoordinator:
        adapter = MagicMock()
        adapter.db_path = MagicMock()
        return RecallCoordinator(adapter, _make_config())

    def _memory(self, graph_score: float | None = None) -> MagicMock:
        m = MagicMock()
        if graph_score is None:
            # Simulate missing attribute (old memories without graph_score).
            del m.graph_score
        else:
            m.graph_score = graph_score
        return m

    def test_zero_graph_score_returns_zero(self) -> None:
        coord = self._coordinator()
        mem = self._memory(graph_score=0.0)
        assert coord._graph_score_boost(mem) == pytest.approx(0.0)

    def test_half_graph_score_returns_half_boost(self) -> None:
        coord = self._coordinator()
        mem = self._memory(graph_score=0.5)
        assert coord._graph_score_boost(mem) == pytest.approx(0.05)

    def test_full_graph_score_returns_max_boost(self) -> None:
        coord = self._coordinator()
        mem = self._memory(graph_score=1.0)
        assert coord._graph_score_boost(mem) == pytest.approx(0.10)

    def test_graph_score_above_one_capped_at_max(self) -> None:
        coord = self._coordinator()
        mem = self._memory(graph_score=5.0)
        assert coord._graph_score_boost(mem) <= 0.10

    def test_none_graph_score_returns_zero(self) -> None:
        """getattr default must handle absent attribute gracefully."""
        coord = self._coordinator()
        mem = MagicMock(spec=["id", "content", "importance", "confidence"])
        # graph_score is NOT in spec — getattr returns default 0.0.
        assert coord._graph_score_boost(mem) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# EntityRecallStrategy 2-hop expansion
# ---------------------------------------------------------------------------


class TestEntityRecallStrategy2Hop:
    """Tests that 2-hop expansion query is issued when primary results are sparse."""

    def _make_strategy(self, primary_results: list[dict], hop2_results: list[dict]) -> Any:
        """Return an EntityRecallStrategy with a mock adapter."""
        from kuzu_memory.recall.strategies import EntityRecallStrategy

        call_count: dict[str, int] = {"primary": 0, "hop2": 0}

        def _execute(query: str, params: dict | None = None) -> list[dict]:
            if "CO_OCCURS_WITH" in query:
                call_count["hop2"] += 1
                return hop2_results
            else:
                call_count["primary"] += 1
                return primary_results

        adapter = MagicMock()
        adapter.execute_query.side_effect = _execute

        strategy = EntityRecallStrategy(adapter, _make_config())
        strategy._call_count = call_count
        return strategy

    def test_2hop_query_issued_when_primary_results_sparse(self) -> None:
        """When primary results < max_memories, CO_OCCURS_WITH query must be executed."""
        strategy = self._make_strategy(primary_results=[], hop2_results=[])

        with patch.object(
            strategy.entity_extractor,
            "extract_entities",
            return_value=[MagicMock(text="Python", normalized_text="python")],
        ):
            # _execute_recall triggers 2-hop when primary is empty.
            strategy._execute_recall(
                prompt="Python async patterns",
                max_memories=5,
                user_id=None,
                session_id=None,
                agent_id="default",
            )

        assert (
            strategy._call_count["hop2"] >= 1
        ), "2-hop CO_OCCURS_WITH query was not issued when primary results were sparse"

    def test_2hop_query_not_issued_when_primary_results_sufficient(self) -> None:
        """When primary returns enough results, 2-hop should not execute."""
        # Return enough fake row dicts to fill max_memories=2.
        primary_rows = [{"m": {"id": f"id{i}", "content": "x"}} for i in range(2)]
        strategy = self._make_strategy(primary_results=primary_rows, hop2_results=[])

        # Patch QueryBuilder at the storage module level where it is defined.
        with (
            patch.object(
                strategy.entity_extractor,
                "extract_entities",
                return_value=[MagicMock(text="Python", normalized_text="python")],
            ),
            patch("kuzu_memory.storage.query_builder.QueryBuilder") as MockQB,
        ):
            instance = MockQB.return_value
            instance._convert_db_result_to_memory.return_value = MagicMock()

            strategy._execute_recall(
                prompt="Python async",
                max_memories=2,
                user_id=None,
                session_id=None,
                agent_id="default",
            )

        # 2-hop should NOT have fired — primary produced enough results.
        assert (
            strategy._call_count["hop2"] == 0
        ), "2-hop query was issued despite sufficient primary results"

    def test_2hop_failure_is_non_fatal(self) -> None:
        """If CO_OCCURS_WITH query raises (table not yet populated), recall must not fail."""
        from kuzu_memory.recall.strategies import EntityRecallStrategy

        def _execute(query: str, params: dict | None = None) -> list[dict]:
            if "CO_OCCURS_WITH" in query:
                raise RuntimeError("table does not exist")
            return []

        adapter = MagicMock()
        adapter.execute_query.side_effect = _execute

        strategy = EntityRecallStrategy(adapter, _make_config())

        with patch.object(
            strategy.entity_extractor,
            "extract_entities",
            return_value=[MagicMock(text="Python", normalized_text="python")],
        ):
            # Should not raise.
            memories = strategy._execute_recall(
                prompt="Python",
                max_memories=5,
                user_id=None,
                session_id=None,
                agent_id="default",
            )

        assert isinstance(memories, list)
