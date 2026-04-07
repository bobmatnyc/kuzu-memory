"""
Base classes for the KuzuMemory graph enrichment system.

Enrichers are background-only operations that populate derived graph structures
(e.g. CO_OCCURS_WITH edges, graph_score centrality) from existing Memory and
Entity nodes.  They must never block recall or ingestion.

All DB writes go through KuzuAdapter.execute_query() which holds _write_lock.
Enrichers must NOT load embeddings or sentence-transformers.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.config import KuzuMemoryConfig
    from ..storage.kuzu_adapter import KuzuAdapter

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result of a single enricher run.

    Attributes:
        name: Enricher identifier.
        edges_created: Number of graph edges created or updated.
        nodes_updated: Number of nodes whose properties were updated.
        duration_ms: Wall-clock time taken by the enricher, in milliseconds.
        error: If set, the enricher failed and this is the error message.
    """

    name: str
    edges_created: int = 0
    nodes_updated: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """True when the enricher completed without error."""
        return self.error is None


class BaseEnricher(ABC):
    """Abstract base for graph enrichers.

    Subclasses implement :meth:`enrich`, which should be:

    * **Idempotent** — safe to run repeatedly (use MERGE instead of CREATE).
    * **Non-raising** — catch and log all exceptions internally; return an
      :class:`EnrichmentResult` with ``error`` set on failure.
    * **Write-lock compliant** — all DB writes must go through
      ``KuzuAdapter.execute_query()``, which serialises writes via ``_write_lock``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable enricher identifier used in logs and result objects."""

    @abstractmethod
    def enrich(
        self,
        adapter: KuzuAdapter,
        config: KuzuMemoryConfig,
    ) -> EnrichmentResult:
        """Run the enricher and return a result summary.

        Args:
            adapter: Initialised KuzuAdapter — use ``adapter.execute_query()``
                     for all DB access so writes are serialised correctly.
            config: KuzuMemory configuration, e.g. for batch sizes.

        Returns:
            :class:`EnrichmentResult` describing what was done.
            Must **never raise** — catch exceptions and set ``result.error``.
        """
