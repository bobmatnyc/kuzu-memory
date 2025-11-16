# Contributing to KuzuMemory

We welcome contributions to KuzuMemory! This guide will help you get started with development, testing, and submitting pull requests.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (required for type hints and performance)
- **Git** for version control
- **pipx** (recommended) or pip for package installation

### Development Setup

```bash
# Clone the repository
git clone https://github.com/kuzu-memory/kuzu-memory
cd kuzu-memory

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Verify installation
kuzu-memory --version
pytest --version
```

### Optional: Kuzu CLI Installation

For 2-3x performance boost (recommended but not required):

```bash
# macOS
brew install kuzu

# Linux
curl -L https://github.com/kuzudb/kuzu/releases/download/v0.0.10/kuzu-linux-x86_64.tar.gz | tar xz
sudo mv kuzu /usr/local/bin/

# Verify
kuzu --version
```

## 🏗️ Project Structure

```
kuzu-memory/
├── src/kuzu_memory/          # Main package
│   ├── cli/                  # CLI commands and interface
│   ├── core/                 # Core memory engine
│   ├── storage/              # Database adapters
│   ├── recall/               # Memory recall strategies
│   ├── extraction/           # Pattern and entity extraction
│   ├── integrations/         # AI system integrations
│   └── mcp/                  # MCP server implementation
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── mcp/                  # MCP server tests (151+ tests)
│   └── performance/          # Performance benchmarks
├── docs/                     # Documentation
│   ├── developer/            # Developer guides
│   └── user/                 # User documentation
└── .claude/                  # Claude Code integration
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests
pytest tests/mcp/            # MCP server tests (151+ tests)

# Run with coverage
pytest --cov=kuzu_memory --cov-report=html

# Run benchmarks
pytest tests/ -m benchmark

# Run specific test file
pytest tests/unit/test_memory.py -v
```

### Test Requirements

All contributions should include tests:

- **Unit tests** for new functions/classes
- **Integration tests** for multi-component features
- **Performance tests** for optimization changes
- **Documentation** for new features

### Test Coverage Standards

- Maintain **>80% overall coverage**
- New code should have **>90% coverage**
- Critical paths require **100% coverage**

## 🎯 Code Style Guidelines

### Formatting Standards

We use **Black** for code formatting and **Ruff** for linting:

```bash
# Format code
black src/ tests/

# Run linter
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/
```

### Style Requirements

- **Line length**: 88 characters (Black default)
- **Type hints**: Required for all public methods
- **Docstrings**: Required for all public APIs
- **Error handling**: Use custom exceptions
- **Imports**: Organized and sorted

### Code Quality Checklist

Before submitting a PR:

- [ ] Code is Black-formatted (88 characters)
- [ ] All Ruff checks pass
- [ ] Type hints on all public methods
- [ ] Comprehensive docstrings with examples
- [ ] Error handling with custom exceptions
- [ ] Performance considerations documented
- [ ] Tests included and passing
- [ ] Documentation updated

## 📝 Documentation Standards

### Docstring Format

Use Google-style docstrings with examples:

```python
def attach_memories(self, prompt: str, max_memories: int = 10) -> MemoryContext:
    """Enhance a prompt with relevant memories from the database.

    Args:
        prompt: The user prompt to enhance with context
        max_memories: Maximum number of memories to attach (default: 10)

    Returns:
        MemoryContext containing enhanced prompt and metadata

    Raises:
        DatabaseError: If database connection fails
        ValidationError: If prompt is empty or invalid

    Example:
        >>> memory = KuzuMemory()
        >>> context = memory.attach_memories("What's my coding preference?")
        >>> print(context.enhanced_prompt)
        # Output includes relevant memories about coding preferences
    """
```

### Documentation Updates

When adding features:

1. Update relevant documentation in `docs/`
2. Add examples to README.md if user-facing
3. Update CLI reference in `docs/developer/cli-reference.md`
4. Add troubleshooting section if needed

## 🔄 Pull Request Process

### Before Submitting

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation

3. **Run the test suite**
   ```bash
   pytest
   black src/ tests/
   ruff check src/ tests/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Use conventional commit messages:
   - `feat:` - New features
   - `fix:` - Bug fixes
   - `docs:` - Documentation changes
   - `test:` - Test additions/changes
   - `refactor:` - Code refactoring
   - `perf:` - Performance improvements
   - `chore:` - Maintenance tasks

### Submitting a Pull Request

1. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request**
   - Use a clear, descriptive title
   - Reference related issues
   - Describe what changed and why
   - Include screenshots for UI changes
   - List any breaking changes

3. **PR Review Process**
   - Automated tests will run
   - Code review by maintainers
   - Address feedback
   - Merge when approved

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Coverage maintained/improved

## Documentation
- [ ] README updated
- [ ] Docstrings added/updated
- [ ] Examples added

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
```

## 🐛 Reporting Bugs

### Before Reporting

1. **Search existing issues** to avoid duplicates
2. **Test with latest version** to ensure bug still exists
3. **Gather information** about your environment

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Run command `kuzu-memory ...`
2. See error

**Expected Behavior**
What you expected to happen

**Environment**
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.11.5]
- KuzuMemory version: [e.g., 1.4.47]
- Installation method: [pipx/pip]

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

We welcome feature requests! Please:

1. **Check existing issues** for similar requests
2. **Describe the use case** and problem you're solving
3. **Provide examples** of how it would work
4. **Consider alternatives** you've thought about

## 🔒 Security

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email security concerns to the maintainers
3. Provide detailed information about the vulnerability
4. Allow time for a fix before public disclosure

## 📜 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information
- Other unprofessional conduct

## 🏆 Recognition

Contributors are recognized in:

- Release notes for their contributions
- GitHub contributors page
- Special mentions for significant features

## 📚 Additional Resources

- [Developer Guide](docs/DEVELOPER.md) - Comprehensive development documentation
- [Code Structure](docs/CODE_STRUCTURE.md) - Architectural analysis
- [MCP Testing Guide](docs/MCP_TESTING_GUIDE.md) - MCP server testing

## 🤝 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bug Reports**: Open a GitHub Issue
- **Chat**: Join our community discussions
- **Documentation**: Check the docs/ directory

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to KuzuMemory!** 🎉

Your contributions help make KuzuMemory better for everyone.
