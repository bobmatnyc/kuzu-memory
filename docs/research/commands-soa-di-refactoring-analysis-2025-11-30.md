# KuzuMemory CLI Architecture Analysis: SOA/DI Refactoring Opportunities

**Date**: 2025-11-30
**Project**: kuzu-memory
**Analyzed Files**: 741 lines (commands.py) + 19 modular command files
**Analysis Type**: Architectural Anti-patterns & Service-Oriented Architecture Opportunities

---

## Executive Summary

**Current State**: The CLI layer has been **partially refactored** into modular command files, significantly improving from the original monolithic structure. However, **critical architectural issues persist**:

1. **Direct instantiation of domain objects** in command functions (tight coupling)
2. **Business logic mixed with CLI presentation logic** (SRP violation)
3. **Existing DI infrastructure underutilized** (DependencyContainer exists but unused in CLI)
4. **Service layer abstraction missing** (commands directly call KuzuMemory, installers)
5. **Testability severely impacted** (no way to inject mocks/stubs)

**Good News**:
- Clean modular command structure already exists (19 separate command files)
- Protocol-based DI container infrastructure already implemented (`core/dependencies.py`)
- Installer registry pattern already in place (`installers/registry.py`)
- Clear domain boundaries already established

**Refactoring Scope**: MEDIUM complexity, **incremental migration recommended**
- Estimated: 15-20 services to extract
- Breaking changes: MINIMAL (internal refactoring only)
- Lines affected: ~2000 across CLI modules

---

## Current Architecture Assessment

### Pattern Identified: **Hybrid Modular CLI with Direct Instantiation Anti-pattern**

```
Current Flow (ANTI-PATTERN):
┌─────────────────┐
│  CLI Commands   │ ──────> Direct instantiation
│  (Click Layer)  │         • KuzuMemory(db_path=...)
└─────────────────┘         • get_installer(name, root)
        │                   • AuggieIntegration(project_root)
        ↓
   ❌ NO SERVICE LAYER
        │
        ↓
┌─────────────────┐
│ Domain Objects  │
│ (Core/Utils)    │
└─────────────────┘
```

### Coupling Level: **HIGH**

**Evidence - Direct Instantiations Found:**

```python
# memory_commands.py:103 - Direct KuzuMemory instantiation
with KuzuMemory(db_path=db_path) as memory:
    memory_id = memory.remember(content=content, ...)

# memory_commands.py:244 - Direct KuzuMemory instantiation (fallback)
with KuzuMemory(db_path=db_path) as memory:
    memory_id = memory.remember(content, source=source, ...)

# memory_commands.py:328 - Direct KuzuMemory instantiation
with KuzuMemory(db_path=db_path, enable_git_sync=False) as memory:
    memory_context = memory.attach_memories(prompt, ...)

# init_commands.py:70 - Direct KuzuMemory instantiation
with KuzuMemory(db_path=db_path, config=config) as memory:
    memory.remember(context_str, source="project-initialization", ...)

# init_commands.py:105 - Direct AuggieIntegration instantiation
auggie = AuggieIntegration(project_root)
if auggie.is_auggie_project():
    auggie.setup_project_integration()

# install_unified.py:84 - Direct get_installer() call
installer = get_installer(integration_name, project_root)

# install_unified.py:235 - Direct get_installer() call
installer = get_installer(integration, root)
```

**Pattern Repeats**: 40+ direct instantiations across CLI modules

---

## Identified Anti-Patterns

### 1. **God Object Pattern (KuzuMemory)**

**Issue**: `KuzuMemory` class handles too many responsibilities:
- Memory storage (`remember()`)
- Memory retrieval (`attach_memories()`, `get_recent_memories()`)
- Database lifecycle management (context manager)
- Configuration management
- Git sync coordination

**Impact**:
- Hard to test individual capabilities
- Commands tightly coupled to concrete implementation
- Cannot swap implementations (e.g., remote memory service)

### 2. **Service Locator Anti-pattern (get_installer)**

**Current Code**:
```python
# install_unified.py:235
installer = get_installer(integration, root)
if not installer:
    rich_print(f"❌ No installer found for: {integration}")
    sys.exit(1)
```

**Issue**: Global registry access creates hidden dependencies

**Better Approach**: Inject `InstallerService` via constructor

### 3. **Mixed Concerns (Business + Presentation)**

**Example from memory_commands.py:103-127**:
```python
@memory.command()
def store(ctx, content, source, session_id, agent_id, metadata):
    # ❌ Mixed: Config loading + business logic + formatting
    db_path = get_project_db_path(ctx.obj.get("project_root"))  # Config
    parsed_metadata = json.loads(metadata) if metadata else {}  # Parsing

    with KuzuMemory(db_path=db_path) as memory:  # ❌ Direct instantiation
        memory_id = memory.remember(...)  # Business logic

    # Presentation logic
    rich_print(f"✅ Stored memory: {content[:100]}")  # CLI formatting
```

