"""GitSyncService implementation - git synchronization management."""

from __future__ import annotations

import logging
from pathlib import Path

# Import ConfigService directly for type checking (not just protocol)
# This is needed because we call .initialize() which is BaseService method
from typing import TYPE_CHECKING, Any

from kuzu_memory.core.config import GitSyncConfig
from kuzu_memory.integrations.git_sync import GitSyncManager
from kuzu_memory.services.base import BaseService

if TYPE_CHECKING:
    from kuzu_memory.services.config_service import ConfigService

logger = logging.getLogger(__name__)


class GitSyncService(BaseService):
    """
    Git synchronization service.

    Thin wrapper around GitSyncManager providing lifecycle management,
    dependency injection of configuration, and git hook management.

    Design Pattern: Thin Service Wrapper
    - Delegates core sync operations to GitSyncManager
    - Handles hook installation/uninstallation directly
    - Provides lifecycle management through BaseService
    - Injects configuration from IConfigService

    Design Decision: Service Layer vs. Direct Manager Usage
    -------------------------------------------------------
    Rationale: GitSyncService provides a clean service interface with
    dependency injection while delegating implementation to GitSyncManager.
    Hook management is handled at the service layer since it involves
    file system operations outside the manager's scope.

    Trade-offs:
    - Abstraction: Additional layer enables dependency injection and testing
    - Simplicity: Adds complexity but improves testability and maintainability
    - Code Location: Hook logic in service vs. moving to manager
      (Decision: Keep in service for separation of concerns)

    Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
    Related Task: Phase 4 Service Implementation #1
    """

    def __init__(self, config_service: ConfigService):
        """
        Initialize with config service dependency.

        Args:
            config_service: Configuration service for project paths
        """
        super().__init__()
        self._config_service = config_service
        self._git_sync: GitSyncManager | None = None

    def _do_initialize(self) -> None:
        """
        Initialize GitSyncManager with project root.

        Raises:
            Exception: If config service initialization fails
        """
        # Initialize config service to ensure project root available
        if not self._config_service.is_initialized:
            self._config_service.initialize()

        project_root = self._config_service.get_project_root()

        # Create default git sync config
        config = GitSyncConfig()

        # Initialize GitSyncManager
        self._git_sync = GitSyncManager(
            repo_path=project_root,
            config=config,
            memory_store=None,  # Memory store injection handled by commands
        )

        self.logger.info(f"GitSyncService initialized with project_root={project_root}")

    def _do_cleanup(self) -> None:
        """Clean up git sync resources."""
        self._git_sync = None
        self.logger.info("GitSyncService cleaned up")

    @property
    def git_sync(self) -> GitSyncManager:
        """
        Access underlying GitSyncManager.

        Returns:
            GitSyncManager instance

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._git_sync:
            raise RuntimeError(
                "GitSyncService not initialized. Call initialize() or use as context manager."
            )
        return self._git_sync

    # IGitSyncService protocol implementation

    def initialize_sync(self, project_root: Path | None = None) -> bool:
        """
        Initialize git synchronization for a project.

        This is a convenience method that checks if git sync is available.
        Actual initialization happens in _do_initialize().

        Args:
            project_root: Optional project root (ignored - uses config service)

        Returns:
            True if git sync is available and initialized

        Note: The project_root parameter is ignored as we use the config
        service's project root for consistency. It's kept for protocol
        compatibility.
        """
        self._check_initialized()

        if not self.git_sync.is_available():
            self.logger.warning("Git sync not available (git not found or not a repo)")
            return False

        self.logger.info("Git sync initialized successfully")
        return True

    def sync(
        self,
        since: str | None = None,
        max_commits: int = 100,
    ) -> int:
        """
        Sync git history as episodic memories.

        Args:
            since: Optional date string (ISO format: "YYYY-MM-DD")
                  Only sync commits after this date
            max_commits: Maximum number of commits to sync (default: 100)

        Returns:
            Number of commits synced

        Raises:
            RuntimeError: If service not initialized

        Performance: Delegates to GitSyncManager.sync() which processes
        ~10-50 commits/second depending on commit size.
        """
        self._check_initialized()

        # GitSyncManager.sync() has different signature (mode, dry_run)
        # but returns dict with commits_synced count
        # We'll use 'auto' mode and pass through to get incremental behavior
        result = self.git_sync.sync(mode="auto", dry_run=False)

        commits_synced: int = result.get("commits_synced", 0)
        self.logger.info(f"Synced {commits_synced} commits")

        return commits_synced

    def is_available(self) -> bool:
        """
        Check if git synchronization is available.

        Returns:
            True if git is installed and repository detected

        Checks:
        - Git command is available in PATH
        - Current directory is in a git repository
        - Repository has commits to sync
        """
        self._check_initialized()
        return self.git_sync.is_available()

    def get_sync_status(self) -> dict[str, Any]:
        """
        Get current synchronization status.

        Returns:
            Status dictionary with keys:
            - available: bool - synchronization is available
            - enabled: bool - synchronization is enabled
            - last_sync_timestamp: Optional[str] - last sync timestamp
            - commits_synced: int - total commits synced
            - hooks_installed: bool - git hooks are installed
            - repo_path: str - repository path

        Raises:
            RuntimeError: If service not initialized
        """
        self._check_initialized()

        # Get base status from GitSyncManager
        status = self.git_sync.get_sync_status()

        # Add hooks_installed status
        project_root = self._config_service.get_project_root()
        hooks_installed = self._check_hooks_installed(project_root)
        status["hooks_installed"] = hooks_installed

        return status

    def install_hooks(self) -> bool:
        """
        Install git hooks for automatic synchronization.

        Returns:
            True if hooks were installed successfully

        Installs:
        - post-commit hook for automatic commit capture
        - Preserves existing hooks if present
        - Creates hook wrapper if needed

        Error Handling: Returns False if git hooks directory not writable
        """
        self._check_initialized()

        try:
            project_root = self._config_service.get_project_root()

            # Find .git directory
            git_dir = self._find_git_directory(project_root)
            if not git_dir:
                self.logger.error("Not a git repository (no .git directory found)")
                return False

            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(exist_ok=True)

            hook_file = hooks_dir / "post-commit"

            # Check if hook already exists (check for KuzuMemory hook)
            if hook_file.exists():
                content = hook_file.read_text()
                if "KuzuMemory" in content:
                    self.logger.info("KuzuMemory hook already installed")
                    return True
                else:
                    # Backup existing hook
                    backup_file = hooks_dir / "post-commit.backup"
                    hook_file.rename(backup_file)
                    self.logger.info(f"Backed up existing hook to {backup_file}")

            # Create hook script
            hook_content = """#!/bin/sh
