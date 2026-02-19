"""
Unit tests for memory merge command.

Tests the memory merge functionality including:
- Empty source database
- No duplicates (all new)
- All duplicates (various strategies)
- Partial duplicates
- Dry-run mode
- Invalid source path
- Statistics reporting
"""

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import kuzu
import pytest
from click.testing import CliRunner

from kuzu_memory.cli.commands import cli
from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.storage.kuzu_adapter import KuzuAdapter


def create_test_memory(
    content: str,
    memory_type: str = "episodic",
    importance: float = 0.5,
    source_type: str = "test",
) -> dict:
    """Helper to create a test memory dictionary."""
    import hashlib

    content_hash = hashlib.sha256(content.lower().encode()).hexdigest()
    return {
        "id": str(uuid.uuid4()),
        "content": content,
        "content_hash": content_hash,
        "created_at": datetime.now(UTC).isoformat(),
        "memory_type": memory_type,
        "importance": importance,
        "confidence": 1.0,
        "source_type": source_type,
        "agent_id": "test",
        "user_id": None,
        "session_id": None,
        "metadata": json.dumps({}),
        "accessed_at": None,
        "access_count": 0,
    }


def insert_memory_to_db(db_path: Path, memory_data: dict) -> None:
    """Helper to insert a memory into a database."""
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    insert_query = """
        CREATE (m:Memory {
            id: $id,
            content: $content,
            content_hash: $content_hash,
            created_at: TIMESTAMP($created_at),
            memory_type: $memory_type,
            importance: $importance,
            confidence: $confidence,
            source_type: $source_type,
            agent_id: $agent_id,
            user_id: $user_id,
            session_id: $session_id,
            metadata: $metadata,
            accessed_at: $accessed_at,
            access_count: $access_count,
            valid_from: TIMESTAMP($created_at),
            valid_to: NULL
        })
    """

    conn.execute(insert_query, memory_data)


def get_memory_count(db_path: Path) -> int:
    """Helper to get memory count from database."""
    db = kuzu.Database(str(db_path), read_only=True)
    conn = kuzu.Connection(db)

    result = conn.execute("MATCH (m:Memory) RETURN COUNT(m) AS count")
    rows = result.get_all()
    # get_all() returns list of lists: [[count_value]]
    return int(rows[0][0])


def get_all_memories(db_path: Path) -> list:
    """Helper to get all memories from database."""
    db = kuzu.Database(str(db_path), read_only=True)
    conn = kuzu.Connection(db)

    result = conn.execute(
        """
        MATCH (m:Memory)
        RETURN m.id AS id, m.content AS content, m.content_hash AS content_hash
        ORDER BY m.created_at ASC
    """
    )
    # get_all() returns list of lists: [[id, content, hash], ...]
    # Convert to list of dicts using column names
    rows = result.get_all()
    column_names = result.get_column_names()
    return [dict(zip(column_names, row, strict=True)) for row in rows]


def initialize_database(db_path: Path) -> None:
    """Initialize a Kùzu database with schema."""
    config = KuzuMemoryConfig.default()
    adapter = KuzuAdapter(db_path, config)
    adapter.initialize()


@pytest.fixture
def source_db(tmp_path: Path) -> Path:
    """Create a source database for testing."""
    source_path = tmp_path / "source.kuzu"
    initialize_database(source_path)
    return source_path


@pytest.fixture
def target_db(tmp_path: Path) -> Path:
    """Create a target database for testing."""
    target_path = tmp_path / "target.kuzu"
    initialize_database(target_path)
    return target_path


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


def test_merge_empty_source(cli_runner, source_db, target_db):
    """Test merging from an empty source database."""
    # Target has some memories
    insert_memory_to_db(target_db, create_test_memory("Existing memory 1"))

    initial_count = get_memory_count(target_db)

    # Run merge command (dry-run)
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "empty" in result.output.lower()

    # Verify no changes
    assert get_memory_count(target_db) == initial_count


