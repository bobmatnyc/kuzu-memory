# Python Client API (README Snippet)

> Add this section to the main README.md after the installation section

## Python Client API

KuzuMemory provides an async Python client for programmatic access without CLI dependencies.

### Quick Start

```python
import asyncio
from kuzu_memory.client import KuzuMemoryClient

async def main():
    async with KuzuMemoryClient(project_root="/path/to/project") as client:
        # Store memories
        await client.learn("User prefers Python for backend development")

        # Query memories
        memories = await client.recall("What language does user prefer?")
        for memory in memories:
            print(f"[{memory.importance:.2f}] {memory.content}")

        # Enhance prompts with RAG
        context = await client.enhance("Write a REST API server")
        print(context.enhanced_prompt)

        # Get statistics
        stats = client.get_stats()
        print(f"Total memories: {stats['memory_count']}")

asyncio.run(main())
```

### Core Operations

| Operation | Method | Description |
|-----------|--------|-------------|
| **Store** | `await client.learn(content)` | Store new memory |
| **Query** | `await client.recall(query)` | Semantic search |
| **Enhance** | `await client.enhance(prompt)` | RAG augmentation |
| **Stats** | `client.get_stats()` | Get statistics |

### Features

- ✅ **Async/Await**: Non-blocking operations with `asyncio`
- ✅ **Type-Safe**: 100% mypy strict compliance
- ✅ **Context Manager**: Automatic resource cleanup
- ✅ **No CLI Deps**: Pure library mode
- ✅ **Well-Documented**: Comprehensive docstrings and examples

### Installation

```bash
pip install kuzu-memory
```

### Documentation

- [Complete API Reference](./docs/client-api.md)
- [Working Examples](./examples/client_usage.py)
- [Integration Patterns](./docs/client-api.md#integration-patterns)

### FastAPI Integration Example

```python
from fastapi import FastAPI
from kuzu_memory.client import KuzuMemoryClient

app = FastAPI()
memory_client = None

@app.on_event("startup")
async def startup():
    global memory_client
    memory_client = KuzuMemoryClient(project_root="/path")
    await memory_client.__aenter__()

@app.on_event("shutdown")
async def shutdown():
    if memory_client:
        await memory_client.__aexit__(None, None, None)

@app.post("/learn")
async def learn(content: str):
    memory_id = await memory_client.learn(content)
    return {"memory_id": memory_id}

@app.get("/recall")
async def recall(query: str, limit: int = 5):
    memories = await memory_client.recall(query, max_memories=limit)
    return {"memories": [m.model_dump() for m in memories]}
```

### Performance

- **Initialization**: ~50-100ms (disable git sync for faster startup)
- **Learn**: <20ms per operation
- **Recall**: <50ms for typical queries
- **Enhance**: <100ms including context injection

For more details, see the [Python Client API documentation](./docs/client-api.md).
