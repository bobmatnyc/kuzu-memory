# Integration API - Quick Reference

Quick reference for integrating KuzuMemory into your AI framework or application.

## Installation

```bash
pip install kuzu-memory
```

## Basic Usage (Standalone)

```python
from kuzu_memory import KuzuMemoryClient
import asyncio

async def main():
    async with KuzuMemoryClient(project_root="/path/to/project") as client:
        # Store memories
        await client.learn("User prefers FastAPI for APIs")

        # Query memories
        memories = await client.recall("What framework does user like?")

        # Enhance prompts with context
        context = await client.enhance("Build a REST API")
        print(context.enhanced_prompt)

asyncio.run(main())
```

## Framework Integration (Subservient Mode)

For frameworks that manage hooks centrally (like Claude MPM):

### Setup Phase

```python
from kuzu_memory import enable_subservient_mode, is_subservient_mode

# Enable subservient mode (prevents kuzu-memory from managing hooks)
result = enable_subservient_mode(
    project_root="/path/to/project",
    managed_by="your-framework-name"
)

# Verify
assert is_subservient_mode("/path/to/project") is True
```

### Runtime Phase

```python
from kuzu_memory import KuzuMemoryClient

class YourFramework:
    async def start(self):
        self.memory = KuzuMemoryClient(self.project_root)
        await self.memory.__aenter__()

    async def stop(self):
        await self.memory.__aexit__(None, None, None)

    async def process_input(self, user_input: str):
        # Enhance with context
        context = await self.memory.enhance(user_input)

        # Generate response using enhanced_prompt
        response = await self.generate_response(context.enhanced_prompt)

        # Store interaction
        await self.memory.learn(f"User: {user_input}\nAgent: {response}")

        return response
```

## API Reference

### Client Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `learn(content, source="api", ...)` | Store a memory | `str` (memory_id) |
| `recall(query, max_memories=5, ...)` | Query memories | `list[Memory]` |
| `enhance(prompt, max_memories=10, ...)` | Enhance prompt with context | `MemoryContext` |
| `get_stats()` | Get memory statistics | `dict` |
| `delete_memory(memory_id)` | Delete a memory | `bool` |
| `get_recent_memories(limit=20)` | Get recent memories | `list[Memory]` |

### Subservient Mode Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `enable_subservient_mode(project_root, managed_by="unknown", set_env_var=False)` | Enable subservient mode | `dict` |
| `is_subservient_mode(project_root=None)` | Check if subservient mode is active | `bool` |
| `create_subservient_config(project_root, managed_by="unknown")` | Create config file | `Path` |

## Complete Example: Framework Integration

```python
from kuzu_memory import (
    KuzuMemoryClient,
    enable_subservient_mode,
    is_subservient_mode
)
from pathlib import Path
import asyncio

class AIFramework:
    """Example AI framework with KuzuMemory integration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.memory = None

    @classmethod
    async def setup(cls, project_root: Path) -> "AIFramework":
        """Setup framework with subservient mode."""
        # Enable subservient mode
        result = enable_subservient_mode(
            project_root=project_root,
            managed_by="ai-framework"
        )
        print(f"✅ Subservient mode enabled: {result['config_path']}")

        # Create and initialize framework
        framework = cls(project_root)
        await framework.start()
        return framework

    async def start(self):
        """Initialize memory backend."""
        self.memory = KuzuMemoryClient(self.project_root)
        await self.memory.__aenter__()
        print("✅ Memory backend initialized")

    async def stop(self):
        """Cleanup resources."""
        if self.memory:
            await self.memory.__aexit__(None, None, None)
        print("✅ Cleaned up")

    async def chat(self, user_message: str) -> str:
        """Process user message with memory context."""
        # Enhance with relevant memories
        context = await self.memory.enhance(
            prompt=user_message,
            max_memories=5
        )

        # Simulate LLM call (replace with your LLM)
        response = f"Response to: {user_message} (with {len(context.memories)} context memories)"

        # Store interaction
        await self.memory.learn(
            f"User: {user_message}\nAssistant: {response}",
            source="framework-chat"
        )

        return response

# Usage
async def main():
    project_root = Path.cwd()

    # Setup (one-time)
    framework = await AIFramework.setup(project_root)

    try:
        # Chat with memory
        response = await framework.chat("What's the weather like?")
        print(f"Agent: {response}")

        response = await framework.chat("What did I just ask?")
        print(f"Agent: {response}")

    finally:
        await framework.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

- **Full Integration Guide**: [docs/integration-guide.md](./integration-guide.md) (6000+ words)
- **API Reference**: [src/kuzu_memory/client.py](../src/kuzu_memory/client.py) (docstrings)
- **Examples**: See integration guide for 3 detailed patterns

## Support

- GitHub Issues: https://github.com/bobmatnyc/kuzu-memory/issues
- Discussions: https://github.com/bobmatnyc/kuzu-memory/discussions
