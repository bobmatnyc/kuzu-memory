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
- Idempotent: safe to run repeatedly (already-exists guard on index creation).

Schema guarantee:
- ``embedding FLOAT[384]`` is declared directly in the CREATE NODE TABLE Memory
  DDL (schema.py), so the column is present from write #1.  The enricher no
  longer needs to ALTER TABLE — its sole job is to ensure the HNSW index exists.
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
    """Ensures the HNSW vector index exists on Memory.embedding.

    The ``embedding FLOAT[384]`` column is guaranteed to exist because it is
    declared in the CREATE NODE TABLE Memory DDL (schema.py) and is therefore
    present from the very first write.  This enricher's only responsibility is
    to create the HNSW index if it is missing (e.g. on databases created before
    the index was added, or after a manual DROP).

    On every enrichment run:
    1. Attempts to create the HNSW index via ``CALL CREATE_VECTOR_INDEX(...)``
       (Kùzu 0.11.3 confirmed syntax).
    2. An "already exists" or index-related error is silently swallowed so that
       repeated enrichment runs are idempotent.

    The enricher does NOT compute or store embeddings — that is done at ingestion
    time inside ``KuzuMemory.remember()`` / ``generate_memories()``.
    """

    @property
    def name(self) -> str:
        return "hnsw_index"

    def enrich(
        self,
        adapter: KuzuAdapter,
        config: KuzuMemoryConfig,
    ) -> EnrichmentResult:
        """Ensure the HNSW vector index exists on Memory.embedding.

        Returns:
            EnrichmentResult with timing metadata.
        """
        start = time.monotonic()
        result = EnrichmentResult(name=self.name)

        try:
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
