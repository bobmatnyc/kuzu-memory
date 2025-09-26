# Testing Guide

**Comprehensive testing strategies for KuzuMemory development and integration**

---

## 🎯 **Testing Overview**

KuzuMemory testing is organized into multiple levels to ensure reliability, performance, and integration quality:

- **Unit Tests** - Individual component testing
- **Integration Tests** - System component integration
- **Performance Tests** - Benchmark and load testing
- **End-to-End Tests** - Complete workflow validation
- **AI Integration Tests** - Real AI system integration testing

---

## 🏗️ **Test Architecture**

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_memory_models.py
│   ├── test_kuzu_adapter.py
│   ├── test_deduplication.py
│   └── test_cli_commands.py
├── integration/             # Integration tests
│   ├── test_memory_system.py
│   ├── test_async_operations.py
│   └── test_cache_integration.py
├── benchmarks/              # Performance and benchmark tests
│   ├── test_performance.py
│   ├── test_load.py
│   └── test_scalability.py
├── e2e/                     # End-to-end workflow tests
│   ├── test_ai_workflows.py
│   └── test_cli_workflows.py
├── fixtures/                # Test data and utilities
│   ├── test_data.py
│   └── memory_fixtures.py
└── conftest.py             # pytest configuration and fixtures
```

---

## 🔧 **Setup and Configuration**

### **Installing Test Dependencies**
```bash
# Install development dependencies
pip install kuzu-memory[dev]

# Or install test-only dependencies
pip install kuzu-memory[test]

# Manual installation
pip install pytest pytest-benchmark pytest-cov pytest-mock pytest-xdist
```

### **Running Tests**

#### **Basic Test Execution**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kuzu_memory --cov-report=html

# Run specific test categories
pytest -m "not slow"           # Skip slow tests
pytest -m "integration"        # Only integration tests
pytest -m "benchmark"          # Only benchmarks

# Run parallel tests
pytest -n auto                 # Auto-detect CPU count
pytest -n 4                    # Use 4 parallel workers

# Verbose output
pytest -v --tb=short
```

#### **Test Configuration**
```bash
# Using pytest.ini or setup.cfg
pytest --strict-markers --strict-config

# With custom configuration
pytest -c custom-pytest.ini

# Environment variables
export KUZU_MEMORY_TEST_DB="/tmp/test-memories"
export KUZU_MEMORY_DEBUG=true
pytest
```

---

## 🧪 **Unit Tests**

### **Memory Model Tests**
```python
# tests/unit/test_memory_models.py
import pytest
from datetime import datetime, timedelta
from kuzu_memory.core.models import Memory, MemoryType, MemoryContext

class TestMemoryModel:
    """Test Memory data model validation and behavior."""

    def test_memory_creation(self):
        """Test basic memory creation."""
        memory = Memory(
            content="Test memory content",
            memory_type=MemoryType.EPISODIC,
            importance=0.7
        )

        assert memory.content == "Test memory content"
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.importance == 0.7
        assert memory.content_hash  # Auto-generated
        assert memory.created_at
        assert memory.id

    def test_memory_validation(self):
        """Test memory validation rules."""
        # Test empty content
        with pytest.raises(ValueError):
            Memory(content="")

        # Test importance bounds
        with pytest.raises(ValueError):
            Memory(content="test", importance=1.5)

        with pytest.raises(ValueError):
            Memory(content="test", importance=-0.1)

        # Test confidence bounds
        with pytest.raises(ValueError):
            Memory(content="test", confidence=2.0)

    def test_memory_hash_generation(self):
        """Test content hash generation."""
        memory1 = Memory(content="identical content")
        memory2 = Memory(content="identical content")
        memory3 = Memory(content="different content")

        assert memory1.content_hash == memory2.content_hash
        assert memory1.content_hash != memory3.content_hash

    def test_memory_expiration(self):
        """Test memory expiration logic."""
        # Never expiring memory
        memory_permanent = Memory(
            content="permanent",
            memory_type=MemoryType.IDENTITY
        )
        assert not memory_permanent.is_expired()

        # Expired memory
        memory_expired = Memory(
            content="expired",
            valid_to=datetime.now() - timedelta(hours=1)
        )
        assert memory_expired.is_expired()

    def test_memory_type_defaults(self):
        """Test memory type default behaviors."""
        # Test default retention periods
        decision_retention = MemoryType.get_default_retention(MemoryType.DECISION)
        assert decision_retention == timedelta(days=90)

        identity_retention = MemoryType.get_default_retention(MemoryType.IDENTITY)
        assert identity_retention is None  # Never expires

        # Test default importance
        identity_importance = MemoryType.get_default_importance(MemoryType.IDENTITY)
        assert identity_importance == 1.0

        context_importance = MemoryType.get_default_importance(MemoryType.EPISODIC)
        assert context_importance == 0.5

class TestMemoryContext:
    """Test MemoryContext for enhanced prompts."""

    def test_context_creation(self):
        """Test memory context creation."""
        memories = [
            Memory(content="Memory 1"),
            Memory(content="Memory 2")
        ]

        context = MemoryContext(
            original_prompt="Test prompt",
            enhanced_prompt="Enhanced: Test prompt\\nContext: Memory 1, Memory 2",
            memories=memories,
            metadata={"query_time_ms": 45}
        )

        assert context.original_prompt == "Test prompt"
        assert "Enhanced:" in context.enhanced_prompt
        assert len(context.memories) == 2
        assert context.metadata["query_time_ms"] == 45

    def test_context_memory_count(self):
        """Test memory count in context."""
        memories = [Memory(content=f"Memory {i}") for i in range(5)]
        context = MemoryContext(
            original_prompt="test",
            enhanced_prompt="test",
            memories=memories
        )

        assert context.memory_count == 5
        assert len(context.get_memory_summaries()) == 5

@pytest.fixture
def sample_memories():
    """Fixture providing sample memories for testing."""
    return [
        Memory(
            content="We use FastAPI for the backend",
            memory_type=MemoryType.DECISION,
            importance=0.9,
            source_type="team-meeting"
        ),
        Memory(
            content="Database connection pooling is enabled",
            memory_type=MemoryType.PATTERN,
            importance=0.7,
            source_type="code-review"
        ),
        Memory(
            content="Current deployment is on AWS ECS",
            memory_type=MemoryType.STATUS,
            importance=0.5,
            source_type="deployment-notes"
        )
    ]
```

