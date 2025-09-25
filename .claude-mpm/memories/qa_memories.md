# QA Memory - KuzuMemory Testing Strategies

## Testing Philosophy
- **Performance-driven testing**: Every test validates speed targets
- **Integration-first**: Test real-world AI usage patterns
- **Failure scenario coverage**: Test graceful degradation
- **Data integrity focus**: Ensure memory consistency
- **CLI-centric**: Test subprocess integration patterns

## Test Architecture

### Test Suite Structure
```
tests/
├── unit/              # Fast, isolated component tests
│   ├── test_models.py           # Pydantic model validation
│   ├── test_memory.py           # Core KuzuMemory operations
│   ├── test_deduplication.py    # Content hash deduplication
│   ├── test_entity_extraction.py # NER without external deps
│   └── test_pattern_extraction.py # Pattern matching logic
├── integration/       # Cross-component realistic scenarios
│   ├── test_kuzu_memory.py      # Full system integration
│   ├── test_auggie_integration.py # AI system integration
│   └── test_cli_integration.py   # CLI subprocess testing
├── e2e/              # End-to-end user workflows
│   └── test_complete_workflows.py # Full user scenarios
├── benchmarks/       # Performance validation
│   └── test_performance.py      # Speed and memory tests
└── regression/       # Data consistency and perf tracking
    ├── test_data_integrity.py   # Database consistency
    └── test_performance_regression.py # Performance tracking
```

## Performance Testing Strategies

### Speed Validation Tests
```python
@pytest.mark.benchmark
def test_recall_speed_target():
    """Validate <100ms recall performance"""
    with KuzuMemory() as memory:
        # Setup test data
        memory.generate_memories("Test content for recall")

        # Benchmark recall operation
        start = time.time()
        result = memory.attach_memories("test query", max_memories=10)
        duration_ms = (time.time() - start) * 1000

        # Assert performance target
        assert duration_ms < 100.0, f"Recall took {duration_ms:.1f}ms, target <100ms"
        assert len(result.memories) > 0, "Should find relevant memories"

@pytest.mark.benchmark
def test_generation_speed_target():
    """Validate <200ms generation performance"""
    with KuzuMemory() as memory:
        start = time.time()
        memory_ids = memory.generate_memories("Test memory generation content")
        duration_ms = (time.time() - start) * 1000

        assert duration_ms < 200.0, f"Generation took {duration_ms:.1f}ms, target <200ms"
        assert len(memory_ids) > 0, "Should generate memories"
```

### CLI Performance Tests
```python
def test_cli_subprocess_performance():
    """Test AI integration pattern performance"""
    # Test enhance command (synchronous, must be fast)
    start = time.time()
    result = subprocess.run([
        'kuzu-memory', 'enhance', 'test prompt', '--format', 'plain'
    ], capture_output=True, text=True, timeout=5)
    duration = time.time() - start

    assert result.returncode == 0, "CLI command should succeed"
    assert duration < 0.15, f"CLI enhance took {duration:.3f}s, target <150ms"

    # Test learn command (async, should be very fast to queue)
    start = time.time()
    result = subprocess.run([
        'kuzu-memory', 'learn', 'test learning', '--quiet'
    ], check=False, timeout=5)
    duration = time.time() - start

    # Learn should queue quickly and return
    assert duration < 0.05, f"CLI learn took {duration:.3f}s, target <50ms"
```

## Data Integrity Testing

### Memory Deduplication Tests
```python
def test_content_deduplication():
    """Ensure identical content creates single memory"""
    with KuzuMemory() as memory:
        content = "Test duplicate content"

        # Store same content twice
        ids1 = memory.generate_memories(content)
        ids2 = memory.generate_memories(content)

        # Should deduplicate (same hash)
        all_memories = memory.attach_memories("test", max_memories=100)
        content_memories = [m for m in all_memories.memories if m.content == content]

        assert len(content_memories) == 1, "Should deduplicate identical content"

def test_memory_expiration():
    """Test automatic memory expiration"""
    with KuzuMemory() as memory:
        # Create short-lived memory
        from datetime import datetime, timedelta

        short_memory = Memory(
            content="Short lived memory",
            memory_type=MemoryType.STATUS,  # 6 hour expiration
            valid_to=datetime.now() - timedelta(hours=1)  # Already expired
        )

        # Manual storage for testing
        memory.memory_store.store_memory(short_memory)

        # Should not appear in recalls
        result = memory.attach_memories("short lived")
        expired_memories = [m for m in result.memories if "short lived" in m.content.lower()]

        assert len(expired_memories) == 0, "Expired memories should not be recalled"
```

### Database Consistency Tests
```python
def test_database_schema_integrity():
    """Validate database schema after operations"""
    with KuzuMemory() as memory:
        # Perform various operations
        memory.generate_memories("Test schema integrity")
        memory.attach_memories("test query")

        # Check schema consistency
        stats = memory.get_statistics()
        db_stats = stats['storage_stats']['database_stats']

        assert db_stats['memory_count'] >= 0, "Memory count should be non-negative"
        assert db_stats['entity_count'] >= 0, "Entity count should be non-negative"

        # Verify relationships are consistent
        # (Kuzu should maintain referential integrity)
```

## AI Integration Testing

