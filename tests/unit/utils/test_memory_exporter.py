"""Unit tests for the memory export utility.

Covers:
- Export with memories returns correct count and valid JSON
- Export with no memories returns empty list (not error)
- include_archived=True includes archived memories
- Output file is created in the correct directory with timestamp in filename
- Datetime fields are serialised to ISO strings (not datetime objects)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.storage.kuzu_adapter import KuzuAdapter
from kuzu_memory.utils.memory_exporter import export_memories_to_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(db_path: Path) -> KuzuAdapter:
    """Create and initialise a KuzuAdapter backed by a fresh database."""
    config = KuzuMemoryConfig.default()
    adapter = KuzuAdapter(db_path, config)
    adapter.initialize()
    return adapter


def _insert_memory(adapter: KuzuAdapter, content: str) -> str:
    """Insert a single Memory node; return its id."""
    import hashlib

    memory_id = str(uuid.uuid4())
    content_hash = hashlib.sha256(content.lower().encode()).hexdigest()
    now = datetime.now(UTC)

    adapter.execute_query(
        """
        CREATE (m:Memory {
            id: $id,
            content: $content,
            content_hash: $content_hash,
            created_at: $created_at,
            accessed_at: $accessed_at,
            access_count: 0,
            memory_type: 'episodic',
            knowledge_type: 'note',
            importance: 0.5,
            confidence: 1.0,
            source_type: 'test',
            source_speaker: 'user',
            project_tag: '',
            agent_id: 'test',
            user_id: NULL,
            session_id: NULL,
            metadata: '{}',
            valid_from: $created_at,
            valid_to: NULL
        })
        """,
        {
            "id": memory_id,
            "content": content,
            "content_hash": content_hash,
            "created_at": now,
            "accessed_at": now,
        },
    )
    return memory_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExportMemoriesToJson:
    """Tests for export_memories_to_json()."""

    def test_export_with_memories_returns_correct_count(self, tmp_path: Path) -> None:
        """Export writes the correct number of memories to the JSON file."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        _insert_memory(adapter, "First memory content")
        _insert_memory(adapter, "Second memory content")
        _insert_memory(adapter, "Third memory content")

        result = export_memories_to_json(adapter, backup_dir)

        assert result["memories"] == 3
        assert result["archived"] == 0

    def test_export_creates_valid_json_file(self, tmp_path: Path) -> None:
        """The output file is valid JSON with expected top-level keys."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        _insert_memory(adapter, "Some content to export")

        result = export_memories_to_json(adapter, backup_dir)

        output_file = Path(result["path"])
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert data["schema_version"] == "1.0"
        assert "exported_at" in data
        assert "memory_count" in data
        assert "memories" in data
        assert isinstance(data["memories"], list)
        assert data["memory_count"] == len(data["memories"])

    def test_export_with_no_memories_returns_empty_list(self, tmp_path: Path) -> None:
        """Export does not raise when the database has no Memory nodes."""
        db_path = tmp_path / "empty.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        result = export_memories_to_json(adapter, backup_dir)

        assert result["memories"] == 0
        assert result["archived"] == 0

        output_file = Path(result["path"])
        data = json.loads(output_file.read_text())
        assert data["memories"] == []
        assert data["memory_count"] == 0

    def test_output_file_created_in_correct_directory(self, tmp_path: Path) -> None:
        """Backup file appears inside the requested backup directory."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "my-backups" / "nested"

        result = export_memories_to_json(adapter, backup_dir)

        output_file = Path(result["path"])
        assert output_file.parent == backup_dir
        assert backup_dir.exists()

    def test_output_filename_contains_timestamp(self, tmp_path: Path) -> None:
        """Backup filename contains a timestamp pattern."""
        import re

        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        result = export_memories_to_json(adapter, backup_dir)

        filename = Path(result["path"]).name
        # Expect: memories_backup_YYYYMMDD_HHMMSS.json
        assert filename.startswith("memories_backup_")
        assert filename.endswith(".json")
        assert re.search(r"\d{8}_\d{6}", filename), f"Timestamp not found in filename: {filename}"

    def test_datetime_fields_serialised_as_iso_strings(self, tmp_path: Path) -> None:
        """Datetime values in the exported JSON are ISO 8601 strings, not objects."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        _insert_memory(adapter, "Memory with timestamps")

        result = export_memories_to_json(adapter, backup_dir)

        output_file = Path(result["path"])
        data = json.loads(output_file.read_text())

        assert len(data["memories"]) == 1
        mem = data["memories"][0]

        # These fields may be None or an ISO string — never a datetime object
        # (which would cause json.loads to fail anyway; this confirms round-trip)
        for field in ("created_at", "accessed_at"):
            value = mem.get(field)
            if value is not None:
                # Should be parseable as a datetime
                assert isinstance(
                    value, str
                ), f"Field '{field}' should be a string, got {type(value)}"
                # Verify it's a valid ISO string
                datetime.fromisoformat(value.replace("Z", "+00:00"))

    def test_backup_directory_created_if_absent(self, tmp_path: Path) -> None:
        """backup_path directory is created when it does not exist."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "new_dir" / "sub_dir"

        assert not backup_dir.exists()
        export_memories_to_json(adapter, backup_dir)
        assert backup_dir.exists()

    def test_include_archived_true_includes_archived_memories(self, tmp_path: Path) -> None:
        """When include_archived=True, archived memories are included in the export."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        _insert_memory(adapter, "Active memory")

        # Insert an ArchivedMemory node if the table exists
        archived_id = str(uuid.uuid4())
        try:
            adapter.execute_query(
                """
                CREATE (m:ArchivedMemory {
                    id: $id,
                    content: $content,
                    archived_at: $archived_at
                })
                """,
                {
                    "id": archived_id,
                    "content": "Archived content",
                    "archived_at": datetime.now(UTC),
                },
            )
            has_archived_table = True
        except Exception:
            has_archived_table = False

        result = export_memories_to_json(adapter, backup_dir, include_archived=True)

        assert result["memories"] == 1
        if has_archived_table:
            assert result["archived"] == 1
        else:
            # If ArchivedMemory table doesn't exist, exported archived count stays 0
            assert result["archived"] == 0

    def test_include_archived_false_skips_archived(self, tmp_path: Path) -> None:
        """When include_archived=False (default), archived memories are not queried."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        _insert_memory(adapter, "Active memory")

        result = export_memories_to_json(adapter, backup_dir, include_archived=False)

        assert result["archived"] == 0
        output_file = Path(result["path"])
        data = json.loads(output_file.read_text())
        assert data["archived"] == []
        assert data["archived_count"] == 0

    def test_exported_memory_content_matches_inserted(self, tmp_path: Path) -> None:
        """The content field in the exported file matches what was inserted."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        expected_content = "Specific content for export verification"
        _insert_memory(adapter, expected_content)

        result = export_memories_to_json(adapter, backup_dir)

        output_file = Path(result["path"])
        data = json.loads(output_file.read_text())

        contents = [m["content"] for m in data["memories"]]
        assert expected_content in contents

    def test_result_path_key_matches_actual_file(self, tmp_path: Path) -> None:
        """The 'path' value in the return dict points to the file that was written."""
        db_path = tmp_path / "test.kuzu"
        adapter = _make_adapter(db_path)
        backup_dir = tmp_path / "backups"

        result = export_memories_to_json(adapter, backup_dir)

        assert Path(result["path"]).exists()
        assert Path(result["path"]).is_file()
