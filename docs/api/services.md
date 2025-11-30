# Services API Reference

**Ticket**: 1M-428 (Update Architecture and Usage Documentation)
**Epic**: 1M-415 (SOA/DI Refactoring)
**Last Updated**: 2025-11-30

---

## Table of Contents

1. [ServiceManager](#servicemanager)
2. [IMemoryService Protocol](#imemoryservice-protocol)
3. [IGitSyncService Protocol](#igitsyncservice-protocol)
4. [IDiagnosticService Protocol](#idiagnosticservice-protocol)
5. [IConfigService Protocol](#iconfigservice-protocol)
6. [ISetupService Protocol](#isetupservice-protocol)
7. [IInstallerService Protocol](#iinstallerservice-protocol)
8. [Async Utils](#async-utils)

---

## ServiceManager

**Module**: `kuzu_memory.cli.service_manager`

Central service lifecycle manager providing context managers for all services.

### Class Definition

```python
class ServiceManager:
    """Manages service lifecycle for CLI commands."""
```

---

### ServiceManager.memory_service()

Create context manager for MemoryService.

**Signature:**

```python
@staticmethod
@contextmanager
def memory_service(
    db_path: Optional[Path] = None,
    enable_git_sync: bool = False,
    config: Optional[Dict[str, Any]] = None
) -> Iterator[IMemoryService]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `Optional[Path]` | `None` | Database path (auto-detects project DB if None) |
| `enable_git_sync` | `bool` | `False` | Enable git synchronization (default: False for read ops) |
| `config` | `Optional[Dict[str, Any]]` | `None` | Optional configuration dictionary |

**Returns:**

- `Iterator[IMemoryService]`: Context manager yielding initialized memory service

**Example:**

```python
from kuzu_memory.cli.service_manager import ServiceManager

with ServiceManager.memory_service() as memory:
    memories = memory.recall("test query", limit=10)
    print(f"Found {len(memories)} memories")
```

**Error Handling:**

- Propagates exceptions from service operations
- Ensures cleanup even on exceptions
- Safe to use in CLI commands with try/except wrapper

**Performance:**

- O(1) initialization
- Cleanup time varies with open connections
- **16.63% faster** than direct KuzuMemory instantiation (Phase 5 QA verified)

---

### ServiceManager.git_sync_service()

Create context manager for GitSyncService.

**Signature:**

```python
@staticmethod
@contextmanager
def git_sync_service(
    config_service: Optional[IConfigService] = None,
) -> Iterator[IGitSyncService]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_service` | `Optional[IConfigService]` | `None` | Configuration service (auto-creates if None) |

**Returns:**

- `Iterator[IGitSyncService]`: Context manager yielding initialized git sync service

**Example:**

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.services import ConfigService

# With existing config service
config = ConfigService(project_root)
config.initialize()

try:
    with ServiceManager.git_sync_service(config) as git_sync:
        if git_sync.is_available():
            count = git_sync.sync(max_commits=100)
            print(f"Synced {count} commits")
finally:
    config.cleanup()

# Auto-create config service
with ServiceManager.git_sync_service() as git_sync:
    if git_sync.is_available():
        git_sync.sync()
```

**Error Handling:**

- Propagates exceptions from service operations
- Ensures cleanup even on exceptions
- Safe to use in CLI commands with try/except wrapper

**Performance:**

- O(1) initialization
- Cleanup time varies with resources held

---

### ServiceManager.diagnostic_service()

Create context manager for DiagnosticService (async methods).

**Signature:**

```python
@staticmethod
@contextmanager
def diagnostic_service(
    config_service: Optional[IConfigService] = None,
    memory_service: Optional[IMemoryService] = None,
) -> Iterator[IDiagnosticService]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_service` | `Optional[IConfigService]` | `None` | Configuration service (auto-creates if None) |
| `memory_service` | `Optional[IMemoryService]` | `None` | Memory service for DB health checks |

**Returns:**

- `Iterator[IDiagnosticService]`: Context manager yielding initialized diagnostic service

**Example:**

```python
from kuzu_memory.cli.service_manager import ServiceManager
from kuzu_memory.cli.async_utils import run_async

# With auto-created config
with ServiceManager.diagnostic_service() as diagnostic:
    # Run async method in sync context
    result = run_async(diagnostic.run_full_diagnostics())

    if not result["all_healthy"]:
        print("Issues found:", result["issues"])

# With existing services
config = ConfigService(project_root)
config.initialize()

try:
    with ServiceManager.diagnostic_service(config) as diagnostic:
        health = run_async(diagnostic.check_database_health())
        print(f"Database healthy: {health['connected']}")
finally:
    config.cleanup()
```

**Note on Async:**

DiagnosticService methods are async for I/O operations. Use `run_async()` helper:

```python
from kuzu_memory.cli.async_utils import run_async

result = run_async(diagnostic.run_full_diagnostics())
```

**Performance:**

- O(1) initialization
- Cleanup time varies with resources held

---

## IMemoryService Protocol

**Module**: `kuzu_memory.protocols.services`

Protocol for memory management operations.

### Protocol Definition

```python
class IMemoryService(Protocol):
    """Protocol for memory operations."""
```

---

### remember()

Store a new memory with automatic classification.

**Signature:**

```python
def remember(
    self,
    content: str,
    source: str,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | `str` | Yes | Memory content to store |
| `source` | `str` | Yes | Source of memory (e.g., "cli", "api") |
| `session_id` | `Optional[str]` | No | Session identifier |
| `agent_id` | `Optional[str]` | No | Agent identifier |
| `metadata` | `Optional[Dict[str, Any]]` | No | Additional metadata |

**Returns:**

- `str`: Memory ID (UUID string)

**Example:**

```python
memory_id = memory.remember(
    content="User prefers Python over JavaScript",
    source="cli",
    session_id="abc-123",
    metadata={"category": "preference"}
)
```

---

### attach_memories()

Attach relevant memories to a prompt.

**Signature:**

```python
def attach_memories(
    self,
    prompt: str,
    max_memories: int = 10,
    strategy: str = "hybrid",
    **filters: Any,
) -> MemoryContext
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | `str` | Required | Prompt to enhance with memories |
| `max_memories` | `int` | `10` | Maximum memories to attach |
| `strategy` | `str` | `"hybrid"` | Recall strategy ("hybrid", "semantic", "temporal") |
| `**filters` | `Any` | - | Additional filters (memory_type, min_relevance, etc.) |

**Returns:**

- `MemoryContext`: Context with selected memories and metadata

**Example:**

```python
context = memory.attach_memories(
    prompt="What is the project architecture?",
    max_memories=10,
    strategy="hybrid",
    memory_type=MemoryType.SEMANTIC,
    min_relevance=0.7
)

for mem in context.memories:
    print(f"[{mem.relevance:.2f}] {mem.content}")
```

---

### get_recent_memories()

Get recent memories ordered by timestamp.

**Signature:**

```python
def get_recent_memories(
    self,
    limit: int = 20,
    memory_type: Optional[MemoryType] = None,
    **filters: Any,
) -> List[Memory]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `int` | `20` | Maximum memories to return |
| `memory_type` | `Optional[MemoryType]` | `None` | Filter by memory type |
| `**filters` | `Any` | - | Additional filters (source, session_id, etc.) |

**Returns:**

- `List[Memory]`: Memories ordered by `created_at` DESC

**Example:**

```python
recent = memory.get_recent_memories(
    limit=10,
    memory_type=MemoryType.EPISODIC
)

for mem in recent:
    print(f"[{mem.created_at}] {mem.content[:100]}")
```

---

### get_memory_count()

Get total memory count with optional filters.

**Signature:**

```python
def get_memory_count(
    self,
    memory_type: Optional[MemoryType] = None,
    **filters: Any,
) -> int
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `memory_type` | `Optional[MemoryType]` | `None` | Filter by memory type |
| `**filters` | `Any` | - | Additional filters |

**Returns:**

- `int`: Total count of memories matching filters

**Example:**

```python
total = memory.get_memory_count()
episodic = memory.get_memory_count(memory_type=MemoryType.EPISODIC)

print(f"Total: {total}, Episodic: {episodic}")
```

---

### get_database_size()

Get current database size in bytes.

**Signature:**

```python
def get_database_size(self) -> int
```

**Returns:**

- `int`: Database size in bytes

**Example:**

```python
size_bytes = memory.get_database_size()
size_mb = size_bytes / (1024 * 1024)

print(f"Database size: {size_mb:.2f} MB")
```

---

### add_memory()

Add a new memory to the database (low-level API).

**Signature:**

```python
def add_memory(
    self,
    content: str,
    memory_type: MemoryType,
    entities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Memory
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | `str` | Yes | Memory content text |
| `memory_type` | `MemoryType` | Yes | Type of memory |
| `entities` | `Optional[List[str]]` | No | Extracted entities |
| `metadata` | `Optional[Dict[str, Any]]` | No | Additional metadata |

**Returns:**

- `Memory`: Created Memory object with generated ID

**Raises:**

- `ValueError`: If content is empty or invalid
- `DatabaseError`: If storage operation fails

**Example:**

```python
from kuzu_memory.core.models import MemoryType

memory_obj = memory.add_memory(
    content="User prefers tabs over spaces",
    memory_type=MemoryType.PREFERENCE,
    entities=["user", "tabs", "spaces"],
    metadata={"importance": "high"}
)

print(f"Created memory: {memory_obj.id}")
```

---

### get_memory()

Retrieve a memory by ID.

**Signature:**

```python
def get_memory(self, memory_id: str) -> Optional[Memory]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `memory_id` | `str` | Unique memory identifier |

**Returns:**

- `Optional[Memory]`: Memory object if found, None otherwise

**Performance:**

- O(1) lookup by ID

**Example:**

```python
memory_obj = memory.get_memory("550e8400-e29b-41d4-a716-446655440000")

if memory_obj:
    print(f"Found: {memory_obj.content}")
else:
    print("Memory not found")
```

---

### update_memory()

Update an existing memory.

**Signature:**

```python
def update_memory(
    self,
    memory_id: str,
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Memory]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `memory_id` | `str` | Unique memory identifier |
| `content` | `Optional[str]` | New content |
| `metadata` | `Optional[Dict[str, Any]]` | New/updated metadata |

**Returns:**

- `Optional[Memory]`: Updated Memory object if found, None otherwise

**Note:**

At least one of `content` or `metadata` must be provided.

**Example:**

```python
updated = memory.update_memory(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    content="Updated content",
    metadata={"revised": True}
)
```

---

### delete_memory()

Delete a memory by ID.

**Signature:**

```python
def delete_memory(self, memory_id: str) -> bool
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `memory_id` | `str` | Unique memory identifier |

**Returns:**

- `bool`: True if deleted, False if not found

**Error Handling:**

Returns False instead of raising exception if not found.

**Example:**

```python
success = memory.delete_memory("550e8400-e29b-41d4-a716-446655440000")

if success:
    print("Memory deleted")
else:
    print("Memory not found")
```

---

### kuzu_memory (Property)

Access underlying KuzuMemory instance for advanced operations.

**Signature:**

```python
@property
def kuzu_memory(self) -> Any
```

**Returns:**

- `Any`: Underlying KuzuMemory instance

**Note:**

Provided for advanced operations like MemoryPruner integration. Use with caution - prefer service methods when possible.

**Example:**

```python
# Advanced: Access underlying instance
kuzu = memory.kuzu_memory

# Use for operations not exposed by protocol
# (Use sparingly)
```

---

## IGitSyncService Protocol

**Module**: `kuzu_memory.protocols.services`

Protocol for git synchronization operations.

### Protocol Definition

```python
class IGitSyncService(Protocol):
    """Protocol for git synchronization."""
```

---

### sync()

Sync git history as episodic memories.

**Signature:**

```python
def sync(
    self,
    since: Optional[str] = None,
    max_commits: int = 100,
) -> int
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `since` | `Optional[str]` | `None` | Date string (ISO: "YYYY-MM-DD"), only sync commits after this date |
| `max_commits` | `int` | `100` | Maximum commits to sync |

**Returns:**

- `int`: Number of commits synced

**Memory Format:**

- **content**: `"<commit_message> (by <author> on <date>)"`
- **memory_type**: `EPISODIC`
- **entities**: `[author_name, file_paths]`
- **metadata**: `{commit_hash, author, date, files_changed}`

**Performance:**

~10-50 commits/second depending on commit size

**Example:**

```python
# Sync last 100 commits
count = git_sync.sync(max_commits=100)

# Sync commits since specific date
count = git_sync.sync(since="2024-01-01", max_commits=200)

print(f"Synced {count} commits")
```

---

### is_available()

Check if git synchronization is available.

**Signature:**

```python
def is_available(self) -> bool
```

**Returns:**

- `bool`: True if git is installed and repository detected

**Checks:**

- Git command is available in PATH
- Current directory is in a git repository
- Repository has commits to sync

**Example:**

```python
if git_sync.is_available():
    count = git_sync.sync()
else:
    print("Git not available")
```

---

### get_sync_status()

Get current synchronization status.

**Signature:**

```python
def get_sync_status(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `enabled` (bool): Synchronization is enabled
- `last_sync` (Optional[str]): Last sync timestamp
- `commits_synced` (int): Total commits synced
- `hooks_installed` (bool): Git hooks are installed

**Example:**

```python
status = git_sync.get_sync_status()

if status["enabled"]:
    print(f"Last synced {status['commits_synced']} commits")
    print(f"Last sync: {status.get('last_sync', 'Never')}")
```

---

### install_hooks()

Install git hooks for automatic synchronization.

**Signature:**

```python
def install_hooks(self) -> bool
```

**Returns:**

- `bool`: True if hooks installed successfully

**Installs:**

- post-commit hook for automatic commit capture
- Preserves existing hooks if present
- Creates hook wrapper if needed

**Error Handling:**

Returns False if git hooks directory not writable.

**Example:**

```python
if git_sync.install_hooks():
    print("✅ Git hooks installed")
else:
    print("❌ Failed to install hooks")
```

---

### uninstall_hooks()

Uninstall git hooks.

**Signature:**

```python
def uninstall_hooks(self) -> bool
```

**Returns:**

- `bool`: True if hooks uninstalled successfully

**Actions:**

- Removes KuzuMemory git hooks
- Restores original hooks if backed up
- Cleans up hook wrappers

**Note:**

Safe to call even if hooks not installed.

**Example:**

```python
if git_sync.uninstall_hooks():
    print("✅ Git hooks removed")
```

---

### initialize_sync()

Initialize git synchronization for a project.

**Signature:**

```python
def initialize_sync(self, project_root: Optional[Path] = None) -> bool
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_root` | `Optional[Path]` | `None` | Project root (auto-detect if None) |

**Returns:**

- `bool`: True if initialization succeeded

**Setup Actions:**

- Detect git repository
- Verify git is available
- Create initial configuration
- Optionally install git hooks

**Example:**

```python
if git_sync.initialize_sync():
    print("✅ Git sync initialized")
```

---

## IDiagnosticService Protocol

**Module**: `kuzu_memory.protocols.services`

Protocol for diagnostic operations (async methods).

### Protocol Definition

```python
class IDiagnosticService(Protocol):
    """Protocol for diagnostic operations."""
```

---

### run_full_diagnostics() [async]

Run comprehensive diagnostics on entire system.

**Signature:**

```python
async def run_full_diagnostics(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `all_healthy` (bool): All systems healthy
- `configuration` (Dict): Config check results
- `database` (Dict): Database health results
- `mcp_server` (Dict): MCP server status
- `git_integration` (Dict): Git sync status
- `system_info` (Dict): System information
- `timestamp` (str): ISO timestamp

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

result = run_async(diagnostic.run_full_diagnostics())

if result["all_healthy"]:
    print("✅ All systems healthy")
else:
    print("⚠️ Issues found:")
    for issue in result.get("issues", []):
        print(f"  - {issue}")
```

---

### check_database_health() [async]

Check database connectivity and health.

**Signature:**

```python
async def check_database_health(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `connected` (bool): Database connection established
- `memory_count` (int): Total memories
- `db_size_bytes` (int): Database size
- `schema_version` (str): Current schema version
- `issues` (List[str]): Problems found

**Checks:**

- Database file exists and is accessible
- Database connection can be established
- Schema is valid and up-to-date
- No corruption detected

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

result = run_async(diagnostic.check_database_health())

if result["connected"]:
    print(f"✅ Database healthy: {result['memory_count']} memories")
else:
    print("❌ Database issues:", result.get("issues"))
```

---

### check_mcp_server_health() [async]

Check MCP server configuration and health.

**Signature:**

```python
async def check_mcp_server_health(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `configured` (bool): MCP server configured
- `config_valid` (bool): Configuration is valid
- `server_path` (str): Path to MCP server config
- `issues` (List[str]): Problems found

**Checks:**

- MCP config file exists (claude_desktop_config.json)
- Configuration is valid JSON
- Server entry is present and correct
- Paths in configuration are valid

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

result = run_async(diagnostic.check_mcp_server_health())

if result["configured"] and result["config_valid"]:
    print("✅ MCP server healthy")
else:
    print("❌ MCP issues:", result.get("issues"))
```

---

### check_configuration() [async]

Check configuration validity and completeness.

**Signature:**

```python
async def check_configuration(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `valid` (bool): Configuration is valid
- `issues` (List[str]): Problems found
- `config_path` (str): Path to config file
- `project_root` (str): Project root directory

**Checks:**

- Configuration file exists and is readable
- Required configuration keys present
- Paths are valid and accessible
- Environment variables properly set

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

result = run_async(diagnostic.check_configuration())

if result["valid"]:
    print(f"✅ Config valid at {result['config_path']}")
else:
    print("❌ Config issues:", result.get("issues"))
```

---

### check_git_integration() [async]

Check git synchronization integration.

**Signature:**

```python
async def check_git_integration(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `available` (bool): Git is available
- `hooks_installed` (bool): Git hooks installed
- `last_sync` (Optional[str]): Last sync timestamp
- `issues` (List[str]): Problems found

**Checks:**

- Git repository is detected
- Git hooks are installed
- Sync functionality is working
- No permission issues

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

result = run_async(diagnostic.check_git_integration())

if result["available"] and result["hooks_installed"]:
    print("✅ Git integration healthy")
else:
    print("⚠️ Git issues:", result.get("issues"))
```

---

### get_system_info() [async]

Get system information and environment details.

**Signature:**

```python
async def get_system_info(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `version` (str): KuzuMemory version
- `python_version` (str): Python version
- `platform` (str): Operating system
- `kuzu_version` (str): Kuzu database version
- `install_path` (str): Installation path

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

info = run_async(diagnostic.get_system_info())

print(f"KuzuMemory v{info['version']}")
print(f"Python {info['python_version']}")
print(f"Platform: {info['platform']}")
```

---

### verify_dependencies() [async]

Verify all required dependencies are installed.

**Signature:**

```python
async def verify_dependencies(self) -> Dict[str, Any]
```

**Returns:**

Dictionary with keys:
- `all_satisfied` (bool): All dependencies met
- `missing` (List[str]): Missing dependencies
- `outdated` (List[str]): Outdated dependencies
- `suggestions` (List[str]): Remediation steps

**Checks:**

- Required Python packages installed
- Package versions meet requirements
- Optional dependencies for integrations

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

result = run_async(diagnostic.verify_dependencies())

if result["all_satisfied"]:
    print("✅ All dependencies satisfied")
else:
    print("❌ Missing:", result["missing"])
    print("💡 Suggestions:", result["suggestions"])
```

---

### format_diagnostic_report()

Format diagnostic results as human-readable report.

**Signature:**

```python
def format_diagnostic_report(self, results: Dict[str, Any]) -> str
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `results` | `Dict[str, Any]` | Results from `run_full_diagnostics()` |

**Returns:**

- `str`: Formatted report string with sections for each check

**Note:**

This method is synchronous (no async).

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

results = run_async(diagnostic.run_full_diagnostics())
report = diagnostic.format_diagnostic_report(results)

print(report)
```

---

## IConfigService Protocol

**Module**: `kuzu_memory.protocols.services`

Protocol for configuration management.

### get_project_root()

Get the project root directory.

**Signature:**

```python
def get_project_root(self) -> Path
```

**Returns:**

- `Path`: Project root directory

**Implementation Note:**

Should detect git root or use explicit config.

---

### get_db_path()

Get the database path.

**Signature:**

```python
def get_db_path(self) -> Path
```

**Returns:**

- `Path`: Path to Kuzu database directory

**Default:**

`<project_root>/.kuzu-memory/db`

---

### get_config_value()

Get a specific config value.

**Signature:**

```python
def get_config_value(self, key: str, default: Any = None) -> Any
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | Required | Config key (supports dot notation) |
| `default` | `Any` | `None` | Default value if not found |

**Returns:**

- `Any`: Configuration value or default

**Example:**

```python
api_key = config.get_config_value("api.key", default="")
enabled = config.get_config_value("integrations.auggie.enabled", False)
```

---

## ISetupService Protocol

**Module**: `kuzu_memory.protocols.services`

Protocol for setup orchestration.

### initialize_project()

Initialize project with KuzuMemory.

**Signature:**

```python
def initialize_project(
    self,
    force: bool = False,
    git_sync: bool = False,
    claude_desktop: bool = False,
) -> Dict[str, Any]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `bool` | `False` | Force re-initialization |
| `git_sync` | `bool` | `False` | Enable git sync |
| `claude_desktop` | `bool` | `False` | Install Claude Desktop integration |

**Returns:**

Dictionary with keys:
- `success` (bool): Initialization succeeded
- `summary` (str): Description
- `steps_completed` (List[str]): Completed steps
- `warnings` (List[str]): Warnings

**Workflow:**

1. Detect project environment
2. Initialize database if needed
3. Configure integrations based on detected tools
4. Optionally sync git history
5. Verify installation health

**Example:**

```python
result = setup.initialize_project(
    force=True,
    git_sync=True,
    claude_desktop=False
)

if result["success"]:
    print(result["summary"])
else:
    print("Failed:", result.get("error"))
```

---

## IInstallerService Protocol

**Module**: `kuzu_memory.protocols.services`

Protocol for installer management.

### discover_installers()

Discover available installers.

**Signature:**

```python
def discover_installers(self) -> List[str]
```

**Returns:**

- `List[str]`: Available integration names

**Example:**

```python
available = installer.discover_installers()
# ["claude-desktop", "auggie", "cursor", "vscode"]
```

---

### install()

Install an integration.

**Signature:**

```python
def install(self, integration: str, **kwargs) -> bool
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `integration` | `str` | Integration name |
| `**kwargs` | - | Integration-specific options |

**Returns:**

- `bool`: True if installation succeeded

**Raises:**

- `ValueError`: If integration name is unknown
- `InstallationError`: If installation fails

**Example:**

```python
success = installer.install("claude-desktop")
```

---

## Async Utils

**Module**: `kuzu_memory.cli.async_utils`

Utilities for bridging async/sync contexts in CLI commands.

### run_async()

Run async coroutine in sync context.

**Signature:**

```python
def run_async(coro: Awaitable[T]) -> T
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `coro` | `Awaitable[T]` | Async coroutine to run |

**Returns:**

- `T`: Result of the coroutine

**Raises:**

Any exception raised by the coroutine

**Example:**

```python
from kuzu_memory.cli.async_utils import run_async

async def async_operation():
    return await some_service.async_method()

# In sync Click command
@cli.command()
def sync_command():
    result = run_async(async_operation())
    click.echo(result)
```

**Performance:**

- O(1) overhead for event loop management
- Direct execution, no thread pool overhead
- Compatible with both new and existing event loops

**Error Handling:**

- Propagates all exceptions from coroutine
- Ensures event loop cleanup on errors
- Safe to use in CLI error handlers

---

## Related Documentation

- **Architecture Guide**: [/docs/architecture/service-layer.md](../architecture/service-layer.md)
- **Usage Examples**: [/docs/examples/service-usage.md](../examples/service-usage.md)
- **Migration Guide**: [/docs/guides/migrating-to-services.md](../guides/migrating-to-services.md)

---

**Last Updated**: 2025-11-30
**Ticket**: 1M-428
**Epic**: 1M-415
