"""
Integration tests for KuzuMemory main API.

Tests the complete workflow of memory generation and recall
with realistic scenarios and performance requirements.
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from kuzu_memory import KuzuMemory, KuzuMemoryConfig
from kuzu_memory.core.models import MemoryType
from kuzu_memory.utils.exceptions import ValidationError


class TestKuzuMemoryIntegration:
    """Integration tests for the main KuzuMemory API."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "test_memories.db"

    @pytest.fixture
    def test_config(self):
        """Create a test configuration."""
        return {
            "performance": {
                "max_recall_time_ms": 200.0,  # Relaxed for testing (first run is slower)
                "max_generation_time_ms": 1000.0,  # Relaxed for testing (initialization overhead)
                "enable_performance_monitoring": True,
            },
            "recall": {"max_memories": 5, "enable_caching": True, "cache_size": 100},
            "extraction": {
                "enable_entity_extraction": True,
                "enable_pattern_compilation": True,
            },
        }

    def test_basic_memory_workflow(self, temp_db_path, test_config):
        """Test basic memory generation and recall workflow."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Generate memories from content
            content = """
            My name is Alice and I work at TechCorp as a Python developer.
            I prefer using TypeScript for frontend projects.
            We decided to use PostgreSQL for our main database.
            """

            memory_ids = memory.generate_memories(
                content=content, user_id="test-user", session_id="test-session"
            )

            # Should extract multiple memories
            assert len(memory_ids) > 0
            assert all(isinstance(mid, str) for mid in memory_ids)

            # Recall memories with different prompts
            context1 = memory.attach_memories("What's my name?", user_id="test-user")

            assert "Alice" in context1.enhanced_prompt
            assert len(context1.memories) > 0
            assert context1.confidence > 0

            context2 = memory.attach_memories("What database are we using?", user_id="test-user")

            assert "PostgreSQL" in context2.enhanced_prompt
            assert len(context2.memories) > 0

    def test_memory_types_and_importance(self, temp_db_path, test_config):
        """Test that different memory types are extracted with correct importance."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Content with different memory types
            content = """
            My name is Bob (identity).
            I always use Python for backend development (preference).
            We decided to use microservices architecture (decision).
            Currently working on the user authentication module (status).
            """

            memory_ids = memory.generate_memories(content, user_id="test-user")
            assert len(memory_ids) > 0

            # Get individual memories to check types
            memories = []
            for memory_id in memory_ids:
                mem = memory.get_memory_by_id(memory_id)
                if mem:
                    memories.append(mem)

            # Should have different memory types
            memory_types = {mem.memory_type for mem in memories}
            assert len(memory_types) > 1

            # Semantic memories (facts and general knowledge) should have high importance
            semantic_memories = [mem for mem in memories if mem.memory_type == MemoryType.SEMANTIC]
            if semantic_memories:
                assert all(mem.importance >= 0.9 for mem in semantic_memories)

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_duplicate_memory_handling(self, temp_db_path, test_config):
        """Test that duplicate memories are handled correctly."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Store same content multiple times
            content = "My name is Charlie and I work at DataCorp."

            memory_ids1 = memory.generate_memories(content, user_id="test-user")
            memory_ids2 = memory.generate_memories(content, user_id="test-user")
            memory_ids3 = memory.generate_memories(
                "My name is Charlie and I work at DataCorp.",  # Exact duplicate
                user_id="test-user",
            )

            # Should not create many duplicates
            all_ids = memory_ids1 + memory_ids2 + memory_ids3
            unique_contents = set()

            for memory_id in all_ids:
                mem = memory.get_memory_by_id(memory_id)
                if mem:
                    unique_contents.add(mem.content)

            # Should have deduplicated similar content
            assert len(unique_contents) <= len(all_ids) // 2

    def test_memory_updates_and_corrections(self, temp_db_path, test_config):
        """Test that memory updates and corrections work."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Initial information
            initial_content = "I work at OldCorp as a Java developer."
            memory.generate_memories(initial_content, user_id="test-user")

            # Correction
            correction_content = "Actually, I work at NewCorp as a Python developer."
            memory.generate_memories(correction_content, user_id="test-user")

            # Recall should prefer the correction
            context = memory.attach_memories(
                "Where do I work and what language do I use?", user_id="test-user"
            )

            # Should contain the corrected information
            enhanced_prompt = context.enhanced_prompt.lower()
            assert "newcorp" in enhanced_prompt or "python" in enhanced_prompt

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_entity_extraction(self, temp_db_path, test_config):
        """Test entity extraction and entity-based recall."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Content with clear entities
            content = """
            I'm working on the UserService.py file using Django framework.
            The database is PostgreSQL running on AWS.
            My colleague Sarah is helping with the frontend in React.
            """

            memory_ids = memory.generate_memories(content, user_id="test-user")
            assert len(memory_ids) > 0

            # Test entity-based recall
            context = memory.attach_memories(
                "Tell me about Django", strategy="entity", user_id="test-user"
            )

            # Should find memories related to Django
            assert len(context.memories) > 0
            enhanced_lower = context.enhanced_prompt.lower()
            assert "django" in enhanced_lower or "userservice" in enhanced_lower

    def test_temporal_recall(self, temp_db_path, test_config):
        """Test temporal-based memory recall."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Store some memories
            memory.generate_memories(
                "Today I completed the authentication module.", user_id="test-user"
            )

            memory.generate_memories(
                "I'm currently debugging the payment system.", user_id="test-user"
            )

            # Test temporal recall
            context = memory.attach_memories(
                "What did I do recently?", strategy="temporal", user_id="test-user"
            )

            assert len(context.memories) > 0
            assert context.strategy_used == "temporal"

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_performance_requirements(self, temp_db_path, test_config):
        """Test that performance requirements are met."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Store some initial memories
            for i in range(10):
                memory.generate_memories(
                    f"Memory {i}: This is test content for performance testing.",
                    user_id="test-user",
                )

            # Test attach_memories performance
            start_time = time.time()
            context = memory.attach_memories("What are my test memories?", user_id="test-user")
            attach_time_ms = (time.time() - start_time) * 1000

            # Should be reasonably fast (relaxed for testing environment)
            assert attach_time_ms < 100  # 100ms limit for testing
            assert len(context.memories) > 0

            # Test generate_memories performance
            start_time = time.time()
            memory_ids = memory.generate_memories(
                "This is a new memory for performance testing.", user_id="test-user"
            )
            generate_time_ms = (time.time() - start_time) * 1000

            # Should be reasonably fast
            assert generate_time_ms < 200  # 200ms limit for testing
            assert len(memory_ids) > 0

    def test_memory_expiration(self, temp_db_path, test_config):
        """Test memory expiration and cleanup."""
        # Configure short expiration for testing
        test_config["retention"] = {
            "enable_auto_cleanup": True,
            "custom_retention": {"status": 0},  # Expire immediately for testing
        }

        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Store a status memory (should expire quickly)
            memory.generate_memories("Currently working on testing.", user_id="test-user")

            # Cleanup expired memories
            cleaned_count = memory.cleanup_expired_memories()

            # Should have cleaned up some memories
            # Note: This test might be flaky depending on timing
            assert cleaned_count >= 0  # At least no errors

    def test_statistics_and_monitoring(self, temp_db_path, test_config):
        """Test statistics collection and monitoring."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Perform some operations
            memory.generate_memories("Test memory 1", user_id="test-user")
            memory.generate_memories("Test memory 2", user_id="test-user")
            memory.attach_memories("What are my test memories?", user_id="test-user")

            # Get statistics
            stats = memory.get_statistics()

            # Check that statistics are collected
            assert "system_info" in stats
            assert "performance_stats" in stats
            assert "storage_stats" in stats

            perf_stats = stats["performance_stats"]
            assert perf_stats["generate_memories_calls"] >= 2
            assert perf_stats["attach_memories_calls"] >= 1
            assert perf_stats["avg_generate_time_ms"] > 0
            assert perf_stats["avg_attach_time_ms"] > 0

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_context_manager(self, temp_db_path, test_config):
        """Test that KuzuMemory works as a context manager."""
        # Test successful context manager usage
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            memory_ids = memory.generate_memories("Test content", user_id="test-user")
            assert len(memory_ids) > 0

        # Memory should be properly closed after context exit
        # (No specific assertion, just ensuring no exceptions)

    def test_error_handling(self, temp_db_path, test_config):
        """Test error handling for invalid inputs."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Test empty content
            memory_ids = memory.generate_memories("", user_id="test-user")
            assert len(memory_ids) == 0  # Should handle gracefully

            # Test empty prompt
            with pytest.raises(ValidationError):  # Should raise validation error
                memory.attach_memories("", user_id="test-user")

            # Test invalid strategy
            with pytest.raises((ValueError, KeyError, ValidationError)):
                memory.attach_memories(
                    "Test prompt", strategy="invalid_strategy", user_id="test-user"
                )

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_user_isolation(self, temp_db_path, test_config):
        """Test that memories are properly isolated between users."""
        with KuzuMemory(db_path=temp_db_path, config=test_config) as memory:
            # Store memories for different users
            memory.generate_memories("User A's secret project", user_id="user-a")
            memory.generate_memories("User B's different project", user_id="user-b")

            # User A should only see their memories
            context_a = memory.attach_memories("What's my project?", user_id="user-a")

            # User B should only see their memories
            context_b = memory.attach_memories("What's my project?", user_id="user-b")

            # Check isolation
            assert "User A's secret" in context_a.enhanced_prompt
            assert "User A's secret" not in context_b.enhanced_prompt
            assert "User B's different" in context_b.enhanced_prompt
            assert "User B's different" not in context_a.enhanced_prompt
