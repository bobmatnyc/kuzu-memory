"""
Memory sharing module for KuzuMemory.

Provides export and import functionality for sharing memories across machines
and users via JSON files stored in a git-trackable directory.

Export writes delta memories to kuzu-memory-shared/ as date-partitioned JSON files.
Import reads those files and inserts new memories into the local Kùzu database,
deduplicating by content_hash to prevent double-imports.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Shared directory name (git-trackable, NOT in .gitignore)
SHARED_DIR_NAME = "kuzu-memory-shared"
EXPORT_STATE_FILE = ".export-state.json"
IMPORT_STATE_FILE = ".import-state.json"
EXPORT_VERSION = "1.0"


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------


def _load_export_state(shared_dir: Path) -> dict[str, Any]:
    """Load the export state from .export-state.json, or return defaults."""
    state_file = shared_dir / EXPORT_STATE_FILE
    if state_file.exists():
        try:
            data: dict[str, Any] = json.loads(state_file.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read export state file, starting fresh: %s", exc)
    return {"last_export_at": None, "total_exported": 0, "export_history": []}


def _save_export_state(shared_dir: Path, state: dict[str, Any]) -> None:
    """Persist the export state to .export-state.json."""
    state_file = shared_dir / EXPORT_STATE_FILE
    state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _load_import_state(shared_dir: Path) -> dict[str, Any]:
    """Load the import state from .import-state.json, or return defaults."""
    state_file = shared_dir / IMPORT_STATE_FILE
    if state_file.exists():
        try:
            data: dict[str, Any] = json.loads(state_file.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read import state file, starting fresh: %s", exc)
    return {
        "last_import_at": None,
        "processed_files": [],
        "imported_hashes": [],
        "total_imported": 0,
    }


def _save_import_state(shared_dir: Path, state: dict[str, Any]) -> None:
    """Persist the import state to .import-state.json."""
    state_file = shared_dir / IMPORT_STATE_FILE
    state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Date-file helpers
# ---------------------------------------------------------------------------


def _memories_filename(date_str: str) -> str:
    """Return the JSON filename for a given YYYY-MM-DD date string."""
    return f"memories-{date_str}.json"


def _load_memories_file(path: Path) -> dict[str, Any]:
    """Load an existing memories JSON file, or return an empty structure."""
    if path.exists():
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read memories file %s, starting fresh: %s", path, exc)
    return {
        "export_version": EXPORT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "source_project": "",
        "memories": [],
    }


def _save_memories_file(path: Path, data: dict[str, Any]) -> None:
    """Write the memories JSON file with pretty-printing."""
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Kuzu row iteration helper (matches the pattern in _merge)
# ---------------------------------------------------------------------------


def _iter_query_result(result: Any) -> list[dict[str, Any]]:
    """
    Convert a Kuzu QueryResult (or list of results) to a list of dicts.

    Kuzu returns a single QueryResult object (not a list).  Each row is
    accessed via has_next() / get_next().
    """
    rows: list[dict[str, Any]] = []
    if isinstance(result, list):
        # Should not happen in practice, but guard defensively
        for r in result:
            column_names = r.get_column_names()
            while r.has_next():
                row_list: list[Any] = list(r.get_next())
                rows.append({str(column_names[i]): row_list[i] for i in range(len(column_names))})
    else:
        column_names = result.get_column_names()
        while result.has_next():
            row_list = list(result.get_next())
            rows.append({str(column_names[i]): row_list[i] for i in range(len(column_names))})
    return rows


def _format_datetime(value: Any) -> str:
    """Coerce a Kuzu datetime value to an ISO-8601 string with UTC suffix."""
    if value is None:
        return datetime.now(UTC).isoformat()
    if isinstance(value, datetime):
        dt: datetime = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        result: str = dt.isoformat()
        return result
    # String coming from the DB
    s = str(value)
    if not s.endswith("Z") and "+" not in s[10:]:
        s = s + "Z"
    return s


def _parse_datetime(value: Any) -> datetime:
    """Parse an ISO-8601 string (or datetime) to a timezone-aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    s = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def _date_str(dt: datetime) -> str:
    """Return the YYYY-MM-DD portion of a datetime."""
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Export logic
# ---------------------------------------------------------------------------


