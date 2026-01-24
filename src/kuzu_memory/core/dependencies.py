"""
Dependency injection container and interfaces for KuzuMemory.

Provides clean separation of concerns and improved testability.
"""

from abc import abstractmethod
from typing import Any, Protocol, cast, runtime_checkable

from .models import Memory, MemoryType


@runtime_checkable
class MemoryStoreProtocol(Protocol):
    """Protocol defining the interface for memory storage."""

    @abstractmethod
    def store_memory(self, memory: Memory) -> str:
        """Store a memory and return its ID."""
        ...

    @abstractmethod
    def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """Retrieve a memory by its ID."""
        ...

    @abstractmethod
    def get_recent_memories(self, limit: int = 10, **filters: Any) -> list[Memory]:
        """Get recent memories with optional filtering."""
        ...

    @abstractmethod
    def cleanup_expired_memories(self) -> int:
        """Remove expired memories and return count."""
        ...

    @abstractmethod
    def get_memory_count(self) -> int:
        """Get total count of active memories."""
        ...

    @abstractmethod
    def _store_memory_in_database(self, memory: Memory, is_update: bool = False) -> None:
        """Store a memory in the database (internal method)."""
        ...

    @abstractmethod
    def generate_memories(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "conversation",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
    ) -> list[str]:
        """Extract and store memories from content."""
        ...

    @abstractmethod
    def batch_store_memories(self, memories: list[Memory]) -> list[str]:
        """Store multiple memories in a batch operation."""
        ...

    @abstractmethod
    def batch_get_memories_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        """Retrieve multiple memories by their IDs in a batch operation."""
        ...

    @abstractmethod
    def get_storage_statistics(self) -> dict[str, Any]:
        """Get storage statistics."""
        ...

    # Expose db_adapter property for pruning operations
    db_adapter: Any


@runtime_checkable
class RecallCoordinatorProtocol(Protocol):
    """Protocol defining the interface for memory recall coordination."""

    @abstractmethod
    def recall_memories(
        self, query: str, limit: int = 10, filters: dict[str, Any] | None = None
    ) -> list[Memory]:
        """Recall memories matching a query."""
        ...

    @abstractmethod
    def attach_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
    ) -> Any:  # Returns MemoryContext
        """Attach relevant memories to a prompt."""
        ...

    @abstractmethod
    def get_recall_statistics(self) -> dict[str, Any]:
        """Get recall statistics."""
        ...


@runtime_checkable
class NLPClassifierProtocol(Protocol):
    """Protocol defining the interface for NLP classification."""

    @abstractmethod
    def classify_memory_type(self, content: str) -> MemoryType:
        """Classify content into a memory type."""
        ...

    @abstractmethod
    def extract_entities(self, content: str) -> list[str]:
        """Extract entities from content."""
        ...


@runtime_checkable
class DatabaseAdapterProtocol(Protocol):
    """Protocol defining the interface for database operations."""

    @abstractmethod
    def execute_query(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a database query with parameters."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if database is connected."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from database."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the database connection and cleanup resources."""
        ...


class DependencyContainer:
    """
    Simple dependency injection container for managing component instances.

    This provides a centralized way to manage dependencies and makes
    testing easier by allowing mock objects to be injected.
    """

    def __init__(self) -> None:
        """Initialize empty dependency container."""
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Any] = {}

    def register(self, name: str, service: Any, singleton: bool = True) -> None:
        """
        Register a service or factory.

        Args:
            name: Service name for lookup
            service: Service instance or factory function
            singleton: If True, store instance; if False, store factory
        """
        if singleton:
            self._services[name] = service
        else:
            self._factories[name] = service

    def get(self, name: str) -> Any:
        """
        Get a service by name.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not found
        """
        if name in self._services:
            return self._services[name]
        elif name in self._factories:
            # Create new instance from factory
            return self._factories[name]()
        else:
            raise KeyError(f"Service '{name}' not registered")

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services or name in self._factories

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()

    def get_memory_store(self) -> MemoryStoreProtocol:
        """Get the memory store service."""
        return cast(MemoryStoreProtocol, self.get("memory_store"))

    def get_recall_coordinator(self) -> RecallCoordinatorProtocol:
        """Get the recall coordinator service."""
        return cast(RecallCoordinatorProtocol, self.get("recall_coordinator"))

    def get_nlp_classifier(self) -> NLPClassifierProtocol | None:
        """Get the NLP classifier service if available."""
        return (
            cast(NLPClassifierProtocol, self.get("nlp_classifier"))
            if self.has("nlp_classifier")
            else None
        )

    def get_database_adapter(self) -> DatabaseAdapterProtocol:
        """Get the database adapter service."""
        return cast(DatabaseAdapterProtocol, self.get("database_adapter"))


# Global container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    return _container


def reset_container() -> None:
    """Reset the global dependency container (useful for testing)."""
    global _container
    _container = DependencyContainer()
