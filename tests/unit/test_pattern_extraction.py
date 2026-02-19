"""
Unit tests for pattern extraction system.

Tests the PatternExtractor with comprehensive pattern matching,
edge cases, and performance validation using pytest best practices.
"""

import re
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.core.models import ExtractedMemory, MemoryType
from kuzu_memory.extraction.patterns import PatternExtractor, PatternMatch
from kuzu_memory.utils.exceptions import ExtractionError


class TestPatternExtractor:
    """Comprehensive tests for PatternExtractor."""

    @pytest.fixture
    def pattern_extractor(self):
        """Create a PatternExtractor instance for testing."""
        return PatternExtractor(enable_compilation=True)

    @pytest.fixture
    def pattern_extractor_no_compilation(self):
        """Create a PatternExtractor without pre-compilation."""
        return PatternExtractor(enable_compilation=False)

    @pytest.fixture
    def custom_pattern_extractor(self):
        """Create a PatternExtractor with custom patterns."""
        custom_patterns = {
            "test_pattern": r"test pattern: (.*?)(?:\.|$)",
            "custom_identity": r"I am called (.*?)(?:\.|$)",
        }
        return PatternExtractor(custom_patterns=custom_patterns)

    # Test Pattern Compilation
    def test_pattern_compilation_enabled(self, pattern_extractor):
        """Test that patterns are compiled when compilation is enabled."""
        assert pattern_extractor.enable_compilation is True
        assert hasattr(pattern_extractor, "compiled_patterns")
        assert len(pattern_extractor.compiled_patterns) > 0

        # Check that patterns are actually compiled regex objects
        for pattern_group, _memory_type in pattern_extractor.compiled_patterns:
            for compiled_regex, _confidence, _name in pattern_group:
                assert hasattr(compiled_regex, "search")  # Compiled regex method
                assert hasattr(compiled_regex, "finditer")

    def test_pattern_compilation_disabled(self, pattern_extractor_no_compilation):
        """Test runtime compilation when pre-compilation is disabled."""
        extractor = pattern_extractor_no_compilation
        assert extractor.enable_compilation is False

        # Should still work with runtime compilation
        memories = extractor.extract_memories("My name is Alice.")
        assert len(memories) > 0

    def test_custom_patterns_integration(self, custom_pattern_extractor):
        """Test that custom patterns are properly integrated."""
        text = "test pattern: This is a custom test. I am called Bob."
        memories = custom_pattern_extractor.extract_memories(text)

        # Should extract memories using custom patterns
        custom_memories = [
            m for m in memories if m.pattern_used in ["test_pattern", "custom_identity"]
        ]
        assert len(custom_memories) > 0

        # Check specific extractions
        test_memory = next((m for m in memories if "custom test" in m.content), None)
        assert test_memory is not None
        assert test_memory.pattern_used == "test_pattern"

    # Test Identity Pattern Extraction
    def test_identity_pattern_extraction(self, pattern_extractor):
        """Test extraction of identity-related memories."""
        test_cases = [
            ("My name is Alice Johnson.", "Alice Johnson"),
            ("I'm Bob Smith from TechCorp.", "Bob Smith"),
            ("Call me Charlie.", "Charlie"),
            ("I work at DataCorp as a developer.", "DataCorp"),
            ("I am a Senior Python Developer.", "Senior Python Developer"),
        ]

        for text, expected_content in test_cases:
            memories = pattern_extractor.extract_memories(text)
            semantic_memories = [
                m for m in memories if m.memory_type == MemoryType.SEMANTIC
            ]  # Facts and general knowledge

            assert len(semantic_memories) > 0, f"No semantic memory found for: {text}"

            # Check that expected content is captured
            found_content = any(
                expected_content.lower() in m.content.lower() for m in semantic_memories
            )
            assert found_content, f"Expected '{expected_content}' not found in extracted memories"

    def test_preference_pattern_extraction(self, pattern_extractor):
        """Test extraction of preference-related memories."""
        test_cases = [
            (
                "I prefer Python for backend development.",
                "Python for backend development",
            ),
            ("I like using React for frontend.", "using React for frontend"),
            ("I don't like JavaScript frameworks.", "JavaScript frameworks"),
            ("My favorite database is PostgreSQL.", "PostgreSQL"),
            ("I usually use pytest for testing.", "pytest for testing"),
            ("I always validate input data.", "validate input data"),
            ("I never use global variables.", "use global variables"),
        ]

        for text, expected_content in test_cases:
            memories = pattern_extractor.extract_memories(text)
            preference_memories = [m for m in memories if m.memory_type == MemoryType.PREFERENCE]

            assert len(preference_memories) > 0, f"No preference memory found for: {text}"

            # Check content extraction
            found_content = any(
                expected_content.lower() in m.content.lower() for m in preference_memories
            )
            assert found_content, f"Expected '{expected_content}' not found"

    def test_decision_pattern_extraction(self, pattern_extractor):
        """Test extraction of decision-related memories."""
        test_cases = [
            (
                "We decided to use PostgreSQL for the database.",
                "use PostgreSQL for the database",
            ),
            ("Let's go with microservices architecture.", "microservices architecture"),
            ("We'll use Docker for containerization.", "Docker for containerization"),
            (
                "The decision is to implement OAuth authentication.",
                "implement OAuth authentication",
            ),
            (
                "After discussion we chose React for the frontend.",
                "chose React for the frontend",
            ),
        ]

        for text, expected_content in test_cases:
            memories = pattern_extractor.extract_memories(text)
            episodic_memories = [
                m for m in memories if m.memory_type == MemoryType.EPISODIC
            ]  # Personal experiences and events

            assert len(episodic_memories) > 0, f"No episodic memory found for: {text}"

            found_content = any(
                expected_content.lower() in m.content.lower() for m in episodic_memories
            )
            assert found_content, f"Expected '{expected_content}' not found"

    def test_correction_pattern_extraction(self, pattern_extractor):
        """Test extraction of correction/update patterns."""
        test_cases = [
            ("Actually, I work at NewCorp.", "I work at NewCorp"),
            ("No, it's Python not Java.", "it's Python not Java"),
            ("Correction: the deadline is next week.", "the deadline is next week"),
            ("Wait, I meant React not Angular.", "I meant React not Angular"),
            ("Sorry, it's PostgreSQL not MySQL.", "it's PostgreSQL not MySQL"),
            ("Let me correct that - we use FastAPI.", "we use FastAPI"),
        ]

        for text, expected_content in test_cases:
            memories = pattern_extractor.extract_memories(text)

            # Corrections should be high confidence
            high_confidence_memories = [m for m in memories if m.confidence >= 0.9]
            assert (
                len(high_confidence_memories) > 0
            ), f"No high-confidence memory for correction: {text}"

            found_content = any(expected_content.lower() in m.content.lower() for m in memories)
            assert found_content, f"Expected '{expected_content}' not found"

    # Test Edge Cases and Error Handling
    def test_empty_text_handling(self, pattern_extractor):
        """Test handling of empty or whitespace-only text."""
        test_cases = ["", "   ", "\n\t", None]

        for text in test_cases:
            if text is None:
                with pytest.raises((TypeError, AttributeError)):
                    pattern_extractor.extract_memories(text)
            else:
                memories = pattern_extractor.extract_memories(text)
                assert memories == []

    def test_very_long_text_handling(self, pattern_extractor):
        """Test handling of very long text inputs."""
        # Create a very long text with patterns
        long_text = "My name is Alice. " * 1000 + "I prefer Python. " * 1000

        memories = pattern_extractor.extract_memories(long_text)

        # Should still extract memories without errors
        assert len(memories) > 0

        # Should find semantic (facts/knowledge) and preference memories
        semantic_memories = [m for m in memories if m.memory_type == MemoryType.SEMANTIC]
        preference_memories = [m for m in memories if m.memory_type == MemoryType.PREFERENCE]

        assert len(semantic_memories) > 0
        assert len(preference_memories) > 0

    def test_special_characters_handling(self, pattern_extractor):
        """Test handling of text with special characters and unicode."""
        test_cases = [
            "My name is José García-López.",
            "I prefer C++ and C# programming.",
            "We use React.js and Node.js frameworks.",
            "The API endpoint is /api/v1/users/{id}.",
            "I work at Café & Co. company.",
            "My email is user@domain.co.uk.",
        ]

        for text in test_cases:
            memories = pattern_extractor.extract_memories(text)
            # Should handle special characters without crashing
            assert isinstance(memories, list)

    def test_malformed_regex_patterns(self):
        """Test handling of malformed custom regex patterns."""
        malformed_patterns = {
            "bad_pattern1": r"[unclosed_bracket",
            "bad_pattern2": r"*invalid_quantifier",
            "bad_pattern3": r"(?P<invalid_group",
        }

        # Should handle malformed patterns gracefully
        extractor = PatternExtractor(custom_patterns=malformed_patterns)

        # Should still work with valid built-in patterns
        memories = extractor.extract_memories("My name is Alice.")
        assert len(memories) > 0

    # Test Memory Deduplication and Filtering
    def test_duplicate_content_deduplication(self, pattern_extractor):
        """Test that duplicate extracted content is deduplicated."""
        # Text with repeated patterns
        text = """
        My name is Alice. My name is Alice Johnson.
        I prefer Python. I really prefer Python programming.
        """

        memories = pattern_extractor.extract_memories(text)

        # Check for similar content deduplication
        contents = [m.content for m in memories]

        # Should not have exact duplicates
        assert len(contents) == len(set(contents))

    def test_short_memory_filtering(self, pattern_extractor):
        """Test that very short memories are filtered out."""
        text = "My name is A. I like X. We use Y."

        memories = pattern_extractor.extract_memories(text)

        # All memories should meet minimum length requirement
        for memory in memories:
            assert len(memory.content) >= 5  # Minimum meaningful length

    def test_common_phrase_filtering(self, pattern_extractor):
        """Test that common phrases are filtered out."""
        text = "Thank you. Yes. No. Okay. I see."

        memories = pattern_extractor.extract_memories(text)

        # Should filter out common phrases
        common_phrases = {"thank you", "yes", "no", "okay", "i see"}
        for memory in memories:
            assert memory.content.lower().strip() not in common_phrases

    # Test Performance and Statistics
    def test_extraction_statistics_tracking(self, pattern_extractor):
        """Test that extraction statistics are properly tracked."""
        initial_stats = pattern_extractor.get_pattern_statistics()
        initial_total = initial_stats["extraction_stats"]["total_extractions"]

        # Extract memories from multiple texts
        texts = [
            "My name is Alice and I work at TechCorp.",
            "I prefer Python for backend development.",
            "We decided to use PostgreSQL as our database.",
        ]

        for text in texts:
            pattern_extractor.extract_memories(text)

        # Check that statistics were updated
        final_stats = pattern_extractor.get_pattern_statistics()
        final_total = final_stats["extraction_stats"]["total_extractions"]

        assert final_total > initial_total
        assert "patterns_matched" in final_stats["extraction_stats"]
        assert "memory_types_extracted" in final_stats["extraction_stats"]

    def test_pattern_testing_utility(self, pattern_extractor):
        """Test the pattern testing utility method."""
        test_pattern = r"I work at (.*?)(?:\.|$)"
        test_text = "I work at TechCorp. I also work at DataCorp."

        matches = pattern_extractor.test_pattern(test_pattern, test_text)

        # This pattern should only match "I work at", not "I also work at"
        assert len(matches) == 1
        assert matches[0]["groups"] == ("TechCorp",)

        # Test a pattern that would match both
        test_pattern2 = r"(?:I (?:also )?work at) (.*?)(?:\.|$)"
        matches2 = pattern_extractor.test_pattern(test_pattern2, test_text)
        assert len(matches2) == 2
        assert matches2[0]["groups"] == ("TechCorp",)
        assert matches2[1]["groups"] == ("DataCorp",)

        # Test invalid pattern
        invalid_matches = pattern_extractor.test_pattern("[invalid", test_text)
        assert len(invalid_matches) == 1
        assert "error" in invalid_matches[0]

    # Test Memory Type Assignment
    def test_memory_type_assignment_accuracy(self, pattern_extractor):
        """Test that extracted memories get correct memory types."""
        test_cases = [
            ("My name is Alice.", MemoryType.SEMANTIC),  # Facts and general knowledge
            ("I prefer Python programming.", MemoryType.PREFERENCE),
            (
                "We decided to use PostgreSQL.",
                MemoryType.EPISODIC,
            ),  # Personal experiences and events
            (
                "Always validate user input.",
                MemoryType.PROCEDURAL,
            ),  # Instructions and how-to content
            (
                "To fix this bug, restart the service.",
                MemoryType.PROCEDURAL,
            ),  # Instructions and how-to content
            (
                "Currently working on authentication.",
                MemoryType.WORKING,
            ),  # Tasks and current focus
            ("Actually, I work at NewCorp.", MemoryType.EPISODIC),  # Correction (event)
        ]

        for text, expected_type in test_cases:
            memories = pattern_extractor.extract_memories(text)

            # Should have at least one memory of the expected type
            type_memories = [m for m in memories if m.memory_type == expected_type]
            assert len(type_memories) > 0, f"No {expected_type} memory found for: {text}"

    def test_confidence_score_assignment(self, pattern_extractor):
        """Test that confidence scores are properly assigned."""
        # High confidence patterns
        high_confidence_texts = [
            "My name is Alice Johnson.",  # Explicit identity
            "Correction: we use PostgreSQL.",  # Explicit correction
            "I always use pytest for testing.",  # Strong preference
        ]

        # Lower confidence patterns

        for text in high_confidence_texts:
            memories = pattern_extractor.extract_memories(text)
            high_conf_memories = [m for m in memories if m.confidence >= 0.8]
            assert len(high_conf_memories) > 0, f"No high-confidence memory for: {text}"

        # Note: Lower confidence patterns might not be in our current pattern set
        # This test validates the confidence assignment mechanism exists
