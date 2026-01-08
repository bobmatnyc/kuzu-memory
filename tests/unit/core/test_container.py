"""
Unit tests for enhanced DependencyContainer.

Tests cover:
- Service registration (singleton and transient)
- Service resolution with automatic dependency injection
- Lazy singleton initialization
- Factory function registration
- Error handling for missing services
- Thread safety considerations
- Container reset functionality

Related Task: 1M-419 (Write Integration Tests)
"""

from typing import Protocol

import pytest
from kuzu_memory.core.container import (
    DependencyContainer,
    get_container,
    reset_container,
)


# Test service interfaces
class ITestService(Protocol):
    """Test service interface."""

    def get_value(self) -> str: ...


class IConfigService(Protocol):
    """Test config service interface."""

    def get_config(self) -> dict: ...


class IDependentService(Protocol):
    """Service that depends on other services."""

    def get_dependency(self) -> ITestService: ...


# Test service implementations
class TestServiceImpl:
    """Simple test service implementation."""

    def __init__(self):
        self.value = "test"

    def get_value(self) -> str:
        return self.value


class ConfigServiceImpl:
    """Test config service implementation."""

    def __init__(self):
        self.config = {"key": "value"}

    def get_config(self) -> dict:
        return self.config


class DependentService:
    """Service with dependencies."""

    def __init__(self, test_service: ITestService):
        self.test_service = test_service

    def get_dependency(self) -> ITestService:
        return self.test_service


class MultipleDependenciesService:
    """Service with multiple dependencies."""

    def __init__(self, test_service: ITestService, config_service: IConfigService):
        self.test_service = test_service
        self.config_service = config_service


class ServiceWithDefaultParam:
    """Service with optional parameter with default value."""

    def __init__(self, test_service: ITestService, optional_value: str = "default"):
        self.test_service = test_service
        self.optional_value = optional_value


class ServiceWithoutTypeHints:
    """Service without type hints on constructor."""

    def __init__(self, value):
        self.value = value


# Tests
def test_register_and_resolve_singleton():
    """Test singleton service registration and resolution."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=True)

    service1 = container.resolve(ITestService)
    service2 = container.resolve(ITestService)

    assert isinstance(service1, TestServiceImpl)
    assert service1 is service2  # Same instance (singleton)
    assert service1.get_value() == "test"


def test_register_and_resolve_transient():
    """Test transient service registration and resolution."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=False)

    service1 = container.resolve(ITestService)
    service2 = container.resolve(ITestService)

    assert isinstance(service1, TestServiceImpl)
    assert isinstance(service2, TestServiceImpl)
    assert service1 is not service2  # Different instances (transient)


def test_register_singleton_instance():
    """Test registering an already-created singleton instance."""
    container = DependencyContainer()
    instance = TestServiceImpl()
    instance.value = "custom"

    container.register_singleton(ITestService, instance)

    service = container.resolve(ITestService)
    assert service is instance
    assert service.get_value() == "custom"


def test_automatic_dependency_injection():
    """Test automatic dependency injection via constructor inspection."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=True)
    container.register_service(IDependentService, DependentService, singleton=False)

    service = container.resolve(IDependentService)

    assert isinstance(service, DependentService)
    assert isinstance(service.test_service, TestServiceImpl)
    assert service.get_dependency().get_value() == "test"


def test_multiple_dependencies():
    """Test service with multiple dependencies."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=True)
    container.register_service(IConfigService, ConfigServiceImpl, singleton=True)
    container.register_service(
        MultipleDependenciesService, MultipleDependenciesService, singleton=False
    )

    service = container.resolve(MultipleDependenciesService)

    assert isinstance(service.test_service, TestServiceImpl)
    assert isinstance(service.config_service, ConfigServiceImpl)


def test_dependency_with_default_parameter():
    """Test dependency injection with default parameter values."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=True)
    container.register_service(ServiceWithDefaultParam, ServiceWithDefaultParam, singleton=False)

    service = container.resolve(ServiceWithDefaultParam)

    assert isinstance(service.test_service, TestServiceImpl)
    assert service.optional_value == "default"  # Used default value


def test_unregistered_service():
    """Test resolving unregistered service raises error."""
    container = DependencyContainer()

    with pytest.raises(ValueError, match="Service not registered: ITestService"):
        container.resolve(ITestService)


def test_unresolvable_dependency():
    """Test that unresolvable dependency raises helpful error."""
    container = DependencyContainer()
    # Register DependentService but not its dependency (ITestService)
    container.register_service(IDependentService, DependentService, singleton=False)

    with pytest.raises(ValueError, match="Cannot resolve dependency"):
        container.resolve(IDependentService)


def test_has_service():
    """Test checking if service is registered."""
    container = DependencyContainer()

    assert not container.has(ITestService)

    container.register_service(ITestService, TestServiceImpl, singleton=True)

    assert container.has(ITestService)


def test_clear_container():
    """Test clearing all registered services."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=True)
    container.register_service(IConfigService, ConfigServiceImpl, singleton=True)

    assert container.has(ITestService)
    assert container.has(IConfigService)

    container.clear()

    assert not container.has(ITestService)
    assert not container.has(IConfigService)


