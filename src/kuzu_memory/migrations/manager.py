"""Enhanced migration manager for version upgrades."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from packaging import version

from .base import Migration, MigrationResult, MigrationType

logger = logging.getLogger(__name__)


@dataclass
class MigrationHistory:
    """Record of a completed migration."""

    name: str
    version: str
    migration_type: str
    timestamp: str
    success: bool
    message: str
    changes: list[str] = field(default_factory=list)


@dataclass
class MigrationState:
    """Persistent state for migrations."""

    last_version: str = "0.0.0"
    history: list[MigrationHistory] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "last_version": self.last_version,
            "history": [
                {
                    "name": h.name,
                    "version": h.version,
                    "migration_type": h.migration_type,
                    "timestamp": h.timestamp,
                    "success": h.success,
                    "message": h.message,
                    "changes": h.changes,
                }
                for h in self.history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> MigrationState:
        """
        Create from dictionary.

        Args:
            data: Dictionary with migration state

        Returns:
            MigrationState instance
        """
        history = [MigrationHistory(**h) for h in data.get("history", [])]
        return cls(
            last_version=data.get("last_version", "0.0.0"),
            history=history,
        )


class MigrationManager:
    """Manages version migrations on startup."""

    STATE_FILE = ".kuzu-memory/migration_state.json"

    def __init__(self, project_root: Path | None = None) -> None:
        """
        Initialize migration manager.

        Args:
            project_root: Project root directory (defaults to current directory)
        """
        self.project_root = project_root or Path.cwd()
        self.state_file = self.project_root / self.STATE_FILE
        self._migrations: list[type[Migration]] = []
        self._state: MigrationState | None = None

    def register(self, migration_class: type[Migration]) -> MigrationManager:
        """
        Register a migration class.

        Args:
            migration_class: Migration class to register

        Returns:
            Self for method chaining
        """
        self._migrations.append(migration_class)
        return self

    def register_all(self, *migration_classes: type[Migration]) -> MigrationManager:
        """
        Register multiple migration classes.

        Args:
            migration_classes: Migration classes to register

        Returns:
            Self for method chaining
        """
        for cls in migration_classes:
            self.register(cls)
        return self

    @property
    def state(self) -> MigrationState:
        """
        Get or load the migration state.

        Returns:
            Current migration state
        """
        if self._state is None:
            self._state = self._load_state()
        return self._state

    def _load_state(self) -> MigrationState:
        """
        Load migration state from disk.

        Returns:
            Migration state (or default if not found)
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return MigrationState.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load migration state: {e}")
        return MigrationState()

    def _save_state(self) -> None:
        """Save migration state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state.to_dict(), indent=2))

    def get_last_version(self) -> str:
        """
        Get the last migrated version.

        Returns:
            Version string of last migration, or "0.0.0" if none
        """
        return self.state.last_version

    def set_version(self, ver: str) -> None:
        """
        Record the current version.

        Args:
            ver: Version string to record
        """
        self.state.last_version = ver
        self._save_state()

    def get_pending_migrations(self, target_version: str) -> list[Migration]:
        """
        Get migrations that need to run.

        Args:
            target_version: Target version to migrate to

        Returns:
            List of pending migration instances
        """
        last_ver = version.parse(self.state.last_version)
        target_ver = version.parse(target_version)

        pending = []
        completed_names = {h.name for h in self.state.history if h.success}

        for migration_cls in self._migrations:
            m = migration_cls(project_root=self.project_root)
            from_ver = version.parse(m.from_version)
            to_ver = version.parse(m.to_version)

            # Skip if already run
            if m.name in completed_names:
                continue

            # Check version range
            if target_ver >= from_ver and last_ver < to_ver:
                # Check if applicable
                if m.check_applicable():
                    pending.append(m)

        # Sort by priority (lower first), then by from_version
        pending.sort(key=lambda m: (m.priority, version.parse(m.from_version)))
        return pending

    def run_migrations(
        self,
        target_version: str,
        dry_run: bool = False,
        migration_types: list[MigrationType] | None = None,
    ) -> list[MigrationResult]:
        """
        Run all applicable migrations.

        Args:
            target_version: Version to migrate to
            dry_run: If True, only report what would run
            migration_types: Optional filter for specific migration types

        Returns:
            List of migration results
        """
        pending = self.get_pending_migrations(target_version)

        # Filter by type if specified
        if migration_types:
            pending = [m for m in pending if m.migration_type in migration_types]

        if not pending:
            return []

        results = []
        for migration in pending:
            if dry_run:
                results.append(
                    MigrationResult(
                        success=True,
                        message=f"[DRY RUN] Would run: {migration.description()}",
                        changes=[],
                    )
                )
                continue

            logger.info(f"Running migration: {migration.name} - {migration.description()}")

            try:
                result = migration.migrate()

                # Record in history
                history_entry = MigrationHistory(
                    name=migration.name,
                    version=migration.from_version,
                    migration_type=migration.migration_type.value,
                    timestamp=datetime.now().isoformat(),
                    success=result.success,
                    message=result.message,
                    changes=result.changes,
                )
                self.state.history.append(history_entry)
                results.append(result)

                if not result.success:
                    logger.warning(f"Migration {migration.name} failed: {result.message}")
                    # Attempt rollback
                    if migration.rollback():
                        logger.info(f"Rollback successful for {migration.name}")

            except Exception as e:
                logger.error(f"Migration {migration.name} error: {e}")
                results.append(
                    MigrationResult(
                        success=False,
                        message=f"Error: {e}",
                    )
                )

        # Update version and save state
        self.state.last_version = target_version
        self._save_state()

        return results

    def get_history(self, limit: int = 10) -> list[MigrationHistory]:
        """
        Get recent migration history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of recent migration history entries
        """
        return self.state.history[-limit:]

    def reset_state(self) -> None:
        """Reset migration state (for testing)."""
        self._state = MigrationState()
        if self.state_file.exists():
            self.state_file.unlink()
