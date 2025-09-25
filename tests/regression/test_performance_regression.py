"""
Performance regression tests for KuzuMemory.

Tests to ensure performance doesn't degrade over time with
baseline comparisons and performance monitoring.
"""

import pytest
import tempfile
import time
import json
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from kuzu_memory import KuzuMemory
from kuzu_memory.utils.performance import PerformanceMonitor


class TestPerformanceRegression:
    """Performance regression tests with baseline comparisons."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for regression testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "regression_memories.db"
    
    @pytest.fixture
    def regression_config(self):
        """Configuration for regression testing."""
        return {
            "performance": {
                "max_recall_time_ms": 10.0,
                "max_generation_time_ms": 20.0,
                "enable_performance_monitoring": True
            },
            "recall": {
                "max_memories": 10,
                "enable_caching": True,
                "cache_size": 1000
            },
            "extraction": {
                "enable_entity_extraction": True,
                "enable_pattern_compilation": True
            }
        }
    
    @pytest.fixture
    def performance_baseline(self):
        """Performance baseline values for regression testing."""
        return {
            "attach_memories": {
                "mean_ms": 8.0,
                "p95_ms": 15.0,
                "p99_ms": 25.0
            },
            "generate_memories": {
                "mean_ms": 15.0,
                "p95_ms": 30.0,
                "p99_ms": 50.0
            },
            "memory_scaling": {
                "degradation_factor": 2.0,  # Max acceptable degradation
                "max_memories_tested": 1000
            },
            "cache_performance": {
                "cache_hit_speedup": 2.0,  # Minimum speedup from caching
                "cache_miss_overhead": 1.2  # Max overhead for cache miss
            }
        }
    
    def measure_operation_performance(self, operation_func, iterations: int = 50) -> Dict[str, float]:
        """Measure operation performance with detailed statistics."""
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            operation_func()
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        if not times:
            return {}
        
        sorted_times = sorted(times)
        n = len(sorted_times)
        
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'p95': sorted_times[int(0.95 * n)] if n > 1 else sorted_times[0],
            'p99': sorted_times[int(0.99 * n)] if n > 1 else sorted_times[0],
            'std_dev': statistics.stdev(times) if n > 1 else 0.0,
            'iterations': iterations
        }
    
    def test_attach_memories_performance_regression(self, temp_db_path, regression_config, performance_baseline):
        """Test that attach_memories performance doesn't regress."""
        with KuzuMemory(db_path=temp_db_path, config=regression_config) as memory:
            # Populate with test data
            test_contents = [
                "My name is Alice Johnson and I work at TechCorp as a Python developer.",
                "I prefer React for frontend and PostgreSQL for database.",
                "We use Docker for containerization and Kubernetes for orchestration.",
                "Currently working on the user authentication microservice.",
                "My team follows Agile methodology with two-week sprints.",
            ]
            
            for content in test_contents:
                memory.generate_memories(content, user_id="regression-user")
            
            # Test recall performance
            test_query = "What technologies and tools do I use?"
            
            def recall_operation():
                context = memory.attach_memories(
                    test_query,
                    user_id="regression-user",
                    max_memories=5
                )
                assert len(context.memories) > 0
                return context
            
            # Measure performance
            perf_stats = self.measure_operation_performance(recall_operation, iterations=100)
            
            # Compare against baseline
            baseline = performance_baseline["attach_memories"]
            
            print(f"\nattach_memories Performance Regression Test:")
            print(f"  Mean: {perf_stats['mean']:.2f}ms (baseline: {baseline['mean_ms']:.2f}ms)")
            print(f"  P95:  {perf_stats['p95']:.2f}ms (baseline: {baseline['p95_ms']:.2f}ms)")
            print(f"  P99:  {perf_stats['p99']:.2f}ms (baseline: {baseline['p99_ms']:.2f}ms)")
            
            # Regression assertions (allow 20% degradation)
            tolerance = 1.2
            assert perf_stats['mean'] <= baseline['mean_ms'] * tolerance, \
                f"Mean performance regressed: {perf_stats['mean']:.2f}ms > {baseline['mean_ms'] * tolerance:.2f}ms"
            
            assert perf_stats['p95'] <= baseline['p95_ms'] * tolerance, \
                f"P95 performance regressed: {perf_stats['p95']:.2f}ms > {baseline['p95_ms'] * tolerance:.2f}ms"
            
            assert perf_stats['p99'] <= baseline['p99_ms'] * tolerance, \
                f"P99 performance regressed: {perf_stats['p99']:.2f}ms > {baseline['p99_ms'] * tolerance:.2f}ms"
    
    def test_generate_memories_performance_regression(self, temp_db_path, regression_config, performance_baseline):
        """Test that generate_memories performance doesn't regress."""
        with KuzuMemory(db_path=temp_db_path, config=regression_config) as memory:
            test_content = "I'm working on a new microservice using FastAPI and PostgreSQL with Redis caching."
            
            def generation_operation():
                memory_ids = memory.generate_memories(
                    test_content,
                    user_id="regression-user",
                    session_id="perf-test"
                )
                assert len(memory_ids) > 0
                return memory_ids
            
            # Measure performance
            perf_stats = self.measure_operation_performance(generation_operation, iterations=100)
            
            # Compare against baseline
            baseline = performance_baseline["generate_memories"]
            
            print(f"\ngenerate_memories Performance Regression Test:")
            print(f"  Mean: {perf_stats['mean']:.2f}ms (baseline: {baseline['mean_ms']:.2f}ms)")
            print(f"  P95:  {perf_stats['p95']:.2f}ms (baseline: {baseline['p95_ms']:.2f}ms)")
            print(f"  P99:  {perf_stats['p99']:.2f}ms (baseline: {baseline['p99_ms']:.2f}ms)")
            
            # Regression assertions (allow 20% degradation)
            tolerance = 1.2
            assert perf_stats['mean'] <= baseline['mean_ms'] * tolerance, \
                f"Mean performance regressed: {perf_stats['mean']:.2f}ms > {baseline['mean_ms'] * tolerance:.2f}ms"
            
            assert perf_stats['p95'] <= baseline['p95_ms'] * tolerance, \
                f"P95 performance regressed: {perf_stats['p95']:.2f}ms > {baseline['p95_ms'] * tolerance:.2f}ms"
    
    def test_memory_scaling_regression(self, temp_db_path, regression_config, performance_baseline):
        """Test that performance scaling with memory count doesn't regress."""
        with KuzuMemory(db_path=temp_db_path, config=regression_config) as memory:
            user_id = "scaling-user"
            
            # Test performance at different memory counts
            memory_counts = [10, 50, 100, 200]
            performance_data = {}
            
            for count in memory_counts:
                # Add memories up to target count
                current_count = len([m for m in memory.get_statistics().get('storage_stats', {}).get('database_stats', {}).get('memory_count', 0) if True])
                
                while current_count < count:
                    memory.generate_memories(
                        f"Memory {current_count}: This is test content for scaling analysis with Python, React, and PostgreSQL.",
                        user_id=user_id,
                        session_id=f"scaling-session-{current_count}"
                    )
                    current_count += 1
                
                # Measure recall performance at this scale
                def recall_at_scale():
                    context = memory.attach_memories(
                        "What technologies are mentioned in my memories?",
                        user_id=user_id,
                        max_memories=10
                    )
                    assert len(context.memories) > 0
                    return context
                
                perf_stats = self.measure_operation_performance(recall_at_scale, iterations=20)
                performance_data[count] = perf_stats['mean']
            
            print(f"\nMemory Scaling Regression Test:")
            for count, avg_time in performance_data.items():
                print(f"  {count:3d} memories: {avg_time:6.2f}ms")
            
            # Check scaling regression
            baseline_scaling = performance_baseline["memory_scaling"]
            min_time = min(performance_data.values())
            max_time = max(performance_data.values())
            actual_degradation = max_time / min_time
            
            print(f"  Scaling factor: {actual_degradation:.2f}x (baseline limit: {baseline_scaling['degradation_factor']:.2f}x)")
            
            assert actual_degradation <= baseline_scaling['degradation_factor'], \
                f"Scaling performance regressed: {actual_degradation:.2f}x > {baseline_scaling['degradation_factor']:.2f}x"
    
    def test_cache_performance_regression(self, temp_db_path, regression_config, performance_baseline):
        """Test that caching performance doesn't regress."""
        with KuzuMemory(db_path=temp_db_path, config=regression_config) as memory:
            # Populate with data
            memory.generate_memories(
                "I'm a software engineer specializing in Python and React development.",
                user_id="cache-user"
            )
            
            test_query = "What's my specialization?"
            
            # Measure cache miss performance (first call)
            def cache_miss_operation():
                context = memory.attach_memories(test_query, user_id="cache-user")
                assert len(context.memories) > 0
                return context
            
            miss_stats = self.measure_operation_performance(cache_miss_operation, iterations=10)
            
            # Measure cache hit performance (subsequent calls)
            def cache_hit_operation():
                context = memory.attach_memories(test_query, user_id="cache-user")
                assert len(context.memories) > 0
                return context
            
            hit_stats = self.measure_operation_performance(cache_hit_operation, iterations=50)
            
            # Calculate cache performance metrics
            cache_speedup = miss_stats['mean'] / hit_stats['mean'] if hit_stats['mean'] > 0 else 1.0
            
            print(f"\nCache Performance Regression Test:")
            print(f"  Cache miss (first call): {miss_stats['mean']:.2f}ms")
            print(f"  Cache hit (cached call): {hit_stats['mean']:.2f}ms")
            print(f"  Cache speedup: {cache_speedup:.2f}x")
            
            # Compare against baseline
            baseline_cache = performance_baseline["cache_performance"]
            
            assert cache_speedup >= baseline_cache['cache_hit_speedup'], \
                f"Cache speedup regressed: {cache_speedup:.2f}x < {baseline_cache['cache_hit_speedup']:.2f}x"
    
    def test_concurrent_performance_regression(self, temp_db_path, regression_config):
        """Test that concurrent operation performance doesn't regress."""
        import threading
        import queue
        
        with KuzuMemory(db_path=temp_db_path, config=regression_config) as memory:
            # Populate with data
            for i in range(20):
                memory.generate_memories(
                    f"Memory {i}: I work with various technologies including Python, React, and PostgreSQL.",
                    user_id="concurrent-user",
                    session_id=f"session-{i}"
                )
            
            # Concurrent operation test
            results_queue = queue.Queue()
            num_threads = 5
            operations_per_thread = 10
            
            def worker():
                times = []
                for i in range(operations_per_thread):
                    start_time = time.perf_counter()
                    context = memory.attach_memories(
                        f"Query {i}: What technologies do I work with?",
                        user_id="concurrent-user",
                        max_memories=5
                    )
                    end_time = time.perf_counter()
                    times.append((end_time - start_time) * 1000)
                    assert len(context.memories) > 0
                
                results_queue.put(times)
            
            # Start threads
            threads = []
            start_time = time.perf_counter()
            
            for _ in range(num_threads):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            total_time = (time.perf_counter() - start_time) * 1000
            
            # Collect results
            all_times = []
            while not results_queue.empty():
                times = results_queue.get()
                all_times.extend(times)
            
            # Analyze concurrent performance
            mean_time = statistics.mean(all_times)
            p95_time = sorted(all_times)[int(0.95 * len(all_times))]
            throughput = len(all_times) / (total_time / 1000)  # operations per second
            
            print(f"\nConcurrent Performance Regression Test:")
            print(f"  Total operations: {len(all_times)}")
            print(f"  Mean time: {mean_time:.2f}ms")
            print(f"  P95 time: {p95_time:.2f}ms")
            print(f"  Throughput: {throughput:.1f} ops/sec")
            
            # Regression assertions
            assert mean_time < 50.0, f"Concurrent mean time regressed: {mean_time:.2f}ms"
            assert p95_time < 100.0, f"Concurrent P95 time regressed: {p95_time:.2f}ms"
            assert throughput > 10.0, f"Throughput regressed: {throughput:.1f} ops/sec"
    
    def test_memory_usage_regression(self, temp_db_path, regression_config):
        """Test that memory usage doesn't regress significantly."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with KuzuMemory(db_path=temp_db_path, config=regression_config) as memory:
            # Store substantial amount of data
            for i in range(100):
                content = f"""
                Memory {i}: I'm working on project {i} using Python and React.
                The database is PostgreSQL with Redis caching.
                Team members include Alice, Bob, and Charlie.
                We use Docker for containerization and Kubernetes for orchestration.
                """
                memory.generate_memories(
                    content,
                    user_id=f"user-{i % 10}",
                    session_id=f"session-{i}"
                )
            
            # Perform many recall operations
            for i in range(50):
                memory.attach_memories(
                    f"Query {i}: What project am I working on?",
                    user_id=f"user-{i % 10}",
                    max_memories=5
                )
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            print(f"\nMemory Usage Regression Test:")
            print(f"  Initial memory: {initial_memory:.1f} MB")
            print(f"  Final memory: {final_memory:.1f} MB")
            print(f"  Memory increase: {memory_increase:.1f} MB")
            
            # Memory usage should be reasonable
            assert memory_increase < 100.0, f"Memory usage regressed: {memory_increase:.1f} MB increase"
    
    def test_database_size_regression(self, temp_db_path, regression_config):
        """Test that database size growth is reasonable."""
        with KuzuMemory(db_path=temp_db_path, config=regression_config) as memory:
            initial_size = temp_db_path.stat().st_size if temp_db_path.exists() else 0
            
            # Store known amount of data
            test_data_size = 0
            for i in range(50):
                content = f"Memory {i}: This is test content for database size analysis. " * 10
                test_data_size += len(content.encode('utf-8'))
                
                memory.generate_memories(
                    content,
                    user_id="size-test-user",
                    session_id=f"session-{i}"
                )
            
            final_size = temp_db_path.stat().st_size
            size_increase = final_size - initial_size
            
            # Calculate storage efficiency
            storage_ratio = size_increase / test_data_size if test_data_size > 0 else 0
            
            print(f"\nDatabase Size Regression Test:")
            print(f"  Test data size: {test_data_size / 1024:.1f} KB")
            print(f"  Database size increase: {size_increase / 1024:.1f} KB")
            print(f"  Storage ratio: {storage_ratio:.2f}x")
            
            # Storage should be reasonably efficient
            assert storage_ratio < 5.0, f"Database storage efficiency regressed: {storage_ratio:.2f}x"
            assert size_increase < 10 * 1024 * 1024, f"Database size too large: {size_increase / 1024 / 1024:.1f} MB"
