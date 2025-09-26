# KuzuMemory - AI-Optimized Project Documentation

**Project-specific memory system with intelligent context recall for AI applications**

## 🎯 Priority Index

### 🔴 CRITICAL Instructions (Must Follow)
- **NEVER modify core memory schema without migration** - Database schema changes require proper migration scripts
- **ALWAYS use async operations for memory learning** - `learn` command must be non-blocking (fire-and-forget)
- **NEVER block on learn operations** - They must be asynchronous by default for AI integration
- **ALWAYS maintain <100ms response time** for `enhance`/`recall` operations
- **Security: Never store sensitive data** (passwords, keys, tokens) in memories
- **Git integration: Memories are project-specific** and committed to `kuzu-memories/` directory
- **CLI-only integration** - Use subprocess calls, not direct Python imports for AI systems

### 🟡 IMPORTANT Instructions
- **Architecture: Layered design** - CLI → Async System → Core Memory Engine → Kuzu DB
- **Performance: Connection pooling** - Use LRU caching, batch operations, CLI adapter for speed
- **Testing: Run pytest** for unit tests, separate async operations testing
- **AI Integration: Always subprocess** calls to CLI, never direct memory imports
- **Error handling: Fail gracefully** with clear error messages, respect --quiet flag
- **Project Model: No user-scoped memories** - All memories are project-specific, shared by team

### 🟢 STANDARD Instructions
- **Code style: Black formatting** with type hints and comprehensive docstrings
- **CLI Framework: Click** with rich formatting, maintain backward compatibility
- **Database: Kuzu graph database** in `.kuzu-memory/` or `kuzu-memories/` directory
- **Logging: Standard Python logging** with debug support, respect --quiet mode
- **Performance targets**: <100ms recall, <200ms generation, async learning
- **Memory Types**: IDENTITY (never expire), PREFERENCE, DECISION (90d), PATTERN (30d), etc.

### ⚪ OPTIONAL Instructions
- **Documentation updates** in `docs/developer/` when adding features
- **Performance profiling** with cProfile for optimization work
- **Memory visualization** features for debugging and analysis
- **Advanced CLI features** like progress bars and interactive prompts

---

## 🎯 **What is KuzuMemory?**

KuzuMemory is an intelligent memory system designed specifically for AI applications. It provides persistent, project-specific memory that enables AI assistants to maintain context across conversations and learn from interactions without requiring LLM calls.

### **Key Features:**
- 🧠 **Intelligent Memory** - Stores and recalls project-specific information
- ⚡ **High Performance** - Sub-100ms context retrieval, async learning
- 🔄 **AI Integration** - Seamless integration with AI systems like Claude/Auggie
- 📁 **Project-Based** - Memories are project-specific and git-committed
- 🚀 **Zero Config** - Works out of the box with sensible defaults
- 🎯 **CLI-First** - Simple command-line interface for all operations

### **Perfect For:**
- AI assistants that need persistent memory
- Project-specific context and knowledge management
- Team collaboration with shared AI context
- Learning from user interactions and corrections
- Maintaining conversation history and preferences

---

## 🚀 **Quick Start**

### **Installation:**
```bash
pip install kuzu-memory
```

### **Initialize Project:**
```bash
cd your-project
kuzu-memory init
```

### **Basic Usage:**
```bash
# Store project information
kuzu-memory remember "This project uses FastAPI with PostgreSQL"

# Enhance prompts with context
kuzu-memory enhance "How do I structure an API endpoint?" --format plain

# Learn from conversations (async by default)
kuzu-memory learn "User prefers TypeScript over JavaScript" --quiet
```

---

## 📚 **Developer Documentation**

### **Core Documentation:**
- **[Goals & Vision](docs/developer/goals.md)** - Project objectives and design philosophy
- **[Architecture Overview](docs/developer/architecture.md)** - System design and components
- **[Core Features](docs/developer/features.md)** - Detailed feature documentation
- **[API Reference](docs/developer/api.md)** - Complete API documentation
- **[Performance Guide](docs/developer/performance.md)** - Performance characteristics and optimization

