"""
Performance tests for MCP server latency.

Tests connection, tool call, and message roundtrip latency against
defined performance thresholds.
"""

import asyncio
import time

import pytest

from tests.mcp.fixtures.mock_clients import MCPClientSimulator

# Performance thresholds (milliseconds)
# Updated 2025-02-10: Thresholds adjusted based on real-world measurements
# - Connection includes subprocess spawn + stdio setup (~100-200ms)
# - Initialization includes protocol negotiation + server warmup (~300-600ms)
# - Tool calls include JSON-RPC overhead + DB queries (~150-1000ms)
# - Roundtrip is pure JSON-RPC with minimal work (~20-200ms)
LATENCY_THRESHOLDS = {
    "connection": {"target": 150, "critical": 600},  # Allow for subprocess startup
    "tool_call": {"target": 250, "critical": 1200},  # DB queries can be slow
    "roundtrip": {"target": 60, "critical": 250},  # JSON-RPC overhead
    "initialization": {"target": 400, "critical": 800},  # Protocol + warmup
    "batch": {"target": 500, "critical": 1500},  # Multiple operations
}


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestConnectionLatency:
    """Test connection establishment latency."""

    @pytest.mark.asyncio
    async def test_connection_latency(self, project_root, benchmark):
        """Test time to establish connection."""

        async def connect_disconnect():
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            start = time.perf_counter()
            connected = await client.connect()
            latency = (time.perf_counter() - start) * 1000  # ms
            await client.disconnect()
            return latency, connected

        latency, connected = await connect_disconnect()

        assert connected, "Connection should succeed"
        assert (
            latency < LATENCY_THRESHOLDS["connection"]["critical"]
        ), f"Connection latency {latency:.2f}ms exceeds critical threshold"

    @pytest.mark.asyncio
    async def test_connection_latency_percentiles(self, project_root):
        """Test connection latency distribution across multiple attempts."""
        latencies = []

        for _ in range(10):
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            start = time.perf_counter()
            connected = await client.connect()
            latency = (time.perf_counter() - start) * 1000
            await client.disconnect()

            if connected:
                latencies.append(latency)

        assert len(latencies) >= 8, "Most connections should succeed"

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[-1]

        print("\nConnection Latency Percentiles:")
        print(f"  p50: {p50:.2f}ms")
        print(f"  p95: {p95:.2f}ms")
        print(f"  p99: {p99:.2f}ms")

        assert p95 < LATENCY_THRESHOLDS["connection"]["critical"]

    @pytest.mark.asyncio
    async def test_protocol_initialization_latency(self, mcp_client, benchmark):
        """Test protocol initialization latency."""

        async def initialize():
            start = time.perf_counter()
            await mcp_client.initialize()
            return (time.perf_counter() - start) * 1000

        latency = await initialize()

        assert (
            latency < LATENCY_THRESHOLDS["initialization"]["critical"]
        ), f"Initialization latency {latency:.2f}ms exceeds critical threshold"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestToolCallLatency:
    """Test tool execution latency."""

    @pytest.mark.asyncio
    async def test_stats_tool_latency(self, initialized_client, benchmark):
        """Test stats tool call latency."""

        async def call_stats():
            start = time.perf_counter()
            result = await initialized_client.call_tool("kuzu_stats", {})
            latency = (time.perf_counter() - start) * 1000
            return latency, result

        latency, result = await call_stats()

        assert result is not None, "Stats call should return result"
        assert (
            latency < LATENCY_THRESHOLDS["tool_call"]["critical"]
        ), f"Stats latency {latency:.2f}ms exceeds critical threshold"

    @pytest.mark.asyncio
    async def test_recall_tool_latency(self, initialized_client, benchmark):
        """Test recall tool call latency (target: 3ms typical, 100ms threshold)."""

        async def call_recall():
            start = time.perf_counter()
            result = await initialized_client.call_tool(
                "kuzu_recall", {"query": "test", "limit": 5}
            )
            latency = (time.perf_counter() - start) * 1000
            return latency, result

        latency, result = await call_recall()

        assert result is not None, "Recall should return result"
        # Recall should be very fast (target 3ms)
        assert (
            latency < LATENCY_THRESHOLDS["tool_call"]["critical"]
        ), f"Recall latency {latency:.2f}ms exceeds critical threshold"

        print(f"\nRecall latency: {latency:.2f}ms (target: 3ms typical)")

    @pytest.mark.asyncio
    async def test_enhance_tool_latency(self, initialized_client):
        """Test enhance tool call latency."""
        start = time.perf_counter()
        result = await initialized_client.call_tool(
            "enhance", {"prompt": "test prompt", "limit": 5}
        )
        latency = (time.perf_counter() - start) * 1000

        assert result is not None, "Enhance should return result"
        assert (
            latency < LATENCY_THRESHOLDS["tool_call"]["critical"]
        ), f"Enhance latency {latency:.2f}ms exceeds critical threshold"

    @pytest.mark.asyncio
    async def test_tool_latency_by_type(self, initialized_client):
        """Test latency for different tool types."""
        tools = ["stats", "recall", "recent", "project"]
        latencies = {}

        for tool_name in tools:
            args = (
                {"query": "test", "limit": 5}
                if tool_name == "recall"
                else {"limit": 10} if tool_name == "recent" else {}
            )

            start = time.perf_counter()
            result = await initialized_client.call_tool(tool_name, args)
            latency = (time.perf_counter() - start) * 1000
            latencies[tool_name] = latency

            assert result is not None, f"{tool_name} should return result"

        print("\nTool Latencies:")
        for tool, latency in latencies.items():
            status = (
                "✓"
                if latency < LATENCY_THRESHOLDS["tool_call"]["target"]
                else (
                    "⚠"
                    if latency < LATENCY_THRESHOLDS["tool_call"]["critical"]
                    else "✗"
                )
            )
            print(f"  {tool:15s}: {latency:6.2f}ms {status}")


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestRoundtripLatency:
    """Test message roundtrip latency."""

    @pytest.mark.asyncio
    async def test_ping_roundtrip(self, initialized_client, benchmark):
        """Test ping message roundtrip latency."""

        async def ping():
            start = time.perf_counter()
            result = await initialized_client.send_request("ping", {})
            latency = (time.perf_counter() - start) * 1000
            return latency, result

        latency, result = await ping()

        assert result is not None, "Ping should return result"
        assert (
            latency < LATENCY_THRESHOLDS["roundtrip"]["critical"]
        ), f"Ping roundtrip {latency:.2f}ms exceeds critical threshold"

    @pytest.mark.asyncio
    async def test_tools_list_roundtrip(self, initialized_client):
        """Test tools/list roundtrip latency."""
        start = time.perf_counter()
        result = await initialized_client.send_request("tools/list", {})
        latency = (time.perf_counter() - start) * 1000

        assert result is not None, "tools/list should return result"
        assert (
            latency < LATENCY_THRESHOLDS["roundtrip"]["critical"]
        ), f"tools/list roundtrip {latency:.2f}ms exceeds critical threshold"

    @pytest.mark.asyncio
    async def test_sequential_roundtrips(self, initialized_client):
        """Test latency of sequential requests."""
        requests = [
            ("ping", {}),
            ("tools/list", {}),
            ("ping", {}),
            ("tools/list", {}),
        ]

        latencies = []
        for method, params in requests:
            start = time.perf_counter()
            result = await initialized_client.send_request(method, params)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

            assert result is not None, f"{method} should return result"

        avg_latency = sum(latencies) / len(latencies)
        assert (
            avg_latency < LATENCY_THRESHOLDS["roundtrip"]["critical"]
        ), f"Average roundtrip {avg_latency:.2f}ms exceeds critical threshold"

    @pytest.mark.asyncio
    async def test_batch_request_latency(self, initialized_client):
        """Test batch request latency."""
        batch = [
            {"jsonrpc": "2.0", "method": "ping", "id": 1},
            {"jsonrpc": "2.0", "method": "tools/list", "id": 2},
            {"jsonrpc": "2.0", "method": "ping", "id": 3},
        ]

        start = time.perf_counter()
        results = await initialized_client.send_batch_request(batch)
        latency = (time.perf_counter() - start) * 1000

        assert results is not None, "Batch should return results"
        assert len(results) == 3, "Should get 3 responses"
        assert (
            latency < LATENCY_THRESHOLDS["batch"]["critical"]
        ), f"Batch latency {latency:.2f}ms exceeds critical threshold"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestLatencyConsistency:
    """Test latency consistency over time."""

    @pytest.mark.asyncio
    async def test_latency_stability(self, initialized_client):
        """Test that latency remains stable over multiple operations."""
        latencies = []

        for _ in range(20):
            start = time.perf_counter()
            await initialized_client.send_request("ping", {})
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            await asyncio.sleep(0.01)  # Small delay between requests

        # Calculate statistics
        avg = sum(latencies) / len(latencies)
        variance = sum((lat - avg) ** 2 for lat in latencies) / len(latencies)
        std_dev = variance**0.5

        print("\nLatency Stability:")
        print(f"  Mean: {avg:.2f}ms")
        print(f"  Std Dev: {std_dev:.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")

        # Standard deviation should be reasonable
        assert std_dev < 20.0, f"High latency variance: {std_dev:.2f}ms"

    @pytest.mark.asyncio
    async def test_warmup_effect(self, initialized_client):
        """Test if there's a warmup effect on latency."""
        # First call (potential warmup)
        start = time.perf_counter()
        await initialized_client.call_tool("kuzu_stats", {})
        first_latency = (time.perf_counter() - start) * 1000

        # Subsequent calls
        subsequent_latencies = []
        for _ in range(5):
            start = time.perf_counter()
            await initialized_client.call_tool("kuzu_stats", {})
            latency = (time.perf_counter() - start) * 1000
            subsequent_latencies.append(latency)

        avg_subsequent = sum(subsequent_latencies) / len(subsequent_latencies)

        print("\nWarmup Analysis:")
        print(f"  First call: {first_latency:.2f}ms")
        print(f"  Avg subsequent: {avg_subsequent:.2f}ms")
        print(f"  Warmup overhead: {first_latency - avg_subsequent:.2f}ms")

        # Warmed up latency should meet targets
        assert (
            avg_subsequent < LATENCY_THRESHOLDS["tool_call"]["critical"]
        ), "Warmed up latency exceeds critical threshold"
