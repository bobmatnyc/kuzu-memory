# Engineer Memory - KuzuMemory Implementation Patterns

## Core Architecture Patterns

### Memory System Design
- **Layered architecture**: CLI → Async → Core → Storage → Database
- **Performance-first**: <100ms recall, <200ms generation targets
- **Dual database adapters**: CLI adapter (2-3x faster) + Python API
- **Connection pooling**: Reuse database connections for performance
- **LRU caching**: Cache frequent queries and entity lookups

### Data Models (Pydantic-based)
```python
class Memory(BaseModel):
    content: str              # Validated, trimmed content
    content_hash: str         # SHA256 for deduplication
    memory_type: MemoryType   # IDENTITY, PREFERENCE, DECISION, etc.
    importance: float         # 0.0-1.0, auto-set by type
    confidence: float         # 0.0-1.0, extraction confidence
    agent_id: str            # Source agent identification
    metadata: Dict[str, Any]  # Flexible additional data
    valid_to: Optional[datetime]  # Expiration (None = never)
```

### Memory Types and Retention
```python
MemoryType.IDENTITY     # Never expires (name, role, company)
MemoryType.PREFERENCE   # Never expires (tech preferences)
MemoryType.DECISION     # 90 days (architectural decisions)
MemoryType.PATTERN      # 30 days (code patterns)
MemoryType.SOLUTION     # 60 days (problem solutions)
MemoryType.STATUS       # 6 hours (current state)
MemoryType.CONTEXT      # 1 day (session context)
```

## Implementation Best Practices

### CLI Design (Click + Rich)
- **Rich formatting with fallbacks**: Graceful degradation when Rich unavailable
- **Comprehensive help system**: Every command has detailed examples
- **Error handling**: Custom exceptions with user-friendly messages
- **Debug mode**: `--debug` flag for detailed logging
- **Quiet mode**: `--quiet` for script/AI integration

### Async Processing System
```python
# Non-blocking learning pattern
class BackgroundLearner:
    def queue_learning_task(self, content: str) -> str:
        """Fire-and-forget async learning"""
        # Queue task, return task_id
        # Process in background thread
        # Never block CLI response
```

### Database Layer Abstraction
```python
def create_kuzu_adapter(db_path: Path, config: KuzuMemoryConfig):
    """Factory pattern for database adapters"""
    if config.storage.use_cli_adapter:
        return KuzuCLIAdapter(db_path)      # Faster, less control
    else:
        return KuzuPythonAdapter(db_path)   # Slower, more control
```

## Performance Optimization Patterns

### Query Optimization
- **Indexed entity lookups**: Fast retrieval by entity names
- **Batch operations**: Group database writes
- **Prepared statements**: Reuse query plans
- **Connection pooling**: Avoid connection overhead

### Memory Optimization
- **Content deduplication**: SHA256 hash-based duplicate detection
- **Automatic cleanup**: Remove expired memories
- **Streaming results**: Handle large result sets efficiently
- **Memory-mapped database**: Let Kuzu handle memory management

### Caching Strategy
```python
@lru_cache(maxsize=1000)
def cached_entity_lookup(entity: str) -> List[Memory]:
    """Cache entity-based memory lookups"""

# Cache invalidation on memory updates
def invalidate_entity_cache(entity: str):
    cached_entity_lookup.cache_clear()
```

## Testing Implementation Patterns

### Test Structure
- **Unit tests**: Component isolation, fast execution
- **Integration tests**: Cross-component scenarios
- **E2E tests**: Full CLI workflows via subprocess
- **Benchmark tests**: Performance validation
- **Regression tests**: Data integrity assurance

### Performance Testing
```python
@pytest.mark.benchmark
def test_recall_performance(benchmark):
    """Ensure <100ms recall time"""
    result = benchmark(memory.attach_memories, "test prompt")
    assert result.recall_time_ms < 100.0

def test_cli_subprocess_performance():
    """Test CLI integration pattern performance"""
    start = time.time()
    subprocess.run(['kuzu-memory', 'enhance', 'test'],
                  capture_output=True, timeout=5)
    assert (time.time() - start) < 0.1  # 100ms max
```

## AI Integration Implementation

### Universal Pattern (Subprocess-based)
```python
class AIMemoryIntegration:
    def enhance_prompt(self, prompt: str) -> str:
        """Standard enhancement pattern"""
        try:
            result = subprocess.run([
                'kuzu-memory', 'enhance', prompt, '--format', 'plain'
            ], capture_output=True, text=True, timeout=5)

            return result.stdout.strip() if result.returncode == 0 else prompt
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return prompt  # Always have fallback

    def learn_async(self, content: str) -> None:
        """Non-blocking learning"""
        subprocess.run([
            'kuzu-memory', 'learn', content, '--quiet'
        ], check=False)  # Fire and forget
```

### Error Handling Patterns
- **Graceful degradation**: Always return usable result
- **Timeout protection**: Never block indefinitely
- **Fallback strategies**: Original prompt if enhancement fails
- **Silent failures**: Log but don't crash on learning errors

## Code Quality Standards

### Type Hints and Validation
```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

def attach_memories(
    self,
    prompt: str,
    max_memories: int = 10,
    strategy: str = "auto"
) -> MemoryContext:
    """Type hints on all public methods"""
```

### Error Handling Hierarchy
```python
KuzuMemoryError              # Base exception
├── ConfigurationError       # Config issues
├── DatabaseError           # DB connectivity/corruption
├── PerformanceError        # Timeout/resource issues
├── ValidationError         # Input validation failures
└── IntegrationError        # AI system integration issues
```

### Logging Strategy
```python
import logging

logger = logging.getLogger(__name__)

# Use structured logging
logger.info("Memory operation", extra={
    'operation': 'recall',
    'prompt_length': len(prompt),
    'recall_time_ms': recall_time,
    'memories_found': len(memories)
})
```

## Database Schema Patterns

### Graph Structure
```cypher
// Kuzu graph schema
CREATE NODE TABLE Memory(
    id STRING,
    content STRING,
    memory_type STRING,
    importance DOUBLE,
    created_at TIMESTAMP,
    PRIMARY KEY(id)
)

CREATE NODE TABLE Entity(
    name STRING,
    entity_type STRING,
    PRIMARY KEY(name)
)

CREATE REL TABLE CONTAINS(FROM Memory TO Entity)
```

### Migration Strategy
- **Schema versioning**: Track schema version in system table
- **Backward compatibility**: Support multiple schema versions
- **Migration scripts**: Automated upgrade procedures
- **Data validation**: Verify integrity after migrations

## Configuration Management

### Hierarchical Configuration
```python
class KuzuMemoryConfig:
    """Configuration with validation and defaults"""
    storage: StorageConfig
    performance: PerformanceConfig
    recall: RecallConfig
    extraction: ExtractionConfig

    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'KuzuMemoryConfig':
        """Create from dictionary with validation"""
```

### Environment Override Pattern
```python
# Priority order:
# 1. CLI arguments (highest)
# 2. Environment variables (KUZU_MEMORY_*)
# 3. Config file (kuzu-memory.yaml)
# 4. Project defaults
# 5. System defaults (lowest)
```