"""
Abstract interface for connection pooling.

Defines the contract for managing database connections efficiently
with pooling, health checks, and resource management.
"""

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any


class IConnection(ABC):
    """
    Abstract interface for a database connection.

    Represents a single connection that can execute queries
    and manage transactions.
    """

    @abstractmethod
    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """
        Execute a query on this connection.

        Args:
            query: SQL or Cypher query to execute
            params: Query parameters

        Returns:
            Query result
        """
        pass

    @abstractmethod
    async def execute_many(self, queries: list[tuple[str, dict[str, Any] | None]]) -> list[Any]:
        """
        Execute multiple queries on this connection.

        Args:
            queries: List of (query, params) tuples

        Returns:
            List of query results
        """
        pass

    @abstractmethod
    async def begin_transaction(self) -> None:
        """Begin a database transaction."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close this connection."""
        pass

    @abstractmethod
    async def is_alive(self) -> bool:
        """Check if connection is still alive and responsive."""
        pass


class IConnectionPool(ABC):
    """
    Abstract interface for database connection pooling.

    Manages a pool of database connections with health monitoring,
    automatic recovery, and resource limits.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        pass

    @abstractmethod
    async def get_connection(self) -> AbstractAsyncContextManager[IConnection]:
        """
        Get a connection from the pool.

        Returns:
            Context manager that yields a connection and returns it to pool
        """
        pass

    @abstractmethod
    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """
        Execute a query using a connection from the pool.

        Args:
            query: SQL or Cypher query to execute
            params: Query parameters

        Returns:
            Query result
        """
        pass

    @abstractmethod
    async def execute_many(self, queries: list[tuple[str, dict[str, Any] | None]]) -> list[Any]:
        """
        Execute multiple queries using connections from the pool.

        Args:
            queries: List of (query, params) tuples

        Returns:
            List of query results
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Check the health of the connection pool.

        Returns:
            Dictionary containing pool health metrics
        """
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Dictionary containing pool metrics like active connections,
            idle connections, total created, etc.
        """
        pass

    @abstractmethod
    async def close_all(self) -> None:
        """Close all connections in the pool."""
        pass

    @abstractmethod
    def get_pool_size(self) -> int:
        """Get current pool size."""
        pass

    @abstractmethod
    def get_active_connections(self) -> int:
        """Get number of currently active connections."""
        pass

    @abstractmethod
    def get_idle_connections(self) -> int:
        """Get number of currently idle connections."""
        pass
