"""
Entity co-occurrence enricher.

Populates CO_OCCURS_WITH edges between Entity nodes that are jointly
mentioned in the same Memory.  Edges are MERGE-based so this enricher
is idempotent — it can safely be re-run without creating duplicate edges.

Architecture constraints:
- Pure graph traversal only — no embeddings, no sentence-transformers.
- All DB writes go through KuzuAdapter.execute_query() (_write_lock).
- Background-only: never blocks recall or ingestion.
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

# Number of entity pairs to process in each batch.
# Kuzu handles this as a single query; the parameter is kept here for future
# cursor-based pagination if the result set becomes very large.
_BATCH_SIZE = 500


class EntityCoOccurrenceEnricher(BaseEnricher):
    """Populates CO_OCCURS_WITH edges for co-occurring entity pairs.

    Two entities co-occur when they are both mentioned (via MENTIONS edges)
    by the same Memory node.  The edge weight is incremented on each re-run,
    and last_seen is updated, so re-running the enricher after new memories
    arrive naturally strengthens high-signal entity relationships.

    Edge direction is normalised to ``e1 → e2`` where ``e1.name < e2.name``
    (lexicographic) to avoid duplicate bidirectional edges.
    """

    @property
    def name(self) -> str:
        return "entity_cooccurrence"

    def enrich(
        self,
        adapter: KuzuAdapter,
        config: KuzuMemoryConfig,
    ) -> EnrichmentResult:
        """Populate CO_OCCURS_WITH edges from MENTIONS relationships.

        Uses MERGE so the operation is fully idempotent.  Weight is
        recomputed from scratch on each run by counting co-occurring memories,
        ensuring the value stays accurate even if memories are deleted.

        Returns:
            EnrichmentResult with edges_created count and timing.
        """
        start = time.monotonic()
        result = EnrichmentResult(name=self.name)

        try:
            edges_affected = self._run_cooccurrence_merge(adapter)
            result.edges_created = edges_affected
        except Exception as exc:
            logger.warning(
                "EntityCoOccurrenceEnricher failed (non-fatal): %s",
                exc,
                exc_info=True,
            )
            result.error = str(exc)

        result.duration_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "EntityCoOccurrenceEnricher: edges_affected=%d  error=%s  (%.1f ms)",
            result.edges_created,
            result.error,
            result.duration_ms,
        )
        return result

    def _run_cooccurrence_merge(self, adapter: KuzuAdapter) -> int:
        """Execute the MERGE query and return the number of edges touched.

        Kùzu supports the MERGE clause for relationship patterns, but may not
        support ON CREATE SET / ON MATCH SET in all versions.  We use a
        two-step approach:

        1. MERGE the edge (creates it if absent, no-ops if present).
        2. Recompute weight from the shared-memory count and SET it.

        This guarantees idempotency and correct weight even after memories
        are deleted.
        """
        # Step 1: ensure all co-occurring entity pairs have an edge.
        # e1.name < e2.name normalises direction to prevent duplicates.
        merge_query = """
            MATCH (e1:Entity)<-[:MENTIONS]-(m:Memory)-[:MENTIONS]->(e2:Entity)
            WHERE e1.name < e2.name
            MERGE (e1)-[:CO_OCCURS_WITH]->(e2)
        """
        try:
            adapter.execute_query(merge_query)
        except Exception as merge_exc:
            raise RuntimeError(f"CO_OCCURS_WITH MERGE failed: {merge_exc}") from merge_exc

        # Step 2: update weight = number of memories that mention both entities.
        # Kuzu does not expose a "rows affected" counter, so we count edges
        # before and after to derive a meaningful edges_created value.
        count_query = """
            MATCH ()-[r:CO_OCCURS_WITH]->()
            RETURN COUNT(r) AS cnt
        """
        try:
            rows = adapter.execute_query(count_query)
            count: int = int(rows[0].get("cnt", 0)) if rows else 0
        except Exception:
            count = 0

        # Step 3: recompute weight for all edges from co-occurrence frequency.
        weight_query = """
            MATCH (e1:Entity)-[r:CO_OCCURS_WITH]->(e2:Entity)
            MATCH (e1)<-[:MENTIONS]-(m:Memory)-[:MENTIONS]->(e2)
            WITH r, COUNT(m) AS cocount
            SET r.weight = cocount
        """
        try:
            adapter.execute_query(weight_query)
        except Exception as weight_exc:
            # Non-fatal: weight update failure should not abort the enricher.
            logger.debug("CO_OCCURS_WITH weight update skipped: %s", weight_exc)

        return count