def test_merge_no_duplicates_dry_run(cli_runner, source_db, target_db):
    """Test merging with no duplicates (all new) in dry-run mode."""
    # Source has new memories
    insert_memory_to_db(source_db, create_test_memory("Source memory 1"))
    insert_memory_to_db(source_db, create_test_memory("Source memory 2"))

    # Target has different memories
    insert_memory_to_db(target_db, create_test_memory("Target memory 1"))

    initial_count = get_memory_count(target_db)

    # Run merge command (dry-run)
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "2" in result.output  # 2 new memories
    assert "dry-run" in result.output.lower() or "preview" in result.output.lower()

    # Verify no changes in dry-run
    assert get_memory_count(target_db) == initial_count


def test_merge_no_duplicates_execute(cli_runner, source_db, target_db):
    """Test merging with no duplicates (all new) in execute mode."""
    # Source has new memories
    insert_memory_to_db(source_db, create_test_memory("Source memory 1"))
    insert_memory_to_db(source_db, create_test_memory("Source memory 2"))
    insert_memory_to_db(source_db, create_test_memory("Source memory 3"))

    # Target has different memories
    insert_memory_to_db(target_db, create_test_memory("Target memory 1"))

    initial_count = get_memory_count(target_db)

    # Run merge command (execute with --yes)
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0
    assert "imported" in result.output.lower() or "complete" in result.output.lower()

    # Verify changes
    final_count = get_memory_count(target_db)
    assert final_count == initial_count + 3


def test_merge_all_duplicates_skip(cli_runner, source_db, target_db):
    """Test merging with all duplicates using skip strategy."""
    # Create identical memories in both databases
    mem1 = create_test_memory("Duplicate memory 1")
    mem2 = create_test_memory("Duplicate memory 2")

    insert_memory_to_db(source_db, mem1)
    insert_memory_to_db(source_db, mem2)
    insert_memory_to_db(target_db, mem1)
    insert_memory_to_db(target_db, mem2)

    initial_count = get_memory_count(target_db)

    # Run merge with skip strategy
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--strategy",
            "skip",
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0
    assert "2" in result.output  # 2 duplicates

    # Verify no new memories added
    assert get_memory_count(target_db) == initial_count


def test_merge_all_duplicates_update(cli_runner, source_db, target_db):
    """Test merging with all duplicates using update strategy."""
    # Create identical memories with different importance
    mem1 = create_test_memory("Duplicate memory 1", importance=0.5)
    mem2 = create_test_memory("Duplicate memory 2", importance=0.6)

    insert_memory_to_db(source_db, mem1)
    insert_memory_to_db(source_db, mem2)

    # Target has same content_hash but different importance
    target_mem1 = mem1.copy()
    target_mem1["importance"] = 0.3
    target_mem2 = mem2.copy()
    target_mem2["importance"] = 0.4

    insert_memory_to_db(target_db, target_mem1)
    insert_memory_to_db(target_db, target_mem2)

    initial_count = get_memory_count(target_db)

    # Run merge with update strategy
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--strategy",
            "update",
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0
    assert "updated" in result.output.lower()

    # Verify no new memories added (count stays same)
    assert get_memory_count(target_db) == initial_count


def test_merge_partial_duplicates(cli_runner, source_db, target_db):
    """Test merging with partial duplicates (mix of new and existing)."""
    # Source has 3 memories: 2 duplicates, 1 new
    dup1 = create_test_memory("Duplicate memory 1")
    dup2 = create_test_memory("Duplicate memory 2")
    new1 = create_test_memory("New memory 1")

    insert_memory_to_db(source_db, dup1)
    insert_memory_to_db(source_db, dup2)
    insert_memory_to_db(source_db, new1)

    # Target has the 2 duplicates
    insert_memory_to_db(target_db, dup1)
    insert_memory_to_db(target_db, dup2)

    initial_count = get_memory_count(target_db)

    # Run merge
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0

    # Verify 1 new memory added
    final_count = get_memory_count(target_db)
    assert final_count == initial_count + 1


def test_merge_strategy_merge_consolidated_into(cli_runner, source_db, target_db):
    """Test merge strategy creates CONSOLIDATED_INTO relationships."""
    # Create duplicate
    dup = create_test_memory("Duplicate memory")

    insert_memory_to_db(source_db, dup)
    insert_memory_to_db(target_db, dup)

    initial_count = get_memory_count(target_db)

    # Run merge with merge strategy
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--strategy",
            "merge",
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0
    assert "consolidated" in result.output.lower() or "merged" in result.output.lower()

    # Verify new memory with relationship created
    final_count = get_memory_count(target_db)
    assert final_count == initial_count + 1  # Original + merged node


