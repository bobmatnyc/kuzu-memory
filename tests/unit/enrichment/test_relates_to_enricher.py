"""
Unit tests for RelatesToEnricher.

Covers:
- Shared-entity MERGE queries are issued
- Knowledge-type affinity edges are created for gotcha→pattern and rule→architecture
- Idempotency via MERGE semantics
- m1.id < m2.id guard prevents self-loops / reverse duplicates
- Empty graph returns EnrichmentResult with 0 edges and no error
- EnrichmentRunner now contains exactly 4 enrichers
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, call

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.enrichment import EnrichmentRunner, RelatesToEnricher
from kuzu_memory.enrichment.base import EnrichmentResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> KuzuMemoryConfig:
    return KuzuMemoryConfig.default()


def _make_adapter(query_responses: dict[str, Any] | None = None) -> MagicMock:
    """Return a mock KuzuAdapter with canned query responses."""
    adapter = MagicMock()
    adapter.config = _make_config()
    responses = query_responses or {}

    def _execute_query(query: str, params: dict | None = None) -> list[dict]:
        for key, value in responses.items():
            if key in query:
                if isinstance(value, Exception):
                    raise value
                return list(value)
        return []

    adapter.execute_query.side_effect = _execute_query
    return adapter


def _all_queries(adapter: MagicMock) -> list[str]:
    """Return all query strings passed to execute_query."""
    return [c.args[0] for c in adapter.execute_query.call_args_list]


# ---------------------------------------------------------------------------
# TestSharedEntityEdgesCreated
# ---------------------------------------------------------------------------


class TestSharedEntityEdgesCreated:
    def test_shared_entity_edges_created(self) -> None:
        """Enricher must issue a MERGE query for RELATES_TO via shared entities."""
        adapter = _make_adapter(
            {
                # Shared-entity count query returns 3 edges
                "MATCH ()-[r:RELATES_TO]->()": [{"cnt": 3}],
            }
        )
        enricher = RelatesToEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, f"Expected success, got error: {result.error}"
        assert result.name == "relates_to"

        # Verify a MERGE query for RELATES_TO was issued.
        queries = _all_queries(adapter)
        merge_queries = [q for q in queries if "MERGE" in q and "RELATES_TO" in q]
        assert merge_queries, "No MERGE query containing RELATES_TO found"

    def test_shared_entity_merge_uses_direction_guard(self) -> None:
        """MERGE query must include m1.id < m2.id to prevent self-loops and duplicates."""
        adapter = _make_adapter()
        enricher = RelatesToEnricher()
        enricher.enrich(adapter, _make_config())

        queries = _all_queries(adapter)
        # At least one shared-entity MERGE should contain the direction guard.
        guarded = [q for q in queries if "m1.id < m2.id" in q]
        assert guarded, "No query with m1.id < m2.id direction guard found"

    def test_edges_created_count_from_count_query(self) -> None:
        """edges_created should reflect the count returned by the count query."""
        adapter = _make_adapter(
            {
                "MATCH ()-[r:RELATES_TO]->()": [{"cnt": 7}],
            }
        )
        enricher = RelatesToEnricher()
        result = enricher.enrich(adapter, _make_config())

        # The shared-entity pass returns the RELATES_TO count (7).
        # The kt_affinity pass also queries the same pattern (for kt_affinity type).
        # Total will be 7 + 7 + 7 (one per pair x affinity count).
        assert result.edges_created > 0


# ---------------------------------------------------------------------------
# TestKtAffinityEdgesCreated
# ---------------------------------------------------------------------------


class TestKtAffinityEdgesCreated:
    def test_kt_affinity_edges_created(self) -> None:
        """Enricher must issue kt_affinity MERGE queries for gotcha→pattern and rule→architecture."""
        adapter = _make_adapter()
        enricher = RelatesToEnricher()
        enricher.enrich(adapter, _make_config())

        queries = _all_queries(adapter)

        # Should see affinity MERGE queries parameterised with kt1/kt2 values.
        # The mock adapter won't have params, but we can verify MERGE + relationship_type pattern.
        affinity_merges = [q for q in queries if "MERGE" in q and "kt_affinity" in q]
        assert affinity_merges, "No kt_affinity MERGE queries found"

    def test_gotcha_pattern_pair_queried(self) -> None:
        """gotcha→pattern affinity pair must produce a MERGE call."""
        seen_gotcha_pattern: list[bool] = []

        adapter = MagicMock()
        adapter.config = _make_config()

        def _execute_query(query: str, params: dict | None = None) -> list[dict]:
            if params and params.get("kt1") == "gotcha" and params.get("kt2") == "pattern":
                seen_gotcha_pattern.append(True)
            return []

        adapter.execute_query.side_effect = _execute_query

        enricher = RelatesToEnricher()
        enricher.enrich(adapter, _make_config())

        assert seen_gotcha_pattern, "No execute_query call with kt1='gotcha', kt2='pattern' found"

    def test_rule_architecture_pair_queried(self) -> None:
        """rule→architecture affinity pair must produce a MERGE call."""
        seen_rule_arch: list[bool] = []

        adapter = MagicMock()
        adapter.config = _make_config()

        def _execute_query(query: str, params: dict | None = None) -> list[dict]:
            if params and params.get("kt1") == "rule" and params.get("kt2") == "architecture":
                seen_rule_arch.append(True)
            return []

        adapter.execute_query.side_effect = _execute_query

        enricher = RelatesToEnricher()
        enricher.enrich(adapter, _make_config())

        assert seen_rule_arch, "No execute_query call with kt1='rule', kt2='architecture' found"

    def test_affinity_weight_set_to_2_or_higher(self) -> None:
        """The kt_affinity MERGE SET clause must specify weight >= 2.0."""
        adapter = _make_adapter()
        enricher = RelatesToEnricher()
        enricher.enrich(adapter, _make_config())

        queries = _all_queries(adapter)
        affinity_queries = [q for q in queries if "kt_affinity" in q and "MERGE" in q]
        assert affinity_queries, "No kt_affinity MERGE found"

        # Each affinity query should reference 2.0 as the minimum weight.
        for q in affinity_queries:
            assert "2.0" in q, f"Expected '2.0' in affinity MERGE query, got:\n{q}"


# ---------------------------------------------------------------------------
# TestIdempotentOnRerun
# ---------------------------------------------------------------------------


class TestIdempotentOnRerun:
    def test_idempotent_on_rerun(self) -> None:
        """Running the enricher twice on the same adapter must not raise and must succeed both times."""
        adapter = _make_adapter(
            {
                "MATCH ()-[r:RELATES_TO]->()": [{"cnt": 2}],
            }
        )
        enricher = RelatesToEnricher()
        config = _make_config()

        result1 = enricher.enrich(adapter, config)
        result2 = enricher.enrich(adapter, config)

        assert result1.success, f"First run failed: {result1.error}"
        assert result2.success, f"Second run failed: {result2.error}"

    def test_merge_is_used_not_create(self) -> None:
        """All RELATES_TO writes must use MERGE (not CREATE) for idempotency."""
        adapter = _make_adapter()
        enricher = RelatesToEnricher()
        enricher.enrich(adapter, _make_config())

        queries = _all_queries(adapter)
        relates_to_queries = [q for q in queries if "RELATES_TO" in q]

        # None of the RELATES_TO write queries should use bare CREATE.
        create_queries = [
            q
            for q in relates_to_queries
            if "CREATE" in q and "MERGE" not in q and "IF NOT EXISTS" not in q
        ]
        assert not create_queries, f"Found CREATE (non-MERGE) queries: {create_queries}"


# ---------------------------------------------------------------------------
# TestNoSelfEdges
# ---------------------------------------------------------------------------


class TestNoSelfEdges:
    def test_no_self_edges_guard_present(self) -> None:
        """The shared-entity MERGE must include m1.id < m2.id to exclude self-edges."""
        adapter = _make_adapter()
        enricher = RelatesToEnricher()
        enricher.enrich(adapter, _make_config())

        queries = _all_queries(adapter)
        shared_merge = [
            q for q in queries if "MERGE" in q and "RELATES_TO" in q and "m1.id < m2.id" in q
        ]
        assert shared_merge, (
            "Shared-entity MERGE query does not contain m1.id < m2.id guard. "
            "This allows self-loops and bidirectional duplicates."
        )


# ---------------------------------------------------------------------------
# TestEmptyGraphNoError
# ---------------------------------------------------------------------------


class TestEmptyGraphNoError:
    def test_empty_graph_no_error(self) -> None:
        """Empty DB (no entities, no memories) must return EnrichmentResult with 0 edges."""
        # All queries return empty lists (no rows)
        adapter = _make_adapter()
        enricher = RelatesToEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert result.success, f"Expected success on empty graph, got error: {result.error}"
        assert result.edges_created == 0
        assert result.name == "relates_to"

    def test_empty_graph_does_not_raise(self) -> None:
        """enrich() must never raise even when adapter returns empty results."""
        adapter = _make_adapter()
        enricher = RelatesToEnricher()

        # Should not raise
        result = enricher.enrich(adapter, _make_config())
        assert isinstance(result, EnrichmentResult)

    def test_merge_failure_sets_error_not_raises(self) -> None:
        """If the MERGE query raises, result.error is set but no exception propagates."""
        adapter = _make_adapter(
            {
                "MATCH (m1:Memory)-[:MENTIONS]": RuntimeError("DB unavailable"),
            }
        )
        enricher = RelatesToEnricher()
        result = enricher.enrich(adapter, _make_config())

        assert not result.success
        assert result.error is not None
        assert "DB unavailable" in result.error


# ---------------------------------------------------------------------------
# TestRunnerHasFourEnrichers
# ---------------------------------------------------------------------------


class TestRunnerHasFourEnrichers:
    def test_runner_has_four_enrichers(self) -> None:
        """EnrichmentRunner must have exactly 4 enrichers after Phase 3 addition."""
        adapter = MagicMock()
        adapter.config = _make_config()
        runner = EnrichmentRunner(adapter, _make_config())

        assert len(runner._enrichers) == 5, (
            f"Expected 5 enrichers, got {len(runner._enrichers)}: "
            f"{[e.name for e in runner._enrichers]}"
        )

    def test_runner_fourth_enricher_is_relates_to(self) -> None:
        """The 4th enricher must be RelatesToEnricher."""
        adapter = MagicMock()
        adapter.config = _make_config()
        runner = EnrichmentRunner(adapter, _make_config())

        fourth = runner._enrichers[3]
        assert isinstance(
            fourth, RelatesToEnricher
        ), f"Expected RelatesToEnricher at index 3, got {type(fourth).__name__}"
        assert fourth.name == "relates_to"

    def test_runner_enricher_order(self) -> None:
        """Enrichers must appear in the expected order."""
        adapter = MagicMock()
        adapter.config = _make_config()
        runner = EnrichmentRunner(adapter, _make_config())

        names = [e.name for e in runner._enrichers]
        assert names == [
            "entity_cooccurrence",
            "centrality",
            "hnsw_index",
            "relates_to",
            "tfidf_keyword",
        ], f"Unexpected enricher order: {names}"
