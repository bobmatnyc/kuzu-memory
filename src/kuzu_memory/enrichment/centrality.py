"""
Centrality enricher.

Computes a simple in-degree proxy for Memory nodes (number of Entity mentions)
and stores it as ``graph_score`` on each Memory.  This score is later used by
the recall ranking layer to boost well-connected memories.

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

# Memories mentioning more than this many entities are capped at 1.0.
_ENTITY_CAP = 10


class CentralityEnricher(BaseEnricher):
    """Computes graph_score (entity-mention centrality) for Memory nodes.

    ``graph_score`` is defined as::

        min(entity_count / _ENTITY_CAP, 1.0)

    where ``entity_count`` is the number of distinct Entity nodes connected
    to the Memory via MENTIONS edges.  Memories that reference many entities
    score higher and surface earlier during graph-aware recall.

    The enricher first ensures the ``graph_score`` column exists (via ALTER
    TABLE), then recomputes scores for all memories.  Both operations are
    idempotent.
    """

    @property
    def name(self) -> str:
        return "centrality"

    def enrich(
        self,
        adapter: KuzuAdapter,
        config: KuzuMemoryConfig,
    ) -> EnrichmentResult:
        """Add graph_score column (if missing) then recompute for all Memory nodes.

        Returns:
            EnrichmentResult with nodes_updated count and timing.
        """
        start = time.monotonic()
        result = EnrichmentResult(name=self.name)

        try:
            self._ensure_column(adapter)
            updated = self._compute_scores(adapter)
            result.nodes_updated = updated
        except Exception as exc:
            logger.warning(
                "CentralityEnricher failed (non-fatal): %s",
                exc,
                exc_info=True,
            )
            result.error = str(exc)

        result.duration_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "CentralityEnricher: nodes_updated=%d  error=%s  (%.1f ms)",
            result.nodes_updated,
            result.error,
            result.duration_ms,
        )
        return result

    def _ensure_column(self, adapter: KuzuAdapter) -> None:
        """Add graph_score column to Memory table if it does not already exist.

        Uses the probe-then-alter pattern established in
        KuzuAdapter._run_schema_migrations(): attempt a LIMIT 0 read of the
        column; if Kuzu raises "cannot find property", execute the ALTER TABLE.
        """
        probe_query = "MATCH (m:Memory) RETURN m.graph_score LIMIT 0"
        try:
            adapter.execute_query(probe_query)
            # Column already present — nothing to do.
        except Exception as probe_exc:
            probe_msg = str(probe_exc).lower()
            if "cannot find property" in probe_msg or "graph_score" in probe_msg:
                alter_query = "ALTER TABLE Memory ADD graph_score FLOAT DEFAULT 0.0"
                try:
                    adapter.execute_query(alter_query)
                    logger.info("Schema migration applied: %s", alter_query)
                except Exception as alter_exc:
                    logger.warning(
                        "ALTER TABLE Memory ADD graph_score failed (non-fatal): %s",
                        alter_exc,
                    )
            else:
                # Unexpected probe error — log and continue; the SET below will
                # surface a meaningful error if the column truly does not exist.
                logger.debug("graph_score column probe error (non-fatal): %s", probe_exc)

    def _compute_scores(self, adapter: KuzuAdapter) -> int:
        """Recompute graph_score for all Memory nodes.

        Score formula: min(COUNT(distinct entities) / _ENTITY_CAP, 1.0)

        Returns:
            Number of Memory nodes updated (approximate — derived from a
            COUNT query after the SET, since Kuzu does not expose rows-affected).
        """
        score_query = f"""
            MATCH (m:Memory)
            OPTIONAL MATCH (m)-[:MENTIONS]->(e:Entity)
            WITH m, COUNT(e) AS cnt
            SET m.graph_score = CASE
                WHEN cnt > {_ENTITY_CAP} THEN 1.0
                ELSE toFloat(cnt) / {_ENTITY_CAP}.0
            END
        """
        try:
            adapter.execute_query(score_query)
        except Exception as set_exc:
            raise RuntimeError(f"graph_score SET query failed: {set_exc}") from set_exc

        # Return a count of memories as a proxy for "rows updated".
        count_query = "MATCH (m:Memory) RETURN COUNT(m) AS cnt"
        try:
            rows = adapter.execute_query(count_query)
            return int(rows[0].get("cnt", 0)) if rows else 0
        except Exception:
            return 0
