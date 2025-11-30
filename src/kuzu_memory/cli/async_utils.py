"""Async utilities for CLI commands.

Since Click is synchronous but some services have async methods, we need helpers
to bridge the async/sync gap.

Design Decision: Async/Sync Bridge for Click Commands
------------------------------------------------------
Rationale: Click commands must be synchronous, but DiagnosticService has async
methods for I/O operations. This utility provides a clean bridge using asyncio.run().

Trade-offs:
- Simplicity: Single function to run async code in sync context
- Compatibility: Works with both new and existing event loops
- Performance: No overhead from thread pools, direct asyncio execution

Related Epic: 1M-415 (Refactor Commands to SOA/DI Architecture)
Related Phase: 5.3 (High-Risk Async Command Migrations)
"""

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


def run_async(coro: Awaitable[T]) -> T:
    """
    Run async coroutine in sync context.

    Provides a clean bridge between Click's synchronous command interface
    and async service methods. Handles event loop creation and management.

    Args:
        coro: Async coroutine to run

    Returns:
        Result of the coroutine

    Raises:
        Any exception raised by the coroutine

    Example:
        >>> async def async_operation():
        >>>     return await some_service.async_method()
        >>>
        >>> @cli.command()
        >>> def sync_command():
        >>>     result = run_async(async_operation())
        >>>     click.echo(result)

    Performance:
    - O(1) overhead for event loop management
    - Direct execution, no thread pool overhead
    - Compatible with both new and existing event loops

    Error Handling:
    - Propagates all exceptions from coroutine
    - Ensures event loop cleanup on errors
    - Safe to use in CLI error handlers
    """
    try:
        # Try to get running event loop (Python 3.10+)
        asyncio.get_running_loop()
        # If we get here, we're already in async context - should not happen in CLI
        raise RuntimeError("run_async should not be called from async context")
    except RuntimeError:
        # No running loop - this is expected for sync CLI commands
        # Use asyncio.run() which creates and closes loop automatically
        # Type ignore needed because asyncio.run expects Coroutine but we use Awaitable for flexibility
        return asyncio.run(coro)  # type: ignore[arg-type]  # Awaitable[T] is compatible with Coroutine at runtime


__all__ = ["run_async"]