**Should Be**:
```python
@memory.command()
def store(ctx, content, source, session_id, agent_id, metadata):
    # ✅ Separated: Only CLI concerns
    memory_service = ctx.obj['memory_service']  # Injected
    result = memory_service.store_memory(...)  # Service call

    # Only presentation logic
    rich_print(f"✅ {result.message}")
```

### 4. **No Abstraction Over External Dependencies**

**Issue**: Commands directly call utility functions:
```python
# Scattered across files:
from ..utils.project_setup import get_project_db_path, find_project_root
from ..installers.registry import get_installer
from ..async_memory.async_cli import get_async_cli
```

**Impact**:
- Cannot mock for testing
- Hard to replace implementations
- Utility functions become de-facto service layer (unstructured)

---

## Identified Service Boundaries

### Service Architecture (Proposed):

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI LAYER (Click)                        │
│  commands.py, memory_commands.py, install_unified.py, etc.  │
└────────────┬────────────────────────────────────────────────┘
             │ Depends on (injected services)
             ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER (NEW)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ MemoryService│  │SetupService  │  │InstallerService │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ConfigService │  │DiagService   │  │GitSyncService   │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└────────────┬────────────────────────────────────────────────┘
             │ Uses (via Protocol interfaces)
             ↓
┌─────────────────────────────────────────────────────────────┐
│                   DOMAIN LAYER (Existing)                    │
│  KuzuMemory, InstallerRegistry, AuggieIntegration, etc.     │
└─────────────────────────────────────────────────────────────┘
```

### Proposed Services:

#### 1. **MemoryService** (High Priority)
**Responsibilities**:
- Memory CRUD operations (store, recall, enhance, recent)
- Memory lifecycle management (prune, cleanup)
- Performance tracking and optimization
- Async operation coordination

**Interface**:
```python
class MemoryServiceProtocol(Protocol):
    def store_memory(
        self,
        content: str,
        source: str,
        session_id: str | None = None,
        agent_id: str = "cli",
        metadata: dict[str, Any] | None = None
    ) -> MemoryStoreResult:
        """Store a new memory with validation and error handling."""
        ...

    def recall_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto",
        **filters
    ) -> RecallResult:
        """Recall memories with ranking and performance metrics."""
        ...

    def enhance_prompt(
        self,
        prompt: str,
        max_memories: int = 5
    ) -> EnhancementResult:
        """Enhance prompt with memory context."""
        ...

    def get_recent_memories(
        self,
        limit: int = 10
    ) -> list[Memory]:
        """Get recent memories with caching."""
        ...

    def prune_memories(
        self,
        strategy: str = "safe",
        execute: bool = False,
        create_backup: bool = True
    ) -> PruneResult:
        """Analyze and optionally prune old memories."""
        ...
```

**Dependencies**:
- `KuzuMemory` (domain object)
- `ConfigService` (for db_path resolution)
- `AsyncMemoryService` (optional, for learn operations)

**Usage in Commands**:
```python
# Before (memory_commands.py:103)
db_path = get_project_db_path(ctx.obj.get("project_root"))
with KuzuMemory(db_path=db_path) as memory:
    memory_id = memory.remember(...)

# After
memory_service = ctx.obj['memory_service']
result = memory_service.store_memory(content, source, session_id, agent_id, metadata)
```

---

#### 2. **InstallerService** (High Priority)
**Responsibilities**:
- Installer discovery and lifecycle
- Installation validation and health checks
- Multi-installer coordination (auto-detection)
- MCP configuration repair

**Interface**:
```python
class InstallerServiceProtocol(Protocol):
    def detect_installed_systems(self) -> list[InstalledSystem]:
        """Detect all installed AI systems in project."""
        ...

    def install_integration(
        self,
        integration: str,
        dry_run: bool = False,
        verbose: bool = False
    ) -> InstallResult:
        """Install integration with validation."""
        ...

    def uninstall_integration(
        self,
        integration: str,
        verbose: bool = False
    ) -> UninstallResult:
        """Uninstall integration with cleanup."""
        ...

    def repair_mcp_configs(self) -> RepairResult:
        """Auto-repair broken MCP configurations."""
        ...

    def get_installer_for(self, integration: str) -> BaseInstaller | None:
        """Get installer instance (factory method)."""
        ...
```

**Dependencies**:
- `InstallerRegistry` (existing)
- `ConfigService` (for project_root)

**Usage in Commands**:
```python
# Before (install_unified.py:235)
installer = get_installer(integration, root)
if not installer:
    rich_print(f"❌ No installer found")
    sys.exit(1)
result = installer.install(dry_run=dry_run)

