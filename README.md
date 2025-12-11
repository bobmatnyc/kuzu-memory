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

**Now available on PyPI!** KuzuMemory v1.4.48 is published and ready for production use.

### Smart Setup (Recommended - ONE Command!)

The easiest way to get started is with the smart `setup` command:

```bash
# Navigate to your project directory
cd /path/to/your/project

# Run smart setup - auto-detects and configures everything
kuzu-memory setup

# That's it! The setup command will:
# ✅ Initialize the memory database
# ✅ Detect your AI tools (Claude Code, Cursor, VS Code, etc.)
# ✅ Install/update integrations automatically
# ✅ Verify everything is working
```

**Options**:
```bash
# Preview what would happen (dry run)
kuzu-memory setup --dry-run

# Setup for specific AI tool
kuzu-memory setup --integration claude-code

# Initialize only (skip AI tool installation)
kuzu-memory setup --skip-install

# Force reinstall everything
kuzu-memory setup --force
```

### Manual Installation (Advanced Users)

If you need granular control, KuzuMemory can be installed manually with various AI systems following the **ONE PATH** principle:

```bash
# Install Claude Code integration (MCP + hooks)
kuzu-memory install claude-code

# Install Claude Desktop integration (MCP only)
kuzu-memory install claude-desktop

# Install Codex integration (MCP only)
kuzu-memory install codex

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
- `codex` - Codex IDE with MCP server (global configuration)
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

**Codex** (`codex`):
- **Configuration**: Creates `~/.codex/config.toml` in home directory (TOML format)
- **Database**: Uses project-specific database via environment variables
- **Memory Scope**: Global configuration, project-specific memory
- **Use Case**: Codex IDE integration with MCP protocol
- **Format**: Uses snake_case `mcp_servers` convention (TOML)

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

See [Claude Setup Guide](docs/user/CLAUDE_SETUP.md) for detailed instructions on Claude Desktop and Claude Code integration.

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

### Keeping KuzuMemory Updated

**Check for updates:**
```bash
kuzu-memory update --check-only
```

**Check and upgrade:**
```bash
kuzu-memory update
```

**Include pre-releases:**
```bash
kuzu-memory update --pre
```

**Silent check (for scripts/cron):**
```bash
kuzu-memory update --check-only --quiet
# Exit code 0 = up to date, 2 = update available
```

**JSON output for automation:**
```bash
kuzu-memory update --check-only --format json
```

The update command queries PyPI for the latest version and uses pip to upgrade. It's safe to run anytime and will preserve your database and configuration files.

### Repair Command

**Auto-fix broken MCP configurations:**

If your MCP server fails to start due to configuration issues, the repair command can automatically fix common problems:

```bash
# Auto-detect and repair all installed systems
kuzu-memory repair

# Show detailed repair information
kuzu-memory repair --verbose
```

**What it fixes:**
- Broken `["mcp", "serve"]` args → `["mcp"]` (common MCP server startup issue)
- Auto-detects Claude Code, Claude Desktop, Cursor, VS Code, Windsurf configurations
- Creates backups before making changes
- Shows clear before/after comparison

**When to use:**
- MCP server fails to start with args-related errors
- After upgrading from older versions
- When integrations stop working unexpectedly

See [Troubleshooting Guide](docs/user/troubleshooting.md) for more repair scenarios.

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

See [Git Sync Guide](docs/user/GIT_SYNC.md) for detailed documentation.

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

### High-Level Architecture

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

### Service-Oriented Architecture (v1.5+)

KuzuMemory uses a **service layer architecture** with dependency injection for clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    ServiceManager                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │MemoryService │  │GitSyncService│  │DiagnosticSvc │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
    IMemoryService    IGitSyncService   IDiagnosticService
    (Protocol)        (Protocol)        (Protocol)
```

**Key Benefits:**
- ✅ **16.63% faster** than direct instantiation (Phase 5 verified)
- ✅ **Easy testing** via protocol-based mocking
- ✅ **Consistent lifecycle** management with context managers
- ✅ **Resource safety** - automatic cleanup prevents leaks

**For Developers:**
- 📖 [Service Layer Architecture](docs/developer/service-layer.md) - Comprehensive architecture guide
- 💡 [Usage Examples](docs/developer/service-usage.md) - Copy-paste ready code samples
- 🔄 [Migration Guide](docs/developer/migrating-to-services.md) - Migrate existing code
- 📚 [API Reference](docs/developer/services.md) - Complete API documentation

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

See [MCP Testing Guide](docs/user/MCP_TESTING_GUIDE.md) and [MCP Diagnostics Reference](docs/user/MCP_DIAGNOSTICS.md) for complete documentation.

## 🩺 System Diagnostics

The `kuzu-memory doctor` command provides comprehensive health checks and diagnostics for your project-level KuzuMemory installation.

### Quick Start

```bash
# Run full diagnostics (interactive, 29 checks)
kuzu-memory doctor

# Auto-fix detected issues (non-interactive)
kuzu-memory doctor --fix

# Quick health check
kuzu-memory doctor health

# MCP-specific diagnostics
kuzu-memory doctor mcp

# Test database connection
kuzu-memory doctor connection

# Selective testing
kuzu-memory doctor --no-server-lifecycle  # Skip server checks
kuzu-memory doctor --no-hooks            # Skip hooks checks

# JSON output for automation
kuzu-memory doctor --format json > diagnostics.json

# Save report to file
kuzu-memory doctor --output report.html --format html
```

**New in v1.4.x:**
- `--fix` flag for automatic issue resolution
- Multiple output formats (text, JSON, HTML)
- Focused diagnostic commands (health, mcp, connection)
- Enhanced error messages with fix suggestions

### What Gets Tested

**Configuration Checks (11)**:
- Database directory and file
- Project metadata files (PROJECT.md, README.md)
- Hook scripts and configuration
- Claude Code settings (.claude/config.local.json)
- MCP server configuration

**Hooks Diagnostics (12)**:
- Hook configuration validation
- Event name validation (UserPromptSubmit, Stop)
- Command path verification
- Hook execution tests (session-start, enhance, learn)
- Environment validation (logs, cache, project root)

**Server Lifecycle Checks (7)**:
- Server startup validation
- Health checks (ping, protocol, tools)
- Graceful shutdown
- Resource cleanup (zombie process detection)
- Restart/recovery capability

**Performance Metrics**:
- Startup time
- Protocol latency
- Throughput testing

### Understanding Results

**Severity Levels**:
- ✅ SUCCESS: Check passed
- ℹ️ INFO: Informational message (not an error)
- ⚠️ WARNING: Issue found but not critical
- ❌ ERROR: Problem that should be fixed
- 🔴 CRITICAL: Serious issue requiring immediate attention

**Auto-Fix Suggestions**:
Most failures include a "Fix:" suggestion with a specific command to resolve the issue.

### Performance Benchmarks

From QA testing:
- Full diagnostics: ~4.5 seconds (29 checks)
- Hooks only: ~1.6 seconds (12 checks)
- Server only: ~3.0 seconds (7 checks)
- Core only: ~0.25 seconds (11 checks)

### Troubleshooting

**Common Issues**:

1. **MCP server not configured (INFO)**
   - Fix: `kuzu-memory install add claude-code`

2. **Hook executable not found (ERROR)**
   - Fix: `kuzu-memory install add claude-code --force`

3. **Database not initialized (CRITICAL)**
   - Fix: `kuzu-memory init` or reinstall

### Exit Codes

- 0: All checks passed (or INFO level only)
- 1: Some checks failed

See [Diagnostics Reference](docs/user/diagnostics-reference.md) for detailed check documentation.

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
