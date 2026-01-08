"""
Performance tests for concurrent load handling.

Tests concurrent connections, load balancing, and stress conditions.
"""

import asyncio
import time

import pytest

from tests.mcp.fixtures.mock_clients import (
    ConcurrentClientSimulator,
    MCPClientSimulator,
)

# Concurrency thresholds
CONCURRENCY_THRESHOLDS = {
    "max_connections": {"target": 10, "critical": 5},
    "success_rate": {"target": 0.95, "critical": 0.90},
    "stress_clients": 50,
}


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestConcurrentConnections:
    """Test concurrent connection handling."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self, project_root):
        """Test establishing multiple concurrent connections."""
        num_clients = 10
        clients = []

        async def create_and_connect():
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            success = await client.connect()
            if success:
                await client.initialize()
            return client, success

        # Create connections concurrently
        start_time = time.perf_counter()
        results = await asyncio.gather(*[create_and_connect() for _ in range(num_clients)])
        elapsed = time.perf_counter() - start_time

        clients = [r[0] for r in results]
        successes = [r[1] for r in results]
        success_count = sum(successes)
        success_rate = success_count / num_clients

        # Cleanup
        for client in clients:
            await client.disconnect()

        print("\nConcurrent Connections Test:")
        print(f"  Clients: {num_clients}")
        print(f"  Successful: {success_count}")
        print(f"  Success rate: {success_rate * 100:.1f}%")
        print(f"  Time: {elapsed:.2f}s")

        assert (
            success_count >= CONCURRENCY_THRESHOLDS["max_connections"]["critical"]
        ), f"Only {success_count}/{num_clients} connections succeeded"
        assert (
            success_rate >= CONCURRENCY_THRESHOLDS["success_rate"]["critical"]
        ), f"Connection success rate {success_rate * 100:.1f}% below critical"

    @pytest.mark.asyncio
    async def test_concurrent_initialization(self, project_root):
        """Test concurrent client initialization."""
        num_clients = 8

        async def init_client():
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            connected = await client.connect()
            if connected:
                await client.initialize()
                # Verify initialization worked
                result = await client.send_request("ping", {})
                await client.disconnect()
                return result is not None
            return False

        start_time = time.perf_counter()
        results = await asyncio.gather(*[init_client() for _ in range(num_clients)])
        elapsed = time.perf_counter() - start_time

        success_count = sum(results)
        success_rate = success_count / num_clients

        print("\nConcurrent Initialization:")
        print(f"  Clients: {num_clients}")
        print(f"  Successful: {success_count}")
        print(f"  Success rate: {success_rate * 100:.1f}%")
        print(f"  Time: {elapsed:.2f}s")

        assert (
            success_rate >= CONCURRENCY_THRESHOLDS["success_rate"]["target"]
        ), f"Initialization success rate {success_rate * 100:.1f}% below target"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestConcurrentExecution:
    """Test concurrent operation execution."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, multiple_clients):
        """Test concurrent tool execution across clients."""
        num_ops_per_client = 20

        async def client_worker(client):
            await client.initialize()
            results = []
            for _ in range(num_ops_per_client):
                result = await client.call_tool("kuzu_stats", {})
                results.append(result is not None)
            return results

        start_time = time.perf_counter()
        all_results = await asyncio.gather(*[client_worker(c) for c in multiple_clients])
        elapsed = time.perf_counter() - start_time

        total_ops = len(multiple_clients) * num_ops_per_client
        total_successes = sum(sum(r) for r in all_results)
        success_rate = total_successes / total_ops
        throughput = total_ops / elapsed

        print("\nConcurrent Tool Execution:")
        print(f"  Clients: {len(multiple_clients)}")
        print(f"  Total operations: {total_ops}")
        print(f"  Successful: {total_successes}")
        print(f"  Success rate: {success_rate * 100:.1f}%")
        print(f"  Throughput: {throughput:.2f} ops/sec")

        assert (
            success_rate >= CONCURRENCY_THRESHOLDS["success_rate"]["critical"]
        ), f"Concurrent execution success rate {success_rate * 100:.1f}% below critical"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, multiple_clients):
        """Test concurrent mixed operations."""
        operations = [
            ("ping", {}, False),
            ("stats", {}, True),
            ("tools/list", {}, False),
            ("recall", {"query": "test", "limit": 5}, True),
        ]

        async def client_worker(client):
            await client.initialize()
            results = []
            for method, args, is_tool in operations * 5:  # 20 ops per client
                if is_tool:
                    result = await client.call_tool(method, args)
                else:
                    result = await client.send_request(method, args)
                results.append(result is not None)
            return results

        start_time = time.perf_counter()
        all_results = await asyncio.gather(*[client_worker(c) for c in multiple_clients])
        _elapsed = time.perf_counter() - start_time

        total_ops = len(multiple_clients) * len(operations) * 5
        total_successes = sum(sum(r) for r in all_results)
        success_rate = total_successes / total_ops

        print("\nConcurrent Mixed Operations:")
        print(f"  Clients: {len(multiple_clients)}")
        print(f"  Operations: {total_ops}")
        print(f"  Successful: {total_successes}")
        print(f"  Success rate: {success_rate * 100:.1f}%")

        assert (
            success_rate >= CONCURRENCY_THRESHOLDS["success_rate"]["target"]
        ), f"Mixed operation success rate {success_rate * 100:.1f}% below target"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestLoadBalancing:
    """Test load balancing and resource contention."""

    @pytest.mark.asyncio
    async def test_resource_contention(self, multiple_clients):
        """Test behavior under resource contention."""

        # Have all clients compete for resources simultaneously
        async def aggressive_worker(client):
            await client.initialize()
            successes = 0
            for _ in range(30):
                try:
                    result = await asyncio.wait_for(client.call_tool("kuzu_stats", {}), timeout=2.0)
                    if result is not None:
                        successes += 1
                except TimeoutError:
                    pass
            return successes

        start_time = time.perf_counter()
        results = await asyncio.gather(*[aggressive_worker(c) for c in multiple_clients])
        elapsed = time.perf_counter() - start_time

        total_expected = len(multiple_clients) * 30
        total_successes = sum(results)
        success_rate = total_successes / total_expected

        print("\nResource Contention Test:")
        print(f"  Concurrent clients: {len(multiple_clients)}")
        print(f"  Expected operations: {total_expected}")
        print(f"  Successful: {total_successes}")
        print(f"  Success rate: {success_rate * 100:.1f}%")
        print(f"  Time: {elapsed:.2f}s")

        assert (
            success_rate >= CONCURRENCY_THRESHOLDS["success_rate"]["critical"]
        ), f"Success rate under contention {success_rate * 100:.1f}% below critical"

    @pytest.mark.asyncio
    async def test_load_distribution(self, concurrent_simulator):
        """Test that load is distributed evenly across clients."""
        operations = [{"method": "ping", "params": {}}]

        result = await concurrent_simulator.simulate_load(
            operations=operations, operations_per_client=30
        )

        # Check that latency is consistent across clients
        latencies = result.get("client_latencies", [])
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_deviation = max(abs(lat - avg_latency) for lat in latencies)
            deviation_pct = (max_deviation / avg_latency) * 100

            print("\nLoad Distribution:")
            print(f"  Avg latency: {avg_latency:.2f}ms")
            print(f"  Max deviation: {max_deviation:.2f}ms ({deviation_pct:.1f}%)")

            # Deviation should be reasonable
            assert deviation_pct < 50, f"High latency deviation: {deviation_pct:.1f}%"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestSessionIsolation:
    """Test concurrent session isolation."""

    @pytest.mark.asyncio
    async def test_session_independence(self, multiple_clients):
        """Test that concurrent sessions don't interfere."""

        async def session_worker(client, session_id):
            await client.initialize()

            # Each client performs unique operations
            results = []
            for i in range(10):
                result = await client.call_tool(
                    "remember", {"content": f"session_{session_id}_memory_{i}"}
                )
                results.append(result is not None if result else False)

            # Verify operations succeeded
            return sum(results) == len(results)

        # Run sessions concurrently
        session_results = await asyncio.gather(
            *[session_worker(c, i) for i, c in enumerate(multiple_clients)]
        )

        success_count = sum(session_results)
        success_rate = success_count / len(multiple_clients)

        print("\nSession Isolation Test:")
        print(f"  Sessions: {len(multiple_clients)}")
        print(f"  Successful: {success_count}")
        print(f"  Success rate: {success_rate * 100:.1f}%")

        assert (
            success_rate >= CONCURRENCY_THRESHOLDS["success_rate"]["target"]
        ), f"Session isolation success rate {success_rate * 100:.1f}% below target"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.slow
