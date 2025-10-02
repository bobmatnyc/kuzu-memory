# Claude Setup Guide

**Complete integration guide for KuzuMemory with Claude Desktop and Claude Code**

> **Replaces**: This document consolidates and replaces:
> - `docs/CLAUDE_CODE_SETUP.md`
> - `docs/CLAUDE_DESKTOP_SETUP.md`
> - `docs/CLAUDE_HOOKS.md`
> - `docs/CLAUDE_INTEGRATION.md`

---

## 🎯 Quick Start (ONE PATH Principle)

### Choose Your Integration Path

**Claude Desktop Users** (MCP Server - Recommended):
```bash
# List available installation methods
kuzu-memory list-installers

# Install Claude Desktop (auto-detects pipx or home directory)
kuzu-memory install claude-desktop

# Verify installation
kuzu-memory install-status
```

**Claude Code Users** (IDE Integration):
```bash
# Initialize project and install integration
kuzu-memory init
kuzu-memory install claude-code

# Verify installation
kuzu-memory install-status
```

---

> **📢 ONE PATH Principle**: There is now a single command for each AI system:
> - `claude-desktop` - Auto-detects best installation method (pipx or home)
> - `claude-code` - Claude Code IDE integration
>
> **Migration Note**: Old installer names (`claude-desktop-pipx`, `claude-desktop-home`,
> `claude`, `claude-mpm`) still work but show deprecation warnings.
>
> **Script Migration**: If you previously used `python scripts/install-claude-desktop.py`,
> that method still works but is **deprecated**. Use `kuzu-memory install claude-desktop` instead.

---

## 🔴 Claude Desktop Setup (MCP Server)

### Prerequisites

1. **KuzuMemory Installation**: v1.1.0+ via pipx
   ```bash
   pipx install kuzu-memory
   # Or upgrade if already installed
   pipx upgrade kuzu-memory
   ```

2. **Claude Desktop**: Installed on your system

### Automatic Installation (Recommended - ONE PATH)

```bash
# Install KuzuMemory via pipx if not already installed
pipx install kuzu-memory

# Install Claude Desktop integration (auto-detects best method)
kuzu-memory install claude-desktop
```

The installer **automatically detects** the best installation method:
- If `pipx` is available: Uses pipx installation
- Otherwise: Uses home directory installation

#### Installation Options

All installer commands support these options:

- `--force`: Force reinstall even if already installed
- `--dry-run`: Preview changes without modifying files
- `--verbose`: Show detailed installation steps
- `--mode [auto|pipx|home]`: Override auto-detection (claude-desktop only)
- `--backup-dir PATH`: Custom backup directory
- `--memory-db PATH`: Custom memory database location

#### Examples

```bash
# Install with auto-detection (recommended - ONE PATH)
kuzu-memory install claude-desktop

# Preview what would be changed (dry run)
kuzu-memory install claude-desktop --dry-run --verbose

# Override auto-detection to use specific method
kuzu-memory install claude-desktop --mode pipx
kuzu-memory install claude-desktop --mode home

# Install with custom database path
kuzu-memory install claude-desktop \
  --mode home \
  --memory-db ~/my-memories/db

# Force reinstall
kuzu-memory install claude-desktop --force

# Check installation status
kuzu-memory install-status

# Uninstall Claude Desktop integration
kuzu-memory uninstall claude-desktop
```

### Manual Installation

If you prefer to configure Claude Desktop manually:

#### 1. Locate Configuration File

The Claude Desktop configuration file location varies by platform:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### 2. Edit Configuration

Add or update the `mcpServers` section in the configuration file:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp", "serve"],
      "env": {
        "KUZU_MEMORY_DB": "~/.kuzu-memory/memorydb",
        "KUZU_MEMORY_MODE": "mcp"
      }
    }
  }
}
```

For pipx installations, you may need to use the full path:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "/Users/yourusername/.local/pipx/venvs/kuzu-memory/bin/python",
      "args": ["-m", "kuzu_memory.mcp.run_server"],
      "env": {
        "KUZU_MEMORY_DB": "/Users/yourusername/.kuzu-memory/memorydb",
        "KUZU_MEMORY_MODE": "mcp"
      }
    }
  }
}
```

#### 3. Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the new MCP server.

### Available MCP Tools

Once configured, the following tools will be available in Claude Desktop:

