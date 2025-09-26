# Cognitive Memory Types Migration

## Overview

KuzuMemory has been migrated from domain-specific memory types to a cognitive memory model inspired by human memory systems. This change provides a more intuitive and scientifically-grounded approach to memory categorization.

## New Memory Types

The system now uses 6 cognitive memory types:

1. **EPISODIC** - Personal experiences and events
   - Examples: "Yesterday I went to the park", "We decided to use FastAPI"
   - Retention: 30 days (personal experiences fade)
   - Importance: 0.7 (medium-high)

2. **SEMANTIC** - Facts and general knowledge
   - Examples: "Paris is the capital of France", "My name is Alice"
   - Retention: None (facts don't expire)
   - Importance: 1.0 (highest)

3. **PROCEDURAL** - Instructions and how-to content
   - Examples: "To make coffee, first boil water", "Steps to deploy the app"
   - Retention: None (instructions don't expire)
   - Importance: 0.9 (high)

4. **WORKING** - Tasks and current focus
   - Examples: "Need to finish the report by tomorrow", "Currently debugging the API"
   - Retention: 1 day (tasks are short-lived)
   - Importance: 0.5 (medium)

5. **SENSORY** - Sensory descriptions
   - Examples: "The coffee smells like fresh roasted beans", "The room feels cold"
   - Retention: 6 hours (sensory memories fade quickly)
   - Importance: 0.3 (low)

6. **PREFERENCE** - User/team preferences
   - Examples: "I prefer dark mode", "We use tabs not spaces"
   - Retention: None (preferences persist)
   - Importance: 0.9 (high)

## Migration Mapping

Legacy types are automatically migrated to cognitive types:

| Legacy Type | Cognitive Type | Rationale |
|------------|----------------|-----------|
| IDENTITY   | SEMANTIC      | Identity facts are semantic knowledge |
| PREFERENCE | PREFERENCE    | Unchanged - already cognitive |
| DECISION   | EPISODIC      | Decisions are events/experiences |
| PATTERN    | PROCEDURAL    | Patterns are procedures |
| SOLUTION   | PROCEDURAL    | Solutions are instructions |
| STATUS     | WORKING       | Status is current work/tasks |
| CONTEXT    | EPISODIC      | Context is experiential |

## Using the Migration

### Automatic Migration

The system automatically converts legacy types when encountered:

```python
from kuzu_memory.core.models import MemoryType

# Legacy types are automatically converted
memory_type = MemoryType.from_legacy_type("identity")  # Returns SEMANTIC
```

### Manual Migration

To migrate existing memories in your database:

```python
from kuzu_memory.migrations.cognitive_types import CognitiveTypesMigration
from kuzu_memory.storage.memory_store import MemoryStore
from kuzu_memory.core.config import KuzuMemoryConfig

# Initialize
config = KuzuMemoryConfig.from_file()
memory_store = MemoryStore(config)

# Run migration
migration = CognitiveTypesMigration(memory_store)
stats = migration.migrate_all_memories()

# Validate
if migration.validate_migration():
    print("Migration successful!")
```

### CLI Migration

You can also run migration from the command line:

```bash
# Check current memory types
kuzu-memory stats --detailed

# Run migration (if needed)
python -m kuzu_memory.migrations.cognitive_types

# Verify migration
kuzu-memory list --format json | jq '.[] | .memory_type'
```

## API Changes

### Creating New Memories

```python
from kuzu_memory.core.models import Memory, MemoryType

# Create different types of memories
fact = Memory(
    content="Python is a programming language",
    memory_type=MemoryType.SEMANTIC
)

experience = Memory(
    content="Yesterday we deployed the new feature",
    memory_type=MemoryType.EPISODIC
)

instruction = Memory(
    content="To run tests, use pytest command",
    memory_type=MemoryType.PROCEDURAL
)

task = Memory(
    content="Need to review pull request #123",
    memory_type=MemoryType.WORKING
)

sensory = Memory(
    content="The server room sounds unusually loud",
    memory_type=MemoryType.SENSORY
)

preference = Memory(
    content="Team prefers async communication",
    memory_type=MemoryType.PREFERENCE
)
```

### Pattern Matching

The NLP classifier has been updated with new patterns for cognitive types:

```python
from kuzu_memory.nlp.classifier import MemoryClassifier

classifier = MemoryClassifier()

# Automatically classifies to appropriate cognitive type
result = classifier.classify("Yesterday I fixed the bug")
# result.memory_type == MemoryType.EPISODIC

result = classifier.classify("Water boils at 100°C")
# result.memory_type == MemoryType.SEMANTIC

result = classifier.classify("To deploy, run make deploy")
# result.memory_type == MemoryType.PROCEDURAL
```

## Benefits of Cognitive Model

1. **Intuitive Understanding**: Types map to how humans naturally categorize memories
2. **Scientific Basis**: Based on established cognitive psychology models
3. **Better Retention Policies**: Retention periods align with memory characteristics
4. **Improved Classification**: More accurate automatic classification
5. **Clearer Semantics**: Each type has distinct characteristics and use cases

## Backward Compatibility

- All legacy type strings are automatically converted
- Existing memories are migrated with metadata tracking
- No breaking changes to the API structure
- Migration can be rolled back if needed (metadata preserved)

## Testing

Run tests to verify the migration:

```bash
# Run migration tests
pytest tests/test_cognitive_migration.py -v

# Run classifier tests with new types
pytest tests/test_nlp_classifier.py -v

# Run all tests
pytest tests/ -v
```

## Summary

The cognitive memory type system provides a more intuitive and scientifically-grounded approach to memory management. The migration is automatic and backward-compatible, ensuring a smooth transition for existing systems while providing improved memory categorization for future use.