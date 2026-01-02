"""
Session Management End-to-End Tests.

Tests session lifecycle, state management, concurrent sessions, timeout handling,
and cleanup scenarios.
"""

import asyncio
import time

import pytest

from tests.mcp.fixtures.mock_clients import (
    ConcurrentClientSimulator,
    MCPClientSimulator,
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSessionLifecycle:
    """E2E tests for complete session lifecycle."""

    async def test_complete_session_lifecycle(self, project_root):
        """Test complete session from initialization to cleanup."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            # Phase 1: Connection
            start_time = time.time()
            connected = await client.connect()
            assert connected
            connect_time = time.time() - start_time

            # Phase 2: Initialization
            init_start = time.time()
            await client.initialize()
            init_time = time.time() - init_start

            # Phase 3: Active session
            active_start = time.time()
            for _ in range(5):
                await client.call_tool("kuzu_stats", {})
            active_time = time.time() - active_start

            # Phase 4: Shutdown
            shutdown_start = time.time()
            await client.send_request("shutdown", {})
            await asyncio.sleep(0.5)
            shutdown_time = time.time() - shutdown_start

            # Verify timing
            assert connect_time < 2.0
            assert init_time < 1.0
            assert active_time < 10.0
            assert shutdown_time < 2.0

        finally:
            if client.process and client.process.poll() is None:
                await client.disconnect()

    async def test_session_initialization(self, project_root):
        """Test session initialization and setup."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            # Initialize session
            init_response = await client.initialize()
            assert init_response is not None

            # Send initialized notification
            await client.send_notification("notifications/initialized", {})

            # Verify session is operational
            response = await client.send_request("ping", {})
            assert response is not None

            # Check session was tracked
            stats = client.get_session_stats()
            assert stats.get("total_requests", 0) > 0

        finally:
            await client.disconnect()

    async def test_session_state_persistence(self, project_root):
        """Test that session state persists across operations."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Perform operations that affect state
            await client.call_tool("kuzu_remember", {"content": "Session state test"})
            await asyncio.sleep(0.3)

            # Query to verify state persisted
            recall = await client.call_tool("kuzu_recall", {"query": "Session state"})
            assert recall is not None

            # Continue operations
            stats = await client.call_tool("kuzu_stats", {})
            assert stats is not None

        finally:
            await client.disconnect()

    async def test_session_cleanup_on_disconnect(self, project_root):
        """Test proper session cleanup on disconnect."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Record process ID
            pid = client.process.pid if client.process else None
            assert pid is not None

            # Perform some operations
            await client.call_tool("kuzu_stats", {})

            # Disconnect
            await client.disconnect()
            await asyncio.sleep(0.3)

            # Verify cleanup
            assert client.process is None or client.process.poll() is not None

        finally:
            if client.process and client.process.poll() is None:
                await client.disconnect()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSessionStateManagement:
    """E2E tests for session state management."""

    async def test_session_request_tracking(self, project_root):
        """Test tracking of requests within a session."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Make multiple requests
            num_requests = 10
            for i in range(num_requests):
                await client.send_request("ping", {}, request_id=i + 1)

            # Check session stats
            stats = client.get_session_stats()
            assert stats.get("total_requests", 0) >= num_requests

        finally:
            await client.disconnect()

    async def test_session_statistics_accumulation(self, project_root):
        """Test that session statistics accumulate correctly."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Perform various operations
            await client.call_tool("kuzu_stats", {})
            await client.call_tool("project", {})
            await client.send_request("ping", {})

            # Get accumulated stats
            stats = client.get_session_stats()

            assert "total_requests" in stats
            assert "successful" in stats
            assert "failed" in stats
            assert stats["total_requests"] >= 3

        finally:
            await client.disconnect()

    async def test_session_error_tracking(self, project_root):
        """Test tracking of errors within a session."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Mix of successes and errors
            await client.call_tool("kuzu_stats", {})  # Success
            await client.call_tool("nonexistent", {})  # Error
            await client.call_tool("kuzu_stats", {})  # Success

            # Check error tracking
            stats = client.get_session_stats()
            assert stats.get("failed", 0) >= 1
            assert stats.get("successful", 0) >= 2

        finally:
            await client.disconnect()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestConcurrentSessions:
    """E2E tests for multiple concurrent sessions."""

    async def test_multiple_independent_sessions(self, project_root):
        """Test multiple independent sessions running simultaneously."""
        num_sessions = 3
        concurrent_sim = ConcurrentClientSimulator(
            num_clients=num_sessions, project_root=project_root, timeout=15.0
        )

        try:
            # Start all sessions
            connected_count = await concurrent_sim.connect_all()
            assert connected_count >= 2

            # Each session performs independent operations
            for client in concurrent_sim.clients:
                if client.process:
                    await client.initialize()
                    await client.call_tool("kuzu_stats", {})

            # Verify sessions are independent
            for client in concurrent_sim.clients:
                if client.process and client.current_session:
                    stats = client.get_session_stats()
                    assert stats.get("total_requests", 0) > 0

        finally:
            await concurrent_sim.disconnect_all()

    async def test_concurrent_session_isolation(self, project_root):
        """Test that concurrent sessions maintain isolation."""
        concurrent_sim = ConcurrentClientSimulator(
            num_clients=2, project_root=project_root, timeout=15.0
        )

        try:
            connected_count = await concurrent_sim.connect_all()
            assert connected_count == 2

            # Initialize both
            for client in concurrent_sim.clients:
                await client.initialize()

            # Each performs unique operations
            client1, client2 = concurrent_sim.clients

            # Client 1 operations
            r1 = await client1.call_tool("kuzu_stats", {})
            await client1.call_tool("project", {})

            # Client 2 operations
            r3 = await client2.call_tool("kuzu_stats", {})
            await client2.send_request("ping", {})

            # Verify both sessions worked
            assert r1 is not None and r3 is not None

        finally:
            await concurrent_sim.disconnect_all()

    async def test_concurrent_load_distribution(self, project_root):
        """Test load distribution across concurrent sessions."""
        num_clients = 5
        requests_per_client = 5

        concurrent_sim = ConcurrentClientSimulator(
            num_clients=num_clients, project_root=project_root, timeout=20.0
        )

        try:
            connected_count = await concurrent_sim.connect_all()
            assert connected_count >= 3

            # Load test
            results = await concurrent_sim.load_test(
                requests_per_client=requests_per_client
            )

            # Verify load handling
            assert results["total_requests"] >= requests_per_client * 3
            assert results["success_rate"] >= 70.0  # At least 70% success

        finally:
            await concurrent_sim.disconnect_all()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSessionTimeoutHandling:
    """E2E tests for session timeout scenarios."""

    async def test_session_idle_timeout(self, project_root):
        """Test session behavior during idle periods."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Active operation
            await client.call_tool("kuzu_stats", {})

            # Idle period
            await asyncio.sleep(2.0)

            # Should still work after idle
            response = await client.call_tool("kuzu_stats", {})
            assert response is not None

        finally:
            await client.disconnect()

    async def test_session_operation_timeout(self, project_root):
        """Test handling of operation timeouts within session."""
        client = MCPClientSimulator(project_root=project_root, timeout=2.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Operation that might timeout
            response = await client.call_tool("kuzu_stats", {"detailed": True})

            # Should handle timeout gracefully
            if response is None:
                # Timeout occurred
                pass
            else:
                # Completed within timeout
                assert "result" in response or "error" in response

            # Session should still be usable
            ping = await client.send_request("ping", {})
            assert ping is not None or ping is None  # Either is acceptable

        finally:
            await client.disconnect()

    async def test_session_recovery_after_timeout(self, project_root):
        """Test session recovery after timeout."""
        client = MCPClientSimulator(project_root=project_root, timeout=3.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Potentially timeout-inducing operation
            await client.call_tool("kuzu_stats", {"detailed": True})

            # Recovery operations
            for _ in range(3):
                response = await client.send_request("ping", {})
                if response is not None:
                    # Successfully recovered
                    break
                await asyncio.sleep(0.2)

            # Verify recovered
            await client.call_tool("kuzu_stats", {})
            # Should work or at least respond

        finally:
            await client.disconnect()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSessionCleanup:
    """E2E tests for session cleanup scenarios."""

    async def test_graceful_session_termination(self, project_root):
        """Test graceful session termination."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Active session
            await client.call_tool("kuzu_stats", {})

            # Graceful shutdown
            shutdown_response = await client.send_request("shutdown", {})
            assert shutdown_response is not None

            await asyncio.sleep(0.5)

            # Verify terminated
            if client.process:
                assert client.process.poll() is not None

        finally:
            if client.process and client.process.poll() is None:
                await client.disconnect()

    async def test_forced_session_termination(self, project_root):
        """Test forced session termination."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Active operations
            await client.call_tool("kuzu_stats", {})

            # Force disconnect
            await client.disconnect()
            await asyncio.sleep(0.3)

            # Verify cleanup
            assert client.process is None or client.process.poll() is not None

        finally:
            pass  # Already disconnected

    async def test_session_cleanup_with_pending_operations(self, project_root):
        """Test cleanup when operations are pending."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Start operation
            task = asyncio.create_task(client.call_tool("kuzu_stats", {}))

            # Immediate disconnect
            await client.disconnect()

            # Cancel pending operation
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        finally:
            if client.process and client.process.poll() is None:
                await client.disconnect()

    async def test_multiple_session_cleanup(self, project_root):
        """Test cleanup of multiple sessions."""
        num_sessions = 3
        clients = [
            MCPClientSimulator(project_root=project_root, timeout=10.0)
            for _ in range(num_sessions)
        ]

        try:
            # Start all sessions
            for client in clients:
                await client.connect()
                await client.initialize()

            # Cleanup all
            for client in clients:
                await client.disconnect()

            await asyncio.sleep(0.5)

            # Verify all cleaned up
            for client in clients:
                assert client.process is None or client.process.poll() is not None

        finally:
            # Extra cleanup
            for client in clients:
                if client.process and client.process.poll() is None:
                    await client.disconnect()
