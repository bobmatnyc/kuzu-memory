"""
RELATES_TO enricher.

Populates RELATES_TO edges between Memory nodes that share a common Entity
(via MENTIONS relationships).  Two separate passes are run:

1. **Shared-entity edges** — any two memories that both mention the same entity
   get a RELATES_TO edge with relationship_type='shared_entity'.  Weight starts
   at 1.0 and is incremented by 1.0 on each re-run (each additional shared
   entity increases the signal).

2. **Knowledge-type affinity edges** — specific knowledge-type pairs that are
   conceptually complementary receive an elevated weight of 2.0:
   - gotcha → pattern  (problem → solution pairing)
   - rule → architecture  (constraint → structural decision pairing)

Architecture constraints:
- Pure graph traversal only — no embeddings, no sentence-transformers.
- All DB writes go through KuzuAdapter.execute_query() (_write_lock).
- Background-only: never blocks recall or ingestion.
- Fully idempotent via MERGE semantics.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from .base import BaseEnricher, EnrichmentResult

if TYPE_CHECKING:
    from ..core.config import KuzuMemoryConfig
    from ..storage.kuzu_adapter import KuzuAdapter

logger = logging.getLogger(__name__)

# Knowledge-type pairs that receive elevated affinity edges.
_KT_AFFINITY_PAIRS: list[tuple[str, str]] = [
    ("gotcha", "pattern"),
    ("rule", "architecture"),
]


class RelatesToEnricher(BaseEnricher):
    """Populates RELATES_TO edges between Memory nodes sharing common entities.

    Pass 1 — Shared-entity edges:
        Any two memories that both mention the same entity get a RELATES_TO edge.
        Direction is normalised to m1.id < m2.id to avoid bidirectional duplicates.
        Weight is incremented on each re-run so edges strengthen over time.

    Pass 2 — Knowledge-type affinity edges:
        gotcha→pattern and rule→architecture pairs sharing an entity receive a
        relationship_type='kt_affinity' edge with weight >= 2.0.  These are
        merged separately so the elevated weight is never downgraded.

    Idempotency: all writes use MERGE so the enricher is safe to call repeatedly.
    """

    @property
    def name(self) -> str:
        return "relates_to"

    def enrich(
        self,
        adapter: KuzuAdapter,
        config: KuzuMemoryConfig,
    ) -> EnrichmentResult:
        """Run both enrichment passes and return a combined result.

        Returns:
            EnrichmentResult with edges_created = total edges touched across
            both passes.  Never raises — exceptions are logged and set on
            result.error.
        """
        start = time.monotonic()
        result = EnrichmentResult(name=self.name)

        try:
            shared_count = self._run_shared_entity_merge(adapter)
            kt_count = self._run_kt_affinity_merge(adapter)
            result.edges_created = shared_count + kt_count
        except Exception as exc:
            logger.warning(
                "RelatesToEnricher failed (non-fatal): %s",
                exc,
                exc_info=True,
            )
            result.error = str(exc)

        result.duration_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "RelatesToEnricher: edges_affected=%d  error=%s  (%.1f ms)",
            result.edges_created,
            result.error,
            result.duration_ms,
        )
        return result

    def _run_shared_entity_merge(self, adapter: KuzuAdapter) -> int:
        """Merge shared-entity RELATES_TO edges and return edge count.

        Uses m1.id < m2.id to normalise edge direction, preventing both
        (A→B) and (B→A) from being created for the same pair.
        """
        merge_query = """
            MATCH (m1:Memory)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(m2:Memory)
            WHERE m1.id < m2.id
            MERGE (m1)-[r:RELATES_TO]->(m2)
            SET r.weight = CASE WHEN r.weight IS NULL THEN 1.0 ELSE r.weight + 1.0 END,
                r.relationship_type = 'shared_entity'
        """
        try:
            adapter.execute_query(merge_query)
        except Exception as merge_exc:
            raise RuntimeError(f"RELATES_TO shared-entity MERGE failed: {merge_exc}") from merge_exc

        # Count edges after merge to report a meaningful total.
        count_query = """
            MATCH ()-[r:RELATES_TO]->()
            RETURN COUNT(r) AS cnt
        """
        try:
            rows = adapter.execute_query(count_query)
            return int(rows[0].get("cnt", 0)) if rows else 0
        except Exception:
            return 0

    def _run_kt_affinity_merge(self, adapter: KuzuAdapter) -> int:
        """Merge knowledge-type affinity edges for configured pairs.

        For each (kt1, kt2) pair, finds memories of those types that share
        an entity and elevates the RELATES_TO edge weight to at least 2.0
        with relationship_type='kt_affinity'.

        Returns total rows affected across all pairs (approximate).
        """
        total = 0
        for kt1, kt2 in _KT_AFFINITY_PAIRS:
            total += self._merge_one_affinity_pair(adapter, kt1, kt2)
        return total

    def _merge_one_affinity_pair(
        self,
        adapter: KuzuAdapter,
        kt1: str,
        kt2: str,
    ) -> int:
        """Merge kt_affinity edges for a single (kt1, kt2) pair.

        The weight SET logic ensures we never downgrade an existing weight
        that was already raised higher by a previous pass.
        """
        affinity_query = """
            MATCH (m1:Memory {knowledge_type: $kt1})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(m2:Memory {knowledge_type: $kt2})
            MERGE (m1)-[r:RELATES_TO]->(m2)
            SET r.relationship_type = 'kt_affinity',
                r.weight = CASE WHEN r.weight IS NULL THEN 2.0 ELSE CASE WHEN r.weight < 2.0 THEN 2.0 ELSE r.weight END END
        """
        try:
            adapter.execute_query(affinity_query, {"kt1": kt1, "kt2": kt2})
        except Exception as exc:
            # Non-fatal per-pair failure — log and continue.
            logger.debug(
                "kt_affinity MERGE for (%s, %s) failed (non-fatal): %s",
                kt1,
                kt2,
                exc,
            )
            return 0

        # Count kt_affinity edges for this pair.
        count_query = """
            MATCH ()-[r:RELATES_TO]->()
            WHERE r.relationship_type = 'kt_affinity'
            RETURN COUNT(r) AS cnt
        """
        try:
            rows = adapter.execute_query(count_query)
            return int(rows[0].get("cnt", 0)) if rows else 0
        except Exception:
            return 0