def test_lazy_singleton_initialization():
    """Test that singletons are initialized lazily on first resolve."""
    container = DependencyContainer()

    # Track initialization
    init_count = 0

    class CountingService:
        def __init__(self):
            nonlocal init_count
            init_count += 1

    container.register_service(CountingService, CountingService, singleton=True)

    # Not initialized yet
    assert init_count == 0

    # First resolve initializes
    service1 = container.resolve(CountingService)
    assert init_count == 1

    # Second resolve reuses instance
    service2 = container.resolve(CountingService)
    assert init_count == 1  # Still only initialized once
    assert service1 is service2


def test_factory_function_registration():
    """Test registering a factory function."""
    container = DependencyContainer()

    def create_service() -> TestServiceImpl:
        service = TestServiceImpl()
        service.value = "factory"
        return service

    container.register_factory(ITestService, create_service)

    service1 = container.resolve(ITestService)
    service2 = container.resolve(ITestService)

    assert service1.get_value() == "factory"
    assert service2.get_value() == "factory"
    assert service1 is not service2  # Factory creates new instances


def test_global_container():
    """Test get_container returns global instance."""
    container1 = get_container()
    container2 = get_container()

    assert container1 is container2  # Same global instance


def test_reset_container():
    """Test reset_container clears global container."""
    container = get_container()
    container.register_service(ITestService, TestServiceImpl, singleton=True)

    assert container.has(ITestService)

    reset_container()

    # After reset, should be a new container
    new_container = get_container()
    assert not new_container.has(ITestService)


def test_resolve_singleton_after_reset():
    """Test that singleton is re-initialized after container reset."""
    container = get_container()
    container.register_service(ITestService, TestServiceImpl, singleton=True)

    service1 = container.resolve(ITestService)
    service1.value = "modified"

    reset_container()

    # Re-register and resolve
    new_container = get_container()
    new_container.register_service(ITestService, TestServiceImpl, singleton=True)
    service2 = new_container.resolve(ITestService)

    assert service2.value == "test"  # Fresh instance, not "modified"
    assert service1 is not service2


def test_dependency_chain():
    """Test resolving a chain of dependencies (A -> B -> C)."""

    class ServiceA:
        def __init__(self):
            self.name = "A"

    class ServiceB:
        def __init__(self, service_a: ServiceA):
            self.service_a = service_a
            self.name = "B"

    class ServiceC:
        def __init__(self, service_b: ServiceB):
            self.service_b = service_b
            self.name = "C"

    container = DependencyContainer()
    container.register_service(ServiceA, ServiceA, singleton=True)
    container.register_service(ServiceB, ServiceB, singleton=True)
    container.register_service(ServiceC, ServiceC, singleton=True)

    service_c = container.resolve(ServiceC)

    assert service_c.name == "C"
    assert service_c.service_b.name == "B"
    assert service_c.service_b.service_a.name == "A"


def test_mixed_singleton_and_transient():
    """Test mixing singleton and transient services."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=True)
    container.register_service(IDependentService, DependentService, singleton=False)

    # Resolve transient services
    dependent1 = container.resolve(IDependentService)
    dependent2 = container.resolve(IDependentService)

    # Different instances of dependent service
    assert dependent1 is not dependent2

    # But both share same singleton dependency
    assert dependent1.test_service is dependent2.test_service


def test_register_same_interface_twice():
    """Test that registering same interface twice overwrites previous registration."""
    container = DependencyContainer()

    class FirstImpl:
        def get_value(self):
            return "first"

    class SecondImpl:
        def get_value(self):
            return "second"

    container.register_service(ITestService, FirstImpl, singleton=True)
    container.register_service(ITestService, SecondImpl, singleton=True)

    service = container.resolve(ITestService)
    assert service.get_value() == "second"  # Second registration wins


def test_resolve_with_interface_name():
    """Test that resolve uses interface name for lookup."""
    container = DependencyContainer()
    container.register_service(ITestService, TestServiceImpl, singleton=True)

    # Should resolve by interface name, not implementation name
    service = container.resolve(ITestService)
    assert isinstance(service, TestServiceImpl)


def test_dependency_injection_with_no_annotations():
    """Test that services without type annotations can still be resolved if they have defaults."""

    class ServiceWithDefaults:
        def __init__(self, value="default"):
            self.value = value

    container = DependencyContainer()
    container.register_service(ServiceWithDefaults, ServiceWithDefaults, singleton=False)

    service = container.resolve(ServiceWithDefaults)
    assert service.value == "default"
