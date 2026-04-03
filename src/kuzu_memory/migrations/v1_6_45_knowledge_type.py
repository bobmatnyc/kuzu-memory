"""Schema migration to add knowledge_type column to Memory and ArchivedMemory tables."""

from __future__ import annotations

import logging

from .base import MigrationResult, MigrationType, SchemaMigration

logger = logging.getLogger(__name__)


class KnowledgeTypeMigration(SchemaMigration):
    """Add knowledge_type STRING column to Memory and ArchivedMemory node tables.

    KnowledgeType is an orthogonal axis to MemoryType: where MemoryType governs
    cognitive retention (episodic/semantic/procedural/etc.), KnowledgeType
    categorises *what kind* of engineering knowledge the memory represents
    (rule/pattern/convention/gotcha/architecture/note).

    All existing rows receive the default value 'note' via the ALTER TABLE DEFAULT.
    """

    name = "knowledge_type_v1.6.45"
    from_version = "0.0.0"
    to_version = "999.0.0"
    migration_type = MigrationType.SCHEMA
    priority = 50  # Run before data migrations

    def description(self) -> str:
        """Return human-readable description."""
        return (
            "Add knowledge_type STRING DEFAULT 'note' to Memory and ArchivedMemory tables "
            "for software-engineering knowledge categorisation"
        )

    def check_applicable(self) -> bool:
        """Return True when the knowledge_type column is absent from the Memory table.

        Strategy: attempt a lightweight query that projects knowledge_type.
        If Kùzu raises a runtime error the column does not exist yet → applicable.
        If the query succeeds the column already exists → not applicable (idempotent).

        Falls back to the parent check_applicable() (db file existence) first so
        we do not try to open a database that has never been initialised.
        """
        if not super().check_applicable():
            return False

        db_path = self._find_db_path()
        if db_path is None:
            return False

        try:
            result = self._open_database(db_path)
            if result is None:
                # Database locked — skip migration this run, retry on next startup
                return False
            db, conn = result
            try:
                conn.execute("MATCH (m:Memory) RETURN m.knowledge_type LIMIT 1")
                # Query succeeded → column already exists
                return False
            finally:
                conn.close()
                db.close()
        except Exception:
            # Any error (missing column, kuzu unavailable, etc.) → applicable
            return True

    def migrate(self) -> MigrationResult:
        """Add knowledge_type column to Memory and, if present, ArchivedMemory."""
        changes: list[str] = []

        db_path = self._find_db_path()
        if db_path is None:
            return MigrationResult(
                success=False,
                message="Database not found — cannot run knowledge_type migration",
                changes=changes,
            )

        try:
            result = self._open_database(db_path)
            if result is None:
                return MigrationResult(
                    success=False,
                    message="Database locked by another process — migration will retry on next startup",
                    changes=changes,
                )
            db, conn = result
            try:
                # --- Memory table ---
                try:
                    conn.execute("ALTER TABLE Memory ADD knowledge_type STRING DEFAULT 'note'")
                    changes.append("ALTER TABLE Memory ADD knowledge_type STRING DEFAULT 'note'")
                    logger.info("Added knowledge_type column to Memory table")
                except Exception as exc:
                    logger.warning("Could not alter Memory table: %s", exc)
                    return MigrationResult(
                        success=False,
                        message=f"Failed to add knowledge_type to Memory: {exc}",
                        changes=changes,
                    )

                # --- ArchivedMemory table (optional — may not exist in all databases) ---
                try:
                    conn.execute(
                        "ALTER TABLE ArchivedMemory ADD knowledge_type STRING DEFAULT 'note'"
                    )
                    changes.append(
                        "ALTER TABLE ArchivedMemory ADD knowledge_type STRING DEFAULT 'note'"
                    )
                    logger.info("Added knowledge_type column to ArchivedMemory table")
                except Exception as exc:
                    # ArchivedMemory may not exist in older databases; treat as a warning
                    logger.warning("Skipped ArchivedMemory (table may not exist): %s", exc)
                    changes.append("Skipped ArchivedMemory: table absent or column already present")

                # NOTE: Kùzu does not support CREATE INDEX on non-primary-key properties.
                # Columnar storage and vectorised execution provide equivalent performance
                # for MATCH predicates on knowledge_type without an explicit index.
            finally:
                conn.close()
                db.close()

        except Exception as exc:
            logger.error("KnowledgeTypeMigration failed: %s", exc)
            return MigrationResult(
                success=False,
                message=f"Migration failed: {exc}",
                changes=changes,
            )

        return MigrationResult(
            success=True,
            message="Successfully added knowledge_type column to Memory (and ArchivedMemory if present)",
            changes=changes,
        )
