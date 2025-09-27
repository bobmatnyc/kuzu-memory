#!/usr/bin/env python3
"""
KuzuMemory Database Consolidation Script

Consolidates multiple database locations into the standardized .kuzu_memory/ location.
Handles data migration and validation to resolve dual database location issues.

Usage:
    python scripts/consolidate-databases.py [--dry-run] [--backup]

Options:
    --dry-run    Show what would be done without making changes
    --backup     Create backup before consolidation (recommended)
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple


class DatabaseConsolidator:
    """Handles consolidation of KuzuMemory database locations."""

    def __init__(self, project_root: Path, dry_run: bool = False, backup: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.backup = backup

        # Define database locations
        self.primary_db = project_root / ".kuzu_memory"
        self.legacy_db = project_root / "kuzu-memories"
        self.test_db = project_root / ".test_kuzu_memory"
        self.backup_dir = project_root / ".kuzu-memory-backups"

        # Ensure backup directory exists
        if self.backup and not self.dry_run:
            self.backup_dir.mkdir(exist_ok=True)

    def analyze_databases(self) -> List[Tuple[Path, bool, int]]:
        """Analyze existing database locations and return status."""
        databases = []

        for db_path in [self.primary_db, self.legacy_db, self.test_db]:
            exists = db_path.exists()
            size = 0

            if exists:
                try:
                    # Count files to estimate database size
                    size = len(list(db_path.rglob("*"))) if db_path.is_dir() else 1
                except PermissionError:
                    size = -1  # Indicates permission issue

            databases.append((db_path, exists, size))

        return databases

    def create_backup(self, source: Path, backup_name: str) -> Path:
        """Create backup of database directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{backup_name}_{timestamp}"

        if not self.dry_run:
            print(f"Creating backup: {source} -> {backup_path}")
            shutil.copytree(source, backup_path)
        else:
            print(f"[DRY RUN] Would create backup: {source} -> {backup_path}")

        return backup_path

    def consolidate_database(self, source: Path, target: Path) -> bool:
        """Consolidate source database into target location."""
        if not source.exists():
            print(f"Source database does not exist: {source}")
            return False

        if target.exists():
            if self.backup:
                self.create_backup(target, "primary_db_backup")

            if not self.dry_run:
                print(f"Removing existing target database: {target}")
                shutil.rmtree(target)
            else:
                print(f"[DRY RUN] Would remove existing target: {target}")

        if not self.dry_run:
            print(f"Moving database: {source} -> {target}")
            shutil.move(str(source), str(target))
        else:
            print(f"[DRY RUN] Would move: {source} -> {target}")

        return True

    def validate_consolidation(self) -> bool:
        """Validate that consolidation was successful."""
        if self.dry_run:
            print("[DRY RUN] Validation would check database integrity")
            return True

        if not self.primary_db.exists():
            print("ERROR: Primary database does not exist after consolidation")
            return False

        # Check for leftover databases
        leftover_dbs = []
        if self.legacy_db.exists():
            leftover_dbs.append(self.legacy_db)

        if leftover_dbs:
            print(f"WARNING: Leftover databases found: {leftover_dbs}")
            return False

        print("✅ Database consolidation validation successful")
        return True

    def run_consolidation(self) -> bool:
        """Execute the full consolidation process."""
        print("KuzuMemory Database Consolidation")
        print("=" * 40)

        # Analyze current state
        databases = self.analyze_databases()

        print("Current database locations:")
        for db_path, exists, size in databases:
            status = f"EXISTS ({size} files)" if exists else "NOT FOUND"
            print(f"  {db_path.name}: {status}")

        print()

        # Determine consolidation strategy
        primary_exists = self.primary_db.exists()
        legacy_exists = self.legacy_db.exists()

        if not primary_exists and not legacy_exists:
            print("No databases found to consolidate.")
            return True

        if legacy_exists:
            if primary_exists:
                print("Both primary and legacy databases exist.")
                print("Strategy: Backup primary, consolidate legacy into primary")

                if self.backup:
                    self.create_backup(self.primary_db, "primary_db_pre_consolidation")

                # Remove primary to make way for legacy
                if not self.dry_run:
                    shutil.rmtree(self.primary_db)
                else:
                    print(f"[DRY RUN] Would remove primary database")

            # Move legacy to primary
            success = self.consolidate_database(self.legacy_db, self.primary_db)
            if not success:
                return False

        # Clean up test database if it exists
        if self.test_db.exists():
            if self.backup:
                self.create_backup(self.test_db, "test_db_backup")

            if not self.dry_run:
                print(f"Removing test database: {self.test_db}")
                shutil.rmtree(self.test_db)
            else:
                print(f"[DRY RUN] Would remove test database: {self.test_db}")

        # Validate consolidation
        return self.validate_consolidation()


def main():
    """Main entry point for database consolidation."""
    parser = argparse.ArgumentParser(description="Consolidate KuzuMemory databases")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--no-backup", action="store_true",
                       help="Skip creating backups (not recommended)")

    args = parser.parse_args()

    # Find project root
    script_path = Path(__file__).parent
    project_root = script_path.parent

    # Validate we're in the right location
    if not (project_root / "pyproject.toml").exists():
        print("ERROR: Could not find project root (pyproject.toml not found)")
        sys.exit(1)

    # Create consolidator and run
    consolidator = DatabaseConsolidator(
        project_root=project_root,
        dry_run=args.dry_run,
        backup=not args.no_backup
    )

    try:
        success = consolidator.run_consolidation()
        if success:
            print("\n✅ Database consolidation completed successfully")
            if not args.dry_run:
                print("\nNext steps:")
                print("1. Test database functionality: kuzu-memory stats")
                print("2. Verify data integrity: kuzu-memory recall <test-query>")
                print("3. Update configuration if needed")
        else:
            print("\n❌ Database consolidation failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error during consolidation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()