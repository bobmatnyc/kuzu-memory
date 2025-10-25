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

**Claude Desktop Users** (Global Memory - Recommended for Personal Use):
```bash
# List available installation methods
kuzu-memory install list

# Install Claude Desktop (auto-detects pipx or home directory)
# Creates ~/.kuzu-memory/config.yaml and global database
kuzu-memory install add claude-desktop

# Verify installation
kuzu-memory install status
```

**Claude Code Users** (Project-Specific Memory - Recommended for Teams):
```bash
# Initialize project and install integration
# Creates .kuzu-memory/config.yaml and project database
kuzu-memory install add claude-code

# Verify installation
kuzu-memory install status
```

---

> **📢 ONE PATH Principle**: There is now a single command for each AI system:
> - `claude-desktop` - Global memory across all conversations (auto-detects pipx or home)
> - `claude-code` - Project-specific isolated memory
>
> **Migration Note**: Old installer names (`claude-desktop-pipx`, `claude-desktop-home`,
> `claude`, `claude-mpm`) still work but show deprecation warnings.
>
> **Script Migration**: If you previously used `python scripts/install-claude-desktop.py`,
> that method still works but is **deprecated**. Use `kuzu-memory install add claude-desktop` instead.

---

## 🔑 Key Differences: Project vs Global Memory

### Claude Code (`claude-code`) - Project-Specific
- **Configuration**: `.kuzu-memory/config.yaml` in project directory
- **Database**: `.kuzu-memory/memorydb/` (project-local)
- **Memory Scope**: Isolated per-project, each project has separate memories
- **MCP Hooks**: Use project-specific database automatically
- **Use Cases**:
  - Team collaboration (commit memories to git)
  - Project-specific coding patterns and decisions
  - Client-specific requirements and context
  - Multiple projects with different contexts
- **Sharing**: Configuration and memories can be committed to version control
- **Initialization**: Automatic during installation

### Claude Desktop (`claude-desktop`) - Global
- **Configuration**: `~/.kuzu-memory/config.yaml` in home directory
- **Database**: `~/.kuzu-memory/memorydb/` (user-global)
- **Memory Scope**: Shared across all Claude Desktop conversations
- **Installation**: Auto-detects pipx or home directory installation method
- **Use Cases**:
  - Personal knowledge base and learnings
  - User preferences and conventions
  - Cross-project insights
  - General-purpose AI assistant
- **Sharing**: Personal, not version controlled
- **Initialization**: Automatic during installation

### Configuration Behavior

**Automatic Creation**:
- Configuration files (`config.yaml`) are created automatically during installation
- Database is initialized automatically on first install
- No manual configuration required to get started

**Preservation**:
- Existing configurations are preserved by default
- Use `--force` flag to overwrite existing configurations
- Automatic backups created before overwriting

**Customization**:
- Edit `config.yaml` after installation to customize behavior
- Specify custom paths with `--memory-db` flag
- Override defaults with environment variables

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
# This automatically:
# - Creates ~/.kuzu-memory/config.yaml configuration file
# - Initializes global database in ~/.kuzu-memory/memorydb/
# - Configures Claude Desktop MCP server
# - Creates backup of existing configuration
kuzu-memory install add claude-desktop
```

The installer **automatically**:
1. **Detects installation method**: Uses pipx if available, otherwise home directory
2. **Creates configuration**: Generates `~/.kuzu-memory/config.yaml` with sensible defaults
3. **Initializes database**: Sets up global memory database in `~/.kuzu-memory/memorydb/`
4. **Configures MCP**: Updates Claude Desktop's `claude_desktop_config.json`
5. **Preserves existing**: Backs up any existing configuration before changes

#### Installation Options

All installer commands support these options:

- `--force`: Force reinstall and overwrite existing configuration (creates backup)
- `--dry-run`: Preview changes without modifying files
- `--verbose`: Show detailed installation steps
- `--mode [auto|pipx|home]`: Override auto-detection (claude-desktop only)
- `--backup-dir PATH`: Custom backup directory (default: `~/.kuzu-memory-backups/`)
- `--memory-db PATH`: Custom memory database location (default: `~/.kuzu-memory/memorydb/`)

#### Examples

```bash
# Install with auto-detection (recommended - ONE PATH)
# Creates config and initializes database automatically
kuzu-memory install add claude-desktop

# Preview what would be changed (dry run)
kuzu-memory install add claude-desktop --dry-run --verbose

# Override auto-detection to use specific method
kuzu-memory install add claude-desktop --mode pipx
kuzu-memory install add claude-desktop --mode home

# Install with custom database path
# Still creates config.yaml automatically with custom path
kuzu-memory install add claude-desktop \
  --mode home \
  --memory-db ~/my-memories/db

