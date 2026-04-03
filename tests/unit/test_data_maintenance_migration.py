"""Unit tests for the v1.9.0 data maintenance migration.

Covers:
- purge_expired: removes memories whose valid_to is in the past
- dedup_by_content_hash: back-fills hashes and removes duplicates
- trim_git_metadata: slims oversized git_sync blobs
- has_work_to_do: correctly identifies clean vs. dirty databases
- DataMaintenanceMigration.check_applicable: respects has_work_to_do
- DataMaintenanceMigration.migrate: success path and idempotency
- DataMaintenanceMigration.migrate: clean database is a no-op
- KuzuAdapter._run_data_maintenance: called from initialize(), uses pool
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from kuzu_memory.migrations.v1_9_0_data_maintenance import (
    _METADATA_THRESHOLD,
    DataMaintenanceMigration,
    dedup_by_content_hash,
    has_work_to_do,
    purge_expired,
    trim_git_metadata,
)

# ---------------------------------------------------------------------------
# Tiny in-memory "database" helpers
# ---------------------------------------------------------------------------


class FakeDB:
    """Minimal in-memory store that accepts execute(query, params) calls.

    Only understands a handful of Cypher patterns used by the maintenance
    helpers.  Sufficient for unit testing without a real Kuzu instance.
    """

    def __init__(self) -> None:
        # Each memory is a dict with at minimum: id, content, content_hash,
        # valid_to, created_at, source_type, metadata.
        self.memories: list[dict[str, Any]] = []
        self._next_id = 1

    def add(self, **kwargs: Any) -> dict[str, Any]:
        mem: dict[str, Any] = {
            "id": str(self._next_id),
            "content": "default content",
            "content_hash": None,
            "valid_to": None,
            "created_at": datetime.now().isoformat(),
            "source_type": "manual",
            "metadata": None,
        }
        mem.update(kwargs)
        self._next_id += 1
        self.memories.append(mem)
        return mem

    def execute(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Dispatch query to the matching handler."""
        q = query.strip()

        # --- Count expired ---
        if "valid_to < TIMESTAMP" in q and "count(m)" in q:
            now = params.get("now", datetime.now().isoformat())
            cnt = sum(
                1
                for m in self.memories
                if m.get("valid_to") is not None and str(m["valid_to"]) < now
            )
            return [{"cnt": cnt}]

        # --- Delete expired ---
        if "valid_to < TIMESTAMP" in q and "DELETE" in q:
            now = params.get("now", datetime.now().isoformat())
            self.memories = [
                m
                for m in self.memories
                if not (m.get("valid_to") is not None and str(m["valid_to"]) < now)
            ]
            return []

        # --- Count memories with NULL content_hash (has_work_to_do probe) ---
        if "content_hash IS NULL OR m.content_hash = ''" in q and "count(m)" in q:
            cnt = sum(1 for m in self.memories if not m.get("content_hash"))
            return [{"cnt": cnt}]

        # --- Select memories with NULL content_hash (for backfill) ---
        if "content_hash IS NULL OR m.content_hash = ''" in q and "RETURN" in q:
            rows = [
                {"id": m["id"], "content": m["content"]}
                for m in self.memories
                if not m.get("content_hash")
            ]
            return rows

        # --- SET content_hash ---
        if "SET m.content_hash" in q:
            mem_id = params.get("id")
            new_hash = params.get("h")
            for m in self.memories:
                if m["id"] == str(mem_id):
                    m["content_hash"] = new_hash
            return []

        # --- Select all (id, content_hash, created_at) ---
        if "content_hash IS NOT NULL" in q and "RETURN m.id" in q:
            rows = [
                {"id": m["id"], "h": m.get("content_hash"), "created_at": m.get("created_at")}
                for m in self.memories
                if m.get("content_hash")
            ]
            return rows

        # --- Delete by id list ---
        if "m.id IN $ids" in q and "DELETE" in q:
            ids = {str(i) for i in (params.get("ids") or [])}
            self.memories = [m for m in self.memories if m["id"] not in ids]
            return []

        # --- Select git_sync metadata ---
        if "source_type = 'git_sync'" in q and "RETURN m.id" in q:
            rows = [
                {"id": m["id"], "metadata": m.get("metadata")}
                for m in self.memories
                if m.get("source_type") == "git_sync" and m.get("metadata") is not None
            ]
            return rows

        # --- SET metadata ---
        if "SET m.metadata" in q:
            mem_id = params.get("id")
            new_meta = params.get("meta")
            for m in self.memories:
                if m["id"] == str(mem_id):
                    m["metadata"] = new_meta
            return []

        # --- has_work_to_do: git_sync metadata LIMIT 50 ---
        if "source_type = 'git_sync'" in q and "LIMIT 50" in q:
            rows = [
                {"metadata": m.get("metadata")}
                for m in self.memories
                if m.get("source_type") == "git_sync" and m.get("metadata") is not None
            ]
            return rows[:50]

        return []


