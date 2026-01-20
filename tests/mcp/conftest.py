"""
Shared pytest fixtures for MCP testing.

Provides reusable fixtures for MCP server testing including server startup,
connection management, and test data generation.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from kuzu_memory.mcp.server import KuzuMemoryMCPServer as MCPServer
from kuzu_memory.mcp.testing.connection_tester import MCPConnectionTester


@pytest.fixture
def project_root() -> Path:
    """
    Get project root directory.

    Returns:
        Path to project root
    """
    return Path(__file__).parent.parent.parent


@pytest_asyncio.fixture
async def mcp_server(project_root: Path) -> MCPServer:
    """
    Create MCP server instance for testing.

    Args:
        project_root: Project root path

    Returns:
        Configured MCP server
    """
    server = MCPServer(project_root=project_root)
    return server


@pytest_asyncio.fixture
async def connection_tester(project_root: Path) -> MCPConnectionTester:
    """
    Create connection tester instance.

    Args:
        project_root: Project root path

    Yields:
        Configured connection tester (with cleanup)
    """
    tester = MCPConnectionTester(
        server_path=None,  # Auto-detect
        timeout=5.0,
        project_root=project_root,
    )

    yield tester

    # Cleanup: ensure server is stopped
    if tester.process:
        await tester.stop_server()


@pytest.fixture
def sample_requests() -> dict[str, dict[str, Any]]:
    """
    Generate sample JSON-RPC requests for testing.

    Returns:
        Dictionary of named request samples
    """
    return {
        "initialize": {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2025-06-18"},
        },
        "ping": {"jsonrpc": "2.0", "method": "ping", "id": 2},
        "tools_list": {"jsonrpc": "2.0", "method": "tools/list", "id": 3},
        "tools_call_enhance": {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 4,
            "params": {
                "name": "kuzu_enhance",
                "arguments": {"prompt": "test prompt", "limit": 5},
            },
        },
        "tools_call_recall": {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 5,
            "params": {
                "name": "kuzu_recall",
                "arguments": {"query": "test query", "limit": 5},
            },
        },
        "tools_call_stats": {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 6,
            "params": {"name": "kuzu_stats", "arguments": {"format": "json"}},
        },
        "shutdown": {"jsonrpc": "2.0", "method": "shutdown", "id": 99},
        "notification": {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        },
    }


@pytest.fixture
def sample_tools() -> list[dict[str, Any]]:
    """
    Generate sample tool definitions for testing.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "kuzu_enhance",
            "description": "Enhance prompts with relevant project context",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to enhance",
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "kuzu_recall",
            "description": "Query memories for relevant information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
        {
            "name": "kuzu_stats",
            "description": "Get memory system statistics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "detailed": {"type": "boolean", "default": False},
                    "format": {"type": "string", "default": "json"},
                },
            },
        },
    ]


@pytest.fixture
def invalid_requests() -> dict[str, Any]:
    """
    Generate invalid JSON-RPC requests for error handling tests.

    Returns:
        Dictionary of invalid request scenarios
    """
    return {
        "missing_jsonrpc": {"method": "test", "id": 1},
        "wrong_version": {"jsonrpc": "1.0", "method": "test", "id": 1},
        "missing_method": {"jsonrpc": "2.0", "id": 1},
        "invalid_method_type": {"jsonrpc": "2.0", "method": 123, "id": 1},
        "invalid_params_type": {
            "jsonrpc": "2.0",
            "method": "test",
            "params": "string",
            "id": 1,
        },
        "malformed_json": "{'not': 'valid json'}",
    }


@pytest.fixture
def protocol_versions() -> list[str]:
    """
    List of protocol versions to test for compatibility.

    Returns:
        List of protocol version strings
    """
    return ["2025-06-18", "2024-11-05"]


@pytest.fixture
def error_codes() -> dict[str, int]:
    """
    JSON-RPC error codes for validation.

    Returns:
        Dictionary mapping error names to codes
    """
    return {
        "PARSE_ERROR": -32700,
        "INVALID_REQUEST": -32600,
        "METHOD_NOT_FOUND": -32601,
        "INVALID_PARAMS": -32602,
        "INTERNAL_ERROR": -32603,
        "TOOL_EXECUTION_ERROR": -32001,
        "INITIALIZATION_ERROR": -32002,
        "TIMEOUT_ERROR": -32003,
    }


@pytest.fixture
def performance_thresholds() -> dict[str, float]:
    """
    Performance thresholds for benchmark tests.

    Returns:
        Dictionary of operation thresholds in milliseconds
    """
    return {
        "connection_setup": 1000.0,  # 1 second
        "protocol_init": 500.0,  # 500ms
        "tool_call_enhance": 200.0,  # 200ms
        "tool_call_recall": 100.0,  # 100ms (3ms typical)
        "tool_call_stats": 150.0,  # 150ms
        "ping_response": 50.0,  # 50ms
    }


