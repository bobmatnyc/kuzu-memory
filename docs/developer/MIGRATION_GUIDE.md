# Migration Guide: Legacy to Cognitive Memory Types

## Overview

This guide covers migrating from the legacy domain-specific memory types to the new cognitive memory model in KuzuMemory. The cognitive model provides a more intuitive and scientifically-grounded approach to memory categorization.

## Why Migrate to Cognitive Types?

### Benefits of the Cognitive Model

1. **Intuitive Understanding**: Memory types map to how humans naturally categorize information
2. **Scientific Foundation**: Based on established cognitive psychology research
3. **Better Retention Policies**: Retention periods align with natural memory characteristics
4. **Improved Classification**: More accurate automatic classification using NLP
5. **Cross-Platform Compatibility**: Standardized model shared between Python and TypeScript implementations
6. **Clearer Semantics**: Each type has distinct characteristics and use cases

### Migration Advantages

- **Zero Downtime**: Migration happens automatically in the background
- **Backward Compatibility**: Legacy type strings continue to work
- **Data Integrity**: All existing memories are preserved with metadata tracking
- **Rollback Support**: Migration can be reversed if needed

## Legacy vs Cognitive Type Mapping

### Complete Mapping Table

| Legacy Type | Cognitive Type | Rationale | Examples |
|------------|----------------|-----------|----------|
| **IDENTITY** | **SEMANTIC** | Identity facts are semantic knowledge | "My name is Alice", "Team lead is John" |
| **PREFERENCE** | **PREFERENCE** | Already cognitive - no change | "I prefer dark mode", "Team uses TypeScript" |
| **DECISION** | **EPISODIC** | Decisions are temporal events/experiences | "Yesterday we chose FastAPI", "Agreed to use MongoDB" |
| **PATTERN** | **PROCEDURAL** | Patterns are instructional procedures | "Always use async/await", "Follow REST principles" |
| **SOLUTION** | **PROCEDURAL** | Solutions are step-by-step instructions | "To fix bug X, restart service Y", "Deploy using command Z" |
| **STATUS** | **WORKING** | Status represents current work/tasks | "Currently debugging API", "Need to review PR #123" |
| **CONTEXT** | **EPISODIC** | Context is experiential/situational | "During last sprint we...", "In the previous meeting..." |

### Detailed Migration Examples

#### IDENTITY → SEMANTIC
```python
# Legacy
Memory(content="My name is Alice", memory_type="identity")

# Migrated
Memory(content="My name is Alice", memory_type=MemoryType.SEMANTIC)
```

#### DECISION → EPISODIC
```python
# Legacy
Memory(content="We decided to use PostgreSQL", memory_type="decision")

# Migrated
Memory(content="We decided to use PostgreSQL", memory_type=MemoryType.EPISODIC)
```

#### PATTERN → PROCEDURAL
```python
# Legacy
Memory(content="Always validate input parameters", memory_type="pattern")

# Migrated
Memory(content="Always validate input parameters", memory_type=MemoryType.PROCEDURAL)
```

## Migration Methods

### 1. Automatic Migration (Recommended)

The system automatically converts legacy types when encountered:

```python
from kuzu_memory.core.models import MemoryType

# Legacy type strings are automatically converted
memory_type = MemoryType.from_legacy_type("identity")
print(memory_type)  # Output: MemoryType.SEMANTIC

# Works in all contexts
memory = Memory(content="Test content", memory_type="decision")
print(memory.memory_type)  # Output: MemoryType.EPISODIC
```

### 2. Database Migration Script

For bulk migration of existing memories:

```python
from kuzu_memory.migrations.cognitive_types import CognitiveTypesMigration
from kuzu_memory.storage.memory_store import MemoryStore
from kuzu_memory.core.config import KuzuMemoryConfig

def migrate_existing_memories():
    """Migrate all existing memories to cognitive types."""

    # Initialize components
    config = KuzuMemoryConfig.from_file()
    memory_store = MemoryStore(config)

    # Create migration instance
    migration = CognitiveTypesMigration(memory_store)

    # Run migration
    print("Starting migration...")
    stats = migration.migrate_all_memories()

    print(f"Migration completed:")
    print(f"  Migrated: {stats['migrated_count']} memories")
    print(f"  Skipped: {stats['skipped_count']} memories")
    print(f"  Errors: {stats['error_count']} memories")

    # Validate migration
    if migration.validate_migration():
        print("Migration validation successful!")
        return True
    else:
        print("Migration validation failed!")
        return False

# Run migration
if __name__ == "__main__":
    migrate_existing_memories()
```

