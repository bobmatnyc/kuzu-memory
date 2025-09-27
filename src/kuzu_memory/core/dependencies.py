"""
Dependency injection container and interfaces for KuzuMemory.

Provides clean separation of concerns and improved testability.
"""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

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
    def get_recent_memories(self, limit: int = 10, **filters) -> list[Memory]:
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


@runtime_checkable
class RecallCoordinatorProtocol(Protocol):
    """Protocol defining the interface for memory recall coordination."""

    @abstractmethod
    def recall_memories(
        self, query: str, limit: int = 10, filters: dict[str, Any] | None = None
    ) -> list[Memory]:
        """Recall memories matching a query."""
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


class DependencyContainer:
    """
    Simple dependency injection container for managing component instances.

    This provides a centralized way to manage dependencies and makes
    testing easier by allowing mock objects to be injected.
    """

    def __init__(self):
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
        return self.get("memory_store")

    def get_recall_coordinator(self) -> RecallCoordinatorProtocol:
        """Get the recall coordinator service."""
        return self.get("recall_coordinator")

    def get_nlp_classifier(self) -> NLPClassifierProtocol | None:
        """Get the NLP classifier service if available."""
        return self.get("nlp_classifier") if self.has("nlp_classifier") else None

    def get_database_adapter(self) -> DatabaseAdapterProtocol:
        """Get the database adapter service."""
        return self.get("database_adapter")


# Global container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    return _container


def reset_container() -> None:
    """Reset the global dependency container (useful for testing)."""
    global _container
    _container = DependencyContainer()
