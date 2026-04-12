"""Local LLM reranker for memory retrieval."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from kuzu_memory.core.config import LocalLLMConfig

if TYPE_CHECKING:
    from kuzu_memory.core.models import Memory

logger = logging.getLogger(__name__)

_RERANK_SYSTEM = (
    "You are a memory relevance scorer. "
    "Given a user query and a list of memories (each prefixed with an index), "
    "return ONLY the indices of the most relevant memories in order of relevance, "
    "as a comma-separated list. Example: 2,0,4,1"
)


class LocalLLMReranker:
    """Reranks memory candidates using a local LLM (Ollama/LM Studio).

    Falls back gracefully to the original ordering when the LLM is unavailable
    or returns an unexpected response format.

    Args:
        config: LocalLLMConfig controlling endpoint, model, and timeouts.
    """

    def __init__(self, config: LocalLLMConfig) -> None:
        self.config = config
        self._endpoint = config.endpoint
        self._model = config.model
        # Resolve endpoint/model from live detection when model is not configured
        if not self._model:
            from kuzu_memory.integrations.local_llm import detect_local_llm

            info = detect_local_llm()
            if info.available:
                self._endpoint = info.endpoint
                self._model = info.default_model

    def rerank(self, query: str, memories: list[Memory], top_k: int) -> list[Memory]:
        """Rerank memories by relevance to query using the local LLM.

        Args:
            query: The user query used to assess relevance.
            memories: Candidate memories in their current ranked order.
            top_k: Maximum number of memories to return.

        Returns:
            Memories reordered by LLM-assessed relevance, truncated to top_k.
            Returns memories[:top_k] unchanged on error or when no model is available.
        """
        if not memories or not self._model:
            return memories[:top_k]

        numbered = "\n".join(f"{i}: {m.content[:200]}" for i, m in enumerate(memories))
        user_msg = f"Query: {query}\n\nMemories:\n{numbered}"

        try:
            from kuzu_memory.integrations.local_llm import chat_completion

            response = chat_completion(
                endpoint=self._endpoint,
                model=self._model,
                messages=[
                    {"role": "system", "content": _RERANK_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                timeout=self.config.timeout_ms / 1000,
                max_tokens=64,
            )
            indices = [int(x.strip()) for x in response.split(",") if x.strip().isdigit()]
            reranked = [memories[i] for i in indices if i < len(memories)]
            # Append any memories not mentioned by the LLM to preserve completeness
            seen = set(indices)
            reranked += [m for i, m in enumerate(memories) if i not in seen]
            return reranked[:top_k]
        except Exception as e:
            logger.warning("LocalLLMReranker failed, returning original order: %s", e)
            return memories[:top_k]
