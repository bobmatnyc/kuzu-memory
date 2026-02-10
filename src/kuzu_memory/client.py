"""
Python Client API for KuzuMemory.

Provides an async-first, production-ready client interface for programmatic
access to KuzuMemory operations without CLI dependencies.

Features:
- Async/await interface using asyncio.to_thread()
- Context manager support for resource management
- Type-safe with comprehensive type hints
- IDE-friendly with detailed docstrings
- Direct integration with MemoryService layer

Example:
    ```python
    from kuzu_memory.client import KuzuMemoryClient

    async def main():
        async with KuzuMemoryClient(project_root="/path/to/project") as client:
            # Store memories
            await client.learn("User prefers Python for backend")

            # Retrieve memories
            memories = await client.recall("What language does user prefer?")

            # Enhance prompts
            enhanced = await client.enhance("Write a web server")

            # Get statistics
            stats = client.get_stats()
    ```
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from kuzu_memory.core.models import Memory, MemoryContext, MemoryType
from kuzu_memory.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class KuzuMemoryClient:
    """
    Async Python client for KuzuMemory operations.

    Provides a programmatic interface to KuzuMemory with async/await patterns,
    wrapping the MemoryService layer for production use in AI applications.

    Design:
    - Async-first: All I/O operations are async using asyncio.to_thread()
    - Resource-safe: Implements async context manager for cleanup
    - Type-safe: Full type hints for IDE support
    - CLI-independent: Pure library mode, no CLI dependencies

    Thread Safety:
    - Safe for use in async contexts (uses asyncio.to_thread)
    - Each client instance manages its own database connection
    - Not safe for concurrent use of the same client instance

    Example:
        >>> import asyncio
        >>> from kuzu_memory.client import KuzuMemoryClient
        >>>
        >>> async def example():
        ...     # Context manager automatically handles cleanup
        ...     async with KuzuMemoryClient(project_root="/my/project") as client:
        ...         # Store a memory
        ...         await client.learn("User prefers TypeScript")
        ...
        ...         # Query memories
        ...         results = await client.recall("programming preferences")
        ...         for memory in results:
        ...             print(memory.content)
        ...
        ...         # Enhance a prompt
        ...         enhanced = await client.enhance("Write a web app")
        ...         print(enhanced.enhanced_prompt)
        >>>
        >>> asyncio.run(example())
    """

    def __init__(
        self,
        project_root: str | Path,
        db_path: str | Path | None = None,
        enable_git_sync: bool = False,
        auto_sync: bool = False,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize KuzuMemory client.

        Args:
            project_root: Path to project root directory (used to determine db_path)
            db_path: Optional explicit path to Kuzu database directory.
                    Defaults to {project_root}/.kuzu-memory if not provided.
            enable_git_sync: Enable git synchronization (default: False for performance).
                           Set to True only if you need git commit indexing.
            auto_sync: Enable automatic git sync on init (default: False).
                      Only used if enable_git_sync=True.
            config: Optional configuration dictionary for KuzuMemory.

        Example:
            >>> # Simple initialization
            >>> client = KuzuMemoryClient(project_root="/my/project")
            >>>
            >>> # Custom database path
            >>> client = KuzuMemoryClient(
            ...     project_root="/my/project",
            ...     db_path="/custom/db/path"
            ... )
            >>>
            >>> # With git sync enabled
            >>> client = KuzuMemoryClient(
            ...     project_root="/my/project",
            ...     enable_git_sync=True
            ... )
        """
        self._project_root = Path(project_root)
        self._db_path = (
            Path(db_path) if db_path else self._project_root / ".kuzu-memory" / "memories.db"
        )
        self._enable_git_sync = enable_git_sync
        self._auto_sync = auto_sync
        self._config = config or {}

        # Will be initialized in __aenter__
        self._service: MemoryService | None = None
        self._initialized = False

        logger.debug(
            f"KuzuMemoryClient created for project_root={self._project_root}, "
            f"db_path={self._db_path}"
        )

    async def __aenter__(self) -> KuzuMemoryClient:
        """
        Async context manager entry.

        Initializes the underlying MemoryService for database operations.

        Returns:
            Self for context manager usage

        Raises:
            RuntimeError: If client is already initialized
        """
        if self._initialized:
            raise RuntimeError("Client already initialized")

        # Initialize MemoryService in thread pool to avoid blocking
        def _init_service() -> MemoryService:
            service = MemoryService(
                db_path=self._db_path,
                enable_git_sync=self._enable_git_sync,
                config=self._config,
            )
            service.initialize()
            return service

        self._service = await asyncio.to_thread(_init_service)
        self._initialized = True

        logger.info(f"KuzuMemoryClient initialized with db_path={self._db_path}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Async context manager exit.

        Cleans up resources and closes database connections.
        """
        if self._service:
            await asyncio.to_thread(self._service.cleanup)
            self._service = None
            self._initialized = False
            logger.info("KuzuMemoryClient cleaned up")

    def _ensure_initialized(self) -> MemoryService:
        """
        Ensure client is initialized and return service.

        Returns:
            MemoryService instance

        Raises:
            RuntimeError: If client not initialized (not used in context manager)
        """
        if not self._initialized or not self._service:
            raise RuntimeError(
                "Client not initialized. Use 'async with KuzuMemoryClient(...) as client:' "
                "to properly initialize the client."
            )
        return self._service

    async def learn(
        self,
        content: str,
        source: str = "api",
        session_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store a new memory asynchronously.

        This is the primary method for storing memories from your application.
        The memory will be automatically classified and indexed for retrieval.

        Args:
            content: The content to store as a memory
            source: Source identifier (default: "api")
            session_id: Optional session ID for grouping related memories
            agent_id: Optional agent ID that created this memory
            metadata: Optional additional metadata as dictionary

        Returns:
            Memory ID (UUID string) of the stored memory

        Raises:
            RuntimeError: If client not initialized
            ValidationError: If content is empty or invalid

        Example:
            >>> memory_id = await client.learn(
            ...     "User prefers FastAPI over Flask",
            ...     metadata={"confidence": 0.9, "source": "conversation"}
            ... )
            >>> print(f"Stored memory: {memory_id}")
        """
        service = self._ensure_initialized()

        def _remember() -> str:
            return service.remember(
                content=content,
                source=source,
                session_id=session_id,
                agent_id=agent_id,
                metadata=metadata,
            )

        return await asyncio.to_thread(_remember)

    async def recall(
        self,
        query: str,
        max_memories: int = 5,
        strategy: str = "auto",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
    ) -> list[Memory]:
        """
        Retrieve relevant memories for a query.

        Uses semantic search to find memories most relevant to the query.
        Results are ranked by relevance score and temporal decay.

        Args:
            query: Search query (semantic, not keyword-based)
            max_memories: Maximum number of memories to return (default: 5)
            strategy: Recall strategy - "auto", "keyword", "entity", "temporal"
            user_id: Optional filter by user ID
            session_id: Optional filter by session ID
            agent_id: Optional filter by agent ID (default: "default")

        Returns:
            List of Memory objects ranked by relevance

        Raises:
            RuntimeError: If client not initialized
            ValidationError: If query is empty

        Example:
            >>> memories = await client.recall(
            ...     "What web framework does the user prefer?",
            ...     max_memories=3
            ... )
            >>> for memory in memories:
            ...     print(f"[{memory.importance:.2f}] {memory.content}")
        """
        service = self._ensure_initialized()

        def _recall() -> list[Memory]:
            context = service.attach_memories(
                prompt=query,
                max_memories=max_memories,
                strategy=strategy,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
            )
            return context.memories

        return await asyncio.to_thread(_recall)

    async def enhance(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
        context: dict[str, Any] | None = None,
    ) -> MemoryContext:
        """
        Enhance a prompt with relevant context from stored memories.

        This is the primary RAG (Retrieval-Augmented Generation) method.
        Returns an enhanced prompt with injected context for LLM consumption.

        Args:
            prompt: Original prompt to enhance
            max_memories: Maximum memories to inject (default: 10)
            strategy: Recall strategy - "auto", "keyword", "entity", "temporal"
            user_id: Optional filter by user ID
            session_id: Optional filter by session ID
            agent_id: Optional filter by agent ID (default: "default")
            context: Optional additional context dictionary (currently unused)

        Returns:
            MemoryContext containing:
            - original_prompt: The input prompt
            - enhanced_prompt: Prompt with memory context injected
            - memories: List of memories that were injected
            - confidence: Confidence score (0-1)
            - recall_time_ms: Time taken for recall

        Raises:
            RuntimeError: If client not initialized
            ValidationError: If prompt is empty

        Example:
            >>> context = await client.enhance(
            ...     "Write a REST API for user management",
            ...     max_memories=5
            ... )
            >>> print("Enhanced prompt:")
            >>> print(context.enhanced_prompt)
            >>> print(f"\\nUsed {len(context.memories)} memories")
            >>> print(f"Confidence: {context.confidence:.2f}")
        """
        service = self._ensure_initialized()

        def _enhance() -> MemoryContext:
            return service.attach_memories(
                prompt=prompt,
                max_memories=max_memories,
                strategy=strategy,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id,
            )

        return await asyncio.to_thread(_enhance)

    def get_stats(self) -> dict[str, Any]:
        """
        Get memory system statistics (synchronous).

        This is a synchronous operation as it's typically fast and
        used for monitoring/debugging purposes.

        Returns:
            Dictionary with statistics:
            - memory_count: Total number of memories
            - database_size_bytes: Database file size
            - memory_type_stats: Breakdown by memory type
            - recent_memories: Count of recent memories

        Raises:
            RuntimeError: If client not initialized

        Example:
            >>> stats = client.get_stats()
            >>> print(f"Total memories: {stats['memory_count']}")
            >>> print(f"Database size: {stats['database_size_bytes'] / 1024:.2f} KB")
        """
        service = self._ensure_initialized()

        return {
            "memory_count": service.get_memory_count(),
            "database_size_bytes": service.get_database_size(),
            "memory_type_stats": service.kuzu_memory.get_memory_type_stats(),
            "recent_memories": len(service.get_recent_memories(limit=10)),
        }

    async def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """
        Retrieve a specific memory by ID.

        Args:
            memory_id: Unique memory identifier (UUID)

        Returns:
            Memory object if found, None otherwise

        Raises:
            RuntimeError: If client not initialized

        Example:
            >>> memory = await client.get_memory_by_id("123e4567-e89b-12d3-a456-426614174000")
            >>> if memory:
            ...     print(memory.content)
        """
        service = self._ensure_initialized()

        def _get_memory() -> Memory | None:
            return service.get_memory(memory_id)

        return await asyncio.to_thread(_get_memory)

    async def get_recent_memories(
        self, limit: int = 20, memory_type: MemoryType | None = None
    ) -> list[Memory]:
        """
        Get recent memories ordered by creation time.

        Args:
            limit: Maximum number of memories to return (default: 20)
            memory_type: Optional filter by memory type

        Returns:
            List of Memory objects ordered by created_at DESC

        Raises:
            RuntimeError: If client not initialized

        Example:
            >>> recent = await client.get_recent_memories(limit=10)
            >>> for memory in recent:
            ...     print(f"{memory.created_at}: {memory.content[:50]}...")
        """
        service = self._ensure_initialized()

        def _get_recent() -> list[Memory]:
            return service.get_recent_memories(limit=limit, memory_type=memory_type)

        return await asyncio.to_thread(_get_recent)

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if memory was deleted, False if not found

        Raises:
            RuntimeError: If client not initialized

        Example:
            >>> deleted = await client.delete_memory("123e4567-e89b-12d3-a456-426614174000")
            >>> if deleted:
            ...     print("Memory deleted successfully")
        """
        service = self._ensure_initialized()

        def _delete() -> bool:
            return service.delete_memory(memory_id)

        return await asyncio.to_thread(_delete)

    async def batch_store_memories(self, memories: list[Memory]) -> list[str]:
        """
        Store multiple memories in a single batch operation.

        Provides efficient bulk storage with reduced database round-trips.

        Args:
            memories: List of Memory objects to store

        Returns:
            List of memory IDs that were successfully stored

        Raises:
            RuntimeError: If client not initialized
            ValidationError: If memories list is invalid

        Example:
            >>> from kuzu_memory.core.models import Memory, MemoryType
            >>> memories = [
            ...     Memory(
            ...         content="First memory",
            ...         memory_type=MemoryType.SEMANTIC,
            ...         source_type="batch"
            ...     ),
            ...     Memory(
            ...         content="Second memory",
            ...         memory_type=MemoryType.EPISODIC,
            ...         source_type="batch"
            ...     )
            ... ]
            >>> stored_ids = await client.batch_store_memories(memories)
            >>> print(f"Stored {len(stored_ids)} memories")
        """
        service = self._ensure_initialized()

        def _batch_store() -> list[str]:
            return service.kuzu_memory.batch_store_memories(memories)

        return await asyncio.to_thread(_batch_store)

    async def cleanup_expired_memories(self) -> int:
        """
        Clean up expired memories based on retention policies.

        Returns:
            Number of memories cleaned up

        Raises:
            RuntimeError: If client not initialized

        Example:
            >>> count = await client.cleanup_expired_memories()
            >>> print(f"Cleaned up {count} expired memories")
        """
        service = self._ensure_initialized()

        def _cleanup() -> int:
            return service.kuzu_memory.cleanup_expired_memories()

        return await asyncio.to_thread(_cleanup)

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return self._project_root

    @property
    def db_path(self) -> Path:
        """Get the database path."""
        return self._db_path

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._initialized

    def __repr__(self) -> str:
        """String representation."""
        status = "initialized" if self._initialized else "not initialized"
        return f"KuzuMemoryClient(project_root={self._project_root}, {status})"


# Convenience function for quick usage
async def create_client(
    project_root: str | Path,
    db_path: str | Path | None = None,
    **kwargs: Any,
) -> KuzuMemoryClient:
    """
    Convenience function to create and initialize a client.

    Example:
        >>> client = await create_client("/my/project")
        >>> try:
        ...     await client.learn("Some content")
        ... finally:
        ...     await client.__aexit__(None, None, None)
    """
    client = KuzuMemoryClient(project_root=project_root, db_path=db_path, **kwargs)
    await client.__aenter__()
    return client
