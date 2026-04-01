"""
Rule-based knowledge type classifier for automatic memory categorization.

Classifies content into KnowledgeType values using keyword matching and regex
patterns. Designed for use at ingestion time (hooks, MCP tools, service layer).

Architectural constraint: MUST be fast (< 1ms per call). No ML models, no
embeddings, no external calls — pure Python regex/keyword matching only.

Classification order:
  1. Explicit prefix labels ("Rule:", "Gotcha:", etc.) — highest priority
  2. Keyword / pattern matching in order: rule → gotcha → architecture → pattern → convention
  3. Default: "note"

Checking prefixes before keywords ensures that e.g. "Gotcha: enforces single-writer"
is labelled 'gotcha' even though "enforces" would otherwise trigger 'rule'.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Pre-compiled regex patterns (compiled once at module load for performance)
# ---------------------------------------------------------------------------

_RE_FLAGS = re.IGNORECASE

# --- Prefix matchers (high-priority; checked before keyword scanning) -------

_RULE_PREFIX = re.compile(r"^\s*(?:rule)\s*:", _RE_FLAGS)
_GOTCHA_PREFIX = re.compile(r"^\s*(?:bug|fix|gotcha)\s*:", _RE_FLAGS)
_ARCH_PREFIX = re.compile(r"^\s*(?:architecture|design)\s*:", _RE_FLAGS)
_PATTERN_PREFIX = re.compile(r"^\s*(?:pattern|approach)\s*:", _RE_FLAGS)
_CONVENTION_PREFIX = re.compile(r"^\s*(?:convention|standard)\s*:", _RE_FLAGS)

# --- Keyword matchers --------------------------------------------------------

# 1. RULE — hard constraints
_RULE_KEYWORDS = re.compile(
    r"\b("
    r"always|never|must not|must|required|mandatory|"
    r"do not|don't ever|enforce[sd]?|strict(?:ly)?|"
    r"forbidden|prohibited"
    r")\b",
    _RE_FLAGS,
)

# 2. GOTCHA — bugs / surprises
_GOTCHA_KEYWORDS = re.compile(
    r"\b("
    r"bug|gotcha|watch out|careful|warning|caveat|pitfall|"
    r"broke|broken|crash(?:ed|es)?|deadlock|race condition|"
    r"unexpected(?:ly)?|surprisingly|counter.intuitive"
    r")\b",
    _RE_FLAGS,
)

# 3. ARCHITECTURE — structural decisions
_ARCH_KEYWORDS = re.compile(
    r"\b("
    r"architecture|design decision|we decided|chose to|trade.off|"
    r"SOA|dependency injection|microservice[s]?|monolith|"
    r"service layer|component|module boundary"
    r")\b",
    _RE_FLAGS,
)
# "layer", "module", "service", "component" need a nearby decision verb to qualify
_ARCH_CONTEXT = re.compile(
    r"\b(layer|module|service|component)\b.{0,40}\b(decision|chose|decided|design|structure)\b",
    _RE_FLAGS | re.DOTALL,
)

# 4. PATTERN — repeatable solutions
#    "use X for" is narrowed to "use <tool/library> for" to avoid matching
#    conversational "we use pytest for..." which belongs to convention.
_PATTERN_KEYWORDS = re.compile(
    r"\b("
    r"pattern|approach|technique|strategy|workflow|"
    r"best practice[s]?|template|recipe|boilerplate|"
    r"prefer .{1,30} over"
    r")\b",
    _RE_FLAGS,
)

# 5. CONVENTION — style / workflow standards
_CONVENTION_KEYWORDS = re.compile(
    r"\b("
    r"convention|style guide|formatting|naming convention|"
    r"coding standard[s]?|code review|commit message[s]?|"
    r"we use|our standard|project uses"
    r")\b",
    _RE_FLAGS,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_knowledge_type(content: str) -> str:
    """
    Classify content into a KnowledgeType value using rule-based matching.

    Checks patterns in two passes:
      Pass 1 — explicit prefix labels (highest priority):
        Rule: → rule
        Bug: / Fix: / Gotcha: → gotcha
        Architecture: / Design: → architecture
        Pattern: / Approach: → pattern
        Convention: / Standard: → convention

      Pass 2 — keyword scanning in order (first match wins):
        rule → gotcha → architecture → pattern → convention → note (default)

    Args:
        content: The memory content string to classify.

    Returns:
        One of: "rule", "gotcha", "architecture", "pattern", "convention", "note".

    Performance:
        O(1) — fixed number of regex scans regardless of DB size.
        Typical call time < 1 ms for content up to 10 KB.

    Examples:
        >>> classify_knowledge_type("You must always use the context manager")
        'rule'
        >>> classify_knowledge_type("Gotcha: enforces single-writer")
        'gotcha'
        >>> classify_knowledge_type("We decided on SOA with dependency injection")
        'architecture'
        >>> classify_knowledge_type("Pattern: use retry with exponential backoff")
        'pattern'
        >>> classify_knowledge_type("Convention: Google-style docstrings everywhere")
        'convention'
        >>> classify_knowledge_type("Today I worked on the auth module")
        'note'
    """
    if not content or not content.strip():
        return "note"

    # ------------------------------------------------------------------
    # Pass 1: Explicit prefix labels override all keyword scanning.
    # Checked in the same priority order as pass 2 so that e.g.
    # "Rule: ..." still wins over "Gotcha: ...".
    # ------------------------------------------------------------------
    if _RULE_PREFIX.match(content):
        return "rule"
    if _GOTCHA_PREFIX.match(content):
        return "gotcha"
    if _ARCH_PREFIX.match(content):
        return "architecture"
    if _PATTERN_PREFIX.match(content):
        return "pattern"
    if _CONVENTION_PREFIX.match(content):
        return "convention"

    # ------------------------------------------------------------------
    # Pass 2: Keyword / pattern matching (first match wins).
    # ------------------------------------------------------------------

    # 1. RULE
    if _RULE_KEYWORDS.search(content):
        return "rule"

    # 2. GOTCHA
    if _GOTCHA_KEYWORDS.search(content):
        return "gotcha"

    # 3. ARCHITECTURE
    if _ARCH_KEYWORDS.search(content) or _ARCH_CONTEXT.search(content):
        return "architecture"

    # 4. PATTERN
    if _PATTERN_KEYWORDS.search(content):
        return "pattern"

    # 5. CONVENTION
    if _CONVENTION_KEYWORDS.search(content):
        return "convention"

    # 6. Default
    return "note"


def classify_if_unset(content: str, current_knowledge_type: str | None) -> str:
    """
    Return an auto-classified knowledge type only when the caller has not
    explicitly provided one (or provided the default "note").

    Args:
        content: Memory content to classify.
        current_knowledge_type: Caller-supplied value (may be None or "note").

    Returns:
        The existing value if it is meaningful (not None / not "note"),
        otherwise the auto-classified value.

    Examples:
        >>> classify_if_unset("Always use context managers", None)
        'rule'
        >>> classify_if_unset("Always use context managers", "architecture")
        'architecture'
        >>> classify_if_unset("Some content", "note")
        'note'
    """
    if current_knowledge_type and current_knowledge_type.lower() not in ("note", ""):
        return current_knowledge_type
    return classify_knowledge_type(content)
