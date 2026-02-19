"""Migration to bash hooks for v1.7.0."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from .base import HooksMigration, MigrationResult

logger = logging.getLogger(__name__)


class BashHooksMigration(HooksMigration):
    """
    Migrate from Python hooks to bash hooks.

    This migration replaces slow Python hooks (~800ms) with fast bash hooks (~20ms)
    in Claude Code settings files.
    """

    name = "bash_hooks_v1.7.0"
    from_version = "1.7.0"
    to_version = "999.0.0"  # Always applicable from 1.7.0 onwards
    priority = 100

    def description(self) -> str:
        """Return migration description."""
        return "Upgrade to fast bash hooks (40x faster startup)"

    def check_applicable(self) -> bool:
        """Check if migration should run."""
        # Check if any settings files exist with Python hooks
        for settings_path in self._get_settings_paths():
            if settings_path.exists():
                try:
                    settings = json.loads(settings_path.read_text())
                    hooks = settings.get("hooks", {})
                    for _event, hook_list in hooks.items():
                        if not isinstance(hook_list, list):
                            continue
                        for hook in hook_list:
                            if not isinstance(hook, dict):
                                continue
                            cmd = hook.get("command", "")
                            if "kuzu-memory hooks" in cmd and ".sh" not in cmd:
                                return True  # Found Python hook
                except Exception:
                    pass
        return False

    def migrate(self) -> MigrationResult:
        """Replace Python hooks with bash hooks in Claude settings."""
        changes: list[str] = []

        for settings_path in self._get_settings_paths():
            if settings_path.exists():
                result = self._migrate_settings(settings_path)
                if result:
                    changes.extend(result)

        if changes:
            return MigrationResult(
                success=True,
                message=f"Migrated {len(changes)} hook(s) to bash",
                changes=changes,
            )
        else:
            return MigrationResult(
                success=True,
                message="No Python hooks found to migrate",
                changes=[],
                warnings=["No migration needed - hooks already using bash"],
            )

    def _get_settings_paths(self) -> list[Path]:
        """Get all possible Claude settings paths."""
        return [
            Path.home() / ".claude" / "settings.json",
            Path.home() / ".claude" / "settings.local.json",
            Path.cwd() / ".claude" / "settings.json",
            Path.cwd() / ".claude" / "settings.local.json",
        ]

    def _migrate_settings(self, settings_path: Path) -> list[str]:
        """
        Migrate a single settings file.

        Args:
            settings_path: Path to Claude Code settings file

        Returns:
            List of changes made
        """
        changes = []
        try:
            settings = json.loads(settings_path.read_text())
            hooks = settings.get("hooks", {})

            for _event, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    continue

                for hook in hook_list:
                    if not isinstance(hook, dict):
                        continue

                    cmd = hook.get("command", "")

                    # Replace Python hooks with bash equivalents
                    if "kuzu-memory hooks learn" in cmd:
                        hook["command"] = self._get_bash_hook_path("learn_hook.sh")
                        changes.append(f"Migrated learn hook in {settings_path.name}")
                        logger.info(f"Migrated learn hook in {settings_path}")

                    # Keep enhance as Python for now (needs sync response)
                    # elif "kuzu-memory hooks enhance" in cmd:
                    #     hook["command"] = self._get_bash_hook_path("enhance_hook.sh")
                    #     changes.append(f"Migrated enhance hook in {settings_path.name}")

                    elif "kuzu-memory hooks session-start" in cmd:
                        hook["command"] = self._get_bash_hook_path("session_start_hook.sh")
                        changes.append(f"Migrated session-start hook in {settings_path.name}")
                        logger.info(f"Migrated session-start hook in {settings_path}")

            if changes:
                # Backup original
                backup_path = settings_path.with_suffix(".json.bak")
                shutil.copy(settings_path, backup_path)
                logger.info(f"Backed up original settings to {backup_path}")

                # Write updated settings
                settings_path.write_text(json.dumps(settings, indent=2))
                logger.info(f"Migrated hooks in {settings_path}")

            return changes

        except Exception as e:
            logger.error(f"Failed to migrate {settings_path}: {e}")
            return []

    def _get_bash_hook_path(self, script_name: str) -> str:
        """
        Get the path to a bash hook script.

        Args:
            script_name: Name of the bash script (e.g., "learn_hook.sh")

        Returns:
            Absolute path to the bash script
        """
        # Scripts installed with package
        import kuzu_memory

        pkg_dir = Path(kuzu_memory.__file__).parent
        script_path = pkg_dir / "hooks" / "bash" / script_name

        if not script_path.exists():
            logger.warning(f"Bash hook not found: {script_path}")
            # Fallback to Python hook
            return "kuzu-memory hooks " + script_name.replace("_hook.sh", "")

        return str(script_path)
