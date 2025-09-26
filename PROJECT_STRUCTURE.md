# KuzuMemory Project Structure

## Clean Python Package Structure

The project has been reorganized to follow Python packaging best practices:

```
kuzu-memory/
│
├── src/                      # Source code (Python package)
│   └── kuzu_memory/         # Main package
│       ├── __init__.py
│       ├── cli/             # CLI commands
│       ├── core/            # Core memory engine
│       ├── async_memory/    # Async operations
│       ├── storage/         # Database adapters
│       ├── recall/          # Memory recall strategies
│       ├── integrations/    # AI system integrations
│       ├── installers/      # Installation utilities
│       └── utils/           # Utilities
│
├── tests/                   # All test files
│   ├── test_*.py           # Unit and integration tests
│   └── ...
│
├── docs/                    # Documentation
│   ├── developer/          # Developer documentation
│   └── *.md                # Other documentation files
│
├── scripts/                 # Utility scripts
│   ├── install.py          # Installation script
│   ├── publish.py          # Publishing script
│   ├── verify_installation.py
│   └── *.sh                # Shell scripts
│
├── examples/                # Example configurations and code
│   └── *.json              # Example config files
│
├── tmp/                     # Temporary/experimental files
│   └── *_test.py           # Development test scripts
│
├── kuzu-memories/          # Project memory storage (git-tracked)
│
├── .claude-mpm/            # Claude/MCP configuration
│   ├── mcp_config.json
│   └── claude_code_config.json
│
├── README.md               # Main README
├── CLAUDE.md              # Claude AI instructions
├── pyproject.toml         # Package configuration
├── Makefile               # Build automation
├── setup.py               # Package setup
├── requirements.txt       # Dependencies
├── requirements-dev.txt   # Dev dependencies
└── pytest.ini             # Test configuration
```

## Files Moved During Cleanup

### Documentation → `docs/`
- All markdown documentation files except README.md and CLAUDE.md
- Memory system documentation from old Memory/ directory

### Tests → `tests/`
- 11 test files (test_*.py)
- Keeps tests separate from source code

### Scripts → `scripts/`
- Installation and verification utilities
- Shell wrapper scripts
- Publishing tools

### Temporary Files → `tmp/`
- Debug and experimental scripts
- One-off test files
- Development utilities

### Examples → `examples/`
- Example configuration files
- Sample code snippets

### Configuration → `.claude-mpm/`
- Claude and MCP configuration files
- Keep AI-specific configs together

## Benefits of This Structure

1. **Clean Separation**: Source, tests, docs, and scripts are clearly separated
2. **Python Standards**: Follows PEP 517/518 packaging standards
3. **Git-Friendly**: Only essential files in root, reducing clutter
4. **Tool Compatibility**: Works well with pytest, pip, setuptools, etc.
5. **Developer Experience**: Easy to navigate and understand project layout
6. **CI/CD Ready**: Standard structure for automated workflows

## Essential Root Files

Files that should remain in the project root:
- `README.md` - Project introduction
- `CLAUDE.md` - AI assistant instructions
- `pyproject.toml` - Modern Python project configuration
- `setup.py` - Package setup (for compatibility)
- `Makefile` - Build automation
- `requirements*.txt` - Dependency specifications
- `pytest.ini` - Test runner configuration
- `.gitignore` - Git ignore rules
- `.pre-commit-config.yaml` - Pre-commit hooks

## Directory Purposes

- **src/kuzu_memory/**: Core package code only
- **tests/**: All test code, mirrors src structure
- **docs/**: All documentation and guides
- **scripts/**: Standalone utilities and tools
- **examples/**: Example usage and configurations
- **tmp/**: Temporary work, not committed to git
- **kuzu-memories/**: Runtime data storage (project memories)
- **.claude-mpm/**: AI/Claude specific configurations