def export_shared(
    db_path: Path,
    project_root: Path,
    min_age_days: int = 1,
) -> dict[str, Any]:
    """
    Export delta memories to kuzu-memory-shared/ as JSON files.

    Queries memories that are:
    - NOT sourced from 'git_sync' (user-generated only)
    - Newer than the last export timestamp (delta only)
    - At least min_age_days old (no intra-day exports by default)

    Memories are grouped by creation date and written (or merged) into
    memories-YYYY-MM-DD.json files.

    Args:
        db_path: Path to the Kùzu database directory.
        project_root: Project root directory (shared dir is relative to it).
        min_age_days: Minimum age of memories to export (default 1 day).

    Returns:
        Summary dict with exported_count, files_written, last_export.

    Raises:
        ImportError: If the kuzu library is not installed.
        RuntimeError: If the database does not exist.
    """
    try:
        import kuzu
    except ImportError as exc:
        raise ImportError("Kuzu library not found. Install with: pip install kuzu>=0.4.0") from exc

    if not db_path.exists():
        raise RuntimeError(
            f"Memory database not found at {db_path}. Initialize with 'kuzu-memory setup' first."
        )

    # Ensure shared directory exists
    shared_dir = project_root / SHARED_DIR_NAME
    shared_dir.mkdir(parents=True, exist_ok=True)

    # Load export state
    state = _load_export_state(shared_dir)
    last_export_at: datetime | None = None
    if state.get("last_export_at"):
        last_export_at = _parse_datetime(state["last_export_at"])

    # Compute cutoff: now minus min_age_days
    now = datetime.now(UTC)
    cutoff_time = now - timedelta(days=min_age_days)

    # If there's no last export, default to epoch (export everything old enough)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    after_time = last_export_at if last_export_at is not None else epoch

    logger.info(
        "Exporting memories: after=%s, before=%s",
        after_time.isoformat(),
        cutoff_time.isoformat(),
    )

    # Query the database directly (read-only)
    db = kuzu.Database(str(db_path), read_only=True)
    conn = kuzu.Connection(db)

    export_query = """
        MATCH (m:Memory)
        WHERE m.source_type <> 'git_sync'
          AND m.created_at > $last_export
          AND m.created_at <= $cutoff_time
        RETURN m.id AS id,
               m.content AS content,
               m.content_hash AS content_hash,
               m.created_at AS created_at,
               m.memory_type AS memory_type,
               m.source_type AS source_type,
               m.importance AS importance,
               m.confidence AS confidence,
               m.metadata AS metadata,
               m.agent_id AS agent_id,
               m.user_id AS user_id,
               m.session_id AS session_id
        ORDER BY m.created_at ASC
    """

    raw_result = conn.execute(
        export_query,
        {"last_export": after_time, "cutoff_time": cutoff_time},
    )
    rows = _iter_query_result(raw_result)

    if not rows:
        logger.info("No new memories to export.")
        return {
            "exported_count": 0,
            "files_written": [],
            "last_export": _format_datetime(last_export_at or epoch),
        }

    # Group memories by creation date
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        created_at = _parse_datetime(row["created_at"])
        date_key = _date_str(created_at)
        by_date.setdefault(date_key, []).append(row)

    # Write (or merge) per-date JSON files
    project_name = project_root.name
    files_written: list[str] = []
    total_exported = 0

    for date_key, date_rows in sorted(by_date.items()):
        filename = _memories_filename(date_key)
        filepath = shared_dir / filename

        # Load existing file so we can merge (avoid duplicates by content_hash)
        existing = _load_memories_file(filepath)
        existing["source_project"] = project_name
        existing["exported_at"] = now.isoformat()

        existing_hashes: set[str] = {
            str(m.get("content_hash", "")) for m in existing.get("memories", [])
        }

        new_memories: list[dict[str, Any]] = []
        for row in date_rows:
            content_hash = str(row.get("content_hash") or "")
            if content_hash and content_hash in existing_hashes:
                logger.debug("Skipping already-exported memory: %s", content_hash)
                continue

            memory_record: dict[str, Any] = {
                "id": str(row.get("id") or uuid.uuid4()),
                "content": str(row.get("content") or ""),
                "content_hash": content_hash,
                "created_at": _format_datetime(row.get("created_at")),
                "memory_type": str(row.get("memory_type") or "semantic"),
                "source_type": str(row.get("source_type") or "manual"),
                "importance": float(row["importance"])
                if row.get("importance") is not None
                else 0.5,
                "confidence": float(row["confidence"])
                if row.get("confidence") is not None
                else 1.0,
                "metadata": _parse_metadata(row.get("metadata")),
                "agent_id": str(row.get("agent_id") or "default"),
                "user_id": str(row["user_id"]) if row.get("user_id") else None,
                "session_id": str(row["session_id"]) if row.get("session_id") else None,
            }
            new_memories.append(memory_record)
            existing_hashes.add(content_hash)

        if not new_memories:
            continue

        existing.setdefault("memories", []).extend(new_memories)
        _save_memories_file(filepath, existing)
        files_written.append(filename)
        total_exported += len(new_memories)
        logger.info("Wrote %d memories to %s", len(new_memories), filename)

    # Update export state
    new_last_export = now.isoformat()
    history_entry: dict[str, Any] = {
        "timestamp": new_last_export,
        "count": total_exported,
        "files": files_written,
    }
    state["last_export_at"] = new_last_export
    state["total_exported"] = int(state.get("total_exported", 0)) + total_exported
    history: list[dict[str, Any]] = state.get("export_history", [])
    history.append(history_entry)
    state["export_history"] = history[-100:]  # Keep last 100 entries
    _save_export_state(shared_dir, state)

    return {
        "exported_count": total_exported,
        "files_written": files_written,
        "last_export": new_last_export,
    }


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------


