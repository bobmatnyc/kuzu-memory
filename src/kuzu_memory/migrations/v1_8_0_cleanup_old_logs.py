"""Cleanup migration to remove old log files."""

from __future__ import annotations

import shutil
from pathlib import Path

from .base import CleanupMigration, MigrationResult


class CleanupOldLogsMigration(CleanupMigration):
    """Remove old log files from deprecated locations."""

    name = "cleanup_old_logs_v1.8.0"
    from_version = "1.8.0"
    to_version = "999.0.0"

    def description(self) -> str:
        """Return migration description."""
        return "Clean up old log files from deprecated locations"

    def check_applicable(self) -> bool:
        """Check if old log directories exist."""
        old_paths = [
            self.project_root / ".kuzu-memory" / "logs",
            Path("/tmp/kuzu-memory-hooks"),
        ]
        return any(p.exists() for p in old_paths)

    def migrate(self) -> MigrationResult:
        """Remove old log directories and files."""
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

        if changes:
            return MigrationResult(
                success=True,
                message=f"Cleaned up {len(changes)} old paths",
                changes=changes,
            )
        else:
            return MigrationResult(
                success=True,
                message="No old paths found to clean up",
                changes=[],
            )
