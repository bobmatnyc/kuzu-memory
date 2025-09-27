"""
Kuzu database connection wrapper with transaction support.

Provides a unified interface for Kuzu database operations with proper
resource management and error handling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from ..interfaces.connection_pool import IConnection

# Handle Kuzu import gracefully
try:
    import kuzu

    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False
    kuzu = None

logger = logging.getLogger(__name__)


class KuzuConnection(IConnection):
    """
    Wrapper for Kuzu database connection with transaction support.

    Provides async interface over Kuzu's synchronous operations
    and manages connection lifecycle.
    """

    def __init__(self, database_path: str, num_threads: int = 4):
        """
        Initialize Kuzu connection.

        Args:
            database_path: Path to Kuzu database
            num_threads: Number of threads for Kuzu operations
        """
        if not KUZU_AVAILABLE:
            raise ImportError("Kuzu is not available. Install with: pip install kuzu")

        self.database_path = database_path
        self.num_threads = num_threads

        # Connection objects (initialized lazily)
        self._db: kuzu.Database | None = None
        self._conn: kuzu.Connection | None = None

        # Connection state
        self._is_connected = False
        self._in_transaction = False
        self._created_at = datetime.now()
        self._last_used = datetime.now()
        self._query_count = 0

        # Thread safety
        self._lock = asyncio.Lock()

    async def _ensure_connected(self) -> None:
        """Ensure connection is established."""
        if not self._is_connected:
            await self._connect()

    async def _connect(self) -> None:
        """Establish database connection."""
        try:
            # Run connection setup in thread pool to avoid blocking
            loop = asyncio.get_running_loop()

            def _create_connection():
                db = kuzu.Database(self.database_path, num_threads=self.num_threads)
                conn = kuzu.Connection(db)
                return db, conn

            self._db, self._conn = await loop.run_in_executor(None, _create_connection)
            self._is_connected = True

            logger.debug(f"Connected to Kuzu database at {self.database_path}")

        except Exception as e:
            logger.error(f"Failed to connect to Kuzu database: {e}")
            self._is_connected = False
            raise

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """
        Execute a query on this connection.

        Args:
            query: Cypher query to execute
            params: Query parameters (currently not used by Kuzu)

        Returns:
            Query result
        """
        async with self._lock:
            await self._ensure_connected()

            try:
                self._last_used = datetime.now()
                self._query_count += 1

                # Execute query in thread pool
                loop = asyncio.get_running_loop()

                def _execute_query():
                    if params:
                        # Kuzu doesn't support parameterized queries yet
                        # In practice, you'd need to format the query safely
                        logger.warning("Kuzu doesn't support parameterized queries yet")

                    return self._conn.execute(query)

                result = await loop.run_in_executor(None, _execute_query)

                # Convert result to standard format
                return self._process_result(result)

            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                # Mark connection as potentially broken
                self._is_connected = False
                raise

    async def execute_many(
        self, queries: list[tuple[str, dict[str, Any] | None]]
    ) -> list[Any]:
        """
        Execute multiple queries on this connection.

        Args:
            queries: List of (query, params) tuples

        Returns:
            List of query results
        """
        results = []
        for query, params in queries:
            result = await self.execute(query, params)
            results.append(result)
        return results

    async def begin_transaction(self) -> None:
        """Begin a database transaction."""
        async with self._lock:
            if self._in_transaction:
                raise RuntimeError("Transaction already in progress")

            await self._ensure_connected()

            # Kuzu doesn't support explicit transactions yet
            # This is a placeholder for future implementation
            self._in_transaction = True
            logger.debug("Transaction started (placeholder)")

    async def commit(self) -> None:
        """Commit the current transaction."""
        async with self._lock:
            if not self._in_transaction:
                raise RuntimeError("No transaction in progress")

            # Kuzu doesn't support explicit transactions yet
            self._in_transaction = False
            logger.debug("Transaction committed (placeholder)")

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        async with self._lock:
            if not self._in_transaction:
                raise RuntimeError("No transaction in progress")

            # Kuzu doesn't support explicit transactions yet
            self._in_transaction = False
            logger.debug("Transaction rolled back (placeholder)")

    async def close(self) -> None:
        """Close this connection."""
        async with self._lock:
            if self._is_connected and self._conn:
                # Close connection in thread pool
                loop = asyncio.get_running_loop()

                def _close_connection():
                    if self._conn:
                        # Kuzu doesn't have explicit close method
                        # Connection is closed when object is destroyed
                        pass

                await loop.run_in_executor(None, _close_connection)

                self._conn = None
                self._db = None
                self._is_connected = False

            logger.debug("Connection closed")

    async def is_alive(self) -> bool:
        """Check if connection is still alive and responsive."""
        try:
            # Simple health check query
            await self.execute("MATCH (n) RETURN count(*) LIMIT 1")
            return True
        except Exception:
            return False

    def _process_result(self, result) -> Any:
        """Process Kuzu query result into standard format."""
        if result is None:
            return None

        # Handle different result types
        if hasattr(result, "getNext"):
            # Result is a query result with rows
            rows = []
            while result.hasNext():
                row_data = result.getNext()
                # Convert row data to dictionary format
                if isinstance(row_data, list):
                    # Get column names if available
                    column_names = getattr(result, "getColumnNames", lambda: [])()
                    if column_names:
                        row_dict = dict(zip(column_names, row_data, strict=False))
                        rows.append(row_dict)
                    else:
                        rows.append(row_data)
                else:
                    rows.append(row_data)
            return rows

        # For other result types, return as-is
        return result

    @property
    def connection_info(self) -> dict[str, Any]:
        """Get connection information."""
        return {
            "database_path": self.database_path,
            "num_threads": self.num_threads,
            "is_connected": self._is_connected,
            "in_transaction": self._in_transaction,
            "created_at": self._created_at.isoformat(),
            "last_used": self._last_used.isoformat(),
            "query_count": self._query_count,
            "age_seconds": (datetime.now() - self._created_at).total_seconds(),
        }

    def __repr__(self) -> str:
        status = "connected" if self._is_connected else "disconnected"
        return f"KuzuConnection({self.database_path}, {status})"