#### kuzu_enhance
Enhance prompts with project-specific context from KuzuMemory.
- **Parameters**:
  - `prompt` (required): The prompt to enhance
  - `max_memories` (optional): Maximum number of memories to include (default: 5)

#### kuzu_learn
Store learnings or observations asynchronously (non-blocking).
- **Parameters**:
  - `content` (required): The content to learn and store
  - `source` (optional): Source of the learning (default: "ai-conversation")
- **Note**: Uses 5-second default wait behavior for async processing

#### kuzu_recall
Query specific memories from the project.
- **Parameters**:
  - `query` (required): The query to search memories
  - `limit` (optional): Maximum number of results (default: 5)

#### kuzu_remember
Store important project information.
- **Parameters**:
  - `content` (required): The content to remember
  - `memory_type` (optional): Type of memory (identity/preference/decision/pattern, default: "identity")

#### kuzu_stats
Get KuzuMemory statistics and status.
- **Parameters**:
  - `detailed` (optional): Show detailed statistics (default: false)

---

## 🟡 Claude Code Setup (IDE Integration)

### Installation Method (ONE PATH)

```bash
# Initialize your project first
cd your-project
kuzu-memory init

# Install Claude Code integration (ONE command)
kuzu-memory install claude-code

# Verify installation
kuzu-memory install-status
```

#### Installation Options

```bash
# Install with options
kuzu-memory install claude-code --force --verbose

# Preview changes first
kuzu-memory install claude-code --dry-run

# Custom configuration
kuzu-memory install claude-code \
  --memory-db ~/my-project/memories \
  --backup-dir ~/backups
```

> **Note**: Previous commands (`kuzu-memory claude install`, `kuzu-memory install claude`)
> still work but show deprecation warnings. Use `kuzu-memory install claude-code` instead.

### What Gets Installed

1. **MCP Server Configuration** - Enables KuzuMemory tools in Claude Code
2. **Project CLAUDE.md** - Project-specific context and guidelines
3. **Shell Wrappers** - Compatibility scripts for cross-platform support
4. **Auto-Enhancement Hooks** - Automatic context injection for all queries

### Platform Support

#### macOS
- **Config Location**: `~/Library/Application Support/Claude/`
- **Full MCP Support**: ✅
- **Auto-Detection**: ✅

#### Windows
- **Config Location**: `%APPDATA%\Claude\`
- **Full MCP Support**: ✅
- **Auto-Detection**: ✅ (through WSL/Git Bash)

#### Linux
- **Config Location**: `~/.config/claude/`
- **Full MCP Support**: ✅
- **Auto-Detection**: ✅

### File Structure

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

### How It Works

#### 1. Automatic Context Enhancement

When you ask Claude a question, KuzuMemory automatically:
- Searches relevant project memories
- Enhances your prompt with context
- Returns the enriched response

#### 2. Asynchronous Learning

After each interaction:
- Important information is extracted
- Stored asynchronously (non-blocking)
- Available for future queries

#### 3. Project-Specific Memory

All memories are:
- Stored locally in your project
- Git-committable for team sharing
- Project-scoped (not user-scoped)

---

## 🟢 Testing Integration

### Check Installation Status

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

### Verify Claude Desktop Integration

After installation, you can verify the integration is working:

1. Open Claude Desktop
2. Start a new conversation
3. The MCP tools should be available for use
4. Test with a simple command like asking Claude to use `kuzu_stats` to check the memory system

---

## 🔧 Configuration

### MCP Server Configuration

The installer automatically configures Claude Desktop with:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["claude", "mcp-server"],
      "env": {
        "KUZU_MEMORY_PROJECT": "${workspaceFolder}"
      }
    }
  }
}
```

### Project Configuration

Customize memory behavior in `kuzu-config.json`:

```json
{
  "performance": {
    "max_recall_time_ms": 100,
    "max_generation_time_ms": 200
  },
  "memory": {
    "max_memories_per_project": 10000,
    "enable_auto_cleanup": true
  },
  "learning": {
    "min_content_length": 50,
    "excluded_patterns": ["password", "secret", "key"]
  }
}
```

### Environment Variables

The MCP server respects the following environment variables:

- `KUZU_MEMORY_DB`: Path to the memory database (default: `~/.kuzu-memory/memorydb`)
- `KUZU_MEMORY_MODE`: Operating mode (should be set to "mcp")
- `KUZU_MEMORY_PROJECT`: Project root directory (auto-detected if not set)
- `KUZU_MEMORY_ASYNC_TIMEOUT`: Async operation timeout in seconds (default: 5)

