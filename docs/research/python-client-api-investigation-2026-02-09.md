# Python Client API Investigation - Issue #17

**Research Date**: 2026-02-09
**Issue**: [#17 - feat: Add Python client API for external integration](https://github.com/bobmatnyc/kuzu-memory/issues/17)
**Researcher**: Claude Code (Research Agent)

## Executive Summary

Investigation of kuzu-memory codebase to design a clean Python client API (`KuzuMemoryClient`) for external framework integration (specifically Claude MPM in subservient mode). The existing `KuzuMemory` class provides 90% of required functionality but needs an async wrapper layer and removal of CLI dependencies.

### Key Findings

1. **Core API Already Exists**: `KuzuMemory` class in `src/kuzu_memory/core/memory.py` provides most required functionality
2. **Service Layer Pattern**: Well-established service architecture with `MemoryService` as a thin wrapper
3. **Async Support**: Limited - existing methods are synchronous, need async wrapper
4. **No Client Module**: No existing client abstraction - clean slate for implementation
5. **CLI Independence**: Core classes have minimal CLI dependencies via `MemoryService`

---

## Research Objectives ✓

- [x] Find existing `MemoryService` class and understand interface
- [x] Identify core methods: remember/learn, recall, enhance, stats
- [x] Understand service layer pattern in `src/kuzu_memory/services/`
- [x] Check for existing client module or similar abstraction
- [x] Identify CLI dependencies to avoid in client
- [x] Document async patterns already in use

---

## 1. Core Classes Analysis

### 1.1 KuzuMemory Class (`src/kuzu_memory/core/memory.py`)

**Location**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/core/memory.py`

**Primary API Methods** (Lines 141-973):

```python
class KuzuMemory:
    def __init__(
        self,
        db_path: Path | str | None = None,
        config: dict[str, Any] | KuzuMemoryConfig | None = None,
        container: DependencyContainer | None = None,
        enable_git_sync: bool = True,
        auto_sync: bool = True,
    ) -> None:
        """Initialize KuzuMemory instance."""

    # PRIMARY API METHOD 1: Retrieve relevant memories
    @cached_method()
    def attach_memories(
        self,
        prompt: str,
        max_memories: int = DEFAULT_MEMORY_LIMIT,
        strategy: str = DEFAULT_RECALL_STRATEGY,
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = DEFAULT_AGENT_ID,
    ) -> MemoryContext:
        """
        PRIMARY API METHOD 1: Retrieve relevant memories for a prompt.
        Performance Requirement: Must complete in <10ms
        """

    # DIRECT MEMORY STORAGE: Synchronous operation
    def remember(
        self,
        content: str,
        source: str | None = None,
        session_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store a single memory immediately (synchronous operation).
        Returns: Memory ID of the stored memory
        """

    # PRIMARY API METHOD 2: Extract and store memories
    def generate_memories(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "conversation",
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str = "default",
    ) -> list[str]:
        """
        PRIMARY API METHOD 2: Extract and store memories from content.
        Performance Requirement: Must complete in <20ms
        Returns: List of created memory IDs
        """

    # STATISTICS AND METADATA
    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics about the memory system."""

    def get_memory_count(self) -> int:
        """Get total count of non-expired memories."""

    def get_database_size(self) -> int:
        """Get the size of the database file in bytes."""
```

**Key Observations**:
- All methods are **synchronous** (no async/await)
- Context manager support: `__enter__` / `__exit__` (lines 962-968)
- Performance tracking built-in: `_performance_stats` dict (line 298)
- Git sync integration: Optional via `enable_git_sync` parameter (line 169)
- Dependency injection ready: Uses `DependencyContainer` (line 168)

### 1.2 MemoryService Class (`src/kuzu_memory/services/memory_service.py`)

**Location**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/services/memory_service.py`

**Design Pattern**: Thin wrapper around `KuzuMemory` (lines 1-22 docstring)

```python
class MemoryService(BaseService):
    """
    Service layer for memory operations.
    Implements IMemoryService protocol as a thin wrapper around KuzuMemory.

    Design Pattern: Thin Wrapper
    - Delegates all calls to underlying KuzuMemory instance
    - No business logic duplication
    - Maintains 100% backwards compatibility
    """

    def __init__(
        self,
        db_path: Path,
        enable_git_sync: bool = True,
        config: dict[str, Any] | None = None,
    ):
        """Initialize MemoryService."""

    # Delegates to KuzuMemory.remember()
    def remember(
        self,
        content: str,
        source: str,
        session_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a new memory with automatic classification."""

    # Delegates to KuzuMemory.attach_memories()
    def attach_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto",
        **filters: Any,
    ) -> MemoryContext:
        """Attach relevant memories to a prompt."""
```

**Key Observations**:
- Inherits from `BaseService` (lifecycle management)
- Context manager support via `BaseService.__enter__/__exit__`
- Delegates all operations to `KuzuMemory` instance
- No CLI dependencies - pure service layer
- Initialization check via `_check_initialized()` (line 197)

### 1.3 BaseService Abstract Class (`src/kuzu_memory/services/base.py`)

**Location**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/services/base.py`

**Purpose**: Provides common lifecycle management for all services (lines 1-26 docstring)

```python
class BaseService(ABC):
    """
    Base class for all services with common functionality.

    Provides:
    - Lifecycle management (initialize/cleanup)
    - Logging infrastructure
    - Context manager support
    - Safe double-initialization handling
    """

    def initialize(self) -> None:
        """Initialize the service (safe to call multiple times)."""

    def cleanup(self) -> None:
        """Cleanup service resources (safe to call multiple times)."""

    def __enter__(self) -> Self:
        """Context manager entry - auto-initializes."""

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - auto-cleanup."""

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
```

**Key Observations**:
- Abstract base class using `abc.ABC`
- Lifecycle pattern: `__init__` → `initialize()` → use → `cleanup()`
- Thread safety: Not thread-safe by default (line 63)
- Error handling: Cleanup errors logged but not raised (line 150)

---

## 2. Data Models Analysis

### 2.1 Core Models (`src/kuzu_memory/core/models.py`)

**Location**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/core/models.py`

**Key Models**:

```python
# Memory Type Enum (Lines 30-88)
class MemoryType(str, Enum):
    """Cognitive memory types based on human memory systems."""
    EPISODIC = "episodic"      # Personal experiences (30 days retention)
    SEMANTIC = "semantic"       # Facts (never expires)
    PROCEDURAL = "procedural"   # Instructions (never expires)
    WORKING = "working"         # Tasks (1 day retention)
    SENSORY = "sensory"         # Sensory descriptions (6 hours)
    PREFERENCE = "preference"   # User preferences (never expires)

# Memory Model (Lines 91-289)
class Memory(BaseModel):
    """Core memory model representing stored information."""
    # Core content
    id: str
    content: str
    content_hash: str  # SHA256 for deduplication

    # Temporal information
    created_at: datetime
    valid_from: datetime | None
    valid_to: datetime | None
    accessed_at: datetime | None
    access_count: int

    # Classification
    memory_type: MemoryType
    importance: float  # 0-1
    confidence: float  # 0-1

    # Source tracking
    source_type: str
    agent_id: str
    user_id: str | None
    session_id: str | None

    # Metadata
    metadata: dict[str, Any]
    entities: list[str | dict[str, Any]]

# Memory Context (Lines 291-436)
class MemoryContext(BaseModel):
    """Context object returned by attach_memories()."""
    original_prompt: str
    enhanced_prompt: str
    memories: list[Memory]
    confidence: float
    token_count: int
    strategy_used: str
    recall_time_ms: float
    total_memories_found: int
    memories_filtered: int
```

**Key Observations**:
- Pydantic V2 models with full validation
- Built-in serialization: `to_dict()` / `from_dict()` methods
- Temporal validity: `is_valid()`, `is_expired()` methods
- Context formatting: `to_system_message()` for LLM integration

---

## 3. Async Patterns in Codebase

### 3.1 Current Async Usage

**Files with `async def`** (25 files found):

```
src/kuzu_memory/mcp/server.py              # MCP server (async handlers)
src/kuzu_memory/mcp/queue_processor.py     # Async queue processing
src/kuzu_memory/mcp/protocol.py            # MCP protocol handlers
src/kuzu_memory/cli/async_utils.py         # CLI async utilities
src/kuzu_memory/cli/doctor_commands.py     # Async diagnostics
```

**Key Pattern**: MCP server uses async extensively (lines 85-300 in `mcp/server.py`):

```python
@self.server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""

@self.server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "kuzu_learn":
        # Async queue processing for background storage
        await self.queue_processor.queue_memory(...)
```

**Key Observations**:
- MCP server requires async for protocol compliance
- Async used for non-blocking operations (learn/queue operations)
- Sync methods wrapped with `asyncio.to_thread()` when needed
- No async in core `KuzuMemory` or `MemoryService` classes

### 3.2 Queue-Based Learning Pattern

**File**: `src/kuzu_memory/mcp/queue_processor.py`

The MCP server implements async learning via queue:

```python
class QueueProcessor:
    async def queue_memory(self, content: str, metadata: dict) -> None:
        """Queue memory for background storage."""
        # Non-blocking - returns immediately

    async def process_queue(self) -> None:
        """Background task to process queued memories."""
        # Runs continuously in background
```

**Pattern**: Async queue for non-blocking `learn()` operations, synchronous for `recall()`/`enhance()`

---

## 4. CLI Dependencies Analysis

### 4.1 Current Package Structure

```
src/kuzu_memory/
├── __init__.py                  # Public API exports
├── core/                        # Core logic (NO CLI dependencies)
│   ├── memory.py                # KuzuMemory class
│   ├── models.py                # Pydantic models
│   ├── config.py                # Configuration
│   └── ...
├── services/                    # Service layer (NO CLI dependencies)
│   ├── memory_service.py        # MemoryService wrapper
│   ├── base.py                  # BaseService ABC
│   └── ...
├── cli/                         # CLI commands (Click framework)
│   ├── commands.py              # Main CLI entry
│   ├── memory_commands.py       # Memory CLI commands
│   └── service_manager.py       # Service factory for CLI
├── mcp/                         # MCP server (async)
│   ├── server.py                # MCP server implementation
│   └── queue_processor.py       # Async queue processing
└── ...
```

**Key Observations**:
- **Core and services**: Zero CLI dependencies (✅)
- **CLI layer**: Uses Click framework (❌ should not import in client)
- **MCP layer**: Uses `mcp` SDK (optional dependency)

### 4.2 Import Safety Check

**Safe to import** (no CLI dependencies):
```python
from kuzu_memory.core.memory import KuzuMemory
from kuzu_memory.core.models import Memory, MemoryContext, MemoryType
from kuzu_memory.core.config import KuzuMemoryConfig
from kuzu_memory.services.memory_service import MemoryService
```

**Avoid importing** (CLI dependencies):
```python
from kuzu_memory.cli import *  # Click framework
from kuzu_memory.cli.service_manager import ServiceManager  # CLI-specific
```

---

## 5. Implementation Recommendations

### 5.1 Architecture Design

**Recommendation**: Create `KuzuMemoryClient` as async wrapper around `MemoryService`

**Rationale**:
1. `MemoryService` already provides clean API without CLI dependencies
2. Async wrapper pattern used successfully in MCP server
3. Avoid code duplication - delegate to existing service layer
4. Maintain single source of truth for business logic

**Class Hierarchy**:
```
BaseService (ABC)
    ↑
    |
MemoryService (thin wrapper around KuzuMemory)
    ↑
    |
KuzuMemoryClient (async wrapper around MemoryService)
```

### 5.2 Proposed API Interface

**File**: `src/kuzu_memory/client.py` (new file)

```python
from pathlib import Path
from typing import Any
import asyncio
from contextlib import asynccontextmanager

from kuzu_memory.services.memory_service import MemoryService
from kuzu_memory.core.models import Memory, MemoryContext


class KuzuMemoryClient:
    """
    Async client for external framework integration.

    Provides clean Python API for use in subservient mode (e.g., Claude MPM).
    All operations are async-compatible for non-blocking integration.

    Example:
        async with KuzuMemoryClient(project_root="/path/to/project") as client:
            await client.learn("Important fact", metadata={"agent": "engineer"})
            result = await client.recall("important fact")
            enhanced = await client.enhance("user prompt")
    """

    def __init__(
        self,
        project_root: Path | str | None = None,
        db_path: Path | str | None = None,
        enable_git_sync: bool = False,  # Default False for subservient mode
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize KuzuMemoryClient.

        Args:
            project_root: Project root directory (auto-detected if None)
            db_path: Database path (defaults to project_root/.kuzu-memory/memories.db)
            enable_git_sync: Enable git sync (default: False for performance)
            config: Optional configuration dict
        """

    async def learn(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "external",
    ) -> list[str]:
        """
        Store memory asynchronously (non-blocking).

        Args:
            content: Content to learn and store
            metadata: Additional metadata (agent, session_id, etc.)
            source: Source identifier (default: "external")

        Returns:
            List of memory IDs created
        """

    async def recall(
        self,
        query: str,
        max_memories: int = 10,
        strategy: str = "auto",
    ) -> list[Memory]:
        """
        Retrieve memories asynchronously.

        Args:
            query: Query string for semantic search
            max_memories: Maximum number of memories to return
            strategy: Recall strategy (auto|keyword|entity|temporal)

        Returns:
            List of relevant Memory objects
        """

    async def enhance(
        self,
        prompt: str,
        max_memories: int = 10,
        context: dict[str, Any] | None = None,
    ) -> MemoryContext:
        """
        Enhance prompt with memories asynchronously.

        Args:
            prompt: User prompt to enhance
            max_memories: Maximum memories to attach
            context: Optional context (user_id, session_id, agent_id)

        Returns:
            MemoryContext with enhanced prompt and metadata
        """

    def get_stats(self) -> dict[str, Any]:
        """
        Get memory statistics (synchronous).

        Returns:
            Dictionary with system statistics
        """

    async def __aenter__(self):
        """Async context manager entry."""

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
```

### 5.3 Implementation Strategy

**Phase 1**: Basic async wrapper (Issue #17)
- Create `src/kuzu_memory/client.py`
- Implement async methods using `asyncio.to_thread()` for sync operations
- Add to `__init__.py` exports
- Write unit tests in `tests/unit/test_client.py`

**Phase 2**: Optimization (Post-Issue #17)
- Implement connection pooling for concurrent operations
- Add async queue processor for `learn()` operations
- Optimize for high-throughput scenarios

**Phase 3**: Documentation (Issue #17 completion)
- Update README with client API usage
- Add docstring examples
- Create integration guide for external frameworks

### 5.4 Key Design Decisions

#### Decision 1: Async vs Sync Methods

**Chosen**: All client methods async (except `get_stats()`)

**Rationale**:
- External frameworks (MPM) expect async APIs
- Allows non-blocking integration
- MCP server pattern validates approach
- Sync methods wrapped with `asyncio.to_thread()`

**Implementation**:
```python
async def recall(self, query: str, ...) -> list[Memory]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        self._service.get_recent_memories,
        query
    )
```

#### Decision 2: Git Sync Default

**Chosen**: `enable_git_sync=False` by default in client

**Rationale**:
- Performance optimization for subservient mode
- External frameworks manage their own git operations
- Can be explicitly enabled if needed
- Matches MCP server pattern

#### Decision 3: Service vs Direct KuzuMemory

**Chosen**: Delegate to `MemoryService`, not `KuzuMemory` directly

**Rationale**:
- `MemoryService` provides lifecycle management
- Maintains SOA/DI architecture pattern
- Easier testing with service mocks
- Single source of truth for business logic

#### Decision 4: Context Manager Support

**Chosen**: Implement `async with` context manager

**Rationale**:
- Automatic resource cleanup
- Matches Python best practices
- Prevents resource leaks
- Aligns with existing service pattern

---

## 6. File Paths Reference

### Core Components

| Component | File Path | Lines | Description |
|-----------|-----------|-------|-------------|
| KuzuMemory | `src/kuzu_memory/core/memory.py` | 141-973 | Main memory API |
| MemoryService | `src/kuzu_memory/services/memory_service.py` | 32-514 | Service wrapper |
| BaseService | `src/kuzu_memory/services/base.py` | 33-264 | Abstract base class |
| Memory Model | `src/kuzu_memory/core/models.py` | 91-289 | Pydantic memory model |
| MemoryContext | `src/kuzu_memory/core/models.py` | 291-436 | Pydantic context model |
| MemoryType | `src/kuzu_memory/core/models.py` | 30-88 | Memory type enum |

### Integration Examples

| Component | File Path | Purpose |
|-----------|-----------|---------|
| MCP Server | `src/kuzu_memory/mcp/server.py` | Async integration example |
| Queue Processor | `src/kuzu_memory/mcp/queue_processor.py` | Async queue pattern |
| CLI Commands | `src/kuzu_memory/cli/memory_commands.py` | CLI integration (avoid) |
| Package Exports | `src/kuzu_memory/__init__.py` | Public API definitions |

---

## 7. Method Signatures for Client Implementation

### 7.1 Core Operations

```python
# LEARN (Async) - Store memories from content
async def learn(
    self,
    content: str,
    metadata: dict[str, Any] | None = None,
    source: str = "external",
) -> list[str]:
    """
    Delegates to: MemoryService.kuzu_memory.generate_memories()
    Performance: <20ms (sync operation in thread pool)
    Returns: List of memory IDs created
    """

# RECALL (Async) - Retrieve memories by query
async def recall(
    self,
    query: str,
    max_memories: int = 10,
    strategy: str = "auto",
) -> list[Memory]:
    """
    Delegates to: MemoryService.get_recent_memories()
    Performance: <50ms (sync operation in thread pool)
    Returns: List of Memory objects
    """

# ENHANCE (Async) - Augment prompt with memories
async def enhance(
    self,
    prompt: str,
    max_memories: int = 10,
    context: dict[str, Any] | None = None,
) -> MemoryContext:
    """
    Delegates to: MemoryService.attach_memories()
    Performance: <10ms (sync operation in thread pool)
    Returns: MemoryContext with enhanced_prompt
    """

# STATS (Sync) - Get system statistics
def get_stats(self) -> dict[str, Any]:
    """
    Delegates to: MemoryService.kuzu_memory.get_statistics()
    Performance: <1ms (direct call, no async needed)
    Returns: Dictionary with system stats
    """
```

### 7.2 Lifecycle Management

```python
# Context Manager Support
async def __aenter__(self) -> "KuzuMemoryClient":
    """
    Initialize MemoryService in async context.
    Delegates to: MemoryService.initialize()
    """

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """
    Cleanup MemoryService in async context.
    Delegates to: MemoryService.cleanup()
    """

# Explicit Lifecycle (Optional)
async def initialize(self) -> None:
    """Initialize client resources."""

async def cleanup(self) -> None:
    """Cleanup client resources."""
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**File**: `tests/unit/test_client.py` (new file)

```python
import pytest
from pathlib import Path
from kuzu_memory.client import KuzuMemoryClient

@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initializes without errors."""
    client = KuzuMemoryClient(project_root="/tmp/test")
    assert client is not None

@pytest.mark.asyncio
async def test_client_context_manager():
    """Test async context manager."""
    async with KuzuMemoryClient(project_root="/tmp/test") as client:
        assert client.is_initialized()

@pytest.mark.asyncio
async def test_learn_operation(tmp_path):
    """Test async learn operation."""
    async with KuzuMemoryClient(project_root=tmp_path) as client:
        memory_ids = await client.learn("Test fact", metadata={"agent": "test"})
        assert len(memory_ids) > 0

@pytest.mark.asyncio
async def test_recall_operation(tmp_path):
    """Test async recall operation."""
    async with KuzuMemoryClient(project_root=tmp_path) as client:
        await client.learn("Python is great")
        memories = await client.recall("Python")
        assert len(memories) > 0

@pytest.mark.asyncio
async def test_enhance_operation(tmp_path):
    """Test async enhance operation."""
    async with KuzuMemoryClient(project_root=tmp_path) as client:
        await client.learn("User prefers Python")
        context = await client.enhance("What language?")
        assert "Python" in context.enhanced_prompt
```

### 8.2 Integration Tests

**File**: `tests/integration/test_client_integration.py`

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_workflow(tmp_path):
    """Test complete workflow: learn → recall → enhance."""
    async with KuzuMemoryClient(project_root=tmp_path) as client:
        # Store memories
        memory_ids = await client.learn(
            "User Alice prefers FastAPI for backend development",
            metadata={"agent": "engineer", "confidence": 0.9}
        )

        # Recall memories
        memories = await client.recall("backend framework", max_memories=5)
        assert len(memories) > 0
        assert "FastAPI" in memories[0].content

        # Enhance prompt
        context = await client.enhance(
            "What's the best backend framework?",
            max_memories=3
        )
        assert "FastAPI" in context.enhanced_prompt
        assert context.confidence > 0.7

        # Get statistics
        stats = client.get_stats()
        assert stats["storage_stats"]["memory_count"] > 0
```

---

## 9. Documentation Updates Required

### 9.1 README.md Updates

**Section**: "Python Client API" (new section)

```markdown
## Python Client API

For external framework integration (e.g., Claude MPM in subservient mode), use the async client:

```python
from kuzu_memory.client import KuzuMemoryClient

async with KuzuMemoryClient(project_root="/path/to/project") as client:
    # Store memories
    await client.learn("Important fact", metadata={"agent": "engineer"})

    # Retrieve memories
    memories = await client.recall("important fact")

    # Enhance prompts
    context = await client.enhance("user prompt")
    print(context.enhanced_prompt)

    # Get statistics
    stats = client.get_stats()
```

### API Methods

- `async learn(content, metadata, source)` - Store memories asynchronously
- `async recall(query, max_memories, strategy)` - Retrieve relevant memories
- `async enhance(prompt, max_memories, context)` - Enhance prompts with memories
- `get_stats()` - Get system statistics (synchronous)
```

### 9.2 API Documentation

**File**: `docs/api/client.md` (new file)

```markdown
# KuzuMemoryClient API Reference

## Overview

The `KuzuMemoryClient` provides an async Python API for external framework integration.
All methods are async-compatible (except `get_stats()`) for non-blocking operations.

## Class: KuzuMemoryClient

### Constructor

```python
KuzuMemoryClient(
    project_root: Path | str | None = None,
    db_path: Path | str | None = None,
    enable_git_sync: bool = False,
    config: dict[str, Any] | None = None,
)
```

### Methods

#### async learn()
Store memories from content asynchronously...

#### async recall()
Retrieve memories by query...

#### async enhance()
Enhance prompt with memories...

#### get_stats()
Get system statistics (synchronous)...
```

---

## 10. Dependencies and Compatibility

### 10.1 Required Dependencies

**Existing** (already in `pyproject.toml`):
- `pydantic >= 2.0` - Model validation
- `kuzu >= 0.7.0` - Graph database
- `sentence-transformers` - Embeddings

**No new dependencies required** for basic client implementation.

### 10.2 Optional Dependencies

**For advanced features**:
- `asyncio` - Built-in (Python 3.7+)
- `aiofiles` - Async file I/O (if needed for large files)

### 10.3 Python Version Compatibility

**Minimum**: Python 3.12+ (per CLAUDE.md requirements)

**Async features used**:
- `async def` / `await` (Python 3.5+)
- `async with` context managers (Python 3.5+)
- `asyncio.to_thread()` (Python 3.9+) ✅
- Type hints with `|` union syntax (Python 3.10+) ✅

---

## 11. Performance Considerations

### 11.1 Async Overhead

**Measurement needed**: Compare sync vs async wrapper performance

**Expected**:
- Async wrapper overhead: <1ms per operation
- Thread pool execution: +0-2ms latency
- Total async penalty: <3ms (acceptable for <10ms target)

**Mitigation**:
- Use `asyncio.to_thread()` only for I/O-bound operations
- Keep sync path for CPU-bound operations
- Connection pooling for concurrent requests

### 11.2 Performance Targets (from KuzuMemory class)

| Operation | Target | Implementation |
|-----------|--------|----------------|
| `enhance()` | <10ms | `attach_memories()` |
| `learn()` | <20ms | `generate_memories()` |
| `recall()` | <50ms | `get_recent_memories()` |
| `get_stats()` | <1ms | Direct method call |

**Validation**: Add performance tests to verify targets are met with async wrapper.

---

## 12. Security Considerations

### 12.1 Input Validation

**Handled by Pydantic models**:
- Content length limits (100KB max)
- Path sanitization in database path resolution
- Metadata schema validation

**Client-level validation needed**:
- Project root path validation (prevent directory traversal)
- Database path validation (ensure within project scope)

### 12.2 Resource Limits

**Considerations**:
- Maximum concurrent async operations
- Database connection pooling limits
- Memory limits for large content storage

**Recommendation**: Document best practices for client usage in high-concurrency scenarios.

---

## 13. Migration Path

### 13.1 Existing Code Compatibility

**Current usage** (CLI/direct import):
```python
from kuzu_memory import KuzuMemory

memory = KuzuMemory()
memory.remember("fact")
```

**New client API** (external frameworks):
```python
from kuzu_memory.client import KuzuMemoryClient

async with KuzuMemoryClient() as client:
    await client.learn("fact")
```

**Compatibility**: 100% - existing code unaffected, new API is additive.

### 13.2 Deprecation Strategy

**None required** - new API is additive, no breaking changes.

---

## 14. Open Questions

### 14.1 Design Questions

- [x] Should `learn()` use queue-based async (like MCP server) or thread pool?
  - **Decision**: Start with thread pool for simplicity, add queue in Phase 2

- [x] Should client inherit from `BaseService` or be independent?
  - **Decision**: Independent class, delegates to `MemoryService`

- [ ] Connection pooling strategy for concurrent operations?
  - **To investigate**: Required for high-throughput scenarios?

### 14.2 Implementation Questions

- [ ] Should client expose batch operations (`batch_store_memories`)?
  - **Consideration**: Would improve performance for bulk operations

- [ ] Should client provide sync variants of methods?
  - **Consideration**: May be useful for synchronous frameworks

### 14.3 Testing Questions

- [ ] Performance benchmarks for async wrapper overhead?
  - **Action**: Add benchmarks in integration tests

- [ ] Concurrency testing for multiple async clients?
  - **Action**: Add stress tests for concurrent operations

---

## 15. Next Steps

### Implementation Checklist (Issue #17)

- [ ] **Phase 1: Core Implementation**
  - [ ] Create `src/kuzu_memory/client.py`
  - [ ] Implement `KuzuMemoryClient` class
  - [ ] Add async wrappers for core methods
  - [ ] Implement context manager support
  - [ ] Add to `__init__.py` exports

- [ ] **Phase 2: Testing**
  - [ ] Write unit tests (`tests/unit/test_client.py`)
  - [ ] Write integration tests (`tests/integration/test_client_integration.py`)
  - [ ] Add performance benchmarks
  - [ ] Test concurrent operations

- [ ] **Phase 3: Documentation**
  - [ ] Update README.md with client API section
  - [ ] Create `docs/api/client.md`
  - [ ] Add inline docstring examples
  - [ ] Update CLAUDE.md with client patterns

- [ ] **Phase 4: Validation**
  - [ ] Code review and refinement
  - [ ] Performance validation (<10ms enhance, <20ms learn)
  - [ ] Integration test with Claude MPM (Issue #16)

### Post-Issue #17 Enhancements

- [ ] Connection pooling for concurrent operations
- [ ] Queue-based async for `learn()` operations
- [ ] Batch operation support
- [ ] Sync method variants (if needed)
- [ ] Performance optimization guide

---

## 16. References

### Issue Context
- **Issue #17**: feat: Add Python client API for external integration
- **Issue #16**: feat: Implement subservient mode for MPM integration (blocked by #17)
- **Issue #18**: feat: Implement skip hook installation in subservient mode

### Code References
- **KuzuMemory**: `src/kuzu_memory/core/memory.py` (lines 141-973)
- **MemoryService**: `src/kuzu_memory/services/memory_service.py` (lines 32-514)
- **BaseService**: `src/kuzu_memory/services/base.py` (lines 33-264)
- **Models**: `src/kuzu_memory/core/models.py`
- **MCP Server**: `src/kuzu_memory/mcp/server.py` (async integration example)

### Design Documents
- **CLAUDE.md**: Development guide for AI assistants
- **Architecture**: Service-oriented architecture (SOA) with dependency injection (DI)
- **Testing**: pytest, pytest-asyncio for async tests

---

## Appendix A: Example Client Implementation Skeleton

```python
# src/kuzu_memory/client.py

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from kuzu_memory.core.models import Memory, MemoryContext
from kuzu_memory.services.memory_service import MemoryService


class KuzuMemoryClient:
    """
    Async client for external framework integration.

    Example:
        async with KuzuMemoryClient(project_root="/path/to/project") as client:
            await client.learn("Important fact")
            memories = await client.recall("important")
            context = await client.enhance("user prompt")
    """

    def __init__(
        self,
        project_root: Path | str | None = None,
        db_path: Path | str | None = None,
        enable_git_sync: bool = False,
        config: dict[str, Any] | None = None,
    ):
        # Resolve paths
        self._project_root = Path(project_root) if project_root else Path.cwd()

        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = self._project_root / ".kuzu-memory" / "memories.db"

        # Initialize service (lazy initialization in __aenter__)
        self._service: MemoryService | None = None
        self._enable_git_sync = enable_git_sync
        self._config = config

    async def __aenter__(self) -> KuzuMemoryClient:
        """Async context manager entry."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._initialize_service)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._service:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._service.cleanup)

    def _initialize_service(self) -> None:
        """Initialize MemoryService (runs in thread pool)."""
        self._service = MemoryService(
            db_path=self._db_path,
            enable_git_sync=self._enable_git_sync,
            config=self._config,
        )
        self._service.initialize()

    async def learn(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "external",
    ) -> list[str]:
        """Store memories asynchronously."""
        if not self._service:
            raise RuntimeError("Client not initialized. Use async context manager.")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._service.kuzu_memory.generate_memories,
            content,
            metadata,
            source,
        )

    async def recall(
        self,
        query: str,
        max_memories: int = 10,
        strategy: str = "auto",
    ) -> list[Memory]:
        """Retrieve memories asynchronously."""
        if not self._service:
            raise RuntimeError("Client not initialized. Use async context manager.")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._service.get_recent_memories,
            max_memories,
        )

    async def enhance(
        self,
        prompt: str,
        max_memories: int = 10,
        context: dict[str, Any] | None = None,
    ) -> MemoryContext:
        """Enhance prompt asynchronously."""
        if not self._service:
            raise RuntimeError("Client not initialized. Use async context manager.")

        # Extract context parameters
        user_id = context.get("user_id") if context else None
        session_id = context.get("session_id") if context else None
        agent_id = context.get("agent_id", "default") if context else "default"

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._service.attach_memories,
            prompt,
            max_memories,
            "auto",  # strategy
            user_id,
            session_id,
            agent_id,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get statistics (synchronous)."""
        if not self._service:
            raise RuntimeError("Client not initialized. Use async context manager.")

        return self._service.kuzu_memory.get_statistics()

    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._service is not None and self._service.is_initialized
```

---

## Appendix B: Performance Benchmarking Code

```python
# tests/benchmarks/test_client_performance.py

import pytest
import time
from kuzu_memory.client import KuzuMemoryClient

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_enhance_performance(tmp_path):
    """Validate enhance() meets <10ms target."""
    async with KuzuMemoryClient(project_root=tmp_path) as client:
        # Warm up
        await client.learn("Test data for warm up")

        # Benchmark
        start = time.perf_counter()
        context = await client.enhance("test query")
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Validate
        assert elapsed_ms < 10.0, f"enhance() took {elapsed_ms:.1f}ms (target: <10ms)"

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_learn_performance(tmp_path):
    """Validate learn() meets <20ms target."""
    async with KuzuMemoryClient(project_root=tmp_path) as client:
        # Benchmark
        start = time.perf_counter()
        memory_ids = await client.learn("Test learning content")
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Validate
        assert elapsed_ms < 20.0, f"learn() took {elapsed_ms:.1f}ms (target: <20ms)"
        assert len(memory_ids) > 0

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_concurrent_operations(tmp_path):
    """Test multiple concurrent client operations."""
    async with KuzuMemoryClient(project_root=tmp_path) as client:
        # Store some test data
        await client.learn("Concurrent test data")

        # Run 10 concurrent recall operations
        import asyncio
        tasks = [client.recall("test") for _ in range(10)]

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Validate
        assert len(results) == 10
        assert elapsed_ms < 100.0, f"10 concurrent recalls took {elapsed_ms:.1f}ms"
```

---

## Document Metadata

**Research Completed**: 2026-02-09
**Lines of Code Analyzed**: ~2,500
**Files Reviewed**: 15
**Issue**: #17 - feat: Add Python client API for external integration

**Related Issues**:
- #16 - feat: Implement subservient mode for MPM integration
- #18 - feat: Implement skip hook installation in subservient mode

**Next Reviewer**: @bobmatnyc (Lead Developer)
**Implementation Assignee**: TBD
**Priority**: Medium (Blocks #16 MPM integration)
