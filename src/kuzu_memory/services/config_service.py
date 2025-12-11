"""ConfigService implementation - project configuration management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kuzu_memory.services.base import BaseService
from kuzu_memory.utils.project_setup import (
    create_project_memories_structure,
    find_project_root,
    get_project_context_summary,
    get_project_db_path,
    get_project_memories_dir,
)


class ConfigService(BaseService):
    """
    Service layer for configuration management.

    Provides centralized access to project configuration including:
    - Project root detection
    - Database path resolution
    - Configuration file management
    - Environment variable integration

    Design Pattern: Caching Wrapper
    - Caches project root and config for performance
    - Delegates to utils/project_setup.py for core logic
    - Maintains backward compatibility with existing utilities

    Design Decision: Delegation vs. Reimplementation
    -------------------------------------------------
    Rationale: ConfigService delegates to existing utils/project_setup.py
    functions rather than reimplementing them. This maintains the single
    source of truth for project detection logic while providing a service
    layer interface.

    Trade-offs:
    - Code Reuse: Avoids duplicating project detection logic
    - Maintainability: Changes to detection logic only happen in one place
    - Performance: Adds caching layer on top of utilities
    - Migration Path: Existing code can gradually migrate to service

    Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
    Related Task: 1M-421 (Implement ConfigService)
    """

    def __init__(self, project_root: Path | None = None):
        """
        Initialize ConfigService.

        Args:
            project_root: Optional explicit project root (auto-detected if None)
        """
        super().__init__()
        self._explicit_root = project_root
        self._project_root: Path | None = None
        self._config_cache: dict[str, Any] | None = None

    def _do_initialize(self) -> None:
        """Initialize project root and config."""
        if self._explicit_root:
            self._project_root = self._explicit_root
        else:
            self._project_root = find_project_root()

        self.logger.info(f"ConfigService initialized with project_root={self._project_root}")

    def _do_cleanup(self) -> None:
        """Cleanup resources."""
        self._project_root = None
        self._config_cache = None
        self.logger.info("ConfigService cleaned up")

    # IConfigService protocol implementation

    def get_project_root(self) -> Path:
        """
        Get the project root directory.

        Returns:
            Path to project root directory

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._project_root:
            raise RuntimeError("ConfigService not initialized")
        return self._project_root

    def get_db_path(self) -> Path:
        """
        Get the database path.

        Returns:
            Path to Kuzu database directory

        Default: <project_root>/kuzu-memories/memories.db
        """
        return get_project_db_path(self.get_project_root())

    def load_config(self) -> dict[str, Any]:
        """
        Load configuration from disk.

        Searches for config.json in project root/.kuzu-memory/ directory.
        Returns cached config if already loaded.

        Returns:
            Dictionary of all configuration values

        Error Handling: Returns empty dict if config file doesn't exist
        """
        if self._config_cache is not None:
            return self._config_cache

        config_path = self.get_project_root() / ".kuzu-memory" / "config.json"

        if not config_path.exists():
            self.logger.debug(f"No config file at {config_path}, returning defaults")
            self._config_cache = {}
            return self._config_cache

        try:
            with open(config_path, encoding="utf-8") as f:
                self._config_cache = json.load(f)
            self.logger.info(f"Loaded config from {config_path}")
            return self._config_cache
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_path}: {e}")
            self._config_cache = {}
            return self._config_cache

    def save_config(self, config: dict[str, Any]) -> None:
        """
        Save configuration to disk.

        Args:
            config: Configuration dictionary to save

        Raises:
            IOError: If unable to write config file
        """
        config_dir = self.get_project_root() / ".kuzu-memory"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_path = config_dir / "config.json"

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self._config_cache = config
            self.logger.info(f"Saved config to {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save config to {config_path}: {e}")
            raise

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific config value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get_config_value("database.path", "/default/path")
            >>> config.get_config_value("api.timeout", 30)
        """
        config = self.load_config()

        # Support dot notation (e.g., "database.path")
        keys = key.split(".")
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    # Additional utility methods (beyond protocol)

    def get_memories_dir(self) -> Path:
        """
        Get the project memories directory.

        Returns:
            Path to kuzu-memories directory
        """
        return get_project_memories_dir(self.get_project_root())

    def ensure_project_structure(self) -> None:
        """
        Ensure project memory structure exists.

        Creates kuzu-memories directory, README, .gitignore, and project_info.md
        if they don't already exist.

        Raises:
            Exception: If unable to create project structure
        """
        create_project_memories_structure(self.get_project_root())

    def get_project_context(self) -> dict[str, Any]:
        """
        Get project context summary.

        Returns:
            Dictionary with project information:
            - project_name: str
            - project_root: str
            - memories_dir: str
            - db_path: str
            - memories_exist: bool
            - db_exists: bool
            - is_git_repo: bool
            - should_commit: bool
            - db_size_mb: float
        """
        return get_project_context_summary(self.get_project_root())