# Force reinstall (overwrites existing config, creates backup)
kuzu-memory install add claude-desktop --force

# Check installation status
kuzu-memory install status

# Uninstall Claude Desktop integration
kuzu-memory install remove claude-desktop
```

#### What Gets Created

After installation, you'll have:

```
~/.kuzu-memory/
├── config.yaml              # Configuration file (auto-created)
├── memorydb/                # Global memory database (auto-initialized)
│   ├── kuzu_memory.db       # Main database file
│   └── ... (other db files)
└── logs/                    # Optional: log files

~/.kuzu-memory-backups/      # Backup directory
└── config.yaml.backup_[timestamp]  # Backup of previous config (if any)

~/Library/Application Support/Claude/  # macOS
└── claude_desktop_config.json         # Updated MCP configuration
```

You can edit `~/.kuzu-memory/config.yaml` after installation to customize behavior.

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
# Navigate to your project directory
cd your-project

# Install Claude Code integration (ONE command)
# This automatically:
# - Creates .kuzu-memory/config.yaml in project directory
# - Initializes project database in .kuzu-memory/memorydb/
# - Configures MCP hooks for Claude Code
# - Creates project-specific CLAUDE.md context file
kuzu-memory install add claude-code

# Verify installation
kuzu-memory install status
```

The installer **automatically**:
1. **Creates project configuration**: Generates `.kuzu-memory/config.yaml` in project root
2. **Initializes project database**: Sets up isolated database in `.kuzu-memory/memorydb/`
3. **Configures MCP hooks**: Enables KuzuMemory tools in Claude Code
4. **Creates CLAUDE.md**: Project-specific context file for Claude
5. **Preserves existing**: Backs up any existing configuration before changes

#### Installation Options

```bash
# Install with auto-configuration (recommended - ONE PATH)
kuzu-memory install add claude-code

# Install with options
kuzu-memory install add claude-code --force --verbose

# Preview changes first
kuzu-memory install add claude-code --dry-run

# Custom configuration
kuzu-memory install add claude-code \
  --memory-db ./custom-memories \
  --backup-dir ./backups
```

> **Note**: Previous commands (`kuzu-memory claude install`, `kuzu-memory install claude`)
> still work but show deprecation warnings. Use `kuzu-memory install add claude-code` instead.

#### What Gets Created

After installation, your project will have:

```
your-project/
├── .kuzu-memory/
│   ├── config.yaml              # Project configuration (auto-created)
│   ├── memorydb/                # Project database (auto-initialized)
│   │   ├── kuzu_memory.db       # Main database file
│   │   └── ... (other db files)
│   └── logs/                    # Optional: log files
├── CLAUDE.md                     # Project context for Claude (auto-created)
├── .claude-mpm/
│   └── config.json              # MPM configuration
└── .claude/
    ├── kuzu-memory-mcp.json     # Local MCP config
    └── kuzu-memory.sh           # Shell wrapper
```

All files can be committed to git for team collaboration.

### What Gets Installed

1. **Project Configuration** - `.kuzu-memory/config.yaml` with project-specific settings
2. **Project Database** - `.kuzu-memory/memorydb/` isolated from other projects
3. **MCP Server Configuration** - Enables KuzuMemory tools in Claude Code
4. **Project CLAUDE.md** - Project-specific context and guidelines
5. **Shell Wrappers** - Compatibility scripts for cross-platform support
6. **Auto-Enhancement Hooks** - Automatic context injection using Claude Code hooks (see Hook System section below)

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

### How It Works

#### 1. Project Isolation

Each project has completely isolated memory:
- **Configuration**: `.kuzu-memory/config.yaml` specific to this project
- **Database**: `.kuzu-memory/memorydb/` separate from other projects
- **No Cross-Talk**: Memories from Project A never appear in Project B
- **Independent Settings**: Each project can have different configurations

#### 2. Automatic Context Enhancement

When you ask Claude a question in this project:
- Searches only this project's memories
- Enhances your prompt with project-specific context
- Returns responses based on project conventions

#### 3. Asynchronous Learning

After each interaction in this project:
- Important information is extracted
- Stored asynchronously (non-blocking) in project database
- Available for future queries in this project only

#### 4. Team Collaboration

All memories are:
- Stored locally in `.kuzu-memory/` directory
- Git-committable for team sharing
- Project-scoped (shared across team, isolated from other projects)
- Version-controlled with your codebase

**Example Workflow**:
```bash
# Developer A creates memories
cd my-project
kuzu-memory install add claude-code
# ... work with Claude, memories are created ...
git add .kuzu-memory/ CLAUDE.md
git commit -m "Add project memories"
git push

# Developer B gets memories
git pull
# Memories are automatically available!
kuzu-memory status  # See shared memories
```

---

