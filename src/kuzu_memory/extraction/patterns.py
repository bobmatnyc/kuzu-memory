"""
Enhanced pattern-based memory extraction for KuzuMemory.

Implements comprehensive regex patterns for extracting different types of memories
from text without requiring LLM calls. Includes pre-compilation for performance
and sophisticated pattern matching for various memory types.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from ..core.models import ExtractedMemory, MemoryType
from ..utils.validation import validate_text_input

logger = logging.getLogger(__name__)


@dataclass
class PatternMatch:
    """Represents a pattern match with metadata."""

    content: str
    confidence: float
    memory_type: MemoryType
    pattern_name: str
    start_pos: int
    end_pos: int


class PatternExtractor:
    """
    Enhanced pattern-based memory extractor with comprehensive regex patterns.

    Extracts memories using sophisticated regex patterns without requiring LLM calls.
    Patterns are pre-compiled for performance and organized by memory type.
    """

    def __init__(
        self,
        enable_compilation: bool = True,
        custom_patterns: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize pattern extractor.

        Args:
            enable_compilation: Whether to pre-compile regex patterns for performance
            custom_patterns: Optional custom patterns to add/override defaults
        """
        self.enable_compilation = enable_compilation
        self.custom_patterns = custom_patterns or {}

        # Define comprehensive pattern sets
        self._define_patterns()

        # Compile patterns if enabled
        if self.enable_compilation:
            self._compile_patterns()

        # Statistics
        self._extraction_stats: dict[str, Any] = {
            "total_extractions": 0,
            "patterns_matched": {},
            "memory_types_extracted": {},
        }

    def _define_patterns(self) -> None:
        """Define comprehensive regex patterns for memory extraction."""

        # Explicit memory patterns - highest confidence
        self.REMEMBER_PATTERNS = [
            (r"[Rr]emember that (.*?)(?:\.|$|!|\?)", 0.95, "explicit_remember"),
            (r"[Dd]on't forget (?:that )?(.*?)(?:\.|$|!|\?)", 0.95, "dont_forget"),
            (
                r"[Ff]or (?:future )?reference[,:]?\s*(.*?)(?:\.|$|!|\?)",
                0.90,
                "for_reference",
            ),
            (r"[Kk]eep in mind (?:that )?(.*?)(?:\.|$|!|\?)", 0.90, "keep_in_mind"),
            (r"[Nn]ote that (.*?)(?:\.|$|!|\?)", 0.90, "note_that"),
            (r"[Ii]mportant[,:]?\s*(.*?)(?:\.|$|!|\?)", 0.85, "important"),
            (r"[Aa]lways (.*?)(?:\.|$|!|\?)", 0.95, "always"),
            (r"[Nn]ever (.*?)(?:\.|$|!|\?)", 0.95, "never"),
        ]

        # Identity patterns - personal information
        self.IDENTITY_PATTERNS = [
            (r"[Mm]y name is ([A-Z][a-zA-Z\s]+?)(?:\.|$|,|\s+and)", 1.0, "name_is"),
            (r"I'?m ([A-Z][a-zA-Z\s]+?)(?:\.|$|,|\s+and)", 0.95, "im_name"),
            (r"[Cc]all me ([A-Z][a-zA-Z\s]+?)(?:\.|$|,)", 0.95, "call_me"),
            (
                r"I (?:work at|work for|am at|am with) ([A-Z][a-zA-Z0-9\s&.,'-]+?)(?:\.|$|,|\s+as)",
                0.95,
                "work_at",
            ),
            (r"I am (?:a|an) ([a-zA-Z\s]+?)(?:\.|$|,|\s+at)", 0.90, "i_am_role"),
            (r"I'?m (?:a|an) ([a-zA-Z\s]+?)(?:\.|$|,|\s+at)", 0.90, "im_role"),
            (
                r"I (?:live in|am from|am based in) ([A-Z][a-zA-Z\s,]+?)(?:\.|$)",
                0.90,
                "location",
            ),
            (
                r"[Mm]y (?:role|position|job|title) is ([a-zA-Z\s]+?)(?:\.|$|,)",
                0.90,
                "my_role",
            ),
            (r"I'?ve been (?:working as|a) ([a-zA-Z\s]+?) for", 0.85, "working_as"),
        ]

        # Preference patterns - user preferences and settings
        self.PREFERENCE_PATTERNS = [
            (r"I prefer (.*?)(?:\.|$|,|\s+over|\s+to)", 0.95, "i_prefer"),
            (r"I (?:like|love|enjoy) (.*?)(?:\.|$|,)", 0.85, "i_like"),
            (
                r"I (?:don't|do not|dont) (?:like|want|prefer) (.*?)(?:\.|$|,)",
                0.85,
                "i_dont_like",
            ),
            (
                r"[Mm]y favorite (?:.*?) is (.*?)(?:\.|$|,)",
                0.90,
                "my_favorite",
            ),  # Capture the second part (the actual favorite thing)
            (r"I usually (?:use|choose|go with) (.*?)(?:\.|$|,)", 0.80, "i_usually"),
            (r"I typically (.*?)(?:\.|$|,)", 0.80, "i_typically"),
            (
                r"I always (.*?)(?:\.|$|,)",
                0.95,
                "i_always_prefer",
            ),  # Higher confidence for personal preferences
            (
                r"I never (.*?)(?:\.|$|,)",
                0.95,
                "i_never_prefer",
            ),  # Higher confidence for personal preferences
            (
                r"(?:Please|please) (?:always |use |make sure to )?(.*?)(?:\.|$|,)",
                0.80,
                "please_always",
            ),
            (r"[Mm]ake sure (?:to |that )?(.*?)(?:\.|$|,)", 0.85, "make_sure"),
        ]

        # Decision patterns - project and architectural decisions
        self.DECISION_PATTERNS = [
            (
                r"[Ww]e (?:decided|agreed|chose) (?:to |on |that )?(.*?)(?:\.|$|,)",
                0.95,
                "we_decided",
            ),
            (
                r"[Ll]et's (?:go with|use|choose|implement) (.*?)(?:\.|$|,)",
                0.90,
                "lets_use",
            ),
            (
                r"[Ww]e'?(?:ll|re going to) (?:use|go with|implement|choose) (.*?)(?:\.|$|,)",
                0.90,
                "well_use",
            ),
            (
                r"[Tt]he (?:decision|choice) (?:is|was) (?:to )?(.*?)(?:\.|$|,)",
                0.90,
                "decision_is",
            ),
            (
                r"[Ww]e should (?:use|go with|implement|choose) (.*?)(?:\.|$|,)",
                0.85,
                "we_should",
            ),
            (
                r"[Ii]t'?s (?:been )?decided (?:that )?(.*?)(?:\.|$|,)",
                0.90,
                "its_decided",
            ),
            (
                r"[Aa]fter discussion[,]? (?:we )?(.*?)(?:\.|$)",
                0.85,
                "after_discussion",
            ),
        ]

        # Pattern patterns - code patterns and best practices
        self.PATTERN_PATTERNS = [
            (
                r"[Aa]lways (?:use|implement|follow|apply|validate|check|test|ensure) (.*?)(?:\.|$|,)",
                0.90,
                "always_use",
            ),
            (
                r"[Nn]ever (?:use|implement|do|skip|ignore|forget) (.*?)(?:\.|$|,)",
                0.90,
                "never_use",
            ),
            (
                r"[Bb]est practice (?:is )?(?:to )?(.*?)(?:\.|$|,)",
                0.90,
                "best_practice",
            ),
            (
                r"[Ff]ollow (?:the )?pattern (?:of )?(.*?)(?:\.|$|,)",
                0.85,
                "follow_pattern",
            ),
            (
                r"[Uu]se (?:the )?(?:standard|conventional|typical) (.*?)(?:\.|$|,)",
                0.80,
                "use_standard",
            ),
            (r"[Aa]void (.*?)(?:\.|$|,)", 0.85, "avoid"),
            (r"[Mm]ake sure to (.*?)(?:\.|$|,)", 0.80, "make_sure_to"),
        ]

        # Solution patterns - problem-solution pairs
        self.SOLUTION_PATTERNS = [
            (
                r"[Tt]o (?:fix|solve|resolve) (.*?)[,]? (?:use|do|try|implement|restart|run|execute|check) (.*?)(?:\.|$)",
                0.90,
                "to_fix_use",
            ),
            (
                r"[Ii]f (.*?)[,]? (?:then |you should |use |do |try |restart |run )(.*?)(?:\.|$)",
                0.85,
                "if_then",
            ),
            (
                r"[Ww]hen (.*?)[,]? (?:use |do |try |implement |restart |run )(.*?)(?:\.|$)",
                0.85,
                "when_use",
            ),
            (
                r"[Ff]or (.*?)[,]? (?:use |try |implement |restart |run )(.*?)(?:\.|$)",
                0.80,
                "for_use",
            ),
            (
                r"[Tt]he solution (?:to |for )?(.*?) (?:is |was )(.*?)(?:\.|$)",
                0.90,
                "solution_is",
            ),
            (r"[Tt]his (?:fixes|solves|resolves) (.*?)(?:\.|$)", 0.85, "this_fixes"),
        ]

        # Status patterns - current state (short retention)
        self.STATUS_PATTERNS = [
            (
                r"[Cc]urrently (?:working on |doing |implementing )(.*?)(?:\.|$|,)",
                0.80,
                "currently",
            ),
            (r"[Rr]ight now (?:I'?m |we'?re )?(.*?)(?:\.|$|,)", 0.75, "right_now"),
            (r"[Aa]t the moment (.*?)(?:\.|$|,)", 0.75, "at_moment"),
            (r"[Tt]oday (?:I |we )?(.*?)(?:\.|$|,)", 0.70, "today"),
            (
                r"[Tt]his (?:week|month) (?:I'?m |we'?re )?(.*?)(?:\.|$|,)",
                0.70,
                "this_period",
            ),
            (r"[Ss]tatus[:]?\s*(.*?)(?:\.|$)", 0.85, "status"),
        ]

        # Correction patterns - high importance updates
        self.CORRECTION_PATTERNS = [
            (
                r"[Aa]ctually[,]?\s*((?:it's |its |it is |that's )?.*?)(?:\.|$|,)",
                0.95,
                "actually",
            ),
            (
                r"[Nn]o[,]?\s*((?:it's |its |it is |that's )?.*?)(?:\.|$|,)",
                0.95,
                "no_its",
            ),
            (r"[Cc]orrection[:]?\s*(.*?)(?:\.|$)", 1.0, "correction"),
            (
                r"[Ww]ait[,]?\s*((?:it's |its |it is |that's |I meant )?.*?)(?:\.|$|,)",
                0.90,
                "wait",
            ),
            (
                r"[Ss]orry[,]?\s*((?:it's |its |it is |that's )?.*?)(?:\.|$|,)",
                0.85,
                "sorry",
            ),
            (r"I meant (.*?)(?:\.|$|,)", 0.90, "i_meant"),
            (
                r"[Ll]et me correct (?:that[,]?\s*)?(.*?)(?:\.|$)",
                0.95,
                "let_me_correct",
            ),
            (r"[Tt]o clarify[,]?\s*(.*?)(?:\.|$)", 0.90, "to_clarify"),
        ]

        # Combine all patterns with their memory types
        # Order matters: more specific patterns should come first
        self.ALL_PATTERNS = [
            (
                self.CORRECTION_PATTERNS,
                MemoryType.EPISODIC,
            ),  # High importance corrections first
            (
                self.IDENTITY_PATTERNS,
                MemoryType.SEMANTIC,
            ),  # Identity info is semantic knowledge
            (self.PREFERENCE_PATTERNS, MemoryType.PREFERENCE),
            (
                self.DECISION_PATTERNS,
                MemoryType.EPISODIC,
            ),  # Decisions are episodic events
            (
                self.PATTERN_PATTERNS,
                MemoryType.PROCEDURAL,
            ),  # Patterns are procedural knowledge
            (
                self.SOLUTION_PATTERNS,
                MemoryType.PROCEDURAL,
            ),  # Solutions are procedural instructions
            (self.STATUS_PATTERNS, MemoryType.WORKING),  # Status is working memory
            (self.REMEMBER_PATTERNS, MemoryType.EPISODIC),  # General patterns last
        ]

        # Add custom patterns if provided
        if self.custom_patterns:
            for pattern_name, pattern_regex in self.custom_patterns.items():
                # Add custom patterns as CONTEXT type by default
                custom_pattern = [(pattern_regex, 0.80, pattern_name)]
                self.ALL_PATTERNS.append((custom_pattern, MemoryType.EPISODIC))

    def _compile_patterns(self) -> None:
        """Pre-compile all regex patterns for performance."""
        self.compiled_patterns = []

        for pattern_group, memory_type in self.ALL_PATTERNS:
            compiled_group = []
            for pattern, confidence, name in pattern_group:
                try:
                    compiled_regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    compiled_group.append((compiled_regex, confidence, name))
                except re.error as e:
                    logger.warning(f"Failed to compile pattern '{name}': {e}")
                    continue

            if compiled_group:
                self.compiled_patterns.append((compiled_group, memory_type))

        logger.info(f"Compiled {sum(len(group) for group, _ in self.compiled_patterns)} patterns")

    def extract_memories(self, text: str) -> list[ExtractedMemory]:
        """
        Extract all potential memories from text using pattern matching.

        Args:
            text: Text to extract memories from

        Returns:
            List of extracted memories
        """
        if text is None:
            raise TypeError("Text input cannot be None")

        if not text or not text.strip():
            return []

        try:
            # Validate and sanitize input
            clean_text = validate_text_input(text, "extraction_text")

            memories = []
            patterns_to_use = (
                self.compiled_patterns if self.enable_compilation else self._get_runtime_patterns()
            )

            # Process each pattern group
            for pattern_group, memory_type in patterns_to_use:
                group_matches = self._extract_from_pattern_group(
                    clean_text, pattern_group, memory_type
                )
                memories.extend(group_matches)

            # Deduplicate and filter
            unique_memories = self._deduplicate_extractions(memories)
            filtered_memories = self._filter_extractions(unique_memories)

            # Update statistics
            self._update_extraction_stats(filtered_memories)

            return filtered_memories

        except Exception as e:
            logger.error(f"Error extracting memories from text: {e}")
            return []

    def _get_runtime_patterns(
        self,
    ) -> list[tuple[list[tuple[re.Pattern[str], float, str]], MemoryType]]:
        """Get patterns for runtime compilation (when pre-compilation is disabled)."""
        runtime_patterns = []

        for pattern_group, memory_type in self.ALL_PATTERNS:
            runtime_group = []
            for pattern, confidence, name in pattern_group:
                try:
                    compiled_regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    runtime_group.append((compiled_regex, confidence, name))
                except re.error:
                    continue

            if runtime_group:
                runtime_patterns.append((runtime_group, memory_type))

        return runtime_patterns

    def _extract_from_pattern_group(
        self,
        text: str,
        pattern_group: list[tuple[re.Pattern[str], float, str]],
        memory_type: MemoryType,
    ) -> list[ExtractedMemory]:
        """Extract memories from a specific pattern group.

        Args:
            text: Text to extract from
            pattern_group: List of (compiled_regex, confidence, name) tuples
            memory_type: Type of memory to extract
        """
        memories = []

        for pattern_regex, confidence, pattern_name in pattern_group:
            matches = pattern_regex.finditer(text)

            for match in matches:
                # Extract the captured content
                if match.groups():
                    content = match.group(1).strip()
                else:
                    content = match.group(0).strip()

                # Filter out very short or empty matches
                if not content or len(content) < 3:
                    continue

                # Clean up the content
                content = self._clean_extracted_content(content)

                # Enrich content with context keywords for better recall
                content = self._enrich_content_with_context(content, pattern_name, match.group(0))

                if content and len(content) >= 5:  # Minimum meaningful length
                    extracted_memory = ExtractedMemory(
                        content=content,
                        confidence=confidence,
                        memory_type=memory_type,
                        pattern_used=pattern_name,
                        entities=[],  # Will be populated by entity extraction
                        metadata={
                            "start_pos": match.start(),
                            "end_pos": match.end(),
                            "original_match": match.group(0),
                        },
                    )
                    memories.append(extracted_memory)

        return memories

    def _enrich_content_with_context(
        self, content: str, pattern_name: str, original_match: str
    ) -> str:
        """
        Enrich memory content with context keywords for better recall.

        For identity patterns like "My name is Alice", we want to store
        "name: Alice" so it can be found when asking "What's my name?".

        Args:
            content: Extracted content (e.g., "Alice")
            pattern_name: Name of the pattern that matched (e.g., "name_is")
            original_match: Full original match (e.g., "My name is Alice")

        Returns:
            Enriched content with context keywords
        """
        # Map pattern names to context prefixes for better keyword matching
        context_prefixes = {
            "name_is": "name:",
            "im_name": "name:",
            "call_me": "name:",
            "work_at": "works at",
            "i_am_role": "role:",
            "im_role": "role:",
            "live_in": "location:",
            "i_prefer": "prefers",
            "we_use": "uses",
            "we_decided": "decided to",
            "i_like": "likes",
            "i_dislike": "dislikes",
            "we_should": "should",
            "we_must": "must",
        }

        # If pattern has a context prefix, prepend it
        if pattern_name in context_prefixes:
            prefix = context_prefixes[pattern_name]
            # Only add prefix if it's not already in the content
            if not content.lower().startswith(prefix.lower()):
                return f"{prefix} {content}"

        return content

    def _clean_extracted_content(self, content: str) -> str:
        """Clean and normalize extracted content."""
        # Remove leading/trailing whitespace
        content = content.strip()

        # Remove common trailing words that don't add meaning
        trailing_words = ["and", "or", "but", "so", "then", "also", "too"]
        words = content.split()
        while words and words[-1].lower() in trailing_words:
            words.pop()

        content = " ".join(words)

        # Remove excessive punctuation
        content = re.sub(r"[.!?]{2,}", ".", content)
        content = re.sub(r"[,]{2,}", ",", content)

        # Normalize whitespace
        content = " ".join(content.split())

        return content

    def _deduplicate_extractions(self, memories: list[ExtractedMemory]) -> list[ExtractedMemory]:
        """Remove duplicate extractions based on content similarity."""
        if not memories:
            return []

        unique_memories = []
        seen_content = {}  # Map from normalized content to memory index

        for _i, memory in enumerate(memories):
            # Normalize content for comparison
            normalized = memory.content.lower().strip()

            # Check for exact duplicates
            if normalized in seen_content:
                # Keep the memory with higher confidence or longer content
                existing_idx = seen_content[normalized]
                existing_memory = unique_memories[existing_idx]

                if memory.confidence > existing_memory.confidence or (
                    memory.confidence == existing_memory.confidence
                    and len(memory.content) > len(existing_memory.content)
                ):
                    unique_memories[existing_idx] = memory
                continue

            # Check for very similar content (simple heuristic)
            is_duplicate = False
            duplicate_key = None
            for existing_content, existing_idx in seen_content.items():
                if self._are_contents_similar(normalized, existing_content):
                    is_duplicate = True
                    duplicate_key = existing_content

                    # Prefer longer, more descriptive content
                    existing_memory = unique_memories[existing_idx]
                    if len(memory.content) > len(existing_memory.content) or (
                        len(memory.content) == len(existing_memory.content)
                        and memory.confidence >= existing_memory.confidence
                    ):
                        # Replace the existing memory with the better one
                        unique_memories[existing_idx] = memory
                        seen_content[normalized] = existing_idx
                        del seen_content[duplicate_key]
                    break

            if not is_duplicate:
                seen_content[normalized] = len(unique_memories)
                unique_memories.append(memory)

        return unique_memories

    def _are_contents_similar(self, content1: str, content2: str, threshold: float = 0.9) -> bool:
        """Check if two contents are very similar."""
        if not content1 or not content2:
            return False

        # Simple similarity check based on character overlap
        if len(content1) == 0 or len(content2) == 0:
            return False

        # If one is much shorter than the other, they're probably different
        len_ratio = min(len(content1), len(content2)) / max(len(content1), len(content2))
        if len_ratio < 0.7:
            return False

        # Check character overlap
        set1 = set(content1.replace(" ", ""))
        set2 = set(content2.replace(" ", ""))

        if not set1 or not set2:
            return False

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold

    def _filter_extractions(self, memories: list[ExtractedMemory]) -> list[ExtractedMemory]:
        """Filter extractions based on quality and relevance."""
        filtered = []

        for memory in memories:
            # Skip very short memories
            if len(memory.content) < 5:
                continue

            # Skip memories that are mostly punctuation or numbers
            alpha_chars = sum(1 for c in memory.content if c.isalpha())
            if alpha_chars < len(memory.content) * 0.5:
                continue

            # Skip memories that are just common phrases
            if self._is_common_phrase(memory.content):
                continue

            # Skip memories with very low confidence
            if memory.confidence < 0.3:
                continue

            filtered.append(memory)

        return filtered

    def _is_common_phrase(self, content: str) -> bool:
        """Check if content is a common phrase that shouldn't be stored."""
        common_phrases = {
            "thank you",
            "thanks",
            "please",
            "yes",
            "no",
            "ok",
            "okay",
            "sure",
            "alright",
            "got it",
            "i see",
            "i understand",
            "hello",
            "hi",
            "bye",
            "goodbye",
            "see you",
            "talk soon",
        }

        normalized = content.lower().strip()

        # Check if it's in common phrases
        if normalized in common_phrases:
            return True

        # Don't filter out names or specific terms - only filter very short generic phrases
        words = normalized.split()
        if len(words) == 1:
            # Single words that are too generic
            generic_single_words = {
                "ok",
                "yes",
                "no",
                "sure",
                "maybe",
                "perhaps",
                "well",
                "so",
                "and",
                "but",
            }
            return normalized in generic_single_words
        elif len(words) == 2:
            # Only filter out very generic two-word phrases
            generic_two_words = {
                "i see",
                "got it",
                "i understand",
                "thank you",
                "see you",
                "talk soon",
            }
            return normalized in generic_two_words

        return False

    def _update_extraction_stats(self, memories: list[ExtractedMemory]) -> None:
        """Update extraction statistics."""
        self._extraction_stats["total_extractions"] += len(memories)

        for memory in memories:
            # Count pattern usage
            pattern_name = memory.pattern_used
            self._extraction_stats["patterns_matched"][pattern_name] = (
                self._extraction_stats["patterns_matched"].get(pattern_name, 0) + 1
            )

            # Count memory types
            memory_type = memory.memory_type.value
            self._extraction_stats["memory_types_extracted"][memory_type] = (
                self._extraction_stats["memory_types_extracted"].get(memory_type, 0) + 1
            )

    def get_pattern_statistics(self) -> dict[str, any]:
        """Get pattern extraction statistics."""
        total_patterns = sum(len(group) for group, _ in self.compiled_patterns)

        return {
            "total_patterns": total_patterns,
            "compilation_enabled": self.enable_compilation,
            "custom_patterns_count": len(self.custom_patterns),
            "extraction_stats": self._extraction_stats.copy(),
            "memory_type_distribution": self._extraction_stats["memory_types_extracted"].copy(),
            "top_patterns": sorted(
                self._extraction_stats["patterns_matched"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }

    def test_pattern(self, pattern: str, test_text: str) -> list[dict[str, any]]:
        """
        Test a specific pattern against text (useful for debugging).

        Args:
            pattern: Regex pattern to test
            test_text: Text to test against

        Returns:
            List of matches with details
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            matches = []

            for match in compiled_pattern.finditer(test_text):
                matches.append(
                    {
                        "match": match.group(0),
                        "groups": match.groups(),
                        "start": match.start(),
                        "end": match.end(),
                        "span": match.span(),
                    }
                )

            return matches

        except re.error as e:
            return [{"error": f"Invalid regex pattern: {e}"}]
