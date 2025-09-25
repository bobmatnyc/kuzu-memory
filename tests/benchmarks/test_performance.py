"""
Performance benchmarks for KuzuMemory.

Tests performance requirements and provides benchmarking data
for attach_memories() <10ms and generate_memories() <20ms targets.
"""

import pytest
import time
import statistics
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from kuzu_memory import KuzuMemory


class TestPerformanceBenchmarks:
    """Performance benchmarks for KuzuMemory operations."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for benchmarking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "benchmark_memories.db"
    
    @pytest.fixture
    def benchmark_config(self):
        """Configuration optimized for performance."""
        return {
            "performance": {
                "max_recall_time_ms": 10.0,
                "max_generation_time_ms": 20.0,
                "enable_performance_monitoring": True
            },
            "recall": {
                "max_memories": 10,
                "enable_caching": True,
                "cache_size": 1000,
                "cache_ttl_seconds": 300
            },
            "extraction": {
                "enable_entity_extraction": True,
                "enable_pattern_compilation": True
            },
            "storage": {
                "connection_pool_size": 10,
                "query_timeout_ms": 1000
            }
        }
    
    @pytest.fixture
    def populated_memory(self, temp_db_path, benchmark_config):
        """Create a KuzuMemory instance with pre-populated data."""
        memory = KuzuMemory(db_path=temp_db_path, config=benchmark_config)
        
        # Populate with realistic test data
        test_contents = [
            "My name is Alice Johnson and I work at TechCorp as a Senior Python Developer.",
            "I prefer using TypeScript for frontend development and React for UI components.",
            "We decided to use PostgreSQL as our primary database with Redis for caching.",
            "Currently working on the user authentication microservice using FastAPI.",
            "My colleague Bob is handling the payment integration with Stripe API.",
            "The project deadline is next month and we're using Agile methodology.",
            "I always use pytest for testing and GitHub Actions for CI/CD.",
            "For deployment, we use Docker containers on AWS ECS.",
            "The team uses Slack for communication and Jira for project management.",
            "I'm learning Rust in my spare time and considering it for performance-critical services."
        ]
        
        for i, content in enumerate(test_contents):
            memory.generate_memories(
                content,
                user_id=f"user-{i % 3}",  # 3 different users
                session_id=f"session-{i % 5}",  # 5 different sessions
                agent_id="benchmark-agent"
            )
        
        return memory
    
    def measure_operation_times(self, operation_func, iterations: int = 100) -> Dict[str, float]:
        """Measure operation times and return statistics."""
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            operation_func()
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'p95': sorted(times)[int(0.95 * len(times))],
            'p99': sorted(times)[int(0.99 * len(times))],
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def test_attach_memories_performance_target(self, populated_memory):
        """Test that attach_memories meets <10ms performance target."""
        test_prompts = [
            "What's my name?",
            "What programming languages do I use?",
            "What database are we using?",
            "Who is working on payments?",
            "What's our deployment strategy?"
        ]
        
        def attach_operation():
            prompt = test_prompts[0]  # Use first prompt for consistency
            context = populated_memory.attach_memories(
                prompt,
                user_id="user-0",
                max_memories=5
            )
            assert len(context.memories) > 0
        
        # Measure performance
        stats = self.measure_operation_times(attach_operation, iterations=50)
        
        print(f"\nattach_memories() Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Median: {stats['median']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  P99: {stats['p99']:.2f}ms")
        print(f"  Min: {stats['min']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")
        
        # Performance assertions
        assert stats['mean'] < 10.0, f"Mean time {stats['mean']:.2f}ms exceeds 10ms target"
        assert stats['p95'] < 15.0, f"P95 time {stats['p95']:.2f}ms exceeds 15ms threshold"
        assert stats['p99'] < 25.0, f"P99 time {stats['p99']:.2f}ms exceeds 25ms threshold"
    
    def test_generate_memories_performance_target(self, temp_db_path, benchmark_config):
        """Test that generate_memories meets <20ms performance target."""
        memory = KuzuMemory(db_path=temp_db_path, config=benchmark_config)
        
        test_content = "I'm working on a new feature for the mobile app using React Native and TypeScript."
        
        def generate_operation():
            memory_ids = memory.generate_memories(
                test_content,
                user_id="benchmark-user",
                session_id="benchmark-session"
            )
            assert len(memory_ids) > 0
        
        # Measure performance
        stats = self.measure_operation_times(generate_operation, iterations=50)
        
        print(f"\ngenerate_memories() Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Median: {stats['median']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  P99: {stats['p99']:.2f}ms")
        print(f"  Min: {stats['min']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")
        
        # Performance assertions
        assert stats['mean'] < 20.0, f"Mean time {stats['mean']:.2f}ms exceeds 20ms target"
        assert stats['p95'] < 30.0, f"P95 time {stats['p95']:.2f}ms exceeds 30ms threshold"
        assert stats['p99'] < 50.0, f"P99 time {stats['p99']:.2f}ms exceeds 50ms threshold"
        
        memory.close()
    
    def test_recall_strategies_performance(self, populated_memory):
        """Compare performance of different recall strategies."""
        prompt = "What technologies are we using for the project?"
        strategies = ["auto", "keyword", "entity", "temporal"]
        
        strategy_stats = {}
        
        for strategy in strategies:
            def strategy_operation():
                context = populated_memory.attach_memories(
                    prompt,
                    strategy=strategy,
                    user_id="user-0",
                    max_memories=5
                )
                assert len(context.memories) >= 0
            
            stats = self.measure_operation_times(strategy_operation, iterations=20)
            strategy_stats[strategy] = stats
        
        print(f"\nRecall Strategy Performance Comparison:")
        for strategy, stats in strategy_stats.items():
            print(f"  {strategy:8}: {stats['mean']:6.2f}ms (±{stats['std_dev']:5.2f})")
        
        # All strategies should be reasonably fast
        for strategy, stats in strategy_stats.items():
            assert stats['mean'] < 15.0, f"{strategy} strategy too slow: {stats['mean']:.2f}ms"
    
    def test_cache_performance_impact(self, populated_memory):
        """Test the performance impact of caching."""
        prompt = "What's my name and where do I work?"
        
        # First call (cache miss)
        def first_call():
            context = populated_memory.attach_memories(prompt, user_id="user-0")
            assert len(context.memories) > 0
        
        # Subsequent calls (cache hits)
        def cached_call():
            context = populated_memory.attach_memories(prompt, user_id="user-0")
            assert len(context.memories) > 0
        
        # Measure first call
        first_stats = self.measure_operation_times(first_call, iterations=10)
        
        # Measure cached calls
        cached_stats = self.measure_operation_times(cached_call, iterations=20)
        
        print(f"\nCache Performance Impact:")
        print(f"  First call (miss): {first_stats['mean']:.2f}ms")
        print(f"  Cached call (hit): {cached_stats['mean']:.2f}ms")
        print(f"  Speedup: {first_stats['mean'] / cached_stats['mean']:.1f}x")
        
        # Cached calls should be faster
        assert cached_stats['mean'] < first_stats['mean'], "Cache should improve performance"
    
    def test_memory_count_scaling(self, temp_db_path, benchmark_config):
        """Test how performance scales with number of memories."""
        memory = KuzuMemory(db_path=temp_db_path, config=benchmark_config)
        
        memory_counts = [10, 50, 100, 200]
        performance_data = {}
        
        for count in memory_counts:
            # Populate with specified number of memories
            for i in range(count):
                memory.generate_memories(
                    f"Memory {i}: This is test content for scaling analysis with various entities like Python, React, and PostgreSQL.",
                    user_id="scale-user",
                    session_id=f"session-{i % 10}"
                )
            
            # Measure recall performance
            def recall_operation():
                context = memory.attach_memories(
                    "What technologies and tools are mentioned?",
                    user_id="scale-user",
                    max_memories=10
                )
                assert len(context.memories) > 0
            
            stats = self.measure_operation_times(recall_operation, iterations=10)
            performance_data[count] = stats['mean']
        
        print(f"\nMemory Count Scaling:")
        for count, avg_time in performance_data.items():
            print(f"  {count:3d} memories: {avg_time:6.2f}ms")
        
        # Performance should not degrade too much with more memories
        max_time = max(performance_data.values())
        min_time = min(performance_data.values())
        degradation_factor = max_time / min_time
        
        assert degradation_factor < 3.0, f"Performance degraded by {degradation_factor:.1f}x with more memories"
        
        memory.close()
    
    def test_concurrent_operations_performance(self, populated_memory):
        """Test performance under concurrent operations (simulated)."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        num_threads = 5
        operations_per_thread = 10
        
        def worker():
            times = []
            for i in range(operations_per_thread):
                start_time = time.perf_counter()
                context = populated_memory.attach_memories(
                    f"Query {i}: What are my current projects?",
                    user_id="concurrent-user",
                    max_memories=5
                )
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            
            results_queue.put(times)
        
        # Start threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Collect results
        all_times = []
        while not results_queue.empty():
            times = results_queue.get()
            all_times.extend(times)
        
        # Analyze concurrent performance
        mean_time = statistics.mean(all_times)
        p95_time = sorted(all_times)[int(0.95 * len(all_times))]
        
        print(f"\nConcurrent Operations Performance:")
        print(f"  Total operations: {len(all_times)}")
        print(f"  Mean time: {mean_time:.2f}ms")
        print(f"  P95 time: {p95_time:.2f}ms")
        
        # Performance should remain reasonable under concurrent load
        assert mean_time < 20.0, f"Concurrent mean time {mean_time:.2f}ms too high"
        assert p95_time < 40.0, f"Concurrent P95 time {p95_time:.2f}ms too high"
    
    def test_memory_cleanup_performance(self, populated_memory):
        """Test performance of memory cleanup operations."""
        def cleanup_operation():
            cleaned_count = populated_memory.cleanup_expired_memories()
            # Should complete without error
            assert cleaned_count >= 0
        
        stats = self.measure_operation_times(cleanup_operation, iterations=5)
        
        print(f"\nMemory Cleanup Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")
        
        # Cleanup should be reasonably fast
        assert stats['mean'] < 100.0, f"Cleanup too slow: {stats['mean']:.2f}ms"
    
    def teardown_method(self, method):
        """Clean up after each test method."""
        # Close any open memory instances
        pass
