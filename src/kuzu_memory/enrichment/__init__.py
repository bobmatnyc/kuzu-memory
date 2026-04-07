"""
KuzuMemory graph enrichment subsystem.

Provides background enrichers that populate derived graph structures from
existing Memory and Entity nodes.  Enrichers are idempotent, write-lock
compliant, and must never block recall or ingestion.

Public API::

    from kuzu_memory.enrichment import (
        BaseEnricher,
        EnrichmentResult,
        EnrichmentRunner,
        EntityCoOccurrenceEnricher,
        CentralityEnricher,
    )

Typical usage::

    from kuzu_memory.enrichment import EnrichmentRunner

    # Fire-and-forget from _optimize_full_maintenance or post-ingestion:
    EnrichmentRunner(adapter, config).run_background()

    # Synchronous (tests, explicit kuzu_optimize tool):
    results = EnrichmentRunner(adapter, config).run_all()
"""

from .base import BaseEnricher, EnrichmentResult
from .centrality import CentralityEnricher
from .entity_cooccurrence import EntityCoOccurrenceEnricher
from .hnsw_index import EMBEDDING_DIM, HNSW_INDEX_NAME, HNSWIndexEnricher
from .relates_to import RelatesToEnricher
from .runner import EnrichmentRunner
from .tfidf_keyword import TFIDFKeywordEnricher

__all__ = [
    "EMBEDDING_DIM",
    "HNSW_INDEX_NAME",
    "BaseEnricher",
    "CentralityEnricher",
    "EnrichmentResult",
    "EnrichmentRunner",
    "EntityCoOccurrenceEnricher",
    "HNSWIndexEnricher",
    "RelatesToEnricher",
    "TFIDFKeywordEnricher",
]
