# KuzuMemory - Project Instructions for Claude Code

**AI-First Memory System for Intelligent Context Management**

---

## 🔴 CRITICAL - PROJECT IDENTITY & MISSION

### Project Identity
- **Name**: KuzuMemory v1.1.4
- **Type**: Python CLI Library/Tool for AI Memory Management
- **Path**: `/Users/masa/Projects/managed/kuzu-memory`
- **Language**: Python 3.11+
- **Database**: Kuzu Embedded Graph Database

### Core Mission
Lightweight, embedded graph-based memory system for AI applications using cognitive memory models inspired by human memory psychology. Provides fast, offline memory capabilities without requiring LLM calls.

### Why This Matters (Critical Context)
- **AI-First Design**: Built specifically for AI context management
- **Zero External Dependencies**: Embedded database, no cloud required
- **Production Performance**: 3ms recall enables real-time AI enhancement
- **Cognitive Models**: Psychology-based memory classification (SEMANTIC, PROCEDURAL, etc.)
- **Open Source**: Published to PyPI for universal access

### 🔴 CRITICAL - Production Status v1.1.4
✅ **Published to PyPI**: Available as `kuzu-memory` package
✅ **Performance Verified**: 3ms recall, genuine Kuzu graph database
✅ **Database Confirmed**: Genuine Kuzu implementation validated
✅ **MCP Server Fixed**: Async stdin issue resolved for Claude Desktop integration
✅ **Memory Recall Fixed**: Search functionality restored (fixed in v1.1.3)