## 🔗 Claude Code Hook System

### Overview

KuzuMemory integrates with Claude Code using hooks that automatically enhance your prompts and learn from conversations. The hook system uses correct Claude Code event names and has been tested and verified.

### Hook Events

The installation configures two hooks with correct event names:

#### UserPromptSubmit Hook (Prompt Enhancement)
- **Event Name**: `UserPromptSubmit` (camelCase, not snake_case)
- **When It Fires**: When you submit a prompt to Claude
- **What It Does**: Enhances your prompt with relevant project memories
- **Command**: `kuzu-memory memory enhance "{{prompt}}"`
- **Performance**: 350-450ms (acceptable for CLI)
- **Template Variable**: `{{prompt}}` - Your input text

#### Stop Hook (Conversation Learning)
- **Event Name**: `Stop` (not `assistant_response`)
- **When It Fires**: When Claude finishes responding
- **What It Does**: Stores learnings from the conversation asynchronously
- **Command**: `kuzu-memory memory learn "{{response}}" --quiet`
- **Performance**: ~400ms, non-blocking
- **Template Variable**: `{{response}}` - Claude's response text

### Hook Configuration Example

After installation, your `.claude/config.local.json` will contain:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "handler": "kuzu_memory_enhance",
      "command": "/path/to/kuzu-memory memory enhance \"{{prompt}}\"",
      "enabled": true
    }],
    "Stop": [{
      "handler": "kuzu_memory_learn",
      "command": "/path/to/kuzu-memory memory learn \"{{response}}\" --quiet",
      "enabled": true
    }]
  }
}
```

### Performance Expectations

Based on testing with v1.3.3:

| Operation | Performance | Status |
|-----------|-------------|--------|
| CLI Enhance Command | 350-450ms | ✅ Acceptable |
| CLI Learn Command | ~400ms | ✅ Acceptable |
| Core DB Recall | <100ms | ✅ As designed |
| Core DB Generation | <200ms | ✅ As designed |
| Async Learning Queue | <200ms | ✅ Non-blocking |

**Note**: CLI commands have overhead from process startup (~300ms), but core database operations are <100ms as designed. This is expected and acceptable for hook-based integration.

### Available Claude Code Hook Events

For reference, here are all valid Claude Code hook events:

- **UserPromptSubmit** - User submits a prompt (used for enhancement)
- **Stop** - Claude finishes responding (used for learning)
- **PreToolUse** - Before tool execution
- **PostToolUse** - After tool execution
- **SubagentStop** - Subagent finishes
- **Notification** - Notification events
- **SessionStart** - Session begins
- **SessionEnd** - Session ends
- **PreCompact** - Before context compaction

KuzuMemory uses `UserPromptSubmit` and `Stop` for optimal integration.

### Testing Hooks

#### Manual Testing

Test the commands that hooks will execute:

```bash
# Test enhance command (UserPromptSubmit)
kuzu-memory memory enhance "How do I optimize database queries?"

# Test learn command (Stop)
kuzu-memory memory learn "Testing hook system" --quiet

# Verify memories were created
kuzu-memory memory recent
```

#### Verify Hook Configuration

```bash
# Check installation status
kuzu-memory install status

# Validate hook configuration
python3 -m json.tool .claude/config.local.json

# Look for UserPromptSubmit and Stop events
cat .claude/config.local.json | grep -A 5 "UserPromptSubmit"
cat .claude/config.local.json | grep -A 5 "Stop"
```

#### In Claude Code

1. **Open Claude Code** in your project
2. **Start a conversation**: "What are the main features of this project?"
3. **Observe**: Prompt should be enhanced automatically (UserPromptSubmit hook)
4. **After response**: Check `kuzu-memory memory recent` to see if conversation was learned (Stop hook)

### Troubleshooting Hooks

#### Hooks Not Firing

If hooks don't seem to be working:

1. **Check event names** - Must be `UserPromptSubmit` and `Stop` (camelCase)
   ```bash
   cat .claude/config.local.json | grep -E "UserPromptSubmit|Stop"
   ```

2. **Verify command path** - Binary must exist and be executable
   ```bash
   which kuzu-memory
   ls -la $(which kuzu-memory)
   ```

3. **Test commands manually**
   ```bash
   kuzu-memory memory enhance "test"
   kuzu-memory memory learn "test" --quiet
   ```

4. **Check for old event names** - Old configs may have incorrect names
   ```bash
   # Should return nothing (these are wrong)
   cat .claude/config.local.json | grep -E "user_prompt_submit|assistant_response"
   ```

5. **Reinstall if needed**
   ```bash
   kuzu-memory install add claude-code --force
   ```

#### Performance Issues

If hooks are slow:

```bash
# Check database health
kuzu-memory status --detailed

