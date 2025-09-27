# KuzuMemory - Project Instructions for Claude Code

**AI-First Memory System for Intelligent Context Management**

---

## 🔴 CRITICAL PROJECT INFORMATION

### Project Identity
- **Name**: KuzuMemory v1.1.0
- **Type**: Python CLI Library/Tool for AI Memory Management
- **Path**: `/Users/masa/Projects/managed/kuzu-memory`
- **Language**: Python 3.11+
- **Database**: Kuzu Embedded Graph Database

### Core Mission
Lightweight, embedded graph-based memory system for AI applications using cognitive memory models inspired by human memory psychology. Provides fast, offline memory capabilities without requiring LLM calls.

### Production Status - v1.1.0 Release Success
✅ **Published to PyPI**: Available as `kuzu-memory` package
✅ **Performance Verified**: 3ms recall, genuine Kuzu graph database
✅ **Production Ready**: All systems tested and validated
✅ **Claude-MPM Compatible**: Ready for hook integration

---

## 🟡 IMPORTANT - SINGLE PATH WORKFLOWS (ONE WAY TO DO ANYTHING)

### Development Commands
```bash
# 🛠️ SETUP (ONE command path)
make dev-setup              # Complete development environment setup

# 🎯 QUALITY (ONE command each)
make quality                 # ALL quality checks (format + lint + typecheck)
make test                   # ALL tests (unit + integration + e2e)

# 🚀 BUILD & DEPLOY (ONE command each)
make build                  # Build package for distribution
make publish                # Publish to PyPI
make release                # Complete release workflow

# 🏷️ VERSION MANAGEMENT (ONE command each)
make version-patch          # Bump patch version (1.1.0 -> 1.1.1)
make version-minor          # Bump minor version (1.1.0 -> 1.2.0)
make version-major          # Bump major version (1.1.0 -> 2.0.0)
```

### Performance Standards (v1.1.0)
- **Memory Recall**: <100ms (target: ~3ms typical) ✅ VERIFIED
- **Memory Generation**: <200ms (target: ~8ms typical) ✅ VERIFIED
- **Database Size**: <500 bytes/memory (~300 bytes typical) ✅ VERIFIED
- **Async Operations**: Enhanced reliability with threshold controls ✅ VERIFIED

### Installation & Usage
```bash
# 📦 INSTALL FROM PYPI (Production Ready)
pip install kuzu-memory

# 🚀 QUICK START
kuzu-memory init                 # Initialize database
kuzu-memory remember "Important fact"
kuzu-memory recall "fact"        # Fast 3ms recall
```

---

## 🟢 STANDARD - DEVELOPMENT GUIDELINES

### Claude Desktop MCP Integration (Production Ready)
```bash
# 🔌 ONE-COMMAND INSTALLATION
python scripts/install-claude-desktop.py

# Features:
# - Automatic pipx detection and installation
# - Claude Desktop MCP configuration
# - Backup of existing configuration
# - Installation validation and verification
# - Compatible with claude-mpm hooks system
```

### Memory System Operations
```bash
# 🧠 MEMORY COMMANDS (CLI)
kuzu-memory init            # Initialize memory database
kuzu-memory remember <text> # Store a memory
kuzu-memory recall <query>  # Query memories
kuzu-memory stats          # View statistics

# 🔗 MCP TOOLS (Claude Desktop)
kuzu_enhance               # Enhance prompts with project memories
kuzu_learn                 # Store new learnings asynchronously
kuzu_recall                # Query specific memories
kuzu_stats                 # Get memory system statistics
```

### Cognitive Memory Types (Standardized with TypeScript)
- **SEMANTIC**: Facts, specifications, identity info (never expires)
- **PROCEDURAL**: Instructions, processes, patterns (never expires)
- **PREFERENCE**: Team/user preferences, conventions (never expires)
- **EPISODIC**: Project decisions, events, experiences (30 days)
- **WORKING**: Current tasks, immediate priorities (1 day)
- **SENSORY**: UI/UX observations, system behavior (6 hours)

### Code Quality Standards
- **Formatting**: Black (88 char line length) + isort
- **Linting**: Ruff with auto-fix
- **Type Checking**: mypy with strict mode
- **Testing**: pytest with coverage reporting
- **Performance**: Benchmark validation with make perf-validate

---

