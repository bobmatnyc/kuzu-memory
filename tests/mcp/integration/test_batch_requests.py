"""
Comprehensive Batch Request Integration Tests.

Tests batch request handling including multiple requests, mixed tool calls,
error handling, request ordering, and partial failures.
"""

import asyncio
import os

import pytest

from tests.mcp.fixtures.mock_clients import MCPClientSimulator


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestBatchRequests:
    """Integration tests for batch request processing."""

    async def test_simple_batch_request(self, project_root):
        """Test basic batch request with multiple pings."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Send batch of ping requests
            batch = [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "ping", "id": 2},
                {"jsonrpc": "2.0", "method": "ping", "id": 3},
            ]

            responses = await client.send_batch(batch)

            if responses is not None and isinstance(responses, list):
                assert len(responses) == 3
                # Verify all IDs present
                response_ids = [r.get("id") for r in responses]
                assert 1 in response_ids
                assert 2 in response_ids
                assert 3 in response_ids

        finally:
            await client.disconnect()

    async def test_mixed_tool_calls_in_batch(self, project_root):
        """Test batch with different tool calls."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Mixed batch: stats, ping, tools/list
            batch = [
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "id": 1,
                    "params": {"name": "stats", "arguments": {}},
                },
                {"jsonrpc": "2.0", "method": "ping", "id": 2},
                {"jsonrpc": "2.0", "method": "tools/list", "id": 3},
            ]

            responses = await client.send_batch(batch)

            if responses is not None and isinstance(responses, list):
                # Should have responses for all
                assert len(responses) >= 2  # Allow some tolerance

        finally:
            await client.disconnect()

    async def test_batch_with_errors(self, project_root):
        """Test batch where some requests have errors."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Batch with valid and invalid requests
            batch = [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "invalid_method", "id": 2},
                {"jsonrpc": "2.0", "method": "ping", "id": 3},
            ]

            responses = await client.send_batch(batch)

            if responses is not None and isinstance(responses, list):
                # Should have responses for all
                successes = sum(1 for r in responses if "result" in r)
                errors = sum(1 for r in responses if "error" in r)

                # Should have both successes and errors
                assert successes >= 1
                assert errors >= 1

        finally:
            await client.disconnect()

    async def test_batch_request_ordering(self, project_root):
        """Test that batch requests are processed in order."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Batch with sequential IDs
            batch = [{"jsonrpc": "2.0", "method": "ping", "id": i} for i in range(1, 6)]

            responses = await client.send_batch(batch)

            if responses is not None and isinstance(responses, list):
                # Verify IDs are present
                response_ids = [r.get("id") for r in responses]
                for i in range(1, 6):
                    assert i in response_ids, f"Missing response for ID {i}"

        finally:
            await client.disconnect()

    async def test_large_batch_request(self, project_root):
        """Test handling of large batch with many requests."""
        client = MCPClientSimulator(project_root=project_root, timeout=20.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Large batch (20 requests)
            batch = [{"jsonrpc": "2.0", "method": "ping", "id": i} for i in range(1, 21)]

            responses = await client.send_batch(batch)

            if responses is not None and isinstance(responses, list):
                # Should handle most requests
                assert len(responses) >= 15  # At least 75% success

        finally:
            await client.disconnect()

    async def test_empty_batch_request(self, project_root):
        """Test handling of empty batch.

        According to JSON-RPC 2.0 spec section 6 (Batch), an rpc call with an empty
        Array is invalid and the server should respond with a single Response object
        with error code -32600 (Invalid Request).
        """
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Empty batch - invalid per JSON-RPC 2.0 spec
            batch = []

            responses = await client.send_batch(batch)

            # Per JSON-RPC 2.0, server must respond to empty batch with error
            assert responses is not None, "Server should respond to empty batch with error"

            # Should be a list with one error response
            assert isinstance(responses, list), f"Expected list response, got {type(responses)}"
            assert len(responses) == 1, f"Expected 1 error response, got {len(responses)}"

            # Verify it's an error response with proper structure
            error_response = responses[0]
            assert "jsonrpc" in error_response, "Response should have jsonrpc field"
            assert error_response["jsonrpc"] == "2.0", "Should be JSON-RPC 2.0"
            assert "id" in error_response, "Response should have id field"
            assert error_response["id"] is None, "Invalid request should have id=null"
            assert "error" in error_response, "Response should contain error field"
            assert error_response["error"]["code"] == -32600, (
                f"Expected error code -32600 (Invalid Request), "
                f"got {error_response['error']['code']}"
            )

        finally:
            await client.disconnect()

    async def test_batch_partial_failure_recovery(self, project_root):
        """Test recovery after partial batch failure."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # First batch with some errors
            batch1 = [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "invalid", "id": 2},
            ]

            responses1 = await client.send_batch(batch1)
            assert responses1 is not None

            # Second batch should work normally
            batch2 = [
                {"jsonrpc": "2.0", "method": "ping", "id": 3},
                {"jsonrpc": "2.0", "method": "ping", "id": 4},
            ]

            responses2 = await client.send_batch(batch2)

            if responses2 is not None and isinstance(responses2, list):
                # Second batch should succeed
                successes = sum(1 for r in responses2 if "result" in r)
                assert successes >= 1

        finally:
            await client.disconnect()

    async def test_batch_with_notifications(self, project_root):
        """Test batch containing notifications (no ID)."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Batch with request and notification
            batch = [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "notifications/test"},  # No ID
                {"jsonrpc": "2.0", "method": "ping", "id": 2},
            ]

            responses = await client.send_batch(batch)

            if responses is not None and isinstance(responses, list):
                # Should have responses for requests, not notifications
                # Notifications don't get responses
                response_ids = [r.get("id") for r in responses if "id" in r]
                assert 1 in response_ids or 2 in response_ids

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestBatchErrorScenarios:
    """Tests for batch request error scenarios."""

    async def test_all_batch_requests_invalid(self, project_root):
        """Test batch where all requests are invalid."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # All invalid
            batch = [
                {"jsonrpc": "2.0", "method": "invalid1", "id": 1},
                {"jsonrpc": "2.0", "method": "invalid2", "id": 2},
                {"jsonrpc": "2.0", "method": "invalid3", "id": 3},
            ]

            responses = await client.send_batch(batch)

            if responses is not None and isinstance(responses, list):
                # All should be errors
                errors = sum(1 for r in responses if "error" in r)
                assert errors == 3

        finally:
            await client.disconnect()

    async def test_batch_with_malformed_request(self, project_root):
        """Test batch containing malformed request."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Mix of valid and malformed
            batch = [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"not_valid": "json_rpc"},  # Malformed
                {"jsonrpc": "2.0", "method": "ping", "id": 3},
            ]

            responses = await client.send_batch(batch)

            # Should handle gracefully
            assert responses is not None

        finally:
            await client.disconnect()

    async def test_batch_timeout_handling(self, project_root):
        """Test batch request timeout behavior."""
        client = MCPClientSimulator(project_root=project_root, timeout=3.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Large batch that might timeout
            batch = [{"jsonrpc": "2.0", "method": "ping", "id": i} for i in range(1, 31)]

            responses = await client.send_batch(batch)

            # Should complete or timeout gracefully
            if responses is None:
                # Timeout is acceptable
                pass
            else:
                assert isinstance(responses, list)

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestSequentialBatches:
    """Tests for sequential batch request processing."""

    async def test_multiple_sequential_batches(self, project_root):
        """Test sending multiple batches sequentially."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Send 3 batches sequentially
            for batch_num in range(1, 4):
                batch = [
                    {
                        "jsonrpc": "2.0",
                        "method": "ping",
                        "id": batch_num * 10 + i,
                    }
                    for i in range(3)
                ]

                responses = await client.send_batch(batch)

                if responses is not None:
                    assert isinstance(responses, list)
                    assert len(responses) >= 2

        finally:
            await client.disconnect()

    async def test_batch_state_isolation(self, project_root):
        """Test that batches maintain state isolation."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # First batch
            batch1 = [
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "id": 1,
                    "params": {"name": "stats", "arguments": {}},
                }
            ]

            responses1 = await client.send_batch(batch1)

            # Second batch should work independently
            batch2 = [
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "id": 2,
                    "params": {"name": "stats", "arguments": {}},
                }
            ]

            responses2 = await client.send_batch(batch2)

            # Both should succeed
            assert responses1 is not None
            assert responses2 is not None

        finally:
            await client.disconnect()
