"""
Kuzu CLI-based database adapter for KuzuMemory.

Uses Kuzu's native CLI interface for optimal performance and compatibility.
This approach leverages Kuzu's native query processing instead of the Python API.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.config import KuzuMemoryConfig
from ..utils.exceptions import (
    CorruptedDatabaseError,
    DatabaseError,
    DatabaseLockError,
    PerformanceError,
    PerformanceThresholdError,
)

logger = logging.getLogger(__name__)


class KuzuCLIAdapter:
    """
    Kuzu CLI-based database adapter.

    Uses Kuzu's native CLI interface to execute queries, providing:
    - Optimal performance through native query processing
    - Better compatibility with Kuzu's latest features
    - Reduced memory overhead compared to Python API
    - Direct access to Kuzu's query optimization
    """

    def __init__(self, db_path: Path, config: KuzuMemoryConfig) -> None:
        """
        Initialize the CLI adapter.

        Args:
            db_path: Path to the database file
            config: KuzuMemory configuration
        """
        self.db_path = Path(db_path)
        self.config = config
        self._kuzu_cli_path = self._find_kuzu_cli()

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized Kuzu CLI adapter with database at {self.db_path}")

    def _find_kuzu_cli(self) -> str:
        """Find the Kuzu CLI executable."""
        # Try common locations for Kuzu CLI
        possible_paths = [
            "kuzu",  # In PATH
            "/usr/local/bin/kuzu",
            "/opt/homebrew/bin/kuzu",
            "~/.local/bin/kuzu",
        ]

        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Found Kuzu CLI at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        # If not found, assume it's in PATH
        logger.warning("Kuzu CLI not found in common locations, assuming 'kuzu' is in PATH")
        return "kuzu"

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        timeout_ms: float | None = None,
        output_format: str = "json",
    ) -> list[dict[str, Any]]:
        """
        Execute a query using Kuzu CLI.

        Args:
            query: Cypher query to execute
            parameters: Query parameters (will be substituted)
            timeout_ms: Query timeout in milliseconds
            output_format: Output format (json, csv, etc.)

        Returns:
            List of result dictionaries

        Raises:
            DatabaseError: If query execution fails
            PerformanceError: If query exceeds timeout
        """
        start_time = time.time()
        timeout_ms = timeout_ms or self.config.storage.query_timeout_ms
        timeout_seconds = timeout_ms / 1000.0

        try:
            # Substitute parameters in query if provided
            if parameters:
                query = self._substitute_parameters(query, parameters)

            # Create temporary file for query
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cypher", delete=False) as f:
                f.write(query)
                query_file = f.name

            try:
                # Execute query via CLI
                cmd = [
                    self._kuzu_cli_path,
                    str(self.db_path),
                    "--mode",
                    output_format,
                    "--nostats",  # Disable stats for cleaner output
                ]

                # Run the query
                result = subprocess.run(
                    cmd,
                    input=query,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )

                # Check for errors
                if result.returncode != 0:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    raise DatabaseError(f"Query execution failed: {error_msg}")

                # Parse results
                results = self._parse_output(result.stdout, output_format)

                # Check performance
                execution_time_ms = (time.time() - start_time) * 1000
                if (
                    self.config.performance.enable_performance_monitoring
                    and execution_time_ms > timeout_ms
                ):
                    raise PerformanceThresholdError(
                        "execute_query", execution_time_ms / 1000, timeout_ms / 1000
                    )

                return results

            finally:
                # Clean up temporary file
                Path(query_file).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            execution_time_ms = (time.time() - start_time) * 1000
            raise PerformanceThresholdError(
                "execute_query", execution_time_ms / 1000, timeout_ms / 1000
            )
        except Exception as e:
            if isinstance(e, DatabaseError | PerformanceError):
                raise

            # Check for specific error types
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

    def _substitute_parameters(self, query: str, parameters: dict[str, Any]) -> str:
        """
        Substitute parameters in the query.

        Args:
            query: Query with parameter placeholders ($param)
            parameters: Parameter values

        Returns:
            Query with substituted parameters
        """
        substituted_query = query

        for param_name, param_value in parameters.items():
            placeholder = f"${param_name}"

            # Format value based on type
            if isinstance(param_value, str):
                escaped_value = param_value.replace("'", "\\'")
                formatted_value = f"'{escaped_value}'"
            elif isinstance(param_value, datetime):
                formatted_value = f"'{param_value.isoformat()}'"
            elif isinstance(param_value, bool):
                formatted_value = "true" if param_value else "false"
            elif param_value is None:
                formatted_value = "null"
            else:
                formatted_value = str(param_value)

            substituted_query = substituted_query.replace(placeholder, formatted_value)

        return substituted_query

    def _parse_output(self, output: str, format_type: str) -> list[dict[str, Any]]:
        """
        Parse CLI output into structured data.

        Args:
            output: Raw CLI output
            format_type: Output format used

        Returns:
            Parsed results
        """
        if not output.strip():
            return []

        try:
            if format_type == "json":
                # Parse JSON output
                return json.loads(output)
            elif format_type == "jsonlines":
                # Parse JSONLINES output
                results = []
                for line in output.strip().split("\n"):
                    if line.strip():
                        results.append(json.loads(line))
                return results
            else:
                # For other formats, return raw output
                return [{"result": output}]

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse {format_type} output: {e}")
            # Fallback to raw output
            return [{"result": output}]

    def execute_transaction(
        self,
        queries: list[tuple[str, dict[str, Any]]],  # List of (query, parameters) tuples
        timeout_ms: float | None = None,
    ) -> list[list[dict[str, Any]]]:
        """
        Execute multiple queries in a transaction.

        Args:
            queries: List of (query, parameters) tuples
            timeout_ms: Transaction timeout in milliseconds

        Returns:
            List of results for each query
        """
        time.time()
        timeout_ms = timeout_ms or self.config.storage.query_timeout_ms

        # Build transaction query
        transaction_query = "BEGIN TRANSACTION;\n"

        for query, parameters in queries:
            if parameters:
                query = self._substitute_parameters(query, parameters)
            transaction_query += query + ";\n"

        transaction_query += "COMMIT;"

        try:
            # Execute as single transaction
            result = self.execute_query(
                transaction_query, timeout_ms=timeout_ms, output_format="json"
            )

            # Split results by query (this is simplified - real implementation would be more complex)
            results = []
            for _ in queries:
                results.append(result)

            return results

        except Exception:
            # Try to rollback
            try:
                self.execute_query("ROLLBACK;", timeout_ms=5000)
            except Exception:
                pass  # Rollback failed, but original error is more important
            raise

    def get_statistics(self) -> dict[str, Any]:
        """Get database statistics using CLI."""
        try:
            # Query for basic statistics
            stats_query = """
            MATCH (m:Memory)
            WITH COUNT(m) as memory_count
            MATCH (e:Entity)
            WITH memory_count, COUNT(e) as entity_count
            MATCH (s:Session)
            WITH memory_count, entity_count, COUNT(s) as session_count
            RETURN memory_count, entity_count, session_count
            """

            result = self.execute_query(stats_query)

            if result and len(result) > 0:
                stats = result[0]

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
                "db_size_bytes": 0,
                "db_size_mb": 0.0,
            }

        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {"error": str(e)}

    def close(self) -> None:
        """Close the adapter (no-op for CLI adapter)."""
        logger.info("Closed Kuzu CLI adapter")

    def __enter__(self) -> KuzuCLIAdapter:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
