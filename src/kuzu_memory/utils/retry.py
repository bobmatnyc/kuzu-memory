"""
Retry logic and resilience patterns for KuzuMemory.

Provides decorators and utilities for implementing retry logic,
circuit breakers, and other resilience patterns.
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for exponential backoff retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to delays
        exceptions: Tuple of exceptions to catch and retry
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Add jitter if enabled
                    if jitter:
                        import random

                        delay *= 0.5 + random.random()

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)

            # This shouldn't be reached, but just in case
            if last_exception:
                raise last_exception
            # If somehow we get here with no exception, raise a runtime error
            raise RuntimeError(f"{func.__name__} failed all retries without capturing exception")

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    class State:
        CLOSED = "CLOSED"
        OPEN = "OPEN"
        HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
        name: str | None = None,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to track
            name: Optional name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or "CircuitBreaker"

        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = self.State.CLOSED

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to apply circuit breaker to a function."""

        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable[..., T], *args: object, **kwargs: object) -> T:
        """
        Call function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == self.State.OPEN:
            if self._should_attempt_reset():
                self.state = self.State.HALF_OPEN
                logger.info(f"{self.name}: Attempting reset (HALF_OPEN)")
            else:
                raise Exception(f"{self.name}: Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == self.State.HALF_OPEN:
            logger.info(f"{self.name}: Circuit breaker reset (CLOSED)")
        self.failure_count = 0
        self.state = self.State.CLOSED

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = self.State.OPEN
            logger.error(f"{self.name}: Circuit breaker opened after {self.failure_count} failures")

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.State.CLOSED
        logger.info(f"{self.name}: Manually reset")

    def get_state(self) -> dict[str, object]:
        """Get current state information."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
        }


def retry_with_fallback(
    primary_func: Callable[..., T],
    fallback_func: Callable[..., T],
    max_retries: int = 2,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[..., T]:
    """
    Create a function that retries primary and falls back to secondary.

    Args:
        primary_func: Primary function to try
        fallback_func: Fallback function if primary fails
        max_retries: Number of retries for primary
        exceptions: Exceptions to catch

    Returns:
        Wrapped function with retry and fallback logic
    """

    @wraps(primary_func)
    def wrapper(*args: object, **kwargs: object) -> T:
        # Try primary function with retries
        for attempt in range(max_retries):
            try:
                return primary_func(*args, **kwargs)
            except exceptions as e:
                if attempt == max_retries - 1:
                    logger.warning(
                        f"{primary_func.__name__} failed after {max_retries} attempts, "
                        f"falling back to {fallback_func.__name__}: {e}"
                    )
                    break
                time.sleep(0.1 * (2**attempt))  # Simple exponential backoff

        # Fall back to secondary function
        try:
            return fallback_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback {fallback_func.__name__} also failed: {e}")
            raise

    return wrapper