# After
installer_service = ctx.obj['installer_service']
result = installer_service.install_integration(integration, dry_run=dry_run)
if not result.success:
    rich_print(f"❌ {result.error_message}")
```

---

#### 3. **ConfigService** (High Priority)
**Responsibilities**:
- Project root detection and validation
- DB path resolution
- Configuration loading/saving
- Environment-specific config management

**Interface**:
```python
class ConfigServiceProtocol(Protocol):
    def get_project_root(self) -> Path:
        """Get validated project root."""
        ...

    def get_db_path(self) -> Path:
        """Resolve database path for current project."""
        ...

    def load_config(self, config_path: str | None = None) -> KuzuMemoryConfig:
        """Load configuration with fallback chain."""
        ...

    def save_config(self, config: KuzuMemoryConfig, path: Path) -> None:
        """Save configuration to file."""
        ...
```

**Dependencies**:
- `project_setup` utilities (wrapped)
- `config_loader` utilities (wrapped)

**Usage in Commands**:
```python
# Before (scattered across files)
project_root = ctx.obj.get("project_root") or find_project_root()
db_path = get_project_db_path(project_root)
config_loader = get_config_loader()
loaded_config = config_loader.load_config(project_root)

# After (injected once in main CLI)
config_service = ctx.obj['config_service']
db_path = config_service.get_db_path()
config = config_service.load_config()
```

---

#### 4. **SetupService** (Medium Priority)
**Responsibilities**:
- Smart setup orchestration (init + install)
- Project initialization workflow
- Post-init hook management
- Auggie integration detection

**Interface**:
```python
class SetupServiceProtocol(Protocol):
    def smart_setup(
        self,
        integration: str | None = None,
        force: bool = False
    ) -> SetupResult:
        """Orchestrate full setup (init + install)."""
        ...

    def init_project(
        self,
        force: bool = False,
        config_path: str | None = None
    ) -> InitResult:
        """Initialize project database."""
        ...

    def detect_auggie_integration(self) -> bool:
        """Check if project has Auggie integration."""
        ...

    def setup_auggie_integration(self) -> bool:
        """Setup Auggie integration if detected."""
        ...
