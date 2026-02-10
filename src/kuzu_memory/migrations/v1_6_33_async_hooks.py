"""Migration to enable async hooks for Claude Code integration (v1.6.33)."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from .base import HooksMigration, MigrationResult

logger = logging.getLogger(__name__)


class AsyncHooksMigration(HooksMigration):
    """
    Enable async flag on SessionStart and PostToolUse hooks.

    Claude Code now supports async hooks via an "async": true flag in hook configurations.
    This migration adds the async flag to hooks that should run in the background:
    - SessionStart: Background initialization (doesn't block UI)
    - PostToolUse: Non-blocking learning (doesn't delay next prompt)

    UserPromptSubmit remains synchronous as it must enhance the prompt before submission.
    """

    name = "async_hooks_v1.6.33"
    from_version = "1.6.33"
    to_version = "999.0.0"  # Always applicable from 1.6.33 onwards
    priority = 150  # Run after bash hooks migration (100) but before cleanup (900)

    def description(self) -> str:
        """Return migration description."""
        return "Enable async hooks for SessionStart and PostToolUse events"

    def check_applicable(self) -> bool:
        """
        Check if migration should run.

        Returns True if any Claude Code settings file exists with kuzu-memory hooks
        that don't have the async flag set appropriately.
        """
        for settings_path in self._get_settings_paths():
            if settings_path.exists():
                try:
                    settings = json.loads(settings_path.read_text())
                    hooks = settings.get("hooks", {})

                    # Check SessionStart hooks
                    session_start = hooks.get("SessionStart", [])
                    if self._needs_async_flag(session_start, "session-start"):
                        return True

                    # Check PostToolUse hooks
                    post_tool_use = hooks.get("PostToolUse", [])
                    if self._needs_async_flag(post_tool_use, "learn"):
                        return True

                except Exception as e:
                    logger.debug(f"Failed to check {settings_path}: {e}")
        return False

    def migrate(self) -> MigrationResult:
        """Add async flag to SessionStart and PostToolUse hooks in Claude settings."""
        changes: list[str] = []
        warnings: list[str] = []

        for settings_path in self._get_settings_paths():
            if settings_path.exists():
                result = self._migrate_settings(settings_path)
                if result:
                    changes.extend(result["changes"])
                    warnings.extend(result.get("warnings", []))

        if changes:
            return MigrationResult(
                success=True,
                message=f"Enabled async on {len(changes)} hook(s)",
                changes=changes,
                warnings=warnings,
            )
        else:
            return MigrationResult(
                success=True,
                message="No hooks needed async flag migration",
                changes=[],
                warnings=["No migration needed - hooks already have async flags"],
            )

    def _get_settings_paths(self) -> list[Path]:
        """Get all possible Claude settings paths."""
        return [
            Path.home() / ".claude" / "settings.json",
            Path.home() / ".claude" / "settings.local.json",
            self.project_root / ".claude" / "settings.json",
            self.project_root / ".claude" / "settings.local.json",
        ]

    def _needs_async_flag(self, hook_list: list[dict[str, Any]], command_keyword: str) -> bool:
        """
        Check if a hook list contains kuzu-memory hooks without async flag.

        Args:
            hook_list: List of hook configurations
            command_keyword: Keyword to identify kuzu-memory hook (e.g., "session-start", "learn")

        Returns:
            True if any kuzu-memory hook is missing async flag, False otherwise
        """

        for hook_entry in hook_list:
            nested_hooks = hook_entry.get("hooks", [])

            for hook in nested_hooks:
                if not isinstance(hook, dict):
                    continue

                cmd = hook.get("command", "")
                # Check if this is a kuzu-memory hook with the target command
                if "kuzu-memory" in cmd and command_keyword in cmd:
                    # Check if async flag is missing or False
                    if not hook.get("async", False):
                        return True

        return False

    def _migrate_settings(self, settings_path: Path) -> dict[str, list[str]] | None:
        """
        Migrate a single settings file.

        Args:
            settings_path: Path to Claude Code settings file

        Returns:
            Dict with "changes" and "warnings" lists, or None if no changes
        """
        changes: list[str] = []
        warnings: list[str] = []

        try:
            settings = json.loads(settings_path.read_text())
            hooks = settings.get("hooks", {})
            modified = False

            # Migrate SessionStart hooks
            if "SessionStart" in hooks:
                count = self._add_async_flag(hooks["SessionStart"], "session-start")
                if count > 0:
                    changes.append(
                        f"Enabled async on {count} SessionStart hook(s) in {settings_path.name}"
                    )
                    modified = True
                    logger.info(f"Enabled async on {count} SessionStart hook(s) in {settings_path}")

            # Migrate PostToolUse hooks
            if "PostToolUse" in hooks:
                count = self._add_async_flag(hooks["PostToolUse"], "learn")
                if count > 0:
                    changes.append(
                        f"Enabled async on {count} PostToolUse hook(s) in {settings_path.name}"
                    )
                    modified = True
                    logger.info(f"Enabled async on {count} PostToolUse hook(s) in {settings_path}")

            # Verify UserPromptSubmit remains synchronous
            if "UserPromptSubmit" in hooks:
                sync_count = self._ensure_synchronous(hooks["UserPromptSubmit"], "enhance")
                if sync_count > 0:
                    warnings.append(
                        f"Removed async flag from {sync_count} UserPromptSubmit hook(s) "
                        f"(must be synchronous) in {settings_path.name}"
                    )
                    modified = True
                    logger.info(
                        f"Ensured {sync_count} UserPromptSubmit hook(s) are synchronous in {settings_path}"
                    )

            if modified:
                # Backup original
                backup_path = settings_path.with_suffix(".json.bak")
                shutil.copy(settings_path, backup_path)
                logger.info(f"Backed up original settings to {backup_path}")

                # Write updated settings
                settings_path.write_text(json.dumps(settings, indent=2))
                logger.info(f"Migrated async flags in {settings_path}")

                return {"changes": changes, "warnings": warnings}

        except Exception as e:
            logger.error(f"Failed to migrate {settings_path}: {e}")
            return None

        return None

    def _add_async_flag(self, hook_list: list[dict[str, Any]], command_keyword: str) -> int:
        """
        Add async: true flag to kuzu-memory hooks.

        Args:
            hook_list: List of hook configurations
            command_keyword: Keyword to identify kuzu-memory hook

        Returns:
            Number of hooks modified
        """
        count = 0

        for hook_entry in hook_list:
            nested_hooks = hook_entry.get("hooks", [])

            for hook in nested_hooks:
                if not isinstance(hook, dict):
                    continue

                cmd = hook.get("command", "")
                if "kuzu-memory" in cmd and command_keyword in cmd:
                    # Only add if not already set
                    if not hook.get("async", False):
                        hook["async"] = True
                        count += 1

        return count

    def _ensure_synchronous(self, hook_list: list[dict[str, Any]], command_keyword: str) -> int:
        """
        Ensure hooks are synchronous (remove async flag if present).

        Args:
            hook_list: List of hook configurations
            command_keyword: Keyword to identify kuzu-memory hook

        Returns:
            Number of hooks modified
        """
        count = 0

        for hook_entry in hook_list:
            nested_hooks = hook_entry.get("hooks", [])

            for hook in nested_hooks:
                if not isinstance(hook, dict):
                    continue

                cmd = hook.get("command", "")
                if "kuzu-memory" in cmd and command_keyword in cmd:
                    # Remove async flag if present (ensure synchronous)
                    if "async" in hook:
                        del hook["async"]
                        count += 1

        return count
