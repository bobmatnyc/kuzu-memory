"""
Unit tests for BaseService lifecycle management.

Tests cover:
- Service initialization
- Cleanup behavior
- Context manager usage
- Double-initialization safety
- Error handling

Related Task: 1M-419 (Write Integration Tests)
"""

import logging

import pytest

from kuzu_memory.services.base import BaseService


class MockService(BaseService):
    """
    Mock service for testing BaseService lifecycle.

    Tracks initialization and cleanup calls for verification.
    """

    def __init__(self):
        super().__init__()
        self.init_called = False
        self.cleanup_called = False
        self.init_call_count = 0
        self.cleanup_call_count = 0

    def _do_initialize(self):
        self.init_called = True
        self.init_call_count += 1

    def _do_cleanup(self):
        self.cleanup_called = True
        self.cleanup_call_count += 1


class FailingInitService(BaseService):
    """Mock service that fails during initialization."""

    def _do_initialize(self):
        raise RuntimeError("Initialization failed")

    def _do_cleanup(self):
        pass


class FailingCleanupService(BaseService):
    """Mock service that fails during cleanup."""

    def __init__(self):
        super().__init__()
        self.cleanup_error_logged = False

    def _do_initialize(self):
        pass

    def _do_cleanup(self):
        raise RuntimeError("Cleanup failed")


def test_base_service_initialization():
    """Test service initialization."""
    service = MockService()
    assert not service._initialized
    assert not service.is_initialized
    assert not service.init_called

    service.initialize()
    assert service._initialized
    assert service.is_initialized
    assert service.init_called
    assert service.init_call_count == 1


def test_base_service_cleanup():
    """Test service cleanup."""
    service = MockService()
    service.initialize()
    assert service._initialized

    service.cleanup()
    assert not service._initialized
    assert not service.is_initialized
    assert service.cleanup_called
    assert service.cleanup_call_count == 1


def test_base_service_context_manager():
    """Test service as context manager."""
    service = MockService()
    assert not service._initialized

    with service as svc:
        assert svc is service
        assert service._initialized
        assert service.is_initialized
        assert service.init_called

    # After exiting context, should be cleaned up
    assert not service._initialized
    assert not service.is_initialized
    assert service.cleanup_called


def test_double_initialization():
    """Test that double initialization is safe (no-op)."""
    service = MockService()
    service.initialize()
    assert service.init_call_count == 1

    service.initialize()  # Should be no-op
    assert service._initialized
    assert service.init_call_count == 1  # Still only called once


def test_double_cleanup():
    """Test that double cleanup is safe (no-op)."""
    service = MockService()
    service.initialize()

    service.cleanup()
    assert service.cleanup_call_count == 1

    service.cleanup()  # Should be no-op
    assert not service._initialized
    assert service.cleanup_call_count == 1  # Still only called once


def test_cleanup_without_initialization():
    """Test cleanup without initialization is safe."""
    service = MockService()
    service.cleanup()  # Should not raise
    assert not service.cleanup_called  # Cleanup not called if never initialized


def test_initialization_failure():
    """Test that initialization failures are propagated."""
    service = FailingInitService()

    with pytest.raises(RuntimeError, match="Initialization failed"):
        service.initialize()

    # Service should not be marked as initialized
    assert not service._initialized
    assert not service.is_initialized


def test_cleanup_failure_is_logged_not_raised():
    """Test that cleanup failures are logged but not raised."""
    service = FailingCleanupService()
    service.initialize()

    # Cleanup should not raise, even though _do_cleanup raises
    service.cleanup()

    # Service should still be marked as not initialized
    # (cleanup completes despite error)
    assert not service._initialized


def test_context_manager_with_exception():
    """Test context manager cleanup happens even on exception."""
    service = MockService()

    with pytest.raises(ValueError):
        with service:
            assert service._initialized
            raise ValueError("Test exception")

    # Cleanup should have happened despite exception
    assert not service._initialized
    assert service.cleanup_called


def test_logger_is_set():
    """Test that logger is properly initialized."""
    service = MockService()
    assert isinstance(service.logger, logging.Logger)
    assert service.logger.name == "MockService"


def test_check_initialized_raises_when_not_initialized():
    """Test that _check_initialized raises when service not initialized."""
    service = MockService()

    with pytest.raises(RuntimeError, match="not initialized"):
        service._check_initialized()


def test_check_initialized_succeeds_when_initialized():
    """Test that _check_initialized succeeds when service initialized."""
    service = MockService()
    service.initialize()

    # Should not raise
    service._check_initialized()


def test_is_initialized_property():
    """Test is_initialized property."""
    service = MockService()
    assert service.is_initialized is False

    service.initialize()
    assert service.is_initialized is True

    service.cleanup()
    assert service.is_initialized is False


def test_context_manager_initialization_failure():
    """Test context manager with initialization failure."""
    service = FailingInitService()

    with pytest.raises(RuntimeError, match="Initialization failed"):
        with service:
            pass

    # Cleanup should not have been called since init failed
    assert not service._initialized


def test_multiple_context_managers():
    """Test using service in multiple context managers."""
    service = MockService()

    with service:
        assert service.init_call_count == 1

    # Should be cleaned up
    assert service.cleanup_call_count == 1

    # Use again
    with service:
        assert service.init_call_count == 2  # Re-initialized

    assert service.cleanup_call_count == 2


def test_service_reinitialization_after_cleanup():
    """Test that service can be reinitialized after cleanup."""
    service = MockService()

    # First lifecycle
    service.initialize()
    assert service.is_initialized
    service.cleanup()
    assert not service.is_initialized

    # Second lifecycle
    service.initialize()
    assert service.is_initialized
    assert service.init_call_count == 2
    service.cleanup()
    assert service.cleanup_call_count == 2
