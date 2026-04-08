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

# Batch size for UNWIND edge merge batches.  With UNWIND, each batch is a
# single query, so larger batches dramatically reduce round-trips.  5000
# edges per batch handles even the largest haystack (500 sessions x ~50
# unique keywords) in 1-2 queries.
_BATCH_SIZE = 5000

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

        Uses a single UNWIND query to batch all keyword nodes in one DB
        round-trip, replacing the previous per-keyword loop.

        Args:
            adapter: KuzuAdapter for query execution.
            idf_map: word -> IDF score.
            df_map: word -> document frequency (total_mentions).

        Returns:
            Number of keywords submitted for merge (len of idf_map).
        """
        if not idf_map:
            return 0

        keywords = [
            {
                "word": word,
                "idf": float(idf_val),
                "total_mentions": int(df_map.get(word, 0)),
            }
            for word, idf_val in idf_map.items()
        ]

        # Single UNWIND query — one write-lock acquisition for all keywords.
        bulk_keyword_query = (
            "UNWIND $keywords AS kw "
            "MERGE (k:Keyword {word: kw.word}) "
            "SET k.idf = kw.idf, k.total_mentions = kw.total_mentions"
        )
        try:
            adapter.execute_query(bulk_keyword_query, {"keywords": keywords})
        except Exception as exc:
            logger.warning("Bulk Keyword MERGE failed, falling back to per-item: %s", exc)
            # Per-item fallback so partial failures don't abort everything.
            count = 0
            for kw in keywords:
                try:
                    adapter.execute_query(
                        "MERGE (k:Keyword {word: $word}) "
                        "SET k.idf = $idf, k.total_mentions = $total_mentions",
                        kw,
                    )
                    count += 1
                except Exception as exc2:
                    logger.debug("Failed to merge Keyword node '%s': %s", kw["word"], exc2)
            return count

        return len(keywords)

    def _merge_keyword_edges(
        self,
        adapter: KuzuAdapter,
        tf_map: dict[str, dict[str, float]],
        idf_map: dict[str, float],
    ) -> int:
        """MERGE HAS_KEYWORD edges in batches of _BATCH_SIZE edges.

        Uses UNWIND to batch multiple (memory, keyword) edge MERGEs into a
        single write-lock acquisition per batch, replacing the previous
        per-edge query loop.

        Args:
            adapter: KuzuAdapter for query execution.
            tf_map: memory_id -> {word -> tf_score}.
            idf_map: word -> IDF score.

        Returns:
            Total number of edges merged.
        """
        # Flatten all (memory_id, word, tf, tfidf) tuples into a single list.
        all_edges: list[dict[str, object]] = []
        for mem_id, word_tf in tf_map.items():
            for word, tf_val in word_tf.items():
                idf_val = idf_map.get(word, 0.0)
                all_edges.append(
                    {
                        "memory_id": mem_id,
                        "word": word,
                        "tf": float(tf_val),
                        "tfidf": float(tf_val * idf_val),
                    }
                )

        if not all_edges:
            return 0

        bulk_edge_query = (
            "UNWIND $edges AS e "
            "MATCH (m:Memory {id: e.memory_id}), (k:Keyword {word: e.word}) "
            "MERGE (m)-[hk:HAS_KEYWORD]->(k) "
            "SET hk.tf = e.tf, hk.tfidf = e.tfidf"
        )

        edge_count = 0
        for batch_start in range(0, len(all_edges), _BATCH_SIZE):
            batch = all_edges[batch_start : batch_start + _BATCH_SIZE]
            try:
                adapter.execute_query(bulk_edge_query, {"edges": batch})
                edge_count += len(batch)
            except Exception as exc:
                logger.warning(
                    "Bulk HAS_KEYWORD MERGE failed for batch starting at %d, "
                    "falling back to per-item writes: %s",
                    batch_start,
                    exc,
                )
                # Per-item fallback for this batch.
                per_item_query = (
                    "MATCH (m:Memory {id: $memory_id}), (k:Keyword {word: $word}) "
                    "MERGE (m)-[hk:HAS_KEYWORD]->(k) "
                    "SET hk.tf = $tf, hk.tfidf = $tfidf"
                )
                for edge in batch:
                    try:
                        adapter.execute_query(per_item_query, edge)
                        edge_count += 1
                    except Exception as exc2:
                        logger.debug(
                            "Failed to merge HAS_KEYWORD edge m=%s w=%s: %s",
                            edge["memory_id"],
                            edge["word"],
                            exc2,
                        )

        return edge_count
