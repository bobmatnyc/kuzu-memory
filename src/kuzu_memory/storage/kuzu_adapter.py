"""
Kuzu database adapter for KuzuMemory.

Provides connection management, query execution, and database operations
with connection pooling, error handling, and performance monitoring.

Supports both Python API and CLI adapters for optimal performance.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any

try:
    import kuzu
except ImportError:
    kuzu = None  # type: ignore[assignment]

from ..core.config import KuzuMemoryConfig
from ..core.models import Memory
from ..utils.exceptions import (
    CorruptedDatabaseError,
    DatabaseError,
    DatabaseLockError,
    DatabaseVersionError,
    PerformanceError,
)
from .schema import (
    get_query,
    get_schema_version,
    validate_schema_compatibility,
)

logger = logging.getLogger(__name__)


def create_kuzu_adapter(db_path: Path, config: KuzuMemoryConfig) -> KuzuAdapter:
    """
    Factory function to create the appropriate Kuzu adapter.

    Args:
        db_path: Path to the database
        config: KuzuMemory configuration

    Returns:
        KuzuAdapter instance (either Python API or CLI-based)
    """
    if config.storage.use_cli_adapter:
        logger.info("Using Kuzu CLI adapter for optimal performance")
        from .kuzu_cli_adapter import KuzuCLIAdapter

        return KuzuCLIAdapter(db_path, config)  # type: ignore[return-value]  # Both adapters implement IMemoryStore
    else:
        logger.info("Using Kuzu Python API adapter")
        return KuzuAdapter(db_path, config)


class KuzuConnectionPool:
    """
    Connection pool for Kuzu database connections.

    Manages a pool of database connections to improve performance
    and handle concurrent access safely.
    """

    def __init__(self, db_path: Path, pool_size: int = 5) -> None:
        if kuzu is None:
            raise DatabaseError(
                "Kuzu is not installed. Please install with: pip install kuzu>=0.4.0"
            )

        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: Queue[Any] = Queue(maxsize=pool_size)  # kuzu.Connection has no type stubs
        self._lock = threading.Lock()
        self._initialized = False
        self._database: Any = None  # kuzu.Database has no type stubs

    def _create_connection(self) -> Any:  # kuzu.Connection has no type stubs
        """Create a new Kuzu connection using the shared database instance."""
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create shared database instance if not exists
            if self._database is None:
                self._database = kuzu.Database(str(self.db_path))

            # Create connection using shared database
            connection = kuzu.Connection(self._database)

            return connection

        except Exception as e:
            raise DatabaseError(f"Failed to create Kuzu connection: {e}")

    def initialize(self) -> None:
        """Initialize the connection pool."""
        with self._lock:
            if self._initialized:
                return

            try:
                # Create initial connections
                for _ in range(self.pool_size):
                    conn = self._create_connection()
                    self._pool.put(conn)

                self._initialized = True
                logger.info(f"Initialized Kuzu connection pool with {self.pool_size} connections")

            except Exception as e:
                raise DatabaseError(f"Failed to initialize connection pool: {e}")

    @contextmanager
    def get_connection(
        self, timeout: float = 5.0
    ) -> Iterator[Any]:  # kuzu.Connection has no type stubs
        """
        Get a connection from the pool.

        Args:
            timeout: Timeout in seconds to wait for a connection

        Yields:
            Kuzu connection

        Raises:
            DatabaseLockError: If no connection is available within timeout
        """
        if not self._initialized:
            self.initialize()

        connection = None
        try:
            # Get connection from pool
            connection = self._pool.get(timeout=timeout)
            yield connection

        except Empty:
            raise DatabaseLockError(
                f"Failed to get connection from pool within {timeout}s for {self.db_path}"
            )

        finally:
            # Return connection to pool
            if connection is not None:
                try:
                    self._pool.put(connection, timeout=1.0)
                except Exception:
                    # If we can't return to pool, create a new connection
                    logger.warning("Failed to return connection to pool, creating new one")
                    try:
                        new_conn = self._create_connection()
                        self._pool.put(new_conn, timeout=1.0)
                    except Exception:
                        logger.error("Failed to create replacement connection")

    def close(self) -> None:
        """Close all connections in the pool and the shared database."""
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    # Kuzu connections are automatically closed when they go out of scope
                    del conn
                except Empty:
                    break

            # Close shared database
            if self._database is not None:
                del self._database
                self._database = None

            self._initialized = False
            logger.info("Closed Kuzu connection pool")


class KuzuAdapter:
    """
    Main adapter for Kuzu database operations.

    Provides high-level database operations with error handling,
    performance monitoring, and schema management.
    """

    def __init__(self, db_path: Path, config: KuzuMemoryConfig) -> None:
        self.db_path = db_path
        self.config = config
        self._pool = KuzuConnectionPool(db_path, pool_size=config.storage.connection_pool_size)
        self._schema_initialized = False

    def initialize(self) -> None:
        """Initialize the database and schema."""
        try:
            # Initialize connection pool
            self._pool.initialize()

            # Check and initialize schema
            self._initialize_schema()

            logger.info(f"Initialized Kuzu database at {self.db_path}")

        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {e}")

    def _initialize_schema(self) -> None:
        """Initialize or verify database schema."""
        try:
            # Check if schema exists and is compatible
            current_version = self._get_current_schema_version()
            required_version = get_schema_version()

            if current_version is None:
                # New database - create schema
                logger.info("Creating new database schema")
                self._create_schema()

            elif not validate_schema_compatibility(current_version, required_version):
                # Schema version mismatch
                raise DatabaseVersionError(current_version, required_version)

            else:
                logger.info(f"Database schema version {current_version} is compatible")

            self._schema_initialized = True

        except Exception as e:
            if isinstance(e, DatabaseVersionError):
                raise
            raise DatabaseError(f"Failed to initialize schema: {e}")

    def _get_current_schema_version(self) -> str | None:
        """Get the current schema version from database."""
        try:
            result = self.execute_query(get_query("get_schema_version"))
            if result and len(result) > 0:
                return str(result[0]["sv.version"])
            return None

        except Exception:
            # Schema version table doesn't exist - new database
            return None

    def _create_schema(self) -> None:
        """Create the database schema using a single connection."""
        try:
            from .schema import INDICES_DDL, INITIAL_DATA_DDL, SCHEMA_DDL

            # Use a single connection for all schema operations
            with self._pool.get_connection() as conn:
                # Create tables first
                table_statements = [stmt.strip() for stmt in SCHEMA_DDL.split(";") if stmt.strip()]
                logger.info(f"Creating {len(table_statements)} table statements")
                for i, statement in enumerate(table_statements):
                    if statement:
                        logger.info(f"Executing table statement {i + 1}: {statement[:50]}...")
                        try:
                            conn.execute(statement)
                            logger.info(f"✅ Table statement {i + 1} completed successfully")
                        except Exception as e:
                            logger.error(f"❌ Table statement {i + 1} failed: {e}")
                            logger.error(f"   Full statement: {statement}")
                            raise

                # Then create indices
                index_statements = [stmt.strip() for stmt in INDICES_DDL.split(";") if stmt.strip()]
                logger.info(f"Creating {len(index_statements)} index statements")
                for i, statement in enumerate(index_statements):
                    if statement:
                        logger.info(f"Executing index statement {i + 1}: {statement[:50]}...")
                        try:
                            conn.execute(statement)
                            logger.info(f"✅ Index statement {i + 1} completed successfully")
                        except Exception as e:
                            logger.error(f"❌ Index statement {i + 1} failed: {e}")
                            # Indices failing is not critical, continue

                # Finally insert initial data
                data_statements = [
                    stmt.strip() for stmt in INITIAL_DATA_DDL.split(";") if stmt.strip()
                ]
                for i, statement in enumerate(data_statements):
                    if statement:
                        logger.info(f"Executing data statement {i + 1}: {statement[:50]}...")
                        try:
                            conn.execute(statement)
                            logger.info(f"✅ Data statement {i + 1} completed successfully")
                        except Exception as e:
                            logger.error(f"❌ Data statement {i + 1} failed: {e}")
                            # Data insertion failing is not critical, continue

                logger.info("Created database schema successfully")

        except Exception as e:
            raise DatabaseError(f"Failed to create schema: {e}")

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        timeout_ms: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a query and return results.

        Args:
            query: Cypher query to execute
            parameters: Query parameters
            timeout_ms: Query timeout in milliseconds

        Returns:
            List of result dictionaries

        Raises:
            DatabaseError: If query execution fails
            PerformanceError: If query exceeds timeout
        """
        start_time = time.time()
        timeout_ms = timeout_ms or self.config.storage.query_timeout_ms

        try:
            with self._pool.get_connection() as conn:
                # Execute query
                if parameters:
                    # Debug logging for parameter issues
                    if "week_ago" in query and "week_ago" not in parameters:
                        logger.warning(
                            f"Query contains $week_ago but parameter not provided. Params: {parameters.keys()}"
                        )
                    result = conn.execute(query, parameters)
                else:
                    result = conn.execute(query)

                # Convert result to list of dictionaries
                results = []
                while result.has_next():
                    row = result.get_next()
                    # Convert row to dictionary
                    row_dict = {}
                    for i in range(len(result.get_column_names())):
                        col_name = result.get_column_names()[i]
                        row_dict[col_name] = row[i]
                    results.append(row_dict)

                # Check performance
                execution_time_ms = (time.time() - start_time) * 1000
                if self.config.performance.enable_performance_monitoring:
                    if execution_time_ms > timeout_ms:
                        raise PerformanceError(
                            f"Query execution exceeded timeout: {execution_time_ms:.1f}ms > {timeout_ms}ms"
                        )

                    if (
                        self.config.performance.log_slow_operations
                        and execution_time_ms > timeout_ms * 0.8
                    ):
                        logger.warning(f"Slow query ({execution_time_ms:.1f}ms): {query[:100]}...")

                return results

        except Exception as e:
            if isinstance(e, PerformanceError):
                raise

            # Check for specific Kuzu errors
            error_msg = str(e).lower()
            if "locked" in error_msg or "busy" in error_msg:
                raise DatabaseLockError(f"Database locked: {self.db_path}")
            elif "corrupt" in error_msg or "malformed" in error_msg:
                raise CorruptedDatabaseError(
                    f"Database corrupted at {self.db_path}: {e}",
                    context={"db_path": str(self.db_path), "error": str(e)},
                )
            else:
                raise DatabaseError(f"Query execution failed: {e}")

    def execute_transaction(
        self,
        queries: list[tuple[str, dict[str, Any] | None]],  # List of (query, parameters) tuples
        timeout_ms: float | None = None,
    ) -> list[list[dict[str, Any]]]:
        """
        Execute multiple queries in a transaction.

        Args:
            queries: List of (query, parameters) tuples
            timeout_ms: Transaction timeout in milliseconds

        Returns:
            List of results for each query

        Raises:
            DatabaseError: If transaction fails
        """
        start_time = time.time()
        timeout_ms = timeout_ms or self.config.storage.query_timeout_ms * len(queries)

        try:
            with self._pool.get_connection() as conn:
                # Begin transaction
                conn.execute("BEGIN TRANSACTION")

                results = []
                try:
                    # Execute all queries
                    for query, parameters in queries:
                        if parameters:
                            result = conn.execute(query, parameters)
                        else:
                            result = conn.execute(query)

                        # Convert result
                        query_results = []
                        while result.has_next():
                            row = result.get_next()
                            row_dict = {}
                            for i in range(len(result.get_column_names())):
                                col_name = result.get_column_names()[i]
                                row_dict[col_name] = row[i]
                            query_results.append(row_dict)

                        results.append(query_results)

                    # Commit transaction
                    conn.execute("COMMIT")

                    # Check performance
                    execution_time_ms = (time.time() - start_time) * 1000
                    if (
                        self.config.performance.enable_performance_monitoring
                        and execution_time_ms > timeout_ms
                    ):
                        logger.warning(f"Slow transaction ({execution_time_ms:.1f}ms)")

                    return results

                except Exception:
                    # Rollback on error
                    conn.execute("ROLLBACK")
                    raise

        except Exception as e:
            raise DatabaseError(f"Transaction failed: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """Get database statistics."""
        try:
            stats_result = self.execute_query(get_query("get_database_stats"))

            if stats_result:
                stats = stats_result[0]

                # Add file size information
                if self.db_path.exists():
                    file_size_bytes = self.db_path.stat().st_size
                    stats["db_size_bytes"] = file_size_bytes
                    stats["db_size_mb"] = round(file_size_bytes / (1024 * 1024), 2)
                else:
                    stats["db_size_bytes"] = 0
                    stats["db_size_mb"] = 0.0

                return stats

            return {
                "memory_count": 0,
                "entity_count": 0,
                "session_count": 0,
                "relationship_count": 0,
                "db_size_bytes": 0,
                "db_size_mb": 0.0,
            }

        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {"error": str(e)}

    def cleanup_expired_memories(self) -> int:
        """
        Clean up expired memories.

        Returns:
            Number of memories cleaned up
        """
        try:
            current_time = datetime.now().isoformat()

            # Get count before cleanup
            before_result = self.execute_query(get_query("get_memory_count"))
            before_count = before_result[0]["count"] if before_result else 0

            # Execute cleanup
            self.execute_query(
                get_query("cleanup_expired_memories"), {"current_time": current_time}
            )

            # Get count after cleanup
            after_result = self.execute_query(get_query("get_memory_count"))
            after_count = after_result[0]["count"] if after_result else 0

            cleaned_count = before_count - after_count

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired memories")

            return cleaned_count

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
            query = """
                MATCH (m:Memory)
                WHERE (m.valid_to IS NULL OR m.valid_to > $current_time)
            """

            parameters = {"current_time": datetime.now().isoformat(), "limit": limit}

            # Add filters
            if "memory_type" in filters:
                query += " AND m.memory_type = $memory_type"
                parameters["memory_type"] = filters["memory_type"]

            if "user_id" in filters:
                query += " AND m.user_id = $user_id"
                parameters["user_id"] = filters["user_id"]

            query += " RETURN m ORDER BY m.created_at DESC LIMIT $limit"

            results = self.execute_query(query, parameters)

            memories = []
            for result in results:
                memory_data = result["m"]
                memory = self._result_to_memory(memory_data)
                if memory:
                    memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []

    def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """
        Get a specific memory by ID.

        Args:
            memory_id: Memory ID to retrieve

        Returns:
            Memory object or None if not found
        """
        try:
            query = """
                MATCH (m:Memory)
                WHERE m.id = $memory_id
                RETURN m
            """

            results = self.execute_query(query, {"memory_id": memory_id})

            if results:
                memory_data = results[0]["m"]
                return self._result_to_memory(memory_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get memory by ID: {e}")
            return None

    def _result_to_memory(self, memory_data: dict[str, Any]) -> Memory | None:
        """
        Convert database result to Memory object.

        Args:
            memory_data: Raw memory data from database

        Returns:
            Memory object or None if conversion fails
        """
        try:
            return Memory.from_dict(memory_data)
        except Exception as e:
            logger.warning(f"Failed to parse memory from database: {e}")
            return None

    def close(self) -> None:
        """Close the database adapter."""
        try:
            self._pool.close()
            logger.info("Closed Kuzu database adapter")
        except Exception as e:
            logger.error(f"Error closing database adapter: {e}")
