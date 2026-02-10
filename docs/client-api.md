# KuzuMemory Python Client API

The Python Client API provides an async-first, production-ready interface for programmatic access to KuzuMemory without CLI dependencies.

## Features

- **Async/Await Interface**: Built with `asyncio.to_thread()` for non-blocking operations
- **Context Manager Support**: Automatic resource cleanup with `async with` syntax
- **Type-Safe**: Comprehensive type hints for IDE support (mypy strict mode)
- **CLI-Independent**: Pure library mode with no CLI dependencies
- **Thread-Safe**: Safe for use in async contexts

## Installation

```bash
pip install kuzu-memory
```

## Quick Start

### Basic Usage

```python
import asyncio
from kuzu_memory.client import KuzuMemoryClient

async def main():
    # Initialize client with project root
    async with KuzuMemoryClient(project_root="/path/to/project") as client:
        # Store a memory
        memory_id = await client.learn("User prefers Python for backend development")
        print(f"Stored memory: {memory_id}")

        # Query memories
        memories = await client.recall("What language does user prefer?")
        for memory in memories:
            print(f"[{memory.importance:.2f}] {memory.content}")

        # Enhance a prompt with context
        context = await client.enhance("Write a REST API server")
        print(context.enhanced_prompt)

        # Get statistics
        stats = client.get_stats()
        print(f"Total memories: {stats['memory_count']}")

asyncio.run(main())
```

### Custom Database Path

```python
async with KuzuMemoryClient(
    project_root="/path/to/project",
    db_path="/custom/db/path/memories.db"
) as client:
    await client.learn("Custom database location")
```

### With Git Sync

```python
async with KuzuMemoryClient(
    project_root="/path/to/project",
    enable_git_sync=True  # Enable git commit indexing
) as client:
    await client.learn("Memory with git sync enabled")
```

## Core Operations

### 1. Storing Memories (`learn`)

Store new memories with optional metadata:

```python
# Basic storage
memory_id = await client.learn("User prefers FastAPI framework")

# With metadata
memory_id = await client.learn(
    content="User likes TypeScript for frontend",
    source="conversation",
    session_id="session-123",
    agent_id="assistant",
    metadata={"confidence": 0.9, "category": "preference"}
)
```

### 2. Retrieving Memories (`recall`)

Query memories using semantic search:

```python
# Basic recall
memories = await client.recall(
    "What web framework does user prefer?",
    max_memories=5
)

# With filters
memories = await client.recall(
    query="programming preferences",
    max_memories=10,
    strategy="entity",  # "auto", "keyword", "entity", "temporal"
    session_id="session-123"
)

# Process results
for memory in memories:
    print(f"ID: {memory.id}")
    print(f"Content: {memory.content}")
    print(f"Type: {memory.memory_type}")
    print(f"Importance: {memory.importance}")
    print(f"Created: {memory.created_at}")
    print("---")
```

### 3. Enhancing Prompts (`enhance`)

RAG-style prompt enhancement with retrieved context:

```python
context = await client.enhance(
    prompt="Write a REST API for user management",
    max_memories=10,
    strategy="auto"
)

# Access enhanced prompt
print("Enhanced Prompt:")
print(context.enhanced_prompt)

# Access retrieval metadata
print(f"\nRetrieved {len(context.memories)} memories")
print(f"Confidence: {context.confidence:.2f}")
print(f"Recall time: {context.recall_time_ms:.2f}ms")
print(f"Strategy used: {context.strategy_used}")

# Send enhanced prompt to LLM
llm_response = await your_llm_client.generate(context.enhanced_prompt)
```

### 4. Statistics (`get_stats`)

Get system statistics (synchronous operation):

```python
stats = client.get_stats()

print(f"Total memories: {stats['memory_count']}")
print(f"Database size: {stats['database_size_bytes'] / 1024:.2f} KB")
print(f"Memory types: {stats['memory_type_stats']}")
print(f"Recent memories: {stats['recent_memories']}")
```

## Advanced Operations

### Memory Management

```python
# Get specific memory by ID
memory = await client.get_memory_by_id(memory_id)
if memory:
    print(memory.content)

# Get recent memories
recent = await client.get_recent_memories(limit=20)

# Delete a memory
deleted = await client.delete_memory(memory_id)
```

### Batch Operations

```python
from kuzu_memory.core.models import Memory, MemoryType

# Create multiple memories
memories = [
    Memory(
        content="First memory",
        memory_type=MemoryType.SEMANTIC,
        source_type="batch"
    ),
    Memory(
        content="Second memory",
        memory_type=MemoryType.EPISODIC,
        source_type="batch"
    )
]

# Store in batch
stored_ids = await client.batch_store_memories(memories)
print(f"Stored {len(stored_ids)} memories")
```

### Cleanup

```python
# Clean up expired memories
count = await client.cleanup_expired_memories()
print(f"Cleaned up {count} expired memories")
```

## Integration Patterns

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from kuzu_memory.client import KuzuMemoryClient

app = FastAPI()

# Global client instance
memory_client: KuzuMemoryClient | None = None

@app.on_event("startup")
async def startup():
    global memory_client
    memory_client = KuzuMemoryClient(
        project_root="/path/to/project",
        enable_git_sync=False
    )
    await memory_client.__aenter__()

@app.on_event("shutdown")
async def shutdown():
    if memory_client:
        await memory_client.__aexit__(None, None, None)

@app.post("/learn")
async def learn_endpoint(content: str):
    memory_id = await memory_client.learn(content)
    return {"memory_id": memory_id}

@app.get("/recall")
async def recall_endpoint(query: str, limit: int = 5):
    memories = await memory_client.recall(query, max_memories=limit)
    return {"memories": [m.model_dump() for m in memories]}
