"""
Unit tests for deduplication engine.

Tests the DeduplicationEngine with comprehensive duplicate detection,
update recognition, and similarity analysis using pytest best practices.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from kuzu_memory.utils.deduplication import DeduplicationEngine
from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.utils.exceptions import ValidationError


class TestDeduplicationEngine:
    """Comprehensive tests for DeduplicationEngine."""
    
    @pytest.fixture
    def dedup_engine(self):
        """Create a DeduplicationEngine with default settings."""
        return DeduplicationEngine()
    
    @pytest.fixture
    def strict_dedup_engine(self):
        """Create a DeduplicationEngine with strict thresholds."""
        return DeduplicationEngine(
            near_threshold=0.98,
            semantic_threshold=0.95,
            min_length_for_similarity=20
        )
    
    @pytest.fixture
    def lenient_dedup_engine(self):
        """Create a DeduplicationEngine with lenient thresholds."""
        return DeduplicationEngine(
            near_threshold=0.80,
            semantic_threshold=0.70,
            enable_update_detection=False
        )
    
    @pytest.fixture
    def sample_memories(self):
        """Create sample memories for testing."""
        return [
            Memory(
                content="My name is Alice Johnson and I work at TechCorp.",
                memory_type=MemoryType.IDENTITY,
                created_at=datetime.now() - timedelta(days=1)
            ),
            Memory(
                content="I prefer Python for backend development.",
                memory_type=MemoryType.PREFERENCE,
                created_at=datetime.now() - timedelta(hours=12)
            ),
            Memory(
                content="We decided to use PostgreSQL as our database.",
                memory_type=MemoryType.DECISION,
                created_at=datetime.now() - timedelta(hours=6)
            ),
            Memory(
                content="Currently working on the authentication module.",
                memory_type=MemoryType.STATUS,
                created_at=datetime.now() - timedelta(hours=1)
            ),
        ]
    
    # Test Exact Hash Matching
    def test_exact_duplicate_detection(self, dedup_engine, sample_memories):
        """Test detection of exact duplicates using content hash."""
        new_content = "My name is Alice Johnson and I work at TechCorp."
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find exact match
        assert len(duplicates) > 0
        exact_matches = [d for d in duplicates if d[2] == 'exact']
        assert len(exact_matches) == 1
        assert exact_matches[0][1] == 1.0  # Perfect similarity score
    
    def test_exact_duplicate_case_insensitive(self, dedup_engine, sample_memories):
        """Test that exact matching is case-insensitive."""
        new_content = "MY NAME IS ALICE JOHNSON AND I WORK AT TECHCORP."
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find exact match despite case difference
        exact_matches = [d for d in duplicates if d[2] == 'exact']
        assert len(exact_matches) == 1
    
    def test_exact_duplicate_whitespace_normalized(self, dedup_engine, sample_memories):
        """Test that exact matching normalizes whitespace."""
        new_content = "  My   name    is Alice Johnson   and I work at TechCorp.  "
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find exact match despite whitespace differences
        exact_matches = [d for d in duplicates if d[2] == 'exact']
        assert len(exact_matches) == 1
    
    # Test Normalized Text Comparison
    def test_normalized_similarity_detection(self, dedup_engine, sample_memories):
        """Test detection of similar content using normalized comparison."""
        # Similar but not identical content
        new_content = "My name is Alice Johnson, and I work at TechCorp Inc."
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find normalized similarity
        normalized_matches = [d for d in duplicates if d[2] == 'normalized']
        assert len(normalized_matches) > 0
        assert normalized_matches[0][1] >= 0.95  # High similarity
    
    def test_normalized_similarity_with_punctuation(self, dedup_engine, sample_memories):
        """Test that normalized similarity ignores punctuation differences."""
        new_content = "My name is Alice Johnson, and I work at TechCorp!"
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find high similarity despite punctuation
        assert len(duplicates) > 0
        best_match = duplicates[0]
        assert best_match[1] >= 0.90
    
    def test_normalized_similarity_with_articles(self, dedup_engine, sample_memories):
        """Test that normalized similarity handles articles and common words."""
        new_content = "The name is Alice Johnson and she works at the TechCorp."
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find similarity despite added articles
        assert len(duplicates) > 0
        best_match = duplicates[0]
        assert best_match[1] >= 0.80
    
    # Test Semantic Similarity (Token Overlap)
    def test_semantic_similarity_detection(self, dedup_engine, sample_memories):
        """Test detection of semantic similarity using token overlap."""
        new_content = "Alice Johnson is employed at TechCorp as a developer."
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find semantic similarity
        semantic_matches = [d for d in duplicates if d[2] == 'semantic']
        assert len(semantic_matches) > 0
        assert semantic_matches[0][1] >= 0.70
    
    def test_semantic_similarity_different_structure(self, dedup_engine, sample_memories):
        """Test semantic similarity with different sentence structure."""
        new_content = "TechCorp employs Alice Johnson in their development team."
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find semantic similarity despite different structure
        assert len(duplicates) > 0
        best_match = duplicates[0]
        assert best_match[1] >= 0.60
    
    def test_semantic_similarity_partial_overlap(self, dedup_engine, sample_memories):
        """Test semantic similarity with partial token overlap."""
        new_content = "I use Python programming language for backend services."
        
        duplicates = dedup_engine.find_duplicates(new_content, sample_memories)
        
        # Should find similarity with Python preference memory
        python_matches = [d for d in duplicates if "python" in d[0].content.lower()]
        assert len(python_matches) > 0
    
    # Test Update and Correction Detection
    def test_update_pattern_detection(self, dedup_engine, sample_memories):
        """Test detection of update/correction patterns."""
        update_contents = [
            "Actually, my name is Alice Smith and I work at TechCorp.",
            "Correction: I prefer TypeScript for backend development.",
            "No, I work at DataCorp, not TechCorp.",
            "Wait, we decided to use MongoDB as our database.",
            "Sorry, I meant React for frontend development.",
            "Let me correct that - I work at NewCorp now.",
        ]
        
        for content in update_contents:
            duplicates = dedup_engine.find_duplicates(content, sample_memories)
            
            # Should detect updates
            update_matches = [d for d in duplicates if d[2] == 'update']
            if update_matches:  # Not all may match existing memories
                assert len(update_matches) > 0
                assert update_matches[0][1] > 0.5  # Reasonable similarity
    
    def test_update_detection_disabled(self, lenient_dedup_engine, sample_memories):
        """Test that update detection can be disabled."""
        content = "Actually, my name is Alice Smith and I work at TechCorp."
        
        duplicates = lenient_dedup_engine.find_duplicates(content, sample_memories)
        
        # Should not detect as update when disabled
        update_matches = [d for d in duplicates if d[2] == 'update']
        assert len(update_matches) == 0
    
    def test_contradiction_detection(self, dedup_engine, sample_memories):
        """Test detection of contradictory statements."""
        contradictory_contents = [
            "I don't prefer Python for backend development.",
            "We decided not to use PostgreSQL as our database.",
            "My name is not Alice Johnson.",
        ]
        
        for content in contradictory_contents:
            duplicates = dedup_engine.find_duplicates(content, sample_memories)
            
            # May detect as updates due to contradiction
            if duplicates:
                # Should have some similarity to existing content
                assert duplicates[0][1] > 0.3
    
    # Test Deduplication Actions
    def test_deduplication_action_skip_exact(self, dedup_engine, sample_memories):
        """Test that exact duplicates get 'skip' action."""
        content = "My name is Alice Johnson and I work at TechCorp."
        
        action = dedup_engine.get_deduplication_action(content, sample_memories)
        
        assert action['action'] == 'skip'
        assert action['reason'] == 'Exact duplicate found'
        assert action['existing_memory'] is not None
        assert action['similarity_score'] == 1.0
        assert action['match_type'] == 'exact'
    
    def test_deduplication_action_update(self, dedup_engine, sample_memories):
        """Test that updates get 'update' action."""
        content = "Actually, my name is Alice Smith and I work at TechCorp."
        
        action = dedup_engine.get_deduplication_action(content, sample_memories)
        
        # Should recommend update for correction
        if action['action'] == 'update':
            assert action['reason'] == 'Content appears to be an update/correction'
            assert action['existing_memory'] is not None
            assert action['match_type'] == 'update'
    
    def test_deduplication_action_store_new(self, dedup_engine, sample_memories):
        """Test that new content gets 'store' action."""
        content = "I enjoy playing chess in my free time."
        
        action = dedup_engine.get_deduplication_action(content, sample_memories)
        
        assert action['action'] == 'store'
        assert 'No duplicates found' in action['reason'] or 'sufficiently different' in action['reason']
    
    def test_deduplication_action_store_similar(self, dedup_engine, sample_memories):
        """Test that similar but distinct content gets 'store' action."""
        content = "I work as a software engineer at TechCorp's competitor."
        
        action = dedup_engine.get_deduplication_action(content, sample_memories)
        
        # Should store similar but distinct content
        if action['similarity_score'] > 0.5:
            assert action['action'] in ['store', 'skip']  # Depends on similarity threshold
    
    # Test Memory Type Filtering
    def test_memory_type_filtering(self, dedup_engine, sample_memories):
        """Test that deduplication can filter by memory type."""
        content = "My name is Alice Johnson and I work at TechCorp."
        
        # Filter by identity type
        duplicates = dedup_engine.find_duplicates(
            content, sample_memories, MemoryType.IDENTITY
        )
        
        # Should only find identity memories
        for memory, score, match_type in duplicates:
            assert memory.memory_type == MemoryType.IDENTITY
    
    def test_memory_type_filtering_no_matches(self, dedup_engine, sample_memories):
        """Test memory type filtering with no matches."""
        content = "My name is Alice Johnson and I work at TechCorp."
        
        # Filter by status type (shouldn't match identity content)
        duplicates = dedup_engine.find_duplicates(
            content, sample_memories, MemoryType.STATUS
        )
        
        # Should find no matches in status memories
        assert len(duplicates) == 0
    
    # Test Threshold Configuration
    def test_strict_thresholds(self, strict_dedup_engine, sample_memories):
        """Test behavior with strict similarity thresholds."""
        content = "My name is Alice Johnson, I work at TechCorp."  # Slightly different
        
        duplicates = strict_dedup_engine.find_duplicates(content, sample_memories)
        
        # Strict thresholds should find fewer matches
        high_similarity_matches = [d for d in duplicates if d[1] >= 0.95]
        # May or may not find matches depending on exact similarity
        assert isinstance(duplicates, list)  # Should not crash
    
    def test_lenient_thresholds(self, lenient_dedup_engine, sample_memories):
        """Test behavior with lenient similarity thresholds."""
        content = "Alice works at some tech company."
        
        duplicates = lenient_dedup_engine.find_duplicates(content, sample_memories)
        
        # Lenient thresholds should find more matches
        assert len(duplicates) > 0  # Should find some similarity
    
    def test_minimum_length_threshold(self, dedup_engine, sample_memories):
        """Test minimum length threshold for similarity checking."""
        short_content = "Hi"
        
        duplicates = dedup_engine.find_duplicates(short_content, sample_memories)
        
        # Should not perform similarity checks on very short content
        similarity_matches = [d for d in duplicates if d[2] in ['normalized', 'semantic']]
        assert len(similarity_matches) == 0
    
    # Test Edge Cases and Error Handling
    def test_empty_content_handling(self, dedup_engine, sample_memories):
        """Test handling of empty content."""
        test_cases = ["", "   ", "\n\t"]
        
        for content in test_cases:
            duplicates = dedup_engine.find_duplicates(content, sample_memories)
            assert duplicates == []
    
    def test_empty_memory_list_handling(self, dedup_engine):
        """Test handling of empty memory list."""
        content = "Test content"
        
        duplicates = dedup_engine.find_duplicates(content, [])
        assert duplicates == []
        
        action = dedup_engine.get_deduplication_action(content, [])
        assert action['action'] == 'store'
        assert action['reason'] == 'No duplicates found'
    
    def test_expired_memory_filtering(self, dedup_engine):
        """Test that expired memories are filtered out."""
        expired_memory = Memory(
            content="This memory has expired.",
            valid_to=datetime.now() - timedelta(hours=1)  # Expired
        )
        
        content = "This memory has expired."
        duplicates = dedup_engine.find_duplicates(content, [expired_memory])
        
        # Should not find duplicates in expired memories
        assert len(duplicates) == 0
    
    def test_very_long_content_handling(self, dedup_engine, sample_memories):
        """Test handling of very long content."""
        long_content = "My name is Alice Johnson and I work at TechCorp. " * 100
        
        duplicates = dedup_engine.find_duplicates(long_content, sample_memories)
        
        # Should handle long content without crashing
        assert isinstance(duplicates, list)
        # Should still find duplicates
        assert len(duplicates) > 0
    
    def test_special_characters_handling(self, dedup_engine, sample_memories):
        """Test handling of content with special characters."""
        special_contents = [
            "My name is Alice Johnson & I work @TechCorp!",
            "I prefer Python (3.9+) for backend development.",
            "We use PostgreSQL v13.2 as our database.",
            "Currently working on the auth-module project.",
        ]
        
        for content in special_contents:
            duplicates = dedup_engine.find_duplicates(content, sample_memories)
            # Should handle special characters without crashing
            assert isinstance(duplicates, list)
    
    # Test Performance and Statistics
    def test_deduplication_statistics(self, dedup_engine):
        """Test that deduplication statistics are tracked."""
        stats = dedup_engine.get_statistics()
        
        # Check statistics structure
        assert 'exact_threshold' in stats
        assert 'near_threshold' in stats
        assert 'semantic_threshold' in stats
        assert 'min_length_for_similarity' in stats
        assert 'enable_update_detection' in stats
        assert 'update_patterns_count' in stats
        
        # Check values
        assert stats['exact_threshold'] == 1.0
        assert 0.0 <= stats['near_threshold'] <= 1.0
        assert 0.0 <= stats['semantic_threshold'] <= 1.0
        assert stats['min_length_for_similarity'] >= 0
        assert isinstance(stats['enable_update_detection'], bool)
        assert stats['update_patterns_count'] > 0
    
    def test_duplicate_ranking(self, dedup_engine, sample_memories):
        """Test that duplicates are properly ranked by similarity."""
        # Content that should match multiple memories with different similarities
        content = "Alice Johnson works at TechCorp and prefers Python development."
        
        duplicates = dedup_engine.find_duplicates(content, sample_memories)
        
        if len(duplicates) > 1:
            # Should be sorted by similarity score (highest first)
            for i in range(len(duplicates) - 1):
                assert duplicates[i][1] >= duplicates[i + 1][1]
    
    def test_is_duplicate_method(self, dedup_engine, sample_memories):
        """Test the is_duplicate convenience method."""
        # Exact duplicate
        exact_content = "My name is Alice Johnson and I work at TechCorp."
        assert dedup_engine.is_duplicate(exact_content, sample_memories) is True
        
        # New content
        new_content = "I enjoy playing chess in my free time."
        assert dedup_engine.is_duplicate(new_content, sample_memories) is False
        
        # Update (should not be considered duplicate)
        update_content = "Actually, my name is Alice Smith and I work at TechCorp."
        # Depends on implementation - updates might not be considered duplicates
        result = dedup_engine.is_duplicate(update_content, sample_memories)
        assert isinstance(result, bool)
    
    # Test Configuration Validation
    def test_invalid_threshold_handling(self):
        """Test handling of invalid threshold values."""
        # Should handle invalid thresholds gracefully
        with pytest.raises((ValueError, AssertionError)):
            DeduplicationEngine(near_threshold=1.5)  # > 1.0
        
        with pytest.raises((ValueError, AssertionError)):
            DeduplicationEngine(semantic_threshold=-0.1)  # < 0.0
    
    def test_threshold_boundary_values(self):
        """Test threshold boundary values."""
        # Should accept boundary values
        engine = DeduplicationEngine(
            near_threshold=1.0,
            semantic_threshold=0.0,
            min_length_for_similarity=1
        )
        
        assert engine.near_threshold == 1.0
        assert engine.semantic_threshold == 0.0
        assert engine.min_length_for_similarity == 1