### Subprocess Integration Tests
```python
class TestAIIntegrationPatterns:
    """Test real-world AI integration patterns"""

    def test_enhance_fallback_behavior(self):
        """Test graceful degradation when enhancement fails"""
        original_prompt = "Test prompt for AI"

        # Should fallback to original if CLI fails
        try:
            result = subprocess.run([
                'nonexistent-command', 'enhance', original_prompt
            ], capture_output=True, text=True, timeout=1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Expected failure - should fallback to original
            fallback_prompt = original_prompt

        assert fallback_prompt == original_prompt, "Should fallback gracefully"

    def test_learn_fire_and_forget(self):
        """Test async learning doesn't block"""
        start = time.time()

        # Learning should return immediately (fire and forget)
        result = subprocess.run([
            'kuzu-memory', 'learn', 'Async learning test', '--quiet'
        ], check=False)  # Don't check return code

        duration = time.time() - start

        # Should return very quickly (just queue the task)
        assert duration < 0.1, f"Async learn took {duration:.3f}s, should be <100ms"

def test_integration_error_handling():
    """Test error handling in AI integration scenarios"""
    # Test timeout handling
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run([
            'kuzu-memory', 'enhance', 'test'
        ], timeout=0.001)  # Intentionally short timeout

    # Test invalid arguments
    result = subprocess.run([
        'kuzu-memory', 'enhance'  # Missing required argument
    ], capture_output=True)

    assert result.returncode != 0, "Should fail with missing arguments"
    assert len(result.stderr) > 0, "Should provide error message"
```

## Memory System Testing

### Memory Type Behavior Tests
```python
def test_memory_type_retention_policies():
    """Test each memory type has correct retention"""
    test_cases = [
        (MemoryType.IDENTITY, None, "Should never expire"),
        (MemoryType.PREFERENCE, None, "Should never expire"),
        (MemoryType.DECISION, timedelta(days=90), "Should expire in 90 days"),
        (MemoryType.STATUS, timedelta(hours=6), "Should expire in 6 hours"),
    ]

    for memory_type, expected_retention, description in test_cases:
        retention = MemoryType.get_default_retention(memory_type)
        assert retention == expected_retention, f"{memory_type}: {description}"

def test_memory_importance_scoring():
    """Test importance scores are set correctly by type"""
    high_importance_types = [MemoryType.IDENTITY, MemoryType.PREFERENCE, MemoryType.DECISION]

    for memory_type in high_importance_types:
        importance = MemoryType.get_default_importance(memory_type)
        assert importance >= 0.9, f"{memory_type} should have high importance (>= 0.9)"

    low_importance = MemoryType.get_default_importance(MemoryType.STATUS)
    assert low_importance <= 0.5, "STATUS memories should have low importance"
```

## Stress Testing

### Scalability Tests
```python
@pytest.mark.slow
def test_large_memory_set_performance():
    """Test performance with large number of memories"""
    with KuzuMemory() as memory:
        # Generate many memories
        for i in range(1000):
            memory.generate_memories(f"Test memory {i} with content")

        # Test recall performance doesn't degrade
        start = time.time()
        result = memory.attach_memories("test", max_memories=10)
        duration_ms = (time.time() - start) * 1000

        assert duration_ms < 150.0, f"Large set recall took {duration_ms:.1f}ms, target <150ms"
        assert len(result.memories) > 0, "Should find memories in large set"

@pytest.mark.slow
def test_concurrent_access():
    """Test thread safety of memory operations"""
    import threading

    def worker_function(memory_instance, worker_id):
        # Each worker performs memory operations
        memory_instance.generate_memories(f"Worker {worker_id} content")
        memory_instance.attach_memories(f"worker {worker_id}")

    with KuzuMemory() as memory:
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_function, args=(memory, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)
            assert not thread.is_alive(), "Thread should complete within timeout"
```

## Test Data Management

### Test Fixtures
```python
@pytest.fixture
def sample_memories():
    """Standard test memory set"""
    return [
        Memory(content="I prefer Python for backend development",
               memory_type=MemoryType.PREFERENCE),
        Memory(content="We decided to use PostgreSQL for the user database",
               memory_type=MemoryType.DECISION),
        Memory(content="My name is Alex and I work at TechCorp",
               memory_type=MemoryType.IDENTITY),
    ]

@pytest.fixture
def temp_memory_db():
    """Temporary database for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        yield db_path

@pytest.fixture
def memory_instance(temp_memory_db):
    """Configured memory instance for testing"""
    config = KuzuMemoryConfig()
    config.performance.max_recall_time_ms = 100.0
    config.performance.max_generation_time_ms = 200.0

    with KuzuMemory(db_path=temp_memory_db, config=config) as memory:
        yield memory
```

## Regression Testing Strategy

### Performance Regression Detection
```python
def test_performance_regression():
    """Track performance metrics over time"""
    benchmarks_file = "benchmarks/performance_history.json"

    with KuzuMemory() as memory:
        # Run standard benchmark
        start = time.time()
        result = memory.attach_memories("standard benchmark query")
        current_time = (time.time() - start) * 1000

        # Compare with historical data
        if Path(benchmarks_file).exists():
            with open(benchmarks_file) as f:
                history = json.load(f)

            baseline = history.get('recall_time_ms', 100.0)
            regression_threshold = baseline * 1.2  # 20% regression threshold

            assert current_time < regression_threshold, \
                f"Performance regression: {current_time:.1f}ms vs baseline {baseline:.1f}ms"
```

## Quality Metrics Targets

### Coverage Requirements
- **Core Memory Engine**: >95% line coverage
- **CLI Commands**: >90% line coverage
- **Storage Layer**: >95% line coverage
- **AI Integration**: >85% line coverage
- **Overall Project**: >90% line coverage

### Performance Benchmarks
- **Memory Recall**: <100ms (99th percentile)
- **Memory Generation**: <200ms (99th percentile)
- **CLI Startup**: <50ms (cold start)
- **Database Operations**: <10ms per query
- **Memory Usage**: <100MB for 10k memories

### Test Execution Targets
- **Unit Tests**: <30 seconds total execution
- **Integration Tests**: <2 minutes total execution
- **E2E Tests**: <5 minutes total execution
- **Full Suite**: <10 minutes total execution