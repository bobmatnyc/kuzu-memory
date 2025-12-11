"""
Service protocol interfaces for KuzuMemory SOA/DI architecture.

This module defines Protocol interfaces that serve as contracts for all services
in the system. Protocols enable:
- Clean separation of concerns
- Improved testability through dependency injection
- Type-safe service interactions
- Easy mocking in tests

Design Decision: Using typing.Protocol instead of ABC
-------------------------------------------------------
Rationale: Protocols provide structural subtyping (duck typing with type hints)
which is more flexible than nominal subtyping with ABCs. Services can implement
the interface without explicitly inheriting from it.

Trade-offs:
- Performance: Protocols have zero runtime overhead vs. ABC's metaclass
- Flexibility: Services can satisfy multiple protocols without diamond inheritance
- Testability: Mock objects don't need to inherit from ABC, just match the interface

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Task: 1M-416 (Design Service Interfaces)
"""

from pathlib import Path
from typing import Any, Protocol

from kuzu_memory.core.models import Memory, MemoryContext, MemoryType


class IMemoryService(Protocol):
    """
    Protocol for memory management operations.

    This service encapsulates all memory CRUD operations and provides
    a context manager interface for resource management.

    Usage Example:
        >>> with memory_service as svc:
        >>>     memory = svc.add_memory("User prefers Python", MemoryType.PREFERENCE)
        >>>     retrieved = svc.get_memory(memory.id)

    Performance:
    - add_memory: O(1) average case
    - get_memory: O(1) lookup by ID
    - list_memories: O(n) with limit parameter for pagination
    """

    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        entities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """
        Add a new memory to the database.

        Args:
            content: Memory content text
            memory_type: Type of memory (episodic, semantic, etc.)
            entities: Optional list of extracted entities
            metadata: Optional additional metadata

        Returns:
            Created Memory object with generated ID

        Raises:
            ValueError: If content is empty or invalid
            DatabaseError: If storage operation fails
        """
        ...

    def get_memory(self, memory_id: str) -> Memory | None:
        """
        Retrieve a memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory object if found, None otherwise

        Performance: O(1) lookup by ID
        """
        ...

    def list_memories(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        """
        List memories with optional filtering and pagination.

        Args:
            memory_type: Optional filter by memory type
            limit: Maximum number of memories to return (default: 100)
            offset: Number of memories to skip for pagination (default: 0)

        Returns:
            List of Memory objects matching criteria

        Performance: O(n) where n = limit
        """
        ...

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if memory was deleted, False if not found

        Error Handling: Returns False instead of raising exception if not found
        """
        ...

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory | None:
        """
        Update an existing memory.

        Args:
            memory_id: Unique memory identifier
            content: Optional new content
            metadata: Optional new/updated metadata

        Returns:
            Updated Memory object if found, None otherwise

        Note: At least one of content or metadata must be provided
        """
        ...

    # NEW METHOD 1: remember() - Used by store, learn commands
    def remember(
        self,
        content: str,
        source: str,
        session_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store a new memory with automatic classification.

        Args:
            content: The memory content to store
            source: Source of the memory (e.g., "cli", "api", "integration")
            session_id: Optional session identifier
            agent_id: Optional agent identifier
            metadata: Optional additional metadata

        Returns:
            Memory ID (UUID string)
        """
        ...

    # NEW METHOD 2: attach_memories() - Used by recall, enhance commands
    def attach_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "hybrid",
        **filters: Any,
    ) -> MemoryContext:
        """
        Attach relevant memories to a prompt.

        Args:
            prompt: The prompt to enhance with memories
            max_memories: Maximum number of memories to attach
            strategy: Recall strategy ("hybrid", "semantic", "temporal")
            **filters: Additional filters (memory_type, min_relevance, etc.)

        Returns:
            MemoryContext with selected memories and metadata
        """
        ...

    # NEW METHOD 3: get_recent_memories() - Used by recent command
    def get_recent_memories(
        self,
        limit: int = 20,
        memory_type: MemoryType | None = None,
        **filters: Any,
    ) -> list[Memory]:
        """
        Get recent memories ordered by timestamp.

        Args:
            limit: Maximum number of memories to return
            memory_type: Optional filter by memory type
            **filters: Additional filters (source, session_id, etc.)

        Returns:
            List of Memory objects ordered by created_at DESC
        """
        ...

    # NEW METHOD 4: get_memory_count() - Used by recall, prune, recent
    def get_memory_count(
        self,
        memory_type: MemoryType | None = None,
        **filters: Any,
    ) -> int:
        """
        Get total memory count with optional filters.

        Args:
            memory_type: Optional filter by memory type
            **filters: Additional filters

        Returns:
            Total count of memories matching filters
        """
        ...

    # NEW METHOD 5: get_database_size() - Used by recall, prune, recent
    def get_database_size(self) -> int:
        """
        Get current database size in bytes.

        Returns:
            Database size in bytes
        """
        ...

    # NEW PROPERTY: Access to underlying KuzuMemory (for MemoryPruner)
    @property
    def kuzu_memory(self) -> Any:
        """
        Access underlying KuzuMemory instance for advanced operations.

        Provided for advanced operations like MemoryPruner integration.
        Use with caution - prefer service methods when possible.
        """
        ...

    def __enter__(self) -> "IMemoryService":
        """
        Enter context manager.

        Returns:
            Self for use in with statement
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        Exit context manager and cleanup resources.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred
        """
        ...


