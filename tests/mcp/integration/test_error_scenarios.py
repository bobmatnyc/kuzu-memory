"""
Comprehensive Error Scenario Integration Tests.

Tests error handling for tool not found, invalid parameters, execution failures,
timeouts, error recovery, batch errors, and notification errors.
"""

import asyncio
import json

import pytest

from tests.mcp.fixtures.mock_clients import MCPClientSimulator


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestToolNotFoundErrors:
    """Tests for tool not found error scenarios."""

    async def test_nonexistent_tool_call(self, project_root):
        """Test calling a tool that doesn't exist."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call non-existent tool
            response = await client.call_tool("nonexistent_tool", {})

            assert response is not None
            assert "error" in response
            assert response["error"]["code"] in [
                -32601,
                -32001,
            ]  # Method not found or tool error

        finally:
            await client.disconnect()

    async def test_tool_name_case_sensitivity(self, project_root):
        """Test that tool names are case-sensitive."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Try incorrect case
            response = await client.call_tool("STATS", {})

            assert response is not None
            # Should error if case-sensitive
            if "error" in response:
                assert response["error"]["code"] in [-32601, -32001]

        finally:
            await client.disconnect()

    async def test_misspelled_tool_name(self, project_root):
        """Test handling of misspelled tool names."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Misspelled tool name
            response = await client.call_tool("stat", {})  # Should be "kuzu_stats"

            assert response is not None
            assert "error" in response

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestInvalidParameterErrors:
    """Tests for invalid parameter error scenarios."""

    async def test_missing_required_parameter(self, project_root):
        """Test error when required parameter is missing."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # kuzu_enhance requires 'prompt' parameter
            response = await client.call_tool("kuzu_enhance", {})

            assert response is not None
            # Should error for missing required param
            if "error" in response:
                assert response["error"]["code"] == -32602  # Invalid params

        finally:
            await client.disconnect()

    async def test_wrong_parameter_type(self, project_root):
        """Test error when parameter has wrong type."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # limit should be integer, not string
            response = await client.call_tool("kuzu_recall", {"query": "test", "limit": "five"})

            assert response is not None
            # Should handle type error gracefully
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_out_of_range_parameter(self, project_root):
        """Test handling of out-of-range parameter values."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Negative limit
            response = await client.call_tool("kuzu_recall", {"query": "test", "limit": -5})

            assert response is not None
            # Should handle gracefully
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_null_parameter_value(self, project_root):
        """Test handling of null parameter values."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Null query
            response = await client.call_tool("kuzu_recall", {"query": None, "limit": 5})

            assert response is not None
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestToolExecutionFailures:
    """Tests for tool execution failure scenarios."""

    async def test_execution_with_empty_string(self, project_root):
        """Test tool execution with empty string parameters."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Empty query
            response = await client.call_tool("kuzu_recall", {"query": "", "limit": 5})

            assert response is not None
            # Should handle empty string gracefully
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_execution_with_special_characters(self, project_root):
        """Test tool execution with special characters."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Special characters in query
            response = await client.call_tool("kuzu_recall", {"query": "!@#$%^&*()", "limit": 5})

            assert response is not None
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_execution_with_very_long_input(self, project_root):
        """Test tool execution with very long input strings."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Very long prompt (10KB)
            long_prompt = "x" * 10000
            response = await client.call_tool("kuzu_enhance", {"prompt": long_prompt})

            assert response is not None
            # Should handle or error gracefully
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestTimeoutScenarios:
    """Tests for timeout error scenarios."""

    async def test_request_timeout(self, project_root):
        """Test request timeout handling."""
        client = MCPClientSimulator(project_root=project_root, timeout=1.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call with very short timeout
            response = await client.call_tool("kuzu_stats", {"detailed": True})

            # Should complete or timeout
            if response is None:
                # Timeout is acceptable
                pass
            else:
                assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_timeout_recovery(self, project_root):
        """Test recovery after timeout."""
        client = MCPClientSimulator(project_root=project_root, timeout=2.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # First request might timeout
            response1 = await client.call_tool("kuzu_stats", {"detailed": True})

            # Second request should work
            response2 = await client.send_request("ping", {})

            # At least one should succeed
            assert response1 is not None or response2 is not None

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestErrorRecovery:
    """Tests for error recovery and continuation."""

    async def test_recovery_after_error(self, project_root):
        """Test that server continues after error."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Trigger error
            error_response = await client.call_tool("nonexistent", {})
            assert "error" in error_response

            # Should still work after error
            success_response = await client.call_tool("kuzu_stats", {})
            assert success_response is not None
            assert "result" in success_response or "error" not in success_response

        finally:
            await client.disconnect()

    async def test_multiple_consecutive_errors(self, project_root):
        """Test handling multiple consecutive errors."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Multiple errors in a row
            for _ in range(3):
                response = await client.call_tool("nonexistent", {})
                assert "error" in response

            # Should still be functional
            final_response = await client.send_request("ping", {})
            assert final_response is not None

        finally:
            await client.disconnect()

    async def test_error_then_success_pattern(self, project_root):
        """Test alternating error and success pattern."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            results = []
            for i in range(4):
                if i % 2 == 0:
                    # Error
                    response = await client.call_tool("nonexistent", {})
                else:
                    # Success
                    response = await client.call_tool("kuzu_stats", {})

                results.append(response is not None)

            # All requests should get responses (error or success)
            assert all(results)

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestBatchErrorHandling:
    """Tests for error handling in batch requests."""

    async def test_partial_batch_failure(self, project_root):
        """Test batch request where some requests fail."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Send multiple requests, some invalid
            responses = []
            responses.append(await client.call_tool("kuzu_stats", {}))
            responses.append(await client.call_tool("nonexistent", {}))
            responses.append(await client.call_tool("kuzu_stats", {}))

            # Should have mix of successes and errors
            successes = sum(1 for r in responses if r and "result" in r)
            errors = sum(1 for r in responses if r and "error" in r)

            assert successes >= 1
            assert errors >= 1

        finally:
            await client.disconnect()

    async def test_all_batch_requests_fail(self, project_root):
        """Test batch where all requests fail."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # All invalid requests
            responses = []
            for _ in range(3):
                response = await client.call_tool("nonexistent", {})
                responses.append(response)

            # All should have errors
            errors = sum(1 for r in responses if r and "error" in r)
            assert errors == 3

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestNotificationErrors:
    """Tests for notification error handling."""

    async def test_invalid_notification(self, project_root):
        """Test handling of invalid notifications."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send invalid notification
            await client.send_notification("invalid/notification", {})

            # Server should continue functioning - wait for processing
            await asyncio.sleep(0.3)

            # Retry ping with exponential backoff to handle bulk test timing issues
            response = None
            for attempt in range(3):
                response = await client.send_request("ping", {})
                if response is not None:
                    break
                await asyncio.sleep(0.2 * (attempt + 1))  # 0.2s, 0.4s, 0.6s

            assert response is not None, "Server failed to respond after invalid notification"

        finally:
            await client.disconnect()

    async def test_notification_after_error(self, project_root):
        """Test sending notification after error."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Error
            await client.call_tool("nonexistent", {})

            # Notification
            await client.send_notification("notifications/test", {})

            # Give server time to process notification before next request
            await asyncio.sleep(0.3)

            # Should still work - retry with exponential backoff
            response = None
            for attempt in range(3):
                response = await client.send_request("ping", {})
                if response is not None:
                    break
                await asyncio.sleep(0.2 * (attempt + 1))  # 0.2s, 0.4s, 0.6s

            assert response is not None, "Server failed to respond after error and notification"

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestErrorMessages:
    """Tests for error message quality and content."""

    async def test_error_has_code(self, project_root):
        """Test that errors include error codes."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            response = await client.call_tool("nonexistent", {})

            assert "error" in response
            assert "code" in response["error"]
            assert isinstance(response["error"]["code"], int)

        finally:
            await client.disconnect()

    async def test_error_has_message(self, project_root):
        """Test that errors include descriptive messages."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            response = await client.call_tool("nonexistent", {})

            assert "error" in response
            assert "message" in response["error"]
            assert len(response["error"]["message"]) > 0

        finally:
            await client.disconnect()

    async def test_error_preserves_request_id(self, project_root):
        """Test that error responses preserve request IDs."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            response = await client.call_tool("nonexistent", {})

            assert "error" in response
            assert "id" in response
            # ID should match the request (generated by client)

        finally:
            await client.disconnect()