### **Database Adapter Tests**
```python
# tests/unit/test_kuzu_adapter.py
import pytest
import tempfile
import asyncio
from pathlib import Path
from kuzu_memory.storage.kuzu_adapter import KuzuAdapter
from kuzu_memory.core.models import Memory, MemoryType

class TestKuzuAdapter:
    """Test KuzuAdapter database operations."""

    @pytest.fixture
    async def adapter(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            adapter = KuzuAdapter(db_path)
            await adapter.initialize()
            yield adapter
            await adapter.close()

    async def test_adapter_initialization(self, adapter):
        """Test database initialization."""
        assert adapter.is_initialized
        assert adapter.db_path.exists()

    async def test_store_memory(self, adapter):
        """Test storing memories."""
        memory = Memory(
            content="Test memory for database",
            memory_type=MemoryType.EPISODIC
        )

        # Store memory
        result = await adapter.store_memory(memory)
        assert result is True

        # Verify storage
        memories = await adapter.query_memories("Test memory")
        assert len(memories) == 1
        assert memories[0].content == "Test memory for database"

    async def test_query_memories(self, adapter):
        """Test querying memories."""
        # Store test memories
        memories = [
            Memory(content="Python programming tips"),
            Memory(content="JavaScript best practices"),
            Memory(content="Database optimization techniques")
        ]

        for memory in memories:
            await adapter.store_memory(memory)

        # Query by content
        python_results = await adapter.query_memories("Python")
        assert len(python_results) == 1
        assert "Python" in python_results[0].content

        # Query all
        all_results = await adapter.query_memories("")
        assert len(all_results) == 3

    async def test_memory_deduplication(self, adapter):
        """Test deduplication of identical memories."""
        memory1 = Memory(content="Identical content")
        memory2 = Memory(content="Identical content")

        # Store same content twice
        await adapter.store_memory(memory1)
        await adapter.store_memory(memory2)

        # Should only have one memory
        results = await adapter.query_memories("Identical")
        assert len(results) == 1

    async def test_memory_expiration(self, adapter):
        """Test expired memory handling."""
        from datetime import datetime, timedelta

        expired_memory = Memory(
            content="Expired memory",
            valid_to=datetime.now() - timedelta(hours=1)
        )

        valid_memory = Memory(
            content="Valid memory",
            valid_to=datetime.now() + timedelta(hours=1)
        )

        await adapter.store_memory(expired_memory)
        await adapter.store_memory(valid_memory)

        # Query should only return valid memory
        results = await adapter.query_memories("memory")
        assert len(results) == 1
        assert results[0].content == "Valid memory"

    async def test_performance_stats(self, adapter):
        """Test performance statistics collection."""
        # Generate some operations
        for i in range(10):
            memory = Memory(content=f"Performance test {i}")
            await adapter.store_memory(memory)

        for i in range(5):
            await adapter.query_memories(f"test {i}")

        # Check stats
        stats = await adapter.get_performance_stats()
        assert stats["queries_executed"] >= 5
        assert stats["memories_stored"] >= 10
        assert "avg_query_time_ms" in stats

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent database operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "concurrent_test.db"
        adapter = KuzuAdapter(db_path)
        await adapter.initialize()

        # Create memories concurrently
        async def store_memory(index):
            memory = Memory(content=f"Concurrent memory {index}")
            return await adapter.store_memory(memory)

        # Run concurrent operations
        tasks = [store_memory(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

        # Verify all memories stored
        all_memories = await adapter.query_memories("")
        assert len(all_memories) == 20

        await adapter.close()
```

