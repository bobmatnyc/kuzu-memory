"""
Automatic git commit synchronization for KuzuMemory.

Manages automatic triggering of git commit indexing based on configurable
intervals and triggers (enhance, learn, init).
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..core.config import GitSyncConfig

logger = logging.getLogger(__name__)


class AutoGitSyncManager:
    """
    Manages automatic git commit indexing with interval-based triggers.

    Features:
    - Interval-based syncing (e.g., every 24 hours)
    - Trigger-based syncing (on enhance, learn, init)
    - Persistent state tracking (last sync time, commit SHA)
    - Configurable limits to prevent blocking operations
    - Graceful degradation when git not available
    """

    def __init__(
        self,
        git_sync_manager: Any,
        config: GitSyncConfig,
        state_path: Path | None = None,
    ) -> None:
        """
        Initialize automatic git sync manager.

        Args:
            git_sync_manager: GitSyncManager instance for actual syncing
            config: Git sync configuration
            state_path: Path to state file (default: .kuzu-memory/git_sync_state.json)
        """
        self.git_sync = git_sync_manager
        self.config = config
        self.state_path = state_path or (Path.cwd() / ".kuzu-memory" / "git_sync_state.json")
        self._state: dict[str, Any] = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """
        Load sync state from disk.

        Returns:
            State dictionary with last_sync, last_commit_sha, commits_synced
        """
        try:
            if self.state_path.exists():
                with open(self.state_path, encoding="utf-8") as f:
                    state: dict[str, Any] = json.load(f)
                    logger.debug(f"Loaded git sync state: {state}")
                    return state
        except Exception as e:
            logger.warning(f"Failed to load git sync state: {e}")

        default_state: dict[str, Any] = {
            "last_sync": None,
            "last_commit_sha": None,
            "commits_synced": 0,
        }
        return default_state

    def _save_state(self) -> None:
        """Save sync state to disk."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            logger.debug(f"Saved git sync state to {self.state_path}")
        except Exception as e:
            logger.warning(f"Failed to save git sync state: {e}")

    def should_auto_sync(self, trigger: str = "periodic") -> bool:
        """
        Check if auto-sync should run based on configuration and interval.

        Args:
            trigger: Sync trigger type ("enhance", "learn", "init", "periodic")

        Returns:
            True if sync should be performed
        """
        # Check if auto-sync is globally enabled
        if not self.config.auto_sync_enabled:
            logger.debug("Auto-sync disabled in config")
            return False

        # Check if git sync is available
        if not self.git_sync.is_available():
            logger.debug("Git sync not available")
            return False

        # Check trigger-specific configuration
        if trigger == "enhance" and not self.config.auto_sync_on_enhance:
            return False
        if trigger == "learn" and not self.config.auto_sync_on_learn:
            return False

        # For init and periodic triggers, always sync if enabled
        if trigger in ("init", "periodic"):
            # Check interval for periodic syncs
            if trigger == "periodic" and self.config.auto_sync_interval_hours > 0:
                return self._should_sync_by_interval()
            return True

        # For enhance/learn, check interval
        if self.config.auto_sync_interval_hours > 0:
            return self._should_sync_by_interval()

        # Default: allow sync
        return True

    def _should_sync_by_interval(self) -> bool:
        """
        Check if enough time has passed since last sync.

        Returns:
            True if interval has elapsed
        """
        # If interval is 0, don't use interval-based syncing
        if self.config.auto_sync_interval_hours == 0:
            return False

        last_sync = self._state.get("last_sync")
        if not last_sync:
            logger.debug("No previous sync, should sync")
            return True

        try:
            last_sync_dt = datetime.fromisoformat(last_sync)
            interval = timedelta(hours=self.config.auto_sync_interval_hours)
            next_sync = last_sync_dt + interval

            if datetime.now() >= next_sync:
                logger.debug(
                    f"Sync interval elapsed (last: {last_sync_dt}, interval: {self.config.auto_sync_interval_hours}h)"
                )
                return True
            else:
                logger.debug(
                    f"Sync interval not elapsed (next: {next_sync}, now: {datetime.now()})"
                )
                return False
        except Exception as e:
            logger.warning(f"Failed to parse last sync time: {e}")
            return True  # Sync on error to recover

    def auto_sync_if_needed(
        self, trigger: str = "periodic", verbose: bool = False
    ) -> dict[str, Any]:
        """
        Run git sync if conditions are met.

        Args:
            trigger: Sync trigger type ("enhance", "learn", "init", "periodic")
            verbose: If True, log sync results

        Returns:
            Sync result dictionary with success, commits_synced, etc.
        """
        # Check if sync should run
        if not self.should_auto_sync(trigger):
            return {
                "success": True,
                "skipped": True,
                "reason": "Auto-sync conditions not met",
                "trigger": trigger,
            }

        try:
            logger.info(f"Running auto git sync (trigger: {trigger})")

            # Determine sync mode based on state
            mode = "incremental" if self._state.get("last_sync") else "initial"

            # Run sync with max commits limit to prevent blocking
            sync_result: dict[str, Any] = self.git_sync.sync(mode=mode, dry_run=False)

            # Update state on success
            if sync_result.get("success"):
                self._state["last_sync"] = datetime.now().isoformat()
                self._state["last_commit_sha"] = sync_result.get("last_commit_sha")
                self._state["commits_synced"] = self._state.get(
                    "commits_synced", 0
                ) + sync_result.get("commits_synced", 0)
                self._save_state()

                if verbose:
                    logger.info(
                        f"Auto-sync completed: {sync_result.get('commits_synced', 0)} commits synced"
                    )

            sync_result["trigger"] = trigger
            return sync_result

        except Exception as e:
            logger.error(f"Auto git sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "trigger": trigger,
            }

    def get_sync_state(self) -> dict[str, Any]:
        """
        Get current sync state.

        Returns:
            State dictionary with last_sync, last_commit_sha, commits_synced
        """
        return self._state.copy()

    def force_sync(self, verbose: bool = False) -> dict[str, Any]:
        """
        Force a sync regardless of interval.

        Args:
            verbose: If True, log sync results

        Returns:
            Sync result dictionary
        """
        logger.info("Forcing git sync (ignoring interval)")

        try:
            sync_result: dict[str, Any] = self.git_sync.sync(mode="auto", dry_run=False)

            if sync_result.get("success"):
                self._state["last_sync"] = datetime.now().isoformat()
                self._state["last_commit_sha"] = sync_result.get("last_commit_sha")
                self._state["commits_synced"] = self._state.get(
                    "commits_synced", 0
                ) + sync_result.get("commits_synced", 0)
                self._save_state()

                if verbose:
                    logger.info(
                        f"Force sync completed: {sync_result.get('commits_synced', 0)} commits synced"
                    )

            return sync_result

        except Exception as e:
            logger.error(f"Force sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
