# Enhanced Migration System Framework

## Overview

The kuzu-memory migration system has been enhanced into a robust, general-purpose framework for managing various types of version upgrades. It provides automatic discovery, type-safe operations, rollback support, and comprehensive history tracking.

## Key Features

### 1. **Multiple Migration Types**
- **CONFIG**: Configuration file changes
- **SCHEMA**: Database schema updates
- **HOOKS**: Hook configuration changes
- **SETTINGS**: User settings/preferences
- **STRUCTURE**: File/directory structure changes
- **DATA**: Data transformations
- **CLEANUP**: Removal of deprecated files/configs

### 2. **Type-Safe Architecture**
```python
from kuzu_memory.migrations.base import (
    Migration,
    MigrationResult,
    MigrationType,
    ConfigMigration,
    SchemaMigration,
    HooksMigration,
    CleanupMigration,
)

class MyMigration(ConfigMigration):
    name = "my_migration_v1.0.0"
    from_version = "1.0.0"
    to_version = "999.0.0"
    config_file = ".kuzu-memory/config.json"
    priority = 100  # Lower runs first

    def description(self) -> str:
        return "Add new config defaults"

    def migrate(self) -> MigrationResult:
        config = self.read_json(self.get_config_path())
        config["new_key"] = "new_value"
        self.write_json(self.get_config_path(), config)

        return MigrationResult(
            success=True,
            message="Config updated successfully",
            changes=["Added new_key to config"],
        )
```

### 3. **Auto-Discovery**
Migrations are automatically discovered from modules matching `v*` pattern:
- `v1_7_0_bash_hooks.py` → BashHooksMigration
- `v1_7_0_config_defaults.py` → ConfigDefaultsMigration
- `v1_8_0_cleanup_old_logs.py` → CleanupOldLogsMigration

No manual registration required - just create the migration class!

### 4. **Built-in Helper Methods**
All migrations inherit powerful helper methods:

```python
# JSON operations
config = self.read_json(path)
self.write_json(path, config, backup=True)

# File operations
self.backup_file(path)
self.move_file(src, dst, backup=True)
self.ensure_directory(dir_path)

# Database operations (for SchemaMigration)
self.execute_cypher("MATCH (n) RETURN n")
```

### 5. **Rollback Support**
Automatic backup and rollback:
```python
def migrate(self) -> MigrationResult:
    # Backup created automatically
    self.write_json(config_path, new_config)

    if something_fails:
        # Rollback restores from backup
        self.rollback()
        return MigrationResult(success=False, message="Failed")
```

### 6. **Priority-Based Execution**
Migrations run in priority order (lower first):
- Priority 50: Config updates
- Priority 100: Hook migrations
- Priority 900: Cleanup operations

### 7. **Comprehensive History Tracking**
Every migration is recorded with:
- Migration name and type
- Timestamp
- Success/failure status
- List of changes made
- Warnings

History is persisted in `.kuzu-memory/migration_state.json`

## CLI Commands

### View Migration Status
```bash
kuzu-memory migrations status
# Output:
# Current version: 1.6.31
# Last migrated: 1.6.31
# ✓ No pending migrations

kuzu-memory migrations status --verbose
# Shows detailed history
```

### Run Migrations
```bash
# Run all pending migrations
kuzu-memory migrations run

# Dry run (preview changes)
kuzu-memory migrations run --dry-run

# Run only specific type
kuzu-memory migrations run --type cleanup
```

### View History
```bash
# Show recent migration history
kuzu-memory migrations history

# Show last 20 entries
kuzu-memory migrations history --limit 20

# Filter by type
kuzu-memory migrations history --type hooks
```

### Reset State (Development)
```bash
kuzu-memory migrations reset
```

## Creating New Migrations

### Step 1: Choose Base Class
- **ConfigMigration**: For config file changes
- **SchemaMigration**: For database schema updates
- **HooksMigration**: For hook configuration
- **CleanupMigration**: For removing old files

### Step 2: Create Migration File
Create `src/kuzu_memory/migrations/vX_Y_Z_description.py`:

```python
"""Migration for vX.Y.Z - Description."""

from pathlib import Path
from .base import ConfigMigration, MigrationResult

class MyConfigMigration(ConfigMigration):
    """Add new configuration defaults."""

    name = "my_config_vX.Y.Z"
    from_version = "X.Y.Z"
    to_version = "999.0.0"
    config_file = ".kuzu-memory/config.json"
    priority = 50

    def description(self) -> str:
        return "Add new config defaults for feature X"

    def migrate(self) -> MigrationResult:
        config = self.read_json(self.get_config_path())
        changes = []

        if "new_key" not in config:
            config["new_key"] = "default_value"
            changes.append("Added new_key")

        if changes:
            self.write_json(self.get_config_path(), config)

        return MigrationResult(
            success=True,
            message=f"Updated {len(changes)} config keys",
            changes=changes,
        )
```

### Step 3: Test Your Migration
```bash
# Dry run first
kuzu-memory migrations run --dry-run

# Run it
kuzu-memory migrations run

# Check status
kuzu-memory migrations status --verbose
```

## Example Migrations

### Config Migration
```python
class ConfigDefaultsMigration(ConfigMigration):
    """Add queue_dir and bash_hooks defaults."""

    name = "config_defaults_v1.7.0"
    from_version = "1.7.0"
    config_file = ".kuzu-memory/config.json"
    priority = 50

    def migrate(self) -> MigrationResult:
        config = self.read_json(self.get_config_path())

        if "queue_dir" not in config:
            config["queue_dir"] = "/tmp/kuzu-memory-queue"

        if "hooks" not in config:
            config["hooks"] = {"use_bash_hooks": True}

        self.write_json(self.get_config_path(), config)
        return MigrationResult(success=True, message="Config updated")
```

