# Project Management Memory - KuzuMemory

## Project Overview
- **Name**: KuzuMemory
- **Type**: Python CLI library/tool for AI applications
- **Version**: 1.0.0
- **Purpose**: Intelligent memory system with project-specific context recall
- **Architecture**: Layered design - CLI → Async System → Core → Kuzu DB

## Key Technologies
- **Language**: Python 3.11+
- **Database**: Kuzu graph database
- **CLI**: Click framework with Rich formatting
- **Async**: Background learning system
- **AI Integration**: Subprocess-based for universal compatibility

## Core Features
- Sub-100ms memory recall for AI responsiveness
- Async learning operations (non-blocking)
- Project-specific memories (git-committed)
- CLI-first design with Rich UI
- Multi-strategy memory recall
- Entity and pattern extraction (no LLM required)

## Development Standards
- **Single-path workflows**: ONE command for each operation
- **Priority-based documentation**: 🔴 Critical → 🟡 Important → 🟢 Standard → ⚪ Optional
- **Performance targets**: <100ms recall, <200ms generation
- **Code style**: Black formatting with type hints
- **Testing**: pytest with >95% coverage for core components

## Project Structure
```
kuzu-memory/
├── src/kuzu_memory/          # Core source code
│   ├── cli/                  # CLI interface (commands.py)
│   ├── core/                 # Memory engine (memory.py, models.py)
│   ├── async_memory/         # Async operations system
│   ├── storage/              # Database adapters
│   ├── recall/               # Memory recall strategies
│   └── integrations/         # AI system integrations
├── tests/                    # Comprehensive test suite
├── kuzu-memories/           # Project memories (git-committed)
├── Makefile                 # Single-path workflows
├── CLAUDE.md                # Priority instructions for AI agents
└── pyproject.toml          # Package configuration
```

## Key Commands
- `make install` - Install dependencies
- `make test` - Run all tests
- `make quality` - Complete quality check (format + lint + typecheck)
- `make build` - Build package
- `kuzu-memory init` - Initialize project memories
- `kuzu-memory enhance "prompt"` - Enhance with context (<100ms)
- `kuzu-memory learn "content" --quiet` - Async learning

## AI Integration Pattern
```python
import subprocess

# Enhance prompts (synchronous, fast)
result = subprocess.run(['kuzu-memory', 'enhance', prompt, '--format', 'plain'],
                       capture_output=True, text=True, timeout=5)

# Learn from interactions (async, non-blocking)
subprocess.run(['kuzu-memory', 'learn', content, '--quiet'], check=False)
```

## Critical Instructions
- NEVER modify memory schema without migration
- ALWAYS use async learning (--quiet flag)
- NEVER block on learn operations
- ALWAYS maintain <100ms recall performance
- Use subprocess calls for AI integration (not direct imports)