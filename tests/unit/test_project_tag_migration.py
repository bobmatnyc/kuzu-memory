"""
Unit tests for the v1.6.46 project_tag schema migration.

Covers:
- Migration applicability detection (column absent vs present)
- Migration idempotency (running twice does not raise)
- ALTER TABLE statements applied to both Memory and ArchivedMemory
- Lock-error handling (database held by another process)
- Migration class metadata
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.migrations.v1_6_46_project_tag import ProjectTagMigration


class TestProjectTagMigration:
    """Tests for ProjectTagMigration — applicability, idempotency, and metadata."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_migration(self, project_root: Path) -> ProjectTagMigration:
        return ProjectTagMigration(project_root=project_root)

    def _create_fake_db(self, project_root: Path) -> None:
        """Create the sentinel file that SchemaMigration._find_db_path() looks for."""
        db_dir = project_root / ".kuzu-memory"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "memories.db").touch()

    # ------------------------------------------------------------------
    # Applicability
    # ------------------------------------------------------------------

    def test_migration_not_applicable_when_no_database(self, tmp_path: Path) -> None:
        """Migration should not apply when the database file does not exist."""
        migration = self._make_migration(tmp_path)
        assert not migration.check_applicable()

    def test_migration_check_applicable_column_absent(self, tmp_path: Path) -> None:
        """Migration is applicable when project_tag column is absent (probe query raises)."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        # Mock kuzu so that the probe query raises RuntimeError (column absent)
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = RuntimeError("Column project_tag not found")
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            assert migration.check_applicable() is True

    def test_migration_check_not_applicable_column_present(self, tmp_path: Path) -> None:
        """Migration is not applicable when project_tag column already exists."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        # Mock kuzu so that the probe query succeeds (column present — no exception)
        mock_conn = MagicMock()
        mock_conn.execute.return_value = None  # success means column exists
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            assert migration.check_applicable() is False

    # ------------------------------------------------------------------
    # migrate() success path
    # ------------------------------------------------------------------

    def test_migration_runs_alter_table_on_memory(self, tmp_path: Path) -> None:
        """migrate() must execute ALTER TABLE ADD project_tag on Memory table."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        mock_conn = MagicMock()
        mock_conn.execute.return_value = None  # all statements succeed
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()

        assert result.success is True
        assert any("Memory" in c and "project_tag" in c for c in result.changes)

    def test_migration_runs_alter_table_on_archived_memory(self, tmp_path: Path) -> None:
        """migrate() should also attempt ALTER TABLE on ArchivedMemory."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        mock_conn = MagicMock()
        mock_conn.execute.return_value = None  # both ALTER TABLE succeed
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()

        assert result.success is True
        assert any("ArchivedMemory" in c and "project_tag" in c for c in result.changes)

    def test_migration_archived_memory_failure_is_non_fatal(self, tmp_path: Path) -> None:
        """ArchivedMemory ALTER failure is captured in warnings, not a hard error."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        call_log: list[str] = []

        def execute_side_effect(stmt: str, *_: object) -> None:
            call_log.append(stmt)
            if "ArchivedMemory" in stmt:
                raise RuntimeError("ArchivedMemory table does not exist")

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = execute_side_effect
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()

        assert result.success is True
        assert any("ArchivedMemory" in w for w in result.warnings)

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_project_tag_migration_is_idempotent(self, tmp_path: Path) -> None:
        """Running migrate() when column already exists must not raise."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        call_count = {"n": 0}

        def execute_side_effect(stmt: str, *_: object) -> None:
            call_count["n"] += 1
            if call_count["n"] > 2:
                # Simulate "column already exists" on second migrate() run
                raise RuntimeError("Column already exists")

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = execute_side_effect
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result1 = migration.migrate()

        # Force all execute calls to fail on second run (column already exists)
        call_count["n"] = 99

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result2 = migration.migrate()

        # First run succeeded
        assert result1.success is True
        # Second run failed cleanly (column already exists — no crash)
        assert result2.success is False
        assert "project_tag" in result2.message.lower() or "failed" in result2.message.lower()

    def test_project_tag_migration_on_existing_db(self, tmp_path: Path) -> None:
        """check_applicable() returns False immediately for a DB that already has project_tag."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        # Simulate a database where project_tag already exists (probe succeeds)
        mock_conn = MagicMock()
        mock_conn.execute.return_value = MagicMock()  # no exception = column present
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            # check_applicable must return False when column exists
            applicable = migration.check_applicable()

        assert applicable is False

    # ------------------------------------------------------------------
    # Lock error paths
    # ------------------------------------------------------------------

    def test_check_applicable_returns_false_when_db_locked(self, tmp_path: Path) -> None:
        """When database is locked by another process, check_applicable returns False."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        mock_kuzu = MagicMock()
        mock_kuzu.Database.side_effect = RuntimeError("IO exception: Could not set lock on file")

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            assert migration.check_applicable() is False

    def test_migrate_returns_lock_result_when_db_locked(self, tmp_path: Path) -> None:
        """When database is locked, migrate() returns graceful failure."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        mock_kuzu = MagicMock()
        mock_kuzu.Database.side_effect = RuntimeError("IO exception: Could not set lock on file")

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()

        assert result.success is False
        assert "locked by another process" in result.message.lower()

    def test_migrate_returns_failure_when_no_database(self, tmp_path: Path) -> None:
        """migrate() returns failure gracefully when no database file exists."""
        migration = self._make_migration(tmp_path)
        result = migration.migrate()
        assert result.success is False
        assert "not found" in result.message.lower() or "cannot run" in result.message.lower()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def test_migration_metadata(self) -> None:
        """Verify migration class-level metadata is correctly set."""
        migration = ProjectTagMigration()
        assert migration.name == "project_tag_v1.6.46"
        assert migration.from_version == "1.6.46"
        assert migration.to_version == "999.0.0"
        assert migration.priority == 50
        assert "project_tag" in migration.description().lower()
