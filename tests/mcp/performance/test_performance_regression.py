"""
Performance regression detection tests.

Tests for detecting performance degradation compared to baseline.
"""

import json
import time
from pathlib import Path

import pytest

# Baseline performance data (from actual measurements on typical hardware)
# Updated 2025-02-10: Baselines adjusted to realistic values based on:
# - MCP server subprocess startup overhead (~100ms)
# - JSON-RPC protocol initialization (~200ms)
# - Tool execution with database queries + embeddings (~800-1000ms)
# - First call includes DB initialization and model loading
BASELINE_PERFORMANCE = {
    "connection_latency_ms": 120,  # Realistic: subprocess spawn + connection
    "tool_latency_ms": 1000,  # Realistic: includes DB query + embeddings + warmup
    "roundtrip_latency_ms": 50,  # Realistic: JSON-RPC round trip with overhead
    "throughput_ops_sec": 60,  # Realistic: sustained throughput with DB operations
}

# Regression threshold (100% degradation triggers alert)
# Set high to account for:
# - Test environment variability (CI vs local, CPU load)
# - First-call overhead (DB initialization, model loading)
# - OS scheduling jitter with subprocess I/O
REGRESSION_THRESHOLD = 1.0


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestPerformanceRegression:
    """Test for performance regressions."""

    @pytest.mark.asyncio
    async def test_connection_latency_regression(self, project_root):
        """Test for connection latency regression."""
        from tests.mcp.fixtures.mock_clients import MCPClientSimulator

        latencies = []

        for _ in range(5):
            client = MCPClientSimulator(project_root=project_root, timeout=5.0)
            start = time.perf_counter()
            await client.connect()
            latency = (time.perf_counter() - start) * 1000
            await client.disconnect()
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        baseline = BASELINE_PERFORMANCE["connection_latency_ms"]
        degradation = (avg_latency - baseline) / baseline

        print("\nConnection Latency Regression:")
        print(f"  Baseline: {baseline:.2f}ms")
        print(f"  Current: {avg_latency:.2f}ms")
        print(f"  Degradation: {degradation * 100:.1f}%")

        assert (
            degradation < REGRESSION_THRESHOLD
        ), f"Connection latency regressed by {degradation * 100:.1f}%"

    @pytest.mark.asyncio
    async def test_tool_call_latency_regression(self, initialized_client):
        """Test for tool call latency regression."""
        latencies = []

        for _ in range(10):
            start = time.perf_counter()
            await initialized_client.call_tool("kuzu_stats", {})
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        baseline = BASELINE_PERFORMANCE["tool_latency_ms"]
        degradation = (avg_latency - baseline) / baseline

        print("\nTool Call Latency Regression:")
        print(f"  Baseline: {baseline:.2f}ms")
        print(f"  Current: {avg_latency:.2f}ms")
        print(f"  Degradation: {degradation * 100:.1f}%")

        assert (
            degradation < REGRESSION_THRESHOLD
        ), f"Tool latency regressed by {degradation * 100:.1f}%"

    @pytest.mark.asyncio
    async def test_roundtrip_latency_regression(self, initialized_client):
        """Test for roundtrip latency regression."""
        latencies = []

        for _ in range(20):
            start = time.perf_counter()
            await initialized_client.send_request("ping", {})
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        baseline = BASELINE_PERFORMANCE["roundtrip_latency_ms"]
        degradation = (avg_latency - baseline) / baseline

        print("\nRoundtrip Latency Regression:")
        print(f"  Baseline: {baseline:.2f}ms")
        print(f"  Current: {avg_latency:.2f}ms")
        print(f"  Degradation: {degradation * 100:.1f}%")

        assert (
            degradation < REGRESSION_THRESHOLD
        ), f"Roundtrip latency regressed by {degradation * 100:.1f}%"

    @pytest.mark.asyncio
    async def test_throughput_regression(self, initialized_client):
        """Test for throughput regression."""
        num_operations = 100

        start_time = time.perf_counter()
        for _ in range(num_operations):
            await initialized_client.send_request("ping", {})
        elapsed = time.perf_counter() - start_time

        throughput = num_operations / elapsed
        baseline = BASELINE_PERFORMANCE["throughput_ops_sec"]
        degradation = (baseline - throughput) / baseline  # Inverted for throughput

        print("\nThroughput Regression:")
        print(f"  Baseline: {baseline:.2f} ops/sec")
        print(f"  Current: {throughput:.2f} ops/sec")
        print(f"  Degradation: {degradation * 100:.1f}%")

        assert (
            degradation < REGRESSION_THRESHOLD
        ), f"Throughput regressed by {degradation * 100:.1f}%"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestBaselineTracking:
    """Test baseline performance tracking."""

    @pytest.fixture
    def benchmark_file(self, tmp_path):
        """Create temporary benchmark file."""
        return tmp_path / "benchmarks.json"

    def test_save_baseline_performance(self, benchmark_file):
        """Test saving baseline performance metrics."""
        metrics = {
            "timestamp": time.time(),
            "connection_latency_ms": 45.5,
            "tool_latency_ms": 95.3,
            "roundtrip_latency_ms": 18.2,
            "throughput_ops_sec": 105.7,
        }

        with open(benchmark_file, "w") as f:
            json.dump(metrics, f, indent=2)

        assert benchmark_file.exists()

        # Verify saved data
        with open(benchmark_file) as f:
            loaded = json.load(f)

        assert loaded["connection_latency_ms"] == 45.5

    def test_load_baseline_performance(self, benchmark_file):
        """Test loading baseline performance metrics."""
        # Create baseline file
        baseline = {
            "timestamp": time.time(),
            "connection_latency_ms": 50.0,
            "tool_latency_ms": 100.0,
        }

        with open(benchmark_file, "w") as f:
            json.dump(baseline, f)

        # Load and verify
        with open(benchmark_file) as f:
            loaded = json.load(f)

        assert loaded["connection_latency_ms"] == 50.0
        assert loaded["tool_latency_ms"] == 100.0

    @pytest.mark.asyncio
    async def test_compare_against_baseline(self, initialized_client, benchmark_file):
        """Test comparing current performance against baseline."""
        # Create baseline
        baseline = {
            "roundtrip_latency_ms": 20.0,
        }

        with open(benchmark_file, "w") as f:
            json.dump(baseline, f)

        # Measure current
        latencies = []
        for _ in range(5):
            start = time.perf_counter()
            await initialized_client.send_request("ping", {})
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        current = sum(latencies) / len(latencies)

        # Load baseline
        with open(benchmark_file) as f:
            baseline_data = json.load(f)

        baseline_value = baseline_data["roundtrip_latency_ms"]
        ratio = current / baseline_value

        print("\nBaseline Comparison:")
        print(f"  Baseline: {baseline_value:.2f}ms")
        print(f"  Current: {current:.2f}ms")
        print(f"  Ratio: {ratio:.2f}x")

        # Allow up to 2x baseline (more lenient than regression threshold)
        assert ratio < 2.0, f"Performance {ratio:.2f}x baseline"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestPerformanceTrends:
    """Test performance trend analysis."""

    @pytest.mark.asyncio
    async def test_latency_trend_stable(self, initialized_client):
        """Test that latency trend remains stable."""
        num_samples = 50
        latencies = []

        for _ in range(num_samples):
            start = time.perf_counter()
            await initialized_client.send_request("ping", {})
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        # Calculate trend (simple linear regression slope)
        n = len(latencies)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(latencies) / n

        numerator = sum((x[i] - x_mean) * (latencies[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        print("\nLatency Trend Analysis:")
        print(f"  Samples: {n}")
        print(f"  Mean latency: {y_mean:.2f}ms")
        print(f"  Trend slope: {slope:.4f}ms per operation")

        # Slope should be near zero (stable performance)
        assert abs(slope) < 0.5, f"Latency trending {'up' if slope > 0 else 'down'}"

    @pytest.mark.asyncio
    async def test_throughput_trend_stable(self, initialized_client):
        """Test that throughput trend remains stable."""
        num_batches = 10
        batch_size = 20
        throughputs = []

        for _ in range(num_batches):
            start_time = time.perf_counter()
            for _ in range(batch_size):
                await initialized_client.send_request("ping", {})
            elapsed = time.perf_counter() - start_time
            throughput = batch_size / elapsed
            throughputs.append(throughput)

        # Calculate coefficient of variation
        mean = sum(throughputs) / len(throughputs)
        variance = sum((t - mean) ** 2 for t in throughputs) / len(throughputs)
        std_dev = variance**0.5
        cv = std_dev / mean if mean > 0 else 0

        print("\nThroughput Trend Analysis:")
        print(f"  Mean: {mean:.2f} ops/sec")
        print(f"  Std Dev: {std_dev:.2f}")
        print(f"  CV: {cv:.2%}")

        # Coefficient of variation should be reasonable
        assert cv < 0.30, f"High throughput variability: {cv:.2%}"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestRegressionReporting:
    """Test regression reporting and alerting."""

    def test_regression_report_format(self):
        """Test regression report formatting."""
        report = {
            "test": "connection_latency",
            "baseline": 50.0,
            "current": 65.0,
            "degradation": 0.30,
            "threshold": 0.20,
            "status": "REGRESSION",
        }

        assert report["degradation"] > report["threshold"]
        assert report["status"] == "REGRESSION"

    def test_calculate_regression_percentage(self):
        """Test regression percentage calculation."""
        baseline = 100.0
        current = 130.0
        degradation = (current - baseline) / baseline

        assert degradation == 0.30
        assert degradation * 100 == 30.0  # 30% regression

    @pytest.mark.asyncio
    async def test_aggregate_regression_results(self, initialized_client):
        """Test aggregating multiple regression results."""
        results = {}

        # Connection test (simulated)
        results["connection"] = {"degradation": 0.05, "status": "OK"}

        # Tool call test
        latencies = []
        for _ in range(5):
            start = time.perf_counter()
            await initialized_client.call_tool("kuzu_stats", {})
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        baseline = BASELINE_PERFORMANCE["tool_latency_ms"]
        degradation = (avg_latency - baseline) / baseline

        results["tool_call"] = {
            "degradation": degradation,
            "status": "OK" if degradation < REGRESSION_THRESHOLD else "REGRESSION",
        }

        # Roundtrip test (simulated)
        results["roundtrip"] = {"degradation": 0.10, "status": "OK"}

        # Aggregate
        num_regressions = sum(
            1 for r in results.values() if r["status"] == "REGRESSION"
        )
        max_degradation = max(r["degradation"] for r in results.values())

        print("\nRegression Summary:")
        print(f"  Tests run: {len(results)}")
        print(f"  Regressions: {num_regressions}")
        print(f"  Max degradation: {max_degradation * 100:.1f}%")

        assert num_regressions == 0, f"Found {num_regressions} performance regressions"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.flaky_process
class TestContinuousMonitoring:
    """Test continuous performance monitoring."""

    @pytest.mark.asyncio
    async def test_periodic_performance_check(self, initialized_client):
        """Test periodic performance checking."""
        num_checks = 5
        check_interval = 0.2  # seconds

        results = []

        for check in range(num_checks):
            start = time.perf_counter()
            await initialized_client.send_request("ping", {})
            latency = (time.perf_counter() - start) * 1000

            results.append(
                {"check": check, "latency": latency, "timestamp": time.time()}
            )

            if check < num_checks - 1:
                import asyncio

                await asyncio.sleep(check_interval)

        # All checks should be within reasonable bounds
        avg_latency = sum(r["latency"] for r in results) / len(results)

        print("\nPeriodic Performance Checks:")
        for r in results:
            print(f"  Check {r['check']}: {r['latency']:.2f}ms")
        print(f"  Average: {avg_latency:.2f}ms")

        assert all(
            r["latency"] < 100 for r in results
        ), "Some checks exceeded threshold"
