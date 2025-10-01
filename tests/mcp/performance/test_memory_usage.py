"""
Performance tests for MCP server memory usage.

Tests memory consumption, growth, and leak detection using psutil.
"""

import asyncio
import time

import psutil
import pytest

# Memory thresholds (MB)
MEMORY_THRESHOLDS = {
    "per_connection": {"target": 10, "critical": 20},
    "growth_rate": {"target": 0.5, "critical": 2.0},  # MB per 100 operations
    "peak": {"target": 50, "critical": 100},
}


def get_process_memory_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


@pytest.mark.performance
@pytest.mark.benchmark
class TestMemoryPerConnection:
    """Test memory usage per connection."""

    @pytest.mark.asyncio
    async def test_single_connection_memory(self, project_root):
        """Test memory usage of a single connection."""
        from tests.mcp.fixtures.mock_clients import MCPClientSimulator

        # Baseline memory
        await asyncio.sleep(0.1)  # Stabilize
        baseline_memory = get_process_memory_mb()

        # Create and connect client
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)
        await client.connect()
        await client.initialize()

        # Measure memory after connection
        await asyncio.sleep(0.1)  # Stabilize
        connected_memory = get_process_memory_mb()
        memory_per_connection = connected_memory - baseline_memory

        # Cleanup
        await client.disconnect()

        print("\nMemory Per Connection:")
        print(f"  Baseline: {baseline_memory:.2f}MB")
        print(f"  Connected: {connected_memory:.2f}MB")
        print(f"  Per Connection: {memory_per_connection:.2f}MB")

        assert (
            memory_per_connection < MEMORY_THRESHOLDS["per_connection"]["critical"]
        ), f"Memory per connection {memory_per_connection:.2f}MB exceeds critical"

    @pytest.mark.asyncio
    async def test_multiple_connections_memory(self, project_root):
        """Test memory usage with multiple connections."""
        from tests.mcp.fixtures.mock_clients import MCPClientSimulator

        baseline_memory = get_process_memory_mb()
        clients = []
        num_connections = 5

        # Create multiple connections
        for _ in range(num_connections):
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            await client.connect()
            await client.initialize()
            clients.append(client)
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.2)  # Stabilize
        total_memory = get_process_memory_mb()
        memory_increase = total_memory - baseline_memory
        avg_per_connection = memory_increase / num_connections

        # Cleanup
        for client in clients:
            await client.disconnect()

        print("\nMultiple Connections Memory:")
        print(f"  Baseline: {baseline_memory:.2f}MB")
        print(f"  Total with {num_connections} connections: {total_memory:.2f}MB")
        print(f"  Total increase: {memory_increase:.2f}MB")
        print(f"  Avg per connection: {avg_per_connection:.2f}MB")

        assert (
            avg_per_connection < MEMORY_THRESHOLDS["per_connection"]["critical"]
        ), f"Avg memory per connection {avg_per_connection:.2f}MB exceeds critical"


@pytest.mark.performance
@pytest.mark.benchmark
class TestMemoryGrowth:
    """Test memory growth over time."""

    @pytest.mark.asyncio
    async def test_memory_growth_during_operations(self, initialized_client):
        """Test memory growth during sustained operations."""
        num_operations = 500
        memory_samples = []

        # Initial memory
        initial_memory = get_process_memory_mb()
        memory_samples.append(initial_memory)

        # Perform operations and sample memory
        sample_interval = 50
        for i in range(num_operations):
            await initialized_client.send_request("ping", {})

            if (i + 1) % sample_interval == 0:
                memory_samples.append(get_process_memory_mb())

        final_memory = get_process_memory_mb()
        memory_growth = final_memory - initial_memory
        growth_rate = (memory_growth / num_operations) * 100  # MB per 100 ops

        print("\nMemory Growth Analysis:")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Growth: {memory_growth:.2f}MB")
        print(f"  Growth rate: {growth_rate:.4f}MB per 100 ops")

        assert (
            growth_rate < MEMORY_THRESHOLDS["growth_rate"]["critical"]
        ), f"Memory growth rate {growth_rate:.4f}MB/100ops exceeds critical"

    @pytest.mark.asyncio
    async def test_memory_growth_with_tool_calls(self, initialized_client):
        """Test memory growth with tool operations."""
        num_operations = 200
        tools = ["stats", "recall", "recent", "project"]

        initial_memory = get_process_memory_mb()

        for i in range(num_operations):
            tool = tools[i % len(tools)]
            args = (
                {"query": "test", "limit": 5}
                if tool == "recall"
                else {"limit": 10}
                if tool == "recent"
                else {}
            )
            await initialized_client.call_tool(tool, args)

        await asyncio.sleep(0.2)  # Stabilize
        final_memory = get_process_memory_mb()
        memory_growth = final_memory - initial_memory
        growth_rate = (memory_growth / num_operations) * 100

        print("\nMemory Growth (Tool Calls):")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Growth: {memory_growth:.2f}MB")
        print(f"  Growth rate: {growth_rate:.4f}MB per 100 ops")

        assert (
            growth_rate < MEMORY_THRESHOLDS["growth_rate"]["critical"]
        ), f"Tool call growth rate {growth_rate:.4f}MB/100ops exceeds critical"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.slow
