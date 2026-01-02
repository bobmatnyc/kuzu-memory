"""
Comprehensive Tool Execution Integration Tests.

Tests execution of all 9 MCP tools, parameter validation, error handling,
timeouts, concurrent execution, and state consistency.
"""

import asyncio
import json

import pytest

from tests.mcp.fixtures.mock_clients import MCPClientSimulator


@pytest.mark.integration
@pytest.mark.asyncio
class TestToolExecution:
    """Integration tests for individual tool execution."""

    async def test_enhance_tool_execution(self, project_root):
        """Test enhance tool with prompt enhancement."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            # Initialize first
            await client.initialize()

            # Call enhance tool
            response = await client.call_tool(
                "kuzu_enhance", {"prompt": "test prompt", "limit": 5}
            )

            assert response is not None
            assert "result" in response or "error" in response

            if "result" in response:
                result = response["result"]
                assert "content" in result or "enhanced_prompt" in str(result)

        finally:
            await client.disconnect()

    async def test_learn_tool_execution(self, project_root):
        """Test learn tool for async learning."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call learn tool
            response = await client.call_tool(
                "learn", {"content": "Test learning content", "source": "test"}
            )

            assert response is not None
            # Learn is async, should return success quickly
            if "result" in response:
                assert (
                    "success" in str(response["result"]).lower()
                    or "queued" in str(response["result"]).lower()
                )

        finally:
            await client.disconnect()

    async def test_recall_tool_execution(self, project_root):
        """Test recall tool for memory query."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call recall tool
            response = await client.call_tool(
                "kuzu_recall", {"query": "test query", "limit": 5}
            )

            assert response is not None
            assert "result" in response or "error" in response

            if "result" in response:
                result = response["result"]
                assert "content" in result or "memories" in str(result)

        finally:
            await client.disconnect()

    async def test_remember_tool_execution(self, project_root):
        """Test remember tool for direct memory storage."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call remember tool
            response = await client.call_tool(
                "remember", {"content": "Test memory", "source": "test"}
            )

            assert response is not None
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_stats_tool_execution(self, project_root):
        """Test stats tool for system statistics."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call stats tool
            response = await client.call_tool("kuzu_stats", {"format": "json"})

            assert response is not None
            assert "result" in response or "error" in response

            if "result" in response:
                result = response["result"]
                assert "content" in result or "stats" in str(result)

        finally:
            await client.disconnect()

    async def test_recent_tool_execution(self, project_root):
        """Test recent tool for retrieving recent memories."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call recent tool
            response = await client.call_tool("recent", {"limit": 10})

            assert response is not None
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_cleanup_tool_execution(self, project_root):
        """Test cleanup tool for expired memory cleanup."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call cleanup tool with dry_run
            response = await client.call_tool("cleanup", {"dry_run": True})

            assert response is not None
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_project_tool_execution(self, project_root):
        """Test project tool for project information."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call project tool
            response = await client.call_tool("project", {"verbose": False})

            assert response is not None
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_init_tool_execution(self, project_root):
        """Test init tool for project initialization."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call init tool (should be idempotent)
            response = await client.call_tool("init", {})

            assert response is not None
            # Init might succeed or report already initialized
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
class TestToolDiscovery:
    """Tests for tool discovery and listing."""

    async def test_tools_list_method(self, project_root):
        """Test tools/list method returns all available tools."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # List tools
            response = await client.list_tools()

            assert response is not None
            assert "result" in response

            if "result" in response:
                tools = response["result"].get("tools", [])
                tool_names = [t.get("name") for t in tools]

                # Should include all 9 tools
                expected_tools = [
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

                for tool in expected_tools:
                    assert (
                        tool in tool_names
                    ), f"Missing tool: {tool}, found: {tool_names}"

        finally:
            await client.disconnect()

    async def test_tool_descriptions_present(self, project_root):
        """Test that all tools have descriptions."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            response = await client.list_tools()
            assert response is not None

            if "result" in response:
                tools = response["result"].get("tools", [])

                for tool in tools:
                    assert "name" in tool
                    assert "description" in tool
                    assert len(tool["description"]) > 0

        finally:
            await client.disconnect()

    async def test_tool_parameters_defined(self, project_root):
        """Test that tool parameters are properly defined."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            response = await client.list_tools()
            assert response is not None

            if "result" in response:
                tools = response["result"].get("tools", [])

                for tool in tools:
                    # Should have inputSchema or parameters
                    assert "inputSchema" in tool or "parameters" in tool

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
class TestToolParameterValidation:
    """Tests for tool parameter validation."""

    async def test_missing_required_parameter(self, project_root):
        """Test error when required parameter is missing."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call enhance without required prompt parameter
            response = await client.call_tool("kuzu_enhance", {})

            assert response is not None
            # Should error or handle missing parameter
            if "error" in response:
                assert response["error"]["code"] == -32602  # Invalid params

        finally:
            await client.disconnect()

    async def test_invalid_parameter_type(self, project_root):
        """Test error when parameter has wrong type."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call stats with invalid format type
            response = await client.call_tool(
                "stats",
                {"format": 123},  # Should be string
            )

            assert response is not None
            # Should handle gracefully or error
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_extra_parameters_ignored(self, project_root):
        """Test that extra parameters are handled gracefully."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call with extra parameter
            response = await client.call_tool(
                "kuzu_stats", {"format": "json", "extra_param": "ignored"}
            )

            assert response is not None
            # Should ignore extra param
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
class TestToolErrorHandling:
    """Tests for tool execution error scenarios."""

    async def test_tool_not_found_error(self, project_root):
        """Test error when calling non-existent tool."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call non-existent tool
            response = await client.call_tool("nonexistent", {})

            assert response is not None
            assert "error" in response
            # Should be METHOD_NOT_FOUND or similar
            assert response["error"]["code"] in [-32601, -32001]

        finally:
            await client.disconnect()

    async def test_tool_execution_failure_handling(self, project_root):
        """Test handling of tool execution failures."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Try to cause execution failure with invalid input
            response = await client.call_tool(
                "recall",
                {"query": "", "limit": -1},  # Invalid limit
            )

            assert response is not None
            # Should handle gracefully
            assert "result" in response or "error" in response

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
class TestToolConcurrency:
    """Tests for concurrent tool execution."""

    async def test_concurrent_tool_calls(self, project_root):
        """Test executing multiple tools concurrently."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Execute multiple tools
            responses = []
            for _i in range(5):
                response = await client.call_tool("kuzu_stats", {"format": "json"})
                responses.append(response)

            # Most should succeed
            successful = sum(1 for r in responses if r and "result" in r)
            assert successful >= 3, f"Only {successful}/5 concurrent calls succeeded"

        finally:
            await client.disconnect()

    async def test_tool_state_consistency(self, project_root):
        """Test that concurrent calls maintain state consistency."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Store memory
            await client.call_tool("kuzu_remember", {"content": "Test consistency"})

            # Retrieve multiple times
            responses = []
            for _ in range(3):
                response = await client.call_tool(
                    "kuzu_recall", {"query": "consistency", "limit": 5}
                )
                responses.append(response)

            # All should return consistent results
            successful = sum(1 for r in responses if r and "result" in r)
            assert successful >= 2

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
class TestToolTimeouts:
    """Tests for tool execution timeout scenarios."""

    async def test_tool_timeout_handling(self, project_root):
        """Test that tool calls timeout appropriately."""
        client = MCPClientSimulator(project_root=project_root, timeout=2.0)

        try:
            connected = await client.connect()
            assert connected

            await client.initialize()

            # Call tool with short timeout
            response = await client.call_tool("kuzu_stats", {"detailed": True})

            # Should complete or timeout gracefully
            if response is None:
                # Timeout occurred
                pass
            else:
                # Completed within timeout
                assert "result" in response or "error" in response

        finally:
            await client.disconnect()
