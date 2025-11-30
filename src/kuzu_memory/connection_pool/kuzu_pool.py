"""
Connection pool implementation for Kuzu database.

Manages a pool of database connections with health monitoring,
automatic recovery, and resource limits.
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

from ..interfaces.connection_pool import IConnectionPool
from .kuzu_connection import KuzuConnection

logger = logging.getLogger(__name__)


class KuzuConnectionPool(IConnectionPool):
    """
    High-performance connection pool for Kuzu database.

    Features:
    - Configurable pool size with min/max connections
    - Health monitoring and automatic recovery
    - Connection lifecycle management
    - Load balancing across connections
    - Comprehensive metrics and monitoring
    """

    def __init__(
        self,
        database_path: str,
        min_connections: int = 2,
        max_connections: int = 10,
        num_threads_per_connection: int = 4,
        health_check_interval: timedelta = timedelta(minutes=5),
        connection_timeout: timedelta = timedelta(seconds=30),
        idle_timeout: timedelta = timedelta(minutes=30),
    ):
        """
        Initialize connection pool.

        Args:
            database_path: Path to Kuzu database
            min_connections: Minimum connections to maintain
            max_connections: Maximum connections allowed
            num_threads_per_connection: Threads per connection
            health_check_interval: How often to check connection health
            connection_timeout: Timeout for getting connection from pool
            idle_timeout: How long connections can stay idle
        """
        self.database_path = database_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.num_threads_per_connection = num_threads_per_connection
        self.health_check_interval = health_check_interval
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout

        # Pool state
        self._available_connections: deque[KuzuConnection] = deque()
        self._active_connections: set[KuzuConnection] = set()
        self._all_connections: set[KuzuConnection] = set()

        # Synchronization
        self._lock = asyncio.Lock()
        self._connection_semaphore = asyncio.Semaphore(max_connections)
        self._pool_condition = asyncio.Condition()

        # Health monitoring
        self._health_check_task: asyncio.Task[None] | None = None
        self._last_health_check = time.time()

        # Statistics
        self._created_connections = 0
        self._destroyed_connections = 0
        self._connection_requests = 0
        self._connection_timeouts = 0
        self._health_check_failures = 0

        # Pool state
        self._initialized = False
        self._closing = False

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info(
                f"Initializing Kuzu connection pool: {self.min_connections}-{self.max_connections} connections"
            )

            # Create minimum connections
            for _ in range(self.min_connections):
                connection = await self._create_connection()
                self._available_connections.append(connection)

            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            self._initialized = True

    async def _create_connection(self) -> KuzuConnection:
        """Create a new database connection."""
        try:
            connection = KuzuConnection(
                database_path=self.database_path,
                num_threads=self.num_threads_per_connection,
            )

            # Test the connection
            await connection._ensure_connected()

            self._all_connections.add(connection)
            self._created_connections += 1

            logger.debug(f"Created new connection (total: {len(self._all_connections)})")
            return connection

        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise

    async def _destroy_connection(self, connection: KuzuConnection) -> None:
        """Destroy a database connection."""
        try:
            await connection.close()
            self._all_connections.discard(connection)
            self._destroyed_connections += 1

            logger.debug(f"Destroyed connection (total: {len(self._all_connections)})")

        except Exception as e:
            logger.error(f"Failed to destroy connection: {e}")

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[KuzuConnection]:
        """
        Get a connection from the pool.

        Returns:
            Context manager that yields a connection and returns it to pool
        """
        if not self._initialized:
            await self.initialize()

        if self._closing:
            raise RuntimeError("Connection pool is closing")

        self._connection_requests += 1

        # Wait for available slot
        try:
            await asyncio.wait_for(
                self._connection_semaphore.acquire(),
                timeout=self.connection_timeout.total_seconds(),
            )
        except TimeoutError:
            self._connection_timeouts += 1
            raise RuntimeError("Connection timeout")

        connection = None
        try:
            # Get connection from pool
            connection = await self._get_connection_from_pool()

            # Mark as active
            async with self._lock:
                self._active_connections.add(connection)

            yield connection

        finally:
            # Return connection to pool
            if connection:
                await self._return_connection_to_pool(connection)

            self._connection_semaphore.release()

    async def _get_connection_from_pool(self) -> KuzuConnection:
        """Get a connection from the available pool."""
        async with self._lock:
            # Try to get an available connection
            while self._available_connections:
                connection = self._available_connections.popleft()

                # Check if connection is still healthy
                if await connection.is_alive():
                    return connection
                else:
                    # Connection is dead, destroy it
                    await self._destroy_connection(connection)

            # No healthy connections available, create new one if possible
            if len(self._all_connections) < self.max_connections:
                return await self._create_connection()

        # Pool is full, wait for a connection to become available
        async with self._pool_condition:
            await self._pool_condition.wait_for(
                lambda: self._available_connections
                or len(self._all_connections) < self.max_connections
            )

        # Try again recursively
        return await self._get_connection_from_pool()

    async def _return_connection_to_pool(self, connection: KuzuConnection) -> None:
        """Return a connection to the available pool."""
        async with self._lock:
            self._active_connections.discard(connection)

            # Check if connection is still healthy
            if await connection.is_alive() and not self._closing:
                self._available_connections.append(connection)
            else:
                # Connection is unhealthy, destroy it
                await self._destroy_connection(connection)

                # Create replacement if below minimum
                if len(self._all_connections) < self.min_connections:
                    try:
                        new_connection = await self._create_connection()
                        self._available_connections.append(new_connection)
                    except Exception as e:
                        logger.error(f"Failed to create replacement connection: {e}")

        # Notify waiting tasks
        async with self._pool_condition:
            self._pool_condition.notify()

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a query using a connection from the pool."""
        async with self.get_connection() as connection:
            return await connection.execute(query, params)

    async def execute_many(self, queries: list[tuple[str, dict[str, Any] | None]]) -> list[Any]:
        """Execute multiple queries using connections from the pool."""
        async with self.get_connection() as connection:
            return await connection.execute_many(queries)

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the connection pool."""
        async with self._lock:
            healthy_connections = 0
            unhealthy_connections = []

            # Check each connection
            for connection in self._all_connections.copy():
                if await connection.is_alive():
                    healthy_connections += 1
                else:
                    unhealthy_connections.append(connection)

            # Remove unhealthy connections
            for connection in unhealthy_connections:
                await self._destroy_connection(connection)
                self._health_check_failures += 1

            # Ensure minimum connections
            while len(self._all_connections) < self.min_connections:
                try:
                    connection = await self._create_connection()
                    self._available_connections.append(connection)
                except Exception as e:
                    logger.error(f"Failed to create connection during health check: {e}")
                    break

            return {
                "healthy_connections": healthy_connections,
                "unhealthy_removed": len(unhealthy_connections),
                "total_connections": len(self._all_connections),
                "available_connections": len(self._available_connections),
                "active_connections": len(self._active_connections),
                "health_check_failures": self._health_check_failures,
            }

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive pool statistics."""
        async with self._lock:
            return {
                "pool_size": len(self._all_connections),
                "available_connections": len(self._available_connections),
                "active_connections": len(self._active_connections),
                "min_connections": self.min_connections,
                "max_connections": self.max_connections,
                "created_connections": self._created_connections,
                "destroyed_connections": self._destroyed_connections,
                "connection_requests": self._connection_requests,
                "connection_timeouts": self._connection_timeouts,
                "health_check_failures": self._health_check_failures,
                "utilization": (
                    len(self._active_connections) / self.max_connections
                    if self.max_connections > 0
                    else 0
                ),
                "database_path": self.database_path,
            }

    async def close_all(self) -> None:
        """Close all connections in the pool."""
        self._closing = True

        # Stop health monitoring
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            # Close all connections
            for connection in self._all_connections.copy():
                await self._destroy_connection(connection)

            self._available_connections.clear()
            self._active_connections.clear()

        logger.info("Connection pool closed")

    def get_pool_size(self) -> int:
        """Get current pool size."""
        return len(self._all_connections)

    def get_active_connections(self) -> int:
        """Get number of currently active connections."""
        return len(self._active_connections)

    def get_idle_connections(self) -> int:
        """Get number of currently idle connections."""
        return len(self._available_connections)

    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while not self._closing:
            try:
                await asyncio.sleep(self.health_check_interval.total_seconds())

                if self._closing:
                    break

                # Perform health check
                health_result = await self.health_check()
                logger.debug(f"Health check completed: {health_result}")

                self._last_health_check = time.time()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}")

    def __repr__(self) -> str:
        return (
            f"KuzuConnectionPool("
            f"size={len(self._all_connections)}, "
            f"active={len(self._active_connections)}, "
            f"available={len(self._available_connections)}"
            f")"
        )