### **Integration Guides:**
- **[AI Integration](docs/developer/ai-integration.md)** - Integrating with AI systems
- **[Auggie Integration](docs/developer/auggie-integration.md)** - Specific Auggie/Claude integration
- **[CLI Reference](docs/developer/cli-reference.md)** - Complete CLI documentation
- **[Async Operations](docs/developer/async-operations.md)** - Async memory system guide
- **[Temporal Decay](docs/developer/temporal-decay.md)** - Memory retention and expiration system

### **Advanced Topics:**
- **[Memory Models](docs/developer/memory-models.md)** - Memory types and retention policies
- **[Database Schema](docs/developer/database-schema.md)** - Kuzu graph database structure
- **[Configuration](docs/developer/configuration.md)** - Advanced configuration options
- **[Testing Guide](docs/developer/testing.md)** - Testing strategies and tools

### **Development:**
- **[Contributing](docs/developer/contributing.md)** - How to contribute to the project
- **[Development Setup](docs/developer/development.md)** - Setting up development environment
- **[Release Process](docs/developer/releases.md)** - Release and deployment process

---

## 🏗️ **Architecture Overview**

KuzuMemory is built with a **layered architecture** optimized for performance and AI integration:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface                            │
│  kuzu-memory enhance | learn | recall | stats | project    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Async Memory System                        │
│     Queue Manager | Background Learner | Status Reporter   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Core Memory Engine                        │
│   Memory Generation | Context Attachment | Deduplication   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Kuzu Graph Database                        │
│      Memories | Entities | Patterns | Relationships        │
└─────────────────────────────────────────────────────────────┘
```

### **Key Design Principles:**
1. **Performance First** - Sub-100ms context retrieval, async learning
2. **AI-Optimized** - Designed specifically for AI system integration
3. **Project-Centric** - Memories are project-specific, not user-specific
4. **Git-Integrated** - Memories are committed and shared with the team
5. **Zero-Config** - Works out of the box with intelligent defaults

---

## 🎮 **Usage Examples**

### **AI Assistant Integration:**
```python
import subprocess

# Enhance user prompt with project context
def enhance_prompt(user_input):
    result = subprocess.run([
        'kuzu-memory', 'enhance', user_input, '--format', 'plain'
    ], capture_output=True, text=True)
    return result.stdout.strip()

# Store learning from conversation (async, non-blocking)
def store_learning(content):
    subprocess.run([
        'kuzu-memory', 'learn', content, '--quiet'
    ], check=False)

# Usage in AI conversation
user_query = "How should I handle authentication?"
enhanced_query = enhance_prompt(user_query)
ai_response = generate_ai_response(enhanced_query)
store_learning(f"User asked about auth: {ai_response}")
```

### **Project Memory Management:**
```bash
# Initialize project memories
kuzu-memory init

# Store project decisions
kuzu-memory remember "We use FastAPI with PostgreSQL and Redis"
kuzu-memory learn "Team prefers async/await patterns" --source team-convention

# Query project context
kuzu-memory recall "What's our database setup?"
kuzu-memory enhance "How do I connect to the database?" --format plain

# Monitor system
kuzu-memory stats
kuzu-memory recent --format list
```

---

## 🔧 **Integration with AI Systems**

KuzuMemory is designed for seamless integration with AI systems:

### **Auggie/Claude Integration:**
- **Markdown-based rules** in `AGENTS.md` and `.augment/rules/`
- **Automatic context enhancement** before AI responses
- **Async learning** from conversations without blocking
- **Project-specific memory** shared across team

### **Universal AI Integration:**
- **CLI-only interface** - works with any AI system
- **Standard subprocess calls** - no HTTP complexity
- **Fast context retrieval** - <100ms response time
- **Async learning** - non-blocking memory operations

---

## 📊 **Performance Characteristics**

- **Context Retrieval**: <100ms (synchronous, needed for AI responses)
- **Memory Learning**: Async by default (non-blocking)
- **Database**: Kuzu graph database with optimized queries
- **Memory Usage**: Efficient with LRU caching and connection pooling
- **Scalability**: Handles thousands of memories per project

---

## 🤝 **Contributing**

We welcome contributions! See [docs/developer/contributing.md](docs/developer/contributing.md) for:
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process

---

## 📄 **License**

MIT License - see [LICENSE](LICENSE) for details.

---

## 🆘 **Support**

- **Documentation**: [docs/developer/](docs/developer/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

**KuzuMemory: Making AI assistants smarter, one memory at a time.** 🧠✨

---

## 🔧 **Single-Path Workflows**

### **🚀 Development Workflows (ONE Command Each)**
```bash
# Installation and setup
make install          # Install all dependencies
make dev             # Install development dependencies
make init            # Initialize project memories

