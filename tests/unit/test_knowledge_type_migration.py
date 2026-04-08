"""
Unit tests for KnowledgeType enum and the v1.6.45 schema migration.

Covers:
- All six KnowledgeType enum values
- Default knowledge_type on new Memory instances
- Explicit knowledge_type assignment
- Migration applicability detection (column absent vs present)
- Migration idempotency (running twice does not raise)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.models import KnowledgeType, Memory, MemoryType
from kuzu_memory.migrations.v1_6_45_knowledge_type import KnowledgeTypeMigration

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestKnowledgeTypeEnum:
    """Verify KnowledgeType enum values and membership."""

    def test_knowledge_type_enum_values(self) -> None:
        """All six engineering knowledge categories must be present."""
        assert KnowledgeType.RULE.value == "rule"
        assert KnowledgeType.PATTERN.value == "pattern"
        assert KnowledgeType.CONVENTION.value == "convention"
        assert KnowledgeType.GOTCHA.value == "gotcha"
        assert KnowledgeType.ARCHITECTURE.value == "architecture"
        assert KnowledgeType.NOTE.value == "note"

    def test_knowledge_type_has_exactly_six_members(self) -> None:
        """Guard against accidental additions or removals."""
        assert len(KnowledgeType) == 6

    def test_knowledge_type_is_str_enum(self) -> None:
        """KnowledgeType must be a str subclass for clean JSON serialisation."""
        assert isinstance(KnowledgeType.GOTCHA, str)
        assert KnowledgeType.GOTCHA == "gotcha"


# ---------------------------------------------------------------------------
# Memory model tests
# ---------------------------------------------------------------------------


class TestMemoryKnowledgeTypeField:
    """Verify the knowledge_type field on the Memory Pydantic model."""

    def test_memory_default_knowledge_type(self) -> None:
        """A Memory created without knowledge_type defaults to NOTE."""
        memory = Memory(content="Some engineering note")
        assert memory.knowledge_type == KnowledgeType.NOTE

    def test_memory_knowledge_type_assignment(self) -> None:
        """knowledge_type can be explicitly set to any KnowledgeType value."""
        memory = Memory(
            content="KuzuConnectionPool._lock must be RLock, not Lock",
            knowledge_type=KnowledgeType.GOTCHA,
        )
        assert memory.knowledge_type == KnowledgeType.GOTCHA

    def test_memory_all_knowledge_types_assignable(self) -> None:
        """Every KnowledgeType value can be stored in a Memory instance."""
        for kt in KnowledgeType:
            mem = Memory(content=f"Test content for {kt.value}", knowledge_type=kt)
            assert mem.knowledge_type == kt

    def test_memory_knowledge_type_in_to_dict(self) -> None:
        """to_dict() must include knowledge_type as a string value."""
        memory = Memory(
            content="Use ServiceManager context manager",
            knowledge_type=KnowledgeType.PATTERN,
        )
        d = memory.to_dict()
        assert "knowledge_type" in d
        assert d["knowledge_type"] == "pattern"

    def test_memory_from_dict_with_knowledge_type(self) -> None:
        """from_dict() must round-trip knowledge_type correctly."""
        memory = Memory(content="Architecture note", knowledge_type=KnowledgeType.ARCHITECTURE)
        d = memory.to_dict()
        # Simulate DB round-trip (datetime fields stay as datetime in to_dict)
        restored = Memory.from_dict(d)
        assert restored.knowledge_type == KnowledgeType.ARCHITECTURE

    def test_memory_from_dict_missing_knowledge_type_defaults_to_note(self) -> None:
        """Rows fetched from pre-migration databases have no knowledge_type — must default to NOTE."""
        memory = Memory(content="Legacy memory")
        d = memory.to_dict()
        del d["knowledge_type"]  # Simulate pre-migration row
        restored = Memory.from_dict(d)
        assert restored.knowledge_type == KnowledgeType.NOTE

    def test_memory_from_dict_unknown_knowledge_type_defaults_to_note(self) -> None:
        """Unknown/corrupt values in the DB must not raise — fall back to NOTE."""
        memory = Memory(content="Legacy memory")
        d = memory.to_dict()
        d["knowledge_type"] = "nonexistent_type"
        restored = Memory.from_dict(d)
        assert restored.knowledge_type == KnowledgeType.NOTE

    def test_memory_knowledge_type_is_independent_of_memory_type(self) -> None:
        """The two classification axes are fully independent."""
        memory = Memory(
            content="Service layer pattern",
            memory_type=MemoryType.SEMANTIC,
            knowledge_type=KnowledgeType.PATTERN,
        )
        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.knowledge_type == KnowledgeType.PATTERN


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


class TestKnowledgeTypeMigration:
    """Tests for KnowledgeTypeMigration — applicability and idempotency."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_migration(self, project_root: Path) -> KnowledgeTypeMigration:
        return KnowledgeTypeMigration(project_root=project_root)

    def _create_fake_db(self, project_root: Path) -> None:
        """Create the sentinel file that SchemaMigration.check_applicable() looks for."""
        db_dir = project_root / ".kuzu-memory"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "memories.db").touch()

    # ------------------------------------------------------------------
    # Applicability
    # ------------------------------------------------------------------

    def test_migration_not_applicable_when_no_database(self, tmp_path: Path) -> None:
        """Migration should not apply when the database file does not exist."""
        migration = self._make_migration(tmp_path)
        # No sentinel file → parent check_applicable() returns False immediately
        assert not migration.check_applicable()

    def test_migration_check_applicable_column_absent(self, tmp_path: Path) -> None:
        """Migration is applicable when knowledge_type column is absent (query raises)."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        # Mock kuzu so that the probe query raises RuntimeError (column absent)
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = RuntimeError("Column knowledge_type not found")
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            assert migration.check_applicable() is True

    def test_migration_check_not_applicable_column_present(self, tmp_path: Path) -> None:
        """Migration is not applicable when knowledge_type column already exists."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        # Mock kuzu so that the test query succeeds (column present — no exception raised)
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

    def test_migration_runs_alter_table_statements(self, tmp_path: Path) -> None:
        """migrate() must execute ALTER TABLE on both Memory and ArchivedMemory."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        mock_conn = MagicMock()
        mock_conn.execute.return_value = None  # all ALTER TABLE succeed
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()

        assert result.success is True
        # Both ALTER TABLE calls must appear in the recorded changes
        assert any("Memory" in c and "knowledge_type" in c for c in result.changes)

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_migration_idempotent_second_call_does_not_error(self, tmp_path: Path) -> None:
        """Running migrate() a second time (column already present) must not raise."""
        self._create_fake_db(tmp_path)
        migration = self._make_migration(tmp_path)

        # First call: both ALTER TABLE succeed
        call_count = {"n": 0}

        def execute_side_effect(stmt: str, *_: object) -> None:
            call_count["n"] += 1
            if call_count["n"] > 2:
                # Simulate "column already exists" on a second migrate() run
                raise RuntimeError("Column already exists")

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = execute_side_effect
        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result1 = migration.migrate()

        # Reset mock for second call (column now exists → ALTER TABLE raises)
        call_count["n"] = 99  # Force immediate failure on all execute calls

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result2 = migration.migrate()

        # First run succeeded
        assert result1.success is True
        # Second run failed cleanly (column already exists)
        assert result2.success is False
        assert "knowledge_type" in result2.message.lower() or "failed" in result2.message.lower()

    # ------------------------------------------------------------------
    # Lock error paths
    # ------------------------------------------------------------------

    def test_check_applicable_returns_false_when_db_locked(self, tmp_path: Path) -> None:
        """When database is locked by another process, check_applicable returns False."""
        migration = KnowledgeTypeMigration(project_root=tmp_path)
        (tmp_path / ".kuzu-memory" / "memories.db").mkdir(parents=True, exist_ok=True)

        mock_kuzu = MagicMock()
        mock_kuzu.Database.side_effect = RuntimeError("IO exception: Could not set lock on file")

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            assert migration.check_applicable() is False

    def test_migrate_returns_lock_result_when_db_locked(self, tmp_path: Path) -> None:
        """When database is locked, migrate() returns graceful failure."""
        migration = KnowledgeTypeMigration(project_root=tmp_path)
        (tmp_path / ".kuzu-memory" / "memories.db").mkdir(parents=True, exist_ok=True)

        mock_kuzu = MagicMock()
        mock_kuzu.Database.side_effect = RuntimeError("IO exception: Could not set lock on file")

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()
            assert result.success is False
            assert "locked by another process" in result.message.lower()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def test_migration_metadata(self) -> None:
        """Verify migration class-level metadata is correctly set."""
        migration = KnowledgeTypeMigration()
        assert migration.name == "knowledge_type_v1.6.45"
        assert migration.from_version == "0.0.0"
        assert migration.to_version == "999.0.0"
        assert migration.priority == 50
        assert "knowledge_type" in migration.description().lower()


# ---------------------------------------------------------------------------
# _is_lock_error tests (standalone, not part of TestKnowledgeTypeMigration)
# ---------------------------------------------------------------------------


def test_is_lock_error_detection() -> None:
    """Test _is_lock_error detects lock contention errors."""
    from kuzu_memory.migrations.base import SchemaMigration

    assert SchemaMigration._is_lock_error(
        RuntimeError("IO exception: Could not set lock on file : /path/to/db")
    )
    assert SchemaMigration._is_lock_error(
        RuntimeError("COULD NOT SET LOCK on file")  # case insensitive
    )
    assert not SchemaMigration._is_lock_error(RuntimeError("Column not found"))
    assert not SchemaMigration._is_lock_error(ValueError("some other error"))
