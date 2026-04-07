"""
TF-IDF keyword enricher.

Populates Keyword nodes and HAS_KEYWORD edges between Memory nodes and their
significant keywords, storing per-edge TF-IDF scores.  Replaces the O(N)
content scan in KeywordRecallStrategy with an O(1) graph lookup once this
enricher has run.

Architecture constraints:
- Pure Python tokenisation only — no NLP deps (spacy, nltk, etc.).
- All DB writes go through KuzuAdapter.execute_query() (_write_lock).
- Background-only: never blocks recall or ingestion.
- Fully idempotent via MERGE semantics.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter
from typing import TYPE_CHECKING

from .base import BaseEnricher, EnrichmentResult

if TYPE_CHECKING:
    from ..core.config import KuzuMemoryConfig
    from ..storage.kuzu_adapter import KuzuAdapter

logger = logging.getLogger(__name__)

# Batch size for processing memories.  Larger batches reduce query round-trips
# at the cost of higher peak memory usage.
_BATCH_SIZE = 50

# Minimum token length and stopword list.  Kept here (not in config) to keep
# this module self-contained and avoid coupling to ExtractionConfig changes.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "then",
        "once",
        "and",
        "but",
        "or",
        "nor",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "not",
        "no",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "what",
        "which",
        "who",
        "when",
        "where",
        "why",
        "how",
    }
)


def tokenize(text: str) -> list[str]:
    """Tokenise *text* into lowercase alpha tokens of 3+ characters.

    Removes stopwords, punctuation, and digits.  Returns tokens in the order
    they appear in the text (duplicates preserved for TF computation).

    Args:
        text: Raw content string.

    Returns:
        List of lowercase alpha tokens (3+ chars, non-stopword).
    """
    words = re.findall(r"[a-z]{3,}", text.lower())
    return [w for w in words if w not in STOPWORDS]


class TFIDFKeywordEnricher(BaseEnricher):
    """Populate Keyword nodes and HAS_KEYWORD edges with TF-IDF scores.

    Algorithm:
    1. Fetch all active memories (valid_to IS NULL or in the future).
    2. Tokenise each memory's content with :func:`tokenize`.
    3. Compute per-document TF: ``count(word, doc) / len(doc_tokens)``.
    4. Compute corpus IDF: ``log(N / (1 + df(word)))`` where N = total docs
       and df = number of docs containing the word.
    5. MERGE Keyword nodes (sets idf, total_mentions).
    6. MERGE HAS_KEYWORD edges (sets tf, tfidf) in batches of _BATCH_SIZE.

    The enricher is fully idempotent — re-running updates existing scores.
    Errors are captured per-step; a failure to MERGE one batch does not abort
    the others.
    """

    @property
    def name(self) -> str:
        return "tfidf_keyword"

    def enrich(
        self,
        adapter: KuzuAdapter,
        config: KuzuMemoryConfig,
    ) -> EnrichmentResult:
        """Run the TF-IDF keyword enricher.

        Args:
            adapter: Initialised KuzuAdapter for all DB access.
            config: KuzuMemory configuration (unused currently, reserved for
                    future batch-size config).

        Returns:
            EnrichmentResult with nodes_updated (keyword count) and
            edges_created (HAS_KEYWORD edge count).  Never raises.
        """
        start = time.monotonic()
        result = EnrichmentResult(name=self.name)

        try:
            keyword_count, edge_count = self._run_tfidf(adapter)
            result.nodes_updated = keyword_count
            result.edges_created = edge_count
        except Exception as exc:
            logger.warning(
                "TFIDFKeywordEnricher failed (non-fatal): %s",
                exc,
                exc_info=True,
            )
            result.error = str(exc)

        result.duration_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "TFIDFKeywordEnricher: keywords=%d  edges=%d  error=%s  (%.1f ms)",
            result.nodes_updated,
            result.edges_created,
            result.error,
            result.duration_ms,
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_tfidf(self, adapter: KuzuAdapter) -> tuple[int, int]:
        """Core TF-IDF computation and MERGE logic.

        Returns:
            (keyword_count, edge_count) tuple.

        Raises:
            RuntimeError: If the initial memory fetch fails entirely.
        """
        # Step 1: Fetch all active memories.
        fetch_query = """
            MATCH (m:Memory)
            WHERE m.valid_to IS NULL OR m.valid_to > timestamp('1970-01-01 00:00:00')
            RETURN m.id AS id, m.content AS content
        """
        try:
            rows = adapter.execute_query(fetch_query)
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch memories for TF-IDF: {exc}") from exc

        if not rows:
            logger.debug("TFIDFKeywordEnricher: no active memories found, skipping")
            return 0, 0

        # Build per-document token lists.
        # doc_tokens: memory_id -> list of tokens (with repetition for TF)
        doc_tokens: dict[str, list[str]] = {}
        for row in rows:
            mem_id = str(row.get("id") or "")
            content = str(row.get("content") or "")
            if mem_id and content:
                doc_tokens[mem_id] = tokenize(content)

        if not doc_tokens:
            return 0, 0

        n_docs = len(doc_tokens)

        # Step 2: Compute TF per document.
        # tf_map: memory_id -> {word -> tf_score}
        tf_map: dict[str, dict[str, float]] = {}
        for mem_id, tokens in doc_tokens.items():
            if not tokens:
                tf_map[mem_id] = {}
                continue
            counter = Counter(tokens)
            total = len(tokens)
            tf_map[mem_id] = {word: count / total for word, count in counter.items()}

        # Step 3: Compute document frequency and IDF.
        # df_map: word -> number of documents containing the word
        df_map: dict[str, int] = Counter(
            word for token_dict in tf_map.values() for word in token_dict
        )
        idf_map: dict[str, float] = {
            word: math.log(n_docs / (1 + df)) for word, df in df_map.items()
        }

        # Step 4: MERGE Keyword nodes.
        keyword_count = self._merge_keyword_nodes(adapter, idf_map, df_map)

        # Step 5: MERGE HAS_KEYWORD edges in batches.
        edge_count = self._merge_keyword_edges(adapter, tf_map, idf_map)

        return keyword_count, edge_count

    def _merge_keyword_nodes(
        self,
        adapter: KuzuAdapter,
        idf_map: dict[str, float],
        df_map: dict[str, int],
    ) -> int:
        """MERGE Keyword nodes with updated idf and total_mentions.

        Args:
            adapter: KuzuAdapter for query execution.
            idf_map: word -> IDF score.
            df_map: word -> document frequency (total_mentions).

        Returns:
            Number of keywords merged (len of idf_map).
        """
        merge_keyword_query = (
            "MERGE (k:Keyword {word: $word}) "
            "SET k.idf = $idf, k.total_mentions = $total_mentions"
        )
        merged = 0
        for word, idf_val in idf_map.items():
            try:
                adapter.execute_query(
                    merge_keyword_query,
                    {
                        "word": word,
                        "idf": float(idf_val),
                        "total_mentions": int(df_map.get(word, 0)),
                    },
                )
                merged += 1
            except Exception as exc:
                logger.debug("Failed to merge Keyword node '%s': %s", word, exc)

        return merged

    def _merge_keyword_edges(
        self,
        adapter: KuzuAdapter,
        tf_map: dict[str, dict[str, float]],
        idf_map: dict[str, float],
    ) -> int:
        """MERGE HAS_KEYWORD edges in batches of _BATCH_SIZE memories.

        Args:
            adapter: KuzuAdapter for query execution.
            tf_map: memory_id -> {word -> tf_score}.
            idf_map: word -> IDF score.

        Returns:
            Total number of edges merged.
        """
        merge_edge_query = (
            "MATCH (m:Memory {id: $memory_id}), (k:Keyword {word: $word}) "
            "MERGE (m)-[hk:HAS_KEYWORD]->(k) "
            "SET hk.tf = $tf, hk.tfidf = $tfidf"
        )

        mem_ids = list(tf_map.keys())
        edge_count = 0

        for batch_start in range(0, len(mem_ids), _BATCH_SIZE):
            batch = mem_ids[batch_start : batch_start + _BATCH_SIZE]
            for mem_id in batch:
                word_tf = tf_map[mem_id]
                for word, tf_val in word_tf.items():
                    idf_val = idf_map.get(word, 0.0)
                    tfidf_val = tf_val * idf_val
                    try:
                        adapter.execute_query(
                            merge_edge_query,
                            {
                                "memory_id": mem_id,
                                "word": word,
                                "tf": float(tf_val),
                                "tfidf": float(tfidf_val),
                            },
                        )
                        edge_count += 1
                    except Exception as exc:
                        logger.debug(
                            "Failed to merge HAS_KEYWORD edge m=%s w=%s: %s",
                            mem_id,
                            word,
                            exc,
                        )

        return edge_count