class IConfigService(Protocol):
    """
    Protocol for configuration management.

    Handles loading, saving, and accessing configuration values from
    multiple sources (disk, environment variables, defaults).

    Configuration Priority:
    1. Environment variables (highest)
    2. Project-specific config files
    3. User-level defaults
    4. System defaults (lowest)

    Usage Example:
        >>> config = container.resolve(IConfigService)
        >>> db_path = config.get_db_path()
        >>> api_key = config.get_config_value("api_key", default="")
    """

    def get_project_root(self) -> Path:
        """
        Get the project root directory.

        Returns:
            Path to project root directory

        Implementation Note: Should detect git root or use explicit config
        """
        ...

    def get_db_path(self) -> Path:
        """
        Get the database path.

        Returns:
            Path to Kuzu database directory

        Default: <project_root>/.kuzu-memory/db
        """
        ...

    def load_config(self) -> dict[str, Any]:
        """
        Load configuration from disk.

        Returns:
            Dictionary of all configuration values

        Error Handling: Returns empty dict if config file doesn't exist
        """
        ...

    def save_config(self, config: dict[str, Any]) -> None:
        """
        Save configuration to disk.

        Args:
            config: Configuration dictionary to save

        Raises:
            IOError: If unable to write config file
        """
        ...

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific config value.

        Args:
            key: Configuration key (supports dot notation: "api.key")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> value = config.get_config_value("integrations.auggie.enabled", False)
        """
        ...


class IInstallerService(Protocol):
    """
    Protocol for installer management.

    Manages integration installations (Claude Desktop, Auggie, Cursor, etc.)
    with health checking and repair capabilities.

    Supported Integrations:
    - claude-desktop: Claude Desktop MCP integration
    - auggie: Auggie Codex integration
    - cursor: Cursor IDE integration
    - vscode: VS Code integration

    Usage Example:
        >>> installer = container.resolve(IInstallerService)
        >>> available = installer.discover_installers()
        >>> installer.install("claude-desktop")
        >>> health = installer.check_health("claude-desktop")
    """

    def discover_installers(self) -> list[str]:
        """
        Discover available installers.

        Returns:
            List of available integration names

        Example: ["claude-desktop", "auggie", "cursor", "vscode"]
        """
        ...

    def install(self, integration: str, **kwargs: Any) -> bool:
        """
        Install an integration.

        Args:
            integration: Integration name (e.g., "claude-desktop")
            **kwargs: Integration-specific options

        Returns:
            True if installation succeeded

        Raises:
            ValueError: If integration name is unknown
            InstallationError: If installation fails
        """
        ...

    def uninstall(self, integration: str) -> bool:
        """
        Uninstall an integration.

        Args:
            integration: Integration name

        Returns:
            True if uninstallation succeeded

        Note: Some integrations may not support uninstallation
        """
        ...

    def repair_mcp_config(self) -> bool:
        """
        Repair MCP configuration.

        Fixes common configuration issues:
        - Missing or malformed JSON
        - Incorrect paths
        - Permission issues

        Returns:
            True if repair succeeded

        Usage: Call when health checks fail
        """
        ...

    def check_health(self, integration: str) -> dict[str, Any]:
        """
        Check health of an installation.

        Args:
            integration: Integration name

        Returns:
            Health status dictionary with keys:
            - healthy: bool
            - issues: list[str] of problems found
            - suggestions: list[str] of remediation steps

        Example:
            >>> health = installer.check_health("claude-desktop")
            >>> if not health["healthy"]:
            >>>     print(health["suggestions"])
        """
        ...


class ISetupService(Protocol):
    """
    Protocol for setup orchestration.

    Coordinates the initial setup workflow including:
    - Project initialization
    - Database creation
    - Integration detection and installation
    - Git sync configuration

    Design Decision: Smart Setup vs. Manual Setup
    ---------------------------------------------
    Rationale: Provide intelligent defaults while allowing manual control.
    The smart_setup method detects environment and suggests optimal configuration,
    but users can override with explicit parameters.

    Usage Example:
        >>> setup = container.resolve(ISetupService)
        >>> result = setup.initialize_project(git_sync=True, auggie=True)
        >>> if result["success"]:
        >>>     print(f"Setup complete: {result['summary']}")
    """

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
            git_sync: Enable git history synchronization
            claude_desktop: Install Claude Desktop integration

        Returns:
            Setup result dictionary with keys:
            - success: bool
            - summary: str description
            - steps_completed: list[str]
            - warnings: list[str]

        Workflow:
        1. Detect project environment
        2. Initialize database if needed
        3. Configure integrations based on detected tools
        4. Optionally sync git history
        5. Verify installation health
        """
        ...

    def setup_integrations(self, integrations: list[str]) -> dict[str, bool]:
        """
        Set up specified integrations.

        Args:
            integrations: List of integration names to set up
                         (e.g., ["claude-desktop", "auggie"])

        Returns:
            Dictionary mapping integration name to success status

        Example:
            >>> results = setup.setup_integrations(["claude-desktop"])
            >>> if results["claude-desktop"]:
            >>>     print("Claude Desktop integration installed")
        """
        ...

    def verify_setup(self) -> dict[str, Any]:
        """
        Verify current setup is valid and complete.

        Returns:
            Verification result dictionary with keys:
            - valid: bool - True if setup is complete and valid
            - issues: list[str] - Problems found
            - suggestions: list[str] - Remediation steps

        Example:
            >>> result = setup.verify_setup()
            >>> if not result["valid"]:
            >>>     print("Issues:", result["issues"])
        """
        ...

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
        """
        ...

    def get_project_db_path(self, project_root: Path | None = None) -> Path:
        """
        Get the database path for a project.

        Args:
            project_root: Optional project root (default: auto-detect)

        Returns:
            Path to project's database directory

        Default: <project_root>/.kuzu-memory/db
        """
        ...

    def ensure_project_structure(self, project_root: Path) -> bool:
        """
        Ensure project has required directory structure.

        Args:
            project_root: Project root directory

        Returns:
            True if structure was created or already exists

        Creates:
        - .kuzu-memory/ directory
        - .kuzu-memory/db/ directory
        - .kuzu-memory/config.json (if not exists)
        """
        ...

    def initialize_hooks(self, project_root: Path) -> bool:
        """
        Initialize git hooks for automatic memory capture.

        Args:
            project_root: Project root directory

        Returns:
            True if hooks were installed successfully

        Installs:
        - post-commit hook for automatic commit memory capture
        - Integration with existing git hooks if present
        """
        ...

    def validate_project_structure(self, project_root: Path) -> bool:
        """
        Validate that project structure is correct.

        Args:
            project_root: Project root directory

        Returns:
            True if structure is valid

        Checks:
        - .kuzu-memory/ directory exists
        - Database is accessible
        - Configuration is valid
        - Permissions are correct
        """
        ...


class IDiagnosticService(Protocol):
    """
    Protocol for diagnostic operations.

    Provides health checks, performance diagnostics, and system status reporting.

    Design Decision: Async Methods for I/O Operations
    -------------------------------------------------
    Rationale: Diagnostic operations involve I/O (database checks, file system access,
    network calls to integrations). Async methods prevent blocking and enable concurrent
    health checks for better performance.

    Usage Example:
        >>> diag = container.resolve(IDiagnosticService)
        >>> health = await diag.run_full_diagnostics()
        >>> if not health["all_healthy"]:
        >>>     print("Issues:", health["issues"])
        >>> report = diag.format_diagnostic_report(health)
        >>> print(report)
    """

    async def run_full_diagnostics(self) -> dict[str, Any]:
        """
        Run comprehensive diagnostics on entire system.

        Returns:
            Complete diagnostic results with keys:
            - all_healthy: bool
            - configuration: dict[str, Any] config check results
            - database: dict[str, Any] database health results
            - mcp_server: dict[str, Any] MCP server status
            - git_integration: dict[str, Any] git sync status
            - system_info: dict[str, Any] system information
            - timestamp: str ISO timestamp

        This is the primary diagnostic method that orchestrates all checks.
        """
        ...

    async def check_configuration(self) -> dict[str, Any]:
        """
        Check configuration validity and completeness.

        Returns:
            Configuration check results with keys:
            - valid: bool
            - issues: list[str] problems found
            - config_path: str path to config file
            - project_root: str project root directory

        Checks:
        - Configuration file exists and is readable
        - Required configuration keys present
        - Paths are valid and accessible
        - Environment variables properly set
        """
        ...

    async def check_database_health(self) -> dict[str, Any]:
        """
        Check database connectivity and health.

        Returns:
            Database health results with keys:
            - connected: bool
            - memory_count: int total memories
            - db_size_bytes: int database size
            - schema_version: str current schema version
            - issues: list[str] problems found

        Checks:
        - Database file exists and is accessible
        - Database connection can be established
        - Schema is valid and up-to-date
        - No corruption detected
        """
        ...

    async def check_mcp_server_health(self) -> dict[str, Any]:
        """
        Check MCP server configuration and health.

        Returns:
            MCP server health results with keys:
            - configured: bool
            - config_valid: bool
            - server_path: str path to MCP server config
            - issues: list[str] problems found

        Checks:
        - MCP config file exists (claude_desktop_config.json)
        - Configuration is valid JSON
        - Server entry is present and correct
        - Paths in configuration are valid
        """
        ...

    async def check_git_integration(self) -> dict[str, Any]:
        """
        Check git synchronization integration.

        Returns:
            Git integration results with keys:
            - available: bool git is available
            - hooks_installed: bool git hooks are installed
            - last_sync: Optional[str] last sync timestamp
            - issues: list[str] problems found

        Checks:
        - Git repository is detected
        - Git hooks are installed
        - Sync functionality is working
        - No permission issues
        """
        ...

    async def check_hooks_status(self, project_root: Path | None = None) -> dict[str, Any]:
        """
        Check status of all hooks (git and Claude Code).

        Verifies installation and configuration of:
        - Git post-commit hooks (.git/hooks/post-commit)
        - Claude Code hooks (.claude/settings.local.json)

        Args:
            project_root: Optional project root directory (uses config service default if None)

        Returns:
            dict with keys:
            - git_hooks: dict with installed, executable, path
            - claude_code_hooks: dict with installed, valid, events
            - overall_status: str - "fully_configured", "partially_configured", "not_configured"
            - recommendations: list[str] - Actionable recommendations

        Example:
            >>> async with DiagnosticService(config_svc) as svc:
            >>>     results = await svc.check_hooks_status()
            >>>     if results["overall_status"] == "not_configured":
            >>>         print("Recommendations:", results["recommendations"])
        """
        ...

    async def check_mcp_installation(self, full: bool = False) -> dict[str, Any]:
        """
        Check MCP installation using py-mcp-installer-service diagnostics.

        Args:
            full: If True, include detailed diagnostics

        Returns:
            MCP installation status with keys:
            - installed: bool
            - version: str | None
            - config_path: str | None
            - issues: list[str]

        Checks:
        - MCP server is installed
        - Configuration files exist
        - Version compatibility
        """
        ...

    async def get_system_info(self) -> dict[str, Any]:
        """
        Get system information and environment details.

        Returns:
            System information with keys:
            - version: str KuzuMemory version
            - python_version: str Python version
            - platform: str operating system
            - kuzu_version: str Kuzu database version
            - install_path: str installation path

        Used for debugging and support diagnostics.
        """
        ...

    async def verify_dependencies(self) -> dict[str, Any]:
        """
        Verify all required dependencies are installed.

        Returns:
            Dependency verification results with keys:
            - all_satisfied: bool
            - missing: list[str] missing dependencies
            - outdated: list[str] outdated dependencies
            - suggestions: list[str] remediation steps

        Checks:
        - Required Python packages installed
        - Package versions meet requirements
        - Optional dependencies for integrations
        """
        ...

    def format_diagnostic_report(self, results: dict[str, Any]) -> str:
        """
        Format diagnostic results as human-readable report.

        Args:
            results: Diagnostic results from run_full_diagnostics()

        Returns:
            Formatted report string with sections for each check

        Note: This method is synchronous as it only formats data.

        Example:
            >>> results = await diag.run_full_diagnostics()
            >>> report = diag.format_diagnostic_report(results)
            >>> print(report)
        """
        ...


class IGitSyncService(Protocol):
    """
    Protocol for git synchronization.

    Syncs git commit history as episodic memories, enabling the system
    to recall project evolution and decision context.

    Design Decision: Episodic Memory for Git History
    ------------------------------------------------
    Rationale: Git commits represent episodic events in project timeline.
    Storing as memories enables temporal recall and context awareness.

    Trade-offs:
    - Storage: Each commit becomes a memory (~1KB per commit)
    - Performance: Initial sync may take time for large repos
    - Relevance: Old commits may have low recall value

    Optimization: Use max_commits limit and since date to control scope

    Usage Example:
        >>> git_sync = container.resolve(IGitSyncService)
        >>> if git_sync.is_available():
        >>>     git_sync.install_hooks()
        >>>     count = git_sync.sync(since="2024-01-01", max_commits=100)
        >>>     print(f"Synced {count} commits")
        >>>     status = git_sync.get_sync_status()
        >>>     print(f"Last sync: {status['last_sync']}")
    """

    def initialize_sync(self, project_root: Path | None = None) -> bool:
        """
        Initialize git synchronization for a project.

        Args:
            project_root: Optional project root directory (default: auto-detect)

        Returns:
            True if initialization succeeded

        Setup Actions:
        - Detect git repository
        - Verify git is available
        - Create initial configuration
        - Optionally install git hooks
        """
        ...

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

        Memory Format:
        - content: "<commit_message> (by <author> on <date>)"
        - memory_type: EPISODIC
        - entities: [author_name, file_paths]
        - metadata: {commit_hash, author, date, files_changed}

        Performance: ~10-50 commits/second depending on commit size
        """
        ...

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
        ...

    def get_sync_status(self) -> dict[str, Any]:
        """
        Get current synchronization status.

        Returns:
            Status dictionary with keys:
            - enabled: bool synchronization is enabled
            - last_sync: Optional[str] last sync timestamp
            - commits_synced: int total commits synced
            - hooks_installed: bool git hooks are installed

        Example:
            >>> status = git_sync.get_sync_status()
            >>> if status["enabled"]:
            >>>     print(f"Last synced {status['commits_synced']} commits")
        """
        ...

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
        ...

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
        ...
