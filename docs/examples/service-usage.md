# Service Usage Examples

**Ticket**: 1M-428 (Update Architecture and Usage Documentation)
**Epic**: 1M-415 (SOA/DI Refactoring)
**Last Updated**: 2025-11-30

---

## Table of Contents

1. [Basic Memory Operations](#basic-memory-operations)
2. [Multi-Service Orchestration](#multi-service-orchestration)
3. [Async Service Usage](#async-service-usage)
4. [Error Handling Patterns](#error-handling-patterns)
5. [Testing with Services](#testing-with-services)
6. [Advanced Patterns](#advanced-patterns)

---

## Basic Memory Operations

### Example 1: Simple Memory Recall

```python
from kuzu_memory.cli.service_manager import ServiceManager

def recall_memories(query: str, limit: int = 10):
    """Retrieve relevant memories for a query."""
    with ServiceManager.memory_service() as memory:
        # Attach relevant memories to prompt
        context = memory.attach_memories(
            prompt=query,
            max_memories=limit,
            strategy="hybrid"
        )

        # Display results
        print(f"Found {len(context.memories)} relevant memories:")
        for mem in context.memories:
            print(f"  - [{mem.relevance:.2f}] {mem.content[:100]}")

        return context.memories

# Usage
results = recall_memories("What is the project structure?", limit=5)
```

**Output**:
```
Found 5 relevant memories:
  - [0.89] Project uses Python with Kuzu graph database for memory storage
  - [0.85] Main entry point is src/kuzu_memory/__main__.py
  - [0.82] CLI commands are in src/kuzu_memory/cli/
  - [0.78] Services layer provides SOA architecture
  - [0.75] Configuration stored in .kuzu-memory/config.json
```

---

### Example 2: Storing New Memories

```python
from kuzu_memory.cli.service_manager import ServiceManager

def store_learning(content: str, source: str = "cli"):
    """Store a new learning as a memory."""
    with ServiceManager.memory_service() as memory:
        # Store memory with automatic classification
        memory_id = memory.remember(
            content=content,
            source=source,
            session_id="example-session",
            metadata={
                "category": "learning",
                "importance": "high"
            }
        )

        print(f"✅ Memory stored with ID: {memory_id}")
        return memory_id

# Usage
memory_id = store_learning(
    content="User prefers async/await over callbacks for async code",
    source="conversation"
)
```

**Output**:
```
✅ Memory stored with ID: 550e8400-e29b-41d4-a716-446655440000
```

---

### Example 3: Recent Memories

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.core.models import MemoryType

def show_recent_memories(limit: int = 20, memory_type: str = None):
    """Display recent memories with optional type filter."""
    with ServiceManager.memory_service() as memory:
        # Parse memory type
        type_filter = None
        if memory_type:
            type_filter = MemoryType[memory_type.upper()]

        # Get recent memories
        recent = memory.get_recent_memories(
            limit=limit,
            memory_type=type_filter
        )

        # Display
        print(f"\n📝 Recent Memories ({len(recent)}):")
        for mem in recent:
            timestamp = mem.created_at.strftime("%Y-%m-%d %H:%M")
            print(f"  [{timestamp}] {mem.content[:80]}")

# Usage
show_recent_memories(limit=10, memory_type="episodic")
```

**Output**:
```
📝 Recent Memories (10):
  [2025-11-30 14:30] Implemented service layer architecture for Phase 5
  [2025-11-30 14:15] Fixed type errors in async_utils module
  [2025-11-30 13:45] Updated ServiceManager to support git sync
  [2025-11-30 13:20] Added diagnostic service for health checks
  [2025-11-30 12:50] Completed Phase 5.3 async command migrations
  ...
```

---

### Example 4: Memory Statistics

```python
from kuzu_memory.cli.service_manager import ServiceManager

def show_memory_stats():
    """Display memory database statistics."""
    with ServiceManager.memory_service() as memory:
        # Get statistics
        total_count = memory.get_memory_count()
        db_size = memory.get_database_size()

        # Format size
        size_mb = db_size / (1024 * 1024)

        print("\n📊 Memory Statistics:")
        print(f"  Total Memories: {total_count:,}")
        print(f"  Database Size: {size_mb:.2f} MB")

        # Breakdown by type
        from kuzu_memory.core.models import MemoryType
        print("\n  By Type:")
        for mem_type in MemoryType:
            count = memory.get_memory_count(memory_type=mem_type)
            print(f"    - {mem_type.value}: {count:,}")

# Usage
show_memory_stats()
```

**Output**:
```
📊 Memory Statistics:
  Total Memories: 1,245
  Database Size: 3.94 MB

  By Type:
    - episodic: 832
    - semantic: 305
    - procedural: 98
    - preference: 10
```

---

## Multi-Service Orchestration

### Example 5: Initialize Project with Git Sync

```python
from pathlib import Path
from kuzu_memory.services import ConfigService, SetupService

def initialize_project_with_git(project_root: Path, force: bool = False):
    """Initialize project and sync git history."""

    # Step 1: Initialize configuration
    config = ConfigService(project_root)
    config.initialize()

    # Step 2: Initialize setup service
    setup = SetupService(config)
    setup.initialize()

    try:
        # Step 3: Initialize project structure
        result = setup.initialize_project(
            force=force,
            git_sync=True,
            claude_desktop=False
        )

        if not result["success"]:
            print(f"❌ Setup failed: {result.get('error')}")
            return False

        print("✅ Project initialized successfully")
        print(f"   Steps: {', '.join(result['steps_completed'])}")

        # Step 4: Sync git history
        from kuzu_memory.cli.service_manager import ServiceManager

        with ServiceManager.git_sync_service(config) as git_sync:
            if git_sync.is_available():
                print("\n📦 Syncing git history...")
                count = git_sync.sync(max_commits=100)
                print(f"   Synced {count} commits")
            else:
                print("⚠️  Git not available, skipping sync")

        return True

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        return False
    finally:
        # Cleanup in reverse order
        setup.cleanup()
        config.cleanup()

# Usage
from kuzu_memory.utils.project_setup import find_project_root

project_root = find_project_root()
initialize_project_with_git(project_root, force=True)
```

**Output**:
```
✅ Project initialized successfully
   Steps: create_directories, initialize_database, create_config

📦 Syncing git history...
   Synced 121 commits
```

---

### Example 6: Health Check All Systems

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.cli.async_utils import run_async
from kuzu_memory.services import ConfigService

def run_full_health_check(project_root):
    """Run comprehensive health checks on all systems."""

    # Initialize config
    config = ConfigService(project_root)
    config.initialize()

    try:
        # Step 1: Check database
        print("🔍 Checking database health...")
        with ServiceManager.memory_service() as memory:
            count = memory.get_memory_count()
            size = memory.get_database_size()
            print(f"   ✅ Database healthy: {count} memories, {size/1024/1024:.2f} MB")

        # Step 2: Run diagnostics
        print("\n🔍 Running system diagnostics...")
        with ServiceManager.diagnostic_service(config) as diagnostic:
            result = run_async(diagnostic.run_full_diagnostics())

            if result["all_healthy"]:
                print("   ✅ All systems healthy")
            else:
                print("   ⚠️  Issues found:")
                for issue in result.get("issues", []):
                    print(f"      - {issue}")

        # Step 3: Check git sync
        print("\n🔍 Checking git integration...")
        with ServiceManager.git_sync_service(config) as git_sync:
            status = git_sync.get_sync_status()
            if status["enabled"]:
                print(f"   ✅ Git sync enabled, {status['commits_synced']} commits synced")
            else:
                print("   ⚠️  Git sync not enabled")

        return True

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    finally:
        config.cleanup()

# Usage
from kuzu_memory.utils.project_setup import find_project_root
project_root = find_project_root()
run_full_health_check(project_root)
```

**Output**:
```
🔍 Checking database health...
   ✅ Database healthy: 245 memories, 3.94 MB

🔍 Running system diagnostics...
   ✅ All systems healthy

🔍 Checking git integration...
   ✅ Git sync enabled, 121 commits synced
```

---

## Async Service Usage

### Example 7: MCP Server Diagnostics

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.cli.async_utils import run_async

def check_mcp_server():
    """Check MCP server health using async diagnostics."""
    with ServiceManager.diagnostic_service() as diagnostic:
        # Run async health check in sync context
        result = run_async(diagnostic.check_mcp_server_health())

        print("\n🔍 MCP Server Status:")
        print(f"   Configured: {'✅' if result['configured'] else '❌'}")
        print(f"   Config Valid: {'✅' if result.get('config_valid') else '❌'}")
        print(f"   Config Path: {result.get('server_path', 'N/A')}")

        if result.get("issues"):
            print("\n   Issues:")
            for issue in result["issues"]:
                print(f"      - {issue}")

        return result["configured"] and result.get("config_valid", False)

# Usage
is_healthy = check_mcp_server()
```

**Output**:
```
🔍 MCP Server Status:
   Configured: ✅
   Config Valid: ✅
   Config Path: /Users/user/Library/Application Support/Claude/claude_desktop_config.json
```

---

### Example 8: Database Health Check

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.cli.async_utils import run_async

def check_database_health():
    """Check database connectivity and health."""
    with ServiceManager.diagnostic_service() as diagnostic:
        # Run async database check
        result = run_async(diagnostic.check_database_health())

        print("\n🔍 Database Health:")
        print(f"   Connected: {'✅' if result['connected'] else '❌'}")
        print(f"   Memories: {result.get('memory_count', 0):,}")
        print(f"   Size: {result.get('db_size_bytes', 0) / 1024 / 1024:.2f} MB")
        print(f"   Schema: {result.get('schema_version', 'unknown')}")

        if result.get("issues"):
            print("\n   Issues:")
            for issue in result["issues"]:
                print(f"      - {issue}")

        return result["connected"]

# Usage
is_healthy = check_database_health()
```

**Output**:
```
🔍 Database Health:
   Connected: ✅
   Memories: 245
   Size: 3.94 MB
   Schema: v1.0.0
```

---

### Example 9: Full Diagnostics with Report

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.cli.async_utils import run_async

def run_diagnostics_with_report():
    """Run full diagnostics and display formatted report."""
    with ServiceManager.diagnostic_service() as diagnostic:
        # Run comprehensive diagnostics
        print("🔍 Running full diagnostics...\n")
        result = run_async(diagnostic.run_full_diagnostics())

        # Format and display report
        report = diagnostic.format_diagnostic_report(result)
        print(report)

        # Return summary
        return {
            "all_healthy": result["all_healthy"],
            "issues_count": len(result.get("issues", [])),
            "timestamp": result["timestamp"]
        }

# Usage
summary = run_diagnostics_with_report()
print(f"\n📊 Summary: {'✅ Healthy' if summary['all_healthy'] else '⚠️ Issues Found'}")
```

---

## Error Handling Patterns

### Example 10: Graceful Error Handling

```python
from kuzu_memory.cli.service_manager import ServiceManager
import click

def safe_memory_operation(query: str):
    """Handle errors gracefully during memory operations."""
    try:
        with ServiceManager.memory_service() as memory:
            results = memory.attach_memories(
                prompt=query,
                max_memories=10
            )

            click.echo(f"✅ Found {len(results.memories)} memories")
            return results

    except FileNotFoundError as e:
        click.echo(f"❌ Database not found: {e}", err=True)
        click.echo("💡 Run 'kuzu-memory init' to initialize", err=True)
        return None

    except PermissionError as e:
        click.echo(f"❌ Permission denied: {e}", err=True)
        click.echo("💡 Check database file permissions", err=True)
        return None

    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        return None

# Usage
results = safe_memory_operation("test query")
```

---

### Example 11: Cleanup on Exception

```python
from kuzu_memory.services import ConfigService, SetupService

def setup_with_cleanup(project_root):
    """Ensure cleanup even on exceptions."""
    config = ConfigService(project_root)
    config.initialize()

    setup = SetupService(config)
    setup.initialize()

    try:
        # Potentially failing operation
        result = setup.initialize_project(force=True)

        if not result["success"]:
            raise RuntimeError(f"Setup failed: {result.get('error')}")

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        # Re-raise after logging
        raise

    finally:
        # Cleanup ALWAYS runs
        print("🧹 Cleaning up...")
        setup.cleanup()
        config.cleanup()

# Usage
try:
    result = setup_with_cleanup(project_root)
except Exception:
    pass  # Already handled
```

---

### Example 12: Retry Logic

```python
from kuzu_memory.cli.service_manager import ServiceManager
import time

def recall_with_retry(query: str, max_retries: int = 3):
    """Retry memory recall on transient failures."""
    for attempt in range(max_retries):
        try:
            with ServiceManager.memory_service() as memory:
                return memory.attach_memories(prompt=query, max_memories=10)

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⚠️  Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ All {max_retries} attempts failed")
                raise

# Usage
results = recall_with_retry("test query", max_retries=3)
```

---

## Testing with Services

### Example 13: Mock Service for Testing

```python
from unittest.mock import Mock, MagicMock
from kuzu_memory.protocols.services import IMemoryService
from kuzu_memory.core.models import Memory, MemoryContext, MemoryType
import pytest

def test_memory_recall():
    """Test memory recall with mocked service."""
    # Create mock service
    mock_memory = Mock(spec=IMemoryService)

    # Setup mock behavior
    test_memory = Memory(
        id="test-123",
        content="Test memory content",
        memory_type=MemoryType.SEMANTIC,
        created_at="2025-11-30T10:00:00"
    )

    mock_context = MemoryContext(
        memories=[test_memory],
        total_count=1,
        strategy="hybrid"
    )

    mock_memory.attach_memories.return_value = mock_context

    # Test code using mock
    with mock_memory as memory:
        results = memory.attach_memories(prompt="test", max_memories=10)

        assert len(results.memories) == 1
        assert results.memories[0].content == "Test memory content"

    # Verify mock calls
    mock_memory.attach_memories.assert_called_once_with(
        prompt="test",
        max_memories=10
    )
```

---

### Example 14: Integration Test with Real Service

```python
from kuzu_memory.cli.service_manager import ServiceManager
from pathlib import Path
import tempfile
import pytest

def test_memory_service_integration():
    """Integration test with real MemoryService."""
    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Use real service with test database
        with ServiceManager.memory_service(db_path=db_path) as memory:
            # Store memory
            memory_id = memory.remember(
                content="Test memory",
                source="test"
            )

            assert memory_id is not None

            # Recall memory
            results = memory.attach_memories(
                prompt="Test",
                max_memories=10
            )

            assert len(results.memories) > 0
            assert any("Test memory" in m.content for m in results.memories)

        # Database auto-cleaned up with tmpdir
```

---

### Example 15: Async Service Testing

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.cli.async_utils import run_async
import pytest

def test_diagnostic_service_async():
    """Test async diagnostic service methods."""
    with ServiceManager.diagnostic_service() as diagnostic:
        # Run async method in sync test
        result = run_async(diagnostic.check_database_health())

        # Assertions
        assert "connected" in result
        assert "memory_count" in result
        assert isinstance(result["memory_count"], int)

        # Test another async method
        config_result = run_async(diagnostic.check_configuration())
        assert "valid" in config_result
```

---

## Advanced Patterns

### Example 16: Custom Service Configuration

```python
from kuzu_memory.cli.service_manager import ServiceManager

def use_custom_config():
    """Use service with custom configuration."""
    custom_config = {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "cache_size": 1000,
        "batch_size": 32
    }

    with ServiceManager.memory_service(config=custom_config) as memory:
        # Service uses custom config
        results = memory.attach_memories(
            prompt="test",
            max_memories=10
        )

        return results

# Usage
results = use_custom_config()
```

---

### Example 17: Service with Specific Database

```python
from kuzu_memory.cli.service_manager import ServiceManager
from pathlib import Path

def use_specific_database(db_path: Path):
    """Use service with specific database path."""
    with ServiceManager.memory_service(db_path=db_path) as memory:
        # Use specific database
        count = memory.get_memory_count()
        print(f"Database at {db_path} has {count} memories")

        return count

# Usage
from kuzu_memory.utils.project_setup import get_project_db_path
db_path = get_project_db_path()
count = use_specific_database(db_path)
```

---

### Example 18: Pipeline Pattern

```python
from kuzu_memory.cli.service_manager import ServiceManager
from typing import List, Dict, Any

def memory_processing_pipeline(query: str) -> Dict[str, Any]:
    """Process memories through multi-stage pipeline."""
    with ServiceManager.memory_service() as memory:
        # Stage 1: Recall
        context = memory.attach_memories(
            prompt=query,
            max_memories=20,
            strategy="hybrid"
        )

        # Stage 2: Filter by relevance
        filtered = [
            m for m in context.memories
            if m.relevance > 0.7
        ]

        # Stage 3: Group by type
        by_type = {}
        for mem in filtered:
            type_name = mem.memory_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(mem)

        # Stage 4: Summarize
        return {
            "total_recalled": len(context.memories),
            "after_filter": len(filtered),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "top_memory": filtered[0] if filtered else None
        }

# Usage
result = memory_processing_pipeline("What is the architecture?")
print(f"Recalled {result['total_recalled']}, filtered to {result['after_filter']}")
```

---

## Related Documentation

- **Architecture Guide**: [/docs/architecture/service-layer.md](../architecture/service-layer.md)
- **Migration Guide**: [/docs/guides/migrating-to-services.md](../guides/migrating-to-services.md)
- **API Reference**: [/docs/api/services.md](../api/services.md)

---

**Last Updated**: 2025-11-30
**Ticket**: 1M-428
**Epic**: 1M-415