### **CLI Command Tests**
```python
# tests/unit/test_cli_commands.py
import pytest
from click.testing import CliRunner
from kuzu_memory.cli.commands import cli
import tempfile
import json
from pathlib import Path

class TestCLICommands:
    """Test CLI command functionality."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self):
        """Temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_version_command(self, runner):
        """Test version command."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert "kuzu-memory" in result.output

    def test_init_command(self, runner, temp_project):
        """Test project initialization."""
        result = runner.invoke(cli, ['init'], cwd=str(temp_project))
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

        # Check database directory created
        assert (temp_project / "kuzu-memories").exists()

    def test_learn_command(self, runner, temp_project):
        """Test learn command."""
        # Initialize project
        runner.invoke(cli, ['init'], cwd=str(temp_project))

        # Learn memory
        result = runner.invoke(cli, [
            'learn', 'Test memory content',
            '--source', 'test'
        ], cwd=str(temp_project))

        assert result.exit_code == 0

    def test_enhance_command(self, runner, temp_project):
        """Test enhance command."""
        # Initialize and add memory
        runner.invoke(cli, ['init'], cwd=str(temp_project))
        runner.invoke(cli, [
            'learn', 'We use Python for backend development'
        ], cwd=str(temp_project))

        # Test enhancement
        result = runner.invoke(cli, [
            'enhance', 'How do I set up the backend?',
            '--format', 'json'
        ], cwd=str(temp_project))

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "enhanced_prompt" in data
        assert "Python" in data["enhanced_prompt"]

    def test_recall_command(self, runner, temp_project):
        """Test recall command."""
        # Initialize and add memories
        runner.invoke(cli, ['init'], cwd=str(temp_project))
        runner.invoke(cli, ['learn', 'Python backend setup guide'])
        runner.invoke(cli, ['learn', 'JavaScript frontend patterns'])

        # Test recall
        result = runner.invoke(cli, [
            'recall', 'Python',
            '--format', 'json'
        ], cwd=str(temp_project))

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["memories"]) >= 1

    def test_stats_command(self, runner, temp_project):
        """Test stats command."""
        # Initialize project
        runner.invoke(cli, ['init'], cwd=str(temp_project))

        result = runner.invoke(cli, [
            'stats', '--format', 'json'
        ], cwd=str(temp_project))

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "memory_count" in data

    def test_error_handling(self, runner):
        """Test error handling for invalid commands."""
        # Test without initialization
        result = runner.invoke(cli, ['learn', 'test'])
        assert result.exit_code != 0
        assert "not initialized" in result.output.lower()

    def test_debug_mode(self, runner, temp_project):
        """Test debug mode."""
        runner.invoke(cli, ['init'], cwd=str(temp_project))

        result = runner.invoke(cli, [
            '--debug', 'learn', 'debug test'
        ], cwd=str(temp_project))

        # Debug mode should work without errors
        assert result.exit_code == 0

@pytest.mark.parametrize("memory_type", [
    "identity", "preference", "decision", "pattern", "solution", "status", "context"
])
def test_memory_types(runner, temp_project, memory_type):
    """Test all memory types."""
    runner.invoke(cli, ['init'], cwd=str(temp_project))

    result = runner.invoke(cli, [
        'learn', f'Test {memory_type} memory',
        '--memory-type', memory_type
    ], cwd=str(temp_project))

    assert result.exit_code == 0
```

---

## 🔗 **Integration Tests**

### **Memory System Integration**
```python
# tests/integration/test_memory_system.py
import pytest
import tempfile
import asyncio
from pathlib import Path
from kuzu_memory.core.memory import KuzuMemory
from kuzu_memory.core.models import Memory, MemoryType

@pytest.mark.integration
class TestMemorySystemIntegration:
    """Test full memory system integration."""

    @pytest.fixture
    async def memory_system(self):
        """Create memory system for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "performance": {
                    "query_timeout_ms": 100,
                    "cache_size": 100
                }
            }
            system = KuzuMemory(Path(temp_dir) / "memories.db", config)
            await system.initialize()
            yield system
            await system.close()

    async def test_full_memory_workflow(self, memory_system):
        """Test complete memory workflow."""
        # 1. Generate memories from content
        memories = await memory_system.generate_memories(
            content="Our team uses FastAPI with PostgreSQL. "
                   "We deploy on AWS using Docker containers. "
                   "Authentication is handled via JWT tokens.",
            source_type="team-docs"
        )

        assert len(memories) >= 2  # Should extract multiple memories
        assert any("FastAPI" in m.content for m in memories)

        # 2. Attach memories to prompt
        context = await memory_system.attach_memories(
            prompt="How do I set up authentication in our system?",
            max_memories=3
        )

        assert context.original_prompt == "How do I set up authentication in our system?"
        assert len(context.memories) > 0
        assert any("JWT" in m.content for m in context.memories)
        assert "authentication" in context.enhanced_prompt.lower()

        # 3. Query memories directly
        auth_memories = await memory_system.query_memories("authentication")
        assert len(auth_memories) > 0

    async def test_memory_deduplication(self, memory_system):
        """Test memory deduplication across multiple sources."""
        # Add same content from different sources
        await memory_system.generate_memories(
            "We use PostgreSQL database",
            source_type="docs"
        )

        await memory_system.generate_memories(
            "We use PostgreSQL database",
            source_type="meeting-notes"
        )

        # Should only have one memory
        postgres_memories = await memory_system.query_memories("PostgreSQL")
        assert len(postgres_memories) == 1

    async def test_performance_targets(self, memory_system):
        """Test performance targets."""
        # Add test data
        for i in range(50):
            await memory_system.generate_memories(
                f"Performance test memory {i} with various content",
                source_type="perf-test"
            )

        # Test attach_memories performance
        start_time = asyncio.get_event_loop().time()
        await memory_system.attach_memories("performance test")
        attach_time = (asyncio.get_event_loop().time() - start_time) * 1000

        # Should be under 100ms
        assert attach_time < 100, f"attach_memories took {attach_time}ms"

        # Test query performance
        start_time = asyncio.get_event_loop().time()
        await memory_system.query_memories("test")
        query_time = (asyncio.get_event_loop().time() - start_time) * 1000

        # Should be under 50ms
        assert query_time < 50, f"query_memories took {query_time}ms"

    async def test_concurrent_access(self, memory_system):
        """Test concurrent memory operations."""
        async def generate_and_query(index):
            # Generate memory
            await memory_system.generate_memories(
                f"Concurrent test {index}",
                source_type=f"worker-{index}"
            )

            # Query memories
            results = await memory_system.query_memories(f"test {index}")
            return len(results)

        # Run concurrent operations
        tasks = [generate_and_query(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r >= 0 for r in results)
```

