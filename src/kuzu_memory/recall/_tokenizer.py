"""
Shared tokenizer for recall modules.

Extracted from :mod:`kuzu_memory.enrichment.tfidf_keyword` to avoid
circular imports when the same tokenisation logic is needed inside
:mod:`kuzu_memory.recall.coordinator`.

Do not import from enrichment here — this module must remain leaf-level.
"""

from __future__ import annotations

import re

# Re-exported so callers can import STOPWORDS from here if needed.
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

    This function is intentionally identical to
    :func:`kuzu_memory.enrichment.tfidf_keyword.tokenize` so that boost
    queries use the same vocabulary as the index.

    Args:
        text: Raw content string.

    Returns:
        List of lowercase alpha tokens (3+ chars, non-stopword).
    """
    words = re.findall(r"[a-z]{3,}", text.lower())
    return [w for w in words if w not in STOPWORDS]
