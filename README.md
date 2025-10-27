# KuzuMemory

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/kuzu-memory/kuzu-memory/workflows/Tests/badge.svg)](https://github.com/kuzu-memory/kuzu-memory/actions)

**Lightweight, embedded graph-based memory system for AI applications**

KuzuMemory provides fast, offline memory capabilities for chatbots and AI systems without requiring LLM calls. It uses pattern matching and local graph storage to remember and recall contextual information.

## ✨ Key Features

- **🧠 Cognitive Memory Model** - Based on human memory psychology (SEMANTIC, PROCEDURAL, EPISODIC, etc.)
- **🚀 No LLM Dependencies** - Operates using pattern matching and local NER only
- **⚡ Fast Performance** - <3ms memory recall, <8ms memory generation (verified with Kuzu)
- **💾 Embedded Database** - Single-file Kuzu graph database
- **🔄 Git-Friendly** - Database files <10MB, perfect for version control
- **🔌 Simple API** - Just two methods: `attach_memories()` and `generate_memories()`
- **🌐 Cross-Platform** - Standardized cognitive types shared with TypeScript implementation
- **📱 Offline First** - Works completely without internet connection
- **🔧 MCP Ready** - Native Claude Desktop integration with async learning support
- **🤖 Hook System** - Automatic Claude Code integration using hooks (`UserPromptSubmit`, `Stop`)

## 🚀 Quick Start

### Installation

```bash
# Install via pipx (recommended for CLI usage)
pipx install kuzu-memory

# Or install via pip
pip install kuzu-memory

# For development
pip install kuzu-memory[dev]
```

**Now available on PyPI!** KuzuMemory v1.1.0 is published and ready for production use.

### AI Integration

KuzuMemory can be integrated with various AI systems following the **ONE PATH** principle:

```bash
# Install Claude Code integration (MCP + hooks)
kuzu-memory install claude-code

# Install Claude Desktop integration (MCP only)
kuzu-memory install claude-desktop

# Install Cursor IDE integration (MCP only)
kuzu-memory install cursor

# Install VS Code integration (MCP only)
kuzu-memory install vscode

# Install Windsurf IDE integration (MCP only)
kuzu-memory install windsurf

# Install Auggie integration (rules)
kuzu-memory install auggie

# Uninstall an integration
kuzu-memory uninstall claude-code
```

**Available Integrations** (ONE command per system):
- `claude-code` - Claude Code IDE with MCP + hooks (complete integration)
- `claude-desktop` - Claude Desktop app with MCP server (global memory)
- `cursor` - Cursor IDE with MCP server
- `vscode` - VS Code with Claude extension (MCP server)
- `windsurf` - Windsurf IDE with MCP server
- `auggie` - Auggie AI with rules integration

**Key Differences**:

**Claude Code** (`claude-code`):
- **Configuration**: Creates `.kuzu-memory/config.yaml` in project directory
- **Database**: Initializes project database in `.kuzu-memory/memorydb/`
- **Memory Scope**: Each project has isolated memory
- **Hook System**: Automatic enhancement (`UserPromptSubmit`) and learning (`Stop`)
- **Use Case**: Project-specific context and memories
- **Sharing**: Memory can be committed to git for team collaboration

**Claude Desktop** (`claude-desktop`):
- **Configuration**: Creates `~/.kuzu-memory/config.yaml` in home directory
- **Database**: Initializes global database in `~/.kuzu-memory/memorydb/`
- **Memory Scope**: Shared across all Claude Desktop conversations
- **Use Case**: Personal knowledge base and preferences
- **Installation**: Auto-detects pipx or home directory installation

**Auggie** (`auggie`):
- **Configuration**: Creates `.augment/rules/` directory with enhanced integration rules
- **Version**: v2.0.0 with automatic version detection and migration
- **Auto-Migration**: Automatically upgrades from v1.0.0 to v2.0.0 with backup
- **Backup**: Creates backup at `.augment/backups/v{version}_{timestamp}/` before upgrade
- **Rules**: Enhanced rules based on Claude Code hooks v1.4.0 insights including:
  - Success metrics (2-5 memories per query, <100ms response)
  - Decision tree for when to store vs skip information
  - Deduplication patterns (SHA256 hashing, TTL caching)
  - Performance optimization (batching, targeted filtering)
  - Failure recovery protocols (graceful degradation)
- **Files Created**: `AGENTS.md`, `.augment/rules/kuzu-memory-integration.md`, `.augment/rules/memory-quick-reference.md`
- **Version Tracking**: Maintains version at `.augment/.kuzu-version`
- **Use Case**: Rules-based AI instruction integration (Auggie reads rules and decides when to act)

**Installation Options:**
- `--force` - Force reinstall even if already installed (overwrites existing config)
- `--dry-run` - Preview changes without modifying files
- `--verbose` - Show detailed installation steps
- `--mode [auto|pipx|home]` - Override auto-detection (claude-desktop only)
- `--backup-dir PATH` - Custom backup directory
- `--memory-db PATH` - Custom memory database location

**Automatic Initialization**:
- Configuration files are created automatically during installation
- Database is initialized automatically
- Existing configurations are preserved (use `--force` to overwrite)
- Backups are created when overwriting existing files

See [Claude Setup Guide](docs/CLAUDE_SETUP.md) for detailed instructions on Claude Desktop and Claude Code integration.

> **Note**: Previous installer names (e.g., `claude-desktop-pipx`, `claude-desktop-home`) still work but show deprecation warnings.

### Basic Usage

```python
from kuzu_memory import KuzuMemory

# Initialize memory system
memory = KuzuMemory()

# Store memories from conversation
memory.generate_memories("""
User: My name is Alice and I work at TechCorp as a Python developer.
Assistant: Nice to meet you, Alice! Python is a great choice for development.
""")

# Retrieve relevant memories
context = memory.attach_memories("What's my name and where do I work?")

print(context.enhanced_prompt)
# Output includes: "Alice", "TechCorp", "Python developer"
```

### CLI Usage

```bash
# Initialize memory database
kuzu-memory init

# Store a memory
kuzu-memory memory store "I prefer using TypeScript for frontend projects"

# Recall memories
kuzu-memory memory recall "What do I prefer for frontend?"

# Enhance a prompt
kuzu-memory memory enhance "What's my coding preference?"

# View statistics
kuzu-memory status
```

### Git History Sync

Automatically import project commit history as memories:

```bash
# Smart sync (auto-detects initial vs incremental)
kuzu-memory git sync

# Force full resync
kuzu-memory git sync --initial

# Preview without storing
kuzu-memory git sync --dry-run

# View sync configuration
kuzu-memory git status

# Install automatic sync hook
kuzu-memory git install-hooks
```

**What gets synced**: Commits with semantic prefixes (feat:, fix:, refactor:, perf:) from main, master, develop, feature/*, bugfix/* branches.

**Retention**: Git commits are stored as EPISODIC memories (30-day retention).

**Deduplication**: Running sync multiple times won't create duplicates - each commit SHA is stored once.

See [Git Sync Guide](docs/GIT_SYNC.md) for detailed documentation.

## 📖 Core Concepts

### Cognitive Memory Types

KuzuMemory uses a cognitive memory model inspired by human memory systems:

- **SEMANTIC** - Facts and general knowledge (never expires)
- **PROCEDURAL** - Instructions and how-to content (never expires)
- **PREFERENCE** - User/team preferences (never expires)
- **EPISODIC** - Personal experiences and events (30 days)
- **WORKING** - Current tasks and immediate focus (1 day)
- **SENSORY** - Sensory observations and descriptions (6 hours)

### Cognitive Classification

KuzuMemory automatically classifies memories into cognitive types based on content patterns, providing intuitive categorization that mirrors human memory systems. This standardized model ensures compatibility across Python and TypeScript implementations.

### Pattern-Based Extraction

No LLM required! KuzuMemory uses regex patterns to identify and store memories automatically:

```python
# Automatically detected patterns
"Remember that we use Python for backend"     # → EPISODIC memory
"My name is Alice"                            # → SEMANTIC memory
"I prefer dark mode"                          # → PREFERENCE memory
"Always use type hints"                       # → PROCEDURAL memory
"Currently debugging the API"                 # → WORKING memory
"The interface feels slow"                    # → SENSORY memory
```

**Important**: For pattern matching to work effectively, content should include clear subject-verb-object structures. Memories with specific entities, actions, or preferences are extracted more reliably than abstract statements.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Your App      │    │   KuzuMemory     │    │   Kuzu Graph    │
│                 │    │                  │    │   Database      │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │                 │
│ │  Chatbot    │─┼────┼→│attach_memories│─┼────┼→ Query Engine   │
│ │             │ │    │ │              │ │    │                 │
│ │             │ │    │ │generate_     │ │    │ ┌─────────────┐ │
│ │             │─┼────┼→│memories      │─┼────┼→│ Pattern     │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ │ Extraction  │ │
└─────────────────┘    └──────────────────┘    │ └─────────────┘ │
                                               └─────────────────┘
```

## 🔧 Configuration

Create `.kuzu_memory/config.yaml`:

```yaml
version: 1.0

storage:
  max_size_mb: 50
  auto_compact: true
  
recall:
  max_memories: 10
  strategies:
    - keyword
    - entity  
    - temporal

patterns:
  custom_identity: "I am (.*?)(?:\\.|$)"
  custom_preference: "I always (.*?)(?:\\.|$)"
```

## 📊 Performance

| Operation | Target | Typical | Verified |
|-----------|--------|---------|----------|
| Memory Recall | <100ms | ~3ms | ✅ |
| Memory Generation | <200ms | ~8ms | ✅ |
| Database Size | <500 bytes/memory | ~300 bytes | ✅ |
| RAM Usage | <50MB | ~25MB | ✅ |
| Async Learning | Smart wait | 5s default | ✅ |

## 🧪 Testing

### Quick Start

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run benchmarks
pytest tests/ -m benchmark

# Check coverage
pytest --cov=kuzu_memory
```

### MCP Testing & Diagnostics

KuzuMemory includes comprehensive MCP server testing and diagnostic tools:

```bash
# Run MCP test suite (151+ tests)
pytest tests/mcp/ -v

# Run PROJECT-LEVEL diagnostics (checks project files only)
kuzu-memory doctor

# Quick health check
kuzu-memory doctor health

# MCP-specific diagnostics
kuzu-memory doctor mcp

# Test database connection
kuzu-memory doctor connection

# Performance benchmarks
pytest tests/mcp/performance/ --benchmark-only
```

**Test Coverage**:
- **Unit Tests** (51+ tests) - Protocol and component validation
- **Integration Tests** - Multi-step operations and workflows
- **E2E Tests** - Complete user scenarios
- **Performance Tests** (78 tests) - Latency, throughput, memory profiling
- **Compliance Tests** (73 tests) - JSON-RPC 2.0 and MCP protocol

**Diagnostic Tools** (Project-Level Only):
- Configuration validation with auto-fix
- Connection testing with latency monitoring
- Tool validation and execution testing
- Continuous health monitoring
- Performance regression detection

**Note**: The `doctor` command checks PROJECT-LEVEL configurations only:
- ✅ Project memory database (kuzu-memory/)
- ✅ Claude Code MCP config (.claude/config.local.json)
- ✅ Claude Code hooks (if configured)
- ❌ Does NOT check Claude Desktop (use `kuzu-memory install claude-desktop` instead)

See [MCP Testing Guide](docs/MCP_TESTING_GUIDE.md) and [MCP Diagnostics Reference](docs/MCP_DIAGNOSTICS.md) for complete documentation.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/kuzu-memory/kuzu-memory
cd kuzu-memory
pip install -e ".[dev]"
pre-commit install
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](https://kuzu-memory.readthedocs.io)
- [PyPI Package](https://pypi.org/project/kuzu-memory/)
- [GitHub Repository](https://github.com/kuzu-memory/kuzu-memory)
- [Issue Tracker](https://github.com/kuzu-memory/kuzu-memory/issues)

## 🙏 Acknowledgments

- [Kuzu Database](https://kuzudb.com/) - High-performance graph database
- [Pydantic](https://pydantic.dev/) - Data validation library
- [Click](https://click.palletsprojects.com/) - CLI framework