### **Async Operations Integration**
```python
# tests/integration/test_async_operations.py
import pytest
import asyncio
from kuzu_memory.async_memory.system import AsyncMemorySystem
from kuzu_memory.async_memory.queue import TaskQueue

@pytest.mark.integration
class TestAsyncOperations:
    """Test async memory operations."""

    @pytest.fixture
    async def async_system(self):
        """Async memory system fixture."""
        system = AsyncMemorySystem()
        await system.start()
        yield system
        await system.stop()

    async def test_queue_learning(self, async_system):
        """Test queuing learning operations."""
        # Queue multiple learning tasks
        tasks = []
        for i in range(10):
            task_id = await async_system.queue_learning(
                content=f"Async learning test {i}",
                source_type="async-test"
            )
            tasks.append(task_id)

        # Wait for processing
        await asyncio.sleep(2)

        # Check task status
        for task_id in tasks:
            status = await async_system.get_task_status(task_id)
            assert status.status == "completed"

    async def test_background_processing(self, async_system):
        """Test background task processing."""
        # Queue learning task
        task_id = await async_system.queue_learning(
            "Background processing test",
            priority="high"
        )

        # Should be processed quickly due to high priority
        for _ in range(50):  # Wait up to 5 seconds
            status = await async_system.get_task_status(task_id)
            if status.status == "completed":
                break
            await asyncio.sleep(0.1)

        assert status.status == "completed"
        assert status.execution_time_ms > 0

    async def test_queue_overflow(self, async_system):
        """Test queue overflow handling."""
        # Fill queue beyond capacity
        tasks = []
        for i in range(1000):  # More than typical queue size
            try:
                task_id = await async_system.queue_learning(
                    f"Overflow test {i}",
                    priority="low"
                )
                tasks.append(task_id)
            except Exception as e:
                # Should handle overflow gracefully
                assert "queue full" in str(e).lower()
                break

        # Some tasks should still complete
        assert len(tasks) > 0
```

---

## ⚡ **Performance Tests**

### **Benchmark Tests**
```python
# tests/benchmarks/test_performance.py
import pytest
import asyncio
import tempfile
from pathlib import Path
from kuzu_memory.core.memory import KuzuMemory

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.fixture
    async def memory_system(self):
        """Memory system for benchmarking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = KuzuMemory(Path(temp_dir) / "bench.db")
            await system.initialize()

            # Pre-populate with test data
            for i in range(100):
                await system.generate_memories(
                    f"Benchmark memory {i} with content about "
                    f"{'Python' if i % 3 == 0 else 'JavaScript' if i % 3 == 1 else 'Go'} "
                    f"programming and development practices",
                    source_type="benchmark"
                )

            yield system
            await system.close()

    def test_query_performance(self, benchmark, memory_system):
        """Benchmark query performance."""
        async def query_operation():
            return await memory_system.query_memories("Python programming")

        result = benchmark(asyncio.run, query_operation())
        assert len(result) > 0

    def test_enhance_performance(self, benchmark, memory_system):
        """Benchmark prompt enhancement."""
        async def enhance_operation():
            return await memory_system.attach_memories(
                "How do I optimize Python code?",
                max_memories=5
            )

        result = benchmark(asyncio.run, enhance_operation())
        assert result.memory_count > 0

    def test_memory_generation_performance(self, benchmark, memory_system):
        """Benchmark memory generation."""
        async def generation_operation():
            return await memory_system.generate_memories(
                "This is a test content for memory generation performance "
                "testing with various entities and patterns to extract.",
                source_type="perf-test"
            )

        result = benchmark(asyncio.run, generation_operation())
        assert len(result) > 0

    @pytest.mark.parametrize("memory_count", [10, 50, 100, 500])
    def test_scalability(self, benchmark, memory_count):
        """Test performance scaling with memory count."""
        async def scalability_test():
            with tempfile.TemporaryDirectory() as temp_dir:
                system = KuzuMemory(Path(temp_dir) / "scale.db")
                await system.initialize()

                # Add memories
                for i in range(memory_count):
                    await system.generate_memories(
                        f"Scalability test memory {i}",
                        source_type="scale-test"
                    )

                # Test query performance
                start_time = asyncio.get_event_loop().time()
                results = await system.query_memories("scalability test")
                query_time = (asyncio.get_event_loop().time() - start_time) * 1000

                await system.close()
                return query_time

        query_time = benchmark(asyncio.run, scalability_test())

        # Performance should scale sub-linearly
        expected_max_time = min(100, memory_count * 0.5)  # Max 100ms
        assert query_time < expected_max_time, \
            f"Query took {query_time}ms for {memory_count} memories"

class TestCLIPerformance:
    """CLI performance benchmarks."""

    @pytest.fixture
    def temp_project(self):
        """Temporary project with pre-populated data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Initialize project
            import subprocess
            subprocess.run(['kuzu-memory', 'init'], cwd=project_path, check=True)

            # Add test data
            for i in range(20):
                subprocess.run([
                    'kuzu-memory', 'learn',
                    f'CLI performance test memory {i} with various content',
                    '--source', 'cli-perf'
                ], cwd=project_path)

            yield project_path

    def test_cli_enhance_performance(self, benchmark, temp_project):
        """Benchmark CLI enhance command."""
        import subprocess

        def cli_enhance():
            result = subprocess.run([
                'kuzu-memory', 'enhance',
                'How do I optimize performance?',
                '--format', 'json'
            ], cwd=temp_project, capture_output=True, text=True)
            return result.returncode == 0

        success = benchmark(cli_enhance)
        assert success

    def test_cli_learn_performance(self, benchmark, temp_project):
        """Benchmark CLI learn command."""
        import subprocess

        def cli_learn():
            result = subprocess.run([
                'kuzu-memory', 'learn',
                'CLI performance test learning operation',
                '--source', 'perf-test'
            ], cwd=temp_project, capture_output=True)
            return result.returncode == 0

        success = benchmark(cli_learn)
        assert success
```