@pytest_asyncio.fixture
async def running_server(connection_tester: MCPConnectionTester):
    """
    Start MCP server and ensure it's running.

    Args:
        connection_tester: Connection tester fixture

    Yields:
        Running connection tester with active server
    """
    result = await connection_tester.start_server()

    if not result.success:
        pytest.skip(f"Failed to start server: {result.error}")

    # Wait for server to be ready
    await asyncio.sleep(0.2)

    yield connection_tester

    # Cleanup
    await connection_tester.stop_server()


@pytest.fixture
def batch_requests() -> list[dict[str, Any]]:
    """
    Generate batch request for batch processing tests.

    Returns:
        List of JSON-RPC requests for batch testing
    """
    return [
        {"jsonrpc": "2.0", "method": "ping", "id": 1},
        {"jsonrpc": "2.0", "method": "tools/list", "id": 2},
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "kuzu_stats", "arguments": {}},
        },
    ]


@pytest.fixture
def stress_test_params() -> dict[str, int]:
    """
    Parameters for stress testing scenarios.

    Returns:
        Dictionary of stress test parameters
    """
    return {
        "concurrent_connections": 10,
        "requests_per_connection": 50,
        "message_burst_count": 100,
        "max_message_size": 1024 * 100,  # 100KB
    }


# Phase 4: Additional Integration Test Fixtures


@pytest_asyncio.fixture
async def mcp_client(project_root: Path):
    """
    Create and connect an MCP client simulator.

    Args:
        project_root: Project root path

    Yields:
        Connected MCP client simulator
    """
    from tests.mcp.fixtures.mock_clients import MCPClientSimulator

    client = MCPClientSimulator(project_root=project_root, timeout=10.0)

    connected = await client.connect()
    if not connected:
        pytest.skip("Failed to connect to MCP server")

    yield client

    await client.disconnect()


@pytest_asyncio.fixture
async def initialized_client(project_root: Path):
    """
    Create initialized MCP client ready for operations.

    Args:
        project_root: Project root path

    Yields:
        Initialized and connected MCP client
    """
    from tests.mcp.fixtures.mock_clients import MCPClientSimulator

    client = MCPClientSimulator(project_root=project_root, timeout=10.0)

    connected = await client.connect()
    if not connected:
        pytest.skip("Failed to connect to MCP server")

    await client.initialize()
    await asyncio.sleep(0.1)  # Brief stabilization

    yield client

    await client.disconnect()


@pytest_asyncio.fixture
async def multiple_clients(project_root: Path):
    """
    Create multiple connected MCP clients for concurrent testing.

    Args:
        project_root: Project root path

    Yields:
        List of connected MCP clients
    """
    from tests.mcp.fixtures.mock_clients import MCPClientSimulator

    num_clients = 3
    clients = [
        MCPClientSimulator(project_root=project_root, timeout=10.0)
        for _ in range(num_clients)
    ]

    # Connect all
    for client in clients:
        await client.connect()

    yield clients

    # Cleanup all
    for client in clients:
        await client.disconnect()


