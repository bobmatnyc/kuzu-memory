"""Memory export utility for pre-migration backups."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..storage.kuzu_adapter import KuzuAdapter

logger = logging.getLogger(__name__)


def _serialise(obj: Any) -> Any:
    """Convert non-JSON-serialisable values to serialisable form.

    Handles datetime objects (isoformat) and falls back to the original
    value for all other types.
    """
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def export_memories_to_json(
    db_adapter: KuzuAdapter,
    backup_path: Path,
    *,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Export all memories to a JSON file.

    Designed to be called before schema migrations. Creates a timestamped
    backup file that can be used to restore memories if a migration fails.

    Args:
        db_adapter: Connected KuzuAdapter instance.
        backup_path: Directory to write the backup file. Created if absent.
        include_archived: When True, also exports ArchivedMemory nodes.

    Returns:
        Dict with keys ``memories`` (count exported), ``archived`` (count
        exported), and ``path`` (absolute path of the written file).

    Raises:
        OSError: If backup_path cannot be created or written.
        RuntimeError: If the export query fails.
    """
    backup_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = backup_path / f"memories_backup_{timestamp}.json"

    memories_query = """
    MATCH (m:Memory)
    RETURN m.id AS id,
           m.content AS content,
           m.content_hash AS content_hash,
           m.created_at AS created_at,
           m.accessed_at AS accessed_at,
           m.access_count AS access_count,
           m.memory_type AS memory_type,
           m.knowledge_type AS knowledge_type,
           m.importance AS importance,
           m.confidence AS confidence,
           m.source_type AS source_type,
           m.source_speaker AS source_speaker,
           m.project_tag AS project_tag,
           m.agent_id AS agent_id,
           m.user_id AS user_id,
           m.session_id AS session_id,
           m.metadata AS metadata
    ORDER BY m.created_at
    """

    rows = db_adapter.execute_query(memories_query)

    memories = [{k: _serialise(v) for k, v in row.items()} for row in rows]

    backup_data: dict[str, Any] = {
        "schema_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "memory_count": len(memories),
        "memories": memories,
        "archived": [],
        "archived_count": 0,
    }

    archived_count = 0
    if include_archived:
        archived_query = (
            "MATCH (m:ArchivedMemory) "
            "RETURN m.id AS id, m.content AS content, m.archived_at AS archived_at "
            "ORDER BY m.archived_at"
        )
        try:
            archived_rows = db_adapter.execute_query(archived_query)
            backup_data["archived"] = [
                {k: _serialise(v) for k, v in r.items()} for r in archived_rows
            ]
            archived_count = len(backup_data["archived"])
            backup_data["archived_count"] = archived_count
        except Exception as exc:
            logger.warning("Could not export ArchivedMemory (table may not exist): %s", exc)

    output_file.write_text(json.dumps(backup_data, indent=2, default=str))
    logger.info("Exported %d memories to %s", len(memories), output_file)

    return {"memories": len(memories), "archived": archived_count, "path": str(output_file)}