### **Load Tests**
```python
# tests/benchmarks/test_load.py
import pytest
import asyncio
import concurrent.futures
from pathlib import Path
import tempfile
from kuzu_memory.core.memory import KuzuMemory

@pytest.mark.slow
class TestLoadTests:
    """Load testing for high-throughput scenarios."""

    async def test_concurrent_queries(self):
        """Test concurrent query load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = KuzuMemory(Path(temp_dir) / "load.db")
            await system.initialize()

            # Pre-populate data
            for i in range(200):
                await system.generate_memories(
                    f"Load test memory {i} about various topics",
                    source_type="load-test"
                )

            # Define concurrent query function
            async def query_worker(worker_id):
                results = []
                for i in range(10):
                    start_time = asyncio.get_event_loop().time()
                    memories = await system.query_memories(f"test {i}")
                    query_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    results.append({
                        'worker_id': worker_id,
                        'query_time_ms': query_time,
                        'results_count': len(memories)
                    })
                return results

            # Run concurrent workers
            tasks = [query_worker(i) for i in range(20)]
            all_results = await asyncio.gather(*tasks)

            # Analyze results
            flat_results = [r for worker_results in all_results for r in worker_results]
            avg_query_time = sum(r['query_time_ms'] for r in flat_results) / len(flat_results)
            max_query_time = max(r['query_time_ms'] for r in flat_results)

            print(f"Average query time: {avg_query_time:.1f}ms")
            print(f"Maximum query time: {max_query_time:.1f}ms")
            print(f"Total queries: {len(flat_results)}")

            # Performance assertions
            assert avg_query_time < 100, f"Average query time too high: {avg_query_time}ms"
            assert max_query_time < 200, f"Maximum query time too high: {max_query_time}ms"

            await system.close()

    async def test_memory_generation_load(self):
        """Test memory generation under load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system = KuzuMemory(Path(temp_dir) / "gen_load.db")
            await system.initialize()

            async def generation_worker(worker_id):
                for i in range(20):
                    await system.generate_memories(
                        f"Worker {worker_id} generating memory {i} with "
                        f"various content and entities for extraction testing",
                        source_type=f"worker-{worker_id}"
                    )
                return worker_id

            # Run concurrent generation
            start_time = asyncio.get_event_loop().time()
            workers = [generation_worker(i) for i in range(10)]
            await asyncio.gather(*workers)
            total_time = asyncio.get_event_loop().time() - start_time

            print(f"Generated 200 memories in {total_time:.2f}s")
            print(f"Rate: {200 / total_time:.1f} memories/second")

            # Verify all memories stored
            all_memories = await system.query_memories("")
            assert len(all_memories) >= 200

            await system.close()

    def test_cli_load_testing(self):
        """Test CLI under concurrent load."""
        import subprocess
        import threading
        import time
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Initialize project
            subprocess.run(['kuzu-memory', 'init'], cwd=project_path, check=True)

            # Pre-populate
            for i in range(50):
                subprocess.run([
                    'kuzu-memory', 'learn',
                    f'CLI load test memory {i}',
                ], cwd=project_path)

            # Concurrent CLI operations
            results = []

            def cli_worker(worker_id):
                worker_results = []
                for i in range(5):
                    start = time.time()
                    result = subprocess.run([
                        'kuzu-memory', 'enhance',
                        f'Worker {worker_id} query {i}',
                        '--format', 'json'
                    ], cwd=project_path, capture_output=True)

                    execution_time = (time.time() - start) * 1000
                    worker_results.append({
                        'worker_id': worker_id,
                        'success': result.returncode == 0,
                        'time_ms': execution_time
                    })

                return worker_results

            # Run concurrent workers
            threads = []
            for i in range(10):
                thread = threading.Thread(target=lambda w=i: results.extend(cli_worker(w)))
                threads.append(thread)
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

            # Analyze results
            successful = [r for r in results if r['success']]
            avg_time = sum(r['time_ms'] for r in successful) / len(successful)

            print(f"CLI Load Test Results:")
            print(f"Success rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
            print(f"Average time: {avg_time:.1f}ms")

            assert len(successful) >= len(results) * 0.95  # 95% success rate
            assert avg_time < 200  # Average under 200ms
```