### Custom MCP Server Configuration

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

---

## 🚨 Troubleshooting

### Claude Desktop Issues

#### KuzuMemory Not Found

If Claude Desktop cannot find kuzu-memory:

1. Verify installation:
   ```bash
   pipx list | grep kuzu-memory
   ```

2. Check the command path:
   ```bash
   which kuzu-memory
   ```

3. Update the configuration with the full path

#### MCP Server Not Starting

1. Check Claude Desktop logs for errors
2. Validate the installation:
   ```bash
   python scripts/install-claude-desktop.py --validate
   ```

3. Test the MCP server directly:
   ```bash
   kuzu-memory mcp serve
   ```

#### Permission Issues

Ensure the configuration file and directories have proper permissions:

```bash
# macOS/Linux
chmod 644 ~/Library/Application\ Support/Claude/claude_desktop_config.json
chmod 755 ~/.kuzu-memory
```

#### Async Learning Issues

If async learning (`kuzu_learn`) appears to hang or take too long:

1. **Normal Behavior**: The tool waits up to 5 seconds for processing by default
2. **Check Status**: Use `kuzu_stats` to verify memories are being stored
3. **Adjust Timeout**: Set `KUZU_MEMORY_ASYNC_TIMEOUT` environment variable:
   ```json
   "env": {
     "KUZU_MEMORY_DB": "~/.kuzu-memory/memorydb",
     "KUZU_MEMORY_MODE": "mcp",
     "KUZU_MEMORY_ASYNC_TIMEOUT": "3"
   }
   ```

### Claude Code Issues

#### Claude Code Not Detected

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

---

## ⚪ Advanced Topics

### Customization

#### Project-Specific CLAUDE.md

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

### Backup and Recovery

The installer automatically creates backups of your configuration before making changes:

- Backups are stored in: `~/.kuzu-memory-backups/`
- Named with timestamp: `claude_desktop_config.json.backup_YYYYMMDD_HHMMSS`

To restore a backup:

```bash
cp ~/.kuzu-memory-backups/claude_desktop_config.json.backup_[timestamp] \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Uninstalling

#### Uninstall Claude Desktop Integration

```bash
python scripts/install-claude-desktop.py --uninstall
```

Or manually remove the "kuzu-memory" entry from the `mcpServers` section in your Claude Desktop configuration file.

#### Uninstall Claude Code Integration

```bash
# Remove Claude integration
kuzu-memory claude uninstall

# Or using the script
./install-claude-hooks.sh --uninstall
```

### Team Collaboration

#### Sharing Memories

```bash
# Commit memories to git
git add kuzu-memories/ CLAUDE.md .claude-mpm/
git commit -m "Update project memories and Claude configuration"
git push
```

#### Team Member Setup

```bash
# After cloning
git pull
kuzu-memory claude install

# Memories are already available!
kuzu-memory stats
```

---

## 📊 Performance

KuzuMemory MCP integration provides:
- **<100ms response time** for context retrieval
- **Async learning** that doesn't block conversations
- **Project-specific memory** that's git-committed
- **Zero-config operation** with sensible defaults

Performance Metrics:

| Operation | Target | Actual |
|-----------|--------|--------|
| Prompt Enhancement | <100ms | ~50ms |
| Memory Learning | Async | Non-blocking |
| Memory Recall | <100ms | ~40ms |
| Database Query | <50ms | ~20ms |

---

## 🔒 Security

- **Local-first**: All memories stored locally in your project
- **No external APIs**: No data sent to external services
- **Respects .gitignore**: Sensitive files not indexed
- **Credential filtering**: Never stores passwords/keys
- **Project isolation**: Memories scoped per project

---

## 🆘 Support

For issues or questions:

1. Check the [troubleshooting section](#troubleshooting)
2. Run validation: `python scripts/install-claude-desktop.py --validate --verbose`
3. Check the [project issues](https://github.com/yourusername/kuzu-memory/issues)
4. Review the [MCP documentation](https://github.com/anthropics/mcp)

**Documentation**: [docs/](docs/)
**Issues**: [GitHub Issues](https://github.com/yourusername/kuzu-memory/issues)

---

**KuzuMemory + Claude = Smarter AI Conversations** 🧠🤖✨