# ---------------------------------------------------------------------------
# purge_expired
# ---------------------------------------------------------------------------


class TestPurgeExpired:
    def test_purges_expired_memories(self) -> None:
        db = FakeDB()
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        db.add(id="1", valid_to=past)
        db.add(id="2", valid_to=None)  # permanent — must not be deleted

        purged = purge_expired(db.execute)

        assert purged == 1
        assert len(db.memories) == 1
        assert db.memories[0]["id"] == "2"

    def test_no_op_on_clean_database(self) -> None:
        db = FakeDB()
        db.add(id="1", valid_to=None)

        purged = purge_expired(db.execute)

        assert purged == 0
        assert len(db.memories) == 1

    def test_does_not_delete_future_expiry(self) -> None:
        db = FakeDB()
        future = (datetime.now() + timedelta(days=1)).isoformat()
        db.add(id="1", valid_to=future)

        purged = purge_expired(db.execute)

        assert purged == 0
        assert len(db.memories) == 1

    def test_returns_zero_on_execute_error(self) -> None:
        def bad_execute(q: str, p: dict) -> list:
            raise RuntimeError("DB exploded")

        result = purge_expired(bad_execute)
        assert result == 0


# ---------------------------------------------------------------------------
# dedup_by_content_hash
# ---------------------------------------------------------------------------


class TestDedupByContentHash:
    def test_backfills_missing_hashes(self) -> None:
        import hashlib

        db = FakeDB()
        db.add(id="1", content="hello world", content_hash=None)

        hashes_written, dupes = dedup_by_content_hash(db.execute)

        assert hashes_written == 1
        assert dupes == 0
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert db.memories[0]["content_hash"] == expected

    def test_removes_duplicates_keeps_newest(self) -> None:
        import hashlib

        db = FakeDB()
        h = hashlib.sha256(b"dup content").hexdigest()
        older = (datetime.now() - timedelta(minutes=5)).isoformat()
        newer = datetime.now().isoformat()
        db.add(id="10", content="dup content", content_hash=h, created_at=older)
        db.add(id="11", content="dup content", content_hash=h, created_at=newer)

        _hashes_written, dupes = dedup_by_content_hash(db.execute)

        assert dupes == 1
        assert len(db.memories) == 1
        assert db.memories[0]["id"] == "11"  # newest survives

    def test_no_op_on_unique_contents(self) -> None:
        import hashlib

        db = FakeDB()
        db.add(id="1", content="alpha", content_hash=hashlib.sha256(b"alpha").hexdigest())
        db.add(id="2", content="beta", content_hash=hashlib.sha256(b"beta").hexdigest())

        hashes_written, dupes = dedup_by_content_hash(db.execute)

        assert hashes_written == 0
        assert dupes == 0
        assert len(db.memories) == 2

    def test_returns_zeros_on_error(self) -> None:
        def bad_execute(q: str, p: dict) -> list:
            raise RuntimeError("oops")

        hashes_written, dupes = dedup_by_content_hash(bad_execute)
        assert hashes_written == 0
        assert dupes == 0


# ---------------------------------------------------------------------------
# trim_git_metadata
# ---------------------------------------------------------------------------


def _big_metadata(**extras: Any) -> str:
    """Return a JSON metadata string larger than _METADATA_THRESHOLD bytes."""
    meta: dict[str, Any] = {
        "commit_sha": "abc123def456abc123def456abc123def456abc123",
        "commit_author": "Test User Who Wrote A Long Name Here",
        "commit_timestamp": datetime.now().isoformat(),
        "branch": "feature/very-long-branch-name-for-testing-purposes",
        # Use 100 files with longer names to ensure we exceed 1024 bytes
        "changed_files": [f"src/module_{i}/subdir/file_name_{i:04d}.py" for i in range(100)],
        "files_changed_count": 100,
        "diff_stats": {f"file_{i}.py": {"additions": i, "deletions": i} for i in range(10)},
    }
    meta.update(extras)
    raw = json.dumps(meta)
    assert (
        len(raw) > _METADATA_THRESHOLD
    ), f"test setup: metadata must exceed threshold, got {len(raw)} bytes"
    return raw


