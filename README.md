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
- **🤖 Hook Compatible** - Ready for claude-mpm hook integration

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

### Claude Desktop Integration

KuzuMemory can be integrated with Claude Desktop via MCP (Model Context Protocol) for seamless memory operations. The system is also ready for claude-mpm hook integration:

```bash
# Automatic setup with pipx detection
python scripts/install-claude-desktop.py

# Or with custom options
python scripts/install-claude-desktop.py --memory-db ~/custom-path/memorydb
```

The installer automatically:
- Detects your pipx installation
- Configures Claude Desktop MCP settings
- Creates backup of existing configuration
- Validates the installation
- Supports async learning with 5-second wait behavior

See [Claude Desktop Setup Guide](docs/CLAUDE_DESKTOP_SETUP.md) for detailed instructions.

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
kuzu-memory remember "I prefer using TypeScript for frontend projects"

# Recall memories
kuzu-memory recall "What do I prefer for frontend?"

# View statistics
kuzu-memory stats
```

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

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run benchmarks
pytest tests/ -m benchmark

# Check coverage
pytest --cov=kuzu_memory
```

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