def import_shared(
    db_path: Path,
    project_root: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Import new memories from kuzu-memory-shared/ JSON files.

    Scans for memories-*.json files, skips already-processed files and
    content_hashes, and inserts new memories into the local Kùzu database.

    Args:
        db_path: Path to the Kùzu database directory.
        project_root: Project root directory (shared dir is relative to it).
        dry_run: If True, preview what would be imported without making changes.

    Returns:
        Summary dict with imported_count, skipped_duplicates, files_processed.

    Raises:
        ImportError: If the kuzu library is not installed.
        RuntimeError: If the shared directory or database does not exist.
    """
    try:
        import kuzu
    except ImportError as exc:
        raise ImportError("Kuzu library not found. Install with: pip install kuzu>=0.4.0") from exc

    shared_dir = project_root / SHARED_DIR_NAME
    if not shared_dir.exists():
        raise RuntimeError(
            f"Shared directory not found: {shared_dir}. "
            "Run kuzu_export_shared on a machine with memories first."
        )

    if not db_path.exists():
        raise RuntimeError(
            f"Memory database not found at {db_path}. Initialize with 'kuzu-memory setup' first."
        )

    # Load import state
    state = _load_import_state(shared_dir)
    processed_files: set[str] = set(state.get("processed_files", []))
    imported_hashes: set[str] = set(state.get("imported_hashes", []))

    # Scan for memories files
    memory_files = sorted(shared_dir.glob("memories-*.json"))
    if not memory_files:
        logger.info("No memory files found in %s.", shared_dir)
        return {
            "imported_count": 0,
            "skipped_duplicates": 0,
            "files_processed": [],
        }

    # Pre-load existing content_hashes from the local DB for efficient dedup
    existing_hashes_in_db = _fetch_existing_hashes(kuzu, db_path)
    combined_known_hashes = imported_hashes | existing_hashes_in_db

    imported_count = 0
    skipped_duplicates = 0
    files_processed: list[str] = []
    memories_to_insert: list[dict[str, Any]] = []

    for mem_file in memory_files:
        filename = mem_file.name

        try:
            file_data = json.loads(mem_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping unreadable file %s: %s", filename, exc)
            continue

        file_memories: list[dict[str, Any]] = file_data.get("memories", [])
        file_new = 0
        file_skipped = 0

        for memory in file_memories:
            content_hash = str(memory.get("content_hash") or "")
            if not content_hash or content_hash in combined_known_hashes:
                file_skipped += 1
                skipped_duplicates += 1
                continue

            # Mark as known immediately to prevent double-import within a run
            combined_known_hashes.add(content_hash)
            memories_to_insert.append(memory)
            file_new += 1
            imported_count += 1

        if file_new > 0 or filename not in processed_files:
            files_processed.append(filename)
            logger.info("File %s: %d new, %d skipped", filename, file_new, file_skipped)

    if dry_run:
        return {
            "imported_count": imported_count,
            "skipped_duplicates": skipped_duplicates,
            "files_processed": files_processed,
            "dry_run": True,
            "message": (
                f"Dry run: {imported_count} memories would be imported, "
                f"{skipped_duplicates} duplicates would be skipped."
            ),
        }

    # Perform actual insertion
    if memories_to_insert:
        _insert_memories(kuzu, db_path, memories_to_insert)

    # Update import state
    now_str = datetime.now(UTC).isoformat()
    all_processed = sorted(processed_files | set(files_processed))
    # Keep the imported_hashes list bounded to the last 50 000 entries
    all_hashes = list(imported_hashes)
    all_hashes.extend(
        m.get("content_hash", "") for m in memories_to_insert if m.get("content_hash")
    )
    if len(all_hashes) > 50_000:
        all_hashes = all_hashes[-50_000:]

    state["last_import_at"] = now_str
    state["processed_files"] = all_processed
    state["imported_hashes"] = all_hashes
    state["total_imported"] = int(state.get("total_imported", 0)) + imported_count
    _save_import_state(shared_dir, state)

    return {
        "imported_count": imported_count,
        "skipped_duplicates": skipped_duplicates,
        "files_processed": files_processed,
    }


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _fetch_existing_hashes(kuzu_module: Any, db_path: Path) -> set[str]:
    """
    Return the set of content_hash values already present in the local DB.

    Uses a read-only connection to avoid locking issues.
    """
    try:
        db = kuzu_module.Database(str(db_path), read_only=True)
        conn = kuzu_module.Connection(db)
        result = conn.execute("MATCH (m:Memory) RETURN m.content_hash AS content_hash")
        rows = _iter_query_result(result)
        return {str(r["content_hash"]) for r in rows if r.get("content_hash")}
    except Exception as exc:
        logger.warning("Could not fetch existing hashes (treating as empty): %s", exc)
        return set()


def _insert_memories(kuzu_module: Any, db_path: Path, memories: list[dict[str, Any]]) -> None:
    """
    Insert a list of memory records into the local Kùzu database.

    Each record must have at minimum: content, content_hash, memory_type,
    source_type, importance, confidence.
    """
    db = kuzu_module.Database(str(db_path))
    conn = kuzu_module.Connection(db)

    insert_query = """
        CREATE (m:Memory {
            id: $id,
            content: $content,
            content_hash: $content_hash,
            created_at: $created_at,
            memory_type: $memory_type,
            source_type: $source_type,
            importance: $importance,
            confidence: $confidence,
            metadata: $metadata,
            agent_id: $agent_id,
            user_id: $user_id,
            session_id: $session_id,
            accessed_at: $accessed_at,
            access_count: 0,
            valid_from: $created_at,
            valid_to: NULL
        })
    """

    now_dt = datetime.now(UTC)
    errors = 0

    for memory in memories:
        try:
            created_at = _parse_datetime(memory.get("created_at") or now_dt.isoformat())

            metadata_value = memory.get("metadata")
            if isinstance(metadata_value, dict):
                metadata_str = json.dumps(metadata_value)
            elif metadata_value is None:
                metadata_str = "{}"
            else:
                metadata_str = str(metadata_value)

            params: dict[str, Any] = {
                "id": str(memory.get("id") or uuid.uuid4()),
                "content": str(memory.get("content") or ""),
                "content_hash": str(memory.get("content_hash") or ""),
                "created_at": created_at,
                "memory_type": str(memory.get("memory_type") or "semantic"),
                "source_type": str(memory.get("source_type") or "manual"),
                "importance": float(memory["importance"])
                if memory.get("importance") is not None
                else 0.5,
                "confidence": float(memory["confidence"])
                if memory.get("confidence") is not None
                else 1.0,
                "metadata": metadata_str,
                "agent_id": str(memory.get("agent_id") or "default"),
                "user_id": str(memory["user_id"]) if memory.get("user_id") else None,
                "session_id": str(memory["session_id"]) if memory.get("session_id") else None,
                "accessed_at": now_dt,
            }
            conn.execute(insert_query, params)

        except Exception as exc:
            logger.error(
                "Failed to insert memory (hash=%s): %s",
                memory.get("content_hash", "?"),
                exc,
            )
            errors += 1

    if errors:
        logger.warning("Completed import with %d insertion errors.", errors)


# ---------------------------------------------------------------------------
# Metadata parsing helper
# ---------------------------------------------------------------------------


def _parse_metadata(value: Any) -> dict[str, Any]:
    """Coerce a DB metadata value to a plain dict."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