```

### LLM Chat Integration

```python
import asyncio
from kuzu_memory.client import KuzuMemoryClient

class ContextAwareChat:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.client = None

    async def __aenter__(self):
        self.client = KuzuMemoryClient(
            project_root=self.project_root,
            enable_git_sync=False
        )
        await self.client.__aenter__()
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.__aexit__(*args)

    async def chat(self, user_message: str) -> str:
        # Enhance user message with context
        context = await self.client.enhance(
            prompt=user_message,
            max_memories=5
        )

        # Send to LLM
        llm_response = await your_llm_generate(context.enhanced_prompt)

        # Learn from interaction
        await self.client.learn(
            f"User asked: {user_message}",
            metadata={"type": "question"}
        )
        await self.client.learn(
            f"Assistant answered: {llm_response}",
            metadata={"type": "response"}
        )

        return llm_response

# Usage
async def main():
    async with ContextAwareChat("/my/project") as chat:
        response = await chat.chat("What's my preferred stack?")
        print(response)
```

### Concurrent Operations

```python
import asyncio

async def process_batch():
    async with KuzuMemoryClient(project_root="/path") as client:
        # Run multiple operations concurrently
        results = await asyncio.gather(
            client.learn("Memory 1"),
            client.learn("Memory 2"),
            client.learn("Memory 3"),
            client.recall("query 1"),
            client.recall("query 2"),
        )
        print(f"Processed {len(results)} operations")
```

## Error Handling

```python
from kuzu_memory.client import KuzuMemoryClient
from pydantic import ValidationError

async def safe_learning():
    try:
        async with KuzuMemoryClient(project_root="/path") as client:
            await client.learn("Valid content")

    except RuntimeError as e:
        print(f"Client initialization error: {e}")

    except ValidationError as e:
        print(f"Validation error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Configuration

```python
# Custom configuration
config = {
    "performance": {
        "max_recall_time_ms": 50,
        "enable_performance_monitoring": False
    }
}

async with KuzuMemoryClient(
    project_root="/path",
    enable_git_sync=False,
    config=config
) as client:
    # Client uses custom configuration
    pass
```

## Best Practices

### 1. Use Context Managers

Always use `async with` for automatic resource cleanup:

```python
# ✅ CORRECT
async with KuzuMemoryClient(project_root="/path") as client:
    await client.learn("content")

# ❌ WRONG - Manual cleanup required
client = await create_client("/path")
await client.learn("content")
# Forgot to cleanup!
```

### 2. Disable Git Sync for Performance

Unless you need git commit indexing, disable git sync:

```python
async with KuzuMemoryClient(
    project_root="/path",
    enable_git_sync=False  # Faster initialization
) as client:
    pass
```

### 3. Batch Operations for Bulk Data

Use batch operations for better performance:

```python
# ✅ CORRECT - Single batch operation
memories = [Memory(...) for _ in range(100)]
await client.batch_store_memories(memories)

# ❌ WRONG - 100 individual operations
for content in contents:
    await client.learn(content)
```

### 4. Handle Errors Gracefully

```python
from pydantic import ValidationError

try:
    await client.learn(content)
except ValidationError:
    # Handle validation errors
    pass
except RuntimeError:
    # Handle client errors
    pass
```

## API Reference

### `KuzuMemoryClient`

#### Constructor

```python
KuzuMemoryClient(
    project_root: str | Path,
    db_path: str | Path | None = None,
    enable_git_sync: bool = False,
    auto_sync: bool = False,
    config: dict[str, Any] | None = None
)
```

#### Core Methods

- `async learn(content, source="api", **kwargs) -> str`: Store a memory
- `async recall(query, max_memories=5, **kwargs) -> list[Memory]`: Query memories
- `async enhance(prompt, max_memories=10, **kwargs) -> MemoryContext`: Enhance prompt
- `get_stats() -> dict`: Get statistics (sync)

#### Memory Operations

- `async get_memory_by_id(memory_id) -> Memory | None`
- `async get_recent_memories(limit=20) -> list[Memory]`
- `async delete_memory(memory_id) -> bool`
- `async batch_store_memories(memories) -> list[str]`
- `async cleanup_expired_memories() -> int`

#### Properties

- `project_root: Path`: Project root directory
- `db_path: Path`: Database path
- `is_initialized: bool`: Initialization status

### Convenience Functions

```python
# Quick client creation
client = await create_client(
    project_root="/path",
    enable_git_sync=False
)
```

## Performance Considerations

- **Initialization**: ~50-100ms (disable git sync for faster startup)
- **Learn**: <20ms per operation
- **Recall**: <50ms for typical queries
- **Enhance**: <100ms including context injection
- **Concurrent**: Safe for multiple async operations

## Troubleshooting

### "Client not initialized"

```python
# Forgot to use context manager
client = KuzuMemoryClient(project_root="/path")
await client.learn("content")  # ❌ RuntimeError

# Solution: Use async with
async with KuzuMemoryClient(project_root="/path") as client:
    await client.learn("content")  # ✅ Works
```

### "Database already exists" Errors

```python
# Multiple clients pointing to same database
# Each client manages its own connection pool
# This is safe but may be inefficient

# Prefer: Single client instance for your app
```

## Migration from CLI

### Before (CLI)

```bash
kuzu-memory memory learn "User prefers Python"
kuzu-memory memory recall "What language?"
```

### After (Python API)

```python
async with KuzuMemoryClient(project_root="/path") as client:
    await client.learn("User prefers Python")
    memories = await client.recall("What language?")
```

## Examples Repository

See full examples at: https://github.com/bobmatnyc/kuzu-memory/tree/main/examples/client

---

**Related Documentation:**
- [Core API](./core-api.md)
- [MCP Server](./mcp-server.md)
- [CLI Reference](./cli-reference.md)
