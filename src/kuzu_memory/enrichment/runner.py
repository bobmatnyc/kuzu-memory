"""
Enrichment runner — orchestrates all enrichers in a background thread.

The runner can be invoked two ways:

* ``run_all()`` — synchronous, returns results immediately (for tests / CLI).
* ``run_background()`` — submits ``run_all`` to a thread-pool executor and
  returns immediately so the caller is never blocked.

Architecture constraints:
- Only one background enrichment thread runs at a time (max_workers=1).
- All DB writes inside enrichers go through KuzuAdapter.execute_query()
  which holds _write_lock — no additional locking is needed here.
- Enrichers must not load embeddings or sentence-transformers.
"""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING

from .base import EnrichmentResult
from .centrality import CentralityEnricher
from .entity_cooccurrence import EntityCoOccurrenceEnricher
from .hnsw_index import HNSWIndexEnricher

if TYPE_CHECKING:
    from ..core.config import KuzuMemoryConfig
    from ..storage.kuzu_adapter import KuzuAdapter

logger = logging.getLogger(__name__)

# Module-level single-threaded executor.  Using a class-level attribute
# ensures it is shared across all EnrichmentRunner instances in the same
# process, preventing unbounded thread creation.
_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="kuzu-enrichment",
)


class EnrichmentRunner:
    """Orchestrates enrichers and manages background execution.

    Usage (from _optimize_full_maintenance or post-ingestion counter)::

        runner = EnrichmentRunner(adapter, config)

        # Fire-and-forget background enrichment (non-blocking):
        runner.run_background()

        # Synchronous (for tests or explicit kuzu_optimize calls):
        results = runner.run_all()

    Args:
        adapter: Initialised KuzuAdapter used by all enrichers.
        config: KuzuMemory configuration forwarded to each enricher.
    """

    def __init__(self, adapter: KuzuAdapter, config: KuzuMemoryConfig) -> None:
        self.adapter = adapter
        self.config = config
        self._enrichers = [
            EntityCoOccurrenceEnricher(),
            CentralityEnricher(),
            HNSWIndexEnricher(),
        ]

    def run_all(self) -> list[EnrichmentResult]:
        """Run every enricher sequentially and return all results.

        Each enricher is run inside an individual try/except so that a
        failure in one does not prevent the others from running.

        Returns:
            List of :class:`~.base.EnrichmentResult` objects, one per enricher.
        """
        results: list[EnrichmentResult] = []
        for enricher in self._enrichers:
            try:
                r = enricher.enrich(self.adapter, self.config)
            except Exception as exc:
                # BaseEnricher.enrich should never raise, but guard defensively.
                logger.error(
                    "Enricher %s raised unexpectedly: %s",
                    enricher.name,
                    exc,
                    exc_info=True,
                )
                r = EnrichmentResult(name=enricher.name, error=str(exc))
            results.append(r)

        successes = sum(1 for r in results if r.success)
        failures = len(results) - successes
        logger.info(
            "Enrichment run complete: %d/%d enrichers succeeded",
            successes,
            len(results),
        )
        if failures:
            for r in results:
                if not r.success:
                    logger.warning("Enricher %s failed: %s", r.name, r.error)

        return results

    def run_background(self) -> Future[list[EnrichmentResult]]:
        """Submit enrichment to the background thread-pool and return immediately.

        Returns:
            A :class:`concurrent.futures.Future` that resolves to the list of
            results when the run completes.  Callers can safely ignore the
            future — failures are logged inside :meth:`run_all`.
        """
        future: Future[list[EnrichmentResult]] = _EXECUTOR.submit(self.run_all)

        def _log_background_error(f: Future[list[EnrichmentResult]]) -> None:
            exc = f.exception()
            if exc:
                logger.error(
                    "Background enrichment raised unexpected exception: %s",
                    exc,
                    exc_info=True,
                )

        future.add_done_callback(_log_background_error)
        logger.debug("Background enrichment submitted to thread pool")
        return future
