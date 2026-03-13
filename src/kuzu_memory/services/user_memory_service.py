"""User-level cross-project memory service."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

from ..core.config import KuzuMemoryConfig, UserConfig
from ..core.models import KnowledgeType, Memory

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class UserMemoryService:
    """
    Manages the user-level cross-project memory database.

    Opens ~/.kuzu-memory/user.db (or configured path) and provides
    promote/recall/query operations. Follows the context manager protocol.

    Usage:
        with UserMemoryService(config) as user_svc:
            user_svc.promote(memory, project_tag="my-project")
            patterns = user_svc.get_patterns()
    """

    def __init__(self, config: KuzuMemoryConfig | None = None) -> None:
        self._config = config or KuzuMemoryConfig()
        self._user_config: UserConfig = self._config.user
        self._db_path = self._user_config.effective_user_db_path()
        self._memory: Any = None  # KuzuMemory instance, set in __enter__

    def __enter__(self) -> UserMemoryService:
        from ..core.memory import KuzuMemory

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory = KuzuMemory(
            db_path=self._db_path,
            enable_git_sync=False,
        ).__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        if self._memory is not None:
            self._memory.__exit__(*args)
            self._memory = None

    # ------------------------------------------------------------------
    # Promotion

    def promote(self, memory: Memory, project_tag: str) -> bool:
        """
        Promote a single memory to the user DB.

        Returns True if written, False if already present (content_hash dedupe).
        Errors are logged and swallowed — promotion must never block callers.
        """
        assert self._memory is not None, "Must be used as context manager"
        try:
            content_hash = memory.content_hash
            if content_hash:
                # Deduplicate by content_hash
                existing = self._memory.db_adapter.execute_query(
                    "MATCH (m:Memory) WHERE m.content_hash = $hash RETURN m.id LIMIT 1",
                    {"hash": content_hash},
                )
                if len(existing) > 0:
                    return False

            # Build a full CREATE that preserves all promotion-relevant fields.
            # We bypass the QueryBuilder.store_memory_in_database() because it
            # omits knowledge_type, importance, content_hash, and project_tag.
            self._memory.db_adapter.execute_query(
                """CREATE (m:Memory {
                    id: $id,
                    content: $content,
                    content_hash: $content_hash,
                    source_type: $source_type,
                    memory_type: $memory_type,
                    knowledge_type: $knowledge_type,
                    project_tag: $project_tag,
                    importance: $importance,
                    confidence: $confidence,
                    created_at: TIMESTAMP($created_at),
                    valid_to: CASE WHEN $valid_to IS NOT NULL THEN TIMESTAMP($valid_to) ELSE NULL END,
                    accessed_at: TIMESTAMP($accessed_at),
                    access_count: $access_count,
                    user_id: $user_id,
                    session_id: $session_id,
                    agent_id: $agent_id,
                    metadata: $metadata
                })""",
                {
                    "id": memory.id,
                    "content": memory.content,
                    "content_hash": memory.content_hash or "",
                    "source_type": memory.source_type,
                    "memory_type": memory.memory_type.value,
                    "knowledge_type": memory.knowledge_type.value,
                    "project_tag": project_tag,
                    "importance": memory.importance,
                    "confidence": memory.confidence,
                    "created_at": (
                        memory.created_at.isoformat()
                        if memory.created_at
                        else datetime.datetime.now().isoformat()
                    ),
                    "valid_to": memory.valid_to.isoformat() if memory.valid_to else None,
                    "accessed_at": (
                        memory.accessed_at.isoformat()
                        if memory.accessed_at
                        else datetime.datetime.now().isoformat()
                    ),
                    "access_count": memory.access_count,
                    "user_id": memory.user_id,
                    "session_id": memory.session_id,
                    "agent_id": memory.agent_id,
                    "metadata": (__import__("json").dumps(memory.metadata or {})),
                },
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to promote memory {memory.id}: {e}")
            return False

    def promote_batch(self, memories: list[Memory], project_tag: str) -> int:
        """Promote a list of memories. Returns count actually written."""
        written = 0
        for memory in memories:
            if self.promote(memory, project_tag):
                written += 1
        return written

    # ------------------------------------------------------------------
    # Retrieval

    def get_patterns(
        self,
        knowledge_types: list[KnowledgeType] | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """Return top memories by knowledge_type, sorted by importance desc."""
        assert self._memory is not None
        types = knowledge_types or [
            KnowledgeType.RULE,
            KnowledgeType.PATTERN,
            KnowledgeType.GOTCHA,
            KnowledgeType.ARCHITECTURE,
        ]
        type_values = [t.value for t in types]
        try:
            results = self._memory.db_adapter.execute_query(
                """MATCH (m:Memory)
                WHERE m.knowledge_type IN $types
                  AND (m.valid_to IS NULL OR m.valid_to > TIMESTAMP($now))
                RETURN m ORDER BY m.importance DESC LIMIT $limit""",
                {
                    "types": type_values,
                    "now": datetime.datetime.now().isoformat(),
                    "limit": limit,
                },
            )
            return self._results_to_memories(results)
        except Exception as e:
            logger.warning(f"get_patterns failed: {e}")
            return []

    def recall(self, query: str, limit: int = 10) -> list[Memory]:
        """Semantic recall from user DB via attach_memories."""
        assert self._memory is not None
        try:
            context = self._memory.attach_memories(query, max_memories=limit)
            memories: list[Memory] = context.memories if context else []
            return memories
        except Exception as e:
            logger.warning(f"recall failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Stats

    def get_stats(self) -> dict[str, Any]:
        """Return user DB statistics."""
        assert self._memory is not None
        try:
            total = self._memory.get_memory_count()

            # Type breakdown
            type_rows = self._memory.db_adapter.execute_query(
                "MATCH (m:Memory) RETURN m.knowledge_type AS kt, COUNT(*) AS cnt"
            )
            type_counts: dict[str, int] = {
                row["kt"]: int(row["cnt"]) for row in type_rows if row.get("kt")
            }

            # Project breakdown
            proj_rows = self._memory.db_adapter.execute_query(
                "MATCH (m:Memory) WHERE m.project_tag <> '' "
                "RETURN m.project_tag AS pt, COUNT(*) AS cnt ORDER BY cnt DESC LIMIT 10"
            )
            projects: dict[str, int] = {
                row["pt"]: int(row["cnt"]) for row in proj_rows if row.get("pt")
            }

            return {
                "db_path": str(self._db_path),
                "total_memories": total,
                "by_knowledge_type": type_counts,
                "by_project": projects,
            }
        except Exception as e:
            logger.warning(f"get_stats failed: {e}")
            return {
                "db_path": str(self._db_path),
                "total_memories": 0,
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Helpers

    def _results_to_memories(self, results: list[dict[str, Any]]) -> list[Memory]:
        """Convert execute_query rows ({"m": {...}}) to Memory objects."""
        memories: list[Memory] = []
        for row in results:
            try:
                memory_data = row.get("m", row)  # RETURN m → {"m": {...}}
                if isinstance(memory_data, dict):
                    memories.append(Memory.from_dict(memory_data))
            except Exception:
                pass
        return memories