---

## 🔄 **End-to-End Tests**

### **AI Workflow Tests**
```python
# tests/e2e/test_ai_workflows.py
import pytest
import subprocess
import tempfile
import json
from pathlib import Path

@pytest.mark.e2e
class TestAIWorkflows:
    """End-to-end AI integration workflows."""

    @pytest.fixture
    def project_setup(self):
        """Set up project with realistic AI data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Initialize project
            subprocess.run(['kuzu-memory', 'init'], cwd=project_path, check=True)

            # Add realistic project context
            project_memories = [
                "This project uses FastAPI with PostgreSQL database",
                "Authentication is handled via JWT tokens stored in Redis",
                "We deploy using Docker containers on AWS ECS",
                "Frontend is React with TypeScript",
                "API documentation is generated with OpenAPI/Swagger",
                "We use pytest for testing and black for code formatting",
                "Error handling follows RFC 7807 problem details standard"
            ]

            for memory in project_memories:
                subprocess.run([
                    'kuzu-memory', 'learn', memory,
                    '--memory-type', 'decision',
                    '--source', 'project-setup'
                ], cwd=project_path)

            yield project_path

    def test_complete_ai_chat_workflow(self, project_setup):
        """Test complete AI chat workflow."""
        # Simulate AI chat workflow
        user_queries = [
            "How do I set up authentication?",
            "What's our deployment process?",
            "How should I structure API endpoints?",
            "What testing framework do we use?"
        ]

        for query in user_queries:
            # Step 1: Enhance prompt with context
            enhance_result = subprocess.run([
                'kuzu-memory', 'enhance', query, '--format', 'json'
            ], cwd=project_setup, capture_output=True, text=True)

            assert enhance_result.returncode == 0
            enhance_data = json.loads(enhance_result.stdout)

            # Should have enhanced prompt with context
            assert len(enhance_data['memories_used']) > 0
            assert enhance_data['enhanced_prompt'] != query

            # Step 2: Simulate AI response (in real scenario, this goes to AI)
            enhanced_prompt = enhance_data['enhanced_prompt']
            simulated_ai_response = f"Based on the context: {enhanced_prompt[:100]}..."

            # Step 3: Store the interaction for learning
            interaction = f"Q: {query}\\nA: {simulated_ai_response}"
            learn_result = subprocess.run([
                'kuzu-memory', 'learn', interaction,
                '--source', 'ai-chat',
                '--memory-type', 'context'
            ], cwd=project_setup)

            assert learn_result.returncode == 0

        # Verify learning worked - later queries should have more context
        final_query = "Tell me about our tech stack"
        final_result = subprocess.run([
            'kuzu-memory', 'enhance', final_query, '--format', 'json'
        ], cwd=project_setup, capture_output=True, text=True)

        final_data = json.loads(final_result.stdout)
        # Should have multiple memories from both setup and chat history
        assert len(final_data['memories_used']) >= 3

    def test_project_onboarding_workflow(self, project_setup):
        """Test new developer onboarding workflow."""
        # Common onboarding questions
        onboarding_questions = [
            "What's the project structure?",
            "How do I run tests?",
            "What's our coding style?",
            "How do I deploy changes?",
            "Where is the API documentation?"
        ]

        responses = []
        for question in onboarding_questions:
            result = subprocess.run([
                'kuzu-memory', 'enhance', question, '--format', 'json'
            ], cwd=project_setup, capture_output=True, text=True)

            assert result.returncode == 0
            data = json.loads(result.stdout)
            responses.append({
                'question': question,
                'memories_count': len(data['memories_used']),
                'has_context': len(data['memories_used']) > 0
            })

        # All questions should get relevant context
        context_rate = sum(1 for r in responses if r['has_context']) / len(responses)
        assert context_rate >= 0.8  # At least 80% should have context

        print("Onboarding Question Results:")
        for response in responses:
            print(f"  {response['question']}: {response['memories_count']} memories")

    def test_code_review_workflow(self, project_setup):
        """Test code review assistance workflow."""
        # Store code review patterns
        review_patterns = [
            "Always check for proper error handling in API endpoints",
            "Ensure database queries use proper connection pooling",
            "API responses should follow our standard format",
            "Include unit tests for new functions",
            "Use type hints for better code documentation"
        ]

        for pattern in review_patterns:
            subprocess.run([
                'kuzu-memory', 'learn', pattern,
                '--memory-type', 'pattern',
                '--source', 'code-review-guide'
            ], cwd=project_setup)

        # Simulate code review question
        review_query = "What should I check when reviewing an API endpoint?"
        result = subprocess.run([
            'kuzu-memory', 'enhance', review_query, '--format', 'json'
        ], cwd=project_setup, capture_output=True, text=True)

        assert result.returncode == 0
        data = json.loads(result.stdout)

        # Should get relevant review patterns
        assert len(data['memories_used']) >= 3
        enhanced_text = data['enhanced_prompt'].lower()
        assert any(word in enhanced_text for word in ['error', 'test', 'format', 'type'])

class TestCLIWorkflows:
    """Test complete CLI workflows."""

    def test_project_lifecycle_workflow(self):
        """Test complete project lifecycle with CLI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # 1. Initialize new project
            init_result = subprocess.run([
                'kuzu-memory', 'init'
            ], cwd=project_path)
            assert init_result.returncode == 0

            # 2. Add project documentation
            subprocess.run([
                'kuzu-memory', 'remember',
                'Project uses microservices architecture with Docker'
            ], cwd=project_path)

            # 3. Add team decisions
            subprocess.run([
                'kuzu-memory', 'learn',
                'Team decided to use GraphQL for new APIs',
                '--memory-type', 'decision',
                '--source', 'team-meeting'
            ], cwd=project_path)

            # 4. Query project status
            stats_result = subprocess.run([
                'kuzu-memory', 'stats', '--format', 'json'
            ], cwd=project_path, capture_output=True, text=True)

            assert stats_result.returncode == 0
            stats = json.loads(stats_result.stdout)
            assert stats['memory_count'] >= 2

            # 5. Test project context
            context_result = subprocess.run([
                'kuzu-memory', 'enhance',
                'How should I design the new user service?',
                '--format', 'json'
            ], cwd=project_path, capture_output=True, text=True)

            assert context_result.returncode == 0
            context_data = json.loads(context_result.stdout)
            assert len(context_data['memories_used']) > 0

            # 6. Cleanup old memories
            cleanup_result = subprocess.run([
                'kuzu-memory', 'cleanup', '--dry-run'
            ], cwd=project_path)
            assert cleanup_result.returncode == 0

    def test_team_collaboration_workflow(self):
        """Test team collaboration scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Initialize project
            subprocess.run(['kuzu-memory', 'init'], cwd=project_path)

            # Simulate different team members adding knowledge
            team_contributions = [
                ("alice", "Database schema uses UUID primary keys", "decision"),
                ("bob", "Use dependency injection for better testing", "pattern"),
                ("carol", "API rate limiting is 1000 requests per hour", "configuration"),
                ("dave", "Deployment pipeline runs on GitHub Actions", "process")
            ]

            for author, content, mem_type in team_contributions:
                subprocess.run([
                    'kuzu-memory', 'learn', content,
                    '--source', f'team-member-{author}',
                    '--memory-type', mem_type if mem_type != 'configuration' else 'decision'
                ], cwd=project_path)

            # New team member queries
            new_member_queries = [
                "What's our database setup?",
                "How do we handle testing?",
                "What are the API limits?",
                "How is deployment handled?"
            ]

            successful_queries = 0
            for query in new_member_queries:
                result = subprocess.run([
                    'kuzu-memory', 'enhance', query, '--format', 'json'
                ], cwd=project_path, capture_output=True, text=True)

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if len(data['memories_used']) > 0:
                        successful_queries += 1

            # Most queries should find relevant context
            success_rate = successful_queries / len(new_member_queries)
            assert success_rate >= 0.75  # At least 75% success rate
```

