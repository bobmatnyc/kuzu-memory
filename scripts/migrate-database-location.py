#!/usr/bin/env python3
"""
Migrate KuzuMemory database to new standardized location.

Moves databases from old locations to ~/.kuzu-memory/memories.db
"""

import shutil
import sys
from pathlib import Path


def migrate_databases():
    """Migrate databases to new location."""
    # New standard location
    new_dir = Path.home() / ".kuzu-memory"
    new_db = new_dir / "memories.db"

    # Old locations to check
    old_locations = [
        Path(".kuzu_memory/memories.db"),  # Old local default
        Path("kuzu-memories/memories.db"),  # Project location
    ]

    print("🔄 KuzuMemory Database Migration v1.1.2")
    print(f"📍 Target location: {new_db}")
    print()

    # Check if new location already exists
    if new_db.exists():
        size_mb = new_db.stat().st_size / (1024 * 1024)
        print(f"✅ Database already exists at new location ({size_mb:.2f} MB)")
        return

    # Create new directory
    new_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created directory: {new_dir}")

    # Find existing databases
    found_dbs = []
    for old_path in old_locations:
        if old_path.exists():
            size_mb = old_path.stat().st_size / (1024 * 1024)
            found_dbs.append((old_path, size_mb))
            print(f"📁 Found database: {old_path} ({size_mb:.2f} MB)")

    if not found_dbs:
        print("ℹ️  No existing databases found to migrate")
        return

    # Choose the largest database (likely has the most memories)
    found_dbs.sort(key=lambda x: x[1], reverse=True)
    source_db, size_mb = found_dbs[0]

    print()
    print(f"🚀 Migrating: {source_db} → {new_db}")

    # Copy the database
    try:
        shutil.copy2(source_db, new_db)
        print(f"✅ Successfully migrated {size_mb:.2f} MB database")

        # Create backup of old location
        backup_name = f"{source_db}.backup"
        shutil.move(source_db, backup_name)
        print(f"📦 Old database backed up to: {backup_name}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

    print()
    print("✨ Migration complete!")
    print("Your memories are now at:", new_db)

    # Also migrate config if it exists
    old_config_locations = [
        Path(".kuzu_memory/config.yaml"),
        Path(".kuzu_memory/config.yml"),
    ]

    for old_config in old_config_locations:
        if old_config.exists():
            new_config = new_dir / old_config.name
            if not new_config.exists():
                shutil.copy2(old_config, new_config)
                print(f"📋 Migrated config: {old_config} → {new_config}")


if __name__ == "__main__":
    migrate_databases()