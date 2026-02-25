"""
Unit tests for the memory sharing module (export_shared / import_shared)
and the migrate_db_location utility.

These are integration-style tests that use real Kùzu databases created in
tmp_path so that we exercise the actual SQL and file-system behaviour without
mocking the database layer.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Schema helpers (shared across tests)
# ---------------------------------------------------------------------------

MEMORY_SCHEMA_DDL = """
CREATE NODE TABLE IF NOT EXISTS Memory (
    id STRING PRIMARY KEY,
    content STRING,
    content_hash STRING,
    created_at TIMESTAMP,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    accessed_at TIMESTAMP,
    access_count INT32 DEFAULT 0,
    memory_type STRING DEFAULT 'semantic',
    importance FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 1.0,
    source_type STRING DEFAULT 'conversation',
    agent_id STRING DEFAULT 'default',
    user_id STRING,
    session_id STRING,
    metadata STRING DEFAULT '{}'
)
"""


def _content_hash(content: str) -> str:
    """Stable SHA-256 hash mirroring the production helper."""
    return hashlib.sha256(content.lower().encode()).hexdigest()


def _init_db(db_path: Path) -> None:
    """Create an empty Kùzu database with the Memory schema."""
    import kuzu

    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    for stmt in MEMORY_SCHEMA_DDL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    del conn
    del db


def _insert_memory(
    db_path: Path,
    *,
    content: str,
    source_type: str = "ai-conversation",
    created_at: datetime | None = None,
    memory_type: str = "semantic",
    importance: float = 0.5,
    confidence: float = 1.0,
    agent_id: str = "default",
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: str = "{}",
    memory_id: str | None = None,
) -> str:
    """Insert a single memory into the database and return its id."""
    import kuzu

    mem_id = memory_id or str(uuid.uuid4())
    content_hash = _content_hash(content)
    ts = created_at or datetime.now(UTC)

    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    conn.execute(
        """
        CREATE (m:Memory {
            id: $id,
            content: $content,
            content_hash: $content_hash,
            created_at: $created_at,
            valid_from: $created_at,
            valid_to: NULL,
            accessed_at: $created_at,
            access_count: 0,
            memory_type: $memory_type,
            importance: $importance,
            confidence: $confidence,
            source_type: $source_type,
            agent_id: $agent_id,
            user_id: $user_id,
            session_id: $session_id,
            metadata: $metadata
        })
        """,
        {
            "id": mem_id,
            "content": content,
            "content_hash": content_hash,
            "created_at": ts,
            "memory_type": memory_type,
            "importance": importance,
            "confidence": confidence,
            "source_type": source_type,
            "agent_id": agent_id,
            "user_id": user_id,
            "session_id": session_id,
            "metadata": metadata,
        },
    )
    del conn
    del db
    return mem_id


def _count_memories(db_path: Path) -> int:
    """Return total Memory node count from a Kùzu database."""
    import kuzu

    db = kuzu.Database(str(db_path), read_only=True)
    conn = kuzu.Connection(db)
    result = conn.execute("MATCH (m:Memory) RETURN COUNT(m) AS cnt")
    rows = result.get_all()
    return int(rows[0][0])


def _fetch_all_hashes(db_path: Path) -> set[str]:
    """Return all content_hash values stored in the database."""
    import kuzu

    db = kuzu.Database(str(db_path), read_only=True)
    conn = kuzu.Connection(db)
    result = conn.execute("MATCH (m:Memory) RETURN m.content_hash AS h")
    rows = result.get_all()
    return {str(row[0]) for row in rows if row[0]}


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestExportShared:
    """Tests for export_shared()."""

    # ------------------------------------------------------------------
    # A1: empty database → no files, exported_count == 0
    # ------------------------------------------------------------------

    def test_export_empty_database(self, tmp_path: Path) -> None:
        """No memories in DB → export returns zero count, writes no files."""
        from kuzu_memory.mcp.sharing import export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        result = export_shared(db_path, tmp_path, min_age_days=0)

        assert result["exported_count"] == 0
        assert result["files_written"] == []
        # Shared directory is created even when there is nothing to export
        shared_dir = tmp_path / "kuzu-memory-shared"
        assert shared_dir.is_dir()

    # ------------------------------------------------------------------
    # A2: git_sync memories are excluded
    # ------------------------------------------------------------------

    def test_export_filters_git_sync(self, tmp_path: Path) -> None:
        """Memories with source_type='git_sync' must not appear in the export."""
        from kuzu_memory.mcp.sharing import export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        old_ts = datetime.now(UTC) - timedelta(days=3)
        _insert_memory(
            db_path, content="git sync memory", source_type="git_sync", created_at=old_ts
        )
        _insert_memory(
            db_path, content="user memory", source_type="ai-conversation", created_at=old_ts
        )

        result = export_shared(db_path, tmp_path, min_age_days=1)

        assert result["exported_count"] == 1  # only the user memory

        # Verify the exported content
        shared_dir = tmp_path / "kuzu-memory-shared"
        json_files = list(shared_dir.glob("memories-*.json"))
        assert len(json_files) == 1

        file_data = json.loads(json_files[0].read_text(encoding="utf-8"))
        contents = [m["content"] for m in file_data["memories"]]
        assert "user memory" in contents
        assert "git sync memory" not in contents

    # ------------------------------------------------------------------
    # A3: min_age_days filtering
    # ------------------------------------------------------------------

    def test_export_respects_min_age(self, tmp_path: Path) -> None:
        """Memories younger than min_age_days are excluded from the export."""
        from kuzu_memory.mcp.sharing import export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        old_ts = datetime.now(UTC) - timedelta(days=5)
        new_ts = datetime.now(UTC) - timedelta(hours=2)  # less than 1 day old

        _insert_memory(db_path, content="old memory", created_at=old_ts)
        _insert_memory(db_path, content="new memory", created_at=new_ts)

        result = export_shared(db_path, tmp_path, min_age_days=1)

        assert result["exported_count"] == 1

        shared_dir = tmp_path / "kuzu-memory-shared"
        json_files = list(shared_dir.glob("memories-*.json"))
        all_memories = []
        for jf in json_files:
            all_memories.extend(json.loads(jf.read_text())["memories"])

        contents = [m["content"] for m in all_memories]
        assert "old memory" in contents
        assert "new memory" not in contents

    # ------------------------------------------------------------------
    # A4: delta export — second run only gets new memories
    # ------------------------------------------------------------------

    def test_export_delta_only(self, tmp_path: Path) -> None:
        """
        Second export returns only memories whose created_at is newer than
        last_export_at AND older than the cutoff.

        The delta query uses ``created_at > last_export_at``, so the second
        batch memories must have a created_at that is *after* the moment the
        first export ran.  We simulate this by back-dating the export-state
        file so that the first export's ``last_export_at`` falls between the
        two batches.
        """
        from kuzu_memory.mcp.sharing import EXPORT_STATE_FILE, SHARED_DIR_NAME, export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        # "Older" batch: created 5 days ago
        old_ts = datetime.now(UTC) - timedelta(days=5)
        _insert_memory(db_path, content="first batch memory", created_at=old_ts)

        # "Newer" batch: created 2 days ago (old enough to pass the 1-day cutoff)
        newer_ts = datetime.now(UTC) - timedelta(days=2)
        _insert_memory(db_path, content="second batch memory", created_at=newer_ts)

        # Manually write an export-state that sets last_export_at to 4 days ago —
        # i.e. between the two batches — so the second export only sees the
        # newer memory.
        shared_dir = tmp_path / SHARED_DIR_NAME
        shared_dir.mkdir()
        boundary = datetime.now(UTC) - timedelta(days=4)
        state = {
            "last_export_at": boundary.isoformat(),
            "total_exported": 0,
            "export_history": [],
        }
        (shared_dir / EXPORT_STATE_FILE).write_text(json.dumps(state), encoding="utf-8")

        result = export_shared(db_path, tmp_path, min_age_days=1)

        # Only the memory created after the boundary (2 days ago) is picked up
        assert result["exported_count"] == 1

        all_memories: list[dict] = []
        for jf in sorted(shared_dir.glob("memories-*.json")):
            all_memories.extend(json.loads(jf.read_text())["memories"])

        contents = {m["content"] for m in all_memories}
        assert "second batch memory" in contents
        assert "first batch memory" not in contents

    # ------------------------------------------------------------------
    # A5: shared directory is created automatically
    # ------------------------------------------------------------------

    def test_export_creates_shared_directory(self, tmp_path: Path) -> None:
        """export_shared() creates kuzu-memory-shared/ when it does not exist."""
        from kuzu_memory.mcp.sharing import export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        shared_dir = tmp_path / "kuzu-memory-shared"
        assert not shared_dir.exists()

        export_shared(db_path, tmp_path, min_age_days=0)

        assert shared_dir.is_dir()

    # ------------------------------------------------------------------
    # A6: correct JSON structure in output files
    # ------------------------------------------------------------------

    def test_export_writes_json_files(self, tmp_path: Path) -> None:
        """Exported JSON files contain the expected top-level structure and fields."""
        from kuzu_memory.mcp.sharing import export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        ts = datetime.now(UTC) - timedelta(days=2)
        _insert_memory(
            db_path,
            content="structured test memory",
            created_at=ts,
            importance=0.8,
            confidence=0.9,
            memory_type="episodic",
            source_type="manual",
        )

        result = export_shared(db_path, tmp_path, min_age_days=1)
        assert result["exported_count"] == 1

        shared_dir = tmp_path / "kuzu-memory-shared"
        json_files = list(shared_dir.glob("memories-*.json"))
        assert len(json_files) == 1

        data = json.loads(json_files[0].read_text(encoding="utf-8"))

        # Top-level structure
        assert "export_version" in data
        assert "exported_at" in data
        assert "source_project" in data
        assert "memories" in data
        assert isinstance(data["memories"], list)
        assert len(data["memories"]) == 1

        mem = data["memories"][0]
        required_fields = {
            "id",
            "content",
            "content_hash",
            "created_at",
            "memory_type",
            "source_type",
            "importance",
            "confidence",
            "metadata",
            "agent_id",
        }
        assert required_fields.issubset(mem.keys())

        assert mem["content"] == "structured test memory"
        assert mem["memory_type"] == "episodic"
        assert abs(mem["importance"] - 0.8) < 1e-6
        assert abs(mem["confidence"] - 0.9) < 1e-6

    # ------------------------------------------------------------------
    # A7: append / merge to existing files
    # ------------------------------------------------------------------

    def test_export_appends_to_existing_files(self, tmp_path: Path) -> None:
        """
        When a memories-YYYY-MM-DD.json file already exists, a second export
        on the same date merges new memories without overwriting old ones.
        """
        from kuzu_memory.mcp.sharing import SHARED_DIR_NAME, _memories_filename, export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        # Pre-create a shared file with an existing memory entry
        shared_dir = tmp_path / SHARED_DIR_NAME
        shared_dir.mkdir()
        date_str = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%d")
        existing_hash = "pre_existing_hash_abc123"
        pre_existing = {
            "export_version": "1.0",
            "exported_at": "2026-01-01T00:00:00+00:00",
            "source_project": "other-project",
            "memories": [
                {
                    "id": str(uuid.uuid4()),
                    "content": "pre-existing memory",
                    "content_hash": existing_hash,
                    "created_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
                    "memory_type": "semantic",
                    "source_type": "manual",
                    "importance": 0.5,
                    "confidence": 1.0,
                    "metadata": {},
                    "agent_id": "default",
                }
            ],
        }
        file_path = shared_dir / _memories_filename(date_str)
        file_path.write_text(json.dumps(pre_existing), encoding="utf-8")

        # Insert a new memory at the same date
        ts = datetime.now(UTC) - timedelta(days=2)
        _insert_memory(db_path, content="new memory on same day", created_at=ts)

        result = export_shared(db_path, tmp_path, min_age_days=1)
        assert result["exported_count"] == 1

        data = json.loads(file_path.read_text(encoding="utf-8"))
        assert len(data["memories"]) == 2
        contents = {m["content"] for m in data["memories"]}
        assert "pre-existing memory" in contents
        assert "new memory on same day" in contents

    # ------------------------------------------------------------------
    # A8: export state tracking
    # ------------------------------------------------------------------

    def test_export_state_tracking(self, tmp_path: Path) -> None:
        """export_shared() writes .export-state.json and updates it on each call."""
        from kuzu_memory.mcp.sharing import EXPORT_STATE_FILE, SHARED_DIR_NAME, export_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        ts = datetime.now(UTC) - timedelta(days=3)
        _insert_memory(db_path, content="state tracking memory", created_at=ts)

        export_shared(db_path, tmp_path, min_age_days=1)

        shared_dir = tmp_path / SHARED_DIR_NAME
        state_file = shared_dir / EXPORT_STATE_FILE
        assert state_file.exists()

        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["last_export_at"] is not None
        assert state["total_exported"] == 1
        assert isinstance(state["export_history"], list)
        assert len(state["export_history"]) == 1
        assert state["export_history"][0]["count"] == 1

        # Second export (no new data) should still update last_export_at
        before_second = state["last_export_at"]
        export_shared(db_path, tmp_path, min_age_days=1)

        state2 = json.loads(state_file.read_text(encoding="utf-8"))
        # total_exported unchanged (no new data)
        assert state2["total_exported"] == 1
        # timestamp updated
        assert state2["last_export_at"] >= before_second


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


class TestImportShared:
    """Tests for import_shared()."""

    def _write_memories_file(
        self,
        shared_dir: Path,
        date_str: str,
        memories: list[dict],
    ) -> Path:
        """Helper: write a memories-YYYY-MM-DD.json file into shared_dir."""
        from kuzu_memory.mcp.sharing import _memories_filename

        shared_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "export_version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "source_project": "remote-project",
            "memories": memories,
        }
        file_path = shared_dir / _memories_filename(date_str)
        file_path.write_text(json.dumps(data), encoding="utf-8")
        return file_path

    def _make_memory_record(self, content: str, source_type: str = "ai-conversation") -> dict:
        """Helper: build a minimal memory dict as produced by export_shared."""
        ts = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        return {
            "id": str(uuid.uuid4()),
            "content": content,
            "content_hash": _content_hash(content),
            "created_at": ts,
            "memory_type": "semantic",
            "source_type": source_type,
            "importance": 0.5,
            "confidence": 1.0,
            "metadata": {},
            "agent_id": "default",
            "user_id": None,
            "session_id": None,
        }

    # ------------------------------------------------------------------
    # B1: memories from JSON are inserted
    # ------------------------------------------------------------------

    def test_import_new_memories(self, tmp_path: Path) -> None:
        """import_shared() inserts all new memory records into the local DB."""
        from kuzu_memory.mcp.sharing import SHARED_DIR_NAME, import_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        shared_dir = tmp_path / SHARED_DIR_NAME
        records = [
            self._make_memory_record("imported memory alpha"),
            self._make_memory_record("imported memory beta"),
        ]
        self._write_memories_file(shared_dir, "2026-01-10", records)

        result = import_shared(db_path, tmp_path)

        assert result["imported_count"] == 2
        assert result["skipped_duplicates"] == 0
        assert _count_memories(db_path) == 2

    # ------------------------------------------------------------------
    # B2: deduplication by content_hash
    # ------------------------------------------------------------------

    def test_import_dedup_by_hash(self, tmp_path: Path) -> None:
        """Memories whose content_hash already exists in the local DB are skipped."""
        from kuzu_memory.mcp.sharing import SHARED_DIR_NAME, import_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        existing_content = "already in local db"
        _insert_memory(db_path, content=existing_content)

        shared_dir = tmp_path / SHARED_DIR_NAME
        records = [
            self._make_memory_record(existing_content),  # duplicate
            self._make_memory_record("brand new memory"),  # new
        ]
        self._write_memories_file(shared_dir, "2026-01-11", records)

        result = import_shared(db_path, tmp_path)

        assert result["imported_count"] == 1
        assert result["skipped_duplicates"] == 1
        # DB had 1 existing + 1 new imported
        assert _count_memories(db_path) == 2

    # ------------------------------------------------------------------
    # B3: dry_run does not write anything
    # ------------------------------------------------------------------

    def test_import_dry_run(self, tmp_path: Path) -> None:
        """With dry_run=True, no records are inserted into the DB."""
        from kuzu_memory.mcp.sharing import SHARED_DIR_NAME, import_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        shared_dir = tmp_path / SHARED_DIR_NAME
        records = [
            self._make_memory_record("dry run memory one"),
            self._make_memory_record("dry run memory two"),
        ]
        self._write_memories_file(shared_dir, "2026-02-01", records)

        result = import_shared(db_path, tmp_path, dry_run=True)

        assert result["dry_run"] is True
        assert result["imported_count"] == 2  # count of what *would* be imported
        assert _count_memories(db_path) == 0  # nothing actually written

    # ------------------------------------------------------------------
    # B4: RuntimeError when shared dir is missing
    # ------------------------------------------------------------------

    def test_import_no_shared_dir(self, tmp_path: Path) -> None:
        """import_shared() raises RuntimeError when kuzu-memory-shared/ is absent."""
        from kuzu_memory.mcp.sharing import import_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        with pytest.raises(RuntimeError, match="Shared directory not found"):
            import_shared(db_path, tmp_path)

    # ------------------------------------------------------------------
    # B5: empty JSON files handled gracefully
    # ------------------------------------------------------------------

    def test_import_empty_files(self, tmp_path: Path) -> None:
        """An empty or malformed memories JSON file is skipped without raising."""
        from kuzu_memory.mcp.sharing import SHARED_DIR_NAME, import_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        shared_dir = tmp_path / SHARED_DIR_NAME
        shared_dir.mkdir()

        # Empty memories list
        (shared_dir / "memories-2026-01-01.json").write_text(
            json.dumps({"export_version": "1.0", "memories": []}), encoding="utf-8"
        )
        # Malformed JSON (should be skipped without crashing)
        (shared_dir / "memories-2026-01-02.json").write_text("NOT VALID JSON", encoding="utf-8")

        result = import_shared(db_path, tmp_path)

        assert result["imported_count"] == 0
        assert _count_memories(db_path) == 0

    # ------------------------------------------------------------------
    # B6: import state tracking
    # ------------------------------------------------------------------

    def test_import_state_tracking(self, tmp_path: Path) -> None:
        """import_shared() writes .import-state.json and updates it correctly."""
        from kuzu_memory.mcp.sharing import IMPORT_STATE_FILE, SHARED_DIR_NAME, import_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        shared_dir = tmp_path / SHARED_DIR_NAME
        records = [self._make_memory_record("state tracked memory")]
        self._write_memories_file(shared_dir, "2026-01-15", records)

        import_shared(db_path, tmp_path)

        state_file = shared_dir / IMPORT_STATE_FILE
        assert state_file.exists()

        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["last_import_at"] is not None
        assert state["total_imported"] == 1
        assert isinstance(state["processed_files"], list)
        assert len(state["processed_files"]) == 1
        assert "memories-2026-01-15.json" in state["processed_files"]
        assert isinstance(state["imported_hashes"], list)
        assert len(state["imported_hashes"]) == 1

    # ------------------------------------------------------------------
    # B7: second import skips already-imported hashes (via state)
    # ------------------------------------------------------------------

    def test_import_dedup_via_state(self, tmp_path: Path) -> None:
        """
        A second import run skips hashes that were imported in a previous run
        and are recorded in .import-state.json.
        """
        from kuzu_memory.mcp.sharing import SHARED_DIR_NAME, import_shared

        db_path = tmp_path / "memories.db"
        _init_db(db_path)

        shared_dir = tmp_path / SHARED_DIR_NAME
        records = [self._make_memory_record("idempotent import memory")]
        self._write_memories_file(shared_dir, "2026-01-20", records)

        # First import
        result1 = import_shared(db_path, tmp_path)
        assert result1["imported_count"] == 1

        # Second import of the same file
        result2 = import_shared(db_path, tmp_path)
        assert result2["imported_count"] == 0
        assert result2["skipped_duplicates"] == 1
        # DB still has exactly 1 memory
        assert _count_memories(db_path) == 1


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


class TestMigrateDbLocation:
    """Tests for migrate_db_location() in project_setup.py."""

    # ------------------------------------------------------------------
    # C1: full move when only old dir exists
    # ------------------------------------------------------------------

    def test_migrate_full_move(self, tmp_path: Path) -> None:
        """
        When kuzu-memories/ exists and .kuzu-memory/ does not, migrate_db_location
        renames the directory and returns True.
        """
        from kuzu_memory.utils.project_setup import migrate_db_location

        old_path = tmp_path / "kuzu-memories"
        new_path = tmp_path / ".kuzu-memory"

        old_path.mkdir()
        sentinel = old_path / "memories.db"
        sentinel.write_text("mock db", encoding="utf-8")

        result = migrate_db_location(tmp_path)

        assert result is True
        assert not old_path.exists()
        assert new_path.is_dir()
        assert (new_path / "memories.db").read_text() == "mock db"

    # ------------------------------------------------------------------
    # C2: partial merge when both dirs exist
    # ------------------------------------------------------------------

    def test_migrate_partial_merge(self, tmp_path: Path) -> None:
        """
        When both dirs exist, auxiliary files missing from .kuzu-memory/ are
        copied from kuzu-memories/ and True is returned.
        """
        from kuzu_memory.utils.project_setup import migrate_db_location

        old_path = tmp_path / "kuzu-memories"
        new_path = tmp_path / ".kuzu-memory"

        old_path.mkdir()
        new_path.mkdir()

        # Auxiliary file present in old but missing from new
        (old_path / "README.md").write_text("old readme", encoding="utf-8")
        (old_path / "project_info.md").write_text("old project info", encoding="utf-8")

        result = migrate_db_location(tmp_path)

        assert result is True
        assert (new_path / "README.md").read_text() == "old readme"
        assert (new_path / "project_info.md").read_text() == "old project info"

    # ------------------------------------------------------------------
    # C3: no overwrite of existing files in new location
    # ------------------------------------------------------------------

    def test_migrate_no_overwrite(self, tmp_path: Path) -> None:
        """
        Files already present in .kuzu-memory/ are NOT overwritten even when
        the same filename exists in kuzu-memories/.
        """
        from kuzu_memory.utils.project_setup import migrate_db_location

        old_path = tmp_path / "kuzu-memories"
        new_path = tmp_path / ".kuzu-memory"

        old_path.mkdir()
        new_path.mkdir()

        # Both dirs have README.md — new location content must survive
        (old_path / "README.md").write_text("old content", encoding="utf-8")
        (new_path / "README.md").write_text("new content should stay", encoding="utf-8")

        migrate_db_location(tmp_path)

        # New file must not be overwritten
        assert (new_path / "README.md").read_text() == "new content should stay"

    # ------------------------------------------------------------------
    # C4: neither directory exists → False
    # ------------------------------------------------------------------

    def test_migrate_neither_exists(self, tmp_path: Path) -> None:
        """
        When neither kuzu-memories/ nor .kuzu-memory/ exists, migrate_db_location
        returns False without raising.
        """
        from kuzu_memory.utils.project_setup import migrate_db_location

        result = migrate_db_location(tmp_path)

        assert result is False

    # ------------------------------------------------------------------
    # C5: only new dir exists (already migrated) → False
    # ------------------------------------------------------------------

    def test_migrate_only_new_exists(self, tmp_path: Path) -> None:
        """
        When only .kuzu-memory/ exists (migration already done), returns False.
        """
        from kuzu_memory.utils.project_setup import migrate_db_location

        new_path = tmp_path / ".kuzu-memory"
        new_path.mkdir()

        result = migrate_db_location(tmp_path)

        assert result is False
        assert new_path.is_dir()

    # ------------------------------------------------------------------
    # C6: partial merge with no copyable files → False
    # ------------------------------------------------------------------

    def test_migrate_partial_merge_nothing_to_copy(self, tmp_path: Path) -> None:
        """
        When both dirs exist but old has no auxiliary files to contribute, returns False.
        """
        from kuzu_memory.utils.project_setup import migrate_db_location

        old_path = tmp_path / "kuzu-memories"
        new_path = tmp_path / ".kuzu-memory"

        old_path.mkdir()
        new_path.mkdir()
        # old_path has no auxiliary files at all

        result = migrate_db_location(tmp_path)

        assert result is False

    # ------------------------------------------------------------------
    # C7: all auxiliary files already in new → False
    # ------------------------------------------------------------------

    def test_migrate_all_aux_files_already_present(self, tmp_path: Path) -> None:
        """
        When both dirs exist and new already has all auxiliary files, returns False.
        """
        from kuzu_memory.utils.project_setup import migrate_db_location

        old_path = tmp_path / "kuzu-memories"
        new_path = tmp_path / ".kuzu-memory"

        old_path.mkdir()
        new_path.mkdir()

        auxiliary_files = ["README.md", "project_info.md", "config.yaml"]
        for filename in auxiliary_files:
            (old_path / filename).write_text(f"old {filename}", encoding="utf-8")
            (new_path / filename).write_text(f"new {filename}", encoding="utf-8")

        result = migrate_db_location(tmp_path)

        assert result is False
        # Verify new content untouched
        for filename in auxiliary_files:
            assert (new_path / filename).read_text() == f"new {filename}"
