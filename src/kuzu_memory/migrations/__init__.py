"""
Migration system for KuzuMemory version upgrades.

This module provides a comprehensive migration framework for handling:
- Configuration file changes
- Database schema updates
- Hook configuration migrations
- Settings and preferences updates
- File/directory structure changes
- Data transformations
- Cleanup of deprecated files

Migrations are automatically discovered and run based on version numbers.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from .base import (
    CleanupMigration,
    ConfigMigration,
    HooksMigration,
    Migration,
    MigrationResult,
    MigrationType,
    SchemaMigration,
)
from .manager import MigrationHistory, MigrationManager, MigrationState

logger = logging.getLogger(__name__)


def discover_migrations() -> list[type[Migration]]:
    """
    Auto-discover all migration classes in this package.

    Scans for modules starting with 'v' (version migrations) and imports
    all Migration subclasses found within them.

    Returns:
        List of discovered migration classes
    """
    migrations = []
    package_dir = Path(__file__).parent

    # Base class names to skip (only the base classes themselves)
    base_class_names = {
        "Migration",
        "ConfigMigration",
        "SchemaMigration",
        "HooksMigration",
        "CleanupMigration",
    }

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("v"):  # Migration modules start with version
            try:
                module = importlib.import_module(f".{module_info.name}", package=__package__)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Migration)
                        and attr.__name__ not in base_class_names  # Skip only base classes
                    ):
                        migrations.append(attr)
                        logger.debug(f"Discovered migration: {attr.__name__}")
            except Exception as e:
                logger.warning(f"Failed to import migration module {module_info.name}: {e}")

    return migrations


def get_migration_manager(project_root: Path | None = None) -> MigrationManager:
    """
    Get a migration manager with all migrations registered.

    This is the recommended way to get a MigrationManager instance,
    as it automatically discovers and registers all available migrations.

    Args:
        project_root: Optional project root directory

    Returns:
        MigrationManager with all migrations registered
    """
    manager = MigrationManager(project_root=project_root)
    for migration_cls in discover_migrations():
        manager.register(migration_cls)
    return manager


__all__ = [
    "CleanupMigration",
    "ConfigMigration",
    "HooksMigration",
    "Migration",
    "MigrationHistory",
    "MigrationManager",
    "MigrationResult",
    "MigrationState",
    "MigrationType",
    "SchemaMigration",
    "discover_migrations",
    "get_migration_manager",
]