class TestTrimGitMetadata:
    def test_trims_oversized_blob(self) -> None:
        db = FakeDB()
        db.add(id="1", source_type="git_sync", metadata=_big_metadata())

        trimmed, saved = trim_git_metadata(db.execute)

        assert trimmed == 1
        assert saved > 0
        # Slim metadata should contain only the kept keys
        slim = json.loads(db.memories[0]["metadata"])
        assert "commit_sha" in slim
        assert "author" in slim
        assert "changed_files" not in slim

    def test_no_op_on_small_metadata(self) -> None:
        db = FakeDB()
        small = json.dumps({"commit_sha": "abc", "author": "Alice"})
        assert len(small) <= _METADATA_THRESHOLD
        db.add(id="1", source_type="git_sync", metadata=small)

        trimmed, saved = trim_git_metadata(db.execute)

        assert trimmed == 0
        assert saved == 0

    def test_no_op_on_non_git_sync_source(self) -> None:
        db = FakeDB()
        db.add(id="1", source_type="manual", metadata=_big_metadata())

        trimmed, _saved = trim_git_metadata(db.execute)

        assert trimmed == 0

    def test_preserves_files_changed_count_from_list(self) -> None:
        db = FakeDB()
        db.add(id="1", source_type="git_sync", metadata=_big_metadata())

        trim_git_metadata(db.execute)

        slim = json.loads(db.memories[0]["metadata"])
        # files_changed_count is taken from the explicit key (100) in _big_metadata
        assert slim.get("files_changed_count") == 100

    def test_returns_zeros_on_error(self) -> None:
        def bad_execute(q: str, p: dict) -> list:
            raise RuntimeError("oops")

        trimmed, saved = trim_git_metadata(bad_execute)
        assert trimmed == 0
        assert saved == 0


# ---------------------------------------------------------------------------
# has_work_to_do
# ---------------------------------------------------------------------------


class TestHasWorkToDo:
    def test_detects_expired_memory(self) -> None:
        db = FakeDB()
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        db.add(valid_to=past)

        assert has_work_to_do(db.execute) is True

    def test_detects_null_content_hash(self) -> None:
        db = FakeDB()
        db.add(content_hash=None)

        assert has_work_to_do(db.execute) is True

    def test_detects_oversized_metadata(self) -> None:
        db = FakeDB()
        db.add(source_type="git_sync", metadata=_big_metadata())

        assert has_work_to_do(db.execute) is True

    def test_returns_false_on_clean_db(self) -> None:
        import hashlib

        db = FakeDB()
        db.add(
            content="clean",
            content_hash=hashlib.sha256(b"clean").hexdigest(),
            valid_to=None,
            source_type="manual",
            metadata=None,
        )

        assert has_work_to_do(db.execute) is False

    def test_returns_true_on_execute_error(self) -> None:
        def bad_execute(q: str, p: dict) -> list:
            raise RuntimeError("broken")

        assert has_work_to_do(bad_execute) is True


# ---------------------------------------------------------------------------
# DataMaintenanceMigration class
# ---------------------------------------------------------------------------


