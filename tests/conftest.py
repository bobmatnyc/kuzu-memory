"""
Pytest configuration and shared fixtures for KuzuMemory tests.

Provides common test fixtures, utilities, and configuration
for unit tests, integration tests, and benchmarks.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from kuzu_memory import KuzuMemory, KuzuMemoryConfig

# Configure logging for tests
logging.basicConfig(level=logging.WARNING)
logging.getLogger("kuzu_memory").setLevel(logging.INFO)


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kuzu_memory_tests_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_db_path(test_data_dir):
    """Create a unique temporary database path for each test."""
    import uuid

    db_path = test_data_dir / f"test_db_{uuid.uuid4().hex[:8]}.db"
    yield db_path
    # Cleanup is handled by session-level test_data_dir fixture


@pytest.fixture
def default_test_config():
    """Default test configuration with relaxed performance limits."""
    return {
        "version": "1.0",
        "debug": False,
        "log_level": "WARNING",
        "storage": {
            "max_size_mb": 10.0,  # Smaller for tests
            "auto_compact": True,
            "backup_on_corruption": True,
            "connection_pool_size": 3,  # Smaller pool for tests
            "query_timeout_ms": 10000,  # Longer timeout for tests
        },
        "recall": {
            "max_memories": 10,
            "default_strategy": "auto",
            "strategies": ["keyword", "entity", "temporal"],
            "strategy_weights": {"keyword": 0.4, "entity": 0.4, "temporal": 0.2},
            "min_confidence_threshold": 0.1,
            "enable_caching": True,
            "cache_size": 100,  # Smaller cache for tests
            "cache_ttl_seconds": 60,  # Shorter TTL for tests
        },
        "extraction": {
            "min_memory_length": 3,  # Shorter for tests
            "max_memory_length": 500,  # Shorter for tests
            "enable_entity_extraction": True,
            "enable_pattern_compilation": True,
            "custom_patterns": {},
            "pattern_weights": {
                "identity": 1.0,
                "preference": 0.9,
                "decision": 0.9,
                "pattern": 0.7,
                "solution": 0.7,
                "status": 0.3,
                "context": 0.5,
            },
        },
        "performance": {
            "max_recall_time_ms": 100.0,  # Relaxed for tests
            "max_generation_time_ms": 200.0,  # Relaxed for tests
            "enable_performance_monitoring": True,
            "log_slow_operations": False,  # Reduce noise in tests
            "enable_metrics_collection": False,
        },
        "retention": {
            "enable_auto_cleanup": False,  # Disabled for tests
            "cleanup_interval_hours": 24,
            "custom_retention": {},
            "max_total_memories": 1000,  # Smaller for tests
            "cleanup_batch_size": 100,
        },
    }


@pytest.fixture
def fast_test_config(default_test_config):
    """Test configuration optimized for speed."""
    config = default_test_config.copy()
    config["extraction"]["enable_entity_extraction"] = False  # Faster
    config["recall"]["enable_caching"] = False  # More predictable
    return config


@pytest.fixture
def kuzu_memory_instance(temp_db_path, default_test_config):
    """Create a KuzuMemory instance for testing."""
    memory = KuzuMemory(db_path=temp_db_path, config=default_test_config)
    yield memory
    memory.close()


@pytest.fixture
def sample_memories_data():
    """Sample memory data for testing."""
    return [
        {
            "content": "My name is Alice Johnson and I work at TechCorp.",
            "user_id": "user-1",
            "session_id": "session-1",
            "source": "conversation",
            "metadata": {"context": "introduction"},
        },
        {
            "content": "I prefer Python for backend development and React for frontend.",
            "user_id": "user-1",
            "session_id": "session-1",
            "source": "conversation",
            "metadata": {"context": "preferences"},
        },
        {
            "content": "We decided to use PostgreSQL as our main database.",
            "user_id": "user-1",
            "session_id": "session-2",
            "source": "meeting",
            "metadata": {"context": "architecture_decision"},
        },
        {
            "content": "Bob is working on the payment integration module.",
            "user_id": "user-2",
            "session_id": "session-3",
            "source": "conversation",
            "metadata": {"context": "team_update"},
        },
        {
            "content": "Currently debugging the authentication service.",
            "user_id": "user-1",
            "session_id": "session-4",
            "source": "status_update",
            "metadata": {"context": "current_work"},
        },
    ]


@pytest.fixture
def populated_memory(kuzu_memory_instance, sample_memories_data):
    """KuzuMemory instance populated with sample data."""
    memory = kuzu_memory_instance

    # Store sample memories
    for data in sample_memories_data:
        memory.generate_memories(
            content=data["content"],
            user_id=data["user_id"],
            session_id=data["session_id"],
            source=data["source"],
            metadata=data["metadata"],
        )

    return memory


@pytest.fixture
def test_prompts():
    """Common test prompts for recall testing."""
    return [
        "What's my name?",
        "What programming languages do I use?",
        "What database are we using?",
        "Who is working on payments?",
        "What am I currently working on?",
        "Tell me about the team",
        "What technologies do we use?",
        "What are my preferences?",
        "What decisions have we made?",
        "What's the current status?",
    ]


class MemoryTestHelper:
    """Helper class for memory testing utilities."""

    @staticmethod
    def assert_memory_content_contains(memories: list, expected_content: str):
        """Assert that at least one memory contains the expected content."""
        found = any(
            expected_content.lower() in memory.content.lower() for memory in memories
        )
        assert found, f"No memory found containing '{expected_content}'"

    @staticmethod
    def assert_enhanced_prompt_contains(context, expected_content: str):
        """Assert that enhanced prompt contains expected content."""
        assert (
            expected_content.lower() in context.enhanced_prompt.lower()
        ), f"Enhanced prompt does not contain '{expected_content}'"

    @staticmethod
    def count_memories_by_type(memories: list, memory_type) -> int:
        """Count memories of a specific type."""
        return sum(1 for memory in memories if memory.memory_type == memory_type)

    @staticmethod
    def get_unique_memory_contents(memories: list) -> set:
        """Get set of unique memory contents."""
        return {memory.content for memory in memories}

    @staticmethod
    def assert_performance_within_limit(
        actual_time_ms: float, limit_ms: float, operation: str
    ):
        """Assert that operation time is within performance limit."""
        assert (
            actual_time_ms <= limit_ms
        ), f"{operation} took {actual_time_ms:.2f}ms, exceeding limit of {limit_ms}ms"

    @staticmethod
    def create_test_memory_content(
        count: int, prefix: str = "Test memory"
    ) -> list[str]:
        """Create a list of test memory contents."""
        return [
            f"{prefix} {i}: This is test content for memory number {i}."
            for i in range(count)
        ]


@pytest.fixture
def memory_test_helper():
    """Provide memory test helper utilities."""
    return MemoryTestHelper()


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "benchmark: Performance benchmark tests")
    config.addinivalue_line("markers", "slow: Slow tests that take more time")
    config.addinivalue_line(
        "markers", "requires_kuzu: Tests that require Kuzu database"
    )


# Skip tests if Kuzu is not available
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle missing dependencies."""
    try:
        import kuzu

        kuzu_available = True
    except ImportError:
        kuzu_available = False

    if not kuzu_available:
        skip_kuzu = pytest.mark.skip(reason="Kuzu database not available")
        for item in items:
            if "requires_kuzu" in item.keywords:
                item.add_marker(skip_kuzu)


