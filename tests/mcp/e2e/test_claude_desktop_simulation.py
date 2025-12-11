"""
Claude Desktop Client Simulation End-to-End Tests.

Simulates complete Claude Desktop client workflows including initialization,
tool discovery, sequential operations, session persistence, and real-world
usage patterns.
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
class TestClaudeDesktopInitialization:
    """E2E tests for Claude Desktop initialization flow."""

    async def test_complete_initialization_flow(self, project_root):
        """Test complete initialization as Claude Desktop would perform it."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            # Step 1: Connect to server
            connected = await client.connect()
            assert connected, "Failed to connect to MCP server"

            # Step 2: Send initialize request
            init_response = await client.initialize(protocol_version="2025-06-18")
            assert init_response is not None
            assert "result" in init_response or "error" not in init_response

            # Step 3: Send initialized notification
            await client.send_notification("notifications/initialized", {})

            # Step 4: Discover tools
            tools_response = await client.list_tools()
            assert tools_response is not None
            assert "result" in tools_response

            # Step 5: Verify operational with ping
            ping_response = await client.send_request("ping", {})
            assert ping_response is not None

        finally:
            await client.disconnect()

    async def test_initialization_with_protocol_negotiation(self, project_root):
        """Test protocol version negotiation during initialization."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            # Try with different protocol versions
            versions = ["2025-06-18", "2024-11-05"]

            for version in versions:
                response = await client.initialize(protocol_version=version)
                assert response is not None
                # Should accept or reject gracefully

        finally:
            await client.disconnect()

    async def test_initialization_timeout_handling(self, project_root):
        """Test initialization with timeout constraints."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            start = time.time()
            init_response = await client.initialize()
            duration = time.time() - start

            assert init_response is not None
            assert duration < 5.0, "Initialization took too long"

        finally:
            await client.disconnect()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestClaudeDesktopToolDiscovery:
    """E2E tests for tool discovery workflow."""

    async def test_complete_tool_discovery_workflow(self, project_root):
        """Test complete tool discovery as Claude Desktop would perform it."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Discover tools
            tools_response = await client.list_tools()
            assert tools_response is not None
            assert "result" in tools_response

            tools = tools_response["result"].get("tools", [])

            # Verify all expected tools are present
            tool_names = [t.get("name") for t in tools]
            expected = [
                "enhance",
                "learn",
                "recall",
                "remember",
                "stats",
                "recent",
                "cleanup",
                "project",
                "init",
            ]

            for tool in expected:
                assert tool in tool_names, f"Missing tool: {tool}"

            # Verify each tool has required metadata
            for tool in tools:
                assert "name" in tool
                assert "description" in tool
                assert len(tool["description"]) > 0

        finally:
            await client.disconnect()

    async def test_tool_capability_inspection(self, project_root):
        """Test inspecting tool capabilities and parameters."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            tools_response = await client.list_tools()
            tools = tools_response["result"].get("tools", [])

            # Find enhance tool and inspect its schema
            enhance_tool = next((t for t in tools if t["name"] == "enhance"), None)
            assert enhance_tool is not None

            # Should have parameter schema
            assert "inputSchema" in enhance_tool or "parameters" in enhance_tool

        finally:
            await client.disconnect()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestClaudeDesktopToolExecution:
    """E2E tests for sequential tool execution patterns."""

    async def test_memory_workflow_sequence(self, project_root):
        """Test complete memory workflow: remember → recall → enhance."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Step 1: Remember something
            remember_response = await client.call_tool(
                "remember", {"content": "Test memory for E2E workflow", "source": "e2e"}
            )
            assert remember_response is not None

            # Wait for async processing
            await asyncio.sleep(0.5)

            # Step 2: Recall the memory
            recall_response = await client.call_tool(
                "recall", {"query": "E2E workflow", "limit": 5}
            )
            assert recall_response is not None

            # Step 3: Enhance prompt with memories
            enhance_response = await client.call_tool(
                "enhance", {"prompt": "Continue E2E test", "limit": 5}
            )
            assert enhance_response is not None

        finally:
            await client.disconnect()

    async def test_stats_and_cleanup_workflow(self, project_root):
        """Test stats inspection and cleanup workflow."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Step 1: Get current stats
            stats_response = await client.call_tool("stats", {"format": "json"})
            assert stats_response is not None

            # Step 2: Check recent memories
            recent_response = await client.call_tool("recent", {"limit": 5})
            assert recent_response is not None

            # Step 3: Dry-run cleanup
            cleanup_response = await client.call_tool("cleanup", {"dry_run": True})
            assert cleanup_response is not None

        finally:
            await client.disconnect()

    async def test_project_inspection_workflow(self, project_root):
        """Test project inspection and initialization workflow."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Step 1: Get project info
            project_response = await client.call_tool("project", {"verbose": False})
            assert project_response is not None

            # Step 2: Ensure initialized (idempotent)
            init_response = await client.call_tool("init", {})
            assert init_response is not None

        finally:
            await client.disconnect()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestClaudeDesktopSessionPersistence:
    """E2E tests for session persistence and state management."""

    async def test_long_running_session(self, project_root):
        """Test long-running session with multiple operations."""
        client = MCPClientSimulator(project_root=project_root, timeout=20.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Perform 10 operations
            for _ in range(10):
                response = await client.call_tool("stats", {"format": "json"})
                assert response is not None

                # Brief pause between operations
                await asyncio.sleep(0.2)

            # Verify session still healthy
            final_ping = await client.send_request("ping", {})
            assert final_ping is not None

        finally:
            await client.disconnect()

    async def test_session_with_mixed_operations(self, project_root):
        """Test session with mix of requests, notifications, and tool calls."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Mix of operations
            operations = [
                ("request", "ping", {}),
                ("notification", "notifications/test", {}),
                ("tool", "stats", {}),
                ("request", "ping", {}),
                ("tool", "project", {}),
            ]

            for op_type, method, params in operations:
                if op_type == "request":
                    response = await client.send_request(method, params)
                    assert response is not None
                elif op_type == "notification":
                    await client.send_notification(method, params)
                elif op_type == "tool":
                    response = await client.call_tool(method, params)
                    assert response is not None

                await asyncio.sleep(0.1)

        finally:
            await client.disconnect()

    async def test_session_recovery_patterns(self, project_root):
        """Test session recovery from various error conditions."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Pattern: success → error → success
            success1 = await client.call_tool("stats", {})
            assert success1 is not None

            # Trigger error
            error = await client.call_tool("nonexistent", {})
            assert "error" in error

            # Should recover
            success2 = await client.call_tool("stats", {})
            assert success2 is not None

        finally:
            await client.disconnect()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestClaudeDesktopConcurrentSessions:
    """E2E tests for concurrent session handling."""

    async def test_multiple_concurrent_sessions(self, project_root):
        """Test multiple Claude Desktop sessions running concurrently."""
        num_sessions = 3
        concurrent_sim = ConcurrentClientSimulator(
            num_clients=num_sessions, project_root=project_root, timeout=10.0
        )

        try:
            # Connect all clients
            connected_count = await concurrent_sim.connect_all()
            assert connected_count >= 2, f"Only {connected_count}/{num_sessions} connected"

            # Each session performs operations
            results = await concurrent_sim.concurrent_requests("ping", {})

            # Most should succeed
            successful = sum(1 for r in results if r is not None and "result" in r)
            assert successful >= 2

        finally:
            await concurrent_sim.disconnect_all()

    async def test_concurrent_tool_execution(self, project_root):
        """Test concurrent tool execution from multiple sessions."""
        concurrent_sim = ConcurrentClientSimulator(
            num_clients=3, project_root=project_root, timeout=15.0
        )

        try:
            connected_count = await concurrent_sim.connect_all()
            assert connected_count >= 2

            # Initialize all clients
            for client in concurrent_sim.clients:
                if client.process:
                    await client.initialize()

            # Concurrent tool calls
            tasks = [
                client.call_tool("stats", {}) for client in concurrent_sim.clients if client.process
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
            assert successful >= 2

        finally:
            await concurrent_sim.disconnect_all()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestClaudeDesktopRealWorldPatterns:
    """E2E tests simulating real-world usage patterns."""

    async def test_coding_assistant_pattern(self, project_root):
        """Simulate Claude Code assistant workflow."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Pattern: enhance prompt → execute → learn from result
            # 1. Enhance coding prompt
            enhance = await client.call_tool(
                "enhance", {"prompt": "Help me write a Python function", "limit": 5}
            )
            assert enhance is not None

            # 2. Learn from interaction
            learn = await client.call_tool(
                "learn", {"content": "User requested Python function help"}
            )
            assert learn is not None

            # 3. Check stats
            stats = await client.call_tool("stats", {"format": "json"})
            assert stats is not None

        finally:
            await client.disconnect()

    async def test_context_building_pattern(self, project_root):
        """Simulate building context over multiple queries."""
        client = MCPClientSimulator(project_root=project_root, timeout=20.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Progressive context building
            queries = [
                "project architecture",
                "memory system design",
                "MCP integration",
            ]

            for query in queries:
                # Recall relevant context
                recall = await client.call_tool("recall", {"query": query, "limit": 5})
                assert recall is not None

                # Enhance with context
                enhance = await client.call_tool(
                    "enhance", {"prompt": f"Explain {query}", "limit": 5}
                )
                assert enhance is not None

                await asyncio.sleep(0.2)

        finally:
            await client.disconnect()

    async def test_session_lifecycle_pattern(self, project_root):
        """Test complete session lifecycle from start to shutdown."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            # Session start
            connected = await client.connect()
            assert connected

            init = await client.initialize()
            assert init is not None

            await client.send_notification("notifications/initialized", {})

            # Active session operations
            for _ in range(5):
                await client.call_tool("stats", {})
                await asyncio.sleep(0.1)

            # Session end - graceful shutdown
            shutdown = await client.send_request("shutdown", {})
            assert shutdown is not None

            await asyncio.sleep(0.5)

            # Verify clean shutdown
            if client.process:
                assert client.process.poll() is not None

        finally:
            # Cleanup
            if client.process and client.process.poll() is None:
                await client.disconnect()

    async def test_error_recovery_pattern(self, project_root):
        """Simulate error recovery in real-world usage."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Normal operation
            success1 = await client.call_tool("stats", {})
            assert success1 is not None

            # Encounter error
            error = await client.call_tool("nonexistent_tool", {})
            assert "error" in error

            # Continue operation (error recovery)
            success2 = await client.call_tool("project", {})
            assert success2 is not None

            # Multiple operations after recovery
            for _ in range(3):
                response = await client.call_tool("stats", {})
                assert response is not None

        finally:
            await client.disconnect()