### 🔴 CRITICAL - Deployment Status
**Status**: Production Ready - All Systems Operational
**Documentation**: See [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for historical issues

**RECENTLY FIXED (v1.1.4)**:
- ✅ **MCP Server**: Fixed async stdin RuntimeError on macOS (v1.1.4)
- ✅ **Memory Recall**: Search functionality restored (v1.1.3)
- ✅ **Claude Desktop Integration**: Now fully functional with thread-based stdin reading

**DEPLOYMENT READINESS**:
- ✅ **CLI Interface**: Fully functional for all operations
- ✅ **Python API**: Production ready, stable API
- ✅ **MCP Server**: Fixed and ready for Claude Desktop integration
- ✅ **Production Use**: All critical issues resolved, performance validated

**PRODUCTION BLOCKERS**: None - All major issues resolved as of v1.1.4

### 🔴 CRITICAL - Security & Infrastructure Standards
- **Version Control**: All changes tracked with semantic versioning (REQUIRED)
- **Secrets Management**: No secrets committed to repository (ENFORCED)
- **Environment Variables**: Used for configuration (`.env` files gitignored)
- **Audit Logging**: Comprehensive operation logging enabled
- **Dependency Security**: Regular vulnerability scans with `pip-audit`
- **Idempotent Operations**: All commands safe to run multiple times
- **Zero-Downtime Deployments**: Package upgrades preserve data integrity
- **Rollback Capability**: Version pinning enables instant rollbacks

---

## 🟡 IMPORTANT - SINGLE PATH WORKFLOWS (ONE WAY TO DO ANYTHING)

### Why Single Path Matters
- **Zero Ambiguity**: Each task has exactly ONE correct method
- **AI-Friendly**: Agentic coders need clear, deterministic paths
- **Team Consistency**: All developers follow identical workflows
- **Maintainability**: Single point of change for process updates
- **Documentation Sync**: One method = one documentation section

### 🟡 IMPORTANT - Development Commands (Single Path Only)
```bash
# 🛠️ SETUP (ONE command path)
make dev-setup              # Complete development environment setup
make check-tools            # Verify all required tools are available

# 🎯 QUALITY (ONE command each)
make quality                # ALL quality checks (format + lint + typecheck)
make test                   # ALL tests (unit + integration + e2e)
make format                 # Format all code (black + isort)
make lint                   # Lint code (ruff check + fix)
make typecheck              # Type check with mypy

# 🚀 BUILD & DEPLOY (ONE command each)
make build                  # Build package for distribution
make publish                # Publish to PyPI
make release                # Complete release workflow
make clean                  # Clean build artifacts

# 🏷️ VERSION MANAGEMENT (ONE command each)
make version-patch          # Bump patch version (1.1.0 -> 1.1.1)
make version-minor          # Bump minor version (1.1.0 -> 1.2.0)
make version-major          # Bump major version (1.1.0 -> 2.0.0)
make changelog              # Update changelog with current changes

# 🏎️ PERFORMANCE VALIDATION (NEW)
make perf-validate          # Validate performance thresholds
make perf-full              # Full performance test suite
make cache-test             # Test cache performance
make async-test             # Test async performance
make db-perf                # Test database performance
make memory-profile         # Memory usage profiling

# 🎯 CI/CD WORKFLOWS
make ci                     # Complete CI pipeline
make pre-commit             # Pre-commit checks with performance validation
make quick                  # Quick development cycle with validation
```

### 🟡 IMPORTANT - Performance Standards (v1.1.0)
**All thresholds validated in CI/CD pipeline with `make perf-validate`**

- **Memory Recall**: <100ms (target: ~3ms typical) ✅ VERIFIED
- **Memory Generation**: <200ms (target: ~8ms typical) ✅ VERIFIED
- **Database Size**: <500 bytes/memory (~300 bytes typical) ✅ VERIFIED
- **Async Operations**: Enhanced reliability with threshold controls ✅ VERIFIED
- **Cache Hit Rate**: <10ms cache retrieval ✅ VERIFIED
- **Connection Pool**: <50ms database connection ✅ VERIFIED
- **CLI Performance**: <100ms help command response ✅ VERIFIED

### 🟡 IMPORTANT - Monitoring & Observability
- **Performance Benchmarks**: Automated with `make perf-validate`
- **Memory Profiling**: Track memory usage patterns
- **Operation Logging**: Comprehensive audit trail
- **Health Checks**: Database connectivity and performance validation
- **Metrics Collection**: Response times, success rates, error patterns

### 🟡 IMPORTANT - Installation & Usage (Production Paths)
**Single installation method - no alternatives**

```bash
# 📦 PRODUCTION INSTALLATION (ONE command)
pip install kuzu-memory         # Install from PyPI (ONLY installation method)

# 🚀 QUICK START (ONE path for each operation)
kuzu-memory init                         # Initialize database (IDEMPOTENT - safe to re-run)
kuzu-memory memory store "Important fact"  # Store memory (ATOMIC - guaranteed consistency)
kuzu-memory memory recall "fact"         # Fast 3ms recall (CACHED - automatic optimization)
kuzu-memory status                       # View system statistics
kuzu-memory memory enhance "prompt"      # Enhance prompts with context

# 🔧 DEVELOPMENT INSTALLATION (ONE command - full setup)
git clone <repo> && cd kuzu-memory && make dev-setup

# 🔍 HEALTH VERIFICATION (ONE command - comprehensive check)
kuzu-memory status --validate    # Verify system health and performance
```

**Installation Notes**:
- No alternative installation methods documented or supported
- All dependencies managed automatically by pip
- Database auto-initializes on first use
- Configuration created automatically with sensible defaults

---

## 🟢 STANDARD - DEVELOPMENT GUIDELINES

### Why These Are Standard (Not Critical)
- **Established Patterns**: Widely-used, proven approaches
- **Flexible Within Constraints**: Some variation acceptable
- **Best Practices**: Recommended but not strictly enforced
- **Quality Focused**: Maintain high standards without rigidity

### 🟢 STANDARD - AI System Integration (Production Ready - ONE PATH)
```bash
# 🔌 INTEGRATED INSTALLER COMMANDS (ONE path for each AI system)

# List all available integrations
kuzu-memory install list

# Install Claude Code integration (project-specific)
kuzu-memory install add claude-code

# Install Claude Desktop integration (global)
kuzu-memory install add claude-desktop

# Install Auggie integration
kuzu-memory install add auggie

# Install universal integration files
kuzu-memory install add universal

# Check installation status
kuzu-memory install status

# Uninstall integration
kuzu-memory install remove <ai-system>

# 📋 PRIMARY INSTALLERS (4 total - ONE path per system)
claude-code      # Claude Code IDE integration (project-specific memory)
claude-desktop   # Claude Desktop app (global memory, auto-detects method)
auggie           # Auggie AI integration
universal        # Universal integration files

# 🎯 KEY DIFFERENCES: Project-Specific vs Global Memory

# CLAUDE CODE (project-specific):
# - Creates: .kuzu-memory/config.yaml in project directory
# - Database: .kuzu-memory/memorydb/ (project-local)
# - Scope: Isolated per-project memory
# - Use Case: Project-specific context and team collaboration
# - Git-friendly: Can be committed for team sharing

# CLAUDE DESKTOP (global):
# - Creates: ~/.kuzu-memory/config.yaml in home directory
# - Database: ~/.kuzu-memory/memorydb/ (user-global)
# - Scope: Shared across all Claude Desktop conversations
# - Use Case: Personal knowledge base and preferences
# - Installation: Auto-detects pipx or home directory method

# 📋 INSTALLATION OPTIONS (Available for all installers)
--force          # Force reinstall, overwrites existing config (creates backup)
--dry-run        # Preview changes without modifying files
--verbose        # Show detailed installation steps
--mode           # Override auto-detection (auto|pipx|home) - claude-desktop only
--backup-dir     # Custom backup directory
--memory-db      # Custom memory database location

# ⚡ AUTOMATIC INITIALIZATION (NEW)
# - Configuration files created automatically during installation
# - Database initialized automatically on first install
# - Existing configurations preserved (use --force to overwrite)
# - Automatic backups created when overwriting files

# 🎯 EXAMPLE WORKFLOWS
# Dry run to preview changes
kuzu-memory install add claude-desktop --dry-run --verbose

# Force reinstall with custom database path
kuzu-memory install add claude-desktop --force --memory-db ~/my-memories

# Override auto-detection to use specific method
kuzu-memory install add claude-desktop --mode pipx
kuzu-memory install add claude-desktop --mode home

# Project-specific installation with custom config location
kuzu-memory install add claude-code --memory-db ./project-memories

# ⚠️ DEPRECATED (still work but show warnings)
# claude-desktop-pipx, claude-desktop-home, claude, claude-mpm
# Use 'claude-code' or 'claude-desktop' instead
```

### Memory System Operations
```bash
# 🧠 MEMORY COMMANDS (CLI)
kuzu-memory init                # Initialize memory database
kuzu-memory memory store <text> # Store a memory
kuzu-memory memory recall <query>  # Query memories
kuzu-memory memory enhance <prompt>  # Enhance prompts with context
kuzu-memory memory recent       # Show recent memories
kuzu-memory status              # View statistics

# 🔄 GIT SYNC COMMANDS (NEW v1.2.8+)
kuzu-memory git sync           # Smart sync (auto-detects initial vs incremental)
kuzu-memory git sync --initial # Force full resync of all commits
kuzu-memory git sync --incremental  # Only sync new commits
kuzu-memory git sync --dry-run # Preview what would be synced
kuzu-memory git status         # View git sync configuration
kuzu-memory git install-hooks  # Install post-commit auto-sync hook
kuzu-memory git uninstall-hooks # Remove auto-sync hook

# 🔗 MCP TOOLS (Claude Desktop)
kuzu_enhance               # Enhance prompts with project memories
kuzu_learn                 # Store new learnings asynchronously
kuzu_recall                # Query specific memories
kuzu_stats                 # Get memory system statistics
```

### 🟢 STANDARD - Cognitive Memory Types
**Psychology-inspired classification system (standardized with TypeScript)**

- **SEMANTIC**: Facts, specifications, identity info (never expires)
  - Example: "Alice works at TechCorp as Python developer"
  - Use: Core knowledge that remains stable over time

- **PROCEDURAL**: Instructions, processes, patterns (never expires)
  - Example: "Always use type hints in Python code"
  - Use: How-to knowledge and established procedures

- **PREFERENCE**: Team/user preferences, conventions (never expires)
  - Example: "Team prefers pytest over unittest"
  - Use: Style guides and team conventions

- **EPISODIC**: Project decisions, events, experiences (30 days)
  - Example: "Decided to use Kuzu database for this project"
  - Use: Historical decisions and project milestones

- **WORKING**: Current tasks, immediate priorities (1 day)
  - Example: "Currently debugging the async learning system"
  - Use: Active work items and immediate context

- **SENSORY**: UI/UX observations, system behavior (6 hours)
  - Example: "The CLI response feels slow during testing"
  - Use: Transient observations and immediate feedback

### 🟢 STANDARD - Code Quality Standards
- **Formatting**: Black (88 char line length) + isort
- **Linting**: Ruff with auto-fix
- **Type Checking**: mypy with strict mode
- **Testing**: pytest with coverage reporting
- **Performance**: Benchmark validation with make perf-validate

### Testing Framework (ONE path for each test type)
```bash
# 🧪 TESTING COMMANDS
make test                   # ALL tests (unit + integration + e2e)
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/benchmarks/    # Performance benchmarks only

# 🔌 MCP TESTING & DIAGNOSTICS (NEW - Production Ready)
make mcp-test              # Complete MCP test suite (151+ tests)
make mcp-diagnose          # Run MCP diagnostics
make mcp-health            # MCP server health check
make mcp-benchmark         # MCP performance benchmarks

pytest tests/mcp/          # All MCP tests (unit + integration + e2e + performance + compliance)
pytest tests/mcp/unit/     # MCP unit tests (51+ tests)
pytest tests/mcp/performance/  # MCP performance tests (78 tests)
pytest tests/mcp/compliance/   # MCP compliance tests (73 tests)

# 🩺 PROJECT-LEVEL DIAGNOSTICS (checks project files only)
kuzu-memory doctor              # Run full project diagnostics
kuzu-memory doctor health       # Quick health check
kuzu-memory doctor mcp          # MCP diagnostics
kuzu-memory doctor connection   # Test database connection

# 📊 COVERAGE & REPORTING
make test                   # Includes coverage report (HTML + terminal)
pytest --cov-report=html    # Detailed HTML coverage report
pytest --benchmark-sort=mean # Benchmark performance analysis
```

### 🟢 STANDARD - Quality Gate Requirements
**Must pass before merging to main or releasing**

- **Test Coverage**: >90% required for release (enforced in CI)
- **Performance Thresholds**: All benchmarks must pass (`make perf-validate`)
- **Type Safety**: Zero mypy errors in strict mode (enforced)
- **Linting**: Zero ruff violations (auto-fix available)
- **Security**: No known vulnerabilities in dependencies (`pip-audit`)
- **MCP Compliance**: All MCP protocol and JSON-RPC 2.0 tests must pass
- **MCP Performance**: Connection <500ms, tool calls <1000ms, roundtrip <200ms
- **MCP Health**: Diagnostics must pass before deployment (`make mcp-health`)

**Enforcement**: All quality gates automated in `make ci` pipeline

---

## ⚪ OPTIONAL - PROJECT ARCHITECTURE

### Why This Is Optional
- **Reference Information**: Useful for understanding but not required for tasks
- **Deep Dive Details**: Architecture specifics for advanced work
- **Historical Context**: Background information and evolution
- **Nice to Know**: Enhances understanding but not essential for operation

### ⚪ OPTIONAL - Directory Structure (Clean Python Package)
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
├── nlp/                   # NLP classification
├── caching/               # Memory caching system
├── connection_pool/       # Database connection pooling
├── extraction/            # Entity and pattern extraction
├── interfaces/            # Type definitions and interfaces
├── migrations/            # Database schema migrations
├── monitoring/            # Performance monitoring
└── utils/                 # Utility functions

tests/                     # All test files
├── unit/                  # Unit tests
├── integration/           # Integration tests
├── benchmarks/            # Performance benchmarks
├── e2e/                   # End-to-end tests
├── fixtures/              # Test fixtures
├── regression/            # Regression tests
└── stress/                # Stress tests

docs/                      # Documentation
scripts/                   # Utility scripts
examples/                  # Example configurations
```

### ⚪ OPTIONAL - v1.1.0 Release Success Metrics
**Historical milestone - reference for understanding project maturity**

- ✅ **Published to PyPI**: Package successfully deployed and available
- ✅ **Performance Verified**: 3ms recall speed with genuine Kuzu database
- ✅ **Kuzu Database Confirmed**: Real graph database implementation validated
- ✅ **Hook Compatibility Tested**: Claude-mpm integration ready
- ✅ **Production Ready**: All systems tested and deployment validated

### ⚪ OPTIONAL - Key v1.1.0 Improvements
**Historical context - understanding the evolution**

- ✅ **Fixed**: Async learning queue with smart 5-second wait
- ✅ **Fixed**: DateTime comparison errors preventing memory storage
- ✅ **Added**: Claude Desktop MCP installer with pipx detection
- ✅ **Added**: Semantic versioning with VERSION file and build tracking
- ✅ **Improved**: Performance thresholds for async operations reliability

### ⚪ OPTIONAL - Memory Best Practices
```python
# 🧠 STORING MEMORIES BY TYPE
memory.learn("Alice works at TechCorp as Python developer")     # → SEMANTIC
memory.learn("Always use type hints in Python code")            # → PROCEDURAL
memory.learn("Team prefers pytest over unittest")               # → PREFERENCE
memory.learn("Decided to use Kuzu database for this project")   # → EPISODIC
memory.learn("Currently debugging the async learning system")   # → WORKING
memory.learn("The CLI response feels slow during testing")      # → SENSORY
```

### ⚪ OPTIONAL - Integration Patterns (Production API)
**Reference for programmatic integration**

```python
# 🔗 PYTHON API USAGE (Available on PyPI)
from kuzu_memory import KuzuMemory

memory = KuzuMemory()
memory.generate_memories(conversation_text)  # ~8ms generation
context = memory.attach_memories(query)      # ~3ms recall
print(context.enhanced_prompt)
```

### ⚪ OPTIONAL - Production Deployment Notes
**Technical specifications for production deployment**

- **Database**: Embedded Kuzu - no external dependencies
- **Performance**: Sub-100ms operations, typically 3-8ms
- **Memory**: Lightweight footprint, ~300 bytes per memory
- **Compatibility**: Python 3.11+, tested on macOS/Linux
- **Integration**: Ready for claude-mpm hooks and MCP servers

### ⚪ OPTIONAL - Deployment Best Practices
**Operational patterns for production deployments**

- **Zero-Downtime Updates**: Package upgrades preserve data integrity
- **Rollback Capability**: Version pinning enables instant rollbacks
- **Health Checks**: `kuzu-memory status --validate` before routing traffic
- **Gradual Rollout**: Test in development, staging, then production
- **Configuration Management**: Environment variables for all settings
- **Data Backup**: Database files are portable and backup-friendly

---

## 🟡 IMPORTANT - CLAUDE CODE INTEGRATION

### Why This Is Important (Not Critical)
- **AI Enhancement**: Direct integration with Claude Code workflows
- **Production Patterns**: Established, tested integration methods
- **Performance Critical**: Fast recall enables real-time AI enhancement
- **Recommended Usage**: Follow these patterns for best results

### 🟡 IMPORTANT - AI Enhancement Workflow (Production Ready)
**ONE path for each integration step**

1. **Install**: `pip install kuzu-memory` (available on PyPI)
2. **Initialize**: `kuzu-memory init` (creates local .kuzu database)
3. **Enhance**: Use `kuzu-memory memory enhance` for AI interactions
4. **Learn**: Store decisions with `kuzu-memory memory store` (async processing)
5. **Recall**: Query context with `kuzu-memory memory recall` (3ms speed)

### 🟡 IMPORTANT - Claude Code Specific Guidelines
**Leverage KuzuMemory capabilities in Claude Code**

- **Fast Context**: Leverage 3ms recall for real-time AI enhancement
- **Cognitive Types**: Use memory classification for intelligent storage
- **Async Learning**: Background processing prevents blocking operations
- **Graph Database**: Genuine Kuzu database for relationship modeling
- **Production Ready**: Tested and validated for production deployment

### ⚪ OPTIONAL - Claude MPM Integration Patterns
**Advanced integration for Claude MPM users**

```bash
# 🔗 MPM HOOK INTEGRATION (Ready for Production)
kuzu-memory init --mpm          # Initialize with MPM compatibility
kuzu-memory hook-install        # Install MPM hooks
kuzu-memory hook-test          # Test hook functionality

# 🧠 MEMORY-ENHANCED AI SESSIONS
kuzu-memory memory enhance "coding task context"  # Pre-enhance prompts
kuzu-memory memory store "project decision"  # Store learning
kuzu-memory memory recall "related memories"  # Context retrieval
```

### ⚪ OPTIONAL - Browser Console Monitoring Integration
**Client-side monitoring capabilities**

- **Client-Side Memory Events**: Track memory operations in browser
- **Performance Monitoring**: Real-time memory system performance
- **Debug Integration**: Console logging for memory operations
- **Error Tracking**: Capture and log memory-related errors

---

## 🟡 IMPORTANT - DOCUMENTATION NAVIGATION

### Navigation Principle
**Everything discoverable from README.md → CLAUDE.md (this file)**

### 🔴 CRITICAL - Essential Reading (Start Here)
- **[README.md](README.md)** - Project overview and quick start (ENTRY POINT)
- **[CLAUDE.md](CLAUDE.md)** - This file - primary agent instructions (YOU ARE HERE)
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and recent changes
- **[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)** - Production limitations and workarounds

### 🟡 IMPORTANT - User Documentation (Getting Started)
- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** - 5-minute quick start guide
- **[docs/CLAUDE_SETUP.md](docs/CLAUDE_SETUP.md)** - Claude Desktop & Code integration
- **[docs/AI_INTEGRATION.md](docs/AI_INTEGRATION.md)** - Universal AI integration patterns
- **[docs/MEMORY_SYSTEM.md](docs/MEMORY_SYSTEM.md)** - Memory types and best practices
- **[docs/GIT_SYNC.md](docs/GIT_SYNC.md)** - Git commit history synchronization (NEW v1.2.8+)

### 🟢 STANDARD - Developer Documentation (Development)
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Clean architecture overview
- **[docs/developer/](docs/developer/)** - Complete developer documentation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture details
- **[Makefile](Makefile)** - Build system and workflows (single source of truth)

### 🟢 STANDARD - MCP Testing & Diagnostics
- **[docs/MCP_TESTING_GUIDE.md](docs/MCP_TESTING_GUIDE.md)** - Comprehensive MCP testing guide
- **[docs/MCP_DIAGNOSTICS.md](docs/MCP_DIAGNOSTICS.md)** - Diagnostic commands reference
- **[docs/MCP_PHASE5_IMPLEMENTATION_REPORT.md](docs/MCP_PHASE5_IMPLEMENTATION_REPORT.md)** - Phase 5 implementation details
- **[tests/mcp/README.md](tests/mcp/README.md)** - MCP testing framework overview

### ⚪ OPTIONAL - Project Planning & Roadmap
- **[docs/FIX_ROADMAP.md](docs/FIX_ROADMAP.md)** - Prioritized fix implementation plan
- **[docs/PROJECT_ORGANIZATION.md](docs/PROJECT_ORGANIZATION.md)** - Organization completion summary

### ⚠️ DEPRECATED - Legacy Scripts (Do Not Use)
- **[scripts/install-claude-desktop.py](scripts/install-claude-desktop.py)** - ⚠️ DEPRECATED (use `kuzu-memory install` instead)
- **[scripts/install-claude-desktop-home.py](scripts/install-claude-desktop-home.py)** - ⚠️ DEPRECATED (use `kuzu-memory install` instead)

---

## 🟡 IMPORTANT - OPERATIONAL RUNBOOKS & TROUBLESHOOTING

### Troubleshooting Principle
**ONE solution per problem - no alternative methods**

### 🟡 IMPORTANT - Common Issues & Resolution (ONE solution per problem)
```bash
# 🔧 DATABASE ISSUES
kuzu-memory init --force        # Reinitialize corrupted database
kuzu-memory status --validate   # Verify database health

# ⚡ PERFORMANCE ISSUES
make perf-validate              # Check performance thresholds
kuzu-memory memory recall --benchmark  # Benchmark recall performance

# 🐛 INSTALLATION ISSUES
make check-tools                # Verify required tools
pip install --upgrade kuzu-memory  # Update to latest version

# 🔄 DEVELOPMENT ISSUES
make clean && make dev-setup    # Clean rebuild environment
make quality                    # Run all quality checks

# 🔌 MCP SERVER ISSUES (PROJECT-LEVEL ONLY)
kuzu-memory doctor              # Full diagnostic suite (project files only)
kuzu-memory doctor --fix        # Auto-fix common issues
kuzu-memory doctor health       # Quick health check
kuzu-memory doctor connection   # Test database connectivity
kuzu-memory doctor mcp          # MCP diagnostics

# NOTE: Doctor checks PROJECT-LEVEL only:
# ✅ Checks: Project memory files (kuzu-memory/)
# ✅ Checks: Claude Code MCP config (.claude/config.local.json)
# ✅ Checks: Claude Code hooks (if configured)
# ❌ Does NOT check: Claude Desktop (user home directory)
# For Claude Desktop setup, use: kuzu-memory install add claude-desktop
```

### 🟢 STANDARD - Monitoring & Alerting Setup
**Operational monitoring recommendations**

- **Performance Thresholds**: Alert if recall >100ms, generation >200ms
- **Error Tracking**: Monitor async operation failures
- **Health Checks**: Automated database connectivity validation
- **Resource Usage**: Track memory consumption and database size growth

### 🟡 IMPORTANT - Rollback Procedures (ONE method per scenario)
```bash
# 🔙 VERSION ROLLBACK (if new version fails)
pip install kuzu-memory==<previous-version>  # Pin to working version
kuzu-memory status --validate                # Verify rollback success

# 🗃️ DATABASE ROLLBACK (if corruption occurs)
cp ~/.kuzu/backup/database.kuzu ~/.kuzu/     # Restore from backup
kuzu-memory status --validate                # Verify restoration
```

**Rollback Notes**:
- Only ONE rollback method per scenario type
- Always verify with `status --validate` after rollback
- Database files are portable across systems
- Version pinning is preferred over rollback when possible

---

## 🟢 STANDARD - CLAUDE MPM COMPLIANCE CERTIFICATION

### Compliance Framework
**KuzuMemory adheres to Claude MPM best practices for agentic coder optimization**

### ✅ Single Path Principle (ENFORCED)
- **ONE command** for each operation type (no alternatives)
- **NO alternative methods** documented or supported
- **Clear hierarchical priority** (🔴→🟡→🟢→⚪)
- **Discoverable workflows** from README.md → CLAUDE.md
- **Zero ambiguity** in task execution

### ✅ Infrastructure as Code (ENFORCED)
- **Version controlled** configuration (all changes tracked)
- **Idempotent operations** (safe to run multiple times)
- **Declarative setup** via Makefile (single source of truth)
- **Automated quality gates** with performance validation
- **Reproducible builds** across environments

### ✅ Production Standards (ENFORCED)
- **Zero-downtime deployments** supported
- **Comprehensive monitoring** and health checks
- **Rollback capability** for all operations
- **Security best practices** implemented
- **Audit logging** enabled for all operations

### ✅ Performance Benchmarks (VALIDATED)
- **Sub-100ms operations** validated in CI/CD
- **3ms typical recall** verified in production
- **Automated performance testing** integrated
- **Threshold validation** in CI/CD pipeline
- **Continuous monitoring** of performance metrics

### ✅ Documentation Standards (VERIFIED)
- **Priority markers** (🔴🟡🟢⚪) consistently applied
- **Single path enforcement** documented throughout
- **Clear navigation** from entry points
- **No conflicting instructions** or alternative methods
- **Regular updates** synchronized with code changes

---

## 📋 PROJECT METADATA

**Version**: 1.2.8 (Git Sync Feature)
**Updated**: 2025-10-09
**Status**: Production Ready
**PyPI**: Available as `kuzu-memory`
**Performance**: 3ms Recall ✅
**MCP Server**: Fixed ✅
**Git Sync**: Production Ready ✅
**Claude MPM**: Fully Compliant ✅

**Compliance Score**: 100% (All Claude MPM criteria met)
**Last Audit**: 2025-10-09
**Next Review**: On version bump or major changes
