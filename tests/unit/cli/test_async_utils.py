"""Tests for async utilities (async/sync bridge)."""

import asyncio

import pytest

from kuzu_memory.cli.async_utils import run_async


class TestAsyncUtils:
    """Test async/sync bridge utilities."""

    def test_run_async_simple(self):
        """Test running simple async coroutine."""

        async def simple_coro():
            return "test_result"

        result = run_async(simple_coro())
        assert result == "test_result"

    def test_run_async_with_await(self):
        """Test running async coroutine with await."""

        async def async_operation():
            await asyncio.sleep(0.01)
            return 42

        result = run_async(async_operation())
        assert result == 42

    def test_run_async_propagates_exception(self):
        """Test that exceptions are properly propagated."""

        async def failing_coro():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            run_async(failing_coro())

    def test_run_async_multiple_calls(self):
        """Test multiple sequential async calls."""

        async def counter(n):
            await asyncio.sleep(0.001)
            return n * 2

        result1 = run_async(counter(5))
        result2 = run_async(counter(10))

        assert result1 == 10
        assert result2 == 20

    def test_run_async_with_complex_return(self):
        """Test running async coroutine with complex return value."""

        async def complex_coro():
            await asyncio.sleep(0.001)
            return {"status": "success", "data": [1, 2, 3]}

        result = run_async(complex_coro())
        assert result == {"status": "success", "data": [1, 2, 3]}
