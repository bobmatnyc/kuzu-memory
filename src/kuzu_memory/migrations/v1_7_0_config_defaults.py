"""Migration to add new config defaults for v1.7.0."""

from __future__ import annotations

from .base import ConfigMigration, MigrationResult


class ConfigDefaultsMigration(ConfigMigration):
    """Add new configuration defaults."""

    name = "config_defaults_v1.7.0"
    from_version = "1.7.0"
    to_version = "999.0.0"
    config_file = ".kuzu-memory/config.json"
    priority = 50  # Run before hooks migration

    def description(self) -> str:
        """Return migration description."""
        return "Add new configuration defaults (queue_dir, use_bash_hooks)"

    def migrate(self) -> MigrationResult:
        """Add new config defaults if not present."""
        config_path = self.get_config_path()
        config = self.read_json(config_path) if config_path.exists() else {}

        changes = []

        # Add new defaults if not present
        if "queue_dir" not in config:
            config["queue_dir"] = "/tmp/kuzu-memory-queue"
            changes.append("Added queue_dir setting")

        if "hooks" not in config:
            config["hooks"] = {}

        if "use_bash_hooks" not in config["hooks"]:
            config["hooks"]["use_bash_hooks"] = True
            changes.append("Enabled bash hooks by default")

        if changes:
            self.write_json(config_path, config)
            return MigrationResult(
                success=True,
                message=f"Updated config with {len(changes)} new defaults",
                changes=changes,
            )
        else:
            return MigrationResult(
                success=True,
                message="Config already up to date",
                changes=[],
            )