## ⚪ OPTIONAL - PROJECT ARCHITECTURE

### Directory Structure (Clean Python Package)
```
src/kuzu_memory/           # Main package
├── cli/                   # CLI commands
├── core/                  # Core memory engine
├── async_memory/          # Async operations (v1.1.0 fixes)
├── storage/               # Database adapters
├── recall/                # Memory recall strategies
├── integrations/          # AI system integrations
├── installers/            # Installation utilities (new)
├── mcp/                   # MCP server implementation
└── nlp/                   # NLP classification

tests/                     # All test files
docs/                      # Documentation
scripts/                   # Utility scripts
examples/                  # Example configurations
```

### v1.1.0 Release Success Metrics
- ✅ **Published to PyPI**: Package successfully deployed and available
- ✅ **Performance Verified**: 3ms recall speed with genuine Kuzu database
- ✅ **Kuzu Database Confirmed**: Real graph database implementation validated
- ✅ **Hook Compatibility Tested**: Claude-mpm integration ready
- ✅ **Production Ready**: All systems tested and deployment validated

### Key v1.1.0 Improvements
- ✅ **Fixed**: Async learning queue with smart 5-second wait
- ✅ **Fixed**: DateTime comparison errors preventing memory storage
- ✅ **Added**: Claude Desktop MCP installer with pipx detection
- ✅ **Added**: Semantic versioning with VERSION file and build tracking
- ✅ **Improved**: Performance thresholds for async operations reliability

### Memory Best Practices
```python
# 🧠 STORING MEMORIES BY TYPE
memory.learn("Alice works at TechCorp as Python developer")     # → SEMANTIC
memory.learn("Always use type hints in Python code")            # → PROCEDURAL
memory.learn("Team prefers pytest over unittest")               # → PREFERENCE
memory.learn("Decided to use Kuzu database for this project")   # → EPISODIC
memory.learn("Currently debugging the async learning system")   # → WORKING
memory.learn("The CLI response feels slow during testing")      # → SENSORY
```

### Integration Patterns (Production API)
```python
# 🔗 PYTHON API USAGE (Available on PyPI)
from kuzu_memory import KuzuMemory

memory = KuzuMemory()
memory.generate_memories(conversation_text)  # ~8ms generation
context = memory.attach_memories(query)      # ~3ms recall
print(context.enhanced_prompt)
```

### Production Deployment Notes
- **Database**: Embedded Kuzu - no external dependencies
- **Performance**: Sub-100ms operations, typically 3-8ms
- **Memory**: Lightweight footprint, ~300 bytes per memory
- **Compatibility**: Python 3.11+, tested on macOS/Linux
- **Integration**: Ready for claude-mpm hooks and MCP servers

---

## 🎯 MEMORY INTEGRATION FOR CLAUDE CODE

### AI Enhancement Workflow (Production Ready)
1. **Install**: `pip install kuzu-memory` (available on PyPI)
2. **Initialize**: `kuzu-memory init` (creates local .kuzu database)
3. **Enhance**: Use `kuzu-memory enhance` for AI interactions
4. **Learn**: Store decisions with `kuzu-memory learn` (async processing)
5. **Recall**: Query context with `kuzu-memory recall` (3ms speed)

### Claude Code Specific Guidelines
- **Fast Context**: Leverage 3ms recall for real-time AI enhancement
- **Cognitive Types**: Use memory classification for intelligent storage
- **Async Learning**: Background processing prevents blocking operations
- **Graph Database**: Genuine Kuzu database for relationship modeling
- **Production Ready**: Tested and validated for production deployment

---

## 📚 DOCUMENTATION LINKS

### Essential Reading
- **[README.md](README.md)** - Project overview and quick start
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and recent changes
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Clean architecture overview

### Developer Resources
- **[docs/developer/](docs/developer/)** - Complete developer documentation
- **[docs/CLAUDE_CODE_SETUP.md](docs/CLAUDE_CODE_SETUP.md)** - Claude Code integration guide
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture details

### Setup Guides
- **[scripts/install-claude-desktop.py](scripts/install-claude-desktop.py)** - MCP installer
- **[Makefile](Makefile)** - Build system and workflows

---

**Version**: 1.1.0 | **Updated**: 2025-09-27 | **Status**: Production Ready | **PyPI**: Available | **Performance**: 3ms Recall ✅
