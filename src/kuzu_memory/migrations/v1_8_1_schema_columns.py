"""Schema migration to ensure all Memory table columns from current schema exist.

Covers fields that may be absent from databases created before the full schema
was established: content_hash, valid_from, accessed_at, access_count,
importance, confidence.

Each ALTER TABLE is wrapped in its own try/except so a single already-present
column does not abort the whole migration.
"""

from __future__ import annotations

import logging

from .base import MigrationResult, MigrationType, SchemaMigration

logger = logging.getLogger(__name__)

# (column_name, ddl_fragment) — order matters: independent columns only.
_MEMORY_COLUMNS: list[tuple[str, str]] = [
    ("content_hash", "ALTER TABLE Memory ADD content_hash STRING DEFAULT ''"),
    ("valid_from", "ALTER TABLE Memory ADD valid_from TIMESTAMP"),
    ("accessed_at", "ALTER TABLE Memory ADD accessed_at TIMESTAMP"),
    ("access_count", "ALTER TABLE Memory ADD access_count INT32 DEFAULT 0"),
    ("importance", "ALTER TABLE Memory ADD importance FLOAT DEFAULT 0.5"),
    ("confidence", "ALTER TABLE Memory ADD confidence FLOAT DEFAULT 1.0"),
]

_ARCHIVED_COLUMNS: list[tuple[str, str]] = [
    ("content_hash", "ALTER TABLE ArchivedMemory ADD content_hash STRING DEFAULT ''"),
    ("importance", "ALTER TABLE ArchivedMemory ADD importance FLOAT DEFAULT 0.5"),
    ("confidence", "ALTER TABLE ArchivedMemory ADD confidence FLOAT DEFAULT 1.0"),
]


class SchemaColumnsMigration(SchemaMigration):
    """Add any missing Memory/ArchivedMemory columns introduced after initial schema.

    This migration is fully idempotent: it probes each column individually
    and only issues ALTER TABLE when the column is genuinely absent.
    """

    name = "schema_columns_v1.8.1"
    from_version = "0.0.0"
    to_version = "999.0.0"
    migration_type = MigrationType.SCHEMA
    priority = 60  # Run after knowledge_type (50) and before cleanup (900)

    def description(self) -> str:
        """Return human-readable description."""
        return (
            "Ensure all Memory and ArchivedMemory columns from the current schema "
            "are present (content_hash, valid_from, accessed_at, access_count, "
            "importance, confidence)"
        )

    def _column_exists(self, conn: object, table: str, column: str) -> bool:
        """Return True when *column* exists on *table*.

        Strategy: execute a LIMIT 0 projection.  If Kùzu raises with a message
        containing 'cannot find property' the column is absent; otherwise it exists.
        """
        try:
            # conn is a kuzu.Connection — no type stubs available
            conn.execute(f"MATCH (n:{table}) RETURN n.{column} LIMIT 0")  # type: ignore[attr-defined]
            return True
        except Exception as exc:
            msg = str(exc).lower()
            if "cannot find property" in msg or column.lower() in msg:
                return False
            # Unexpected error — treat as column absent to attempt migration
            logger.debug("Unexpected probe error for %s.%s: %s", table, column, exc)
            return False

    def check_applicable(self) -> bool:
        """Return True if any expected column is missing from the Memory table."""
        if not super().check_applicable():
            return False

        db_path = self._find_db_path()
        if db_path is None:
            return False

        try:
            import kuzu

            db = kuzu.Database(str(db_path))
            conn = kuzu.Connection(db)
            for col, _ in _MEMORY_COLUMNS:
                if not self._column_exists(conn, "Memory", col):
                    return True
            return False
        except Exception as exc:
            logger.debug("check_applicable probe failed: %s", exc)
            # If we cannot open the DB, let migrate() handle the error gracefully
            return True

    def migrate(self) -> MigrationResult:
        """Add any missing columns to Memory and ArchivedMemory tables."""
        db_path = self._find_db_path()
        if db_path is None:
            return MigrationResult(
                success=False,
                message="Database not found — cannot run schema_columns migration",
                changes=[],
            )

        changes: list[str] = []
        warnings: list[str] = []

        try:
            import kuzu

            db = kuzu.Database(str(db_path))
            conn = kuzu.Connection(db)

            for col, ddl in _MEMORY_COLUMNS:
                if not self._column_exists(conn, "Memory", col):
                    try:
                        conn.execute(ddl)
                        changes.append(ddl)
                        logger.info("Applied: %s", ddl)
                    except Exception as exc:
                        # Column may have been added by a concurrent process; treat as warning
                        warnings.append(f"Skipped {col} on Memory: {exc}")
                        logger.warning("Could not add Memory.%s: %s", col, exc)
                else:
                    logger.debug("Column Memory.%s already present — skipping", col)

            # ArchivedMemory is optional (may not exist in all deployments)
            try:
                for col, ddl in _ARCHIVED_COLUMNS:
                    if not self._column_exists(conn, "ArchivedMemory", col):
                        try:
                            conn.execute(ddl)
                            changes.append(ddl)
                            logger.info("Applied: %s", ddl)
                        except Exception as exc:
                            warnings.append(f"Skipped {col} on ArchivedMemory: {exc}")
                            logger.warning("Could not add ArchivedMemory.%s: %s", col, exc)
            except Exception as exc:
                warnings.append(f"ArchivedMemory column check skipped: {exc}")
                logger.warning("ArchivedMemory probe failed (table may not exist): %s", exc)

        except Exception as exc:
            logger.error("SchemaColumnsMigration failed: %s", exc)
            return MigrationResult(
                success=False,
                message=f"Migration failed: {exc}",
                changes=changes,
                warnings=warnings,
            )

        return MigrationResult(
            success=True,
            message=(
                f"Schema columns migration completed: {len(changes)} column(s) added"
                + (f", {len(warnings)} warning(s)" if warnings else "")
            ),
            changes=changes,
            warnings=warnings,
        )
