"""
Abstract base classes for memory storage and recall operations.

Defines the core interfaces that all memory storage implementations must follow,
enabling easy testing, mocking, and swapping of storage backends.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..core.models import Memory, MemoryContext


class IMemoryStore(ABC):
    """
    Abstract interface for memory storage operations.

    Defines the contract for storing, retrieving, and managing memories
    in any storage backend (Kuzu, SQLite, in-memory, etc.).
    """

    @abstractmethod
    async def store_memory(self, memory: Memory) -> str:
        """
        Store a memory and return its ID.

        Args:
            memory: Memory object to store

        Returns:
            Memory ID

        Raises:
            StorageError: If storage operation fails
        """
        pass

    @abstractmethod
    async def get_memory(self, memory_id: str) -> Memory | None:
        """
        Retrieve a memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory object if found, None otherwise
        """
        pass

    @abstractmethod
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        min_confidence: float = 0.0,
        valid_only: bool = True,
    ) -> list[Memory]:
        """
        Search for memories based on content similarity.

        Args:
            query: Search query text
            limit: Maximum number of results
            memory_types: Filter by memory types
            min_confidence: Minimum confidence threshold
            valid_only: Include only non-expired memories

        Returns:
            List of matching memories
        """
        pass

    @abstractmethod
    async def update_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        """
        Update an existing memory.

        Args:
            memory_id: Memory to update
            updates: Dictionary of field updates

        Returns:
            True if update succeeded, False if memory not found
        """
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: Memory to delete

        Returns:
            True if deletion succeeded, False if memory not found
        """
        pass

    @abstractmethod
    async def count_memories(
        self, memory_types: list[str] | None = None, valid_only: bool = True
    ) -> int:
        """
        Count total memories matching criteria.

        Args:
            memory_types: Filter by memory types
            valid_only: Include only non-expired memories

        Returns:
            Number of matching memories
        """
        pass

    @abstractmethod
    async def get_recent_memories(self, limit: int = 10, hours_back: int = 24) -> list[Memory]:
        """
        Get recently created or accessed memories.

        Args:
            limit: Maximum number of results
            hours_back: How many hours back to search

        Returns:
            List of recent memories
        """
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Remove expired memories from storage.

        Returns:
            Number of memories removed
        """
        pass

    @abstractmethod
    async def get_statistics(self) -> dict[str, Any]:
        """
        Get storage statistics and health metrics.

        Returns:
            Dictionary containing storage stats
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources and close connections."""
        pass


class IMemoryRecall(ABC):
    """
    Abstract interface for memory recall strategies.

    Defines the contract for different approaches to retrieving
    and ranking memories for context enhancement.
    """

    @abstractmethod
    async def recall_memories(
        self,
        query: str,
        limit: int = 5,
        strategy: str = "auto",
        context: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """
        Recall relevant memories for a given query.

        Args:
            query: Query text to find relevant memories for
            limit: Maximum number of memories to return
            strategy: Recall strategy to use
            context: Additional context for recall decisions

        Returns:
            List of relevant memories, ranked by relevance
        """
        pass

    @abstractmethod
    async def attach_memories(
        self,
        prompt: str,
        limit: int = 5,
        strategy: str = "auto",
        format_style: str = "markdown",
    ) -> MemoryContext:
        """
        Enhance a prompt with relevant memory context.

        Args:
            prompt: Original prompt to enhance
            limit: Maximum number of memories to attach
            strategy: Recall strategy to use
            format_style: How to format the enhanced prompt

        Returns:
            MemoryContext with enhanced prompt and metadata
        """
        pass

    @abstractmethod
    async def rank_memories(
        self,
        memories: list[Memory],
        query: str,
        context: dict[str, Any] | None = None,
    ) -> list[Memory]:
        """
        Rank memories by relevance to a query.

        Args:
            memories: List of memories to rank
            query: Query to rank against
            context: Additional ranking context

        Returns:
            Memories sorted by relevance (most relevant first)
        """
        pass

    @abstractmethod
    def get_available_strategies(self) -> list[str]:
        """
        Get list of available recall strategies.

        Returns:
            List of strategy names
        """
        pass