# Monitor command performance
time kuzu-memory memory enhance "test prompt"
time kuzu-memory memory learn "test content" --quiet
```

Expected times:
- Enhance: 350-450ms (includes CLI startup)
- Learn: ~400ms (async, non-blocking)

#### Old Configuration Migration

If you have an old configuration with incorrect event names:

```bash
# Backup old config
cp .claude/config.local.json .claude/config.local.json.backup

# Reinstall with correct event names
kuzu-memory install add claude-code --force

# Verify new config uses correct names
cat .claude/config.local.json | grep -E "UserPromptSubmit|Stop"
```

### Hook Best Practices

1. **Keep hooks enabled** - They enhance every conversation automatically
2. **Monitor performance** - Hooks should complete quickly (<1 second)
3. **Check logs** - Use Claude Code developer console for debugging
4. **Test after updates** - Verify hooks still work after upgrading
5. **Commit configurations** - Share `.claude/config.local.json` with team

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
kuzu-memory memory enhance "test prompt"
kuzu-memory status
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

### Understanding Configuration Files

KuzuMemory uses different configuration files depending on the integration:

#### Claude Desktop (Global Configuration)
- **Location**: `~/.kuzu-memory/config.yaml`
- **Created By**: `kuzu-memory install add claude-desktop`
- **Scope**: All Claude Desktop conversations
- **Database**: `~/.kuzu-memory/memorydb/`

#### Claude Code (Project Configuration)
- **Location**: `.kuzu-memory/config.yaml` (in project root)
- **Created By**: `kuzu-memory install add claude-code`
- **Scope**: This project only
- **Database**: `.kuzu-memory/memorydb/` (in project)

### Configuration File Structure

Both installers create a `config.yaml` with sensible defaults:

```yaml
version: 1.0

# Database settings
storage:
  database_path: "./memorydb"  # Relative to config location
  max_size_mb: 50
  auto_compact: true

# Memory recall settings
recall:
  max_memories: 10
  strategies:
    - keyword
    - entity
    - temporal

# Learning patterns
patterns:
  custom_identity: "I am (.*?)(?:\\.|$)"
  custom_preference: "I always (.*?)(?:\\.|$)"

# Performance thresholds
performance:
  max_recall_time_ms: 100
  max_generation_time_ms: 200

# Content filtering
learning:
  min_content_length: 50
  excluded_patterns: ["password", "secret", "key", "token"]
```

### Customizing Configuration

After installation, you can edit the `config.yaml` file:

**For Claude Desktop** (global):
```bash
# Edit global configuration
vim ~/.kuzu-memory/config.yaml
```

**For Claude Code** (project-specific):
```bash
# Edit project configuration
vim .kuzu-memory/config.yaml
```

### MCP Server Configuration

The installer automatically configures Claude Desktop with:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/claude/claude_desktop_config.json`

**Claude Desktop** (global memory):
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

**Claude Code** (project-specific memory):
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp", "serve"],
      "env": {
        "KUZU_MEMORY_DB": "${workspaceFolder}/.kuzu-memory/memorydb",
        "KUZU_MEMORY_MODE": "mcp",
        "KUZU_MEMORY_PROJECT": "${workspaceFolder}"
      }
    }
  }
}
```

### Environment Variables

The MCP server respects the following environment variables:

- `KUZU_MEMORY_DB`: Path to the memory database
  - Claude Desktop: `~/.kuzu-memory/memorydb` (global)
  - Claude Code: `.kuzu-memory/memorydb` (project-specific)
- `KUZU_MEMORY_MODE`: Operating mode (should be set to "mcp")
- `KUZU_MEMORY_PROJECT`: Project root directory (for Claude Code)
- `KUZU_MEMORY_ASYNC_TIMEOUT`: Async operation timeout in seconds (default: 5)

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

#### Hooks Not Firing

See the detailed "Troubleshooting Hooks" section in the Hook System chapter above. Quick checklist:

1. **Verify event names** are `UserPromptSubmit` and `Stop` (not snake_case)
2. **Check binary path** exists: `which kuzu-memory`
3. **Test commands manually**:
   ```bash
   kuzu-memory memory enhance "test"
   kuzu-memory memory learn "test" --quiet
   ```
4. **Reinstall hooks**: `kuzu-memory install add claude-code --force`

#### Hooks Using Wrong Event Names

If you have an old configuration with `user_prompt_submit` or `assistant_response`:

```bash
# These event names are INCORRECT and won't work:
# ❌ user_prompt_submit (should be UserPromptSubmit)
# ❌ assistant_response (should be Stop)

# Fix by reinstalling:
kuzu-memory install add claude-code --force

# Verify correct names:
cat .claude/config.local.json | grep -E "UserPromptSubmit|Stop"
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
kuzu-memory status
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
