# Getting Started with KuzuMemory

**Fast-track guide to productive AI memory management in 5 minutes**

> **Replaces**: This document consolidates and replaces:
> - `docs/QUICK_START.md`
> - `docs/SETUP.md`
> - `docs/README_CLI.md`

---

## 🚀 5-Minute Quick Start

### Step 1: Installation (1 minute)

Choose your installation method:

#### Production Install (Recommended - pipx)
```bash
# Install via pipx (isolated environment)
pipx install kuzu-memory

# Or use our installer script
python scripts/install-pipx.py
```

#### Python Package Install (For Python projects)
```bash
pip install kuzu-memory
```

#### Development Install (For contributing)
```bash
git clone <repository>
cd kuzu-memory
make dev-setup    # Installs everything + initializes memories
```

### Step 2: Initialize & Verify (30 seconds)

```bash
# Initialize memory system
kuzu-memory init

# Check installation
kuzu-memory --version    # Should show v1.1.4+

# For development: Test performance and quality
make test && make quality
```

### Step 3: Try It Out (30 seconds)

```bash
# Store a memory
kuzu-memory remember "I'm working on KuzuMemory, an AI memory system"

# Recall memories
kuzu-memory recall "What am I working on?"

# AI-style enhancement
kuzu-memory enhance "How do I improve performance?" --format plain
```

### Step 4: Instant Demo (Optional)

```bash
# See KuzuMemory in action immediately - no setup required!
kuzu-memory demo

# Or run interactive quickstart
kuzu-memory quickstart
```

---

## 🎯 Essential Commands

### Memory Operations

```bash
# Initialize project memories
kuzu-memory init

# Store information
kuzu-memory remember "Project uses Python 3.11+ with Kuzu database"

# Find relevant info
kuzu-memory recall "What technology stack do we use?"

# Enhance AI prompts (fast, <100ms)
kuzu-memory enhance "How should I structure the code?" --format plain

# Learn from conversations (async, non-blocking)
kuzu-memory learn "User prefers FastAPI over Flask" --quiet
```

### Monitoring & Stats

```bash
# Project health
kuzu-memory project --verbose

# Performance stats
kuzu-memory stats --detailed

# Recent memories
kuzu-memory recent --format json
```

### Development Commands (ONE command each)

```bash
make install     # Install production dependencies
make dev         # Install development dependencies
make init        # Initialize project memories
make test        # Run all tests
make quality     # Format + lint + typecheck
make build       # Build package
make clean       # Clean artifacts
```

---

## 🤖 AI Integration Pattern (Universal)

This pattern works with **any AI system** (Claude, GPT, Auggie, etc.):

### Python Integration

```python
import subprocess

def enhance_with_memory(prompt: str) -> str:
    """Enhance prompt with project memories"""
    result = subprocess.run([
        'kuzu-memory', 'enhance', prompt, '--format', 'plain'
    ], capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else prompt

def learn_async(content: str, source: str = "ai-conversation") -> None:
    """Store learning asynchronously (non-blocking)"""
    subprocess.run([
        'kuzu-memory', 'learn', content,
        '--source', source, '--quiet'
    ], check=False)  # Fire and forget

# Usage in AI workflow
user_query = "How do I optimize database queries?"
enhanced_query = enhance_with_memory(user_query)
ai_response = your_ai_system(enhanced_query)
learn_async(f"User asked about DB optimization: {ai_response}")
```

### Quick Integration Test

```bash
# Test the pattern works
python -c "
import subprocess
result = subprocess.run(['kuzu-memory', 'enhance', 'test query', '--format', 'plain'],
                       capture_output=True, text=True, timeout=5)
print('✅ Enhancement works:', result.returncode == 0)

result = subprocess.run(['kuzu-memory', 'learn', 'test learning', '--quiet'])
print('✅ Async learning works:', result.returncode == 0)
"
```

---

## 📋 Installation Options (Detailed)

### Production: pipx Installation (Recommended)

pipx installs KuzuMemory in an isolated environment:

```bash
# Install pipx if needed
pip install pipx
pipx ensurepath

# Install KuzuMemory
pipx install kuzu-memory

# Use anywhere
kuzu-memory demo
kuzu-memory --help
```

**Benefits:**
- ✅ Isolated from other Python packages
- ✅ Available system-wide as `kuzu-memory` command
- ✅ Easy updates: `pipx upgrade kuzu-memory`
- ✅ Clean uninstall: `pipx uninstall kuzu-memory`

### Development: Source Installation

For working on KuzuMemory source code:

```bash
# Use the development shell script
./kuzu-memory.sh --setup    # One-time setup
./kuzu-memory.sh demo       # Run commands from source
./kuzu-memory.sh --help-dev # Development help
```

