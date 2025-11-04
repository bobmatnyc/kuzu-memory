"""
Test that MCP server correctly handles protocol version 2025-06-18.

This test verifies the fix for Claude Code compatibility, which requires
protocol version 2025-06-18 instead of the legacy 2024-11-05.
"""

import asyncio
import json
from pathlib import Path

import pytest

from kuzu_memory.mcp.run_server import MCPProtocolHandler
from kuzu_memory.mcp.server import KuzuMemoryMCPServer as MCPServer


@pytest.mark.asyncio
async def test_protocol_version_2025_06_18():
    """Test that server supports Claude Code's protocol version 2025-06-18."""
    server = MCPServer(project_root=Path.cwd())
    handler = MCPProtocolHandler(server)

    # Test initialize with 2025-06-18 (Claude Code version)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    }

    response = await handler.handle_request(request)

    assert response is not None, "Response should not be None"
    assert response.get("jsonrpc") == "2.0", "Should have JSON-RPC 2.0"
    assert "result" in response, "Should have result field"
    assert response["result"]["protocolVersion"] == "2025-06-18", "Should echo back 2025-06-18"
    assert "capabilities" in response["result"], "Should have capabilities"
    assert "serverInfo" in response["result"], "Should have serverInfo"


@pytest.mark.asyncio
async def test_protocol_version_backward_compatibility():
    """Test that server still supports legacy protocol version 2024-11-05."""
    server = MCPServer(project_root=Path.cwd())
    handler = MCPProtocolHandler(server)

    # Test initialize with 2024-11-05 (legacy version)
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }

    response = await handler.handle_request(request)

    assert response is not None, "Response should not be None"
    assert response["result"]["protocolVersion"] == "2024-11-05", "Should support legacy 2024-11-05"


@pytest.mark.asyncio
async def test_protocol_version_default():
    """Test that server defaults to 2025-06-18 when no version specified."""
    server = MCPServer(project_root=Path.cwd())
    handler = MCPProtocolHandler(server)

    # Test initialize without protocol version
    request = {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {}}

    response = await handler.handle_request(request)

    assert response is not None, "Response should not be None"
    assert response["result"]["protocolVersion"] == "2025-06-18", (
        "Should default to latest version 2025-06-18"
    )


@pytest.mark.asyncio
async def test_protocol_version_unsupported():
    """Test that server handles unsupported protocol version gracefully."""
    server = MCPServer(project_root=Path.cwd())
    handler = MCPProtocolHandler(server)

    # Test initialize with unsupported future version
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "initialize",
        "params": {"protocolVersion": "2026-01-01"},
    }

    response = await handler.handle_request(request)

    assert response is not None, "Response should not be None"
    # Should fallback to latest supported version
    assert response["result"]["protocolVersion"] == "2025-06-18", (
        "Should fallback to latest supported version"
    )


@pytest.mark.asyncio
async def test_full_handshake_with_claude_code_version():
    """Test a complete MCP handshake with Claude Code's protocol version."""
    server = MCPServer(project_root=Path.cwd())
    handler = MCPProtocolHandler(server)

    # Step 1: Initialize with Claude Code version
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    }

    init_response = await handler.handle_request(init_request)

    assert init_response["result"]["protocolVersion"] == "2025-06-18", (
        "Initialization should succeed"
    )

    # Step 2: List tools (should work after initialization)
    tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    tools_response = await handler.handle_request(tools_request)

    assert "result" in tools_response, "Tools list should succeed"
    assert "tools" in tools_response["result"], "Should return tools array"
    assert len(tools_response["result"]["tools"]) > 0, "Should have at least one tool"

    # Verify expected tools are present
    tool_names = [tool["name"] for tool in tools_response["result"]["tools"]]
    expected_tools = ["enhance", "learn", "recall", "remember", "stats"]
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Should have {expected_tool} tool available"
