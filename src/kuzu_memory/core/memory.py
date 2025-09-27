"""
Main KuzuMemory API class.

Provides the primary interface for memory operations with the two main methods:
attach_memories() and generate_memories() with performance targets of <10ms and <20ms.
"""

import hashlib
import logging
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

from ..recall.coordinator import RecallCoordinator
from ..storage.kuzu_adapter import create_kuzu_adapter
from ..storage.memory_store import MemoryStore
from ..utils.exceptions import (
    ConfigurationError,
    DatabaseError,
    KuzuMemoryError,
    PerformanceError,
    ValidationError,
)
from .config import KuzuMemoryConfig
from .constants import (
    DEFAULT_AGENT_ID,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_RECALL_STRATEGY,
    MEMORY_BY_ID_CACHE_SIZE,
    MEMORY_BY_ID_CACHE_TTL,
)
from .dependencies import (
    DependencyContainer,
    get_container,
)
from .models import Memory, MemoryContext

# Removed validation import to avoid circular dependency

logger = logging.getLogger(__name__)


def cache_key_from_args(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    key_parts = []
    for arg in args:
        if hasattr(arg, "__dict__"):
            # Skip self/cls arguments
            continue
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    key_str = "|".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached_method(
    maxsize: int = DEFAULT_CACHE_SIZE, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
):
    """
    Decorator for caching method results with TTL support.

    Args:
        maxsize: Maximum cache size (for LRU eviction)
        ttl_seconds: Time-to-live in seconds for cached results
    """

    def decorator(func):
        cache = {}
        cache_times = {}

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = cache_key_from_args(*args, **kwargs)

            # Check if cached and not expired
            if cache_key in cache:
                cached_time = cache_times.get(cache_key, 0)
                if time.time() - cached_time < ttl_seconds:
                    logger.debug(
                        f"Cache hit for {func.__name__} with key {cache_key[:8]}"
                    )
                    return cache[cache_key]
                else:
                    # Expired, remove from cache
                    del cache[cache_key]
                    del cache_times[cache_key]

            # Cache miss, execute function
            result = func(self, *args, **kwargs)

            # Store in cache with timestamp
            cache[cache_key] = result
            cache_times[cache_key] = time.time()

            # LRU eviction if cache is too large
            if len(cache) > maxsize:
                # Remove oldest entry
                oldest_key = min(cache_times, key=cache_times.get)
                del cache[oldest_key]
                del cache_times[oldest_key]

            return result

        # Add cache control methods
        wrapper.cache_clear = lambda: (cache.clear(), cache_times.clear())
        wrapper.cache_info = lambda: {
            "size": len(cache),
            "maxsize": maxsize,
            "ttl": ttl_seconds,
        }

        return wrapper

    return decorator


class KuzuMemory:
    """
    Main interface for KuzuMemory operations.

    Provides fast, offline memory capabilities for AI applications with
    two primary methods: attach_memories() and generate_memories().
    """

    def __init__(
        self,
        db_path: Path | None = None,
        config: dict[str, Any] | None = None,
        container: DependencyContainer | None = None,
    ):
        """
        Initialize KuzuMemory.

        Args:
            db_path: Path to database file (default: ~/.kuzu-memory/memories.db)
            config: Optional configuration dict or KuzuMemoryConfig object
            container: Optional dependency container for testing/customization

        Raises:
            ConfigurationError: If configuration is invalid
            DatabaseError: If database initialization fails
        """
        try:
            # Set up database path
            db_path_resolved = db_path or (Path.home() / ".kuzu-memory" / "memories.db")
            if isinstance(db_path_resolved, str):
                db_path_resolved = Path(db_path_resolved)
            self.db_path = db_path_resolved

            # Set up configuration
            if isinstance(config, KuzuMemoryConfig):
                self.config = config
            elif isinstance(config, dict):
                self.config = KuzuMemoryConfig.from_dict(config)
            elif config is None:
                self.config = KuzuMemoryConfig.default()
            else:
                raise ConfigurationError(f"Invalid config type: {type(config)}")

            # Validate configuration
            self.config.validate()

            # Set up dependency container
            self.container = container or get_container()

            # Initialize components
            self._initialize_components()

            # Track initialization time
            self._initialized_at = datetime.now()

            logger.info(f"KuzuMemory initialized with database at {self.db_path}")

        except Exception as e:
            if isinstance(e, ConfigurationError | DatabaseError):
                raise
            raise KuzuMemoryError(f"Failed to initialize KuzuMemory: {e}")

    def _initialize_components(self) -> None:
        """Initialize internal components."""
        try:
            # Check if components are already in container (for testing)
            if not self.container.has("database_adapter"):
                # Initialize database adapter (CLI or Python API based on config)
                db_adapter = create_kuzu_adapter(self.db_path, self.config)
                if hasattr(db_adapter, "initialize"):
                    db_adapter.initialize()
                self.container.register("database_adapter", db_adapter)

            if not self.container.has("memory_store"):
                # Initialize memory store
                db_adapter = self.container.get_database_adapter()
                memory_store = MemoryStore(db_adapter, self.config)
                self.container.register("memory_store", memory_store)

            if not self.container.has("recall_coordinator"):
                # Initialize recall coordinator
                db_adapter = self.container.get_database_adapter()
                recall_coordinator = RecallCoordinator(db_adapter, self.config)
                self.container.register("recall_coordinator", recall_coordinator)

            # Get references to components
            self.db_adapter = self.container.get_database_adapter()
            self.memory_store = self.container.get_memory_store()
            self.recall_coordinator = self.container.get_recall_coordinator()

            # Performance tracking
            self._performance_stats = {
                "attach_memories_calls": 0,
                "generate_memories_calls": 0,
                "avg_attach_time_ms": 0.0,
                "avg_generate_time_ms": 0.0,
                "total_memories_generated": 0,
                "total_memories_recalled": 0,
            }

        except Exception as e:
            raise DatabaseError(f"Failed to initialize components: {e}")

    @cached_method()  # Uses default cache settings from constants
    def attach_memories(
        self,
        prompt: str,
        max_memories: int = DEFAULT_MEMORY_LIMIT,
        strategy: str = DEFAULT_RECALL_STRATEGY,
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = DEFAULT_AGENT_ID,
    ) -> MemoryContext:
        """
        PRIMARY API METHOD 1: Retrieve relevant memories for a prompt.

        Args:
            prompt: User input to find memories for
            max_memories: Maximum number of memories to return
            strategy: Recall strategy (auto|keyword|entity|temporal)
            user_id: Optional user ID for filtering
            session_id: Optional session ID for filtering
            agent_id: Agent ID for filtering

        Returns:
            MemoryContext object containing:
                - original_prompt: The input prompt
                - enhanced_prompt: Prompt with memories injected
                - memories: List of relevant Memory objects
                - confidence: Confidence score (0-1)

        Performance Requirement: Must complete in <10ms

        Raises:
            ValidationError: If input parameters are invalid
            RecallError: If memory recall fails
            PerformanceError: If operation exceeds 10ms
        """
        start_time = time.time()

        try:
            # Validate inputs
            if not prompt or not prompt.strip():
                raise ValidationError("prompt", prompt, "cannot be empty")

            if max_memories <= 0:
                raise ValidationError(
                    "max_memories", str(max_memories), "must be positive"
                )

            if strategy not in ["auto", "keyword", "entity", "temporal"]:
                raise ValidationError(
                    "strategy",
                    strategy,
                    "must be one of: auto, keyword, entity, temporal",
                )

            # Execute recall
            context = self.recall_coordinator.attach_memories(
                prompt=prompt,
                max_memories=max_memories,
                strategy=strategy,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
            )

            # Update performance statistics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_attach_stats(execution_time_ms, len(context.memories))

            # Check performance requirement
            if execution_time_ms > self.config.performance.max_recall_time_ms:
                if self.config.performance.enable_performance_monitoring:
                    raise PerformanceError(
                        f"attach_memories took {execution_time_ms:.1f}ms, exceeding target of {self.config.performance.max_recall_time_ms}ms"
                    )
                else:
                    logger.warning(
                        f"attach_memories took {execution_time_ms:.1f}ms (target: {self.config.performance.max_recall_time_ms}ms)"
                    )

            logger.debug(
                f"attach_memories completed in {execution_time_ms:.1f}ms with {len(context.memories)} memories"
            )

            return context

        except Exception as e:
            if isinstance(e, ValidationError | PerformanceError):
                raise
            raise KuzuMemoryError(f"attach_memories failed: {e}")

    def remember(
        self,
        content: str,
        source: str | None = None,
        session_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store a single memory immediately (synchronous operation).

        This method directly stores content as a memory without pattern extraction,
        making it suitable for direct user input that should be remembered as-is.

        Args:
            content: The content to remember
            source: Source of the memory (e.g., "conversation", "document")
            session_id: Session ID to group related memories
            agent_id: Agent ID that created this memory
            metadata: Additional metadata as dictionary

        Returns:
            Memory ID of the stored memory
        """
        # Directly store the content as a memory
        # Use EPISODIC type for direct memories as they represent specific events/facts
        import uuid
        from datetime import datetime

        from .models import Memory, MemoryType

        memory = Memory(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=MemoryType.EPISODIC,
            source_type=source or "manual",  # Note: field is source_type, not source
            importance=0.8,  # Default importance for direct memories
            confidence=1.0,  # High confidence since it's explicit
            created_at=datetime.now(),  # Keep as datetime object
            user_id=metadata.get("user_id") if metadata else None,
            session_id=session_id,
            agent_id=agent_id or "default",
            metadata=metadata or {},
        )

        # Store directly in the database
        try:
            self.memory_store._store_memory_in_database(memory)
            return memory.id
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return ""

    def generate_memories(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "conversation",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
    ) -> list[str]:
        """
        PRIMARY API METHOD 2: Extract and store memories from content.

        Args:
            content: Text to extract memories from (usually LLM response)
            metadata: Additional context (user_id, session_id, etc.)
            source: Origin of content
            user_id: Optional user ID
            session_id: Optional session ID
            agent_id: Agent ID

        Returns:
            List of created memory IDs

        Performance Requirement: Must complete in <20ms

        Raises:
            ValidationError: If input parameters are invalid
            ExtractionError: If memory extraction fails
            PerformanceError: If operation exceeds 20ms
        """
        start_time = time.time()

        try:
            # Validate inputs
            if not content or not content.strip():
                return []  # Empty content is valid, just return empty list

            # Basic content validation
            if len(content) > 100000:  # 100KB limit
                raise ValidationError("Content exceeds maximum length")

            # Execute memory generation
            memory_ids = self.memory_store.generate_memories(
                content=content,
                metadata=metadata,
                source=source,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
            )

            # Update performance statistics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_generate_stats(execution_time_ms, len(memory_ids))

            # Check performance requirement
            if execution_time_ms > self.config.performance.max_generation_time_ms:
                if self.config.performance.enable_performance_monitoring:
                    raise PerformanceError(
                        f"generate_memories took {execution_time_ms:.1f}ms, exceeding target of {self.config.performance.max_generation_time_ms}ms"
                    )
                else:
                    logger.warning(
                        f"generate_memories took {execution_time_ms:.1f}ms (target: {self.config.performance.max_generation_time_ms}ms)"
                    )

            logger.debug(
                f"generate_memories completed in {execution_time_ms:.1f}ms with {len(memory_ids)} memories"
            )

            return memory_ids

        except Exception as e:
            if isinstance(e, ValidationError | PerformanceError):
                raise
            raise KuzuMemoryError(f"generate_memories failed: {e}")

    @cached_method(maxsize=MEMORY_BY_ID_CACHE_SIZE, ttl_seconds=MEMORY_BY_ID_CACHE_TTL)
    def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """
        Get a specific memory by its ID.

        Args:
            memory_id: Memory ID to retrieve

        Returns:
            Memory object or None if not found
        """
        try:
            return self.memory_store.get_memory_by_id(memory_id)
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    def cleanup_expired_memories(self) -> int:
        """
        Clean up expired memories based on retention policies.

        Returns:
            Number of memories cleaned up
        """
        try:
            return self.memory_store.cleanup_expired_memories()
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return 0

    def get_recent_memories(self, limit: int = 10, **filters) -> list[Memory]:
        """
        Get recent memories, optionally filtered.

        Args:
            limit: Maximum number of memories to return
            **filters: Optional filters (e.g., memory_type, user_id)

        Returns:
            List of recent memories
        """
        try:
            return self.memory_store.get_recent_memories(limit=limit, **filters)
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []

    def get_memory_count(self) -> int:
        """
        Get total count of non-expired memories.

        Returns:
            Total number of active memories
        """
        try:
            return self.memory_store.get_memory_count()
        except Exception as e:
            logger.error(f"Failed to get memory count: {e}")
            return 0

    def get_memory_type_stats(self) -> dict[str, int]:
        """
        Get statistics grouped by memory type.

        Returns:
            Dictionary with memory type counts
        """
        try:
            return self.memory_store.get_memory_type_stats()
        except Exception as e:
            logger.error(f"Failed to get memory type stats: {e}")
            return {}

    def get_source_stats(self) -> dict[str, int]:
        """
        Get statistics grouped by source.

        Returns:
            Dictionary with source counts
        """
        try:
            return self.memory_store.get_source_stats()
        except Exception as e:
            logger.error(f"Failed to get source stats: {e}")
            return {}

    def get_daily_activity_stats(self, days: int = 7) -> dict[str, int]:
        """Get daily activity statistics (placeholder)."""
        # Simplified implementation - just return recent count
        recent_count = len(self.get_recent_memories(limit=days * 10))
        return {"recent_days": recent_count}

    def get_average_memory_length(self) -> float:
        """Get average memory length (placeholder)."""
        recent = self.get_recent_memories(limit=100)
        if not recent:
            return 0.0
        return sum(len(m.content) for m in recent) / len(recent)

    def get_oldest_memory_date(self) -> datetime | None:
        """Get oldest memory date (placeholder)."""
        # Would need a specific query - return None for now
        return None

    def get_newest_memory_date(self) -> datetime | None:
        """Get newest memory date (placeholder)."""
        recent = self.get_recent_memories(limit=1)
        return recent[0].created_at if recent else None

    @cached_method()
    def batch_store_memories(self, memories: list[Memory]) -> list[str]:
        """
        Store multiple memories in a single batch operation.

        This method provides efficient batch storage of Memory objects,
        reducing database round-trips and improving performance for bulk
        memory operations.

        Args:
            memories: List of Memory objects to store

        Returns:
            List of memory IDs that were successfully stored

        Example:
            >>> from kuzu_memory import KuzuMemory, Memory, MemoryType
            >>> km = KuzuMemory()
            >>> memories = [
            ...     Memory(
            ...         content="First memory content",
            ...         memory_type=MemoryType.SEMANTIC,
            ...         source_type="batch"
            ...     ),
            ...     Memory(
            ...         content="Second memory content",
            ...         memory_type=MemoryType.EPISODIC,
            ...         source_type="batch"
            ...     )
            ... ]
            >>> stored_ids = km.batch_store_memories(memories)
            >>> print(f"Stored {len(stored_ids)} memories")

        Raises:
            ValidationError: If memories list is invalid or contains non-Memory objects
            DatabaseError: If batch storage operation fails

        Performance Note:
            This method uses batch operations to minimize database round-trips.
            For best performance, batch sizes of 100-1000 memories are recommended.
        """
        try:
            if not memories:
                return []

            # Validate input
            if not isinstance(memories, list):
                raise ValidationError(
                    "memories",
                    type(memories).__name__,
                    "must be a list of Memory objects",
                )

            # Delegate to memory store for batch storage
            stored_ids = self.memory_store.batch_store_memories(memories)

            # Update performance statistics
            self._performance_stats["total_memories_generated"] += len(stored_ids)

            logger.info(f"Batch stored {len(stored_ids)} memories")
            return stored_ids

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to batch store memories: {e}")
            raise KuzuMemoryError(f"batch_store_memories failed: {e}")

    @cached_method(
        maxsize=MEMORY_BY_ID_CACHE_SIZE * 10, ttl_seconds=MEMORY_BY_ID_CACHE_TTL
    )
    def batch_get_memories_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        """
        Retrieve multiple memories by their IDs in a single batch operation.

        This method provides efficient batch retrieval of memories,
        utilizing caching when available and minimizing database queries.

        Args:
            memory_ids: List of memory IDs to retrieve

        Returns:
            List of Memory objects (may be fewer than requested if some IDs don't exist)

        Example:
            >>> from kuzu_memory import KuzuMemory
            >>> km = KuzuMemory()
            >>> # Assume we have some memory IDs
            >>> memory_ids = ["mem1", "mem2", "mem3"]
            >>> memories = km.batch_get_memories_by_ids(memory_ids)
            >>> for memory in memories:
            ...     print(f"{memory.id}: {memory.content[:50]}...")

        Raises:
            DatabaseError: If batch retrieval operation fails

        Performance Note:
            This method leverages caching to minimize database hits. Frequently
            accessed memories will be served from cache for optimal performance.
        """
        try:
            if not memory_ids:
                return []

            # Validate input
            if not isinstance(memory_ids, list):
                raise ValidationError(
                    "memory_ids", type(memory_ids).__name__, "must be a list of strings"
                )

            # Delegate to memory store for batch retrieval
            memories = self.memory_store.batch_get_memories_by_ids(memory_ids)

            # Update performance statistics
            self._performance_stats["total_memories_recalled"] += len(memories)

            logger.debug(
                f"Batch retrieved {len(memories)} memories from {len(memory_ids)} IDs"
            )
            return memories

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to batch get memories: {e}")
            raise KuzuMemoryError(f"batch_get_memories_by_ids failed: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive statistics about the memory system.

        Returns:
            Dictionary with statistics from all components
        """
        try:
            return {
                "system_info": {
                    "initialized_at": self._initialized_at.isoformat(),
                    "db_path": str(self.db_path),
                    "config_version": self.config.version,
                },
                "performance_stats": self._performance_stats.copy(),
                "storage_stats": self.memory_store.get_storage_statistics(),
                "recall_stats": self.recall_coordinator.get_recall_statistics(),
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

    def _update_attach_stats(
        self, execution_time_ms: float, memories_count: int
    ) -> None:
        """Update attach_memories performance statistics."""
        self._performance_stats["attach_memories_calls"] += 1
        self._performance_stats["total_memories_recalled"] += memories_count

        # Update average time
        total_calls = self._performance_stats["attach_memories_calls"]
        current_avg = self._performance_stats["avg_attach_time_ms"]
        new_avg = ((current_avg * (total_calls - 1)) + execution_time_ms) / total_calls
        self._performance_stats["avg_attach_time_ms"] = new_avg

    def _update_generate_stats(
        self, execution_time_ms: float, memories_count: int
    ) -> None:
        """Update generate_memories performance statistics."""
        self._performance_stats["generate_memories_calls"] += 1
        self._performance_stats["total_memories_generated"] += memories_count

        # Update average time
        total_calls = self._performance_stats["generate_memories_calls"]
        current_avg = self._performance_stats["avg_generate_time_ms"]
        new_avg = ((current_avg * (total_calls - 1)) + execution_time_ms) / total_calls
        self._performance_stats["avg_generate_time_ms"] = new_avg

    def close(self) -> None:
        """
        Close the KuzuMemory instance and clean up resources.
        """
        try:
            if hasattr(self, "db_adapter"):
                self.db_adapter.close()
            logger.info("KuzuMemory closed successfully")
        except Exception as e:
            logger.error(f"Error closing KuzuMemory: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"KuzuMemory(db_path='{self.db_path}', initialized_at='{self._initialized_at}')"
