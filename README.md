# KuzuMemory

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/kuzu-memory/kuzu-memory/workflows/Tests/badge.svg)](https://github.com/kuzu-memory/kuzu-memory/actions)

**Lightweight, embedded graph-based memory system for AI applications**

KuzuMemory provides fast, offline memory capabilities for chatbots and AI systems without requiring LLM calls. It uses pattern matching and local graph storage to remember and recall contextual information.

## ✨ Key Features

- **🚀 No LLM Dependencies** - Operates using pattern matching and local NER only
- **⚡ Fast Performance** - <10ms memory recall, <20ms memory generation
- **💾 Embedded Database** - Single-file Kuzu graph database
- **🔄 Git-Friendly** - Database files <10MB, perfect for version control
- **🔌 Simple API** - Just two methods: `attach_memories()` and `generate_memories()`
- **📱 Offline First** - Works completely without internet connection

## 🚀 Quick Start

### Installation

```bash
pip install kuzu-memory
```

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

### Memory Types

KuzuMemory automatically categorizes memories:

- **Identity** - Personal information (never expires)
- **Preference** - User preferences and settings
- **Decision** - Project decisions and agreements
- **Pattern** - Code patterns and best practices
- **Solution** - Problem-solution pairs
- **Status** - Current state information (expires quickly)
- **Context** - Session context (expires daily)

### Pattern-Based Extraction

No LLM required! KuzuMemory uses regex patterns to identify:

```python
# Automatically detected patterns
"Remember that we use Python for backend"     # → Decision memory
"My name is Alice"                            # → Identity memory  
"I prefer dark mode"                          # → Preference memory
"Always use type hints"                       # → Pattern memory
```

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

| Operation | Target | Typical |
|-----------|--------|---------|
| Memory Recall | <10ms | ~3ms |
| Memory Generation | <20ms | ~8ms |
| Database Size | <500 bytes/memory | ~300 bytes |
| RAM Usage | <50MB | ~25MB |

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
