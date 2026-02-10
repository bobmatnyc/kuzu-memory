"""
Comprehensive MCP Connection Integration Tests.

Tests all connection scenarios including startup, handshake, reconnection,
timeout handling, graceful shutdown, and protocol version negotiation.
"""

import asyncio
import os
import time

import pytest

from tests.mcp.fixtures.mock_clients import MCPClientSimulator


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestConnectionIntegration:
    """Integration tests for MCP connection scenarios."""

    async def test_successful_connection_and_handshake(self, project_root):
        """Test successful connection establishment and protocol handshake."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            # Connect to server
            connected = await client.connect()
            assert connected, "Failed to establish connection"

            # Initialize protocol
            response = await client.initialize(protocol_version="2025-06-18")
            assert response is not None, "No initialization response"
            assert "result" in response or "error" not in response
            assert response.get("jsonrpc") == "2.0"

        finally:
            await client.disconnect()

    async def test_connection_timeout_handling(self, project_root):
        """Test connection timeout when server doesn't respond."""
        client = MCPClientSimulator(project_root=project_root, timeout=1.0)

        try:
            connected = await client.connect()
            assert connected

            # Send request with short timeout
            start = time.time()
            # This should timeout if server takes too long
            await client.send_request("ping", {})
            duration = time.time() - start

            # Should complete within timeout or timeout properly
            assert duration < 2.0, "Timeout not enforced"

        finally:
            await client.disconnect()

    async def test_reconnection_after_disconnect(self, project_root):
        """Test reconnection capability after disconnection."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            # First connection
            connected1 = await client.connect()
            assert connected1, "First connection failed"

            response1 = await client.send_request("ping", {})
            assert response1 is not None

            # Disconnect
            await client.disconnect()
            await asyncio.sleep(0.2)

            # Reconnect
            connected2 = await client.connect()
            assert connected2, "Reconnection failed"

            response2 = await client.send_request("ping", {})
            assert response2 is not None

        finally:
            await client.disconnect()

    async def test_graceful_shutdown(self, project_root):
        """Test graceful server shutdown via shutdown method."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send shutdown request
            response = await client.send_request("shutdown", {})
            assert response is not None

            # Wait for graceful shutdown with retry logic (exponential backoff)
            max_retries = 5
            for attempt in range(max_retries):
                await asyncio.sleep(0.2 * (2**attempt))  # 0.2s, 0.4s, 0.8s, 1.6s, 3.2s

                if client.process and client.process.poll() is not None:
                    # Process terminated successfully
                    break
            else:
                # All retries exhausted
                if client.process:
                    assert (
                        client.process.poll() is not None
                    ), "Server did not shut down gracefully after 6.2s"

        finally:
            # Ensure cleanup
            if client.process and client.process.poll() is None:
                await client.disconnect()

    async def test_connection_with_invalid_protocol_version(self, project_root):
        """Test server response to invalid protocol version."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Try invalid protocol version
            response = await client.initialize(protocol_version="1.0.0")
            assert response is not None

            # Should either accept or reject gracefully
            # Both are valid behaviors
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_multiple_sequential_connections(self, project_root):
        """Test multiple sequential connection cycles."""
        num_cycles = 3
        successful_cycles = 0

        for _i in range(num_cycles):
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)

            try:
                connected = await client.connect()
                if not connected:
                    continue

                response = await client.send_request("ping", {})
                if response is not None:
                    successful_cycles += 1

            finally:
                await client.disconnect()
                await asyncio.sleep(0.2)  # Brief pause between cycles

        # At least 2 out of 3 should succeed (allowing for flakiness)
        assert (
            successful_cycles >= 2
        ), f"Only {successful_cycles}/{num_cycles} succeeded"

    async def test_connection_with_immediate_request(self, project_root):
        """Test sending request immediately after connection."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send request immediately without initialization
            response = await client.send_request("ping", {})

            # Should handle gracefully (accept or error)
            assert response is not None

        finally:
            await client.disconnect()

    async def test_connection_persistence_across_requests(self, project_root):
        """Test that connection remains stable across multiple requests."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send multiple requests
            for i in range(5):
                response = await client.send_request("ping", {}, request_id=i + 1)
                assert response is not None, f"Request {i + 1} failed"
                assert (
                    response.get("id") == i + 1
                ), f"Response ID mismatch for request {i + 1}"

        finally:
            await client.disconnect()

    async def test_connection_recovery_after_error(self, project_root):
        """Test connection recovery after encountering an error."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send invalid request to trigger error
            response1 = await client.send_request("invalid_method", {})
            # Should get error response, not disconnect
            assert response1 is not None

            # Connection should still work
            response2 = await client.send_request("ping", {})
            assert response2 is not None, "Connection failed after error"

        finally:
            await client.disconnect()

    async def test_connection_with_rapid_requests(self, project_root):
        """Test connection stability with rapid sequential requests."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send rapid requests
            responses = []
            for i in range(10):
                response = await client.send_request("ping", {}, request_id=i)
                responses.append(response)

            # Most should succeed
            successful = sum(1 for r in responses if r is not None)
            assert successful >= 8, f"Only {successful}/10 rapid requests succeeded"

        finally:
            await client.disconnect()

    async def test_connection_process_stability(self, project_root):
        """Test that server process remains stable during connection lifecycle."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            initial_pid = client.process.pid if client.process else None
            assert initial_pid is not None

            # Send several requests
            for _ in range(5):
                await client.send_request("ping", {})
                await asyncio.sleep(0.1)

                # Process should still be running with same PID
                assert client.process is not None
                assert client.process.poll() is None, "Process terminated unexpectedly"
                assert client.process.pid == initial_pid, "Process PID changed"

        finally:
            await client.disconnect()

    async def test_connection_initialization_flow(self, project_root):
        """Test complete connection initialization flow."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            # Step 1: Connect
            connected = await client.connect()
            assert connected, "Connection failed"

            # Step 2: Initialize protocol
            init_response = await client.initialize()
            assert init_response is not None, "Initialization failed"

            # Step 3: Send initialized notification
            await client.send_notification("notifications/initialized", {})

            # Step 4: Wait for server to process notification before next request
            # Notifications are fire-and-forget, but server needs time to process
            await asyncio.sleep(0.3)

            # Step 5: Verify operational with retry logic
            ping_response = None
            for attempt in range(3):
                ping_response = await client.send_request("ping", {})
                if ping_response is not None:
                    break
                await asyncio.sleep(0.2 * (attempt + 1))  # 0.2s, 0.4s, 0.6s

            assert (
                ping_response is not None
            ), "Post-initialization ping failed after retries"

        finally:
            await client.disconnect()

    async def test_connection_timeout_values(self, project_root):
        """Test connection behavior with different timeout values."""
        timeout_values = [1.0, 3.0, 5.0]

        for timeout in timeout_values:
            client = MCPClientSimulator(project_root=project_root, timeout=timeout)

            try:
                connected = await client.connect()
                assert connected, f"Connection failed with timeout={timeout}"

                start = time.time()
                response = await client.send_request("ping", {})
                duration = time.time() - start

                assert response is not None, f"Request failed with timeout={timeout}"
                assert (
                    duration < timeout
                ), f"Request exceeded timeout: {duration}s > {timeout}s"

            finally:
                await client.disconnect()

    async def test_connection_with_server_ready_check(self, project_root):
        """Test connection with explicit server readiness verification."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Wait for server to be ready
            max_retries = 5
            ready = False

            for _attempt in range(max_retries):
                try:
                    response = await client.send_request("ping", {})
                    if response is not None:
                        ready = True
                        break
                except Exception:
                    pass

                await asyncio.sleep(0.2)

            assert ready, "Server not ready after connection"

        finally:
            await client.disconnect()

    async def test_connection_resource_cleanup(self, project_root):
        """Test that connection cleanup properly releases resources."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            process = client.process
            assert process is not None

            # Disconnect should clean up
            await client.disconnect()
            await asyncio.sleep(0.3)

            # Process should be terminated
            assert process.poll() is not None, "Process not terminated after disconnect"

        finally:
            # Extra cleanup
            if client.process and client.process.poll() is None:
                await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestConnectionPoolManagement:
    """Tests for connection pool management scenarios."""

    async def test_sequential_connection_reuse(self, project_root):
        """Test sequential connection establishment and cleanup."""
        for i in range(3):
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)

            try:
                connected = await client.connect()
                assert connected, f"Connection {i + 1} failed"

                response = await client.send_request("ping", {})
                assert response is not None

            finally:
                await client.disconnect()
                await asyncio.sleep(0.2)

    async def test_connection_state_isolation(self, project_root):
        """Test that each connection maintains isolated state."""
        client1 = MCPClientSimulator(project_root=project_root, timeout=5.0)
        client2 = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            # Connect both
            c1 = await client1.connect()
            c2 = await client2.connect()
            assert c1 and c2

            # Each should have independent process
            assert client1.process is not None
            assert client2.process is not None
            assert client1.process.pid != client2.process.pid

            # Both should work independently
            r1 = await client1.send_request("ping", {}, request_id=1)
            r2 = await client2.send_request("ping", {}, request_id=2)

            assert r1 is not None and r2 is not None

        finally:
            await client1.disconnect()
            await client2.disconnect()