class TestMemoryLeaks:
    """Test for memory leaks."""

    @pytest.mark.asyncio
    async def test_connection_cycle_leak(self, project_root):
        """Test for memory leaks in connection/disconnection cycles."""
        from tests.mcp.fixtures.mock_clients import MCPClientSimulator

        initial_memory = get_process_memory_mb()
        num_cycles = 10

        for _ in range(num_cycles):
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            await client.connect()
            await client.initialize()
            await client.send_request("ping", {})
            await client.disconnect()
            await asyncio.sleep(0.05)

        # Force garbage collection
        import gc

        gc.collect()
        await asyncio.sleep(0.2)

        final_memory = get_process_memory_mb()
        memory_increase = final_memory - initial_memory
        per_cycle = memory_increase / num_cycles

        print("\nConnection Cycle Leak Test:")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Increase: {memory_increase:.2f}MB")
        print(f"  Per cycle: {per_cycle:.4f}MB")

        # Allow some memory increase but it should be minimal
        assert per_cycle < 0.5, f"Potential leak: {per_cycle:.4f}MB per cycle"

    @pytest.mark.asyncio
    async def test_operation_cycle_leak(self, initialized_client):
        """Test for memory leaks in operation cycles."""
        num_cycles = 10
        operations_per_cycle = 100

        memory_readings = []

        for cycle in range(num_cycles):
            cycle_start_memory = get_process_memory_mb()

            for _ in range(operations_per_cycle):
                await initialized_client.send_request("ping", {})

            cycle_end_memory = get_process_memory_mb()
            memory_readings.append((cycle, cycle_start_memory, cycle_end_memory))

            # Brief pause between cycles
            await asyncio.sleep(0.1)

        # Analyze memory trend
        first_cycle_delta = memory_readings[0][2] - memory_readings[0][1]
        last_cycle_delta = memory_readings[-1][2] - memory_readings[-1][1]

        print("\nOperation Cycle Leak Test:")
        print(f"  First cycle delta: {first_cycle_delta:.4f}MB")
        print(f"  Last cycle delta: {last_cycle_delta:.4f}MB")

        # Later cycles should not grow significantly more than first
        assert (
            last_cycle_delta < first_cycle_delta * 2
        ), "Memory growth increasing per cycle (potential leak)"


@pytest.mark.performance
@pytest.mark.benchmark
class TestPeakMemoryUsage:
    """Test peak memory usage under load."""

    @pytest.mark.asyncio
    async def test_peak_memory_single_client(self, initialized_client):
        """Test peak memory usage with single client under load."""
        initial_memory = get_process_memory_mb()
        peak_memory = initial_memory

        num_operations = 1000

        for i in range(num_operations):
            await initialized_client.send_request("ping", {})

            if i % 50 == 0:
                current_memory = get_process_memory_mb()
                peak_memory = max(peak_memory, current_memory)

        final_memory = get_process_memory_mb()
        peak_increase = peak_memory - initial_memory

        print("\nPeak Memory Usage (Single Client):")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Peak: {peak_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Peak increase: {peak_increase:.2f}MB")

        assert (
            peak_increase < MEMORY_THRESHOLDS["peak"]["critical"]
        ), f"Peak memory increase {peak_increase:.2f}MB exceeds critical"

    @pytest.mark.asyncio
    async def test_peak_memory_concurrent(self, multiple_clients):
        """Test peak memory usage with concurrent clients."""
        initial_memory = get_process_memory_mb()

        async def client_worker(client):
            await client.initialize()
            for _ in range(50):
                await client.send_request("ping", {})

        await asyncio.gather(*[client_worker(c) for c in multiple_clients])

        peak_memory = get_process_memory_mb()
        peak_increase = peak_memory - initial_memory

        print("\nPeak Memory Usage (Concurrent):")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Peak: {peak_memory:.2f}MB")
        print(f"  Peak increase: {peak_increase:.2f}MB")
        print(f"  Clients: {len(multiple_clients)}")

        assert (
            peak_increase < MEMORY_THRESHOLDS["peak"]["critical"]
        ), f"Peak memory {peak_increase:.2f}MB exceeds critical"


@pytest.mark.performance
@pytest.mark.benchmark
class TestMemoryByToolType:
    """Test memory usage by tool type."""

    @pytest.mark.asyncio
    async def test_memory_by_tool(self, initialized_client):
        """Test memory usage for different tool types."""
        tools = {
            "stats": {},
            "recall": {"query": "test", "limit": 5},
            "recent": {"limit": 10},
            "project": {},
        }

        num_ops_per_tool = 100
        tool_memory = {}

        for tool_name, args in tools.items():
            # Stabilize
            await asyncio.sleep(0.2)
            import gc

            gc.collect()

            start_memory = get_process_memory_mb()

            for _ in range(num_ops_per_tool):
                await initialized_client.call_tool(tool_name, args)

            await asyncio.sleep(0.1)
            end_memory = get_process_memory_mb()
            memory_increase = end_memory - start_memory
            per_op = memory_increase / num_ops_per_tool

            tool_memory[tool_name] = {"total": memory_increase, "per_op": per_op}

        print("\nMemory Usage by Tool Type:")
        for tool, mem in tool_memory.items():
            print(f"  {tool:15s}: {mem['total']:6.2f}MB total, "
                  f"{mem['per_op']*1000:6.2f}KB/op")

        # Each tool should have reasonable memory usage
        for tool, mem in tool_memory.items():
            assert (
                mem["per_op"] < 0.1
            ), f"{tool} uses {mem['per_op']:.4f}MB per operation"
