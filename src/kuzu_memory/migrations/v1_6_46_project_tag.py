"""Migration to add project_tag field to Memory and ArchivedMemory tables (v1.6.46)."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import MigrationResult, SchemaMigration

logger = logging.getLogger(__name__)


class ProjectTagMigration(SchemaMigration):
    """
    Add project_tag STRING field to Memory and ArchivedMemory tables.

    This field supports user-level cross-project memory:
    - Project DB: always empty string (project is implicit from DB path)
    - User DB: set to the source project basename at promotion time

    Migration strategy: ALTER TABLE ADD with DEFAULT '' so existing rows
    get an empty string automatically without requiring a full table scan.
    """

    name = "project_tag_v1.6.46"
    from_version = "1.6.46"
    to_version = "999.0.0"
    priority = 50  # Run early (before cleanup migrations at 900)

    def description(self) -> str:
        """Return migration description."""
        return (
            "Add project_tag STRING DEFAULT '' to Memory and ArchivedMemory "
            "tables for user-level cross-project memory tracking"
        )

    def check_applicable(self) -> bool:
        """
        Check if migration should run.

        Probes whether project_tag already exists on the Memory table.
        If the probe raises (column not found), the migration is applicable.
        Returns False if project_tag already exists or DB doesn't exist.
        """
        db_path = self._find_db_path()
        if db_path is None or not db_path.exists():
            return False

        try:
            import kuzu

            db = kuzu.Database(str(db_path))
            conn = kuzu.Connection(db)
            # If project_tag doesn't exist this will raise
            conn.execute("MATCH (m:Memory) RETURN m.project_tag LIMIT 1")
            return False  # Column already exists — migration not needed
        except Exception:
            return True  # Column missing — migration needed

    def migrate(self) -> MigrationResult:
        """
        Add project_tag column to Memory and ArchivedMemory tables.

        Uses ALTER TABLE ADD with DEFAULT '' so existing rows get empty string.
        ArchivedMemory failure is wrapped in try/except because the table may
        not exist in all deployments.
        """
        db_path = self._find_db_path()
        if db_path is None or not db_path.exists():
            return MigrationResult(
                success=False,
                message="Database not found — cannot run project_tag migration",
                changes=[],
            )

        changes: list[str] = []
        warnings: list[str] = []

        try:
            import kuzu

            db = kuzu.Database(str(db_path))
            conn = kuzu.Connection(db)

            # Add to Memory table
            conn.execute("ALTER TABLE Memory ADD project_tag STRING DEFAULT ''")
            changes.append("ALTER TABLE Memory ADD project_tag STRING DEFAULT ''")
            logger.info("Added project_tag to Memory table")

            # Add to ArchivedMemory table (may not exist in all deployments)
            try:
                conn.execute("ALTER TABLE ArchivedMemory ADD project_tag STRING DEFAULT ''")
                changes.append("ALTER TABLE ArchivedMemory ADD project_tag STRING DEFAULT ''")
                logger.info("Added project_tag to ArchivedMemory table")
            except Exception as e:
                warning = f"ArchivedMemory migration skipped (table may not exist): {e}"
                warnings.append(warning)
                logger.warning(warning)

        except Exception as e:
            logger.error(f"project_tag migration failed: {e}")
            return MigrationResult(
                success=False,
                message=f"Migration failed: {e}",
                changes=changes,
                warnings=warnings,
            )

        return MigrationResult(
            success=True,
            message=f"Added project_tag field ({len(changes)} table(s) updated)",
            changes=changes,
            warnings=warnings,
        )

    def _find_db_path(self) -> Path | None:
        """Locate the project database file.

        Returns the path to the memories.db file, not the parent directory.
        Kuzu requires a file path; passing a directory raises
        "Database path cannot be a directory".
        """
        # Current format: .kuzu-memory/memories.db
        candidate = self.project_root / ".kuzu-memory" / "memories.db"
        if candidate.exists():
            return candidate
        # Legacy locations
        for legacy in ("kuzu-memories", ".kuzu-memories"):
            p = self.project_root / legacy / "memories.db"
            if p.exists():
                return p
        return None