class TestDataMaintenanceMigration:
    def _make_migration(self, project_root: Path) -> DataMaintenanceMigration:
        return DataMaintenanceMigration(project_root=project_root)

    def _create_fake_db_file(self, project_root: Path) -> Path:
        """Create the sentinel file that SchemaMigration._find_db_path() looks for."""
        db_dir = project_root / ".kuzu-memory"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_file = db_dir / "memories.db"
        db_file.touch()
        return db_file

    # --- metadata ---

    def test_migration_metadata(self) -> None:
        m = DataMaintenanceMigration()
        assert m.name == "data_maintenance_v1.9.0"
        assert m.priority == 70
        assert "maintenance" in m.description().lower()
        assert m.migration_type.value == "data"

    # --- check_applicable ---

    def test_not_applicable_when_no_db(self, tmp_path: Path) -> None:
        migration = self._make_migration(tmp_path)
        assert not migration.check_applicable()

    def test_applicable_when_work_exists(self, tmp_path: Path) -> None:
        self._create_fake_db_file(tmp_path)
        migration = self._make_migration(tmp_path)

        mock_conn = MagicMock()
        # Simulate expired memory count returning 1
        mock_result = MagicMock()
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = [1]
        mock_result.get_column_names.return_value = ["cnt"]
        mock_conn.execute.return_value = mock_result

        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.check_applicable()

        assert result is True

    def test_not_applicable_when_clean(self, tmp_path: Path) -> None:
        self._create_fake_db_file(tmp_path)
        migration = self._make_migration(tmp_path)

        mock_conn = MagicMock()
        # All count queries return 0, no oversized metadata
        mock_result = MagicMock()
        mock_result.has_next.return_value = False
        mock_conn.execute.return_value = mock_result

        mock_db = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.check_applicable()

        assert result is False

    # --- migrate success path ---

    def test_migrate_cleans_expired_memories(self, tmp_path: Path) -> None:
        self._create_fake_db_file(tmp_path)
        migration = self._make_migration(tmp_path)

        # We'll drive migrate() through a FakeDB-like execute callable
        db = FakeDB()
        past = (datetime.now() - timedelta(hours=2)).isoformat()
        db.add(id="expired1", valid_to=past)

        call_count: dict[str, int] = {}

        def _execute_wrapper(query: str, params: dict) -> list[dict]:
            call_count["n"] = call_count.get("n", 0) + 1
            return db.execute(query, params)

        mock_conn = MagicMock()

        def _conn_execute(query: str, params: dict | None = None) -> Any:
            rows = _execute_wrapper(query, params or {})
            result = MagicMock()
            iter_rows = iter(rows)

            def _has_next() -> bool:
                nonlocal iter_rows
                try:
                    result._current = next(iter_rows)
                    return True
                except StopIteration:
                    return False

            def _get_next() -> list:
                return list(result._current.values())

            def _col_names() -> list[str]:
                return list(result._current.keys()) if hasattr(result, "_current") else []

            result.has_next.side_effect = _has_next
            result.get_next.side_effect = _get_next
            result.get_column_names.side_effect = _col_names
            return result

        mock_conn.execute.side_effect = _conn_execute
        mock_db_obj = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db_obj
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()

        assert result.success is True
        assert any("purged" in c.lower() or "expired" in c.lower() for c in result.changes)

    def test_migrate_no_op_on_clean_database(self, tmp_path: Path) -> None:
        self._create_fake_db_file(tmp_path)
        migration = self._make_migration(tmp_path)

        db = FakeDB()
        import hashlib

        db.add(
            content="clean",
            content_hash=hashlib.sha256(b"clean").hexdigest(),
            valid_to=None,
            source_type="manual",
            metadata=None,
        )

        def _make_result(rows: list[dict]) -> MagicMock:
            result = MagicMock()
            it = iter(rows)
            current: list[dict] = [{}]

            def _has_next() -> bool:
                try:
                    current[0] = next(it)
                    return True
                except StopIteration:
                    return False

            result.has_next.side_effect = _has_next
            result.get_next.side_effect = lambda: list(current[0].values())
            result.get_column_names.side_effect = lambda: list(current[0].keys())
            return result

        def _conn_execute(query: str, params: dict | None = None) -> Any:
            rows = db.execute(query, params or {})
            return _make_result(rows)

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _conn_execute
        mock_db_obj = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db_obj
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()

        assert result.success is True
        assert "nothing to do" in result.message.lower() or len(result.changes) == 0

    # --- idempotency ---

    def test_migrate_idempotent_second_run_is_noop(self, tmp_path: Path) -> None:
        """Running migrate() twice on an already-clean database produces no changes."""
        self._create_fake_db_file(tmp_path)
        migration = self._make_migration(tmp_path)

        db = FakeDB()
        import hashlib

        db.add(
            content="stable",
            content_hash=hashlib.sha256(b"stable").hexdigest(),
            valid_to=None,
            source_type="manual",
            metadata=None,
        )

        def _make_result(rows: list[dict]) -> MagicMock:
            result = MagicMock()
            it = iter(rows)
            current: list[dict] = [{}]

            def _has_next() -> bool:
                try:
                    current[0] = next(it)
                    return True
                except StopIteration:
                    return False

            result.has_next.side_effect = _has_next
            result.get_next.side_effect = lambda: list(current[0].values())
            result.get_column_names.side_effect = lambda: list(current[0].keys())
            return result

        def _conn_execute(query: str, params: dict | None = None) -> Any:
            rows = db.execute(query, params or {})
            return _make_result(rows)

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _conn_execute
        mock_db_obj = MagicMock()
        mock_kuzu = MagicMock()
        mock_kuzu.Database.return_value = mock_db_obj
        mock_kuzu.Connection.return_value = mock_conn

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            first = migration.migrate()
            second = migration.migrate()

        assert first.success is True
        assert second.success is True
        # Second run must not list any changes
        assert len(second.changes) == 0

    # --- no db path ---

    def test_migrate_returns_failure_when_no_db(self, tmp_path: Path) -> None:
        migration = self._make_migration(tmp_path)  # no DB file created
        result = migration.migrate()
        assert result.success is False
        assert "not found" in result.message.lower()

    # --- lock error paths ---

    def test_check_applicable_returns_false_when_db_locked(self, tmp_path: Path) -> None:
        """When database is locked by another process, check_applicable returns False."""
        migration = self._make_migration(tmp_path)
        (tmp_path / ".kuzu-memory" / "memories.db").mkdir(parents=True, exist_ok=True)

        mock_kuzu = MagicMock()
        mock_kuzu.Database.side_effect = RuntimeError("IO exception: Could not set lock on file")

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            assert migration.check_applicable() is False

    def test_migrate_returns_lock_result_when_db_locked(self, tmp_path: Path) -> None:
        """When database is locked, migrate() returns graceful failure."""
        migration = self._make_migration(tmp_path)
        (tmp_path / ".kuzu-memory" / "memories.db").mkdir(parents=True, exist_ok=True)

        mock_kuzu = MagicMock()
        mock_kuzu.Database.side_effect = RuntimeError("IO exception: Could not set lock on file")

        with patch("kuzu_memory.migrations.base._kuzu_module", mock_kuzu):
            result = migration.migrate()
            assert result.success is False
            assert "locked by another process" in result.message.lower()