@pytest.fixture
def sample_tool_calls() -> list[dict[str, Any]]:
    """
    Generate sample tool call requests for testing.

    Returns:
        List of tool call request dictionaries
    """
    return [
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": "kuzu_enhance",
                "arguments": {"prompt": "test", "limit": 5},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {
                "name": "kuzu_recall",
                "arguments": {"query": "test", "limit": 5},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {"name": "kuzu_stats", "arguments": {"format": "json"}},
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 4,
            "params": {
                "name": "kuzu_remember",
                "arguments": {"content": "test memory"},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 5,
            "params": {"name": "recent", "arguments": {"limit": 10}},
        },
    ]


@pytest.fixture
def error_scenarios() -> dict[str, dict[str, Any]]:
    """
    Collection of error test scenarios.

    Returns:
        Dictionary of error scenarios
    """
    return {
        "tool_not_found": {
            "request": {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 1,
                "params": {"name": "nonexistent", "arguments": {}},
            },
            "expected_error_code": -32601,
        },
        "invalid_params": {
            "request": {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 2,
                "params": {"name": "kuzu_enhance", "arguments": {}},  # Missing prompt
            },
            "expected_error_code": -32602,
        },
        "malformed_json": {
            "request": "{'not': 'valid json'}\n",
            "expected_error_code": -32700,
        },
        "missing_method": {
            "request": {"jsonrpc": "2.0", "id": 3},
            "expected_error_code": -32600,
        },
    }


@pytest.fixture
def tool_execution_scenarios() -> dict[str, dict[str, Any]]:
    """
    Collection of tool execution test scenarios.

    Returns:
        Dictionary of tool execution scenarios
    """
    return {
        "enhance_basic": {
            "tool": "kuzu_enhance",
            "arguments": {"prompt": "test prompt", "limit": 5},
        },
        "recall_query": {
            "tool": "kuzu_recall",
            "arguments": {"query": "test", "limit": 5},
        },
        "stats_json": {"tool": "kuzu_stats", "arguments": {"format": "json"}},
        "remember_content": {
            "tool": "kuzu_remember",
            "arguments": {"content": "test memory"},
        },
        "recent_memories": {"tool": "recent", "arguments": {"limit": 10}},
        "cleanup_dry_run": {"tool": "cleanup", "arguments": {"dry_run": True}},
        "project_info": {"tool": "project", "arguments": {}},
        "init_project": {"tool": "init", "arguments": {}},
    }


@pytest_asyncio.fixture
async def session_with_history(mcp_client):
    """
    Create client session with operation history.

    Args:
        mcp_client: Connected MCP client

    Returns:
        Client with established operation history
    """
    await mcp_client.initialize()

    # Build some history
    await mcp_client.call_tool("kuzu_stats", {})
    await mcp_client.send_request("ping", {})
    await mcp_client.call_tool("project", {})

    return mcp_client


@pytest.fixture
def concurrent_simulator(project_root: Path):
    """
    Create concurrent client simulator for load testing.

    Args:
        project_root: Project root path

    Returns:
        Concurrent client simulator
    """
    from tests.mcp.fixtures.mock_clients import ConcurrentClientSimulator

    return ConcurrentClientSimulator(
        num_clients=5, project_root=project_root, timeout=10.0
    )


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop_policy():
    """
    Set event loop policy for async tests.

    Returns:
        Event loop policy
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.get_event_loop_policy()


# Phase 5: Performance Testing & Compliance Fixtures


@pytest.fixture
def benchmark_config():
    """
    pytest-benchmark configuration for performance tests.

    Returns:
        Dictionary of benchmark configuration parameters
    """
    return {
        "min_rounds": 5,
        "min_time": 0.1,
        "max_time": 1.0,
        "warmup": True,
        "warmup_iterations": 2,
        "disable_gc": True,  # Disable GC during benchmarks for consistency
        "timer": "perf_counter",
    }


@pytest.fixture
def performance_thresholds_detailed() -> dict[str, dict[str, float]]:
    """
    Detailed performance thresholds for all operation types.

    Returns:
        Dictionary mapping operations to target/critical thresholds (milliseconds)
    """
    return {
        "connection_latency_ms": {"target": 50, "critical": 100},
        "tool_latency_ms": {"target": 100, "critical": 200},
        "roundtrip_latency_ms": {"target": 20, "critical": 50},
        "initialization_latency_ms": {"target": 100, "critical": 200},
        "batch_latency_ms": {"target": 150, "critical": 300},
        "throughput_ops_sec": {"target": 100, "critical": 50},
        "concurrent_throughput_ops_sec": {"target": 50, "critical": 25},
        "sustained_throughput_ops_sec": {"target": 80, "critical": 40},
        "memory_per_connection_mb": {"target": 10, "critical": 20},
        "memory_growth_rate_mb_per_100ops": {"target": 0.5, "critical": 2.0},
        "peak_memory_mb": {"target": 50, "critical": 100},
        "max_concurrent_connections": {"target": 10, "critical": 5},
        "success_rate_percent": {"target": 95, "critical": 90},
    }


@pytest.fixture
def jsonrpc_error_codes_detailed() -> dict[str, int]:
    """
    Comprehensive JSON-RPC 2.0 error codes.

    Returns:
        Dictionary mapping error names to standard codes
    """
    return {
        # Standard JSON-RPC 2.0 errors
        "PARSE_ERROR": -32700,
        "INVALID_REQUEST": -32600,
        "METHOD_NOT_FOUND": -32601,
        "INVALID_PARAMS": -32602,
        "INTERNAL_ERROR": -32603,
        # Server error range: -32000 to -32099
        "SERVER_ERROR_START": -32099,
        "SERVER_ERROR_END": -32000,
        # MCP-specific errors
        "TOOL_EXECUTION_ERROR": -32001,
        "INITIALIZATION_ERROR": -32002,
        "TIMEOUT_ERROR": -32003,
    }


@pytest.fixture
def mcp_protocol_versions() -> list[str]:
    """
    Supported MCP protocol versions for compliance testing.

    Returns:
        List of protocol version strings
    """
    return ["2025-06-18", "2024-11-05"]


@pytest.fixture
def compliance_test_scenarios() -> dict[str, Any]:
    """
    Compliance test scenarios for protocol validation.

    Returns:
        Dictionary of test scenarios
    """
    return {
        "valid_requests": [
            {"jsonrpc": "2.0", "method": "ping", "id": 1},
            {"jsonrpc": "2.0", "method": "tools/list", "id": 2},
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "kuzu_stats", "arguments": {}},
                "id": 3,
            },
        ],
        "invalid_requests": [
            {"method": "test", "id": 1},  # Missing jsonrpc
            {"jsonrpc": "1.0", "method": "test", "id": 1},  # Wrong version
            {"jsonrpc": "2.0", "id": 1},  # Missing method
            {"jsonrpc": "2.0", "method": 123, "id": 1},  # Invalid method type
            {
                "jsonrpc": "2.0",
                "method": "test",
                "params": "string",
                "id": 1,
            },  # Invalid params
        ],
        "notifications": [
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "method": "notifications/test"},
        ],
        "batch_requests": [
            [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "tools/list", "id": 2},
            ],
            [
                {"jsonrpc": "2.0", "method": "ping", "id": 1},
                {"jsonrpc": "2.0", "method": "invalid", "id": 2},
                {"jsonrpc": "2.0", "method": "ping", "id": 3},
            ],
        ],
    }
