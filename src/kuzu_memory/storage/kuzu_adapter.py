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
from contextlib import AbstractContextManager, contextmanager
from contextlib import nullcontext as _nullcontext
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any, cast

try:
    import kuzu
except ImportError:
    kuzu = None  # type: ignore[assignment,unused-ignore]

from ..core.config import KuzuMemoryConfig
from ..core.models import Memory
from ..utils.exceptions import (
    CorruptedDatabaseError,
    DatabaseError,
    DatabaseLockError,
    DatabaseVersionError,
    PerformanceError,
)
from .schema import get_query, get_schema_version, validate_schema_compatibility

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


def _is_db_lock_error(exc: Exception) -> bool:
    """Return True when *exc* looks like a cross-process kuzu file-lock error."""
    msg = str(exc).lower()
    return "could not set lock" in msg or ("lock" in msg and "file" in msg)


def _lock_error_message(db_path: Path, original_exc: Exception) -> str:
    """Build an actionable DatabaseLockError message, including lsof info when available."""
    import shutil
    import subprocess

    hint = (
        f"The database at '{db_path}' is locked by another process. "
        "Reads and writes are unavailable until that process releases the lock.\n"
        "Tip: use separate database paths for each application, or route all "
        "access through a single MCP server process."
    )

    # Try to identify the lock holder via lsof (macOS/Linux)
    if shutil.which("lsof"):
        try:
            result = subprocess.run(
                ["lsof", str(db_path)],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                # Second line onward are the actual processes
                if len(lines) > 1:
                    pids = {line.split()[1] for line in lines[1:] if line.split()}
                    hint += f"\nLock holder PID(s): {', '.join(sorted(pids))}"
        except Exception:
            pass  # lsof unavailable or timed out — skip

    return hint


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
        # RLock (reentrant) is required because initialize() holds _lock and
        # calls _create_connection(), which also acquires _lock to guard the
        # one-time creation of self._database.  A plain Lock() would deadlock
        # the calling thread on the second acquisition.
        self._lock = threading.RLock()
        self._initialized = False
        self._database: Any = None  # kuzu.Database has no type stubs
        # Set to True when another process holds the write lock and we fall
        # back to opening the database in read-only mode.
        self.read_only: bool = False

    def _create_connection(self) -> Any:  # kuzu.Connection has no type stubs
        """Create a new Kuzu connection using the shared database instance."""
        import errno as _errno_mod

        if kuzu is None:
            raise DatabaseError(
                "Kuzu is not installed. Please install with: pip install kuzu>=0.4.0"
            )

        _kuzu = kuzu  # Local binding for type narrowing after None check

        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create shared database instance if not exists.
            # Guarded by self._lock to prevent a TOCTOU race where two threads
            # both observe self._database is None and then each instantiate a
            # separate kuzu.Database object for the same path.
            with self._lock:
                if self._database is None:
                    try:
                        self._database = _kuzu.Database(str(self.db_path))
                    except Exception as open_exc:
                        if _is_db_lock_error(open_exc):
                            # Another OS process holds the write lock.  Try to
                            # open in read-only mode so recall/enhance still work.
                            logger.warning(
                                f"Database at '{self.db_path}' is locked by another process; "
                                f"falling back to read-only mode (writes will be rejected)."
                            )
                            try:
                                self._database = _kuzu.Database(str(self.db_path), read_only=True)
                                self.read_only = True
                            except Exception:
                                raise DatabaseLockError(_lock_error_message(self.db_path, open_exc))
                        else:
                            raise

            # Create connection using shared database
            connection = _kuzu.Connection(self._database)

            return connection

        except DatabaseLockError:
            raise
        except OSError as e:
            if e.errno == _errno_mod.EEXIST:
                # Two distinct causes for EEXIST here:
                #
                # 1. The parent directory (.kuzu-memory/) is itself a regular
                #    file — this is the old single-file kuzu database format.
                #    Give a specific migration hint.
                #
                # 2. Older kuzu versions (< 0.6) call mkdir() internally on the
                #    parent directory without exist_ok, so they raise EEXIST when
                #    the parent already exists as a directory.
                parent = self.db_path.parent
                if parent.exists() and not parent.is_dir():
                    # Attempt auto-migration before giving up.
                    from kuzu_memory.utils.project_setup import _migrate_single_file_db

                    if _migrate_single_file_db(parent):
                        # Migration succeeded — retry opening the database and
                        # return a fresh connection.
                        try:
                            with self._lock:
                                if self._database is None:
                                    self._database = _kuzu.Database(str(self.db_path))
                            return _kuzu.Connection(self._database)
                        except Exception as retry_exc:
                            raise DatabaseError(
                                f"Failed to initialize database at '{self.db_path}' "
                                f"after auto-migrating old single-file format: {retry_exc}"
                            ) from retry_exc
                    raise DatabaseError(
                        f"Failed to initialize database at '{self.db_path}': "
                        f"'{parent}' exists as a regular file (possibly an old "
                        f"single-file kuzu database). "
                        f"Run 'kuzu-memory init --force' to migrate to the current format."
                    )
                raise DatabaseError(
                    f"Failed to initialize database at '{self.db_path}': "
                    f"the parent directory '{parent}' already exists "
                    f"but kuzu could not create the database inside it "
                    f"(kuzu reported: {e}). "
                    f"Run 'kuzu-memory init --force' to recreate the database."
                )
            raise DatabaseError(f"Failed to create Kuzu connection: {e}")
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
        # Kùzu enforces a single-writer constraint at the engine level: only one
        # write transaction may be open at a time across all connections.  This
        # lock serialises all write operations so that concurrent callers (e.g.
        # asyncio.to_thread workers) queue behind each other instead of racing.
        self._write_lock = threading.Lock()

    def initialize(self) -> None:
        """Initialize the database and schema."""
        try:
            # Initialize connection pool
            self._pool.initialize()

            # Check and initialize schema
            self._initialize_schema()

            # Run any pending schema migrations (e.g. ALTER TABLE ADD COLUMN).
            # This must happen after _initialize_schema() so the base tables exist,
            # and must complete before any business queries execute.  Non-schema
            # migrations (hooks, config, cleanup) are intentionally skipped here to
            # keep DB init fast; they run via _check_migrations() on CLI invocation.
            self._run_schema_migrations()

            # Ensure the HNSW vector index exists (idempotent — swallows
            # "already exists" errors so this is safe to call on every startup).
            self._ensure_hnsw_index()

            # Ensure Keyword node table and HAS_KEYWORD rel table exist
            # (idempotent — swallows "already exists" errors).
            self._ensure_keyword_tables()

            # Run one-time data maintenance (purge expired, dedup, trim git metadata).
            # Uses the already-open pool — no second kuzu.Database is opened.
            self._run_data_maintenance()

            logger.info(f"Initialized Kuzu database at {self.db_path}")

        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {e}")

    def _run_schema_migrations(self) -> None:
        """Run pending SCHEMA-type migrations against this database.

        Called automatically on every DB initialisation so that ALTER TABLE
        additions (knowledge_type, project_tag, etc.) are applied to existing
        databases without requiring manual CLI intervention.

        Uses the already-open connection pool to avoid opening a second Kuzu
        Database instance.  Each column is probed with LIMIT 0 first; if the
        column exists the ALTER TABLE is skipped, making this fully idempotent.

        For brand-new databases just created by _create_schema(), all columns
        are already present by definition — the probes succeed immediately.
        """
        # Each tuple: (column_name, alter_memory_ddl, alter_archived_ddl_or_None)
        _columns: list[tuple[str, str, str | None]] = [
            (
                "knowledge_type",
                "ALTER TABLE Memory ADD knowledge_type STRING DEFAULT 'note'",
                "ALTER TABLE ArchivedMemory ADD knowledge_type STRING DEFAULT 'note'",
            ),
            (
                "project_tag",
                "ALTER TABLE Memory ADD project_tag STRING DEFAULT ''",
                "ALTER TABLE ArchivedMemory ADD project_tag STRING DEFAULT ''",
            ),
            (
                "content_hash",
                "ALTER TABLE Memory ADD content_hash STRING DEFAULT ''",
                "ALTER TABLE ArchivedMemory ADD content_hash STRING DEFAULT ''",
            ),
            (
                "valid_from",
                "ALTER TABLE Memory ADD valid_from TIMESTAMP",
                None,
            ),
            (
                "accessed_at",
                "ALTER TABLE Memory ADD accessed_at TIMESTAMP",
                None,
            ),
            (
                "access_count",
                "ALTER TABLE Memory ADD access_count INT32 DEFAULT 0",
                None,
            ),
            (
                "importance",
                "ALTER TABLE Memory ADD importance FLOAT DEFAULT 0.5",
                "ALTER TABLE ArchivedMemory ADD importance FLOAT DEFAULT 0.5",
            ),
            (
                "confidence",
                "ALTER TABLE Memory ADD confidence FLOAT DEFAULT 1.0",
                "ALTER TABLE ArchivedMemory ADD confidence FLOAT DEFAULT 1.0",
            ),
            (
                "embedding",
                "ALTER TABLE Memory ADD embedding FLOAT[384]",
                None,
            ),
            (
                "source_speaker",
                "ALTER TABLE Memory ADD source_speaker STRING DEFAULT 'user'",
                None,
            ),
        ]

        try:
            with self._pool.get_connection() as conn:
                for col, mem_ddl, arch_ddl in _columns:
                    # Probe Memory: try a LIMIT 0 projection to check column existence
                    try:
                        conn.execute(f"MATCH (m:Memory) RETURN m.{col} LIMIT 0")
                        # Column exists — no ALTER TABLE needed
                    except Exception as probe_exc:
                        probe_msg = str(probe_exc).lower()
                        if "cannot find property" in probe_msg or col.lower() in probe_msg:
                            # Column absent — add it
                            try:
                                conn.execute(mem_ddl)
                                logger.info("Schema migration applied: %s", mem_ddl)
                            except Exception as alter_exc:
                                logger.warning(
                                    "Schema migration for Memory.%s failed (non-fatal): %s",
                                    col,
                                    alter_exc,
                                )
                        else:
                            # Unexpected error (e.g. Memory table absent in some test fixtures)
                            logger.debug(
                                "Schema migration probe error for %s (skipping): %s",
                                col,
                                probe_exc,
                            )
                            continue

                    # ArchivedMemory — best-effort; table may not exist in older DBs
                    if arch_ddl:
                        try:
                            conn.execute(f"MATCH (m:ArchivedMemory) RETURN m.{col} LIMIT 0")
                            # Column exists — skip
                        except Exception as arch_probe_exc:
                            arch_msg = str(arch_probe_exc).lower()
                            if "cannot find property" in arch_msg or col.lower() in arch_msg:
                                try:
                                    conn.execute(arch_ddl)
                                    logger.info("Schema migration applied: %s", arch_ddl)
                                except Exception as arch_alter_exc:
                                    logger.debug(
                                        "Schema migration for ArchivedMemory.%s skipped: %s",
                                        col,
                                        arch_alter_exc,
                                    )
                            # else: table absent or other unexpected error — silently skip

        except Exception as e:
            # Non-fatal: log and continue — a missing column will surface as a
            # query error later, which is easier to diagnose than a startup crash.
            logger.warning("Schema migration check failed (non-fatal): %s", e)

        # Edge-table migrations: RELATES_TO.weight and RELATES_TO.relationship_type
        # These columns are used by RelatesToEnricher and GraphRelatedRecallStrategy.
        # Probe by querying a LIMIT 0 result with the column; ALTER TABLE if absent.
        _rel_columns: list[tuple[str, str]] = [
            (
                "weight",
                "ALTER TABLE RELATES_TO ADD weight FLOAT DEFAULT 1.0",
            ),
            (
                "relationship_type",
                "ALTER TABLE RELATES_TO ADD relationship_type STRING DEFAULT 'shared_entity'",
            ),
        ]
        try:
            with self._pool.get_connection() as conn:
                for col, rel_ddl in _rel_columns:
                    try:
                        conn.execute(f"MATCH ()-[r:RELATES_TO]->() RETURN r.{col} LIMIT 0")
                        # Column exists — no ALTER TABLE needed
                    except Exception as probe_exc:
                        probe_msg = str(probe_exc).lower()
                        if "cannot find property" in probe_msg or col.lower() in probe_msg:
                            try:
                                conn.execute(rel_ddl)
                                logger.info("Schema migration applied: %s", rel_ddl)
                            except Exception as alter_exc:
                                logger.warning(
                                    "Schema migration for RELATES_TO.%s failed (non-fatal): %s",
                                    col,
                                    alter_exc,
                                )
                        else:
                            # Table absent or unexpected error — silently skip
                            logger.debug(
                                "Schema migration probe error for RELATES_TO.%s (skipping): %s",
                                col,
                                probe_exc,
                            )
        except Exception as e:
            logger.warning("RELATES_TO schema migration check failed (non-fatal): %s", e)

    def _ensure_hnsw_index(self) -> None:
        """Create the HNSW vector index on Memory.embedding if not already present.

        Called after _run_schema_migrations() so the embedding column is
        guaranteed to exist (either from schema DDL on new databases, or from
        ALTER TABLE migration on existing ones).

        Swallows "already exists" and index-related errors so this is fully
        idempotent and safe to call on every startup.
        """
        create_query = 'CALL CREATE_VECTOR_INDEX("Memory", "memory_hnsw_idx", "embedding")'
        try:
            self.execute_query(create_query)
            logger.info("HNSW vector index ensured: memory_hnsw_idx")
        except Exception as exc:
            exc_msg = str(exc).lower()
            if "already exists" in exc_msg or "index" in exc_msg:
                logger.debug("HNSW index already exists or not applicable: %s", exc)
            else:
                # Non-fatal: log but don't crash DB initialisation.
                logger.warning("HNSW index creation failed (non-fatal): %s", exc)

    def _ensure_keyword_tables(self) -> None:
        """Create Keyword node table and HAS_KEYWORD rel table if not already present.

        Called after _ensure_hnsw_index() during initialize().  Swallows
        "already exists" and related errors so this is fully idempotent
        and safe to call on every startup.
        """
        keyword_node_ddl = (
            "CREATE NODE TABLE IF NOT EXISTS Keyword ("
            "word STRING, idf FLOAT DEFAULT 0.0, "
            "total_mentions INT64 DEFAULT 0, PRIMARY KEY (word))"
        )
        keyword_rel_ddl = (
            "CREATE REL TABLE IF NOT EXISTS HAS_KEYWORD ("
            "FROM Memory TO Keyword, tf FLOAT DEFAULT 0.0, tfidf FLOAT DEFAULT 0.0)"
        )
        for ddl in (keyword_node_ddl, keyword_rel_ddl):
            try:
                self.execute_query(ddl)
                logger.debug("Keyword table ensured: %s", ddl.split("(")[0].strip())
            except Exception as exc:
                exc_msg = str(exc).lower()
                if "already exists" in exc_msg or "exist" in exc_msg:
                    logger.debug("Keyword table already exists: %s", exc)
                else:
                    logger.warning("Keyword table creation failed (non-fatal): %s", exc)

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

    # Queries that mutate state and therefore require the write lock.  This is
    # intentionally conservative: any keyword that begins a write clause is
    # listed so we never accidentally run two concurrent writers.
    _WRITE_KEYWORDS = frozenset(
        ["create", "merge", "set", "delete", "remove", "detach", "drop", "begin"]
    )

    @classmethod
    def _is_write_query(cls, query: str) -> bool:
        """Return True when *query* contains a write clause."""
        first_keyword = query.strip().split()[0].lower() if query.strip() else ""
        return first_keyword in cls._WRITE_KEYWORDS

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        timeout_ms: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a query and return results.

        Write queries are serialised through ``_write_lock`` so that concurrent
        callers (e.g. asyncio.to_thread workers) queue safely behind each other
        instead of racing for the single Kùzu write-transaction slot.

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

        is_write = self._is_write_query(query)

        # If the pool opened in read-only mode (another process holds the write
        # lock), reject write operations immediately with a clear error rather
        # than letting kuzu throw a raw RuntimeError.
        if is_write and self._pool.read_only:
            raise DatabaseLockError(
                f"Cannot execute write query — the database at '{self.db_path}' "
                f"is open in read-only mode because another process holds the "
                f"write lock.  Stop the other process or use a separate database path."
            )

        max_retries = self.config.storage.max_write_retries if is_write else 1
        backoff_s = self.config.storage.write_retry_backoff_ms / 1000.0

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                # Serialise write operations so concurrent threads never hold two
                # open write transactions against the same Kùzu database at once.
                lock_ctx = cast(
                    AbstractContextManager[object],
                    self._write_lock if is_write else _nullcontext(),
                )
                with lock_ctx:
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
                                logger.warning(
                                    f"Slow query ({execution_time_ms:.1f}ms): {query[:100]}..."
                                )

                        return results

            except Exception as e:
                if isinstance(e, PerformanceError):
                    raise

                # Check for specific Kuzu errors
                error_msg = str(e).lower()
                if (
                    "only one write transaction" in error_msg
                    and is_write
                    and attempt < max_retries - 1
                ):
                    # Another connection beat us to the write slot; back off and retry.
                    wait = backoff_s * (2**attempt)
                    logger.warning(
                        f"Write-transaction contention on attempt {attempt + 1}/{max_retries}; "
                        f"retrying in {wait * 1000:.0f}ms"
                    )
                    time.sleep(wait)
                    last_exc = e
                    continue
                elif "locked" in error_msg or "busy" in error_msg:
                    raise DatabaseLockError(f"Database locked: {self.db_path}")
                elif "corrupt" in error_msg or "malformed" in error_msg:
                    raise CorruptedDatabaseError(
                        f"Database corrupted at {self.db_path}: {e}",
                        context={"db_path": str(self.db_path), "error": str(e)},
                    )
                else:
                    raise DatabaseError(f"Query execution failed: {e}")

        raise DatabaseError(f"Query execution failed after {max_retries} retries: {last_exc}")

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
            # All explicit transactions are write transactions; hold the write
            # lock for the full duration so no other thread can open a competing
            # write transaction while this one is in flight.
            with self._write_lock:
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
            before_count: int = int(before_result[0]["count"]) if before_result else 0

            # Execute cleanup
            self.execute_query(
                get_query("cleanup_expired_memories"), {"current_time": current_time}
            )

            # Get count after cleanup
            after_result = self.execute_query(get_query("get_memory_count"))
            after_count: int = int(after_result[0]["count"]) if after_result else 0

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

    def _run_data_maintenance(self) -> None:
        """Run one-time data maintenance using the already-open connection pool.

        Delegates to the three helper functions defined in
        ``kuzu_memory.migrations.v1_9_0_data_maintenance``:

        1. Purge memories whose ``valid_to`` is in the past.
        2. Back-fill missing ``content_hash`` values and delete duplicates.
        3. Trim oversized ``git_sync`` metadata blobs to a slim schema.

        All steps are non-fatal — failures are logged as warnings and execution
        continues.  The check is short-circuited when the database is already
        clean so the overhead on subsequent startups is a handful of lightweight
        count queries.

        Uses ``self.execute_query`` so writes are serialised through
        ``_write_lock`` and connection pool; no second ``kuzu.Database`` is
        opened.
        """
        try:
            from ..migrations.v1_9_0_data_maintenance import (
                dedup_by_content_hash,
                has_work_to_do,
                purge_expired,
                trim_git_metadata,
            )

            def _execute(query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
                return self.execute_query(query, params or None)

            if not has_work_to_do(_execute):
                logger.debug("Data maintenance: nothing to do — skipping")
                return

            purged = purge_expired(_execute)
            hashes_written, dupes = dedup_by_content_hash(_execute)
            trimmed, saved = trim_git_metadata(_execute)

            if purged or hashes_written or dupes or trimmed:
                logger.info(
                    "Data maintenance complete: purged=%d, hashes_written=%d, "
                    "dupes_removed=%d, metadata_trimmed=%d (~%d bytes saved)",
                    purged,
                    hashes_written,
                    dupes,
                    trimmed,
                    saved,
                )

        except Exception as exc:
            # Non-fatal: a maintenance failure must never crash DB initialisation.
            logger.warning("Data maintenance failed (non-fatal): %s", exc)

    def close(self) -> None:
        """Close the database adapter."""
        try:
            self._pool.close()
            logger.info("Closed Kuzu database adapter")
        except Exception as e:
            logger.error(f"Error closing database adapter: {e}")
