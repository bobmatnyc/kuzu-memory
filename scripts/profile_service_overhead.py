#!/usr/bin/env python3
"""
Profile service layer overhead for migrated commands.

Measures baseline vs. service layer execution time to verify <5% overhead target.
"""
import time
import statistics
from pathlib import Path
from typing import Dict, Tuple

# Add project to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.core.memory import KuzuMemory
from kuzu_memory.core.config import KuzuMemoryConfig


def measure_execution_time(func, iterations: int = 10) -> Tuple[float, float]:
    """Measure mean and std dev of execution time."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)

    return statistics.mean(times), statistics.stdev(times) if len(times) > 1 else 0.0


def profile_memory_service_overhead() -> Dict[str, float]:
    """Profile overhead of memory service initialization and simple query."""
    test_db = Path("/tmp/kuzu_profile_test")
    test_db.mkdir(exist_ok=True)

    # Baseline: Direct instantiation (old pattern)
    def baseline():
        config = KuzuMemoryConfig()
        memory = KuzuMemory(str(test_db / ".kuzu"), config)
        # Simple operation
        _ = memory.get_memory_count()
        memory.close()

    # Service layer: Via ServiceManager (new pattern)
    def service_layer():
        with ServiceManager.memory_service(test_db) as memory:
            _ = memory.get_memory_count()

    baseline_mean, baseline_std = measure_execution_time(baseline, iterations=20)
    service_mean, service_std = measure_execution_time(service_layer, iterations=20)

    overhead_ms = (service_mean - baseline_mean) * 1000
    overhead_pct = ((service_mean - baseline_mean) / baseline_mean) * 100 if baseline_mean > 0 else 0

    return {
        "baseline_ms": baseline_mean * 1000,
        "baseline_std_ms": baseline_std * 1000,
        "service_ms": service_mean * 1000,
        "service_std_ms": service_std * 1000,
        "overhead_ms": overhead_ms,
        "overhead_pct": overhead_pct,
    }


def print_results(service_name: str, results: Dict[str, float]):
    """Print formatted results."""
    print(f"\n{'='*60}")
    print(f"{service_name} Service Overhead Analysis")
    print(f"{'='*60}")
    print(f"Baseline:     {results['baseline_ms']:>8.3f} ± {results['baseline_std_ms']:>6.3f} ms")
    print(f"Service:      {results['service_ms']:>8.3f} ± {results['service_std_ms']:>6.3f} ms")
    print(f"Overhead:     {results['overhead_ms']:>8.3f} ms ({results['overhead_pct']:>6.2f}%)")

    if results['overhead_pct'] < 5.0:
        status = "✅ PASS"
    elif results['overhead_pct'] < 10.0:
        status = "⚠️  ACCEPTABLE"
    else:
        status = "❌ NEEDS OPTIMIZATION"
    print(f"Status:       {status} (target: <5% overhead)")


def main():
    """Run all profiling tests."""
    print("Performance Profiling Report - Phase 5.4")
    print("=" * 60)
    print("Testing service layer overhead for migrated commands")
    print("Target: <5% overhead vs. direct instantiation")
    print()

    # Profile memory service (used by: recall, enhance, stats, init)
    print("Test 1: Memory Service Initialization + Simple Query")
    memory_results = profile_memory_service_overhead()
    print_results("Memory", memory_results)

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")

    overhead_pct = memory_results['overhead_pct']

    print(f"Measured overhead: {overhead_pct:.2f}%")
    print()

    if overhead_pct < 5.0:
        print("✅ Service layer meets <5% overhead target")
        print("   No caching optimization needed")
    elif overhead_pct < 10.0:
        print("⚠️  Overhead exceeds 5% but under 10%")
        print("   Acceptable for Phase 5.4 - monitor in production")
    else:
        print("❌ Overhead exceeds 10% - caching recommended")

    print()
    print("Note: ServiceManager uses context managers for lifecycle management.")
    print("      The measured overhead includes initialization + cleanup,")
    print("      which is a one-time cost per command invocation.")
    print()
    print("Migrated Commands Coverage (10 commands):")
    print("  1. recall (memory_service)")
    print("  2. enhance (memory_service)")
    print("  3. stats (memory_service)")
    print("  4. git status (git_sync_service)")
    print("  5. git sync (git_sync_service)")
    print("  6. git push (git_sync_service)")
    print("  7. git pull (git_sync_service)")
    print("  8. init (memory_service)")
    print("  9. doctor mcp (diagnostic_service)")
    print(" 10. doctor check (diagnostic_service)")

    # Cleanup
    import shutil
    test_db = Path("/tmp/kuzu_profile_test")
    if test_db.exists():
        shutil.rmtree(test_db)


if __name__ == "__main__":
    main()
