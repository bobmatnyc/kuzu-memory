"""
Tests for auto-migration of old single-file .kuzu-memory format.

Covers the _migrate_single_file_db() utility and the callers that invoke it
(get_project_memories_dir and MCP _get_db_path).
"""

import time
from pathlib import Path

from kuzu_memory.utils.project_setup import (
    _migrate_single_file_db,
    get_project_db_path,
    get_project_memories_dir,
)

# ---------------------------------------------------------------------------
# _migrate_single_file_db() unit tests
# ---------------------------------------------------------------------------


class TestMigrateSingleFileDb:
    def test_migrates_file_to_directory(self, tmp_path: Path) -> None:
        """When .kuzu-memory is a regular file it is backed up and replaced by a dir."""
        kuzu_memory = tmp_path / ".kuzu-memory"
        kuzu_memory.write_bytes(b"old binary content")

        result = _migrate_single_file_db(kuzu_memory)

        assert result is True
        assert kuzu_memory.is_dir(), ".kuzu-memory should now be a directory"

    def test_backup_file_contains_original_content(self, tmp_path: Path) -> None:
        """The backup file must preserve the original content."""
        original_content = b"original database bytes"
        kuzu_memory = tmp_path / ".kuzu-memory"
        kuzu_memory.write_bytes(original_content)

        _migrate_single_file_db(kuzu_memory)

        backup = tmp_path / ".kuzu-memory.bak"
        assert backup.exists(), "Backup file should exist at .kuzu-memory.bak"
        assert backup.read_bytes() == original_content

    def test_backup_name_is_timestamped_when_bak_already_exists(self, tmp_path: Path) -> None:
        """When .kuzu-memory.bak already exists a timestamped backup is created."""
        kuzu_memory = tmp_path / ".kuzu-memory"
        kuzu_memory.write_bytes(b"data")

        # Pre-create the default backup path
        (tmp_path / ".kuzu-memory.bak").write_bytes(b"existing backup")

        before = int(time.time())
        _migrate_single_file_db(kuzu_memory)
        after = int(time.time())

        # Find the timestamped backup
        timestamped = [
            p
            for p in tmp_path.iterdir()
            if p.name.startswith(".kuzu-memory.bak.") and p.name != ".kuzu-memory.bak"
        ]
        assert len(timestamped) == 1, "Expected exactly one timestamped backup"
        ts = int(timestamped[0].name.split(".")[-1])
        assert before <= ts <= after + 1

    def test_no_op_when_path_is_already_a_directory(self, tmp_path: Path) -> None:
        """Returns False and does nothing when .kuzu-memory is already a directory."""
        kuzu_memory = tmp_path / ".kuzu-memory"
        kuzu_memory.mkdir()

        result = _migrate_single_file_db(kuzu_memory)

        assert result is False
        assert kuzu_memory.is_dir()

    def test_no_op_when_path_does_not_exist(self, tmp_path: Path) -> None:
        """Returns False and does nothing when .kuzu-memory does not exist yet."""
        kuzu_memory = tmp_path / ".kuzu-memory"

        result = _migrate_single_file_db(kuzu_memory)

        assert result is False
        assert not kuzu_memory.exists()


# ---------------------------------------------------------------------------
# get_project_memories_dir() integration tests
# ---------------------------------------------------------------------------


class TestGetProjectMemoriesDirMigration:
    def test_returns_directory_path_after_migrating_file(self, tmp_path: Path) -> None:
        """get_project_memories_dir auto-migrates and returns a directory path."""
        # Simulate old single-file format
        kuzu_memory = tmp_path / ".kuzu-memory"
        kuzu_memory.write_bytes(b"old data")

        result = get_project_memories_dir(project_root=tmp_path)

        assert result == kuzu_memory
        assert result.is_dir(), "Path must be a directory after migration"

    def test_backup_exists_after_migration(self, tmp_path: Path) -> None:
        """The old file is backed up when get_project_memories_dir is called."""
        (tmp_path / ".kuzu-memory").write_bytes(b"old data")

        get_project_memories_dir(project_root=tmp_path)

        assert (tmp_path / ".kuzu-memory.bak").exists()


# ---------------------------------------------------------------------------
# get_project_db_path() — sanity check after migration
# ---------------------------------------------------------------------------


class TestGetProjectDbPathAfterMigration:
    def test_db_path_is_inside_directory_after_migration(self, tmp_path: Path) -> None:
        """After migration get_project_db_path returns a path inside the new dir."""
        (tmp_path / ".kuzu-memory").write_bytes(b"old data")

        db_path = get_project_db_path(project_root=tmp_path)

        assert db_path.parent.is_dir()
        assert db_path.name == "memories.db"
        assert db_path.parent == tmp_path / ".kuzu-memory"
