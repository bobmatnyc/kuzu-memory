"""SetupService implementation - project setup and initialization."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kuzu_memory.services.base import BaseService
from kuzu_memory.utils import project_setup

if TYPE_CHECKING:
    from kuzu_memory.services.config_service import ConfigService

logger = logging.getLogger(__name__)


class SetupService(BaseService):
    """
    Project setup and initialization service.

    Thin wrapper around project_setup utilities providing lifecycle management
    and dependency injection of configuration.

    Design Pattern: Thin Service Wrapper
    - Delegates setup operations to project_setup utility functions
    - Provides lifecycle management through BaseService
    - Injects configuration from IConfigService
    - Handles project initialization and structure management

    Design Decision: Service Layer vs. Direct Utility Usage
    -------------------------------------------------------
    Rationale: SetupService provides a clean service interface with
    dependency injection while delegating implementation to utility functions.
    This maintains separation of concerns and enables testability.

    Trade-offs:
    - Abstraction: Additional layer enables dependency injection and testing
    - Simplicity: Adds complexity but improves testability and maintainability
    - Flexibility: Makes it easy to swap implementations or add caching

    Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
    Related Task: Phase 4 Service Implementation #2
    """

    def __init__(self, config_service: ConfigService):
        """
        Initialize with config service dependency.

        Args:
            config_service: Configuration service for project paths
        """
        super().__init__()
        self._config_service = config_service
        self._project_root: Path | None = None

    def _do_initialize(self) -> None:
        """
        Initialize SetupService with project root.

        Raises:
            Exception: If config service initialization fails
        """
        # Initialize config service to ensure project root available
        if not self._config_service.is_initialized:
            self._config_service.initialize()

        self._project_root = self._config_service.get_project_root()

        self.logger.info(f"SetupService initialized with project_root={self._project_root}")

    def _do_cleanup(self) -> None:
        """Clean up setup resources."""
        self._project_root = None
        self.logger.info("SetupService cleaned up")

    @property
    def project_root(self) -> Path:
        """
        Access project root path.

        Returns:
            Project root Path

        Raises:
            RuntimeError: If service not initialized
        """
        if not self._project_root:
            raise RuntimeError(
                "SetupService not initialized. Call initialize() or use as context manager."
            )
        return self._project_root

    # ISetupService protocol implementation - Path Utilities

    def find_project_root(self, start_path: Path | None = None) -> Path | None:
        """
        Find the project root directory.

        Args:
            start_path: Optional starting path for search (default: current directory)

        Returns:
            Path to project root if found, None otherwise

        Detection Strategy:
        1. Look for .git directory
        2. Look for pyproject.toml or package.json
        3. Look for .kuzu-memory directory
        4. Use current directory as fallback

        Note: This is a static utility method that doesn't require initialization.
        """
        return project_setup.find_project_root(start_path)

    def get_project_db_path(self, project_root: Path | None = None) -> Path:
        """
        Get the database path for a project.

        Args:
            project_root: Optional project root (default: use initialized root)

        Returns:
            Path to project's database directory

        Default: <project_root>/kuzu-memories/memories.db
        """
        # Use provided project_root or fall back to initialized root
        root = project_root if project_root is not None else self._project_root

        return project_setup.get_project_db_path(root)

    # ISetupService protocol implementation - Project Management

    def initialize_project(
        self,
        force: bool = False,
        git_sync: bool = False,
        claude_desktop: bool = False,
    ) -> dict[str, Any]:
        """
        Initialize project with KuzuMemory.

        Args:
            force: Force re-initialization even if already set up
            git_sync: Enable git history synchronization (reserved for future)
            claude_desktop: Install Claude Desktop integration (reserved for future)

        Returns:
            Setup result dictionary with keys:
            - success: bool
            - summary: str description
            - steps_completed: list[str]
            - warnings: list[str]
            - project_root: str project root path
            - memories_dir: str memories directory path
            - db_path: str database path

        Workflow:
        1. Detect project environment
        2. Create project structure if needed
        3. Initialize database if needed
        4. Return status and paths
        """
        self._check_initialized()

        try:
            # Use initialized project root
            root = self.project_root

            # Create project memories structure
            result = project_setup.create_project_memories_structure(project_root=root, force=force)

            # Build response
            success = result.get("created", False) or result.get("existed", False)
            steps_completed = []
            warnings = []

            if result.get("created"):
                steps_completed.append("Created project memories structure")
                steps_completed.extend(
                    [f"Created: {Path(f).name}" for f in result.get("files_created", [])]
                )
            elif result.get("existed"):
                warnings.append("Project already initialized (use force=True to reinitialize)")
            else:
                warnings.append("Project structure creation skipped")

            # git_sync and claude_desktop are reserved for future use
            # For now, we just acknowledge them in warnings if specified
            if git_sync:
                warnings.append("git_sync parameter reserved for future use")
            if claude_desktop:
                warnings.append("claude_desktop parameter reserved for future use")

            summary = (
                "Project initialized successfully"
                if success
                else "Project initialization incomplete"
            )

            self.logger.info(summary)

            return {
                "success": success,
                "summary": summary,
                "steps_completed": steps_completed,
                "warnings": warnings,
                "project_root": str(result.get("project_root", root)),
                "memories_dir": str(result.get("memories_dir", "")),
                "db_path": str(result.get("db_path", "")),
            }

        except Exception as e:
            self.logger.error(f"Project initialization failed: {e}")
            return {
                "success": False,
                "summary": f"Initialization failed: {e}",
                "steps_completed": [],
                "warnings": [str(e)],
                "project_root": str(self.project_root),
                "memories_dir": "",
                "db_path": "",
            }

    def setup_integrations(self, integrations: list[str]) -> dict[str, bool]:
        """
        Set up specified integrations.

        Args:
            integrations: List of integration names to set up
                         (e.g., ["claude-desktop", "auggie"])

        Returns:
            Dictionary mapping integration name to success status

        Note: This is a placeholder for future integration setup.
        Currently returns False for all integrations.

        Example:
            >>> results = setup.setup_integrations(["claude-desktop"])
            >>> if results["claude-desktop"]:
            >>>     print("Claude Desktop integration installed")
        """
        self._check_initialized()

        # Placeholder implementation - future integration with InstallerService
        self.logger.warning("Integration setup not yet implemented")

        return dict.fromkeys(integrations, False)

    def verify_setup(self) -> dict[str, Any]:
        """
        Verify current setup is valid and complete.

        Returns:
            Verification result dictionary with keys:
            - valid: bool - True if setup is complete and valid
            - issues: list[str] - Problems found
            - suggestions: list[str] - Remediation steps
            - project_root: str - Project root path
            - memories_dir_exists: bool - Whether memories directory exists
            - db_exists: bool - Whether database exists

        Example:
            >>> result = setup.verify_setup()
            >>> if not result["valid"]:
            >>>     print("Issues:", result["issues"])
        """
        self._check_initialized()

        try:
            root = self.project_root
            memories_dir = project_setup.get_project_memories_dir(root)
            db_path = project_setup.get_project_db_path(root)

            issues = []
            suggestions = []

            # Check if memories directory exists
            if not memories_dir.exists():
                issues.append("Memories directory does not exist")
                suggestions.append("Run 'kuzu-memory init' to initialize project")

            # Check if database exists
            if not db_path.exists():
                issues.append("Database file does not exist")
                suggestions.append("Initialize project to create database")

            # Check if it's a git repository
            if not project_setup.is_git_repository(root):
                issues.append("Not a git repository")
                suggestions.append("Initialize git repository for version control: 'git init'")

            valid = len(issues) == 0

            result = {
                "valid": valid,
                "issues": issues,
                "suggestions": suggestions,
                "project_root": str(root),
                "memories_dir_exists": memories_dir.exists(),
                "db_exists": db_path.exists(),
            }

            self.logger.info(f"Setup verification: {'valid' if valid else 'invalid'}")

            return result

        except Exception as e:
            self.logger.error(f"Setup verification failed: {e}")
            return {
                "valid": False,
                "issues": [f"Verification error: {e}"],
                "suggestions": ["Check project configuration and permissions"],
                "project_root": str(self.project_root),
                "memories_dir_exists": False,
                "db_exists": False,
            }

    # ISetupService protocol implementation - Structure Management

    def ensure_project_structure(self, project_root: Path) -> bool:
        """
        Ensure project has required directory structure.

        Args:
            project_root: Project root directory

        Returns:
            True if structure was created or already exists

        Creates:
        - kuzu-memories/ directory
        - kuzu-memories/memories.db database
        - kuzu-memories/README.md documentation
        - kuzu-memories/project_info.md template
        """
        try:
            result = project_setup.create_project_memories_structure(
                project_root=project_root, force=False
            )

            success: bool = bool(result.get("created", False) or result.get("existed", False))

            if success:
                self.logger.info(f"Project structure ensured at {project_root}")
            else:
                self.logger.warning(f"Could not ensure project structure at {project_root}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to ensure project structure: {e}")
            return False

    def initialize_hooks(self, project_root: Path) -> bool:
        """
        Initialize git hooks for automatic memory capture.

        Args:
            project_root: Project root directory

        Returns:
            True if hooks were installed successfully

        Note: This is a placeholder for future git hook integration.
        Currently returns False.

        Installs:
        - post-commit hook for automatic commit memory capture
        - Integration with existing git hooks if present
        """
        self.logger.warning("Git hook initialization not yet implemented")

        # Placeholder - future integration with GitSyncService
        return False

    def validate_project_structure(self, project_root: Path) -> bool:
        """
        Validate that project structure is correct.

        Args:
            project_root: Project root directory

        Returns:
            True if structure is valid

        Checks:
        - kuzu-memories/ directory exists
        - Database is accessible
        - Configuration files exist
        - Permissions are correct
        """
        try:
            memories_dir = project_setup.get_project_memories_dir(project_root)
            db_path = project_setup.get_project_db_path(project_root)

            # Check directory exists
            if not memories_dir.exists():
                self.logger.warning(f"Memories directory does not exist: {memories_dir}")
                return False

            # Check database exists
            if not db_path.exists():
                self.logger.warning(f"Database file does not exist: {db_path}")
                return False

            # Check permissions (try to read the directory)
            try:
                list(memories_dir.iterdir())
            except PermissionError:
                self.logger.error(f"Permission denied accessing: {memories_dir}")
                return False

            self.logger.info(f"Project structure validated at {project_root}")
            return True

        except Exception as e:
            self.logger.error(f"Project structure validation failed: {e}")
            return False
