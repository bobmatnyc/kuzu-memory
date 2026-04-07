"""
Optional LLM reranking pass for KuzuMemory recall results.

Uses a fast Claude Haiku model to reorder the top-K candidates returned by the
graph/HNSW strategies.  The ranker is opt-in (config.recall.reranking.enabled)
and MCP-path only — it must never be called from git hook paths.

Failure modes are all handled gracefully: if the anthropic SDK is absent, the
API times out, or any other error occurs, the original candidate order is
returned unchanged.  The caller always gets a valid list back.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import TYPE_CHECKING

from ..core.models import Memory

if TYPE_CHECKING:
    from ..core.config import RerankingConfig

logger = logging.getLogger(__name__)


class LLMReranker:
    """Optional Haiku reranking pass for recalled memories.

    Requires the ``anthropic`` SDK; disables itself gracefully when the SDK is
    absent or when ``config.enabled`` is ``False``.

    This class is intentionally stateless — it reads the API key from the
    ``ANTHROPIC_API_KEY`` environment variable (the Anthropic SDK default).
    No key is stored in the kuzu-memory config.

    Example::

        cfg = RerankingConfig(enabled=True, model="claude-haiku-4-5")
        reranker = LLMReranker(cfg)
        ranked = reranker.rerank("how do I configure logging?", candidates, limit=5)
    """

    def __init__(self, config: RerankingConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rerank(self, query: str, candidates: list[Memory], limit: int) -> list[Memory]:
        """Rerank *candidates* using an LLM and return at most *limit* results.

        If reranking is disabled, the SDK is unavailable, the request times out,
        or any other error occurs, the original ordering (``candidates[:limit]``)
        is returned unchanged.  This method never raises.

        Args:
            query: The user's recall query string.
            candidates: Memories already ranked by the graph/HNSW strategies.
            limit: Maximum number of memories to return.

        Returns:
            Re-ordered list of at most *limit* memories, best-match first.
        """
        if not self._config.enabled:
            return candidates[:limit]

        if not candidates:
            return []

        try:
            return self._rerank_with_llm(query, candidates, limit)
        except Exception as exc:
            logger.debug("LLMReranker: falling back to original order: %s", exc)
            return candidates[:limit]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rerank_with_llm(self, query: str, candidates: list[Memory], limit: int) -> list[Memory]:
        """Call the Anthropic API in a thread with a timeout guard.

        Raises on any error so that ``rerank()`` can catch-all and fall back.
        """
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("anthropic SDK not installed") from exc

        top_k = min(self._config.top_k_to_rerank, len(candidates))
        to_rank = candidates[:top_k]

        prompt = self._build_prompt(query, to_rank)
        timeout_secs = self._config.timeout_ms / 1000.0

        def _call() -> str:
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=self._config.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract text from first content block
            block = response.content[0]
            return str(block.text)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call)
            try:
                raw_text = future.result(timeout=timeout_secs)
            except FuturesTimeoutError as exc:
                raise TimeoutError(f"LLM rerank timed out after {timeout_secs}s") from exc

        return self._apply_ranking(raw_text, candidates, limit)

    def _build_prompt(self, query: str, candidates: list[Memory]) -> str:
        """Build the reranking prompt sent to the LLM."""
        memory_list = [{"id": m.id, "content": m.content[:200]} for m in candidates]
        memories_json = json.dumps(memory_list, ensure_ascii=False)
        return (
            f'Given the query: "{query}"\n'
            "Rank these memory excerpts by relevance (most relevant first).\n"
            "Return ONLY a JSON array of memory IDs in ranked order, nothing else.\n"
            'Example: ["id1", "id2", "id3"]\n\n'
            f"Memories:\n{memories_json}"
        )

    def _apply_ranking(
        self,
        llm_response: str,
        candidates: list[Memory],
        limit: int,
    ) -> list[Memory]:
        """Parse LLM output and reconstruct the memory list in the new order.

        Rules:
        - IDs returned by the LLM that are not in *candidates* are ignored.
        - Candidates not mentioned by the LLM are appended at the end.
        - The result is truncated to *limit*.
        """
        # Parse the JSON array from the response
        id_order = self._parse_id_list(llm_response)

        # Build an index for O(1) lookup
        candidate_by_id: dict[str, Memory] = {m.id: m for m in candidates}

        result: list[Memory] = []
        seen: set[str] = set()

        for mid in id_order:
            if mid in candidate_by_id and mid not in seen:
                result.append(candidate_by_id[mid])
                seen.add(mid)

        # Append any candidates the LLM omitted (preserving original order)
        for m in candidates:
            if m.id not in seen:
                result.append(m)

        return result[:limit]

    @staticmethod
    def _parse_id_list(text: str) -> list[str]:
        """Extract a JSON array of ID strings from the LLM response text.

        Returns an empty list on any parse failure.
        """
        text = text.strip()
        # Find the first '[' and last ']' to handle surrounding prose
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            logger.debug("LLMReranker: could not find JSON array in response: %r", text[:200])
            return []
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item]
        except json.JSONDecodeError as exc:
            logger.debug("LLMReranker: JSON parse error: %s", exc)
        return []
