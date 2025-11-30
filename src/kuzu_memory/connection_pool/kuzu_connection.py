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
    kuzu = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class KuzuConnection(IConnection):
    """
    Wrapper for Kuzu database connection with transaction support.

    Provides async interface over Kuzu's synchronous operations
    and manages connection lifecycle.

    Uses shared Database instances to avoid file lock conflicts when
    multiple connections access the same database.
    """

    # Class-level storage for shared Database instances (keyed by database path)
    _shared_databases: dict[str, Any] = {}
    _db_locks: dict[str, asyncio.Lock] = {}
    _db_ref_counts: dict[str, int] = {}  # Track number of connections using each DB

    def __init__(self, database_path: str, num_threads: int = 4) -> None:
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
        # Note: _db is now retrieved from shared storage, not stored per-instance
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
        """Establish database connection using shared Database instance."""
        try:
            # Get or create shared Database instance
            db = await self._get_or_create_shared_database()

            # Run connection creation in thread pool to avoid blocking
            loop = asyncio.get_running_loop()

            def _create_connection() -> None:
                # Create connection using shared Database instance
                conn = kuzu.Connection(db)
                return conn

            self._conn = await loop.run_in_executor(None, _create_connection)
            self._is_connected = True

            logger.debug(
                f"Connected to Kuzu database at {self.database_path} "
                f"(using shared Database instance)"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Kuzu database: {e}")
            self._is_connected = False
            raise

    async def _get_or_create_shared_database(self) -> Any:
        """
        Get or create shared Database instance for this database path.

        Uses class-level dictionary to store shared instances, ensuring
        multiple connections to the same database reuse the same Database object.

        Returns:
            Shared Database instance
        """
        # Ensure lock exists for this database path
        if self.database_path not in self._db_locks:
            self._db_locks[self.database_path] = asyncio.Lock()

        # Acquire lock to safely check/create shared database
        async with self._db_locks[self.database_path]:
            # Check if shared database already exists
            if self.database_path in self._shared_databases:
                self._db_ref_counts[self.database_path] = (
                    self._db_ref_counts.get(self.database_path, 0) + 1
                )
                logger.debug(
                    f"Reusing shared Database instance for {self.database_path} "
                    f"(ref_count: {self._db_ref_counts[self.database_path]})"
                )
                return self._shared_databases[self.database_path]

            # Create new shared database instance
            loop = asyncio.get_running_loop()

            def _create_database() -> None:
                # Note: Kuzu uses max_num_threads parameter name
                return kuzu.Database(self.database_path, max_num_threads=self.num_threads)

            db = await loop.run_in_executor(None, _create_database)

            # Store in shared storage
            self._shared_databases[self.database_path] = db
            self._db_ref_counts[self.database_path] = 1

            logger.debug(f"Created new shared Database instance for {self.database_path}")

            return db

    async def execute(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        max_retries: int = 3,
        retry_backoff_ms: int = 100,
    ) -> Any:
        """
        Execute a query on this connection with retry logic.

        Args:
            query: Cypher query to execute
            params: Query parameters (currently not used by Kuzu)
            max_retries: Maximum number of retry attempts for lock/busy errors
            retry_backoff_ms: Base backoff time in milliseconds (doubles each retry)

        Returns:
            Query result

        Raises:
            Exception: If query fails after all retries
        """
        async with self._lock:
            await self._ensure_connected()

            last_error: Exception | None = None
            for attempt in range(max_retries):
                try:
                    self._last_used = datetime.now()
                    self._query_count += 1

                    # Execute query in thread pool
                    loop = asyncio.get_running_loop()

                    def _execute_query() -> None:
                        if params:
                            # Kuzu doesn't support parameterized queries yet
                            # In practice, you'd need to format the query safely
                            logger.warning("Kuzu doesn't support parameterized queries yet")

                        # Type guard: _ensure_connected() guarantees _conn is not None
                        if not self._conn:
                            raise RuntimeError("Connection not established")
                        return self._conn.execute(query)

                    result = await loop.run_in_executor(None, _execute_query)

                    # Convert result to standard format
                    return self._process_result(result)

                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()

                    # Check if this is a retryable error (lock/busy/write transaction)
                    is_retryable = (
                        "locked" in error_msg
                        or "busy" in error_msg
                        or "write transaction" in error_msg
                    )

                    if is_retryable and attempt < max_retries - 1:
                        # Calculate backoff with exponential increase
                        backoff_ms = retry_backoff_ms * (2**attempt)
                        logger.warning(
                            f"Query failed with retryable error (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {backoff_ms}ms..."
                        )

                        # Wait before retry
                        await asyncio.sleep(backoff_ms / 1000.0)
                        continue
                    else:
                        # Non-retryable error or max retries reached
                        if is_retryable:
                            logger.error(
                                f"Query failed after {max_retries} retries with lock/busy error: {e}"
                            )
                        else:
                            logger.error(f"Query execution failed: {e}")

                        # Mark connection as potentially broken
                        self._is_connected = False
                        raise

            # Should never reach here, but raise last error if we do
            if last_error is not None:
                raise last_error
            raise RuntimeError("Query execution loop completed without success or error")

    async def execute_many(self, queries: list[tuple[str, dict[str, Any] | None]]) -> list[Any]:
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
        """Close this connection and cleanup shared Database if no longer needed."""
        async with self._lock:
            if self._is_connected and self._conn:
                # Close connection in thread pool
                loop = asyncio.get_running_loop()

                def _close_connection() -> None:
                    if self._conn:
                        # Kuzu doesn't have explicit close method
                        # Connection is closed when object is destroyed
                        pass

                await loop.run_in_executor(None, _close_connection)

                self._conn = None
                self._is_connected = False

                # Decrement reference count and cleanup shared Database if needed
                await self._cleanup_shared_database()

            logger.debug("Connection closed")

    async def _cleanup_shared_database(self) -> None:
        """
        Cleanup shared Database instance if no connections remain.

        Decrements reference count and removes shared Database if this
        was the last connection using it.
        """
        if self.database_path not in self._db_locks:
            return

        async with self._db_locks[self.database_path]:
            if self.database_path not in self._db_ref_counts:
                return

            # Decrement reference count
            self._db_ref_counts[self.database_path] -= 1

            logger.debug(
                f"Decremented ref_count for {self.database_path} "
                f"(now: {self._db_ref_counts[self.database_path]})"
            )

            # If no more connections, cleanup shared database
            if self._db_ref_counts[self.database_path] <= 0:
                if self.database_path in self._shared_databases:
                    del self._shared_databases[self.database_path]
                    logger.debug(f"Removed shared Database instance for {self.database_path}")

                del self._db_ref_counts[self.database_path]
                # Note: Keep lock around for future connections

    async def is_alive(self) -> bool:
        """Check if connection is still alive and responsive."""
        try:
            # Simple health check query
            await self.execute("MATCH (n) RETURN count(*) LIMIT 1")
            return True
        except Exception:
            return False

    def _process_result(self, result: Any) -> Any:
        """
        Process Kuzu query result into standard format (list of dicts).

        Note: Kuzu Python API uses snake_case method names (has_next, get_next, get_all),
        not camelCase (hasNext, getNext). See: https://kuzudb.com/api-docs/python/

        Kuzu's get_all() returns list of lists, so we convert to list of dicts
        for easier consumption by the rest of the application.
        """
        if result is None:
            return None

        # Use Kuzu's built-in get_all() method (most efficient)
        # get_all() returns list of lists like [[1, 'foo'], [2, 'bar']]
        if hasattr(result, "get_all"):
            rows = result.get_all()

            # Convert list of lists to list of dicts for easier consumption
            if rows and hasattr(result, "get_column_names"):
                column_names = result.get_column_names()
                if column_names:
                    return [dict(zip(column_names, row, strict=False)) for row in rows]

            # If no column names or empty result, return as-is
            return rows

        # Fallback: Manual iteration using snake_case API (if get_all not available)
        # Fixed: Kuzu Python API uses snake_case (has_next, get_next), not camelCase
        if hasattr(result, "has_next"):
            rows = []
            # Get column names once at the start
            column_names = getattr(result, "get_column_names", lambda: [])()

            while result.has_next():  # Fixed: snake_case (was hasNext)
                row_data = result.get_next()  # Fixed: snake_case (was getNext)

                # Convert row data to dictionary format
                if isinstance(row_data, list) and column_names:
                    row_dict = dict(zip(column_names, row_data, strict=False))
                    rows.append(row_dict)
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
