"""
Unit tests for UserConfig and KuzuMemoryConfig user-level config fields.

Covers:
- UserConfig defaults
- effective_project_tag() with and without explicit value
- KuzuMemoryConfig has user field
- from_dict() parses user section
- env var overrides: KUZU_MEMORY_MODE, KUZU_MEMORY_USER_DB_PATH,
  KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE
- to_dict() includes user section
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch


class TestUserConfigDefaults:
    """Test UserConfig dataclass defaults."""

    def test_user_config_defaults(self) -> None:
        """UserConfig initialises with sensible defaults."""
        from kuzu_memory.core.config import UserConfig

        cfg = UserConfig()
        assert cfg.mode == "project"
        assert "user.db" in cfg.user_db_path
        assert ".kuzu-memory" in cfg.user_db_path
        assert cfg.promotion_min_importance == 0.8
        assert "rule" in cfg.promotion_knowledge_types
        assert "pattern" in cfg.promotion_knowledge_types
        assert "gotcha" in cfg.promotion_knowledge_types
        assert "architecture" in cfg.promotion_knowledge_types
        assert cfg.project_tag == ""

    def test_effective_project_tag_uses_cwd_when_empty(self) -> None:
        """effective_project_tag() returns cwd basename when project_tag is empty."""
        from kuzu_memory.core.config import UserConfig

        cfg = UserConfig()
        assert cfg.project_tag == ""
        # Should return basename of current working directory
        expected = Path.cwd().name
        assert cfg.effective_project_tag() == expected

    def test_effective_project_tag_uses_explicit_value(self) -> None:
        """effective_project_tag() returns project_tag when explicitly set."""
        from kuzu_memory.core.config import UserConfig

        cfg = UserConfig()
        cfg.project_tag = "my-project"
        assert cfg.effective_project_tag() == "my-project"

    def test_effective_user_db_path_returns_path(self) -> None:
        """effective_user_db_path() returns a resolved Path."""
        from kuzu_memory.core.config import UserConfig

        cfg = UserConfig()
        result = cfg.effective_user_db_path()
        assert isinstance(result, Path)
        # Default is ~/.kuzu-memory/user.db
        assert result.name == "user.db"

    def test_effective_user_db_path_expands_tilde(self) -> None:
        """effective_user_db_path() expands ~ in the path."""
        from kuzu_memory.core.config import UserConfig

        cfg = UserConfig()
        cfg.user_db_path = "~/.kuzu-memory/user.db"
        result = cfg.effective_user_db_path()
        assert "~" not in str(result)
        assert result.is_absolute()


class TestKuzuMemoryConfigUserField:
    """Test that KuzuMemoryConfig integrates UserConfig correctly."""

    def test_kuzu_memory_config_has_user_field(self) -> None:
        """KuzuMemoryConfig has a user field of type UserConfig."""
        from kuzu_memory.core.config import KuzuMemoryConfig, UserConfig

        config = KuzuMemoryConfig()
        assert hasattr(config, "user")
        assert isinstance(config.user, UserConfig)

    def test_user_config_from_yaml(self) -> None:
        """KuzuMemoryConfig.from_dict() correctly parses the 'user' section."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        data = {
            "user": {
                "mode": "user",
                "user_db_path": "/custom/path/user.db",
                "promotion_min_importance": 0.9,
                "promotion_knowledge_types": ["rule", "gotcha"],
                "project_tag": "test-project",
            }
        }
        config = KuzuMemoryConfig.from_dict(data)
        assert config.user.mode == "user"
        assert config.user.user_db_path == "/custom/path/user.db"
        assert config.user.promotion_min_importance == 0.9
        assert config.user.promotion_knowledge_types == ["rule", "gotcha"]
        assert config.user.project_tag == "test-project"

    def test_to_dict_includes_user(self) -> None:
        """KuzuMemoryConfig.to_dict() includes the 'user' key."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        config = KuzuMemoryConfig()
        d = config.to_dict()
        assert "user" in d
        user_d = d["user"]
        assert "mode" in user_d
        assert "user_db_path" in user_d
        assert "promotion_min_importance" in user_d
        assert "promotion_knowledge_types" in user_d
        assert "project_tag" in user_d

    def test_to_dict_round_trips_user_values(self) -> None:
        """to_dict() then from_dict() preserves user values."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        config = KuzuMemoryConfig()
        config.user.mode = "user"
        config.user.project_tag = "roundtrip-project"
        config.user.promotion_min_importance = 0.75

        d = config.to_dict()
        restored = KuzuMemoryConfig.from_dict(d)
        assert restored.user.mode == "user"
        assert restored.user.project_tag == "roundtrip-project"
        assert restored.user.promotion_min_importance == 0.75


class TestEnvVarOverrides:
    """Test environment variable overrides for user config."""

    def test_env_var_mode_override(self) -> None:
        """KUZU_MEMORY_MODE overrides user.mode."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        with patch.dict(os.environ, {"KUZU_MEMORY_MODE": "user"}):
            config = KuzuMemoryConfig.from_dict({})
        assert config.user.mode == "user"

    def test_env_var_mode_override_project(self) -> None:
        """KUZU_MEMORY_MODE=project keeps project mode."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        with patch.dict(os.environ, {"KUZU_MEMORY_MODE": "project"}):
            config = KuzuMemoryConfig.from_dict({"user": {"mode": "user"}})
        # env var wins over yaml
        assert config.user.mode == "project"

    def test_env_var_user_db_path_override(self) -> None:
        """KUZU_MEMORY_USER_DB_PATH overrides user.user_db_path."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        with patch.dict(os.environ, {"KUZU_MEMORY_USER_DB_PATH": "/tmp/custom/user.db"}):
            config = KuzuMemoryConfig.from_dict({})
        assert config.user.user_db_path == "/tmp/custom/user.db"

    def test_env_var_promotion_min_importance_override(self) -> None:
        """KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE overrides promotion_min_importance."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        with patch.dict(os.environ, {"KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE": "0.95"}):
            config = KuzuMemoryConfig.from_dict({})
        assert config.user.promotion_min_importance == 0.95

    def test_env_var_promotion_min_importance_malformed(self) -> None:
        """Malformed KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE is ignored gracefully."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        with patch.dict(os.environ, {"KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE": "not-a-float"}):
            config = KuzuMemoryConfig.from_dict({})
        # Falls back to default
        assert config.user.promotion_min_importance == 0.8

    def test_env_vars_absent_do_not_override(self) -> None:
        """When env vars are absent, yaml values are preserved."""
        from kuzu_memory.core.config import KuzuMemoryConfig

        # Ensure env vars are not set
        env_keys = [
            "KUZU_MEMORY_MODE",
            "KUZU_MEMORY_USER_DB_PATH",
            "KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE",
        ]
        clean_env = {k: v for k, v in os.environ.items() if k not in env_keys}
        with patch.dict(os.environ, clean_env, clear=True):
            config = KuzuMemoryConfig.from_dict({"user": {"mode": "user"}})
        assert config.user.mode == "user"
