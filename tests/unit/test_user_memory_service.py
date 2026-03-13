"""Unit tests for UserMemoryService."""

from __future__ import annotations

from pathlib import Path

import pytest

from kuzu_memory.core.config import KuzuMemoryConfig, UserConfig
from kuzu_memory.core.models import KnowledgeType, Memory, MemoryType
from kuzu_memory.services.user_memory_service import UserMemoryService


def _make_config(user_db_path: Path) -> KuzuMemoryConfig:
    """Build a KuzuMemoryConfig with a custom user DB path."""
    config = KuzuMemoryConfig()
    config.user = UserConfig(
        mode="user",
        user_db_path=str(user_db_path),
        promotion_min_importance=0.8,
        promotion_knowledge_types=["rule", "pattern", "gotcha", "architecture"],
        project_tag="test-project",
    )
    return config


def _make_memory(
    content: str = "test content",
    knowledge_type: KnowledgeType = KnowledgeType.RULE,
    importance: float = 0.9,
) -> Memory:
    """Create a Memory instance suitable for promotion tests."""
    return Memory(
        content=content,
        memory_type=MemoryType.SEMANTIC,
        knowledge_type=knowledge_type,
        importance=importance,
        valid_to=None,
        user_id=None,
        session_id=None,
    )


# ---------------------------------------------------------------------------
# promote: single memory


def test_promote_writes_memory(tmp_path: Path) -> None:
    """promote() returns True and memory is retrievable from user DB."""
    config = _make_config(tmp_path / "user.db")
    memory = _make_memory("Always use RLock for re-entrant locks")

    with UserMemoryService(config) as svc:
        result = svc.promote(memory, project_tag="project-a")
        assert result is True

        # Verify it's in the DB via stats
        stats = svc.get_stats()
        assert stats["total_memories"] >= 1


def test_promote_deduplication(tmp_path: Path) -> None:
    """Promoting the same memory twice: second call returns False, count stays 1."""
    config = _make_config(tmp_path / "user.db")
    memory = _make_memory("Duplicate gotcha content")

    with UserMemoryService(config) as svc:
        first = svc.promote(memory, project_tag="project-a")
        assert first is True

        second = svc.promote(memory, project_tag="project-a")
        assert second is False

        # Only one memory in DB
        stats = svc.get_stats()
        assert stats["total_memories"] == 1


# ---------------------------------------------------------------------------
# promote_batch


def test_promote_batch_returns_count(tmp_path: Path) -> None:
    """promote_batch with 3 memories and 1 pre-existing duplicate returns 2."""
    config = _make_config(tmp_path / "user.db")
    m1 = _make_memory("Rule one")
    m2 = _make_memory("Rule two")
    m3 = _make_memory("Rule three")

    with UserMemoryService(config) as svc:
        # Pre-promote m1 to create duplicate
        svc.promote(m1, project_tag="project-a")

        # Now batch promote all three — m1 is a dup, m2 and m3 are new
        written = svc.promote_batch([m1, m2, m3], project_tag="project-a")
        assert written == 2

        stats = svc.get_stats()
        assert stats["total_memories"] == 3  # m1 + m2 + m3


# ---------------------------------------------------------------------------
# get_patterns


def test_get_patterns_filters_by_type(tmp_path: Path) -> None:
    """get_patterns returns only memories of the requested knowledge_types."""
    config = _make_config(tmp_path / "user.db")

    rule_mem = _make_memory("A rule memory", KnowledgeType.RULE, importance=0.9)
    pattern_mem = _make_memory("A pattern memory", KnowledgeType.PATTERN, importance=0.85)
    convention_mem = _make_memory("A convention memory", KnowledgeType.CONVENTION, importance=0.8)

    with UserMemoryService(config) as svc:
        svc.promote(rule_mem, "proj")
        svc.promote(pattern_mem, "proj")
        svc.promote(convention_mem, "proj")

        # Request only RULE type
        rules_only = svc.get_patterns(knowledge_types=[KnowledgeType.RULE])
        assert all(m.knowledge_type == KnowledgeType.RULE for m in rules_only)
        assert len(rules_only) >= 1

        # Request RULE + PATTERN
        rules_and_patterns = svc.get_patterns(
            knowledge_types=[KnowledgeType.RULE, KnowledgeType.PATTERN]
        )
        returned_types = {m.knowledge_type for m in rules_and_patterns}
        assert returned_types.issubset({KnowledgeType.RULE, KnowledgeType.PATTERN})
        assert len(rules_and_patterns) == 2


# ---------------------------------------------------------------------------
# get_stats


def test_get_stats_structure(tmp_path: Path) -> None:
    """get_stats returns a dict with the expected top-level keys."""
    config = _make_config(tmp_path / "user.db")

    with UserMemoryService(config) as svc:
        svc.promote(_make_memory("Stats test memory"), "proj")
        stats = svc.get_stats()

    assert "db_path" in stats
    assert "total_memories" in stats
    assert "by_knowledge_type" in stats
    assert "by_project" in stats
    assert stats["total_memories"] >= 1
    assert str(tmp_path / "user.db") in stats["db_path"]


# ---------------------------------------------------------------------------
# Context manager safety


def test_context_manager_cleans_up(tmp_path: Path) -> None:
    """UserMemoryService releases _memory on __exit__."""
    config = _make_config(tmp_path / "user.db")
    svc = UserMemoryService(config)

    with svc:
        assert svc._memory is not None

    assert svc._memory is None


# ---------------------------------------------------------------------------
# UserConfig helpers


def test_effective_project_tag_uses_cwd_when_empty() -> None:
    """effective_project_tag() falls back to cwd basename when project_tag is ''."""
    uc = UserConfig(project_tag="")
    expected = Path.cwd().name
    assert uc.effective_project_tag() == expected


def test_effective_project_tag_uses_override() -> None:
    """effective_project_tag() returns the explicit tag when set."""
    uc = UserConfig(project_tag="my-project")
    assert uc.effective_project_tag() == "my-project"


def test_effective_user_db_path_expands_tilde() -> None:
    """effective_user_db_path() expands ~ in the path."""
    uc = UserConfig(user_db_path="~/.kuzu-memory/user.db")
    result = uc.effective_user_db_path()
    assert not str(result).startswith("~")
    assert result.is_absolute()
