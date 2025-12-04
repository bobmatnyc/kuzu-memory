"""
Base service class with lifecycle management.

Provides common functionality for all services including:
- Initialization/cleanup lifecycle
- Logging infrastructure
- Context manager support
- Safe double-initialization handling

Design Decision: Abstract Base Class vs. Protocol
-------------------------------------------------
Rationale: Use ABC for BaseService instead of Protocol because we want
to provide concrete implementations (lifecycle management, logging) that
all services inherit.

Trade-offs:
- Code Reuse: ABC allows sharing common initialization logic
- Flexibility: Services must inherit BaseService (nominal subtyping)
- Testing: Still easy to mock - just need to implement abstract methods

Protocols are used for service interfaces (IMemoryService, etc.) while
ABC is used for base implementation class.

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Task: 1M-418 (Create Base Service Infrastructure)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Self


class BaseService(ABC):
    """
    Base class for all services with common functionality.

    Provides:
    - Lifecycle management (initialize/cleanup)
    - Logging infrastructure
    - Context manager support
    - Safe double-initialization handling

    Usage Example:
        >>> class MyService(BaseService):
        ...     def _do_initialize(self):
        ...         self.connection = connect_to_db()
        ...
        ...     def _do_cleanup(self):
        ...         self.connection.close()
        ...
        >>> with MyService() as svc:
        ...     svc.do_work()  # Service auto-initialized
        ... # Service auto-cleaned up

    Lifecycle:
    1. __init__() - Create instance
    2. initialize() or __enter__() - Initialize resources
    3. Use service
    4. cleanup() or __exit__() - Cleanup resources

    Thread Safety:
    - Not thread-safe by default
    - Subclasses should add locking if needed for concurrent access
    """

    def __init__(self) -> None:
        """
        Initialize base service.

        Sets up logging and initialization state tracking.
        Subclasses should call super().__init__() first.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize the service.

        Safe to call multiple times - subsequent calls are no-ops.

        Raises:
            Exception: If initialization fails (propagated from _do_initialize)

        Example:
            >>> service = MyService()
            >>> service.initialize()  # First call initializes
            >>> service.initialize()  # Second call is no-op
        """
        if self._initialized:
            self.logger.debug(f"{self.__class__.__name__} already initialized, skipping")
            return

        try:
            self.logger.info(f"Initializing {self.__class__.__name__}")
            self._do_initialize()
            self._initialized = True
            self.logger.info(f"{self.__class__.__name__} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            raise

    @abstractmethod
    def _do_initialize(self) -> None:
        """
        Subclass-specific initialization logic.

        Implement this method to perform service-specific setup:
        - Open database connections
        - Load configuration
        - Initialize caches
        - Validate dependencies

        Raises:
            Exception: If initialization fails

        Example:
            >>> def _do_initialize(self):
            ...     self.db = Database(self.db_path)
            ...     self.cache = Cache()
        """
        pass

    def cleanup(self) -> None:
        """
        Cleanup service resources.

        Safe to call multiple times - subsequent calls are no-ops.

        Error Handling:
        - Logs cleanup errors but doesn't raise
        - This ensures cleanup always completes even if errors occur
        - Service is marked as uninitialized even if cleanup fails

        Example:
            >>> service = MyService()
            >>> service.initialize()
            >>> service.cleanup()  # Cleanup resources
            >>> service.cleanup()  # No-op
        """
        if not self._initialized:
            self.logger.debug(f"{self.__class__.__name__} not initialized, skipping cleanup")
            return

        try:
            self.logger.info(f"Cleaning up {self.__class__.__name__}")
            self._do_cleanup()
            self.logger.info(f"{self.__class__.__name__} cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Failed to cleanup {self.__class__.__name__}: {e}")
            # Don't raise - cleanup should always complete
        finally:
            # Always mark as uninitialized, even if cleanup fails
            self._initialized = False

    @abstractmethod
    def _do_cleanup(self) -> None:
        """
        Subclass-specific cleanup logic.

        Implement this method to perform service-specific teardown:
        - Close database connections
        - Flush caches
        - Release file handles
        - Cancel background tasks

        Should be idempotent - safe to call multiple times.

        Error Handling:
        - Should not raise exceptions (cleanup must complete)
        - Log errors but continue cleanup

        Example:
            >>> def _do_cleanup(self):
            ...     if hasattr(self, 'db') and self.db:
            ...         self.db.close()
            ...     if hasattr(self, 'cache') and self.cache:
            ...         self.cache.clear()
        """
        pass

    def __enter__(self) -> Self:
        """
        Enter context manager.

        Automatically initializes the service.

        Returns:
            Self for use in with statement

        Example:
            >>> with MyService() as svc:
            ...     svc.do_work()
        """
        self.initialize()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """
        Exit context manager and cleanup resources.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred

        Returns:
            None (exceptions are not suppressed)

        Example:
            >>> with MyService() as svc:
            ...     svc.do_work()
            ... # Cleanup happens here automatically
        """
        self.cleanup()

    @property
    def is_initialized(self) -> bool:
        """
        Check if service is initialized.

        Returns:
            True if service is initialized and ready for use

        Example:
            >>> service = MyService()
            >>> service.is_initialized  # False
            >>> service.initialize()
            >>> service.is_initialized  # True
        """
        return self._initialized

    def _check_initialized(self) -> None:
        """
        Check if service is initialized, raise if not.

        Raises:
            RuntimeError: If service not initialized

        Usage:
            >>> def do_work(self):
            ...     self._check_initialized()
            ...     # ... perform work

        Design Decision: Explicit Check vs. Auto-Initialize
        ---------------------------------------------------
        Rationale: Require explicit initialization rather than auto-initializing
        on first use. This makes initialization errors visible and avoids
        surprising behavior.

        Alternative: Auto-initialize on first method call
        Rejected because: Hidden complexity, harder to debug, unclear lifecycle
        """
        if not self._initialized:
            raise RuntimeError(
                f"{self.__class__.__name__} not initialized. "
                f"Call initialize() or use as context manager."
            )