**Features:**
- ✅ Automatic virtual environment creation
- ✅ Dependency installation and updates
- ✅ Proper Python path configuration
- ✅ Colored output and error handling
- ✅ Works with existing venvs (venv, .venv, conda)

### Manual Development Setup

If you prefer manual setup:

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install in development mode
pip install -e .

# 4. Run from source
python -m kuzu_memory.cli.commands demo
```

---

## 💡 Rich Help System

Every command is self-documenting with rich help and examples:

```bash
kuzu-memory --help           # Beautiful overview with examples
kuzu-memory examples         # Comprehensive tutorials
kuzu-memory examples workflow # Complete workflow examples
kuzu-memory COMMAND --help   # Detailed help for any command
```

### Examples for Everything

```bash
kuzu-memory examples remember   # Memory storage examples
kuzu-memory examples recall     # Query examples
kuzu-memory examples auggie     # AI integration examples
kuzu-memory examples workflow   # Complete workflows
kuzu-memory examples patterns   # What works best
```

### Interactive Guidance

```bash
kuzu-memory setup      # Interactive configuration wizard
kuzu-memory tips       # Best practices and optimization
kuzu-memory quickstart # Full guided setup
```

---

## 🎨 Beautiful CLI Experience

Rich formatting with colors, emojis, and structured layouts:

```
╭─────────────────────────── 🚀 Quick Start ───────────────────────────╮
│ Welcome to KuzuMemory! 🧠                                           │
│                                                                      │
│ Get started in 3 minutes:                                           │
│ • kuzu-memory quickstart  (guided setup)                            │
│ • kuzu-memory demo        (instant demo)                             │
│ • kuzu-memory --help      (full help)                               │
╰──────────────────────────────────────────────────────────────────────╯
```

---

## 🔄 Complete Workflows

### Personal Assistant Workflow

```bash
# 1. Store your context
kuzu-memory remember "I'm Alex, a senior Python developer" --user-id alex
kuzu-memory remember "I prefer FastAPI and PostgreSQL" --user-id alex

# 2. Get personalized help
kuzu-memory enhance "How do I build a REST API?" --user-id alex
# Result: Enhanced with Alex's FastAPI and PostgreSQL preferences

# 3. Learn from interactions
kuzu-memory learn "What framework?" "Use Django" \
  --feedback "I prefer FastAPI" --user-id alex
```

### Team Knowledge Base Workflow

```bash
# Store team decisions
kuzu-memory remember "We use microservices with Docker" --user-id team
kuzu-memory remember "PostgreSQL for data, Redis for cache" --user-id team

# Query team knowledge
kuzu-memory recall "What's our architecture?" --user-id team
```

---

## ⚡ Performance Optimization

### Enable CLI Adapter (2-3x speed boost)

```bash
# Check if Kuzu CLI is available
kuzu --version

# Enable CLI adapter for performance
kuzu-memory optimize --enable-cli

# Test performance improvement
time kuzu-memory recall "performance test"
```

### Monitor Performance

```bash
# Check targets: <100ms recall, <200ms generation
make memory-test

# Detailed performance stats
kuzu-memory stats --detailed

# Profile specific operations
time kuzu-memory enhance "test prompt"
time kuzu-memory learn "test content" --quiet
```

---

## 📁 Project Structure

```
kuzu-memory/
├── CLAUDE.md           # 🔴 PRIORITY INSTRUCTIONS (Read First!)
├── Makefile           # 🔴 Single-path commands
├── GETTING_STARTED.md # 🔴 This file
├── docs/
│   ├── CLAUDE_SETUP.md    # 🟡 Claude integration guide
│   ├── MEMORY_SYSTEM.md   # 🟡 Memory types and usage
│   ├── DEVELOPER.md       # 🟡 Comprehensive dev guide
│   └── ARCHITECTURE.md    # 🟡 Technical architecture
├── pyproject.toml     # 🟢 Dependencies and tools
├── src/kuzu_memory/   # 🟢 Core source code
├── tests/             # 🟢 Test suite
└── .claude-mpm/       # 🟢 MPM memories
```

**Start with these files:**
1. **CLAUDE.md** - Priority-based instructions
2. **This file** - Quick start commands
3. **Makefile** - All available commands
4. **DEVELOPER.md** - Deep technical details

---

## 🔍 Troubleshooting

### Setup Issues

```bash
# Check tools are available
make check-tools

# Verify Python version (need 3.11+)
python --version

# Reinstall dependencies
make clean && make dev
```

### Performance Issues

```bash
# Enable CLI adapter
kuzu-memory optimize --enable-cli

# Check database size
kuzu-memory project --verbose

# Clean up old memories
kuzu-memory cleanup --force
```

### Integration Issues

```bash
# Test CLI accessibility
kuzu-memory --help

