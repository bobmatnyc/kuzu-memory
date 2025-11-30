# Migrating to Service Layer Architecture

**Ticket**: 1M-428 (Update Architecture and Usage Documentation)
**Epic**: 1M-415 (SOA/DI Refactoring)
**Last Updated**: 2025-11-30

---

## Table of Contents

1. [Why Migrate?](#why-migrate)
2. [Migration Checklist](#migration-checklist)
3. [Before/After Examples](#beforeafter-examples)
4. [Common Pitfalls](#common-pitfalls)
5. [Testing Migrated Code](#testing-migrated-code)
6. [Troubleshooting](#troubleshooting)

---

## Why Migrate?

### Performance Benefits

**16.63% faster** than direct instantiation (Phase 5 QA verified):

```
Baseline:     49.806 ± 43.469 ms  (direct KuzuMemory)
Service:      41.525 ±  7.856 ms  (ServiceManager pattern)
Overhead:     -8.281 ms (-16.63% faster!)
```

### Testability Improvements

✅ **Easy Mocking**: Protocol-based interfaces simplify testing
✅ **Dependency Injection**: Clear dependencies make unit tests easier
✅ **Isolation**: Services can be tested independently

### Consistency Benefits

✅ **Unified Lifecycle**: All services use context managers
✅ **Single Source of Truth**: ServiceManager handles configuration
✅ **Resource Safety**: Automatic cleanup prevents leaks

### Maintainability

✅ **Clear Architecture**: Service layer separates concerns
✅ **Type Safety**: Protocol interfaces provide type checking
✅ **Future-Proof**: Easy to extend and modify

---

## Migration Checklist

### Pre-Migration

- [ ] **Read architecture docs**: [/docs/architecture/service-layer.md](../architecture/service-layer.md)
- [ ] **Review usage examples**: [/docs/examples/service-usage.md](../examples/service-usage.md)
- [ ] **Identify direct instantiations**: Search for `KuzuMemory(`, `GitSyncManager(`, etc.
- [ ] **List affected commands**: Note which CLI commands use direct instantiation
- [ ] **Understand dependencies**: Map service dependencies

### During Migration

- [ ] **Replace imports**: Change from concrete classes to `ServiceManager`
- [ ] **Update instantiations**: Use `ServiceManager.X_service()` context managers
- [ ] **Remove manual cleanup**: Context managers handle this automatically
- [ ] **Update error handling**: Adjust for context manager exceptions
- [ ] **Remove redundant code**: ServiceManager handles auto-detection

### Post-Migration

- [ ] **Add unit tests**: Test service usage with mocks
- [ ] **Run integration tests**: Verify end-to-end functionality
- [ ] **Manual testing**: Test command in real environment
- [ ] **Update documentation**: Document any command-specific changes
- [ ] **Code review**: Have changes reviewed by team

### Verification

- [ ] **Type checking**: Run `mypy` on migrated code
- [ ] **Formatting**: Run `black` and `isort`
- [ ] **Test pass rate**: Ensure no regressions
- [ ] **Manual smoke test**: Test all command variations
- [ ] **Performance check**: Verify no significant overhead

---

## Before/After Examples

### Example 1: Memory Recall Command

#### Before (Direct Instantiation)

```python
# memory_commands.py (OLD)
from kuzu_memory import KuzuMemory
from kuzu_memory.utils.project_setup import get_project_db_path
import click

@click.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max memories to return")
def recall(query: str, limit: int):
    """Recall relevant memories."""
    # Manual database path detection
    db_path = get_project_db_path()

    # Direct instantiation
    with KuzuMemory(db_path=db_path) as memory:
        # Query memories
        results = memory.attach_memories(
            prompt=query,
            max_memories=limit
        )

        # Display results
        click.echo(f"Found {len(results.memories)} memories")
        for mem in results.memories:
            click.echo(f"  [{mem.relevance:.2f}] {mem.content[:100]}")
```

#### After (ServiceManager)

```python
# memory_commands.py (NEW)
from kuzu_memory.cli.service_manager import ServiceManager
import click

@click.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max memories to return")
def recall(query: str, limit: int):
    """Recall relevant memories."""
    # ServiceManager handles db_path auto-detection
    with ServiceManager.memory_service() as memory:
        # Query memories (same API)
        results = memory.attach_memories(
            prompt=query,
            max_memories=limit
        )

        # Display results (unchanged)
        click.echo(f"Found {len(results.memories)} memories")
        for mem in results.memories:
            click.echo(f"  [{mem.relevance:.2f}] {mem.content[:100]}")
```

#### Changes Summary

1. ✅ **Import**: `ServiceManager` instead of `KuzuMemory`
2. ✅ **No manual path**: `ServiceManager` auto-detects database
3. ✅ **Same API**: `attach_memories()` works identically
4. ✅ **Simpler code**: 3 fewer lines

---

### Example 2: Git Sync Command

#### Before (Direct Instantiation)

```python
# git_commands.py (OLD)
from kuzu_memory import KuzuMemory
from kuzu_memory.git_sync import GitSyncManager
from kuzu_memory.utils.project_setup import get_project_db_path, find_project_root
from kuzu_memory.config import get_config_loader
import click

@click.command()
@click.option("--dry-run", is_flag=True, help="Preview without syncing")
def sync(dry_run: bool):
    """Sync git history as memories."""
    # Manual setup
    db_path = get_project_db_path()
    project_root = find_project_root()
    config_loader = get_config_loader()
    config = config_loader.load_config()

    # Create git sync manager
    git_sync = GitSyncManager(
        repo_path=project_root,
        config=config
    )

    if not git_sync.is_available():
        click.echo("❌ Git not available", err=True)
        return

    # Sync commits
    if dry_run:
        click.echo("🔍 Dry run mode - no changes will be made")

    count = git_sync.sync(max_commits=100)
    click.echo(f"✅ Synced {count} commits")
```

#### After (ServiceManager)

```python
# git_commands.py (NEW)
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.services import ConfigService
from kuzu_memory.utils.project_setup import find_project_root
import click

@click.command()
@click.option("--dry-run", is_flag=True, help="Preview without syncing")
def sync(dry_run: bool):
    """Sync git history as memories."""
    # Setup config service
    project_root = find_project_root()
    config = ConfigService(project_root)
    config.initialize()

    try:
        # Use git sync service
        with ServiceManager.git_sync_service(config) as git_sync:
            if not git_sync.is_available():
                click.echo("❌ Git not available", err=True)
                return

            # Sync commits (same API)
            if dry_run:
                click.echo("🔍 Dry run mode - no changes will be made")

            count = git_sync.sync(max_commits=100)
            click.echo(f"✅ Synced {count} commits")
    finally:
        # Cleanup config service
        config.cleanup()
```

#### Changes Summary

1. ✅ **Import**: `ServiceManager` and `ConfigService`
2. ✅ **Config management**: Explicit lifecycle for config service
3. ✅ **Cleanup**: Manual cleanup in finally block
4. ✅ **Same API**: `is_available()` and `sync()` unchanged

---

### Example 3: Doctor Command (Async)

#### Before (Direct Instantiation)

```python
# doctor_commands.py (OLD)
from kuzu_memory.diagnostics import MCPDiagnostics
from kuzu_memory.utils.project_setup import find_project_root
import click
import asyncio

@click.command()
def mcp():
    """Check MCP server health."""
    project_root = find_project_root()

    # Direct instantiation
    diagnostics = MCPDiagnostics(
        project_root=project_root,
        verbose=True
    )

    # Run async method with asyncio.run()
    result = asyncio.run(diagnostics.check_mcp_server_health())

    if result["configured"]:
        click.echo("✅ MCP server healthy")
    else:
        click.echo("❌ MCP server issues found")
        for issue in result.get("issues", []):
            click.echo(f"  - {issue}")
```

#### After (ServiceManager + run_async)

```python
# doctor_commands.py (NEW)
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.cli.async_utils import run_async
import click

@click.command()
def mcp():
    """Check MCP server health."""
    # ServiceManager with auto-detected config
    with ServiceManager.diagnostic_service() as diagnostic:
        # Use run_async helper
        result = run_async(diagnostic.check_mcp_server_health())

        if result["configured"]:
            click.echo("✅ MCP server healthy")
        else:
            click.echo("❌ MCP server issues found")
            for issue in result.get("issues", []):
                click.echo(f"  - {issue}")
```

#### Changes Summary

1. ✅ **Import**: `ServiceManager` and `run_async` helper
2. ✅ **No manual setup**: ServiceManager handles config creation
3. ✅ **Clean async bridge**: `run_async()` instead of `asyncio.run()`
4. ✅ **Automatic cleanup**: Context manager handles it
5. ✅ **Simpler**: 7 fewer lines

---

### Example 4: Init Command (Multi-Service)

#### Before (Direct Instantiation)

```python
# init_commands.py (OLD)
from kuzu_memory import KuzuMemory
from kuzu_memory.utils.project_setup import (
    get_project_db_path,
    find_project_root,
    ensure_project_structure
)
import click

@click.command()
@click.option("--force", is_flag=True, help="Force re-initialization")
def init(force: bool):
    """Initialize project database."""
    project_root = find_project_root()

    # Manual structure creation
    ensure_project_structure(project_root)

    # Get database path
    db_path = get_project_db_path()

    # Initialize database
    with KuzuMemory(db_path=db_path) as memory:
        # Database automatically initialized on context entry
        count = memory.get_memory_count()
        click.echo(f"✅ Database initialized with {count} memories")
```

#### After (ServiceManager)

```python
# init_commands.py (NEW)
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.services import ConfigService, SetupService
from kuzu_memory.utils.project_setup import find_project_root
import click

@click.command()
@click.option("--force", is_flag=True, help="Force re-initialization")
def init(force: bool):
    """Initialize project database."""
    project_root = find_project_root()

    # Setup services
    config = ConfigService(project_root)
    config.initialize()

    setup = SetupService(config)
    setup.initialize()

    try:
        # Initialize project
        result = setup.initialize_project(force=force)

        if result["success"]:
            # Verify with memory service
            with ServiceManager.memory_service() as memory:
                count = memory.get_memory_count()
                click.echo(f"✅ Database initialized with {count} memories")
        else:
            click.echo(f"❌ Initialization failed: {result.get('error')}")
    finally:
        setup.cleanup()
        config.cleanup()
```

#### Changes Summary

1. ✅ **Service orchestration**: Uses `SetupService` for initialization
2. ✅ **Explicit lifecycle**: Manual cleanup for multi-service scenario
3. ✅ **Better error handling**: `result` dict with success flag
4. ✅ **Verification**: Uses `MemoryService` to verify initialization

---

## Common Pitfalls

### Pitfall 1: Forgetting to Cleanup Multi-Service Code

❌ **Wrong**:
```python
config = ConfigService(project_root)
config.initialize()

with ServiceManager.git_sync_service(config) as git_sync:
    git_sync.sync()

# BUG: config never cleaned up!
```

✅ **Correct**:
```python
config = ConfigService(project_root)
config.initialize()

try:
    with ServiceManager.git_sync_service(config) as git_sync:
        git_sync.sync()
finally:
    config.cleanup()  # Always cleanup
```

---

### Pitfall 2: Calling run_async() on Sync Methods

❌ **Wrong**:
```python
with ServiceManager.memory_service() as memory:
    # BUG: attach_memories is sync, not async!
    result = run_async(memory.attach_memories(prompt="test"))
```

✅ **Correct**:
```python
with ServiceManager.memory_service() as memory:
    # Sync method - call directly
    result = memory.attach_memories(prompt="test")

with ServiceManager.diagnostic_service() as diagnostic:
    # Async method - use run_async
    result = run_async(diagnostic.check_database_health())
```

---

### Pitfall 3: Not Using Context Managers

❌ **Wrong**:
```python
# BUG: Service not properly initialized/cleaned up
memory = ServiceManager.memory_service()
results = memory.recall("test")
```

✅ **Correct**:
```python
# Context manager ensures proper lifecycle
with ServiceManager.memory_service() as memory:
    results = memory.recall("test")
```

---

### Pitfall 4: Mixing Old and New Patterns

❌ **Wrong**:
```python
# Mixing direct instantiation with ServiceManager
from kuzu_memory import KuzuMemory

db_path = get_project_db_path()  # Old pattern
with ServiceManager.memory_service(db_path=db_path) as memory:
    # ...
```

✅ **Correct**:
```python
# Let ServiceManager handle everything
with ServiceManager.memory_service() as memory:
    # ServiceManager auto-detects db_path
    # ...
```

---

### Pitfall 5: Ignoring Type Hints

❌ **Wrong**:
```python
def process_memories(memory):  # No type hint
    results = memory.recall("test")
    return results
```

✅ **Correct**:
```python
from kuzu_memory.protocols.services import IMemoryService

def process_memories(memory: IMemoryService):
    """Process memories with type-safe interface."""
    results = memory.recall("test")
    return results
```

---

## Testing Migrated Code

### Unit Testing with Mocks

```python
from unittest.mock import Mock
from kuzu_memory.protocols.services import IMemoryService
import pytest

def test_recall_command():
    """Test recall command with mocked service."""
    # Create mock
    mock_memory = Mock(spec=IMemoryService)
    mock_memory.attach_memories.return_value = Mock(memories=[])

    # Test function using mock
    with mock_memory as memory:
        results = memory.attach_memories(prompt="test", max_memories=10)

        # Verify
        mock_memory.attach_memories.assert_called_once()
        assert results is not None
```

### Integration Testing

```python
from kuzu_memory.cli.service_manager import ServiceManager
from pathlib import Path
import tempfile

def test_memory_service_integration():
    """Integration test with real service."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        with ServiceManager.memory_service(db_path=db_path) as memory:
            # Test real operations
            memory_id = memory.remember("Test", source="test")
            assert memory_id is not None

            results = memory.attach_memories(prompt="Test", max_memories=10)
            assert len(results.memories) > 0
```

### Manual Testing Checklist

- [ ] Test command with default options
- [ ] Test command with all options specified
- [ ] Test error cases (missing database, permissions, etc.)
- [ ] Test with different database states (empty, populated)
- [ ] Test cleanup behavior (database not locked after command)
- [ ] Test with verbose output
- [ ] Test with quiet mode (if applicable)

---

## Troubleshooting

### Issue: "ServiceManager has no attribute X_service"

**Cause**: ServiceManager method doesn't exist

**Solution**: Check available methods:
- `memory_service()`
- `git_sync_service()`
- `diagnostic_service()`

For other services (Config, Setup, Installer), use direct instantiation.

---

### Issue: "run_async() doesn't work"

**Cause**: Calling `run_async()` on non-async method

**Solution**: Only use `run_async()` with DiagnosticService async methods:
```python
# Async methods (use run_async)
run_async(diagnostic.check_database_health())
run_async(diagnostic.run_full_diagnostics())

# Sync methods (call directly)
memory.attach_memories(prompt="test")
git_sync.sync()
```

---

### Issue: "Database file not found"

**Cause**: ServiceManager can't auto-detect database path

**Solution**: Provide explicit path or initialize project:
```python
# Option 1: Explicit path
with ServiceManager.memory_service(db_path=Path("/path/to/db")) as memory:
    ...

# Option 2: Initialize project first
from kuzu_memory.services import ConfigService, SetupService
config = ConfigService(project_root)
config.initialize()
setup = SetupService(config)
setup.initialize_project()
```

---

### Issue: "Resource cleanup warnings"

**Cause**: Not using context managers or forgetting cleanup

**Solution**: Always use `with` statement or manual cleanup:
```python
# Good: Context manager
with ServiceManager.memory_service() as memory:
    ...

# Also good: Manual cleanup
config = ConfigService(project_root)
config.initialize()
try:
    ...
finally:
    config.cleanup()
```

---

### Issue: "Type errors with IMemoryService"

**Cause**: Trying to access concrete class methods

**Solution**: Use protocol interface methods only:
```python
# Wrong: Accessing internal attribute
with ServiceManager.memory_service() as memory:
    memory._db.query(...)  # Type error!

# Right: Use protocol methods
with ServiceManager.memory_service() as memory:
    memory.attach_memories(...)  # OK
```

For advanced operations, use `kuzu_memory` property:
```python
with ServiceManager.memory_service() as memory:
    # Access underlying KuzuMemory if needed
    kuzu = memory.kuzu_memory
    # Use with caution
```

---

### Issue: "Async method not awaited"

**Cause**: Forgetting to use `run_async()` or `await`

**Solution**:
```python
# Wrong: Async method not awaited
with ServiceManager.diagnostic_service() as diagnostic:
    result = diagnostic.check_database_health()  # Returns coroutine!

# Right: Use run_async
from kuzu_memory.cli.async_utils import run_async

with ServiceManager.diagnostic_service() as diagnostic:
    result = run_async(diagnostic.check_database_health())
```

---

## Migration Strategy by Command Type

### Simple Read Commands (Lowest Risk)

**Examples**: recall, enhance, recent, status

**Strategy**: Straightforward ServiceManager replacement
1. Replace `KuzuMemory(...)` with `ServiceManager.memory_service()`
2. Remove `get_project_db_path()` call
3. Test and deploy

**Estimated Time**: 15-30 minutes per command

---

### Write Commands (Medium Risk)

**Examples**: learn, prune, init

**Strategy**: Careful testing of side effects
1. Migrate to ServiceManager
2. Add comprehensive tests
3. Manual verification of database changes
4. Deploy with monitoring

**Estimated Time**: 1-2 hours per command

---

### Multi-Service Commands (Higher Risk)

**Examples**: init (Setup + Memory), git sync (Config + GitSync + Memory)

**Strategy**: Careful orchestration
1. Identify all service dependencies
2. Plan cleanup order (reverse of initialization)
3. Add explicit lifecycle management
4. Test error paths
5. Deploy with caution

**Estimated Time**: 2-4 hours per command

---

### Async Commands (Highest Complexity)

**Examples**: doctor commands

**Strategy**: Add async bridge
1. Import `run_async` helper
2. Wrap async calls with `run_async()`
3. Test async behavior thoroughly
4. Verify error propagation

**Estimated Time**: 1-3 hours per command

---

## Related Documentation

- **Architecture Guide**: [/docs/architecture/service-layer.md](../architecture/service-layer.md)
- **Usage Examples**: [/docs/examples/service-usage.md](../examples/service-usage.md)
- **API Reference**: [/docs/api/services.md](../api/services.md)

---

**Last Updated**: 2025-11-30
**Ticket**: 1M-428
**Epic**: 1M-415
