# KuzuMemory Integration Guide

This guide shows how to integrate KuzuMemory as a backend service in your AI framework or application.

## Table of Contents

- [Overview](#overview)
- [Python API](#python-api)
- [Subservient Mode](#subservient-mode)
- [Integration Patterns](#integration-patterns)
- [Example: Claude MPM Integration](#example-claude-mpm-integration)
- [Best Practices](#best-practices)

## Overview

KuzuMemory can be integrated into your application in two ways:

1. **Standalone Mode** (default): KuzuMemory manages its own hooks and configuration
2. **Subservient Mode**: Your framework manages hooks centrally, KuzuMemory provides memory backend

### When to Use Subservient Mode

Use subservient mode when:

- Your framework already manages git hooks centrally
- You want unified hook installation across multiple tools
- You need custom control over when/how memories are captured
- Your framework orchestrates multiple AI memory systems

**Example**: Claude MPM manages hooks for multiple tools (kuzu-memory, custom analyzers, etc.) and needs centralized control.

## Python API

KuzuMemory provides an async-first Python client for programmatic access:

```python
from kuzu_memory import KuzuMemoryClient

async def main():
    # Initialize client with context manager
    async with KuzuMemoryClient(project_root="/path/to/project") as client:
        # Store memories
        memory_id = await client.learn("User prefers FastAPI for APIs")

        # Query memories semantically
        memories = await client.recall("What framework does user like?")
        for memory in memories:
            print(f"{memory.content} (score: {memory.importance})")

        # Enhance prompts with context (RAG pattern)
        context = await client.enhance("Build a REST API")
        print(context.enhanced_prompt)  # Prompt + injected memories

        # Get statistics
        stats = client.get_stats()
        print(f"Total memories: {stats['memory_count']}")
```

### Client Features

- **Async/await**: Non-blocking I/O operations
- **Context manager**: Automatic resource cleanup
- **Type-safe**: Full type hints for IDE support
- **Thread-safe**: Uses `asyncio.to_thread()` for sync operations
- **No CLI dependencies**: Pure library mode

### Client API Reference

#### Storage Operations

```python
# Store a single memory
memory_id = await client.learn(
    content="User prefers Python over JavaScript",
    source="api",  # Optional: source identifier
    session_id="session-123",  # Optional: session grouping
    metadata={"confidence": 0.9}  # Optional: custom metadata
)

# Batch store multiple memories
from kuzu_memory import Memory, MemoryType

memories = [
    Memory(content="First memory", memory_type=MemoryType.SEMANTIC),
    Memory(content="Second memory", memory_type=MemoryType.EPISODIC)
]
stored_ids = await client.batch_store_memories(memories)
```

#### Retrieval Operations

```python
# Semantic recall (vector search)
memories = await client.recall(
    query="programming preferences",
    max_memories=5,
    strategy="auto"  # "auto", "keyword", "entity", "temporal"
)

# Get recent memories
recent = await client.get_recent_memories(limit=20)

# Get specific memory by ID
memory = await client.get_memory_by_id("uuid-string")
```

#### RAG (Retrieval-Augmented Generation)

```python
# Enhance prompt with relevant context
context = await client.enhance(
    prompt="Write a web API",
    max_memories=10
)

# Access enhanced prompt and metadata
print(context.enhanced_prompt)  # Original + context
print(f"Used {len(context.memories)} memories")
print(f"Confidence: {context.confidence}")
print(f"Recall time: {context.recall_time_ms}ms")
```

#### Management Operations

```python
# Delete memory
deleted = await client.delete_memory("memory-id")

# Cleanup expired memories
count = await client.cleanup_expired_memories()

# Get statistics (synchronous)
stats = client.get_stats()
# {
#     "memory_count": 42,
#     "database_size_bytes": 1024000,
#     "memory_type_stats": {...},
#     "recent_memories": 10
# }
```

## Subservient Mode

Subservient mode allows parent frameworks to manage KuzuMemory as a backend service.

### Enabling Subservient Mode

Two methods to enable subservient mode:

#### Method 1: Programmatic (Recommended)

```python
from kuzu_memory import enable_subservient_mode

# Called by parent framework during setup
result = enable_subservient_mode(
    project_root="/path/to/project",
    managed_by="claude-mpm",  # Your framework name
    set_env_var=False  # Optional: set KUZU_MEMORY_MODE env var
)

print(f"Config created at: {result['config_path']}")
# Output: Config created at: /path/to/project/.kuzu-memory-config
```

#### Method 2: Environment Variable

```bash
# Set environment variable (all projects in this shell session)
export KUZU_MEMORY_MODE=subservient

# Or per-command
KUZU_MEMORY_MODE=subservient your-framework-command
```

#### Method 3: Config File (Manual)

Create `.kuzu-memory-config` in project root:

```yaml
mode: subservient
managed_by: your-framework-name
version: "1.0"
```

### Detecting Subservient Mode

```python
from kuzu_memory import is_subservient_mode
from pathlib import Path

project_root = Path("/path/to/project")

if is_subservient_mode(project_root):
    print("Subservient mode active - skip hook installation")
else:
    print("Standalone mode - install hooks")
```

### Behavior in Subservient Mode

When kuzu-memory detects subservient mode:

- ✅ **Memory operations work normally** (store, recall, enhance)
- ✅ **Database operations continue** (no changes)
- ❌ **Hook installation is SKIPPED** (parent manages hooks)
- ❌ **Hook verification is SKIPPED** (parent manages verification)

### Creating Config Files

```python
from kuzu_memory import create_subservient_config
from pathlib import Path

# Create config file manually
config_path = create_subservient_config(
    project_root=Path("/path/to/project"),
    managed_by="my-framework"
)
print(f"Created: {config_path}")
```

## Integration Patterns

### Pattern 1: Direct Client Usage

Simple integration for frameworks that just need memory storage/retrieval:

```python
from kuzu_memory import KuzuMemoryClient

class MyFramework:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.memory_client = None

    async def start(self):
        """Initialize memory backend."""
        self.memory_client = KuzuMemoryClient(self.project_root)
        await self.memory_client.__aenter__()

    async def stop(self):
        """Cleanup memory backend."""
        if self.memory_client:
            await self.memory_client.__aexit__(None, None, None)

    async def handle_user_message(self, message: str):
        """Process user message with memory context."""
        # Retrieve relevant memories
        memories = await self.memory_client.recall(message, max_memories=5)

        # Build context
        context = "\n".join(f"- {m.content}" for m in memories)

        # Generate response with context
        prompt = f"Context:\n{context}\n\nUser: {message}"
        response = await self.generate_response(prompt)

        # Store new memory from conversation
        await self.memory_client.learn(
            f"User said: {message}\nAssistant responded: {response}",
            source="conversation"
        )

        return response
```

### Pattern 2: Subservient Mode with Centralized Hooks

Framework manages hooks, delegates memory storage to kuzu-memory:

```python
from kuzu_memory import KuzuMemoryClient, enable_subservient_mode
from pathlib import Path

class ManagedFramework:
    """Framework with centralized hook management."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.memory_client = None

    async def setup(self):
        """Setup phase: enable subservient mode and install hooks."""
        # Enable subservient mode (prevents kuzu-memory from installing hooks)
        enable_subservient_mode(
            project_root=self.project_root,
            managed_by="managed-framework"
        )

        # Install your own hooks that call kuzu-memory
        self.install_centralized_hooks()

        # Initialize memory client
        self.memory_client = KuzuMemoryClient(self.project_root)
        await self.memory_client.__aenter__()

    def install_centralized_hooks(self):
        """Install framework-managed hooks."""
        hook_script = """#!/usr/bin/env python3
import asyncio
from kuzu_memory import KuzuMemoryClient

async def main():
    # Get commit message
    with open('.git/COMMIT_EDITMSG', 'r') as f:
        commit_msg = f.read()

    # Store in kuzu-memory via API
    async with KuzuMemoryClient('.') as client:
        await client.learn(
            f"Commit: {commit_msg}",
            source="git-hook"
        )

asyncio.run(main())
"""
        hook_path = self.project_root / ".git/hooks/post-commit"
        hook_path.write_text(hook_script)
        hook_path.chmod(0o755)

    async def on_git_commit(self, commit_message: str):
        """Called by centralized hook after commit."""
        await self.memory_client.learn(
            f"Git commit: {commit_message}",
            source="git-hook"
        )
```

### Pattern 3: RAG Pipeline Integration

Integrate KuzuMemory into your RAG (Retrieval-Augmented Generation) pipeline:

```python
from kuzu_memory import KuzuMemoryClient
from typing import List, Dict, Any

class RAGPipeline:
    """RAG pipeline with KuzuMemory as context backend."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.memory_client = None

    async def initialize(self):
        """Initialize memory backend."""
        self.memory_client = KuzuMemoryClient(self.project_root)
        await self.memory_client.__aenter__()

    async def generate_with_context(
        self,
        prompt: str,
        max_context_memories: int = 10
    ) -> Dict[str, Any]:
        """Generate response with memory-enhanced context."""
        # Use KuzuMemory's built-in RAG enhancement
        context = await self.memory_client.enhance(
            prompt=prompt,
            max_memories=max_context_memories
        )

        # Send enhanced prompt to LLM
        response = await self.call_llm(context.enhanced_prompt)

        # Store the interaction as a new memory
        await self.memory_client.learn(
            f"Q: {prompt}\nA: {response}",
            source="rag-pipeline",
            metadata={
                "memories_used": len(context.memories),
                "confidence": context.confidence
            }
        )

        return {
            "response": response,
            "context": context,
            "memories_used": len(context.memories)
        }

    async def call_llm(self, prompt: str) -> str:
        """Call your LLM (OpenAI, Anthropic, etc.)."""
        # Your LLM integration here
        pass
```

## Example: Claude MPM Integration

Complete example of integrating KuzuMemory into Claude MPM:

### Setup Phase (during `mpm setup`)

```python
# File: claude_mpm/setup.py

from kuzu_memory import enable_subservient_mode, is_subservient_mode
from pathlib import Path
import click

@click.command()
@click.argument('project_root', type=click.Path(exists=True))
def setup_kuzu_memory(project_root: str):
    """Setup KuzuMemory as MPM backend."""
    project_path = Path(project_root)

    # Enable subservient mode (prevents kuzu-memory from managing hooks)
    result = enable_subservient_mode(
        project_root=project_path,
        managed_by="claude-mpm"
    )

    click.echo(f"✅ KuzuMemory subservient mode enabled")
    click.echo(f"   Config: {result['config_path']}")

    # Verify subservient mode
    if is_subservient_mode(project_path):
        click.echo("✅ Subservient mode verified")
    else:
        click.echo("❌ Failed to enable subservient mode")
        raise click.ClickException("Subservient mode setup failed")

    # Install MPM's centralized hooks (not kuzu-memory's)
    install_mpm_hooks(project_path)
```

### Runtime Phase (during agent operations)

```python
# File: claude_mpm/agent.py

from kuzu_memory import KuzuMemoryClient
from pathlib import Path
import asyncio

class MPMAgent:
    """Claude MPM agent with KuzuMemory integration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.memory = None

    async def start(self):
        """Initialize agent and memory backend."""
        # Initialize KuzuMemory client
        self.memory = KuzuMemoryClient(self.project_root)
        await self.memory.__aenter__()

        print(f"Agent started with memory at {self.memory.db_path}")

    async def stop(self):
        """Cleanup agent resources."""
        if self.memory:
            await self.memory.__aexit__(None, None, None)

    async def process_user_input(self, user_input: str) -> str:
        """Process user input with memory context."""
        # Retrieve relevant memories
        context = await self.memory.enhance(
            prompt=user_input,
            max_memories=10
        )

        # Generate response using enhanced prompt
        response = await self.generate_response(context.enhanced_prompt)

        # Store interaction as memory
        await self.memory.learn(
            f"User: {user_input}\nAgent: {response}",
            source="mpm-agent",
            session_id=self.get_session_id()
        )

        return response

    async def on_code_change(self, file_path: str, diff: str):
        """Called when code changes (via MPM hooks)."""
        # Store code change as memory
        await self.memory.learn(
            f"Code changed in {file_path}:\n{diff}",
            source="code-change",
            metadata={"file": file_path}
        )

    async def on_git_commit(self, commit_msg: str, changed_files: list):
        """Called when commit happens (via MPM hooks)."""
        # Store commit as memory
        await self.memory.learn(
            f"Commit: {commit_msg}\nFiles: {', '.join(changed_files)}",
            source="git-commit"
        )

# Usage
async def main():
    agent = MPMAgent(Path.cwd())
    try:
        await agent.start()

        # Agent operations
        response = await agent.process_user_input("How should I structure my API?")
        print(response)

    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Hook Integration (MPM manages hooks)

```python
# File: claude_mpm/hooks.py

from kuzu_memory import KuzuMemoryClient
from pathlib import Path
import asyncio

async def post_commit_hook(project_root: Path, commit_message: str):
    """MPM's post-commit hook that delegates to KuzuMemory."""
    async with KuzuMemoryClient(project_root) as memory:
        await memory.learn(
            f"Git commit: {commit_message}",
            source="mpm-git-hook"
        )
        print(f"✅ Stored commit in KuzuMemory")

async def code_analysis_hook(project_root: Path, analysis_results: dict):
    """MPM's code analysis hook."""
    async with KuzuMemoryClient(project_root) as memory:
        # Store analysis insights
        for insight in analysis_results.get("insights", []):
            await memory.learn(
                insight,
                source="mpm-analysis",
                metadata={"analysis_type": analysis_results["type"]}
            )
```

## Best Practices

### 1. Use Context Managers

Always use async context managers for automatic cleanup:

```python
# ✅ CORRECT: Context manager handles cleanup
async with KuzuMemoryClient(project_root) as client:
    await client.learn("content")

# ❌ WRONG: Manual cleanup prone to errors
client = KuzuMemoryClient(project_root)
await client.__aenter__()
try:
    await client.learn("content")
finally:
    await client.__aexit__(None, None, None)
```

### 2. Set Appropriate Timeouts

For production systems, set timeouts to prevent hangs:

```python
import asyncio

async def safe_memory_operation():
    async with asyncio.timeout(5.0):  # 5 second timeout
        async with KuzuMemoryClient(project_root) as client:
            memories = await client.recall("query")
            return memories
```

### 3. Batch Operations for Performance

When storing multiple memories, use batch operations:

```python
# ✅ CORRECT: Single batch operation
memories = [Memory(content=f"Item {i}") for i in range(100)]
await client.batch_store_memories(memories)

# ❌ WRONG: 100 separate operations
for i in range(100):
    await client.learn(f"Item {i}")  # Inefficient
```

### 4. Handle Errors Gracefully

```python
from kuzu_memory import KuzuMemoryClient

async def safe_recall(client: KuzuMemoryClient, query: str):
    """Recall with error handling."""
    try:
        memories = await client.recall(query)
        return memories
    except RuntimeError as e:
        print(f"Memory recall failed: {e}")
        return []  # Return empty list on error
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
```

### 5. Use Meaningful Sources and Metadata

Help future retrieval by using descriptive sources:

```python
# ✅ CORRECT: Descriptive source and metadata
await client.learn(
    "User prefers dark mode",
    source="user-preferences",
    metadata={
        "category": "ui-preferences",
        "confidence": 1.0,
        "timestamp": datetime.now().isoformat()
    }
)

# ❌ WRONG: Generic source, no metadata
await client.learn("User prefers dark mode", source="api")
```

### 6. Monitor Database Size

For long-running applications, monitor database growth:

```python
async def check_memory_health(client: KuzuMemoryClient):
    """Check memory system health."""
    stats = client.get_stats()

    db_size_mb = stats['database_size_bytes'] / (1024 * 1024)
    memory_count = stats['memory_count']

    print(f"Database size: {db_size_mb:.2f} MB")
    print(f"Memory count: {memory_count}")

    # Alert if database is too large
    if db_size_mb > 100:  # 100 MB threshold
        print("⚠️  Warning: Database size exceeding 100 MB")
        # Consider cleanup
        cleaned = await client.cleanup_expired_memories()
        print(f"Cleaned up {cleaned} expired memories")
```

### 7. Separate Concerns in Subservient Mode

When using subservient mode, clearly separate hook management from memory operations:

```python
class Framework:
    """Parent framework managing multiple tools."""

    async def setup(self):
        # Enable subservient mode for kuzu-memory
        enable_subservient_mode(self.project_root, managed_by="framework")

        # Install framework's centralized hooks
        self.install_hooks()  # Framework responsibility

        # Initialize memory client
        self.memory = KuzuMemoryClient(self.project_root)
        await self.memory.__aenter__()

    def install_hooks(self):
        """Framework manages hooks, not kuzu-memory."""
        # Install git hooks
        # Install file watchers
        # Install session hooks
        # etc.
```

## Troubleshooting

### Issue: Client not initialized error

```python
# ❌ ERROR: Client used outside context manager
client = KuzuMemoryClient(project_root)
await client.learn("content")  # RuntimeError!

# ✅ FIX: Use context manager
async with KuzuMemoryClient(project_root) as client:
    await client.learn("content")
```

### Issue: Database locked errors

Multiple clients trying to access same database:

```python
# ✅ FIX: Use one client per process/thread
class MyApp:
    def __init__(self):
        self._client = None

    async def start(self):
        # Single client for app lifetime
        self._client = KuzuMemoryClient(project_root)
        await self._client.__aenter__()

    async def stop(self):
        await self._client.__aexit__(None, None, None)
```

### Issue: Subservient mode not detected

```python
from kuzu_memory import is_subservient_mode
from pathlib import Path

project_root = Path("/path/to/project")

# Check detection
if not is_subservient_mode(project_root):
    print("Subservient mode not detected")

    # Enable it
    enable_subservient_mode(project_root, managed_by="my-framework")

    # Verify
    assert is_subservient_mode(project_root), "Failed to enable"
```

## Additional Resources

- [KuzuMemory README](../README.md) - Installation and quick start
- [CLAUDE.md](../CLAUDE.md) - Development guide
- [Kùzu Database Docs](https://kuzudb.com/docs/) - Graph database reference
- [Python asyncio Docs](https://docs.python.org/3/library/asyncio.html) - Async patterns

## Support

For questions or issues:

- GitHub Issues: https://github.com/bobmatnyc/kuzu-memory/issues
- Discussions: https://github.com/bobmatnyc/kuzu-memory/discussions