---

## 🔍 **Testing Best Practices**

### **Test Organization**
1. **Separate concerns**: Unit, integration, performance, and E2E tests
2. **Use fixtures**: Reusable test setup and teardown
3. **Parametrize tests**: Test multiple scenarios efficiently
4. **Mark slow tests**: Use `@pytest.mark.slow` for long-running tests
5. **Mock external dependencies**: Use `pytest-mock` for isolation

### **Performance Testing**
```python
# Performance test template
@pytest.mark.benchmark
def test_operation_performance(benchmark):
    """Benchmark template."""
    def operation():
        # Your operation here
        return result

    result = benchmark(operation)

    # Assert performance targets
    assert benchmark.stats.stats.mean < 0.1  # 100ms
    assert result is not None

# Load test template
@pytest.mark.slow
async def test_concurrent_load():
    """Concurrent load test template."""
    async def worker(worker_id):
        # Worker operations
        return results

    # Run workers concurrently
    tasks = [worker(i) for i in range(num_workers)]
    results = await asyncio.gather(*tasks)

    # Analyze results
    assert all(results)
```

### **CI/CD Integration**
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -e .[dev]

    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov

    - name: Run integration tests
      run: |
        pytest tests/integration -v

    - name: Run performance tests
      run: |
        pytest tests/benchmarks -v --benchmark-only

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## 🛠️ **Testing Tools & Utilities**

