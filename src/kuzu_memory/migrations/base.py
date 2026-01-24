"""Base migration classes for kuzu-memory upgrades."""

from __future__ import annotations

import json
import logging
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Types of migrations."""

    CONFIG = "config"  # Configuration file changes
    SCHEMA = "schema"  # Database schema changes
    HOOKS = "hooks"  # Hook configuration changes
    SETTINGS = "settings"  # User settings/preferences
    STRUCTURE = "structure"  # File/directory structure
    DATA = "data"  # Data transformations
    CLEANUP = "cleanup"  # Cleanup old files/configs


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    message: str
    changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rollback_info: dict[str, Any] | None = None


class Migration(ABC):
    """Base class for version migrations."""

    # Override in subclasses
    name: str = "unnamed_migration"
    from_version: str = "0.0.0"
    to_version: str = "999.0.0"
    migration_type: MigrationType = MigrationType.CONFIG
    priority: int = 100  # Lower = runs first (0-999)

    def __init__(self, project_root: Path | None = None) -> None:
        """
        Initialize migration.

        Args:
            project_root: Project root directory (defaults to current directory)
        """
        self.project_root = project_root or Path.cwd()
        self._backup_files: list[Path] = []

    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this migration."""
        pass

    @abstractmethod
    def check_applicable(self) -> bool:
        """Check if this migration should run (beyond version check)."""
        pass

    @abstractmethod
    def migrate(self) -> MigrationResult:
        """Run the migration. Return MigrationResult."""
        pass

    def rollback(self) -> bool:
        """
        Rollback the migration if possible.

        Returns:
            True if successful, False otherwise
        """
        # Default: restore backed up files
        try:
            for backup_path in self._backup_files:
                if not backup_path.exists():
                    continue

                original = backup_path.with_suffix("")  # Remove .bak
                if backup_path.name.endswith(".bak"):
                    # Restore original
                    shutil.copy2(backup_path, original)
                    backup_path.unlink()

            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    # Helper methods for common operations

    def backup_file(self, file_path: Path) -> Path:
        """
        Create a backup of a file before modifying.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file
        """
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        if file_path.exists():
            shutil.copy2(file_path, backup_path)
            self._backup_files.append(backup_path)
        return backup_path

    def read_json(self, file_path: Path) -> dict[str, Any]:
        """
        Safely read a JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data or empty dict if file doesn't exist
        """
        if file_path.exists():
            data: dict[str, Any] = json.loads(file_path.read_text())
            return data
        return {}

    def write_json(self, file_path: Path, data: dict[str, Any], backup: bool = True) -> None:
        """
        Safely write a JSON file with optional backup.

        Args:
            file_path: Path to JSON file
            data: Data to write
            backup: Whether to backup existing file
        """
        if backup and file_path.exists():
            self.backup_file(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2))

    def ensure_directory(self, dir_path: Path) -> bool:
        """
        Ensure a directory exists.

        Args:
            dir_path: Directory to create

        Returns:
            True if directory exists after call
        """
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path.exists()

    def move_file(self, src: Path, dst: Path, backup: bool = True) -> bool:
        """
        Move a file with optional backup of destination.

        Args:
            src: Source file path
            dst: Destination file path
            backup: Whether to backup existing destination

        Returns:
            True if successful, False otherwise
        """
        if backup and dst.exists():
            self.backup_file(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.move(str(src), str(dst))
            return True
        return False


class ConfigMigration(Migration):
    """Base class for configuration file migrations."""

    migration_type = MigrationType.CONFIG
    config_file: str = ""  # Override: relative path to config file

    def get_config_path(self) -> Path:
        """
        Get the full path to the config file.

        Returns:
            Path to configuration file
        """
        return self.project_root / self.config_file

    def check_applicable(self) -> bool:
        """
        Config migrations apply if the config file exists.

        Returns:
            True if config file exists, False otherwise
        """
        return self.get_config_path().exists()


class SchemaMigration(Migration):
    """Base class for database schema migrations."""

    migration_type = MigrationType.SCHEMA

    def check_applicable(self) -> bool:
        """
        Schema migrations apply if the database exists.

        Returns:
            True if database exists, False otherwise
        """
        db_path = self.project_root / ".kuzu-memory" / "memories.db"
        return db_path.exists()

    def execute_cypher(self, query: str) -> bool:
        """
        Execute a Cypher query against the database.

        Args:
            query: Cypher query string

        Returns:
            True if successful, False otherwise
        """
        try:
            from ..core.memory import KuzuMemory

            db_path = self.project_root / ".kuzu_memory.db"
            with KuzuMemory(db_path=db_path, enable_git_sync=False, auto_sync=False) as memory:
                memory.db_adapter.execute(query)
            return True
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return False


class HooksMigration(Migration):
    """Base class for hooks configuration migrations."""

    migration_type = MigrationType.HOOKS

    def get_hooks_config_paths(self) -> list[Path]:
        """
        Get all possible hooks configuration paths.

        Returns:
            List of paths to check for hooks configuration
        """
        return [
            Path.home() / ".claude" / "settings.json",
            self.project_root / ".claude" / "settings.json",
        ]

    def check_applicable(self) -> bool:
        """
        Hooks migrations apply if any hooks config exists.

        Returns:
            True if any hooks config exists, False otherwise
        """
        return any(p.exists() for p in self.get_hooks_config_paths())


class CleanupMigration(Migration):
    """Base class for cleanup migrations (removing old files/configs)."""

    migration_type = MigrationType.CLEANUP
    priority = 900  # Cleanup runs last

    def check_applicable(self) -> bool:
        """
        Override to check if cleanup targets exist.

        Returns:
            True by default (check in subclass)
        """
        return True