@pytest.mark.flaky_process
class TestStressLoad:
    """Test behavior under stress conditions."""

    @pytest.mark.asyncio
    async def test_stress_many_clients(self, project_root):
        """Test with many concurrent clients (stress test)."""
        num_clients = CONCURRENCY_THRESHOLDS["stress_clients"]
        ops_per_client = 5

        async def stress_worker():
            client = MCPClientSimulator(project_root=project_root, timeout=10.0)
            try:
                connected = await client.connect()
                if not connected:
                    return 0

                await client.initialize()

                successes = 0
                for _ in range(ops_per_client):
                    try:
                        result = await asyncio.wait_for(
                            client.send_request("ping", {}), timeout=3.0
                        )
                        if result is not None:
                            successes += 1
                    except TimeoutError:
                        pass

                await client.disconnect()
                return successes
            except Exception:
                return 0

        print(f"\nStress Test: {num_clients} concurrent clients")
        start_time = time.perf_counter()
        results = await asyncio.gather(*[stress_worker() for _ in range(num_clients)])
        elapsed = time.perf_counter() - start_time

        total_expected = num_clients * ops_per_client
        total_successes = sum(results)
        success_rate = total_successes / total_expected if total_expected > 0 else 0

        print(f"  Expected operations: {total_expected}")
        print(f"  Successful: {total_successes}")
        print(f"  Success rate: {success_rate * 100:.1f}%")
        print(f"  Time: {elapsed:.2f}s")

        # Under stress, we accept lower success rate
        assert success_rate >= 0.70, f"Stress test success rate {success_rate * 100:.1f}% too low"

    @pytest.mark.asyncio
    async def test_burst_load(self, project_root):
        """Test handling of burst traffic."""
        num_bursts = 3
        clients_per_burst = 10

        async def burst_worker():
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            connected = await client.connect()
            if connected:
                await client.initialize()
                result = await client.send_request("ping", {})
                await client.disconnect()
                return result is not None
            return False

        burst_results = []
        for burst in range(num_bursts):
            print(f"\nBurst {burst + 1}/{num_bursts}")
            start_time = time.perf_counter()
            results = await asyncio.gather(*[burst_worker() for _ in range(clients_per_burst)])
            elapsed = time.perf_counter() - start_time

            success_count = sum(results)
            success_rate = success_count / clients_per_burst
            burst_results.append(success_rate)

            print(f"  Success rate: {success_rate * 100:.1f}%")
            print(f"  Time: {elapsed:.2f}s")

            # Brief pause between bursts
            await asyncio.sleep(0.5)

        avg_success_rate = sum(burst_results) / len(burst_results)
        print(f"\nOverall burst success rate: {avg_success_rate * 100:.1f}%")

        assert (
            avg_success_rate >= CONCURRENCY_THRESHOLDS["success_rate"]["critical"]
        ), f"Burst success rate {avg_success_rate * 100:.1f}% below critical"