### **Custom Test Fixtures**
```python
# tests/conftest.py
import pytest
import tempfile
import asyncio
from pathlib import Path
from kuzu_memory.core.memory import KuzuMemory

@pytest.fixture
def temp_memory_db():
    """Temporary memory database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir) / "test.db"

@pytest.fixture
async def memory_system(temp_memory_db):
    """Async memory system fixture."""
    system = KuzuMemory(temp_memory_db)
    await system.initialize()
    yield system
    await system.close()

@pytest.fixture
def sample_memories():
    """Sample memories for testing."""
    from kuzu_memory.core.models import Memory, MemoryType
    return [
        Memory(content="Python is great for AI", memory_type=MemoryType.PATTERN),
        Memory(content="Use async/await for I/O", memory_type=MemoryType.DECISION),
        Memory(content="FastAPI for web APIs", memory_type=MemoryType.SOLUTION)
    ]

@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

### **Test Data Generators**
```python
# tests/fixtures/test_data.py
import random
from faker import Faker
from kuzu_memory.core.models import Memory, MemoryType

fake = Faker()

def generate_test_memories(count: int = 10):
    """Generate test memories with realistic content."""
    memories = []
    memory_types = list(MemoryType)
    topics = ['python', 'javascript', 'docker', 'api', 'database', 'testing']

    for i in range(count):
        topic = random.choice(topics)
        content = f"{fake.sentence()} about {topic} {fake.text(max_nb_chars=100)}"

        memory = Memory(
            content=content,
            memory_type=random.choice(memory_types),
            importance=random.uniform(0.1, 1.0),
            confidence=random.uniform(0.7, 1.0),
            source_type=f"test-{fake.word()}"
        )
        memories.append(memory)

    return memories

def generate_project_scenario():
    """Generate realistic project scenario data."""
    return {
        'tech_stack': [
            "We use Python 3.11 with FastAPI framework",
            "PostgreSQL is our primary database",
            "Redis for caching and session storage",
            "Docker containers for deployment"
        ],
        'decisions': [
            "Authentication uses JWT tokens",
            "API follows REST principles with OpenAPI docs",
            "We use pytest for testing",
            "Black and isort for code formatting"
        ],
        'patterns': [
            "Use dependency injection for database connections",
            "Async/await for all I/O operations",
            "Proper error handling with custom exceptions",
            "Logging with structured JSON format"
        ]
    }
```

### **Performance Monitoring**
```python
# tests/utils/performance_monitor.py
import time
import psutil
import asyncio
from contextlib import asynccontextmanager

class PerformanceMonitor:
    """Monitor test performance and resource usage."""

    def __init__(self):
        self.metrics = {}

    @asynccontextmanager
    async def monitor_operation(self, operation_name: str):
        """Monitor operation performance."""
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_time = time.time()

        try:
            yield
        finally:
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024  # MB

            self.metrics[operation_name] = {
                'execution_time_ms': (end_time - start_time) * 1000,
                'memory_usage_mb': end_memory - start_memory,
                'peak_memory_mb': end_memory
            }

    def get_summary(self):
        """Get performance summary."""
        return {
            'operations': len(self.metrics),
            'total_time_ms': sum(m['execution_time_ms'] for m in self.metrics.values()),
            'avg_time_ms': sum(m['execution_time_ms'] for m in self.metrics.values()) / len(self.metrics),
            'max_memory_mb': max(m['peak_memory_mb'] for m in self.metrics.values()),
            'details': self.metrics
        }

# Usage in tests
@pytest.fixture
def performance_monitor():
    return PerformanceMonitor()

async def test_with_monitoring(memory_system, performance_monitor):
    async with performance_monitor.monitor_operation("memory_query"):
        await memory_system.query_memories("test")

    summary = performance_monitor.get_summary()
    assert summary['avg_time_ms'] < 100
```

---

## 📊 **Test Reports & Coverage**

### **Coverage Configuration**
```ini
# .coveragerc
[run]
source = src/kuzu_memory
omit =
    */tests/*
    */test_*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    @abstract

[html]
directory = htmlcov
```

### **Test Reports**
```bash
# Generate comprehensive test reports
pytest --cov=kuzu_memory --cov-report=html --cov-report=xml --cov-report=term

# Performance benchmark reports
pytest tests/benchmarks --benchmark-only --benchmark-html=benchmark-report.html

# Generate test documentation
pytest --collect-only --quiet | grep "test_" > test-inventory.txt
```

---

## 🎯 **Quality Gates**

### **Minimum Test Requirements**
- **Unit Test Coverage**: >90%
- **Integration Test Coverage**: >80%
- **Performance Tests**: All operations under target times
- **CLI Tests**: All commands tested with success/failure scenarios
- **E2E Tests**: Core workflows validated

### **Performance Targets**
- `enhance` operations: <100ms average
- `learn` operations: <200ms average
- Database queries: <10ms average
- CLI commands: <50ms startup time
- Memory usage: <100MB for typical workloads

### **Test Automation**
```bash
# Pre-commit hook
#!/bin/sh
pytest tests/unit tests/integration -x --tb=short
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

**Comprehensive testing strategy for KuzuMemory development!** 🧪✅