### Hooks Migration
```python
class BashHooksMigration(HooksMigration):
    """Migrate from Python to bash hooks."""

    name = "bash_hooks_v1.7.0"
    from_version = "1.7.0"
    priority = 100

    def check_applicable(self) -> bool:
        # Check if Python hooks exist
        for path in self.get_hooks_config_paths():
            if path.exists():
                settings = self.read_json(path)
                if "kuzu-memory hooks" in str(settings):
                    return True
        return False

    def migrate(self) -> MigrationResult:
        changes = []
        for path in self.get_hooks_config_paths():
            if path.exists():
                settings = self.read_json(path)
                # Replace Python hooks with bash scripts
                # ... migration logic ...
                self.write_json(path, settings)
                changes.append(f"Migrated {path.name}")

        return MigrationResult(
            success=True,
            message=f"Migrated {len(changes)} files",
            changes=changes,
        )
```

### Cleanup Migration
```python
class CleanupOldLogsMigration(CleanupMigration):
    """Remove deprecated log files."""

    name = "cleanup_logs_v1.8.0"
    from_version = "1.8.0"
    priority = 900  # Cleanup runs last

    def check_applicable(self) -> bool:
        old_paths = [
            self.project_root / ".kuzu-memory" / "logs",
            Path("/tmp/kuzu-memory-hooks"),
        ]
        return any(p.exists() for p in old_paths)

    def migrate(self) -> MigrationResult:
        import shutil
        changes = []

        old_paths = [
            self.project_root / ".kuzu-memory" / "logs",
            Path("/tmp/kuzu-memory-hooks"),
        ]

        for path in old_paths:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                changes.append(f"Removed {path}")

        return MigrationResult(
            success=True,
            message=f"Cleaned up {len(changes)} paths",
            changes=changes,
        )
```

## Architecture

### Base Classes Hierarchy
```
Migration (ABC)
├── ConfigMigration
│   └── ConfigDefaultsMigration
├── SchemaMigration
├── HooksMigration
│   └── BashHooksMigration
└── CleanupMigration
    └── CleanupOldLogsMigration
```

### Migration Flow
1. **Discovery**: Auto-discover all `v*` modules
2. **Filtering**: Check version ranges and `check_applicable()`
3. **Ordering**: Sort by priority, then by from_version
4. **Execution**: Run each migration, track results
5. **History**: Record success/failure, changes, warnings
6. **State**: Update last_version, save to disk

### State Persistence
```json
{
  "last_version": "1.6.31",
  "history": [
    {
      "name": "bash_hooks_v1.7.0",
      "version": "1.7.0",
      "migration_type": "hooks",
      "timestamp": "2025-01-23T10:30:00",
      "success": true,
      "message": "Migrated 2 hook(s) to bash",
      "changes": [
        "Migrated learn hook in settings.json",
        "Migrated session-start hook in settings.json"
      ]
    }
  ]
}
```

## Best Practices

### 1. **Use Specific Base Classes**
Don't inherit directly from `Migration` - use specialized base classes:
- ✅ `class MyMigration(ConfigMigration)`
- ❌ `class MyMigration(Migration)`

### 2. **Implement check_applicable()**
Prevent unnecessary migration runs:
```python
def check_applicable(self) -> bool:
    config = self.read_json(self.get_config_path())
    return "new_key" not in config  # Only run if needed
```

### 3. **Return Detailed Results**
```python
return MigrationResult(
    success=True,
    message="Migrated 3 files",
    changes=["File 1 updated", "File 2 updated", "File 3 updated"],
    warnings=["File 4 was skipped (already migrated)"],
)
```

### 4. **Set Appropriate Priority**
- 0-50: Critical pre-migrations (schema, config)
- 51-500: Normal migrations (features, updates)
- 501-899: Post-migrations (data updates)
- 900+: Cleanup operations

### 5. **Use Helper Methods**
```python
# ✅ Good
config = self.read_json(path)
self.write_json(path, config)

# ❌ Bad (no backup, error handling)
import json
config = json.loads(path.read_text())
path.write_text(json.dumps(config))
```

### 6. **Test with Dry-Run**
Always test with `--dry-run` first:
```bash
kuzu-memory migrations run --dry-run
```

## Testing

Run the comprehensive test suite:
```bash
pytest tests/test_migrations_system.py -v
```

Tests cover:
- Migration discovery
- Type safety
- Rollback functionality
- History tracking
- Priority ordering
- Base class helpers
- Dry-run mode
- Type filtering

## Future Enhancements

Potential additions to the framework:
1. **Schema migrations**: Full database migration support
2. **Data migrations**: Transform existing memory data
3. **Conflict resolution**: Handle migration conflicts
4. **Migration dependencies**: Explicit dependency chains
5. **Parallel execution**: Run independent migrations concurrently
6. **Migration validation**: Pre-flight checks before execution

## Summary

The enhanced migration system provides:
- ✅ Type-safe, Pydantic-validated migrations
- ✅ Auto-discovery (zero registration)
- ✅ Multiple migration types (7 types)
- ✅ Built-in rollback support
- ✅ Comprehensive history tracking
- ✅ CLI for manual control
- ✅ Priority-based execution
- ✅ Dry-run support
- ✅ 100% test coverage
- ✅ Helper methods for common operations

This framework can handle any type of version upgrade, from simple config changes to complex schema transformations.