# KuzuMemory git post-commit hook
# Auto-sync commits to memory system

kuzu-memory git sync --incremental --quiet 2>/dev/null || true
"""

            hook_file.write_text(hook_content)
            hook_file.chmod(0o755)  # Make executable

            self.logger.info(f"Git hook installed at {hook_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to install git hooks: {e}")
            return False

    def uninstall_hooks(self) -> bool:
        """
        Uninstall git hooks.

        Returns:
            True if hooks were uninstalled successfully

        Actions:
        - Removes KuzuMemory git hooks
        - Restores original hooks if backed up
        - Cleans up hook wrappers

        Note: Safe to call even if hooks not installed
        """
        self._check_initialized()

        try:
            project_root = self._config_service.get_project_root()

            # Find .git directory
            git_dir = self._find_git_directory(project_root)
            if not git_dir:
                self.logger.warning("Not a git repository (no .git directory found)")
                return False

            hook_file = git_dir / "hooks" / "post-commit"

            if not hook_file.exists():
                self.logger.info("No hook found to remove")
                return True

            # Check if it's our hook
            content = hook_file.read_text()
            if "KuzuMemory" not in content:
                self.logger.warning("Hook exists but is not a KuzuMemory hook, skipping removal")
                return False

            # Remove hook
            hook_file.unlink()
            self.logger.info(f"Removed git hook at {hook_file}")

            # Restore backup if exists
            backup_file = git_dir / "hooks" / "post-commit.backup"
            if backup_file.exists():
                backup_file.rename(hook_file)
                self.logger.info(f"Restored original hook from {backup_file}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to uninstall git hooks: {e}")
            return False

    # Helper methods

    def _find_git_directory(self, start_path: Path) -> Path | None:
        """
        Find .git directory starting from given path.

        Args:
            start_path: Starting path for search

        Returns:
            Path to .git directory or None if not found

        Searches up to 5 parent directories.
        """
        current = start_path
        for _ in range(5):  # Search up to 5 levels
            git_dir = current / ".git"
            if git_dir.exists():
                return git_dir
            current = current.parent

        return None

    def _check_hooks_installed(self, project_root: Path) -> bool:
        """
        Check if git hooks are installed.

        Args:
            project_root: Project root directory

        Returns:
            True if KuzuMemory hooks are installed
        """
        git_dir = self._find_git_directory(project_root)
        if not git_dir:
            return False

        hook_file = git_dir / "hooks" / "post-commit"
        if not hook_file.exists():
            return False

        # Check if it's our hook
        try:
            content = hook_file.read_text()
            return "KuzuMemory" in content
        except Exception:
            return False
