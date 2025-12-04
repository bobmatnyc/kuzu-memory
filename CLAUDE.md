# KuzuMemory - Development Guide for AI Assistants

KuzuMemory is a lightweight, embedded graph-based memory system for AI applications that provides intelligent context management and temporal knowledge retrieval.

## Project Overview

**Purpose**: Provide AI applications with project-specific memory and context awareness
**Architecture**: Kùzu graph database + sentence-transformers embeddings + temporal decay
**Language**: Python 3.12+
**Key Frameworks**: Click (CLI), Pydantic (validation), FastAPI (future MCP server)

## Technology Stack

- **Database**: Kùzu Graph Database (embedded, file-based)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **CLI Framework**: Click 8.0+
- **Validation**: Pydantic 2.0+
- **Testing**: pytest, pytest-asyncio
- **Type Checking**: mypy (strict mode)
- **Code Quality**: ruff (linting + formatting)

## Architecture Overview

```
kuzu-memory/
├── src/kuzu_memory/
│   ├── core/           # Core memory operations (graph DB + embeddings)
│   ├── services/       # Service layer (DI pattern, lifecycle management)
│   ├── cli/            # Click commands (thin wrappers around services)
│   ├── mcp/            # MCP server implementation (JSON-RPC 2.0)
│   ├── installers/     # Integration installers (Claude Code, Cursor, etc.)
│   ├── integrations/   # Third-party integrations (Auggie, git hooks)
│   └── utils/          # Shared utilities
├── tests/              # pytest test suite
├── scripts/            # Build and release automation
└── docs/               # Documentation and design specs
```

## Development Principles

### 1. Service-Oriented Architecture (SOA)

All business logic is in **services** with dependency injection:

```python
# ✅ CORRECT: Services handle logic
from kuzu_memory.services import MemoryService

with MemoryService(db_path) as memory:
    memory.remember("content", source="test")

# ❌ WRONG: Direct database access in CLI
import kuzu
db = kuzu.Database(str(db_path))  # Violates SOA
```

**Why**: Testability, maintainability, clear separation of concerns

### 2. Async by Default for Learning

```python
# Learning operations are async and non-blocking
memory.learn("content", source="conversation")  # Async by default

# Enhancement operations are sync (needed for immediate response)
result = memory.enhance("query")  # Synchronous
```

**Performance Requirements**:
- Enhancement: <100ms (blocking operation)
- Learning: <200ms (async, non-blocking)
- Recall: <50ms (graph query optimization)

### 3. Type Safety with Pydantic

```python
from pydantic import BaseModel, Field

class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    source: str = Field(default="manual")
    tags: list[str] = Field(default_factory=list)
```

**Why**: Runtime validation, self-documenting code, IDE support

### 4. Click CLI Best Practices

```python
@click.command()
@click.argument("content")
@click.option("--source", default="manual", help="Memory source")
@click.pass_context
def remember(ctx: click.Context, content: str, source: str) -> None:
    """Store a new memory."""
    # Thin wrapper - delegate to service
    with ServiceManager.memory_service(ctx.obj["db_path"]) as memory:
        memory.remember(content, source=source)
```

## Development Workflow

### Setup Development Environment

```bash
# Clone and install in editable mode
git clone https://github.com/bobmatnyc/kuzu-memory.git
cd kuzu-memory
python -m pip install -e ".[dev]"

# Run quality gates before committing
make pre-publish  # Runs: ruff, black, isort, mypy, pytest
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kuzu_memory --cov-report=html

# Run specific test file
pytest tests/unit/test_memory_service.py

# Run with debug output
pytest -v -s
```

### Code Quality Gates

All code must pass these checks before commit:

```bash
make pre-publish
# ✅ Ruff linting (no errors)
# ✅ Black formatting (all files formatted)
# ✅ isort import sorting (all imports organized)
# ✅ mypy type checking (strict mode, informational warnings OK)
# ✅ pytest (all tests passing)
```

### Release Process

```bash
# 1. Run quality gates
make pre-publish

# 2. Bump version (patch/minor/major)
./scripts/manage_version.py bump patch

# 3. Build and publish
make safe-release-build  # Includes quality gates
make release-pypi        # Upload to PyPI

# 4. Create GitHub release
gh release create v$(cat VERSION) --generate-notes
```

## Testing Guidelines

### Unit Tests (Fast, Isolated)

```python
def test_remember_stores_memory(mock_db_path):
    """Test that remember() stores content correctly."""
    with MemoryService(mock_db_path) as memory:
        result = memory.remember("test content", source="test")

        assert result["success"] is True
        assert result["memory_id"] is not None
```

### Integration Tests (Real Database)

