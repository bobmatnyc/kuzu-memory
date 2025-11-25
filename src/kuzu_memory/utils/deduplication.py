"""
Multi-layer deduplication engine for KuzuMemory.

Implements sophisticated deduplication using exact hash matching,
normalized text comparison, and semantic similarity to prevent
duplicate memories while handling updates and corrections.
"""

import hashlib
import logging
import re
from difflib import SequenceMatcher
from typing import Any

from ..core.models import Memory, MemoryType
from ..utils.validation import sanitize_for_database

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """
    Multi-layer deduplication engine with configurable thresholds.

    Implements three layers of deduplication:
    1. Exact hash matching (SHA256)
    2. Normalized text comparison (case-insensitive, whitespace-normalized)
    3. Semantic similarity (token overlap and sequence matching)
    """

    def __init__(
        self,
        exact_threshold: float = 1.0,  # SHA256 exact match
        near_threshold: float = 0.80,  # Normalized similarity threshold
        semantic_threshold: float = 0.50,  # Token overlap threshold
        min_length_for_similarity: int = 10,  # Minimum length to check similarity
        enable_update_detection: bool = True,  # Detect updates vs duplicates
    ) -> None:
        """
        Initialize deduplication engine.

        Args:
            exact_threshold: Threshold for exact hash matches (always 1.0)
            near_threshold: Threshold for normalized text similarity
            semantic_threshold: Threshold for semantic similarity
            min_length_for_similarity: Minimum text length to perform similarity checks
            enable_update_detection: Whether to detect updates vs pure duplicates
        """
        # Validate thresholds
        if not (0.0 <= near_threshold <= 1.0):
            raise ValueError(f"near_threshold must be between 0.0 and 1.0, got {near_threshold}")
        if not (0.0 <= semantic_threshold <= 1.0):
            raise ValueError(
                f"semantic_threshold must be between 0.0 and 1.0, got {semantic_threshold}"
            )
        if min_length_for_similarity < 0:
            raise ValueError(
                f"min_length_for_similarity must be non-negative, got {min_length_for_similarity}"
            )

        self.exact_threshold = exact_threshold
        self.near_threshold = near_threshold
        self.semantic_threshold = semantic_threshold
        self.min_length_for_similarity = min_length_for_similarity
        self.enable_update_detection = enable_update_detection

        # Update/correction patterns
        self.update_patterns = [
            r"actually,?\s*",
            r"correction:?\s*",
            r"no,?\s*(?:it's|its|it is)\s*",
            r"wait,?\s*",
            r"sorry,?\s*",
            r"i meant\s*",
            r"let me correct\s*",
            r"to clarify\s*",
        ]
        self.compiled_update_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.update_patterns
        ]

    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash for content."""
        normalized = content.lower().strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Remove common punctuation that doesn't affect meaning
        normalized = re.sub(r'[.,!?;:()"\'-]', "", normalized)

        # Remove articles and common words that don't affect core meaning
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "and",
            "or",
            "but",
            "in",
            "at",
            "to",
            "for",
            "of",
            "with",
            "as",
            "on",
            "by",
        }
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words and len(word) > 1]

        return " ".join(filtered_words)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using sequence matching.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0

        # Use SequenceMatcher for character-level similarity
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def _calculate_token_overlap(self, text1: str, text2: str) -> float:
        """
        Calculate token overlap between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Overlap ratio between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0

        # Normalize both texts for better comparison
        normalized1 = self._normalize_text(text1)
        normalized2 = self._normalize_text(text2)

        # Tokenize and create sets
        tokens1 = set(normalized1.split()) if normalized1 else set()
        tokens2 = set(normalized2.split()) if normalized2 else set()

        if not tokens1 or not tokens2:
            return 0.0

        # Calculate Jaccard similarity (intersection over union)
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        jaccard = intersection / union if union > 0 else 0.0

        # Also calculate overlap coefficient (intersection / min(set sizes))
        # This is more generous for partial matches
        min_size = min(len(tokens1), len(tokens2))
        overlap_coeff = intersection / min_size if min_size > 0 else 0.0

        # Return the higher of the two (more generous matching)
        return max(jaccard, overlap_coeff)

    def _is_update_or_correction(self, new_content: str, existing_content: str) -> bool:
        """
        Detect if new content is an update/correction of existing content.

        Args:
            new_content: New memory content
            existing_content: Existing memory content

        Returns:
            True if new content appears to be an update/correction
        """
        if not self.enable_update_detection:
            return False

        # Check for update patterns in new content
        for pattern in self.compiled_update_patterns:
            if pattern.search(new_content.lower()):
                return True

        # Check if new content contradicts existing content
        # This is a simple heuristic - could be made more sophisticated
        contradiction_indicators = [
            ("yes", "no"),
            ("true", "false"),
            ("correct", "incorrect"),
            ("right", "wrong"),
            ("is", "is not"),
            ("can", "cannot"),
            ("will", "will not"),
        ]

        new_lower = new_content.lower()
        existing_lower = existing_content.lower()

        for positive, negative in contradiction_indicators:
            if (positive in existing_lower and negative in new_lower) or (
                negative in existing_lower and positive in new_lower
            ):
                return True

        return False

    def find_duplicates(
        self,
        new_content: str,
        existing_memories: list[Memory],
        memory_type: MemoryType | None = None,
    ) -> list[tuple[Memory, float, str]]:
        """
        Find duplicate memories for new content.

        Args:
            new_content: Content to check for duplicates
            existing_memories: List of existing memories to compare against
            memory_type: Optional memory type to filter by

        Returns:
            List of (memory, similarity_score, match_type) tuples
            match_type can be: 'exact', 'normalized', 'semantic'
        """
        if not new_content or not new_content.strip():
            return []

        duplicates = []
        new_content_clean = sanitize_for_database(new_content)
        new_hash = self._generate_content_hash(new_content_clean)
        new_normalized = self._normalize_text(new_content_clean)

        # Filter memories by type if specified
        if memory_type:
            memories_to_check = [m for m in existing_memories if m.memory_type == memory_type]
        else:
            memories_to_check = existing_memories

        for memory in memories_to_check:
            # Skip if memory is expired
            if not memory.is_valid():
                continue

            # Layer 1: Exact hash match
            if memory.content_hash == new_hash:
                duplicates.append((memory, 1.0, "exact"))
                continue

            # Skip similarity checks for very short content
            if (
                len(new_content_clean) < self.min_length_for_similarity
                or len(memory.content) < self.min_length_for_similarity
            ):
                continue

            # Layer 2: Normalized text comparison
            memory_normalized = self._normalize_text(memory.content)
            normalized_similarity = self._calculate_text_similarity(
                new_normalized, memory_normalized
            )

            if normalized_similarity >= self.near_threshold:
                duplicates.append((memory, normalized_similarity, "normalized"))
                continue

            # Layer 3: Semantic similarity (token overlap)
            token_overlap = self._calculate_token_overlap(new_content_clean, memory.content)

            if token_overlap >= self.semantic_threshold:
                # Check if this might be an update rather than a duplicate
                if self._is_update_or_correction(new_content_clean, memory.content):
                    duplicates.append((memory, token_overlap, "update"))
                else:
                    duplicates.append((memory, token_overlap, "semantic"))

        # Sort by similarity score (highest first)
        duplicates.sort(key=lambda x: x[1], reverse=True)

        return duplicates

    def is_duplicate(
        self,
        new_content: str,
        existing_memories: list[Memory],
        memory_type: MemoryType | None = None,
    ) -> bool:
        """
        Check if new content is a duplicate of existing memories.

        Args:
            new_content: Content to check
            existing_memories: List of existing memories
            memory_type: Optional memory type filter

        Returns:
            True if content is a duplicate
        """
        duplicates = self.find_duplicates(new_content, existing_memories, memory_type)

        # Consider it a duplicate if we find any matches above thresholds
        # but exclude updates/corrections
        for _memory, _score, match_type in duplicates:
            if match_type in ["exact", "normalized", "semantic"]:
                return True

        return False

    def get_deduplication_action(
        self,
        new_content: str,
        existing_memories: list[Memory],
        memory_type: MemoryType | None = None,
    ) -> dict[str, Any]:
        """
        Get recommended deduplication action for new content.

        Args:
            new_content: New content to process
            existing_memories: List of existing memories
            memory_type: Optional memory type filter

        Returns:
            Dictionary with action recommendation:
            {
                'action': 'store' | 'skip' | 'update' | 'merge',
                'reason': str,
                'existing_memory': Memory | None,
                'similarity_score': float,
                'match_type': str
            }
        """
        duplicates = self.find_duplicates(new_content, existing_memories, memory_type)

        if not duplicates:
            return {
                "action": "store",
                "reason": "No duplicates found",
                "existing_memory": None,
                "similarity_score": 0.0,
                "match_type": "none",
            }

        # Get the best match
        best_memory, best_score, match_type = duplicates[0]

        if match_type == "exact":
            return {
                "action": "skip",
                "reason": "Exact duplicate found",
                "existing_memory": best_memory,
                "similarity_score": best_score,
                "match_type": match_type,
            }

        elif match_type == "update":
            return {
                "action": "update",
                "reason": "Content appears to be an update/correction",
                "existing_memory": best_memory,
                "similarity_score": best_score,
                "match_type": match_type,
            }

        elif match_type in ["normalized", "semantic"]:
            # For high similarity, recommend skipping
            if best_score >= 0.9:
                return {
                    "action": "skip",
                    "reason": f"Very similar content found ({match_type})",
                    "existing_memory": best_memory,
                    "similarity_score": best_score,
                    "match_type": match_type,
                }
            else:
                return {
                    "action": "store",
                    "reason": f"Similar but distinct content ({match_type})",
                    "existing_memory": best_memory,
                    "similarity_score": best_score,
                    "match_type": match_type,
                }

        return {
            "action": "store",
            "reason": "Content is sufficiently different",
            "existing_memory": None,
            "similarity_score": 0.0,
            "match_type": "none",
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get deduplication engine statistics and configuration."""
        return {
            "exact_threshold": self.exact_threshold,
            "near_threshold": self.near_threshold,
            "semantic_threshold": self.semantic_threshold,
            "min_length_for_similarity": self.min_length_for_similarity,
            "enable_update_detection": self.enable_update_detection,
            "update_patterns_count": len(self.update_patterns),
        }
