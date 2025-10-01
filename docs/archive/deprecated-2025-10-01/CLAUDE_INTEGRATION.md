# 🤖 Claude Code Integration Guide

Complete guide for integrating KuzuMemory with Claude Desktop and Claude Code using MCP (Model Context Protocol).

## 🚀 Quick Start

### One-Command Installation

```bash
# Install KuzuMemory with Claude hooks
kuzu-memory claude install
```

Or use the standalone script:

```bash
# Download and run the installer
curl -sSL https://raw.githubusercontent.com/yourusername/kuzu-memory/main/scripts/install-claude-hooks.sh | bash
```

## 📋 Features

### What Gets Installed

1. **MCP Server Configuration** - Enables KuzuMemory tools in Claude Desktop
2. **Project CLAUDE.md** - Project-specific context and guidelines
3. **Shell Wrappers** - Compatibility scripts for cross-platform support
4. **Auto-Enhancement Hooks** - Automatic context injection for all queries

### Available MCP Tools

When using Claude Desktop with KuzuMemory installed, you get these tools:

- `kuzu_enhance` - Enhance prompts with project context
- `kuzu_learn` - Store learnings asynchronously (non-blocking)
- `kuzu_recall` - Query specific memories
- `kuzu_remember` - Store important project information
- `kuzu_stats` - Get memory system statistics

## 🔧 Installation Methods

### Method 1: CLI Command (Recommended)

```bash
# Initialize your project first
cd your-project
kuzu-memory init

# Install Claude integration
kuzu-memory claude install

# Or use the interactive wizard
kuzu-memory claude wizard
```

### Method 2: Standalone Script

```bash
# Download the installer
curl -O https://raw.githubusercontent.com/yourusername/kuzu-memory/main/scripts/install-claude-hooks.sh
chmod +x install-claude-hooks.sh

# Run installation
./install-claude-hooks.sh

# Or force reinstall
./install-claude-hooks.sh --force
```

### Method 3: Generic Install Command

```bash
# Using the generic install command
kuzu-memory install claude
```

## 🖥️ Platform Support

### macOS
- **Config Location**: `~/Library/Application Support/Claude/`
- **Full MCP Support**: ✅
- **Auto-Detection**: ✅

### Windows
- **Config Location**: `%APPDATA%\Claude\`
- **Full MCP Support**: ✅
- **Auto-Detection**: ✅ (through WSL/Git Bash)

### Linux
- **Config Location**: `~/.config/claude/`
- **Full MCP Support**: ✅
- **Auto-Detection**: ✅

## 📁 File Structure

After installation, your project will have:

```
your-project/
├── CLAUDE.md                    # Project context for Claude
├── .claude-mpm/
│   └── config.json             # MPM configuration
├── .claude/
│   ├── kuzu-memory-mcp.json   # Local MCP config
│   └── kuzu-memory.sh         # Shell wrapper
└── kuzu-memories/
    └── kuzu_memory.db         # Memory database
```

## 🎯 How It Works

### 1. Automatic Context Enhancement

When you ask Claude a question, KuzuMemory automatically:
- Searches relevant project memories
- Enhances your prompt with context
- Returns the enriched response

### 2. Asynchronous Learning

After each interaction:
- Important information is extracted
- Stored asynchronously (non-blocking)
- Available for future queries

### 3. Project-Specific Memory

All memories are:
- Stored locally in your project
- Git-committable for team sharing
- Project-scoped (not user-scoped)

## 🧪 Testing Integration

### Check Status

```bash
# View installation status
kuzu-memory claude status

# JSON output for scripts
kuzu-memory claude status --json
```

### Run Tests

```bash
# Test the integration
kuzu-memory claude test

# Test specific components
kuzu-memory enhance "test prompt"
kuzu-memory stats
```

### Manual MCP Server Test

```bash
# Run MCP server manually (for debugging)
python -m kuzu_memory.integrations.mcp_server
```

## 🔄 Managing Installation

### Update Configuration

```bash
# Reinstall with latest settings
kuzu-memory claude install --force

