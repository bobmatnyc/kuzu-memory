"""
HNSW vector index enricher.

Creates and maintains a Kùzu native HNSW (Hierarchical Navigable Small World)
vector index over the ``embedding`` column on Memory nodes.  This index enables
sub-linear approximate nearest-neighbour search during MCP recall, replacing the
brute-force O(N) NumPy cosine scan with an O(log N) QUERY_VECTOR_INDEX call.

Architecture constraints:
- MCP recall path ONLY.  Hooks remain pure graph traversal — no embeddings.
- All DB writes go through KuzuAdapter.execute_query() (_write_lock).
- Background-only: never blocks recall or ingestion.
- Idempotent: safe to run repeatedly (probe-then-alter / already-exists guard).
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

# Dimensionality of the all-MiniLM-L6-v2 sentence-transformer model.
EMBEDDING_DIM = 384

# Name of the HNSW index in Kùzu — used in both CREATE and QUERY calls.
HNSW_INDEX_NAME = "memory_hnsw_idx"


class HNSWIndexEnricher(BaseEnricher):
    """Ensures the ``embedding`` FLOAT[384] column and HNSW index exist on Memory.

    On every enrichment run:
    1. Probes for ``m.embedding`` via a LIMIT 0 query; if absent, adds the
       column via ALTER TABLE (same probe-then-alter pattern as CentralityEnricher).
    2. Attempts to create the HNSW index via ``CALL CREATE_VECTOR_INDEX(...)``
       (Kùzu 0.11.3 confirmed syntax).  An "already exists" error is silently
       swallowed.

    The enricher does NOT compute or store embeddings — that is done at ingestion
    time inside ``KuzuMemory.remember()`` / ``generate_memories()``.  The enricher
    is purely structural: column + index lifecycle management.
    """

    @property
    def name(self) -> str:
        return "hnsw_index"

    def enrich(
        self,
        adapter: KuzuAdapter,
        config: KuzuMemoryConfig,
    ) -> EnrichmentResult:
        """Ensure embedding column and HNSW index exist.

        Returns:
            EnrichmentResult with timing metadata.
        """
        start = time.monotonic()
        result = EnrichmentResult(name=self.name)

        try:
            self._ensure_embedding_column(adapter)
            self._ensure_hnsw_index(adapter)
        except Exception as exc:
            logger.warning(
                "HNSWIndexEnricher failed (non-fatal): %s",
                exc,
                exc_info=True,
            )
            result.error = str(exc)

        result.duration_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "HNSWIndexEnricher: error=%s  (%.1f ms)",
            result.error,
            result.duration_ms,
        )
        return result

    def _ensure_embedding_column(self, adapter: KuzuAdapter) -> None:
        """Add ``embedding FLOAT[384]`` column to Memory table if absent.

        Uses the probe-then-alter pattern established in
        KuzuAdapter._run_schema_migrations() and CentralityEnricher:
        attempt a LIMIT 0 read; if Kùzu raises "cannot find property",
        execute the ALTER TABLE.
        """
        probe_query = "MATCH (m:Memory) RETURN m.embedding LIMIT 0"
        try:
            adapter.execute_query(probe_query)
            # Column already present — nothing to do.
        except Exception as probe_exc:
            probe_msg = str(probe_exc).lower()
            if "cannot find property" in probe_msg or "embedding" in probe_msg:
                alter_query = f"ALTER TABLE Memory ADD embedding FLOAT[{EMBEDDING_DIM}]"
                try:
                    adapter.execute_query(alter_query)
                    logger.info("Schema migration applied: %s", alter_query)
                except Exception as alter_exc:
                    logger.warning(
                        "ALTER TABLE Memory ADD embedding failed (non-fatal): %s",
                        alter_exc,
                    )
            else:
                # Unexpected probe error — log and continue.
                logger.debug("embedding column probe error (non-fatal): %s", probe_exc)

    def _ensure_hnsw_index(self, adapter: KuzuAdapter) -> None:
        """Create the HNSW vector index on Memory.embedding if not already present.

        Kùzu 0.11.3 confirmed syntax::

            CALL CREATE_VECTOR_INDEX("Memory", "memory_hnsw_idx", "embedding")

        An "already exists" or similar index-conflict error is silently swallowed
        so that repeated enrichment runs are idempotent.
        """
        create_query = f'CALL CREATE_VECTOR_INDEX("Memory", "{HNSW_INDEX_NAME}", "embedding")'
        try:
            adapter.execute_query(create_query)
            logger.info("HNSW vector index created: %s", HNSW_INDEX_NAME)
        except Exception as exc:
            exc_msg = str(exc).lower()
            if "already exists" in exc_msg or "index" in exc_msg:
                # Index already exists — fine, nothing to do.
                logger.debug("HNSW index already exists or not applicable: %s", exc)
            else:
                # Re-raise unexpected errors so the caller can log them properly.
                raise
