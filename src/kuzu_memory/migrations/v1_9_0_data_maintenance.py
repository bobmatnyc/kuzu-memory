"""One-time data maintenance migration for v1.9.0.

Runs the three storage-hygiene passes that were previously only available
via ``kuzu_optimize(strategy="full_maintenance")``:

1. **Purge expired memories** — delete Memory nodes whose ``valid_to`` is
   non-NULL and lies in the past.
2. **Deduplicate by content_hash** — back-fill missing SHA-256 hashes, then
   keep only the newest copy of each duplicate group.
3. **Trim oversized git_sync metadata** — replace metadata blobs > 1 KB on
   ``source_type = 'git_sync'`` memories with a slim subset (commit_sha,
   author, timestamp, branch, files_changed_count).

Each step is independent and non-fatal: if one fails, the migration logs a
warning and continues.  The migration is fully idempotent — ``check_applicable``
returns ``False`` once the database is clean.

This migration is auto-discovered by ``discover_migrations()`` (module name
starts with ``v``).  It is also run automatically on every DB initialisation
via ``KuzuAdapter._run_data_maintenance()``, which uses the already-open
connection pool so no second ``kuzu.Database`` instance is opened.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

try:
    import kuzu  # type: ignore[import-untyped,unused-ignore]
except ImportError:
    kuzu = None  # type: ignore[assignment,unused-ignore]

from .base import MigrationResult, MigrationType, SchemaMigration

logger = logging.getLogger(__name__)

# Metadata blobs larger than this (in bytes) are candidates for trimming.
_METADATA_THRESHOLD = 1024


# ---------------------------------------------------------------------------
# Pure helper functions — no kuzu dependency; called by both the migration
# class and KuzuAdapter._run_data_maintenance()
# ---------------------------------------------------------------------------


def purge_expired(execute: Any) -> int:
    """Delete memories whose valid_to is non-NULL and in the past.

    Args:
        execute: Callable ``execute(query, params) -> list[dict]``, typically
            ``KuzuAdapter.execute_query`` or a ``kuzu.Connection.execute`` wrapper.

    Returns:
        Number of memories deleted (0 on error or when nothing to purge).
    """
    now_iso = datetime.now().isoformat()
    try:
        count_rows = execute(
            """MATCH (m:Memory)
            WHERE m.valid_to IS NOT NULL
              AND m.valid_to < TIMESTAMP($now)
            RETURN count(m) AS cnt""",
            {"now": now_iso},
        )
        expired_count: int = 0
        if count_rows:
            raw = count_rows[0].get("cnt", 0)
            expired_count = int(raw) if raw is not None else 0

        if expired_count > 0:
            execute(
                """MATCH (m:Memory)
                WHERE m.valid_to IS NOT NULL
                  AND m.valid_to < TIMESTAMP($now)
                DELETE m""",
                {"now": now_iso},
            )
            logger.info("Data maintenance: purged %d expired memories", expired_count)

        return expired_count

    except Exception as exc:
        logger.warning("Data maintenance purge_expired failed (non-fatal): %s", exc)
        return 0


def dedup_by_content_hash(execute: Any) -> tuple[int, int]:
    """Back-fill missing content_hash values and remove duplicate memories.

    Args:
        execute: Callable ``execute(query, params) -> list[dict]``.

    Returns:
        Tuple of ``(hashes_written, duplicates_removed)``.
    """
    hashes_written = 0
    duplicates_removed = 0

    try:
        # Step 1: back-fill missing hashes
        missing_rows = execute(
            """MATCH (m:Memory)
            WHERE m.content_hash IS NULL OR m.content_hash = ''
            RETURN m.id AS id, m.content AS content""",
            {},
        )
        for row in missing_rows:
            mem_id = row.get("id")
            content = row.get("content") or ""
            new_hash = hashlib.sha256(content.encode()).hexdigest()
            if mem_id:
                try:
                    execute(
                        "MATCH (m:Memory {id: $id}) SET m.content_hash = $h",
                        {"id": str(mem_id), "h": new_hash},
                    )
                    hashes_written += 1
                except Exception as exc:
                    logger.warning(
                        "Data maintenance: failed to set content_hash for %s: %s", mem_id, exc
                    )

        # Step 2: find duplicate groups (grouped in Python — Kuzu lacks keep-newest GROUP BY)
        all_rows = execute(
            """MATCH (m:Memory)
            WHERE m.content_hash IS NOT NULL AND m.content_hash <> ''
            RETURN m.id AS id, m.content_hash AS h, m.created_at AS created_at""",
            {},
        )

        groups: dict[str, list[tuple[str, Any]]] = defaultdict(list)
        for row in all_rows:
            h = str(row.get("h") or "")
            mid = str(row.get("id") or "")
            ts = row.get("created_at")
            if h and mid:
                groups[h].append((mid, ts))

        ids_to_delete: list[str] = []
        for _h, members in groups.items():
            if len(members) < 2:
                continue
            # Sort descending by created_at; keep first (newest)
            members.sort(key=lambda pair: str(pair[1]) if pair[1] is not None else "", reverse=True)
            ids_to_delete.extend(mid for mid, _ in members[1:])

        duplicates_removed = len(ids_to_delete)
        if ids_to_delete:
            batch_size = 100
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i : i + batch_size]
                try:
                    execute(
                        "MATCH (m:Memory) WHERE m.id IN $ids DELETE m",
                        {"ids": batch},
                    )
                except Exception as exc:
                    logger.warning("Data maintenance: batch dedup delete failed: %s", exc)
            logger.info(
                "Data maintenance: wrote %d content_hash(es), removed %d duplicate(s)",
                hashes_written,
                duplicates_removed,
            )

    except Exception as exc:
        logger.warning("Data maintenance dedup_by_content_hash failed (non-fatal): %s", exc)

    return hashes_written, duplicates_removed


def trim_git_metadata(execute: Any) -> tuple[int, int]:
    """Replace oversized git_sync metadata blobs with a slim subset.

    Keeps: commit_sha, author, timestamp, branch, files_changed_count.

    Args:
        execute: Callable ``execute(query, params) -> list[dict]``.

    Returns:
        Tuple of ``(trimmed_count, bytes_saved_estimate)``.
    """
    trimmed_count = 0
    bytes_saved_estimate = 0

    try:
        rows = execute(
            """MATCH (m:Memory)
            WHERE m.source_type = 'git_sync'
              AND m.metadata IS NOT NULL
            RETURN m.id AS id, m.metadata AS metadata""",
            {},
        )

        for row in rows:
            mem_id = str(row.get("id") or "")
            raw_meta = row.get("metadata") or ""
            if not mem_id or not raw_meta:
                continue

            raw_str = str(raw_meta)
            if len(raw_str) <= _METADATA_THRESHOLD:
                continue  # Already small enough

            try:
                if isinstance(raw_meta, dict):
                    meta: dict[str, Any] = raw_meta
                else:
                    meta = json.loads(raw_str)
            except (json.JSONDecodeError, TypeError):
                continue  # Cannot parse — leave untouched

            slim: dict[str, Any] = {}
            if "commit_sha" in meta:
                slim["commit_sha"] = meta["commit_sha"]
            if "commit_author" in meta:
                slim["author"] = meta["commit_author"]
            elif "author" in meta:
                slim["author"] = meta["author"]
            if "commit_timestamp" in meta:
                slim["timestamp"] = meta["commit_timestamp"]
            if "files_changed_count" in meta:
                slim["files_changed_count"] = int(meta["files_changed_count"])
            elif "changed_files" in meta and isinstance(meta["changed_files"], list):
                slim["files_changed_count"] = len(meta["changed_files"])
            if "branch" in meta:
                slim["branch"] = meta["branch"]

            slim_str = json.dumps(slim)
            old_size = len(raw_str)
            new_size = len(slim_str)
            if new_size >= old_size:
                continue  # Nothing to save

            try:
                execute(
                    "MATCH (m:Memory {id: $id}) SET m.metadata = $meta",
                    {"id": mem_id, "meta": slim_str},
                )
                bytes_saved_estimate += old_size - new_size
                trimmed_count += 1
            except Exception as exc:
                logger.warning("Data maintenance: failed to trim metadata for %s: %s", mem_id, exc)

        if trimmed_count > 0:
            logger.info(
                "Data maintenance: trimmed %d git_sync metadata blob(s), ~%d bytes saved",
                trimmed_count,
                bytes_saved_estimate,
            )

    except Exception as exc:
        logger.warning("Data maintenance trim_git_metadata failed (non-fatal): %s", exc)

    return trimmed_count, bytes_saved_estimate


def has_work_to_do(execute: Any) -> bool:
    """Return True if any of the three maintenance steps have work to do.

    Used by ``DataMaintenanceMigration.check_applicable()`` and by
    ``KuzuAdapter._run_data_maintenance()`` to short-circuit quickly on
    already-clean databases.

    Args:
        execute: Callable ``execute(query, params) -> list[dict]``.

    Returns:
        True when there is at least one expired memory, memory with a NULL
        content_hash, or git_sync memory with a metadata blob > 1 KB.
    """
    now_iso = datetime.now().isoformat()
    try:
        # Check 1: expired memories
        rows = execute(
            """MATCH (m:Memory)
            WHERE m.valid_to IS NOT NULL AND m.valid_to < TIMESTAMP($now)
            RETURN count(m) AS cnt LIMIT 1""",
            {"now": now_iso},
        )
        if rows and int(rows[0].get("cnt", 0) or 0) > 0:
            return True

        # Check 2: memories with NULL content_hash
        rows = execute(
            """MATCH (m:Memory)
            WHERE m.content_hash IS NULL OR m.content_hash = ''
            RETURN count(m) AS cnt LIMIT 1""",
            {},
        )
        if rows and int(rows[0].get("cnt", 0) or 0) > 0:
            return True

        # Check 3: oversized git_sync metadata (fetch first candidate only)
        rows = execute(
            """MATCH (m:Memory)
            WHERE m.source_type = 'git_sync' AND m.metadata IS NOT NULL
            RETURN m.metadata AS metadata LIMIT 50""",
            {},
        )
        for row in rows:
            raw = str(row.get("metadata") or "")
            if len(raw) > _METADATA_THRESHOLD:
                return True

        return False

    except Exception as exc:
        logger.debug("has_work_to_do probe failed (assuming applicable): %s", exc)
        # If we cannot query, assume there is work to do so migrate() can
        # decide gracefully.
        return True


# ---------------------------------------------------------------------------
# Migration class — used by the CLI-based migration framework
# ---------------------------------------------------------------------------


class DataMaintenanceMigration(SchemaMigration):
    """Run one-time data maintenance passes on startup for v1.9.0.

    Purges expired memories, deduplicates by content_hash, and trims oversized
    git_sync metadata blobs.  All steps are non-fatal and idempotent.

    NOTE: This class opens its own ``kuzu.Database`` instance as required by
    the ``SchemaMigration`` base class.  For the hot-path (every DB init), use
    ``KuzuAdapter._run_data_maintenance()`` instead, which reuses the existing
    connection pool.
    """

    name = "data_maintenance_v1.9.0"
    from_version = "0.0.0"
    to_version = "999.0.0"
    migration_type = MigrationType.DATA
    priority = 70  # After schema_columns_v1.8.1 (60), before cleanup (900)

    def description(self) -> str:
        """Return human-readable description."""
        return (
            "One-time data maintenance: purge expired memories, deduplicate by "
            "content_hash, and trim oversized git_sync metadata blobs"
        )

    def check_applicable(self) -> bool:
        """Return True when there is maintenance work to do.

        Runs a lightweight probe against the database.  Returns False once the
        database is already clean so subsequent startups skip the migration.
        """
        if not super().check_applicable():
            return False

        db_path = self._find_db_path()
        if db_path is None:
            return False

        try:
            if kuzu is None:
                logger.debug("kuzu not available — skipping data maintenance check")
                return False

            db = kuzu.Database(str(db_path))
            conn = kuzu.Connection(db)

            def _execute(query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
                res = conn.execute(query, params) if params else conn.execute(query)
                rows: list[dict[str, Any]] = []
                while res.has_next():
                    row = res.get_next()
                    rows.append(
                        {
                            res.get_column_names()[i]: row[i]
                            for i in range(len(res.get_column_names()))
                        }
                    )
                return rows

            return has_work_to_do(_execute)

        except Exception as exc:
            logger.debug("DataMaintenanceMigration.check_applicable probe failed: %s", exc)
            return True  # Allow migrate() to handle gracefully

    def migrate(self) -> MigrationResult:
        """Run all three maintenance passes and return a consolidated result."""
        db_path = self._find_db_path()
        if db_path is None:
            return MigrationResult(
                success=False,
                message="Database not found — cannot run data_maintenance migration",
            )

        changes: list[str] = []
        warnings: list[str] = []

        try:
            if kuzu is None:
                return MigrationResult(
                    success=False,
                    message="kuzu not available — cannot run data_maintenance migration",
                )

            db = kuzu.Database(str(db_path))
            conn = kuzu.Connection(db)

            def _execute(query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
                res = conn.execute(query, params) if params else conn.execute(query)
                rows: list[dict[str, Any]] = []
                while res.has_next():
                    row = res.get_next()
                    rows.append(
                        {
                            res.get_column_names()[i]: row[i]
                            for i in range(len(res.get_column_names()))
                        }
                    )
                return rows

            # Step 1: purge expired
            purged = purge_expired(_execute)
            if purged > 0:
                changes.append(f"Purged {purged} expired memory record(s)")

            # Step 2: dedup
            hashes_written, dupes = dedup_by_content_hash(_execute)
            if hashes_written > 0:
                changes.append(f"Back-filled {hashes_written} content_hash value(s)")
            if dupes > 0:
                changes.append(f"Removed {dupes} duplicate memory record(s)")

            # Step 3: trim git metadata
            trimmed, saved = trim_git_metadata(_execute)
            if trimmed > 0:
                changes.append(
                    f"Trimmed {trimmed} git_sync metadata blob(s) (~{saved // 1024} KB saved)"
                )

        except Exception as exc:
            logger.error("DataMaintenanceMigration.migrate failed: %s", exc, exc_info=True)
            return MigrationResult(
                success=False,
                message=f"Data maintenance migration failed: {exc}",
                changes=changes,
                warnings=warnings,
            )

        total_changes = len(changes)
        return MigrationResult(
            success=True,
            message=(
                f"Data maintenance completed: {total_changes} change group(s)"
                if total_changes
                else "Data maintenance: nothing to do"
            ),
            changes=changes,
            warnings=warnings,
        )