```python
@pytest.mark.integration
def test_end_to_end_memory_lifecycle(tmp_path):
    """Test complete lifecycle: store -> enhance -> recall."""
    db_path = tmp_path / "test.db"

    with MemoryService(db_path) as memory:
        # Store
        memory.remember("FastAPI with PostgreSQL", source="test")

        # Enhance
        result = memory.enhance("How to build API?")
        assert "FastAPI" in result["enhanced_prompt"]

        # Recall
        memories = memory.recall("database")
        assert len(memories) > 0
```

### Test Organization

```
tests/
├── unit/              # Fast, mocked tests
│   ├── test_memory_service.py
│   ├── test_config_service.py
│   └── test_embedding.py
├── integration/       # Real database tests
│   ├── test_cli_commands.py
│   └── test_mcp_server.py
└── fixtures/          # Shared test fixtures
    └── conftest.py
```

## Common Development Tasks

### Adding a New CLI Command

1. **Create service method** (if needed):
```python
# src/kuzu_memory/services/memory_service.py
def export_memories(self, format: str = "json") -> dict:
    """Export all memories to specified format."""
    # Implementation
```

2. **Create Click command**:
```python
# src/kuzu_memory/cli/memory_commands.py
@click.command()
@click.option("--format", type=click.Choice(["json", "csv"]))
@click.pass_context
def export(ctx: click.Context, format: str) -> None:
    """Export memories to file."""
    with ServiceManager.memory_service(ctx.obj["db_path"]) as memory:
        result = memory.export_memories(format=format)
        rich_print(result)
```

3. **Register command**:
```python
# src/kuzu_memory/cli/cli.py
memory_group.add_command(export)
```

4. **Add tests**:
```python
# tests/unit/test_memory_commands.py
def test_export_command(cli_runner, mock_db):
    result = cli_runner.invoke(cli, ["memory", "export", "--format", "json"])
    assert result.exit_code == 0
```

### Adding a New Integration

1. **Create installer** in `src/kuzu_memory/installers/`
2. **Implement `BaseInstaller` protocol**
3. **Register in `installers/registry.py`**
4. **Add to `AVAILABLE_INTEGRATIONS` in `cli/install_unified.py`**
5. **Test installation with `kuzu-memory install <name> --dry-run`**

## Error Handling Patterns

```python
from kuzu_memory.exceptions import MemoryServiceError

# ✅ CORRECT: Specific exceptions with context
try:
    memory.remember(content)
except MemoryServiceError as e:
    logger.error(f"Failed to store memory: {e}")
    rich_print(f"❌ Error: {e}", style="red")
    sys.exit(1)

# ❌ WRONG: Generic exceptions
try:
    memory.remember(content)
except Exception:  # Too broad
    pass
```

## Documentation Standards

- **Docstrings**: Google style with type hints
- **Comments**: Explain "why", not "what"
- **README**: User-facing, installation + quick start
- **CLAUDE.md**: This file - development guide for AI
- **docs/**: Detailed architecture, design decisions, research

## Git Workflow

```bash
# Feature branch workflow
git checkout -b fix/sentinel-error
# Make changes
git add src/kuzu_memory/cli/setup_commands.py
git commit -m "fix: resolve Sentinel error in setup command

Removed explicit config_path=None from ctx.invoke() calls
to avoid click Path type converter issues.

Fixes: #123"

# Push and create PR
git push origin fix/sentinel-error
gh pr create
```

## Performance Optimization

### Database Query Optimization

```cypher
// ✅ CORRECT: Use indexes and limit results
MATCH (m:Memory)
WHERE m.timestamp > $recent_threshold
RETURN m ORDER BY m.timestamp DESC LIMIT 10

// ❌ WRONG: Unbounded queries
MATCH (m:Memory) RETURN m  // Can return millions of nodes
```

### Embedding Cache

```python
# Embeddings are cached automatically
# Only recompute when content changes
embedding = self.embedding_service.embed(content)  # Cached
```

## Security Considerations

- **No secrets in code**: Use environment variables
- **Path validation**: Always validate file paths to prevent traversal
- **Input sanitization**: Validate all user input with Pydantic
- **Database isolation**: One database per project, no shared state

## Troubleshooting

### Common Issues

**Issue**: `kuzu-memory: command not found`
**Fix**: Reinstall in editable mode: `pip install -e .`

**Issue**: Type checking errors with mypy
**Fix**: Check `pyproject.toml` for mypy configuration, ensure strict mode

**Issue**: Tests fail with "Database already exists"
**Fix**: Use `tmp_path` fixture in tests, or add `force=True` flag

**Issue**: MCP server not connecting
**Fix**: Check `~/.claude.json` configuration, verify server path

## Resources

- **GitHub**: https://github.com/bobmatnyc/kuzu-memory
- **PyPI**: https://pypi.org/project/kuzu-memory/
- **Kùzu Docs**: https://kuzudb.com/docs/
- **MCP Spec**: https://modelcontextprotocol.io/

## Questions?

Check `docs/` directory for:
- Architecture decisions
- Design specifications
- Research notes
- API reference

---

**Last Updated**: 2025-12-04
**Version**: 1.6.1
