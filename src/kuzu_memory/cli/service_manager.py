"""Service lifecycle management for CLI commands.

This module provides context managers for proper service initialization and cleanup,
enabling dependency injection in CLI commands.

Design Decision: Context Manager Pattern for Service Lifecycle
---------------------------------------------------------------
Rationale: Context managers ensure proper resource cleanup and explicit lifecycle control.
Each service context manager wraps initialization, yields the service instance, and
guarantees cleanup on exit (including exceptions).

Trade-offs:
- Simplicity: Easy to use with Python's 'with' statement
- Safety: Automatic cleanup prevents resource leaks
- Testability: Services can be mocked by replacing context manager returns

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Phase: 5.1 (Low-Risk Read Command Migrations)
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from kuzu_memory.protocols.services import IMemoryService

if TYPE_CHECKING:
    from kuzu_memory.protocols.services import (
        IConfigService,
        IDiagnosticService,
        IGitSyncService,
    )

from kuzu_memory.services import MemoryService


class ServiceManager:
    """Manages service lifecycle for CLI commands.

    Provides context managers for proper service initialization/cleanup.
    Each context manager handles the full lifecycle: initialize -> use -> cleanup.

    Example Usage:
        >>> with ServiceManager.memory_service(db_path) as memory:
        >>>     memories = memory.recall("test query", limit=10)
    """

    @staticmethod
    @contextmanager
    def memory_service(
        db_path: Path | None = None,
        enable_git_sync: bool = False,
        config: dict[str, Any] | None = None,
    ) -> Iterator[IMemoryService]:
        """Context manager for MemoryService.

        Handles full service lifecycle: initialization, usage, and cleanup.

        Args:
            db_path: Optional database path (auto-detects project DB if not provided)
            enable_git_sync: Enable git synchronization (default: False for read ops)
            config: Optional configuration dictionary

        Yields:
            IMemoryService: Initialized memory service instance

        Example:
            >>> with ServiceManager.memory_service(db_path) as memory:
            >>>     memory.remember("content", "source")

        Error Handling:
            - Propagates exceptions from service operations
            - Ensures cleanup even on exceptions
            - Safe to use in CLI commands with try/except wrapper

        Performance: O(1) initialization, cleanup time varies with open connections
        """
        from kuzu_memory.utils.project_setup import get_project_db_path

        # Auto-detect database path if not provided
        if db_path is None:
            db_path = get_project_db_path()

        # Create and initialize service
        service = MemoryService(db_path=db_path, enable_git_sync=enable_git_sync, config=config)
        service.initialize()

        try:
            yield service
        finally:
            # Ensure cleanup even on exceptions
            service.cleanup()

    @staticmethod
    @contextmanager
    def git_sync_service(
        config_service: Optional["IConfigService"] = None,
    ) -> Iterator["IGitSyncService"]:
        """Context manager for GitSyncService.

        Handles full service lifecycle: initialization, usage, and cleanup.

        Args:
            config_service: Optional configuration service instance.
                          If not provided, creates one with auto-detected project root.

        Yields:
            IGitSyncService: Initialized git sync service instance

        Example:
            >>> # With existing config service
            >>> config = ConfigService(project_root)
            >>> config.initialize()
            >>> with ServiceManager.git_sync_service(config) as git_sync:
            >>>     git_sync.sync()
            >>>
            >>> # Auto-create config service
            >>> with ServiceManager.git_sync_service() as git_sync:
            >>>     if git_sync.is_available():
            >>>         git_sync.sync()

        Error Handling:
            - Propagates exceptions from service operations
            - Ensures cleanup even on exceptions
            - Safe to use in CLI commands with try/except wrapper

        Performance: O(1) initialization, cleanup time varies with resources held
        """
        from kuzu_memory.services import ConfigService, GitSyncService
        from kuzu_memory.services.config_service import ConfigService as ConcreteConfigService
        from kuzu_memory.utils.project_setup import find_project_root

        # Create config service if not provided
        concrete_config: ConcreteConfigService
        if config_service is None:
            project_root = find_project_root()
            concrete_config = ConfigService(project_root)
            concrete_config.initialize()
        else:
            # Cast to concrete type for GitSyncService constructor
            # This is safe as we control the creation of config services
            concrete_config = config_service  # type: ignore[assignment]  # Protocol to concrete cast - safe in context

        # Create and initialize git sync service
        service = GitSyncService(concrete_config)
        service.initialize()

        try:
            yield service
        finally:
            # Ensure cleanup even on exceptions
            service.cleanup()

    @staticmethod
    @contextmanager
    def diagnostic_service(
        config_service: Optional["IConfigService"] = None,
        memory_service: IMemoryService | None = None,
    ) -> Iterator["IDiagnosticService"]:
        """Context manager for DiagnosticService.

        Handles full service lifecycle: initialization, usage, and cleanup.
        DiagnosticService has async methods - use with async_utils.run_async():

        Args:
            config_service: Optional configuration service instance.
                          If not provided, creates one with auto-detected project root.
            memory_service: Optional memory service instance for DB health checks

        Yields:
            IDiagnosticService: Initialized diagnostic service instance

        Example:
            >>> from kuzu_memory.cli.async_utils import run_async
            >>>
            >>> # With existing services
            >>> config = ConfigService(project_root)
            >>> config.initialize()
            >>> with ServiceManager.diagnostic_service(config) as diagnostic:
            >>>     result = run_async(diagnostic.run_full_diagnostics())
            >>>
            >>> # Auto-create config service
            >>> with ServiceManager.diagnostic_service() as diagnostic:
            >>>     health = run_async(diagnostic.check_database_health())

        Error Handling:
            - Propagates exceptions from service operations
            - Ensures cleanup even on exceptions
            - Safe to use in CLI commands with try/except wrapper

        Note on Async:
            DiagnosticService methods are async for I/O operations.
            Use run_async() helper to call them from sync CLI commands:

            >>> result = run_async(diagnostic.run_full_diagnostics())

        Performance: O(1) initialization, cleanup time varies with resources held
        """
        from kuzu_memory.services import ConfigService, DiagnosticService
        from kuzu_memory.services.config_service import ConfigService as ConcreteConfigService
        from kuzu_memory.utils.project_setup import find_project_root

        # Create config service if not provided
        concrete_config: ConcreteConfigService
        if config_service is None:
            project_root = find_project_root()
            concrete_config = ConfigService(project_root)
            concrete_config.initialize()
        else:
            # Cast to concrete type for DiagnosticService constructor
            # This is safe as we control the creation of config services
            concrete_config = config_service  # type: ignore[assignment]  # Protocol to concrete cast - safe in context

        # Create and initialize diagnostic service
        # DiagnosticService expects concrete MemoryService type
        # We cast the protocol interface to concrete type - safe as ServiceManager creates concrete types
        from kuzu_memory.services.memory_service import MemoryService as ConcreteMemoryService

        concrete_memory: ConcreteMemoryService | None = None
        if memory_service is not None:
            # Safe cast from protocol to concrete type
            concrete_memory = memory_service  # type: ignore[assignment]  # Protocol to concrete cast - safe in context

        service = DiagnosticService(concrete_config, concrete_memory)
        service.initialize()

        try:
            yield service
        finally:
            # Ensure cleanup even on exceptions
            service.cleanup()


__all__ = ["ServiceManager"]
