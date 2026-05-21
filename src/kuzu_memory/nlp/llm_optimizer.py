"""LLM-powered memory optimization using local models."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kuzu_memory.nlp.consolidation import MemoryCluster
    from kuzu_memory.storage.kuzu_adapter import KuzuAdapter

logger = logging.getLogger(__name__)

# Model-specific batch limits (align with mcp-vector-search learnings)
# Small models (2b/4b): smaller batches to avoid context overflow
# Large models (13b+): can handle more
_MODEL_BATCH_LIMITS = {
    "2b": 5,  # e.g. llama3.2:1b, gemma2:2b
    "4b": 8,  # e.g. phi4-mini, gemma3:4b
    "8b": 15,  # e.g. llama3.1:8b
    "default": 10,
}


def _batch_limit_for_model(model_name: str) -> int:
    """Return max memories per LLM batch based on model size hint in name."""
    name_lower = model_name.lower()
    for size, limit in _MODEL_BATCH_LIMITS.items():
        if size != "default" and size in name_lower:
            return limit
    return _MODEL_BATCH_LIMITS["default"]


@dataclass
class LLMOptimizationResult:
    """Result of one LLM optimization pass."""

    success: bool
    summaries_generated: int = 0
    memories_reclassified: int = 0
    memories_rescored: int = 0
    execution_time_ms: float = 0.0
    model_used: str = ""
    provider: str = ""
    dry_run: bool = False
    error: str | None = None
    details: list[str] = field(default_factory=list)


class LLMOptimizer:
    """
    Applies local-LLM intelligence to improve memory quality in the background.

    Three passes (all skipped gracefully if no local LLM is detected):
    1. summary_pass: upgrade consolidation cluster summaries
    2. reclassify_pass: tag NOTE memories with specific knowledge_type
    3. rescore_pass: re-evaluate importance=0.5 (default) memories

    All DB writes go through adapter.execute_query() to respect the write lock.
    Designed for background execution — never blocks the hook/recall hot path.
    """

    # Prompts tuned for small local models: terse, structured output only
    _SUMMARY_SYSTEM = (
        "You are a memory consolidation assistant. "
        "Given several related memory fragments, write ONE concise paragraph "
        "(2-4 sentences, max 200 words) that preserves all unique facts. "
        "Output only the paragraph, no preamble."
    )

    _CLASSIFY_SYSTEM = (
        "Classify the engineering memory into exactly one category. "
        "Output ONLY the category word.\n"
        "Categories:\n"
        "  rule       - absolute constraint that must/must not be done\n"
        "  pattern    - repeatable approach/solution\n"
        "  gotcha     - bug, surprise, or pitfall\n"
        "  architecture - structural/design decision\n"
        "  convention - style or workflow standard\n"
        "  note       - general info (use as last resort)"
    )

    _IMPORTANCE_SYSTEM = (
        "Rate the engineering value of this memory on a scale from 0.0 to 1.0. "
        "1.0 = critical, must not forget. 0.0 = trivial, can be deleted. "
        "Output ONLY a decimal number like 0.7, nothing else."
    )

    def __init__(
        self,
        adapter: KuzuAdapter,
        endpoint: str,
        model: str,
        timeout_ms: int = 30000,
        max_tokens: int = 256,
    ) -> None:
        self.adapter = adapter
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout_ms / 1000
        self.max_tokens = max_tokens
        self._batch_limit = _batch_limit_for_model(model)

    def _llm(self, system: str, user: str, max_tokens: int | None = None) -> str:
        """Single LLM call. Returns stripped response or raises."""
        from kuzu_memory.integrations.local_llm import chat_completion

        return chat_completion(
            endpoint=self.endpoint,
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout=self.timeout,
            max_tokens=max_tokens or self.max_tokens,
        ).strip()

    # ------------------------------------------------------------------
    # Pass 1: summary generation for consolidation clusters
    # ------------------------------------------------------------------

    def generate_summary(self, cluster: MemoryCluster) -> str:
        """Generate LLM summary for a consolidation cluster. Falls back to centroid."""
        contents = [m.content for m in cluster.memories]
        numbered = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contents))
        try:
            return self._llm(self._SUMMARY_SYSTEM, numbered, max_tokens=256)
        except Exception as e:
            logger.warning("LLM summary failed for cluster %s: %s", cluster.cluster_id, e)
            return cluster.centroid_memory.content

    # ------------------------------------------------------------------
    # Pass 2: reclassify NOTE memories
    # ------------------------------------------------------------------

    def reclassify_pass(
        self,
        limit: int = 50,
        dry_run: bool = False,
    ) -> tuple[int, list[str]]:
        """
        Find memories with knowledge_type=NOTE and classify them.

        Returns:
            Tuple of (count_updated, detail_lines).
        """
        from kuzu_memory.core.models import KnowledgeType

        query = """
        MATCH (m:Memory)
        WHERE m.knowledge_type = 'note'
          AND m.importance >= 0.5
        RETURN m.id AS id, m.content AS content
        ORDER BY m.importance DESC
        LIMIT $limit
        """
        rows = self.adapter.execute_query(query, {"limit": limit})
        updated = 0
        details: list[str] = []

        for row in rows:
            mem_id = row.get("id")
            content = row.get("content", "")
            if not mem_id or not content:
                continue

            try:
                response = (
                    self._llm(
                        self._CLASSIFY_SYSTEM,
                        content[:500],  # Truncate for small models
                        max_tokens=16,
                    )
                    .lower()
                    .split()[0]
                )  # Take first word only

                # Validate against enum values
                valid = {kt.value for kt in KnowledgeType}
                kt = response if response in valid else "note"

                if kt != "note" and not dry_run:
                    self.adapter.execute_query(
                        "MATCH (m:Memory {id: $id}) SET m.knowledge_type = $kt",
                        {"id": mem_id, "kt": kt},
                    )
                    updated += 1
                    details.append(f"  {mem_id[:8]}\u2026 \u2192 {kt}")
            except Exception as e:
                logger.debug("Reclassify failed for %s: %s", mem_id, e)

        return updated, details

    # ------------------------------------------------------------------
    # Pass 3: re-score default importance
    # ------------------------------------------------------------------

    def rescore_pass(
        self,
        limit: int = 30,
        dry_run: bool = False,
    ) -> tuple[int, list[str]]:
        """
        Find memories with default importance (0.5) and re-evaluate.

        Returns:
            Tuple of (count_updated, detail_lines).
        """
        query = """
        MATCH (m:Memory)
        WHERE m.importance = 0.5
          AND m.source_type <> 'consolidation'
        RETURN m.id AS id, m.content AS content
        ORDER BY m.created_at DESC
        LIMIT $limit
        """
        rows = self.adapter.execute_query(query, {"limit": limit})
        updated = 0
        details: list[str] = []

        for row in rows:
            mem_id = row.get("id")
            content = row.get("content", "")
            if not mem_id or not content:
                continue

            try:
                response = self._llm(
                    self._IMPORTANCE_SYSTEM,
                    content[:400],
                    max_tokens=8,
                )
                # Parse first float-like token
                score_str = response.strip().split()[0].rstrip(".,;")
                score = float(score_str)
                score = max(0.0, min(1.0, score))

                if score != 0.5 and not dry_run:
                    self.adapter.execute_query(
                        "MATCH (m:Memory {id: $id}) SET m.importance = $score",
                        {"id": mem_id, "score": score},
                    )
                    updated += 1
                    details.append(f"  {mem_id[:8]}\u2026 importance 0.5 \u2192 {score:.2f}")
            except Exception as e:
                logger.debug("Rescore failed for %s: %s", mem_id, e)

        return updated, details

    def run_all_passes(
        self,
        limit: int = 50,
        dry_run: bool = False,
    ) -> LLMOptimizationResult:
        """Run all three optimization passes. Designed for background thread execution."""
        start = time.time()
        details: list[str] = []

        reclassified, rc_details = self.reclassify_pass(limit=limit, dry_run=dry_run)
        details.extend(rc_details)

        rescored, rs_details = self.rescore_pass(limit=min(limit, 30), dry_run=dry_run)
        details.extend(rs_details)

        return LLMOptimizationResult(
            success=True,
            summaries_generated=0,  # Summaries are per-cluster, called from _optimize_llm
            memories_reclassified=reclassified,
            memories_rescored=rescored,
            execution_time_ms=(time.time() - start) * 1000,
            model_used=self.model,
            provider="local",
            dry_run=dry_run,
            details=details,
        )