# Code quality (ONE path)
make test            # Run all tests (unit, integration, e2e)
make format          # Format all code (black + isort)
make lint            # Lint code (ruff check)
make typecheck       # Type check (mypy)
make quality         # Run all quality checks

# Build and deployment
make build           # Build package for distribution
make publish         # Publish to PyPI
make clean           # Clean build artifacts

# Development utilities
make docs            # Build documentation
make profile         # Performance profiling
make memory-test     # Test memory system performance
```

### **📊 Project Analysis Commands**
```bash
# Project health
kuzu-memory project --verbose    # Complete project status
kuzu-memory stats --detailed     # Comprehensive statistics
kuzu-memory recent --format json # Latest memories

# Performance analysis
kuzu-memory optimize --enable-cli  # Use CLI adapter for speed
time kuzu-memory recall "test query" # Measure performance
```

### **🤖 AI Integration Pattern**
```python
# Standard AI integration (ALWAYS use this pattern)
import subprocess

def enhance_with_memory(prompt: str) -> str:
    """Enhance prompt with project memories."""
    result = subprocess.run([
        'kuzu-memory', 'enhance', prompt, '--format', 'plain'
    ], capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else prompt

def learn_async(content: str, source: str = "ai-conversation") -> None:
    """Store learning asynchronously (non-blocking)."""
    subprocess.run([
        'kuzu-memory', 'learn', content,
        '--source', source, '--quiet'
    ], check=False)  # Fire and forget
```

### **🔍 Memory Management Workflow**
```bash
# 1. Initialize (once per project)
kuzu-memory init

# 2. Store project context
kuzu-memory remember "Project uses FastAPI + PostgreSQL"

# 3. Use in AI interactions
kuzu-memory enhance "How do I structure the API?" --format plain

# 4. Learn from conversations (async)
kuzu-memory learn "User prefers dependency injection pattern" --quiet

# 5. Monitor and maintain
kuzu-memory stats
kuzu-memory cleanup --force  # Remove expired memories
```

### **⚡ Performance Optimization Checklist**
- ✅ Use CLI adapter: `kuzu-memory optimize --enable-cli`
- ✅ Keep recall operations under 100ms
- ✅ Use async learning: `--quiet` flag for non-blocking operations
- ✅ Batch operations when possible
- ✅ Monitor with: `kuzu-memory stats --detailed`

### **🎯 Meta-Instructions for Documentation Maintenance**
When updating this documentation:
1. **Maintain priority order**: 🔴 → 🟡 → 🟢 → ⚪
2. **Keep single-path principle**: ONE command per operation
3. **Test all command examples** before documenting
4. **Update performance targets** based on real measurements
5. **Validate AI integration patterns** with actual subprocess calls

---

## 📋 **Project Structure Quick Reference**

```
kuzu-memory/
├── src/kuzu_memory/           # Core source code
│   ├── cli/                   # CLI interface (commands.py)
│   ├── core/                  # Memory engine (memory.py, models.py)
│   ├── async_memory/          # Async operations system
│   ├── storage/               # Database adapters (kuzu_adapter.py)
│   ├── recall/                # Memory recall strategies
│   └── integrations/          # AI system integrations
├── tests/                     # Comprehensive test suite
├── kuzu-memories/            # Project memories (git-committed)
├── .claude-mpm/              # MPM configuration
├── Makefile                  # Single-path workflows
├── pyproject.toml           # Package configuration
└── CLAUDE.md                # This file (priority instructions)
```

**🎯 Key Files for AI Agents:**
- `CLAUDE.md` - Priority instructions (this file)
- `Makefile` - Single-path command workflows
- `src/kuzu_memory/cli/commands.py` - CLI interface
- `src/kuzu_memory/core/memory.py` - Core memory operations
- `pyproject.toml` - Dependencies and tooling configuration