# Test subprocess pattern
python -c "import subprocess; print(subprocess.run(['kuzu-memory', '--help']).returncode)"

# Debug with verbose output
kuzu-memory --debug enhance "test prompt"
```

### Production Installation Issues

**Command not found:**
```bash
pipx ensurepath              # Add to PATH
pipx list                    # Check installation
pipx reinstall kuzu-memory   # Reinstall
```

**Version conflicts:**
```bash
pipx uninstall kuzu-memory   # Clean uninstall
pipx install kuzu-memory     # Fresh install
```

### Development Setup Issues

**Virtual environment not found:**
```bash
./kuzu-memory.sh --venv-info  # Check status
./kuzu-memory.sh --setup      # Recreate environment
```

**Import errors:**
```bash
# Reinstall dependencies
./kuzu-memory.sh --setup
```

**Permission errors:**
```bash
chmod +x kuzu-memory.sh
```

---

## 📊 Verification

### Test Development Setup

```bash
./kuzu-memory.sh --venv-info     # Check environment
./kuzu-memory.sh demo            # Test functionality
./kuzu-memory.sh --help          # Verify CLI
```

### Test Production Installation

```bash
kuzu-memory --version            # Check version
kuzu-memory demo                 # Test functionality
pipx list                        # Verify installation
```

---

## 🎯 Success Checklist

After completing this guide, you should be able to:

- [ ] Run all `make` commands successfully
- [ ] Store and recall project memories
- [ ] Integrate KuzuMemory with AI systems using subprocess
- [ ] Optimize performance with CLI adapter
- [ ] Understand the priority-based documentation system
- [ ] Navigate the codebase confidently
- [ ] Follow single-path workflows for all tasks
- [ ] Maintain <100ms recall, <200ms generation performance

---

## 🎯 Key Features

### Lightning Fast
- No LLM calls required
- Sub-20ms memory recall
- Local graph database storage
- Offline operation

### Intelligent Context
- Pattern-based memory extraction
- Semantic similarity matching
- Temporal relevance scoring
- User-scoped memories

### AI Integration
- Automatic prompt enhancement
- Response learning and correction
- Custom rule creation
- Performance monitoring

### Developer Experience
- Rich CLI with examples
- Self-documenting commands
- Interactive setup wizards
- Beautiful error messages

---

## 🚀 Next Steps

### For AI Agents
- Use CLAUDE.md as primary instruction source
- Follow single-path workflows in Makefile
- Always use subprocess pattern for integration
- Respect performance targets (<100ms recall)

### For Developers
- Read DEVELOPER.md for comprehensive guidance
- Follow established code patterns
- Use qa.md for testing strategies
- Contribute following the single-path principle

### For Contributors
- Start with `make dev-setup`
- Run `make pre-commit` before committing
- Update relevant memory files with new patterns
- Maintain documentation priority system

### For Claude Integration
- See [CLAUDE_SETUP.md](CLAUDE_SETUP.md) for complete integration guide
- Install Claude Desktop MCP server or Claude Code hooks
- Configure project-specific memory settings

---

## 📚 Learning Path

### Beginner (30 minutes)
1. ✅ Complete 5-minute setup above
2. 📖 Read [CLAUDE.md](../CLAUDE.md) priority sections (🔴 Critical)
3. 🧪 Try all essential commands
4. 🤖 Test AI integration pattern

### Intermediate (2 hours)
1. 📖 Read [DEVELOPER.md](DEVELOPER.md) architecture overview
2. 🔍 Explore [ARCHITECTURE.md](ARCHITECTURE.md)
3. 🧪 Run `make test` and understand test structure
4. ⚡ Practice performance optimization

### Advanced (1 day)
1. 💻 Read entire [DEVELOPER.md](DEVELOPER.md)
2. 🔬 Study memory system implementation
3. 🏗️ Contribute to codebase using established patterns
4. 📝 Update documentation following priority system

---

## 🆘 Getting Help

Every command has comprehensive help:

```bash
kuzu-memory --help              # Main overview
kuzu-memory COMMAND --help      # Command-specific help
kuzu-memory examples TOPIC      # Examples and tutorials
kuzu-memory tips                # Best practices
```

**No external documentation needed** - everything is built into the CLI!

---

**🧠 You're now ready to build intelligent, memory-enhanced AI applications with KuzuMemory!**

**Quick Links:**
- [CLAUDE.md](../CLAUDE.md) - Priority instructions
- [CLAUDE_SETUP.md](CLAUDE_SETUP.md) - Claude integration
- [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md) - Memory types and usage
- [DEVELOPER.md](DEVELOPER.md) - Comprehensive guide
- [Makefile](../Makefile) - All commands
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture details