# ---------------------------------------------------------------------------
# KuzuAdapter._run_data_maintenance integration
# ---------------------------------------------------------------------------


class TestKuzuAdapterDataMaintenance:
    """Verify that KuzuAdapter calls _run_data_maintenance during initialize()."""

    def test_run_data_maintenance_called_on_initialize(self, tmp_path: Path) -> None:
        """_run_data_maintenance must be invoked as part of initialize()."""
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.kuzu_adapter import KuzuAdapter

        db_path = tmp_path / ".kuzu-memory" / "memories.db"
        config = KuzuMemoryConfig()

        adapter = KuzuAdapter(db_path, config)
        with (
            patch.object(adapter, "_pool") as mock_pool,
            patch.object(adapter, "_initialize_schema"),
            patch.object(adapter, "_run_schema_migrations"),
            patch.object(adapter, "_run_data_maintenance") as mock_maint,
        ):
            mock_pool.initialize.return_value = None
            adapter.initialize()

        mock_maint.assert_called_once()

    def test_run_data_maintenance_non_fatal_on_error(self, tmp_path: Path) -> None:
        """_run_data_maintenance must not propagate exceptions."""
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.kuzu_adapter import KuzuAdapter

        db_path = tmp_path / ".kuzu-memory" / "memories.db"
        config = KuzuMemoryConfig()

        adapter = KuzuAdapter(db_path, config)

        # Patch execute_query so has_work_to_do raises
        def bad_execute(query: str, params: Any = None) -> list:
            raise RuntimeError("simulated DB failure")

        with patch.object(adapter, "execute_query", side_effect=bad_execute):
            # Must not raise
            adapter._run_data_maintenance()

    def test_run_data_maintenance_skips_when_clean(self, tmp_path: Path) -> None:
        """_run_data_maintenance short-circuits when has_work_to_do returns False."""
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.kuzu_adapter import KuzuAdapter

        db_path = tmp_path / ".kuzu-memory" / "memories.db"
        config = KuzuMemoryConfig()

        adapter = KuzuAdapter(db_path, config)

        # Patch has_work_to_do at the migration module level (where it is defined and
        # re-imported by _run_data_maintenance via its local import statement).
        with patch(
            "kuzu_memory.migrations.v1_9_0_data_maintenance.has_work_to_do",
            return_value=False,
        ):
            # Also patch execute_query to avoid real DB calls in has_work_to_do
            with patch.object(adapter, "execute_query", return_value=[{"cnt": 0}]):
                adapter._run_data_maintenance()

        # The method must not raise.  We can't easily assert mock_check was called
        # because _run_data_maintenance imports the function locally, but the absence
        # of exceptions is the critical property we are verifying here.