# Regenerate CLAUDE.md
kuzu-memory claude install --force
```

### Uninstall

```bash
# Remove Claude integration
kuzu-memory claude uninstall

# Or using the script
./install-claude-hooks.sh --uninstall
```

## 🎨 Customization

### Project-Specific CLAUDE.md

Edit `CLAUDE.md` to include:
- Project architecture details
- Coding conventions
- API documentation
- Team preferences
- Technical decisions

Example:

```markdown
# Project Memory Configuration

## Architecture
- Microservices with FastAPI
- PostgreSQL for data storage
- Redis for caching

## Conventions
- Use async/await patterns
- Follow PEP 8 style guide
- Write comprehensive tests

## API Guidelines
- RESTful endpoints
- JWT authentication
- Versioned APIs (/v1, /v2)
```

### MCP Server Configuration

Customize `.claude/kuzu-memory-mcp.json`:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "python",
      "args": ["-m", "kuzu_memory.integrations.mcp_server"],
      "env": {
        "KUZU_MEMORY_PROJECT": "/path/to/project",
        "KUZU_MEMORY_MODE": "mcp"
      }
    }
  }
}
```

## 🚨 Troubleshooting

### Common Issues

#### Claude Desktop Not Detected

```bash
# Check detection manually
kuzu-memory claude status

# Create local config anyway
kuzu-memory claude install --force
```

#### MCP Server Not Working

```bash
# Check Python module
python -c "from kuzu_memory.integrations import mcp_server; print('OK')"

# Install MCP SDK if needed
pip install mcp
```

#### Permission Errors

```bash
# Fix permissions
chmod +x .claude/kuzu-memory.sh
chmod 644 .claude-mpm/config.json
```

### Debug Mode

```bash
# Enable debug output
kuzu-memory --debug claude install

# Verbose installation
./install-claude-hooks.sh --verbose
```

## 📚 Advanced Usage

### Programmatic Integration

```python
from kuzu_memory.installers import ClaudeHooksInstaller
from pathlib import Path

# Initialize installer
installer = ClaudeHooksInstaller(Path.cwd())

# Check status
status = installer.status()
if not status['installed']:
    # Install
    result = installer.install()
    print(f"Installation: {result.success}")
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Install KuzuMemory
  run: pip install kuzu-memory

- name: Setup Claude Integration
  run: |
    kuzu-memory init
    kuzu-memory claude install --force
```

### Docker Support

```dockerfile
FROM python:3.11

# Install KuzuMemory
RUN pip install kuzu-memory

# Setup project
WORKDIR /app
COPY . .

# Initialize with Claude hooks
RUN kuzu-memory init && \
    kuzu-memory claude install --force
```

## 🤝 Team Collaboration

### Sharing Memories

```bash
# Commit memories to git
git add kuzu-memories/ CLAUDE.md .claude-mpm/
git commit -m "Update project memories and Claude configuration"
git push
```

### Team Member Setup

```bash
# After cloning
git pull
kuzu-memory claude install

# Memories are already available!
kuzu-memory stats
```

## 📊 Performance

- **Context Retrieval**: <100ms
- **Async Learning**: Non-blocking
- **Memory Search**: Optimized with embeddings
- **Database**: Local Kuzu graph database
- **Caching**: LRU cache for frequent queries

## 🔮 Future Features

- [ ] Claude Desktop UI integration
- [ ] Memory visualization tools
- [ ] Team memory analytics
- [ ] Cross-project memory sharing
- [ ] Memory export/import

## 📖 Additional Resources

- [KuzuMemory Documentation](../README.md)
- [MCP Protocol Specification](https://modelcontextprotocol.org)
- [Claude Desktop Guide](https://claude.ai/desktop)
- [Project Examples](../examples/)

## 🆘 Support

- **GitHub Issues**: Report bugs and request features
- **Discord**: Join our community for help
- **Documentation**: Check `/docs` for detailed guides

---

*KuzuMemory + Claude = Smarter AI Interactions* 🧠✨