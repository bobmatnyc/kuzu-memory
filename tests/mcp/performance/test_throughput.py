"""
Performance tests for MCP server throughput.

Tests sequential and concurrent operation throughput against
defined performance thresholds.
"""

import asyncio
import time

import pytest

from tests.mcp.fixtures.mock_clients import (
    ConcurrentClientSimulator,
    MCPClientSimulator,
)

# Throughput thresholds
THROUGHPUT_THRESHOLDS = {
    "sequential": {"target": 100, "critical": 50},  # ops/sec
    "concurrent": {"target": 50, "critical": 25},  # ops/sec
    "sustained": {"target": 80, "critical": 40},  # ops/sec
}


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestSequentialThroughput:
    """Test sequential operation throughput."""

    @pytest.mark.asyncio
    async def test_ping_throughput(self, initialized_client):
        """Test throughput of sequential ping operations."""
        num_operations = 100
        start_time = time.perf_counter()

        for _ in range(num_operations):
            result = await initialized_client.send_request("ping", {})
            assert result is not None

        elapsed = time.perf_counter() - start_time
        throughput = num_operations / elapsed

        print(f"\nPing Throughput: {throughput:.2f} ops/sec")
        assert (
            throughput >= THROUGHPUT_THRESHOLDS["sequential"]["critical"]
        ), f"Throughput {throughput:.2f} ops/sec below critical threshold"

    @pytest.mark.asyncio
    async def test_stats_tool_throughput(self, initialized_client):
        """Test throughput of sequential stats tool calls."""
        num_operations = 50
        start_time = time.perf_counter()

        for _ in range(num_operations):
            result = await initialized_client.call_tool("kuzu_stats", {})
            assert result is not None

        elapsed = time.perf_counter() - start_time
        throughput = num_operations / elapsed

        print(f"\nStats Tool Throughput: {throughput:.2f} ops/sec")
        assert (
            throughput >= THROUGHPUT_THRESHOLDS["sequential"]["critical"]
        ), f"Stats throughput {throughput:.2f} ops/sec below critical threshold"

    @pytest.mark.asyncio
    async def test_mixed_operation_throughput(self, initialized_client):
        """Test throughput of mixed operations."""
        operations = [
            ("ping", {}),
            ("tools/list", {}),
            ("stats", {}),
            ("recall", {"query": "test", "limit": 5}),
            ("recent", {"limit": 10}),
        ] * 20  # 100 operations

        start_time = time.perf_counter()

        for method, args in operations:
            if method in ["stats", "recall", "recent"]:
                result = await initialized_client.call_tool(method, args)
            else:
                result = await initialized_client.send_request(method, args)
            assert result is not None

        elapsed = time.perf_counter() - start_time
        throughput = len(operations) / elapsed

        print(f"\nMixed Operations Throughput: {throughput:.2f} ops/sec")
        assert (
            throughput >= THROUGHPUT_THRESHOLDS["sequential"]["critical"]
        ), f"Mixed throughput {throughput:.2f} ops/sec below critical threshold"

    @pytest.mark.asyncio
    async def test_tool_specific_throughput(self, initialized_client):
        """Test throughput for each tool type."""
        tools = {
            "stats": {},
            "recall": {"query": "test", "limit": 5},
            "recent": {"limit": 10},
            "project": {},
        }

        num_ops_per_tool = 25
        throughputs = {}

        for tool_name, args in tools.items():
            start_time = time.perf_counter()

            for _ in range(num_ops_per_tool):
                result = await initialized_client.call_tool(tool_name, args)
                assert result is not None

            elapsed = time.perf_counter() - start_time
            throughput = num_ops_per_tool / elapsed
            throughputs[tool_name] = throughput

        print("\nTool-Specific Throughput:")
        for tool, tput in throughputs.items():
            status = (
                "✓"
                if tput >= THROUGHPUT_THRESHOLDS["sequential"]["target"]
                else (
                    "⚠"
                    if tput >= THROUGHPUT_THRESHOLDS["sequential"]["critical"]
                    else "✗"
                )
            )
            print(f"  {tool:15s}: {tput:6.2f} ops/sec {status}")


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.slow
@pytest.mark.flaky_process
class TestConcurrentThroughput:
    """Test concurrent operation throughput."""

    @pytest.mark.asyncio
    async def test_concurrent_ping_throughput(self, multiple_clients):
        """Test throughput with concurrent clients."""
        num_ops_per_client = 20

        async def client_worker(client):
            for _ in range(num_ops_per_client):
                await client.initialize()
                await client.send_request("ping", {})

        start_time = time.perf_counter()
        await asyncio.gather(*[client_worker(c) for c in multiple_clients])
        elapsed = time.perf_counter() - start_time

        total_ops = len(multiple_clients) * num_ops_per_client
        throughput = total_ops / elapsed

        print(
            f"\nConcurrent Ping Throughput ({len(multiple_clients)} clients): "
            f"{throughput:.2f} ops/sec"
        )
        assert (
            throughput >= THROUGHPUT_THRESHOLDS["concurrent"]["critical"]
        ), f"Concurrent throughput {throughput:.2f} ops/sec below critical threshold"

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, multiple_clients):
        """Test concurrent tool call throughput."""
        num_ops_per_client = 15

        async def client_worker(client):
            await client.initialize()
            for _ in range(num_ops_per_client):
                await client.call_tool("kuzu_stats", {})

        start_time = time.perf_counter()
        await asyncio.gather(*[client_worker(c) for c in multiple_clients])
        elapsed = time.perf_counter() - start_time

        total_ops = len(multiple_clients) * num_ops_per_client
        throughput = total_ops / elapsed

        print(
            f"\nConcurrent Tool Call Throughput ({len(multiple_clients)} clients): "
            f"{throughput:.2f} ops/sec"
        )
        assert (
            throughput >= THROUGHPUT_THRESHOLDS["concurrent"]["critical"]
        ), f"Concurrent tool throughput {throughput:.2f} ops/sec below critical"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, concurrent_simulator):
        """Test throughput with mixed concurrent operations."""
        operations = [
            {"method": "ping", "params": {}},
            {"method": "stats", "params": {}, "is_tool": True},
            {"method": "tools/list", "params": {}},
        ]

        result = await concurrent_simulator.simulate_load(
            operations=operations, operations_per_client=10
        )

        assert result["success_rate"] >= 0.95, "Should have >95% success rate"
        assert (
            result["throughput"] >= THROUGHPUT_THRESHOLDS["concurrent"]["critical"]
        ), f"Throughput {result['throughput']:.2f} ops/sec below critical threshold"

        print("\nConcurrent Mixed Operations:")
        print(f"  Throughput: {result['throughput']:.2f} ops/sec")
        print(f"  Success Rate: {result['success_rate'] * 100:.1f}%")
        print(f"  Avg Latency: {result['avg_latency']:.2f}ms")


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.slow
@pytest.mark.flaky_process
class TestSustainedThroughput:
    """Test sustained load throughput."""

    @pytest.mark.asyncio
    async def test_sustained_load(self, initialized_client):
        """Test throughput under sustained load (1000 operations)."""
        num_operations = 1000
        operations = [
            ("ping", {}),
            ("tools/list", {}),
            ("stats", {}),
        ] * (num_operations // 3)

        start_time = time.perf_counter()
        success_count = 0

        for method, args in operations:
            try:
                if method == "stats":
                    result = await initialized_client.call_tool(method, args)
                else:
                    result = await initialized_client.send_request(method, args)
                if result is not None:
                    success_count += 1
            except Exception:
                pass  # Count as failure

        elapsed = time.perf_counter() - start_time
        throughput = success_count / elapsed
        success_rate = success_count / len(operations)

        print("\nSustained Load Results (1000 operations):")
        print(f"  Throughput: {throughput:.2f} ops/sec")
        print(f"  Success Rate: {success_rate * 100:.1f}%")
        print(f"  Total Time: {elapsed:.2f}s")

        assert success_rate >= 0.95, "Should maintain >95% success rate under load"
        assert (
            throughput >= THROUGHPUT_THRESHOLDS["sustained"]["critical"]
        ), f"Sustained throughput {throughput:.2f} ops/sec below critical threshold"

    @pytest.mark.asyncio
    async def test_throughput_under_memory_operations(self, initialized_client):
        """Test throughput when performing memory operations."""
        num_operations = 100

        # Mix of memory operations
        operations = [
            ("recall", {"query": "test", "limit": 5}),
            ("recent", {"limit": 10}),
            ("stats", {}),
        ] * (num_operations // 3)

        start_time = time.perf_counter()

        for tool, args in operations:
            result = await initialized_client.call_tool(tool, args)
            assert result is not None

        elapsed = time.perf_counter() - start_time
        throughput = num_operations / elapsed

        print(f"\nMemory Operations Throughput: {throughput:.2f} ops/sec")
        assert (
            throughput >= THROUGHPUT_THRESHOLDS["sustained"]["critical"]
        ), f"Memory ops throughput {throughput:.2f} ops/sec below critical threshold"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestThroughputDegradation:
    """Test for throughput degradation over time."""

    @pytest.mark.asyncio
    async def test_no_throughput_degradation(self, initialized_client):
        """Test that throughput doesn't degrade over time."""
        num_batches = 5
        batch_size = 50
        throughputs = []

        for batch in range(num_batches):
            start_time = time.perf_counter()

            for _ in range(batch_size):
                await initialized_client.send_request("ping", {})

            elapsed = time.perf_counter() - start_time
            throughput = batch_size / elapsed
            throughputs.append(throughput)

            print(f"Batch {batch + 1} throughput: {throughput:.2f} ops/sec")

        # Check that throughput doesn't degrade significantly
        first_half_avg = sum(throughputs[: len(throughputs) // 2]) / (
            len(throughputs) // 2
        )
        second_half_avg = sum(throughputs[len(throughputs) // 2 :]) / (
            len(throughputs) - len(throughputs) // 2
        )

        degradation = (first_half_avg - second_half_avg) / first_half_avg

        print("\nThroughput Degradation Analysis:")
        print(f"  First half avg: {first_half_avg:.2f} ops/sec")
        print(f"  Second half avg: {second_half_avg:.2f} ops/sec")
        print(f"  Degradation: {degradation * 100:.1f}%")

        assert degradation < 0.20, f"Throughput degraded by {degradation * 100:.1f}%"

    @pytest.mark.asyncio
    async def test_throughput_recovery(self, initialized_client):
        """Test that throughput recovers after burst load."""
        # Baseline throughput
        start_time = time.perf_counter()
        for _ in range(20):
            await initialized_client.send_request("ping", {})
        baseline_throughput = 20 / (time.perf_counter() - start_time)

        # Burst load
        start_time = time.perf_counter()
        for _ in range(100):
            await initialized_client.send_request("ping", {})
        burst_throughput = 100 / (time.perf_counter() - start_time)

        # Recovery throughput
        await asyncio.sleep(0.5)  # Brief pause
        start_time = time.perf_counter()
        for _ in range(20):
            await initialized_client.send_request("ping", {})
        recovery_throughput = 20 / (time.perf_counter() - start_time)

        print("\nThroughput Recovery:")
        print(f"  Baseline: {baseline_throughput:.2f} ops/sec")
        print(f"  Burst: {burst_throughput:.2f} ops/sec")
        print(f"  Recovery: {recovery_throughput:.2f} ops/sec")

        # Recovery should be close to baseline
        recovery_ratio = recovery_throughput / baseline_throughput
        assert (
            recovery_ratio >= 0.80
        ), f"Throughput recovered to only {recovery_ratio * 100:.1f}% of baseline"