```

**Dependencies**:
- `MemoryService` (for DB operations)
- `InstallerService` (for installation)
- `ConfigService` (for project info)

---

#### 5. **DiagnosticService** (Medium Priority)
**Responsibilities**:
- Health validation checks
- Performance diagnostics
- Database integrity checks
- System status reporting

**Interface**:
```python
class DiagnosticServiceProtocol(Protocol):
    def run_health_checks(self) -> HealthCheckResult:
        """Run comprehensive health validation."""
        ...

    def get_system_status(
        self,
        detailed: bool = False
    ) -> SystemStatus:
        """Get system status and statistics."""
        ...

    def validate_database(self) -> ValidationResult:
        """Validate database integrity."""
        ...

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance metrics."""
        ...
```

---

#### 6. **GitSyncService** (Low Priority - Utility Wrapper)
**Responsibilities**:
- Git commit history synchronization
- Git user detection
- Sync status reporting

**Interface**:
```python
class GitSyncServiceProtocol(Protocol):
    def sync_git_history(
        self,
        since: str | None = None,
        limit: int | None = None
    ) -> GitSyncResult:
        """Sync git commit history to memory."""
        ...

    def get_git_user(self) -> GitUser | None:
        """Get current git user information."""
        ...
```

---

## Dependency Injection Strategy

### Current DI Infrastructure (Underutilized):

**Existing** (core/dependencies.py):
```python
class DependencyContainer:
    def register(self, name: str, service: Any, singleton: bool = True) -> None:
        """Register service or factory."""
        ...

    def get(self, name: str) -> Any:
        """Get service by name."""
        ...

    # Typed accessors
    def get_memory_store(self) -> MemoryStoreProtocol:
        ...

    def get_recall_coordinator(self) -> RecallCoordinatorProtocol:
        ...
```

**Problem**: Used only in `KuzuMemory` class, not in CLI layer

### Proposed DI Pattern: **Constructor Injection via Click Context**

**Main CLI Setup** (commands.py):
```python
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context, debug: bool, config: str | None, ...) -> None:
    """Main CLI entry point."""
    ctx.ensure_object(dict)

    # ✅ NEW: Build service container
    container = build_cli_service_container(
        project_root=resolved_root,
        config=loaded_config,
        debug=debug
    )

    # ✅ NEW: Inject services into context
    ctx.obj['memory_service'] = container.get_memory_service()
    ctx.obj['installer_service'] = container.get_installer_service()
    ctx.obj['config_service'] = container.get_config_service()
    ctx.obj['diagnostic_service'] = container.get_diagnostic_service()
    ctx.obj['setup_service'] = container.get_setup_service()
```

**Service Container Builder** (NEW: cli/service_container.py):
```python
def build_cli_service_container(
    project_root: Path | None,
    config: KuzuMemoryConfig,
    debug: bool = False
) -> CLIServiceContainer:
    """
    Build and configure the CLI service container.

    This is the SINGLE POINT where all services are instantiated
    and dependencies are wired together.
    """
    container = CLIServiceContainer()

    # Register config service (no dependencies)
    config_service = ConfigService(
        project_root=project_root,
        config=config
    )
    container.register('config_service', config_service)

    # Register memory service (depends on config_service)
    memory_service = MemoryService(
        config_service=config_service,
        enable_git_sync=config.enable_git_sync
    )
    container.register('memory_service', memory_service)

    # Register installer service (depends on config_service)
    installer_service = InstallerService(
        config_service=config_service,
        installer_registry=get_global_installer_registry()
    )
    container.register('installer_service', installer_service)

    # Register diagnostic service (depends on memory_service, config_service)
    diagnostic_service = DiagnosticService(
        memory_service=memory_service,
        config_service=config_service
    )
    container.register('diagnostic_service', diagnostic_service)

    # Register setup service (depends on memory, installer, config)
    setup_service = SetupService(
        memory_service=memory_service,
        installer_service=installer_service,
        config_service=config_service
    )
    container.register('setup_service', setup_service)

    return container
```

**Command Usage** (memory_commands.py):
```python
@memory.command()
@click.pass_context
def store(ctx: click.Context, content: str, source: str, ...) -> None:
    """Store a memory."""
    # ✅ Get injected service
    memory_service: MemoryService = ctx.obj['memory_service']

    try:
        # ✅ Business logic delegated to service
        result = memory_service.store_memory(
            content=content,
            source=source,
            session_id=session_id,
            agent_id=agent_id,
            metadata=metadata
        )

        # ✅ Only presentation logic in command
        rich_print(f"✅ {result.success_message}", style="green")
        if result.memory_id:
            rich_print(f"   Memory ID: {result.memory_id[:8]}...", style="dim")

    except MemoryServiceError as e:
        rich_print(f"❌ {e.user_message}", style="red")
        if ctx.obj.get('debug'):
            raise
        sys.exit(1)
```

---

## Testability Impact Analysis

### Current Testability: **POOR**

**Issues**:
1. Cannot test commands without real database
2. Cannot mock installers or external dependencies
3. Integration tests only (slow, brittle)
4. Hard to test error conditions

**Current Test** (impossible to write):
```python
# ❌ Cannot test this - requires real DB and filesystem
def test_store_command():
    runner = CliRunner()
    result = runner.invoke(store, ['Test memory'])
    # Requires real project root, real DB, real filesystem
```

### After Refactoring: **EXCELLENT**

**Unit Test Example**:
```python
def test_store_command_success(mocker):
    """Test store command with mocked service."""
    # ✅ Mock the service
    mock_memory_service = mocker.Mock(spec=MemoryService)
    mock_memory_service.store_memory.return_value = MemoryStoreResult(
        success=True,
        memory_id="abc123",
        success_message="Stored memory successfully"
    )

    # ✅ Inject mock into context
    runner = CliRunner()
    result = runner.invoke(
        store,
        ['Test memory'],
        obj={'memory_service': mock_memory_service}
    )

    # ✅ Assertions
    assert result.exit_code == 0
    assert "✅ Stored memory successfully" in result.output
    mock_memory_service.store_memory.assert_called_once_with(
        content='Test memory',
        source='cli',
        session_id=None,
        agent_id='cli',
        metadata=None
    )

def test_store_command_database_error(mocker):
    """Test store command error handling."""
    # ✅ Mock service to raise error
    mock_memory_service = mocker.Mock(spec=MemoryService)
    mock_memory_service.store_memory.side_effect = DatabaseError("Connection failed")

    runner = CliRunner()
    result = runner.invoke(
        store,
        ['Test memory'],
        obj={'memory_service': mock_memory_service}
    )

    # ✅ Verify error handling
    assert result.exit_code == 1
    assert "❌" in result.output
    assert "Connection failed" in result.output
```

---

## Migration Strategy: INCREMENTAL

**Recommended Approach**: **Phase-by-phase incremental migration** (NOT big-bang)

### Phase 1: Foundation (Week 1)
**Goal**: Establish service layer infrastructure

**Tasks**:
1. Create `cli/services/` directory structure
2. Implement `CLIServiceContainer` and builder function
3. Define all service protocols in `cli/services/protocols.py`
4. Update `commands.py` to build and inject container
5. Add backward compatibility layer (existing commands still work)

**Deliverables**:
- `cli/services/__init__.py`
- `cli/services/protocols.py` (all Protocol definitions)
- `cli/services/container.py` (DI container + builder)
- Updated `commands.py` with container injection

**Risk**: LOW (additive changes only, no breaking changes)

---

### Phase 2: MemoryService Migration (Week 2)
**Goal**: Extract and inject MemoryService

**Tasks**:
1. Implement `MemoryService` class
2. Migrate `memory_commands.py` to use injected service
3. Add comprehensive unit tests for MemoryService
4. Add integration tests for memory commands with mocks
5. Update documentation

**Deliverables**:
- `cli/services/memory_service.py`
- `tests/unit/services/test_memory_service.py`
- `tests/integration/test_memory_commands.py`

**Risk**: MEDIUM (changes command internals, but CLI interface unchanged)

---

### Phase 3: ConfigService + InstallerService (Week 3)
**Goal**: Extract configuration and installer management

**Tasks**:
1. Implement `ConfigService` (wrap project_setup utilities)
2. Implement `InstallerService` (wrap registry + add coordination)
3. Migrate `init_commands.py` and `install_unified.py`
4. Add unit tests for both services
5. Refactor context setup in `commands.py` to use ConfigService

**Deliverables**:
- `cli/services/config_service.py`
- `cli/services/installer_service.py`
- Updated command files

**Risk**: MEDIUM (affects initialization flow)

---

### Phase 4: Remaining Services (Week 4)
**Goal**: Complete service layer migration

**Tasks**:
1. Implement `SetupService`, `DiagnosticService`, `GitSyncService`
2. Migrate remaining command files
3. Complete test coverage
4. Update all documentation

**Deliverables**:
- All remaining service implementations
- 100% test coverage for services
- Updated architecture docs

**Risk**: LOW (following established pattern)

---

### Phase 5: Cleanup & Optimization (Week 5)
**Goal**: Remove technical debt and optimize

**Tasks**:
1. Remove old utility wrapper functions (if unused)
2. Consolidate error handling
3. Performance optimization
4. Refactoring documentation
5. Migration guide for contributors

**Risk**: LOW (cleanup only)

---

## Breaking Changes Analysis

### User-Facing Impact: **NONE**

**CLI Interface**: Unchanged
```bash
# Before refactoring
kuzu-memory memory store "Test memory"
kuzu-memory install claude-code
kuzu-memory status

# After refactoring (IDENTICAL)
kuzu-memory memory store "Test memory"
kuzu-memory install claude-code
kuzu-memory status
```

### Internal API Impact: **MINIMAL**

**Breaking Changes**:
1. **None for CLI users** (commands work identically)
2. **None for library users** (KuzuMemory API unchanged)
3. **Internal CLI testing** (need to inject mocks instead of integration tests)

**Non-Breaking Changes**:
1. New service classes (additive)
2. New protocols (additive)
3. DI container (additive, opt-in)

---

## Recommended Approach Summary

### DI Framework: **Manual DI** (NOT dependency-injector library)

**Rationale**:
1. ✅ Project already has `DependencyContainer` class
2. ✅ Simple, explicit, easy to understand
3. ✅ No external dependencies
4. ✅ Full control over lifecycle
5. ✅ Easier debugging than framework magic

**Comparison**:
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Manual DI | Simple, explicit, no deps | More boilerplate | ✅ **RECOMMENDED** |
| dependency-injector | Feature-rich, autowiring | Learning curve, external dep | ❌ Overkill |
| injector | Pythonic, type-safe | External dep, less popular | ❌ Unnecessary |

---

### Service Layer Pattern: **Application Service Pattern**

**Architecture**:
```
CLI Layer (Presentation)
    ↓ depends on
Application Services (Business Logic Orchestration)
    ↓ uses
Domain Objects (Core Business Logic)
    ↓ uses
Infrastructure (Database, Filesystem, External APIs)
```

**Benefits**:
- Clear separation of concerns
- Easy to test (mock services)
- Easy to swap implementations
- Reusable across CLI/API/MCP layers

---

### Interface Strategy: **Protocol-based** (NOT ABC)

**Rationale**:
1. ✅ Project already uses Protocol pattern (see `dependencies.py`)
2. ✅ Structural subtyping (duck typing with types)
3. ✅ No runtime overhead
4. ✅ Better for testing (easier to mock)
5. ✅ More Pythonic than ABC

**Example**:
```python
from typing import Protocol

class MemoryServiceProtocol(Protocol):
    def store_memory(self, content: str, ...) -> MemoryStoreResult:
        ...

# ✅ Any class matching this signature automatically implements protocol
# ✅ No need for explicit inheritance
# ✅ Easy to create test doubles
```

---

## Refactoring Complexity Estimate

### Lines to Refactor: ~2000 lines
- **commands.py**: 100 lines (container setup)
- **memory_commands.py**: 400 lines (service injection)
- **install_unified.py**: 300 lines (service injection)
- **init_commands.py**: 100 lines (service injection)
- **Other command files**: 600 lines
- **New service layer**: 500 lines (new code)

### Time Estimate: 4-5 weeks (1 developer)
- Week 1: Infrastructure + protocols
- Week 2: MemoryService migration
- Week 3: Config + Installer services
- Week 4: Remaining services
- Week 5: Testing + documentation

### Complexity: **MEDIUM**
- Well-defined boundaries (already modular)
- Clear patterns to follow (Protocol + DI)
- Good test coverage needed (adds time)
- Low breaking change risk (internal only)

---

## Code Examples: Before/After

### Example 1: Memory Store Command

**BEFORE** (memory_commands.py:83-127):
```python
@memory.command()
@click.argument("content", required=True)
@click.option("--source", default="cli")
@click.option("--session-id")
@click.option("--agent-id", default="cli")
@click.option("--metadata")
@click.pass_context
def store(ctx, content, source, session_id, agent_id, metadata):
    """Store a memory."""
    try:
        # ❌ Mixed: Config + parsing + business + presentation
        db_path = get_project_db_path(ctx.obj.get("project_root"))

        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                rich_print(f"⚠️  Invalid JSON: {e}", style="yellow")

        parsed_metadata.update({
            "cli_timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "agent_id": agent_id,
        })

        # ❌ Direct instantiation
        with KuzuMemory(db_path=db_path) as memory:
            memory_id = memory.remember(
                content=content,
                source=source,
                session_id=session_id,
                agent_id=agent_id,
                metadata=parsed_metadata,
            )

        # Presentation
        rich_print(f"✅ Stored memory: {content[:100]}", style="green")
        if memory_id:
            rich_print(f"   Memory ID: {memory_id[:8]}...", style="dim")

    except Exception as e:
        if ctx.obj.get("debug"):
            raise
        rich_print(f"❌ Memory storage failed: {e}", style="red")
        sys.exit(1)
```

**AFTER** (memory_commands.py):
```python
@memory.command()
@click.argument("content", required=True)
@click.option("--source", default="cli")
@click.option("--session-id")
@click.option("--agent-id", default="cli")
@click.option("--metadata")
@click.pass_context
def store(ctx, content, source, session_id, agent_id, metadata):
    """Store a memory."""
    # ✅ Get injected service
    memory_service: MemoryService = ctx.obj['memory_service']

    try:
        # ✅ Parse metadata (presentation concern)
        parsed_metadata = None
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                rich_print(f"⚠️  Invalid JSON: {e}", style="yellow")
                return

        # ✅ Delegate to service
        result = memory_service.store_memory(
            content=content,
            source=source,
            session_id=session_id,
            agent_id=agent_id,
            metadata=parsed_metadata
        )

        # ✅ Only presentation logic
        rich_print(f"✅ {result.message}", style="green")
        if result.memory_id:
            rich_print(f"   Memory ID: {result.memory_id[:8]}...", style="dim")
        rich_print(f"   Source: {source}", style="dim")
        if session_id:
            rich_print(f"   Session: {session_id}", style="dim")

    except MemoryServiceError as e:
        # ✅ Service-specific exceptions
        rich_print(f"❌ {e.user_message}", style="red")
        if ctx.obj.get("debug"):
            logger.exception("Memory storage failed")
        sys.exit(1)
```

**MemoryService Implementation** (NEW: cli/services/memory_service.py):
```python
class MemoryService:
    """
    Service for memory operations.

    Handles business logic for storing, recalling, and managing memories.
    """

    def __init__(
        self,
        config_service: ConfigService,
        enable_git_sync: bool = True
    ):
        """
        Initialize memory service.

        Args:
            config_service: Configuration service for DB path resolution
            enable_git_sync: Whether to enable git sync (default: True)
        """
        self.config_service = config_service
        self.enable_git_sync = enable_git_sync
        self._memory_cache: dict[str, KuzuMemory] = {}

    def store_memory(
        self,
        content: str,
        source: str = "cli",
        session_id: str | None = None,
        agent_id: str = "cli",
        metadata: dict[str, Any] | None = None
    ) -> MemoryStoreResult:
        """
        Store a new memory.

        Args:
            content: Memory content
            source: Memory source identifier
            session_id: Optional session grouping
            agent_id: Agent that created memory
            metadata: Additional metadata

        Returns:
            Result object with memory_id and status

        Raises:
            MemoryServiceError: If storage fails
        """
        try:
            # Validate content
            if not content or not content.strip():
                raise MemoryServiceError(
                    "Content cannot be empty",
                    user_message="Please provide memory content"
                )

            # Get DB path from config service
            db_path = self.config_service.get_db_path()

            # Enrich metadata with CLI context
            enriched_metadata = metadata or {}
            enriched_metadata.update({
                "cli_timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "agent_id": agent_id,
            })

            # Store memory
            with KuzuMemory(db_path=db_path, enable_git_sync=self.enable_git_sync) as memory:
                memory_id = memory.remember(
                    content=content,
                    source=source,
                    session_id=session_id,
                    agent_id=agent_id,
                    metadata=enriched_metadata
                )

            return MemoryStoreResult(
                success=True,
                memory_id=memory_id,
                message=f"Stored memory: {content[:100]}{'...' if len(content) > 100 else ''}"
            )

        except DatabaseError as e:
            logger.error(f"Database error storing memory: {e}")
            raise MemoryServiceError(
                f"Database error: {e}",
                user_message="Failed to store memory due to database error. Please check database connection."
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error storing memory: {e}")
            raise MemoryServiceError(
                f"Unexpected error: {e}",
                user_message="An unexpected error occurred. Please try again or contact support."
            ) from e
```

---

### Example 2: Install Command

**BEFORE** (install_unified.py:161-316):
```python
@click.command(name="install")
@click.argument("integration", type=click.Choice(AVAILABLE_INTEGRATIONS), required=False)
@click.option("--project-root", type=click.Path(exists=True))
@click.option("--force", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True)
def install_command(integration, project_root, force, dry_run, verbose):
    """Install kuzu-memory integration."""
    try:
        # ❌ Direct project root resolution
        if project_root:
            root = Path(project_root).resolve()
        else:
            try:
                root = find_project_root()
            except Exception:
                root = Path.cwd()

        # ❌ Direct auto-detection logic
        if integration is None:
            detected_systems = _detect_installed_systems(root)
            integration = _show_detection_menu(detected_systems)
            if integration is None:
                sys.exit(0)

        # ❌ Direct installer retrieval
        installer = get_installer(integration, root)
        if not installer:
            rich_print(f"❌ No installer found: {integration}", style="red")
            sys.exit(1)

        # ❌ Direct installation
        result = installer.install(dry_run=dry_run, verbose=verbose)

        # ❌ Mixed: Post-install repair + presentation
        if result.success:
            rich_panel(result.message, title="✅ Installation Complete")
            if not dry_run:
                num_fixes, fix_messages = _repair_all_mcp_configs()
                if num_fixes > 0:
                    rich_print(f"🔧 Auto-repaired {num_fixes} configs")
        else:
            rich_print(f"❌ {result.message}", style="red")
            sys.exit(1)

    except Exception as e:
        rich_print(f"❌ Installation failed: {e}", style="red")
        sys.exit(1)
```

**AFTER** (install_unified.py):
```python
@click.command(name="install")
@click.argument("integration", type=click.Choice(AVAILABLE_INTEGRATIONS), required=False)
@click.option("--force", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True)
@click.pass_context
def install_command(ctx, integration, force, dry_run, verbose):
    """Install kuzu-memory integration."""
    # ✅ Get injected services
    installer_service: InstallerService = ctx.obj['installer_service']

    try:
        # ✅ Auto-detection via service
        if integration is None:
            detection_result = installer_service.detect_installed_systems()

            # ✅ Presentation logic only
            rich_panel(
                f"Detected {len(detection_result.systems)} installed system(s)",
                title="🔍 Auto-Detection",
                style="cyan"
            )

            # Show detection menu (presentation helper)
            integration = _show_detection_menu(detection_result.systems)
            if integration is None:
                rich_print("Installation cancelled.", style="yellow")
                return

        # ✅ Installation via service
        result = installer_service.install_integration(
            integration=integration,
            force=force,
            dry_run=dry_run,
            verbose=verbose
        )

        # ✅ Only presentation logic
        if result.success:
            rich_panel(result.message, title="✅ Installation Complete", style="green")

            if result.files_created:
                rich_print("\n📄 Files created:")
                for file_path in result.files_created:
                    rich_print(f"  • {file_path}", style="green")

            if result.files_modified:
                rich_print("\n📝 Files modified:")
                for file_path in result.files_modified:
                    rich_print(f"  • {file_path}", style="yellow")

            if result.mcp_configs_repaired > 0:
                rich_print(
                    f"\n🔧 Auto-repaired {result.mcp_configs_repaired} MCP configuration(s)",
                    style="cyan"
                )

            # Show integration-specific next steps
            _show_next_steps(integration, result)
        else:
            rich_print(f"\n❌ {result.message}", style="red")
            if result.errors:
                for error in result.errors:
                    rich_print(f"  • {error}", style="red")
            sys.exit(1)

    except InstallerServiceError as e:
        rich_print(f"❌ Installation failed: {e.user_message}", style="red")
        if verbose or ctx.obj.get("debug"):
            logger.exception("Installation error")
        sys.exit(1)
```

**InstallerService Implementation** (NEW: cli/services/installer_service.py):
```python
class InstallerService:
    """
    Service for managing installer operations.

    Coordinates installer discovery, installation, and health management.
    """

    def __init__(
        self,
        config_service: ConfigService,
        installer_registry: InstallerRegistry
    ):
        """
        Initialize installer service.

        Args:
            config_service: Configuration service for project info
            installer_registry: Registry of available installers
        """
        self.config_service = config_service
        self.installer_registry = installer_registry

    def detect_installed_systems(self) -> DetectionResult:
        """
        Detect all installed AI systems in current project.

        Returns:
            Detection result with list of installed systems
        """
        project_root = self.config_service.get_project_root()
        installed_systems = []

        for installer_name in AVAILABLE_INTEGRATIONS:
            try:
                installer = self.installer_registry.get_installer(
                    installer_name,
                    project_root
                )
                if installer:
                    detected = installer.detect_installation()
                    if detected.is_installed:
                        installed_systems.append(detected)
            except Exception as e:
                logger.debug(f"Detection failed for {installer_name}: {e}")
                continue

        return DetectionResult(
            systems=installed_systems,
            project_root=project_root
        )

    def install_integration(
        self,
        integration: str,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False
    ) -> InstallResult:
        """
        Install integration with validation and post-install tasks.

        Args:
            integration: Integration name
            force: Force reinstall
            dry_run: Preview changes only
            verbose: Show detailed output

        Returns:
            Installation result

        Raises:
            InstallerServiceError: If installation fails
        """
        try:
            # Get project root
            project_root = self.config_service.get_project_root()

            # Get installer
            installer = self.installer_registry.get_installer(integration, project_root)
            if not installer:
                raise InstallerServiceError(
                    f"No installer found for: {integration}",
                    user_message=f"Integration '{integration}' is not available. "
                                f"Run 'kuzu-memory install --help' to see available options."
                )

            # Perform installation
            install_result = installer.install(dry_run=dry_run, verbose=verbose)

            # Post-install: Auto-repair MCP configs (if not dry-run)
            mcp_fixes = 0
            if install_result.success and not dry_run:
                mcp_fixes = self._repair_all_mcp_configs()

            # Build comprehensive result
            return InstallResult(
                success=install_result.success,
                message=install_result.message,
                files_created=install_result.files_created,
                files_modified=install_result.files_modified,
                warnings=install_result.warnings,
                mcp_configs_repaired=mcp_fixes
            )

        except Exception as e:
            logger.error(f"Installation failed for {integration}: {e}")
            raise InstallerServiceError(
                f"Installation error: {e}",
                user_message="Installation failed. Please check logs or try again with --verbose flag."
            ) from e

    def _repair_all_mcp_configs(self) -> int:
        """
        Auto-repair broken MCP configurations.

        Returns:
            Number of configurations repaired
        """
        claude_json = Path.home() / ".claude.json"
        if not claude_json.exists():
            return 0

        try:
            config = load_json_config(claude_json)
            fixed_config, fixes = fix_broken_mcp_args(config)

            if fixes:
                save_json_config(claude_json, fixed_config)
                logger.info(f"Auto-repaired {len(fixes)} MCP configuration(s)")
                return len(fixes)

            return 0
        except Exception as e:
            logger.warning(f"MCP config repair failed: {e}")
            return 0
```

---

## Conclusion

### Key Findings:

1. **Current Architecture**: Hybrid modular CLI with direct instantiation anti-pattern
2. **Coupling Level**: HIGH (40+ direct instantiations across CLI)
3. **Existing Infrastructure**: DI container + Protocol patterns already exist (underutilized)
4. **Service Boundaries**: 6 clear services identified (Memory, Installer, Config, Setup, Diagnostic, GitSync)
5. **Refactoring Scope**: ~2000 lines, 4-5 weeks, MEDIUM complexity
6. **Breaking Changes**: NONE for users, MINIMAL for internal APIs
7. **Testability Impact**: POOR → EXCELLENT (unit tests become possible)

### Recommendations:

✅ **DO THIS**:
1. Implement incremental migration (5 phases over 5 weeks)
2. Use manual DI (not framework) - leverage existing `DependencyContainer`
3. Use Protocol-based interfaces (consistent with existing code)
4. Start with MemoryService (highest ROI)
5. Build comprehensive unit tests for each service
6. Maintain 100% backward compatibility for CLI interface

❌ **DON'T DO THIS**:
1. Big-bang refactoring (too risky)
2. Use dependency-injector framework (overkill for this project)
3. Change CLI interface (user-facing breaking changes)
4. Skip testing (defeats purpose of refactoring)

### Next Steps:

1. **Review this analysis** with team/maintainers
2. **Approve migration strategy** (incremental vs. other approach)
3. **Create implementation tickets** for each phase
4. **Start Phase 1** (foundation + protocols)
5. **Iterate and refine** based on learnings from Phase 1

---

**Analysis Complete**: 2025-11-30
**Researcher**: Claude (Sonnet 4.5)
**Confidence Level**: HIGH (based on thorough code review and pattern analysis)
