# KuzuMemory - Quick Start Guide

**Get productive with KuzuMemory in 5 minutes**

---

## 🚀 **5-Minute Setup**

### **Step 1: Installation (1 minute)**
```bash
# Clone and install
git clone <repository>
cd kuzu-memory
make dev-setup    # Installs everything + initializes memories
```

### **Step 2: Verify Setup (30 seconds)**
```bash
# Test performance
make memory-test

# Check code quality
make quality
```

### **Step 3: Try It Out (30 seconds)**
```bash
# Store a memory
kuzu-memory remember "I'm working on KuzuMemory, an AI memory system"

# Recall memories
kuzu-memory recall "What am I working on?"

# AI-style enhancement
kuzu-memory enhance "How do I improve performance?" --format plain
```

### **Step 4: Validate Everything (1 minute)**
```bash
# Run full test suite
make test

# Check all workflows work
make all
```

---

## 🎯 **Essential Commands**

### **🔧 Development (ONE command each)**
```bash
make install     # Install production dependencies
make dev        # Install development dependencies
make init       # Initialize project memories
make test       # Run all tests
make quality    # Format + lint + typecheck
make build      # Build package
make clean      # Clean artifacts
```

### **🧠 Memory Operations**
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

### **📊 Monitoring**
```bash
# Project health
kuzu-memory project --verbose

# Performance stats
kuzu-memory stats --detailed

# Recent memories
kuzu-memory recent --format json
```

---

## 🤖 **AI Integration (Copy & Paste)**

### **Universal Pattern (Works with any AI system)**
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

### **Quick Integration Test**
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

## 📁 **Project Structure (Know These Files)**

```
kuzu-memory/
├── CLAUDE.md           # 🔴 PRIORITY INSTRUCTIONS (Read First!)
├── Makefile           # 🔴 Single-path commands
├── QUICK_START.md     # 🔴 This file
├── DEVELOPER.md       # 🟡 Comprehensive dev guide
├── CODE_STRUCTURE.md  # 🟡 Architecture analysis
├── pyproject.toml     # 🟢 Dependencies and tools
├── src/kuzu_memory/   # 🟢 Core source code
├── tests/            # 🟢 Test suite
└── .claude-mpm/      # 🟢 MPM memories
```

**🎯 Start with these files:**
1. **CLAUDE.md** - Priority-based instructions
2. **This file** - Quick start commands
3. **Makefile** - All available commands
4. **DEVELOPER.md** - Deep technical details

---

## ⚡ **Performance Optimization**

### **Enable CLI Adapter (2-3x speed boost)**
```bash
# Check if Kuzu CLI is available
kuzu --version

# Enable CLI adapter for performance
kuzu-memory optimize --enable-cli

# Test performance improvement
time kuzu-memory recall "performance test"
```

### **Monitor Performance**
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

## 🔍 **Troubleshooting**

### **Setup Issues**
```bash
# Check tools are available
make check-tools

# Verify Python version (need 3.11+)
python --version

# Reinstall dependencies
make clean && make dev
```

### **Performance Issues**
```bash
# Enable CLI adapter
kuzu-memory optimize --enable-cli

# Check database size
kuzu-memory project --verbose

# Clean up old memories
kuzu-memory cleanup --force
```

### **Integration Issues**
```bash
# Test CLI accessibility
kuzu-memory --help

# Test subprocess pattern
python -c "import subprocess; print(subprocess.run(['kuzu-memory', '--help']).returncode)"

# Debug with verbose output
kuzu-memory --debug enhance "test prompt"
```

---

## 📚 **Learning Path**

### **Beginner (30 minutes)**
1. ✅ Complete 5-minute setup above
2. 📖 Read [CLAUDE.md](CLAUDE.md) priority sections (🔴 Critical)
3. 🧪 Try all essential commands
4. 🤖 Test AI integration pattern

### **Intermediate (2 hours)**
1. 📖 Read [DEVELOPER.md](DEVELOPER.md) architecture overview
2. 🔍 Explore [CODE_STRUCTURE.md](CODE_STRUCTURE.md)
3. 🧪 Run `make test` and understand test structure
4. ⚡ Practice performance optimization

### **Advanced (1 day)**
1. 💻 Read entire [DEVELOPER.md](DEVELOPER.md)
2. 🔬 Study memory system implementation
3. 🏗️ Contribute to codebase using established patterns
4. 📝 Update documentation following priority system

---

## 🎯 **Success Checklist**

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

## 🤝 **Next Steps**

### **For AI Agents:**
- Use CLAUDE.md as primary instruction source
- Follow single-path workflows in Makefile
- Always use subprocess pattern for integration
- Respect performance targets (<100ms recall)

### **For Developers:**
- Read DEVELOPER.md for comprehensive guidance
- Follow established code patterns in engineer.md
- Use qa.md for testing strategies
- Contribute following the single-path principle

### **For Contributors:**
- Start with `make dev-setup`
- Run `make pre-commit` before committing
- Update relevant memory files with new patterns
- Maintain documentation priority system

---

**🧠 You're now ready to build intelligent, memory-enhanced AI applications with KuzuMemory!**

**🔗 Quick Links:**
- [CLAUDE.md](CLAUDE.md) - Priority instructions
- [DEVELOPER.md](DEVELOPER.md) - Comprehensive guide
- [Makefile](Makefile) - All commands
- [CODE_STRUCTURE.md](CODE_STRUCTURE.md) - Architecture details