# Custom assertions for better error messages
def assert_memory_valid(memory):
    """Assert that a memory object is valid."""
    assert memory is not None, "Memory is None"
    assert memory.id is not None, "Memory ID is None"
    assert memory.content is not None, "Memory content is None"
    assert len(memory.content.strip()) > 0, "Memory content is empty"
    assert memory.created_at is not None, "Memory created_at is None"
    assert memory.confidence >= 0.0, "Memory confidence is negative"
    assert memory.confidence <= 1.0, "Memory confidence exceeds 1.0"
    assert memory.importance >= 0.0, "Memory importance is negative"
    assert memory.importance <= 1.0, "Memory importance exceeds 1.0"


def assert_memory_context_valid(context):
    """Assert that a memory context object is valid."""
    assert context is not None, "MemoryContext is None"
    assert context.original_prompt is not None, "Original prompt is None"
    assert context.enhanced_prompt is not None, "Enhanced prompt is None"
    assert context.memories is not None, "Memories list is None"
    assert isinstance(context.memories, list), "Memories is not a list"
    assert context.confidence >= 0.0, "Context confidence is negative"
    assert context.confidence <= 1.0, "Context confidence exceeds 1.0"
    assert context.recall_time_ms >= 0.0, "Recall time is negative"

    # Validate each memory in the context
    for memory in context.memories:
        assert_memory_valid(memory)


# Add custom assertions to pytest namespace
pytest.assert_memory_valid = assert_memory_valid
pytest.assert_memory_context_valid = assert_memory_context_valid
