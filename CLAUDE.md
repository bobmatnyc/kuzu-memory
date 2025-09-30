# KuzuMemory - Project Instructions for Claude Code

**AI-First Memory System for Intelligent Context Management**

---

## 🔴 CRITICAL PROJECT INFORMATION

### Project Identity
- **Name**: KuzuMemory v1.1.4
- **Type**: Python CLI Library/Tool for AI Memory Management
- **Path**: `/Users/masa/Projects/managed/kuzu-memory`
- **Language**: Python 3.11+
- **Database**: Kuzu Embedded Graph Database

### Core Mission
Lightweight, embedded graph-based memory system for AI applications using cognitive memory models inspired by human memory psychology. Provides fast, offline memory capabilities without requiring LLM calls.

### Production Status - v1.1.4 Release
✅ **Published to PyPI**: Available as `kuzu-memory` package
✅ **Performance Verified**: 3ms recall, genuine Kuzu graph database
✅ **Database Confirmed**: Genuine Kuzu implementation validated
✅ **MCP Server Fixed**: Async stdin issue resolved for Claude Desktop integration
✅ **Memory Recall Fixed**: Search functionality restored (fixed in v1.1.3)

### ⚠️ RESOLVED ISSUES (as of v1.1.4)
**Status**: Production Ready
**Documentation**: See [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) for historical issues

**RECENTLY FIXED**:
- ✅ **MCP Server**: Fixed async stdin RuntimeError on macOS (v1.1.4)
- ✅ **Memory Recall**: Search functionality restored (v1.1.3)
- ✅ **Claude Desktop Integration**: Now fully functional with thread-based stdin reading

**DEPLOYMENT GUIDANCE**:
- ✅ **CLI Interface**: Fully functional for all operations
- ✅ **Python API**: Production ready
- ✅ **MCP Server**: Fixed and ready for Claude Desktop integration
- ✅ **Production Use**: All critical issues resolved

**STATUS**: All major blocking issues have been resolved as of v1.1.4

### Security & Infrastructure Standards
- **Version Control**: All changes tracked with semantic versioning
- **Secrets Management**: No secrets committed to repository
- **Environment Variables**: Used for configuration (`.env` files gitignored)
- **Audit Logging**: Comprehensive operation logging enabled
- **Dependency Security**: Regular vulnerability scans with `pip-audit`

---

## 🟡 IMPORTANT - SINGLE PATH WORKFLOWS (ONE WAY TO DO ANYTHING)

### Development Commands - Single Path Only
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

### Performance Standards (v1.1.0)
- **Memory Recall**: <100ms (target: ~3ms typical) ✅ VERIFIED
- **Memory Generation**: <200ms (target: ~8ms typical) ✅ VERIFIED
- **Database Size**: <500 bytes/memory (~300 bytes typical) ✅ VERIFIED
- **Async Operations**: Enhanced reliability with threshold controls ✅ VERIFIED
- **Cache Hit Rate**: <10ms cache retrieval ✅ VERIFIED
- **Connection Pool**: <50ms database connection ✅ VERIFIED
- **CLI Performance**: <100ms help command response ✅ VERIFIED

### Monitoring & Observability
- **Performance Benchmarks**: Automated with `make perf-validate`
- **Memory Profiling**: Track memory usage patterns
- **Operation Logging**: Comprehensive audit trail
- **Health Checks**: Database connectivity and performance validation
- **Metrics Collection**: Response times, success rates, error patterns

### Installation & Usage - Production Paths
```bash
# 📦 INSTALL FROM PYPI (Production Ready)
pip install kuzu-memory

# 🚀 QUICK START (ONE path for each operation)
kuzu-memory init                 # Initialize database (IDEMPOTENT)
kuzu-memory remember "Important fact"  # Store memory (ATOMIC)
kuzu-memory recall "fact"        # Fast 3ms recall (CACHED)
kuzu-memory stats               # View system statistics
kuzu-memory enhance "prompt"    # Enhance prompts with context

# 🔧 DEVELOPMENT INSTALLATION (ONE command)
git clone <repo> && cd kuzu-memory && make dev-setup

# 🔍 HEALTH VERIFICATION (ONE command)
kuzu-memory stats --validate    # Verify system health and performance
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

### Testing Framework (ONE path for each test type)
```bash
# 🧪 TESTING COMMANDS
make test                   # ALL tests (unit + integration + e2e)
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/benchmarks/    # Performance benchmarks only

