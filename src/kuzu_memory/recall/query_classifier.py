"""Query speaker intent classifier for recall routing.

Classifies a retrieval query as asking about:
- USER_TURN: what the user said/mentioned/asked
- ASSISTANT_TURN: what the assistant said/recommended/explained
- UNSPECIFIED: no clear speaker signal (default — no filtering applied)

Zero external dependencies — only ``re`` and ``enum`` from stdlib.
"""

from __future__ import annotations

import re
from enum import Enum


class SpeakerIntent(str, Enum):
    """Speaker intent classification for retrieval queries."""

    USER_TURN = "user"
    ASSISTANT_TURN = "assistant"
    UNSPECIFIED = "unspecified"


# Patterns where the querier is asking about their own past utterances
_USER_PATTERNS = [
    r"\b(?:what|when|where|how|why|did)\s+(?:did\s+)?i\s+(?:say|tell|mention|ask|share|note|write|type|explain|describe|talk)",
    r"\bi(?:'ve|'d)?\s+(?:said|told|mentioned|asked|shared|noted|explained|described|talked)",
    r"\bwhat\s+i\s+(?:said|told|mentioned|asked|shared|noted)",
    r"\bmy\s+(?:question|request|message|comment|note|statement|response|reply)",
    r"\bwhen\s+i\s+(?:said|mentioned|asked|told|shared)",
    r"\bsomething\s+i\s+(?:said|mentioned|asked|told|shared)",
    r"\bi\s+(?:asked|mentioned|said|noted|told\s+you)\s+(?:about|that|earlier|before|previously)",
    r"\bdo\s+you\s+remember\s+(?:when\s+)?i\s+(?:said|told|mentioned|asked)",
]

# Patterns where the querier is asking about what the assistant said/did
_ASSISTANT_PATTERNS = [
    r"\b(?:what|when|where|how|why|did)\s+you\s+(?:say|tell|mention|suggest|recommend|explain|describe|advise|answer)",
    r"\byou(?:'ve|'d)?\s+(?:said|told|mentioned|suggested|recommended|explained|described|advised)",
    r"\bwhat\s+(?:did\s+)?you\s+(?:say|tell|mention|suggest|recommend|advise|answer)",
    r"\byour\s+(?:recommendation|suggestion|advice|answer|response|reply|explanation|guidance)",
    r"\bwhat\s+(?:was|were)\s+your\s+(?:recommendation|suggestion|advice|answer|response)",
    r"\byou\s+(?:recommended|suggested|advised|told\s+me|explained|said)\s+(?:that|to|me|about|earlier|before)",
    r"\bdo\s+you\s+remember\s+(?:what\s+)?you\s+(?:said|told|mentioned|suggested|recommended)",
    r"\bwhat\s+you\s+(?:said|suggested|recommended|advised|explained)\s+(?:about|earlier|before|previously)",
]

_USER_RE = re.compile("|".join(_USER_PATTERNS), re.IGNORECASE)
_ASSISTANT_RE = re.compile("|".join(_ASSISTANT_PATTERNS), re.IGNORECASE)


def classify_speaker_intent(query: str) -> SpeakerIntent:
    """Classify a query as asking about user utterances, assistant utterances, or unspecified.

    Uses regex pattern matching on first/second-person pronouns combined with
    verbs of saying/communicating. When both patterns match, returns UNSPECIFIED
    (ambiguous query).

    Args:
        query: The raw retrieval query string.

    Returns:
        SpeakerIntent enum value.

    Examples:
        >>> classify_speaker_intent("What did I say about Python async?")
        <SpeakerIntent.USER_TURN: 'user'>
        >>> classify_speaker_intent("What did you recommend for database choice?")
        <SpeakerIntent.ASSISTANT_TURN: 'assistant'>
        >>> classify_speaker_intent("Tell me about Python async patterns")
        <SpeakerIntent.UNSPECIFIED: 'unspecified'>
    """
    user_match = bool(_USER_RE.search(query))
    assistant_match = bool(_ASSISTANT_RE.search(query))

    if user_match and not assistant_match:
        return SpeakerIntent.USER_TURN
    if assistant_match and not user_match:
        return SpeakerIntent.ASSISTANT_TURN
    return SpeakerIntent.UNSPECIFIED