def test_merge_custom_threshold(cli_runner, source_db, target_db):
    """Test merge with custom similarity threshold."""
    # Create similar but not identical memories
    mem1 = create_test_memory("The quick brown fox jumps over the lazy dog")
    mem2_similar = create_test_memory("Quick brown fox jumping over lazy dog")

    insert_memory_to_db(source_db, mem2_similar)
    insert_memory_to_db(target_db, mem1)

    # Run with low threshold (should detect as duplicate)
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--threshold",
            "0.70",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    # With 0.70 threshold, should detect similarity


def test_merge_invalid_source_path(cli_runner, target_db):
    """Test merge with invalid source path."""
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            "/nonexistent/path.kuzu",
            "--db-path",
            str(target_db),
        ],
    )

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "exist" in result.output.lower()


def test_merge_statistics_reporting(cli_runner, source_db, target_db):
    """Test that merge reports correct statistics."""
    # Setup: 2 new, 1 duplicate
    new1 = create_test_memory("New memory 1")
    new2 = create_test_memory("New memory 2")
    dup = create_test_memory("Duplicate memory")

    insert_memory_to_db(source_db, new1)
    insert_memory_to_db(source_db, new2)
    insert_memory_to_db(source_db, dup)
    insert_memory_to_db(target_db, dup)

    # Run merge
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0

    # Verify statistics in output
    assert "3" in result.output  # 3 source memories
    assert "2" in result.output  # 2 new memories
    assert "1" in result.output  # 1 duplicate


def test_merge_preserves_metadata(cli_runner, source_db, target_db):
    """Test that merge preserves original metadata and adds merge provenance."""
    # Create memory with metadata
    mem = create_test_memory("Memory with metadata")
    mem["metadata"] = json.dumps({"custom_key": "custom_value", "tags": ["important"]})

    insert_memory_to_db(source_db, mem)

    # Run merge
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0

    # Verify metadata in target
    all_memories = get_all_memories(target_db)
    assert len(all_memories) == 1

    # Check that merged memory has both original metadata and merge provenance
    db = kuzu.Database(str(target_db), read_only=True)
    conn = kuzu.Connection(db)
    result_query = conn.execute(
        """
        MATCH (m:Memory)
        RETURN m.metadata AS metadata
    """
    )
    rows = result_query.get_all()
    # get_all() returns list of lists: [[metadata_value]]
    metadata_str = str(rows[0][0])
    metadata = json.loads(metadata_str)

    # Original metadata preserved
    assert metadata.get("custom_key") == "custom_value"
    assert "important" in metadata.get("tags", [])

    # Merge provenance added
    assert "merged_from" in metadata
    assert "merged_at" in metadata
    assert "original_id" in metadata


def test_merge_backup_creation(cli_runner, source_db, target_db):
    """Test that merge creates backup when requested."""
    # Add memory to target
    insert_memory_to_db(target_db, create_test_memory("Target memory"))

    # Add memory to source
    insert_memory_to_db(source_db, create_test_memory("Source memory"))

    # Run merge with backup
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--execute",
            "--yes",
            "--backup",
        ],
    )

    assert result.exit_code == 0
    assert "backup" in result.output.lower()

    # Verify backup was created
    backup_dirs = list(target_db.parent.glob("backup_*"))
    assert len(backup_dirs) > 0


def test_merge_no_backup_flag(cli_runner, source_db, target_db):
    """Test that --no-backup skips backup creation."""
    # Add memories
    insert_memory_to_db(source_db, create_test_memory("Source memory"))
    insert_memory_to_db(target_db, create_test_memory("Target memory"))

    # Run merge without backup
    result = cli_runner.invoke(
        cli,
        [
            "memory",
            "merge",
            str(source_db),
            "--db-path",
            str(target_db),
            "--execute",
            "--yes",
            "--no-backup",
        ],
    )

    assert result.exit_code == 0

    # Verify no backup created
    backup_dirs = list(target_db.parent.glob("backup_*"))
    assert len(backup_dirs) == 0
