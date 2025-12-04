"""
Main KuzuMemory API class.

Provides the primary interface for memory operations with the two main methods:
attach_memories() and generate_memories() with performance targets of <10ms and <20ms.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar, cast

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
from ..utils.git_user import GitUserProvider
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
    DatabaseAdapterProtocol,
    DependencyContainer,
    MemoryStoreProtocol,
    RecallCoordinatorProtocol,
    get_container,
)
from .models import Memory, MemoryContext

# Removed validation import to avoid circular dependency

logger = logging.getLogger(__name__)

# Type variables for decorator
P = ParamSpec("P")
R = TypeVar("R")


def cache_key_from_args(*args: Any, **kwargs: Any) -> str:
    """Generate a cache key from function arguments."""
    key_parts: list[str] = []
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
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for caching method results with TTL support.

    Args:
        maxsize: Maximum cache size (for LRU eviction)
        ttl_seconds: Time-to-live in seconds for cached results
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        cache: dict[str, R] = {}
        cache_times: dict[str, float] = {}

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Generate cache key
            cache_key = cache_key_from_args(*args, **kwargs)

            # Check if cached and not expired
            if cache_key in cache:
                cached_time = cache_times.get(cache_key, 0.0)
                if time.time() - cached_time < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__} with key {cache_key[:8]}")
                    return cache[cache_key]
                else:
                    # Expired, remove from cache
                    del cache[cache_key]
                    del cache_times[cache_key]

            # Cache miss, execute function
            result = func(*args, **kwargs)

            # Store in cache with timestamp
            cache[cache_key] = result
            cache_times[cache_key] = time.time()

            # LRU eviction if cache is too large
            if len(cache) > maxsize:
                # Remove oldest entry
                oldest_key = min(cache_times, key=lambda k: cache_times[k])
                del cache[oldest_key]
                del cache_times[oldest_key]

            return result

        # Add cache control methods
        def cache_clear() -> None:
            cache.clear()
            cache_times.clear()

        def cache_info() -> dict[str, Any]:
            return {
                "size": len(cache),
                "maxsize": maxsize,
                "ttl": ttl_seconds,
            }

        # Type-safe attribute assignment
        typed_wrapper = cast(Any, wrapper)
        typed_wrapper.cache_clear = cache_clear
        typed_wrapper.cache_info = cache_info

        return cast(Callable[P, R], wrapper)

    return decorator


class KuzuMemory:
    """
    Main interface for KuzuMemory operations.

    Provides fast, offline memory capabilities for AI applications with
    two primary methods: attach_memories() and generate_memories().
    """

    # Class attributes with types
    db_path: Path
    config: KuzuMemoryConfig
    container: DependencyContainer
    db_adapter: DatabaseAdapterProtocol
    memory_store: MemoryStoreProtocol
    recall_coordinator: RecallCoordinatorProtocol
    auto_git_sync: Any | None  # AutoGitSyncManager or None
    project_root: Path
    _user_id: str | None
    _enable_git_sync: bool
    _initialized_at: datetime
    _performance_stats: dict[str, Any]

    def __init__(
        self,
        db_path: Path | str | None = None,
        config: dict[str, Any] | KuzuMemoryConfig | None = None,
        container: DependencyContainer | None = None,
        enable_git_sync: bool = True,
    ) -> None:
        """
        Initialize KuzuMemory.

        Args:
            db_path: Path to database file (default: ~/.kuzu-memory/memories.db)
            config: Optional configuration dict or KuzuMemoryConfig object
            container: Optional dependency container for testing/customization
            enable_git_sync: Enable git sync initialization (default: True).
                            Set to False for read-only operations to improve performance.

        Raises:
            ConfigurationError: If configuration is invalid
            DatabaseError: If database initialization fails
        """
        try:
            # Set up database path
            db_path_resolved: Path
            if db_path is None:
                db_path_resolved = Path.home() / ".kuzu-memory" / "memories.db"
            elif isinstance(db_path, str):
                db_path_resolved = Path(db_path)
            else:
                db_path_resolved = db_path
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

            # Store git sync preference
            self._enable_git_sync = enable_git_sync

            # Initialize components
            self._initialize_components()

            # Track initialization time
            self._initialized_at = datetime.now()

            # Determine project root from db_path (go up from .kuzu-memory/memories.db)
            self.project_root = self.db_path.parent.parent

            # Auto-detect git user for memory namespacing
            self._user_id = None
            if self.config.memory.auto_tag_git_user:
                if self.config.memory.user_id_override:
                    # Use manual override if provided
                    self._user_id = self.config.memory.user_id_override
                    logger.info(f"Using manual user_id override: {self._user_id}")
                else:
                    # Auto-detect from git
                    try:
                        git_user_info = GitUserProvider.get_git_user_info(self.project_root)
                        self._user_id = git_user_info.user_id
                        logger.info(
                            f"Auto-detected git user_id: {self._user_id} (source: {git_user_info.source})"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to auto-detect git user, memories will not be tagged with user_id: {e}"
                        )
                        self._user_id = None

            logger.info(f"KuzuMemory initialized with database at {self.db_path}")

        except Exception as e:
            if isinstance(e, (ConfigurationError, DatabaseError)):
                raise
            raise KuzuMemoryError(f"Failed to initialize KuzuMemory: {e}") from e

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
                memory_store_adapter = self.container.get_database_adapter()
                memory_store = MemoryStore(memory_store_adapter, self.config)
                self.container.register("memory_store", memory_store)

            if not self.container.has("recall_coordinator"):
                # Initialize recall coordinator
                recall_adapter = self.container.get_database_adapter()
                recall_coordinator = RecallCoordinator(recall_adapter, self.config)
                self.container.register("recall_coordinator", recall_coordinator)

            # Get references to components
            self.db_adapter = self.container.get_database_adapter()
            self.memory_store = self.container.get_memory_store()
            self.recall_coordinator = self.container.get_recall_coordinator()

            # Initialize git sync components only if enabled
            if self._enable_git_sync:
                self._initialize_git_sync()
                # Run initial auto-sync if enabled (periodic check)
                self._auto_git_sync("init")
            else:
                # Set auto_git_sync to None when disabled
                self.auto_git_sync = None
                logger.debug("Git sync disabled for this instance")

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
            raise DatabaseError(f"Failed to initialize components: {e}") from e

    def _initialize_git_sync(self) -> None:
        """
        Initialize git sync components if enabled.

        Sets up GitSyncManager and AutoGitSyncManager for automatic
        git commit indexing.
        """
        try:
            from ..integrations.auto_git_sync import AutoGitSyncManager
            from ..integrations.git_sync import GitSyncManager

            # Determine repository path (use project root or current directory)
            repo_path = self.db_path.parent.parent  # Go up from .kuzu-memory/memories.db

            # Create git sync manager
            git_sync = GitSyncManager(
                repo_path=repo_path,
                config=self.config.git_sync,
                memory_store=self.memory_store,
            )

            # Create auto git sync manager
            state_path = self.db_path.parent / "git_sync_state.json"
            self.auto_git_sync = AutoGitSyncManager(
                git_sync_manager=git_sync,
                config=self.config.git_sync,
                state_path=state_path,
            )

            logger.debug("Git sync components initialized")

        except Exception as e:
            # Git sync is optional, log warning but don't fail initialization
            logger.warning(f"Failed to initialize git sync: {e}")
            self.auto_git_sync = None

    def _auto_git_sync(self, trigger: str = "periodic") -> None:
        """
        Trigger automatic git sync if enabled and conditions are met.

        Args:
            trigger: Sync trigger type ("enhance", "learn", "init", "periodic")
        """
        if not hasattr(self, "auto_git_sync") or self.auto_git_sync is None:
            return

        try:
            # Run auto-sync in background (non-blocking)
            # Only log on init trigger, others are silent by default
            verbose = trigger == "init"
            result = self.auto_git_sync.auto_sync_if_needed(trigger=trigger, verbose=verbose)

            # Log only if sync actually happened
            if result.get("success") and not result.get("skipped"):
                commits_synced = result.get("commits_synced", 0)
                if commits_synced > 0:
                    logger.info(f"Auto-synced {commits_synced} git commits ({trigger})")

        except Exception as e:
            # Don't let git sync failures block main operations
            logger.debug(f"Auto git sync failed ({trigger}): {e}")

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
                raise ValidationError("max_memories", str(max_memories), "must be positive")

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

            # Trigger auto-sync after attach (if enabled)
            self._auto_git_sync("enhance")

            return context  # type: ignore[no-any-return]  # Dict return type inferred as Any from embeddings

        except Exception as e:
            if isinstance(e, (ValidationError, PerformanceError)):
                raise
            raise KuzuMemoryError(f"attach_memories failed: {e}") from e

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

        from .models import MemoryType

        # Auto-populate user_id from git if not provided in metadata
        user_id: str | None = metadata.get("user_id") if metadata else None
        if user_id is None and self._user_id is not None:
            user_id = self._user_id

        memory = Memory(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=MemoryType.EPISODIC,
            source_type=source or "manual",  # Note: field is source_type, not source
            importance=0.8,  # Default importance for direct memories
            confidence=1.0,  # High confidence since it's explicit
            created_at=datetime.now(),  # Keep as datetime object
            valid_to=None,  # No expiration by default
            user_id=user_id,
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
            user_id: Optional user ID (auto-populated from git if None)
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
                raise ValidationError("Content exceeds maximum length", "content", content[:100])

            # Auto-populate user_id from git if not provided
            effective_user_id = user_id
            if effective_user_id is None and self._user_id is not None:
                effective_user_id = self._user_id

            # Execute memory generation
            memory_ids = self.memory_store.generate_memories(
                content=content,
                metadata=metadata,
                source=source,
                user_id=effective_user_id,
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

            # Trigger auto-sync after generate (if enabled)
            self._auto_git_sync("learn")

            return memory_ids  # type: ignore[no-any-return]  # List return type inferred as Any from store

        except Exception as e:
            if isinstance(e, (ValidationError, PerformanceError)):
                raise
            raise KuzuMemoryError(f"generate_memories failed: {e}") from e

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

    def get_recent_memories(self, limit: int = 10, **filters: Any) -> list[Memory]:
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

    def get_database_size(self) -> int:
        """
        Get the size of the database file in bytes.

        Returns:
            Database size in bytes, or 0 if not accessible
        """
        try:
            if self.db_path.exists():
                return self.db_path.stat().st_size
            return 0
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0

    def get_memory_type_stats(self) -> dict[str, int]:
        """
        Get statistics grouped by memory type.

        Returns:
            Dictionary with memory type counts
        """
        try:
            return self.memory_store.get_memory_type_stats()  # type: ignore[no-any-return,attr-defined]
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
            return self.memory_store.get_source_stats()  # type: ignore[no-any-return,attr-defined]
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
            return stored_ids  # type: ignore[no-any-return]  # List[str] inferred as Any from storage layer

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to batch store memories: {e}")
            raise KuzuMemoryError(f"batch_store_memories failed: {e}") from e

    @cached_method(maxsize=MEMORY_BY_ID_CACHE_SIZE * 10, ttl_seconds=MEMORY_BY_ID_CACHE_TTL)
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

            logger.debug(f"Batch retrieved {len(memories)} memories from {len(memory_ids)} IDs")
            return memories  # type: ignore[no-any-return]  # List[Memory] inferred as Any from storage layer

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to batch get memories: {e}")
            raise KuzuMemoryError(f"batch_get_memories_by_ids failed: {e}") from e

    def get_memories_by_user(self, user_id: str, limit: int = 100) -> list[Memory]:
        """
        Get all memories created by a specific user.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of memories to return

        Returns:
            List of memories created by the user
        """
        try:
            return self.memory_store.get_memories_by_user(user_id, limit)  # type: ignore[no-any-return,attr-defined]
        except Exception as e:
            logger.error(f"Failed to get memories by user {user_id}: {e}")
            return []

    def get_users(self) -> list[str]:
        """
        Get list of all user IDs that have created memories.

        Returns:
            List of unique user IDs
        """
        try:
            return self.memory_store.get_users()  # type: ignore[no-any-return,attr-defined]
        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            return []

    def get_current_user_id(self) -> str | None:
        """
        Get the current user ID used for tagging new memories.

        Returns:
            Current user ID or None if not configured
        """
        return self._user_id

    def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive statistics about the memory system.

        Returns:
            Dictionary with statistics from all components
        """
        try:
            stats: dict[str, Any] = {
                "system_info": {
                    "initialized_at": self._initialized_at.isoformat(),
                    "db_path": str(self.db_path),
                    "config_version": self.config.version,
                    "current_user_id": self._user_id,
                },
                "performance_stats": self._performance_stats.copy(),
                "storage_stats": self.memory_store.get_storage_statistics(),
                "recall_stats": self.recall_coordinator.get_recall_statistics(),
            }

            # Add user statistics if multi-user is enabled
            if self.config.memory.enable_multi_user:
                try:
                    users = self.get_users()
                    stats["user_stats"] = {
                        "total_users": len(users),
                        "users": users,
                        "current_user": self._user_id,
                    }
                except Exception as e:
                    logger.warning(f"Failed to get user statistics: {e}")

            return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

    def _update_attach_stats(self, execution_time_ms: float, memories_count: int) -> None:
        """Update attach_memories performance statistics."""
        self._performance_stats["attach_memories_calls"] += 1
        self._performance_stats["total_memories_recalled"] += memories_count

        # Update average time
        total_calls: int = self._performance_stats["attach_memories_calls"]
        current_avg: float = self._performance_stats["avg_attach_time_ms"]
        new_avg = ((current_avg * (total_calls - 1)) + execution_time_ms) / total_calls
        self._performance_stats["avg_attach_time_ms"] = new_avg

    def _update_generate_stats(self, execution_time_ms: float, memories_count: int) -> None:
        """Update generate_memories performance statistics."""
        self._performance_stats["generate_memories_calls"] += 1
        self._performance_stats["total_memories_generated"] += memories_count

        # Update average time
        total_calls: int = self._performance_stats["generate_memories_calls"]
        current_avg: float = self._performance_stats["avg_generate_time_ms"]
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

    def __enter__(self) -> KuzuMemory:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"KuzuMemory(db_path={self.db_path}, memories={self.get_memory_count()})"