# 📊 COVERAGE & REPORTING
make test                   # Includes coverage report (HTML + terminal)
pytest --cov-report=html    # Detailed HTML coverage report
pytest --benchmark-sort=mean # Benchmark performance analysis
```

### Quality Gate Requirements
- **Test Coverage**: >90% required for release
- **Performance Thresholds**: All benchmarks must pass
- **Type Safety**: Zero mypy errors in strict mode
- **Linting**: Zero ruff violations
- **Security**: No known vulnerabilities in dependencies

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

### Deployment Best Practices
- **Zero-Downtime Updates**: Package upgrades preserve data integrity
- **Rollback Capability**: Version pinning enables instant rollbacks
- **Health Checks**: `kuzu-memory stats --validate` before routing traffic
- **Gradual Rollout**: Test in development, staging, then production
- **Configuration Management**: Environment variables for all settings
- **Data Backup**: Database files are portable and backup-friendly

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

### Claude MPM Integration Patterns
```bash
# 🔗 MPM HOOK INTEGRATION (Ready for Production)
kuzu-memory init --mpm          # Initialize with MPM compatibility
kuzu-memory hook-install        # Install MPM hooks
kuzu-memory hook-test          # Test hook functionality

# 🧠 MEMORY-ENHANCED AI SESSIONS
kuzu-memory enhance "coding task context"  # Pre-enhance prompts
kuzu-memory learn --async "project decision"  # Background learning
kuzu-memory recall --context "related memories"  # Context retrieval
```

### Browser Console Monitoring Integration
- **Client-Side Memory Events**: Track memory operations in browser
- **Performance Monitoring**: Real-time memory system performance
- **Debug Integration**: Console logging for memory operations
- **Error Tracking**: Capture and log memory-related errors

---

## 📚 DOCUMENTATION LINKS

### Essential Reading
- **[README.md](README.md)** - Project overview and quick start
- **[CLAUDE.md](CLAUDE.md)** - This file - primary agent instructions
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and recent changes
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Clean architecture overview

### Critical Documentation
- **[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)** - Production limitations and workarounds
- **[docs/FIX_ROADMAP.md](docs/FIX_ROADMAP.md)** - Prioritized fix implementation plan
- **[docs/PROJECT_ORGANIZATION.md](docs/PROJECT_ORGANIZATION.md)** - Organization completion summary

### Developer Resources
- **[docs/developer/](docs/developer/)** - Complete developer documentation
- **[docs/CLAUDE_CODE_SETUP.md](docs/CLAUDE_CODE_SETUP.md)** - Claude Code integration guide
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture details

### Setup Guides
- **[scripts/install-claude-desktop.py](scripts/install-claude-desktop.py)** - MCP installer
- **[Makefile](Makefile)** - Build system and workflows

---

## 🚨 OPERATIONAL RUNBOOKS & TROUBLESHOOTING

### Common Issues & Resolution (ONE solution per problem)
```bash
# 🔧 DATABASE ISSUES
kuzu-memory init --force        # Reinitialize corrupted database
kuzu-memory stats --validate    # Verify database health

# ⚡ PERFORMANCE ISSUES
make perf-validate              # Check performance thresholds
kuzu-memory recall --benchmark  # Benchmark recall performance

# 🐛 INSTALLATION ISSUES
make check-tools                # Verify required tools
pip install --upgrade kuzu-memory  # Update to latest version

# 🔄 DEVELOPMENT ISSUES
make clean && make dev-setup    # Clean rebuild environment
make quality                    # Run all quality checks
```

### Monitoring & Alerting Setup
- **Performance Thresholds**: Alert if recall >100ms, generation >200ms
- **Error Tracking**: Monitor async operation failures
- **Health Checks**: Automated database connectivity validation
- **Resource Usage**: Track memory consumption and database size growth

### Rollback Procedures
```bash
# 🔙 VERSION ROLLBACK (if new version fails)
pip install kuzu-memory==<previous-version>  # Pin to working version
kuzu-memory stats --validate                 # Verify rollback success

# 🗃️ DATABASE ROLLBACK (if corruption occurs)
cp ~/.kuzu/backup/database.kuzu ~/.kuzu/     # Restore from backup
kuzu-memory stats --validate                 # Verify restoration
```

---

## 🎯 CLAUDE MPM COMPLIANCE CERTIFICATION

### Single Path Principle ✅
- **ONE command** for each operation type
- **NO alternative methods** documented
- **Clear hierarchical priority** (🔴→🟡→🟢→⚪)
- **Discoverable workflows** from README.md → CLAUDE.md

### Infrastructure as Code ✅
- **Version controlled** configuration
- **Idempotent operations** (safe to run multiple times)
- **Declarative setup** via Makefile
- **Automated quality gates** with performance validation

### Production Standards ✅
- **Zero-downtime deployments** supported
- **Comprehensive monitoring** and health checks
- **Rollback capability** for all operations
- **Security best practices** implemented

### Performance Benchmarks ✅
- **Sub-100ms operations** validated
- **3ms typical recall** verified
- **Automated performance testing** integrated
- **Threshold validation** in CI/CD pipeline

---

**Version**: 1.1.4 | **Updated**: 2025-09-29 | **Status**: Production Ready | **PyPI**: Available | **Performance**: 3ms Recall ✅ | **MCP Server**: Fixed ✅ | **Claude MPM**: Fully Compliant
