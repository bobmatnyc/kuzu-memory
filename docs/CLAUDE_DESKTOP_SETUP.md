# Claude Desktop MCP Integration Setup

This guide explains how to configure Claude Desktop to use KuzuMemory via the Model Context Protocol (MCP).

## Prerequisites

1. **KuzuMemory Installation**: Ensure KuzuMemory v1.1.0+ is installed via pipx:
   ```bash
   pipx install kuzu-memory
   # Or upgrade if already installed
   pipx upgrade kuzu-memory
   ```

2. **Claude Desktop**: Have Claude Desktop installed on your system

## Automatic Installation

The easiest way to set up the MCP integration is using the provided installer script:

```bash
# Clone the repository (if not already done)
git clone https://github.com/yourusername/kuzu-memory
cd kuzu-memory

# Run the installer
python scripts/install-claude-desktop.py
```

### Installer Options

- `--backup-dir PATH`: Custom backup directory (default: `~/.kuzu-memory-backups`)
- `--memory-db PATH`: Custom memory database path (default: `~/.kuzu-memory/memorydb`)
- `--force`: Force installation even if configuration exists
- `--uninstall`: Remove KuzuMemory from Claude Desktop configuration
- `--validate`: Validate the current installation
- `--dry-run`: Show what would be done without making changes
- `--verbose`: Enable verbose output

### Examples

```bash
# Install with default settings
python scripts/install-claude-desktop.py

# Install with custom memory database location
python scripts/install-claude-desktop.py --memory-db ~/my-memories/db

# Validate existing installation
python scripts/install-claude-desktop.py --validate

# Perform a dry run to see what would be changed
python scripts/install-claude-desktop.py --dry-run

# Uninstall KuzuMemory from Claude Desktop
python scripts/install-claude-desktop.py --uninstall
```

## Manual Installation

If you prefer to configure Claude Desktop manually:

### 1. Locate Configuration File

The Claude Desktop configuration file location varies by platform:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 2. Edit Configuration

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

### 3. Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the new MCP server.

## Available MCP Tools

Once configured, the following tools will be available in Claude Desktop:

### kuzu_enhance
Enhance prompts with project-specific context from KuzuMemory.
- **Parameters**:
  - `prompt` (required): The prompt to enhance
  - `max_memories` (optional): Maximum number of memories to include (default: 5)

### kuzu_learn
Store learnings or observations asynchronously (non-blocking).
- **Parameters**:
  - `content` (required): The content to learn and store
  - `source` (optional): Source of the learning (default: "ai-conversation")
- **Note**: Uses 5-second default wait behavior for async processing

### kuzu_recall
Query specific memories from the project.
- **Parameters**:
  - `query` (required): The query to search memories
  - `limit` (optional): Maximum number of results (default: 5)

### kuzu_remember
Store important project information.
- **Parameters**:
  - `content` (required): The content to remember
  - `memory_type` (optional): Type of memory (identity/preference/decision/pattern, default: "identity")

### kuzu_stats
Get KuzuMemory statistics and status.
- **Parameters**:
  - `detailed` (optional): Show detailed statistics (default: false)

## Troubleshooting

### KuzuMemory Not Found

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

### MCP Server Not Starting

1. Check Claude Desktop logs for errors
2. Validate the installation:
   ```bash
   python scripts/install-claude-desktop.py --validate
   ```

3. Test the MCP server directly:
   ```bash
   kuzu-memory mcp serve
   ```

### Permission Issues

Ensure the configuration file and directories have proper permissions:

```bash
# macOS/Linux
chmod 644 ~/Library/Application\ Support/Claude/claude_desktop_config.json
chmod 755 ~/.kuzu-memory
```

### Async Learning Issues

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

## Environment Variables

The MCP server respects the following environment variables:

- `KUZU_MEMORY_DB`: Path to the memory database (default: `~/.kuzu-memory/memorydb`)
- `KUZU_MEMORY_MODE`: Operating mode (should be set to "mcp")
- `KUZU_MEMORY_PROJECT`: Project root directory (auto-detected if not set)

## Verifying the Integration

After installation, you can verify the integration is working:

1. Open Claude Desktop
2. Start a new conversation
3. The MCP tools should be available for use
4. Test with a simple command like asking Claude to use `kuzu_stats` to check the memory system

## Backup and Recovery

The installer automatically creates backups of your configuration before making changes:

- Backups are stored in: `~/.kuzu-memory-backups/`
- Named with timestamp: `claude_desktop_config.json.backup_YYYYMMDD_HHMMSS`

To restore a backup:

```bash
cp ~/.kuzu-memory-backups/claude_desktop_config.json.backup_[timestamp] \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

## Uninstalling

To remove the KuzuMemory MCP integration:

```bash
python scripts/install-claude-desktop.py --uninstall
```

Or manually remove the "kuzu-memory" entry from the `mcpServers` section in your Claude Desktop configuration file.

## Support

For issues or questions:

1. Check the [troubleshooting section](#troubleshooting)
2. Run validation: `python scripts/install-claude-desktop.py --validate --verbose`
3. Check the [project issues](https://github.com/yourusername/kuzu-memory/issues)
4. Review the [MCP documentation](https://github.com/anthropics/mcp)