### 3. CLI Migration

Command-line migration tools:

```bash
# Check current memory type distribution
kuzu-memory stats --by-type

# Run interactive migration
python -m kuzu_memory.migrations.cognitive_types --interactive

# Run automated migration
python -m kuzu_memory.migrations.cognitive_types --auto

# Validate migration results
kuzu-memory validate --migration cognitive-types

# Rollback if needed
python -m kuzu_memory.migrations.cognitive_types --rollback
```

## Step-by-Step Migration Process

### Step 1: Backup Your Data

```bash
# Create backup before migration
kuzu-memory backup --output ./kuzu-backup-$(date +%Y%m%d).db

# Verify backup
kuzu-memory restore --dry-run ./kuzu-backup-*.db
```

### Step 2: Analyze Current Memory Types

```bash
# Check what types you currently have
kuzu-memory stats --detailed --by-type

# Export current memories for analysis
kuzu-memory export --format json --output memories-pre-migration.json
```

### Step 3: Run Migration

```python
# Python script approach
from kuzu_memory.migrations.cognitive_types import CognitiveTypesMigration

# Initialize migration
migration = CognitiveTypesMigration.from_config()

# Dry run first
dry_run_stats = migration.dry_run()
print(f"Would migrate {dry_run_stats['total_affected']} memories")

# Actual migration
if input("Proceed with migration? (y/N): ").lower() == 'y':
    stats = migration.migrate_all_memories()
    print(f"Migration complete: {stats}")
```

### Step 4: Validate Results

```bash
# Check new type distribution
kuzu-memory stats --by-type

# Verify specific memories
kuzu-memory list --type SEMANTIC | head -5
kuzu-memory list --type EPISODIC | head -5
kuzu-memory list --type PROCEDURAL | head -5

# Test functionality
kuzu-memory recall "test query" --types SEMANTIC,PROCEDURAL
```

### Step 5: Update Application Code

Update your application to use the new types:

```python
# Old code
memory = Memory(content="User prefers dark mode", memory_type="preference")

# New code (both work, but new is preferred)
from kuzu_memory.core.models import MemoryType
memory = Memory(content="User prefers dark mode", memory_type=MemoryType.PREFERENCE)

# For AI integration - no changes needed
# CLI calls automatically handle type conversion
result = subprocess.run(['kuzu-memory', 'enhance', prompt], capture_output=True, text=True)
```

## Code Updates Required

### Minimal Code Changes

Most existing code requires no changes due to automatic conversion:

```python
# This continues to work unchanged
from kuzu_memory import KuzuMemory

memory = KuzuMemory()
memory.generate_memories("I prefer using TypeScript")  # Auto-classified as PREFERENCE
context = memory.attach_memories("What do I prefer?")   # Automatically finds PREFERENCE memories
```

### Recommended Updates

For new code, use the explicit cognitive types:

```python
from kuzu_memory.core.models import Memory, MemoryType

# Recommended: explicit cognitive types
semantic_memory = Memory(
    content="Python is a programming language",
    memory_type=MemoryType.SEMANTIC
)

episodic_memory = Memory(
    content="Yesterday we deployed version 2.0",
    memory_type=MemoryType.EPISODIC
)

procedural_memory = Memory(
    content="To run tests, use pytest command",
    memory_type=MemoryType.PROCEDURAL
)
```

### Configuration Updates

Update configuration files to use cognitive types:

```yaml
# .kuzu_memory/config.yaml
version: 1.0

memory:
  default_type: "SEMANTIC"  # Was: "identity"

  retention:
    SEMANTIC: null          # Was: identity: null
    EPISODIC: "30 days"     # Was: decision: "90 days"
    PROCEDURAL: null        # Was: pattern: null
    WORKING: "1 day"        # Was: status: "1 day"
    SENSORY: "6 hours"      # New type
    PREFERENCE: null        # Unchanged

recall:
  priority_types:           # Updated type names
    - SEMANTIC
    - PROCEDURAL
    - PREFERENCE
```

## Testing Your Migration

### Unit Tests

