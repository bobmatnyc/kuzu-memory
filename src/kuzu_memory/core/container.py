"""
Enhanced dependency injection container with service lifecycle management.

This module provides an advanced DI container that supports:
- Automatic dependency resolution via type hints
- Singleton and transient service lifetimes
- Lazy initialization of singletons
- Thread-safe service registration and resolution

Design Decision: Automatic Dependency Injection
-----------------------------------------------
Rationale: Automatically resolve constructor dependencies by inspecting
type annotations. This eliminates boilerplate wiring code and makes
service registration declarative.

Trade-offs:
- Performance: Reflection overhead on first resolution (cached afterward)
- Complexity: Requires type hints on all constructors
- Debugging: Circular dependencies harder to diagnose

Alternative Considered: Manual wiring via factory functions
Rejected because: High boilerplate, error-prone, poor discoverability

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Task: 1M-417 (Enhance DI Container)
"""

import inspect
from collections.abc import Callable
from threading import RLock
from typing import Any, TypeVar

T = TypeVar("T")


class DependencyContainer:
    """
    Enhanced dependency injection container with service lifecycle management.

    Supports:
    - Singleton services (single shared instance)
    - Transient services (new instance per resolve)
    - Automatic dependency resolution via constructor inspection
    - Thread-safe operations
    - Lazy singleton initialization

    Usage Example:
        >>> container = DependencyContainer()
        >>> # Register services
        >>> container.register_service(IConfigService, ConfigService, singleton=True)
        >>> container.register_service(IMemoryService, MemoryService, singleton=False)
        >>> # Resolve with automatic dependency injection
        >>> memory_svc = container.resolve(IMemoryService)

    Performance Notes:
    - First resolution: O(n) where n = dependency tree depth (reflection overhead)
    - Subsequent resolutions: O(1) for singletons, O(n) for transients
    - Thread-safe operations use locks, minimal contention
    """

    def __init__(self) -> None:
        """Initialize empty dependency container."""
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._singletons: dict[str, Any] = {}
        self._lock = RLock()  # Reentrant lock allows same thread to acquire multiple times
        self._resolving: set[str] = (
            set()
        )  # Track services currently being resolved (prevent circular deps)

    def register_service(
        self, interface: type[T], implementation: type[T], singleton: bool = False
    ) -> None:
        """
        Register a service implementation.

        Args:
            interface: Service interface (Protocol or ABC)
            implementation: Concrete implementation class
            singleton: If True, single shared instance; if False, new instance per resolve

        Example:
            >>> container.register_service(IConfigService, FileConfigService, singleton=True)

        Design Decision: Lazy Singleton Instantiation
        ---------------------------------------------
        Singletons are not instantiated until first resolution. This avoids
        initialization order issues and reduces startup time.
        """
        name = interface.__name__

        if singleton:
            with self._lock:
                # Store class, will instantiate lazily on first resolve
                self._singletons[name] = implementation
        else:
            self._factories[name] = implementation

    def register_singleton(self, interface: type[T], instance: T) -> None:
        """
        Register a singleton service instance.

        Use when you already have an instance to share (e.g., from external initialization).

        Args:
            interface: Service interface
            instance: Concrete instance to register

        Example:
            >>> config = load_config_from_disk()
            >>> container.register_singleton(IConfigService, config)
        """
        name = interface.__name__
        with self._lock:
            self._singletons[name] = instance

    def register_factory(self, interface: type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory function for service creation.

        Args:
            interface: Service interface
            factory: Callable that returns service instance

        Example:
            >>> container.register_factory(
            ...     IMemoryService,
            ...     lambda: MemoryService(db_path="/custom/path")
            ... )
        """
        name = interface.__name__
        self._factories[name] = factory

    def resolve(self, interface: type[T]) -> T:
        """
        Resolve a service instance with automatic dependency injection.

        Args:
            interface: Service interface to resolve

        Returns:
            Service instance (singleton or new instance)

        Raises:
            ValueError: If service not registered or dependency resolution fails
            RuntimeError: If circular dependency detected

        Example:
            >>> memory_svc = container.resolve(IMemoryService)

        Implementation Notes:
        - For singletons: Returns cached instance or creates + caches on first call
        - For transients: Creates new instance every time
        - Dependencies are automatically resolved via constructor inspection
        - Circular dependencies are detected and raise RuntimeError
        """
        name = interface.__name__

        # Check for circular dependency
        if name in self._resolving:
            raise RuntimeError(f"Circular dependency detected while resolving: {name}")

        # Check singletons first
        if name in self._singletons:
            singleton = self._singletons[name]
            if isinstance(singleton, type):
                # Lazy singleton instantiation
                with self._lock:
                    # Double-check after acquiring lock (another thread may have initialized)
                    if isinstance(self._singletons[name], type):
                        try:
                            self._resolving.add(name)
                            instance: T = self._create_instance(singleton)
                            self._singletons[name] = instance
                            return instance
                        finally:
                            self._resolving.discard(name)
                    else:
                        # Already initialized by another thread
                        return self._singletons[name]  # type: ignore[no-any-return]  # Dynamic type from DI registry
            return singleton  # type: ignore[no-any-return]  # Dynamic type from DI registry

        # Check factories
        if name in self._factories:
            factory = self._factories[name]
            # If factory is a class, instantiate with DI; otherwise call factory function
            if isinstance(factory, type):
                try:
                    self._resolving.add(name)
                    return self._create_instance(factory)
                finally:
                    self._resolving.discard(name)
            else:
                return factory()  # type: ignore[no-any-return]  # Factory function return type is dynamic

        raise ValueError(f"Service not registered: {name}")

    def _create_instance(self, cls: type[T]) -> T:
        """
        Create instance with automatic dependency injection.

        Inspects constructor signature and automatically resolves dependencies
        by type annotation.

        Args:
            cls: Class to instantiate

        Returns:
            Instance with all dependencies injected

        Error Handling:
        - If dependency can't be resolved: Uses default value if available
        - If no default and can't resolve: Raises ValueError with helpful message

        Performance: O(n) where n = number of constructor parameters
        """
        sig = inspect.signature(cls.__init__)
        params = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Try to resolve parameter by type annotation
            if param.annotation != inspect.Parameter.empty:
                try:
                    params[param_name] = self.resolve(param.annotation)
                except ValueError:
                    # If can't resolve, use default if available
                    if param.default != inspect.Parameter.empty:
                        params[param_name] = param.default
                    else:
                        # No default and can't resolve - this is an error
                        raise ValueError(
                            f"Cannot resolve dependency '{param_name}: {param.annotation}' "
                            f"for {cls.__name__}. Register the dependency or provide a default value."
                        )
            elif param.default != inspect.Parameter.empty:
                # No annotation but has default
                params[param_name] = param.default

        return cls(**params)

    def has(self, interface: type[Any]) -> bool:
        """
        Check if a service is registered.

        Args:
            interface: Service interface to check

        Returns:
            True if service is registered

        Example:
            >>> if container.has(IConfigService):
            ...     config = container.resolve(IConfigService)
        """
        name = interface.__name__
        return name in self._services or name in self._singletons or name in self._factories

    def clear(self) -> None:
        """
        Clear all registered services.

        Warning: This will remove all service registrations. Primarily useful for testing.

        Example:
            >>> container.clear()  # Clean slate for test
        """
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()


# Global container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """
    Get the global dependency container.

    Returns:
        Global DependencyContainer instance

    Usage:
        >>> container = get_container()
        >>> config = container.resolve(IConfigService)

    Design Decision: Global Container
    ---------------------------------
    Rationale: Single global container simplifies service access throughout
    the application. Alternative would be passing container everywhere.

    Trade-offs:
    - Simplicity: Easy to access services from anywhere
    - Testability: Must reset container between tests (use reset_container())
    - Coupling: Creates implicit global state

    For testing, use reset_container() to clear state between tests.
    """
    return _container


def reset_container() -> None:
    """
    Reset the global dependency container.

    Clears all service registrations. Essential for test isolation.

    Usage:
        >>> def setup_test():
        ...     reset_container()
        ...     # Register test mocks
        ...     container = get_container()
        ...     container.register_singleton(IConfigService, MockConfig())
    """
    global _container
    _container = DependencyContainer()