```python
import pytest
from kuzu_memory.core.models import MemoryType
from kuzu_memory.migrations.cognitive_types import CognitiveTypesMigration

def test_legacy_type_conversion():
    """Test that legacy types convert correctly."""
    assert MemoryType.from_legacy_type("identity") == MemoryType.SEMANTIC
    assert MemoryType.from_legacy_type("decision") == MemoryType.EPISODIC
    assert MemoryType.from_legacy_type("pattern") == MemoryType.PROCEDURAL

def test_migration_preserves_data():
    """Test that migration preserves all memory data."""
    # Test implementation
    pass

def test_rollback_functionality():
    """Test that migration can be rolled back."""
    # Test implementation
    pass
```

### Integration Tests

```bash
# Run migration-specific tests
pytest tests/test_cognitive_migration.py -v

# Run full test suite to ensure nothing breaks
pytest tests/ -v

# Test CLI functionality with new types
bash tests/test_cli_cognitive_types.sh
```

### Performance Testing

```python
import time
from kuzu_memory import KuzuMemory

def benchmark_migration():
    """Benchmark memory operations after migration."""
    memory = KuzuMemory()

    # Test recall performance
    start_time = time.time()
    result = memory.attach_memories("test query")
    recall_time = time.time() - start_time

    assert recall_time < 0.1  # Should be under 100ms

    # Test generation performance
    start_time = time.time()
    memory.generate_memories("test content for generation")
    generation_time = time.time() - start_time

    assert generation_time < 0.2  # Should be under 200ms
```

## Rollback Procedures

If you need to rollback the migration:

### Automatic Rollback

```python
from kuzu_memory.migrations.cognitive_types import CognitiveTypesMigration

# Initialize migration instance
migration = CognitiveTypesMigration.from_config()

# Rollback to legacy types
rollback_stats = migration.rollback_migration()
print(f"Rollback completed: {rollback_stats}")

# Validate rollback
if migration.validate_rollback():
    print("Rollback validation successful!")
```

### Manual Rollback

```bash
# Restore from backup
kuzu-memory restore ./kuzu-backup-*.db

# Or use CLI rollback
python -m kuzu_memory.migrations.cognitive_types --rollback --confirm

# Verify rollback
kuzu-memory stats --by-type
```

## Troubleshooting

### Common Issues

1. **Migration Fails Mid-Process**
   ```bash
   # Check migration status
   kuzu-memory migration-status

   # Resume incomplete migration
   python -m kuzu_memory.migrations.cognitive_types --resume
   ```

2. **Performance Degradation**
   ```python
   # Rebuild indexes after migration
   from kuzu_memory.storage.memory_store import MemoryStore

   store = MemoryStore.from_config()
   store.rebuild_indexes()
   ```

3. **Classification Accuracy Issues**
   ```bash
   # Retrain classifier with new types
   python -m kuzu_memory.nlp.train_classifier --cognitive-types

   # Test classification
   kuzu-memory classify "sample text" --debug
   ```

### Getting Help

- **Documentation**: Check [MEMORY_TYPES.md](MEMORY_TYPES.md) for detailed type information
- **GitHub Issues**: Report bugs or questions
- **Debug Mode**: Use `--debug` flag with CLI commands for detailed output
- **Validation**: Use `kuzu-memory validate` to check system integrity

## Migration Checklist

Before migration:
- [ ] Back up your current database
- [ ] Review current memory type distribution
- [ ] Test in development environment first
- [ ] Review application code for compatibility

During migration:
- [ ] Run dry run first
- [ ] Monitor migration progress
- [ ] Validate results at each step
- [ ] Test core functionality

After migration:
- [ ] Verify type distribution matches expectations
- [ ] Test recall and generation performance
- [ ] Update application code to use new types
- [ ] Update configuration files
- [ ] Run full test suite
- [ ] Monitor system performance

## Best Practices Post-Migration

1. **Use Explicit Types**: Prefer `MemoryType.SEMANTIC` over string literals
2. **Review Classifications**: Audit automatic classifications for accuracy
3. **Update Documentation**: Update team documentation with new type system
4. **Monitor Performance**: Watch for any performance regressions
5. **Train Team**: Ensure team understands new cognitive model

## Summary

The migration from legacy to cognitive memory types provides significant benefits in terms of intuitive understanding, scientific grounding, and cross-platform compatibility. The migration process is designed to be safe, reversible, and minimally disruptive to existing applications.

Key points:
- Migration is automatic and backward-compatible
- Legacy type strings continue to work
- New cognitive types provide better semantics
- Performance and functionality remain unchanged
- Rollback is supported if needed

For questions or issues with migration, refer to the troubleshooting section or open an issue in the project repository.