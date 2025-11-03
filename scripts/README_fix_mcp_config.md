# Fix MCP Configuration Script

## Overview

The `fix_mcp_config.py` script fixes outdated KuzuMemory MCP server configurations in Claude Desktop's configuration file.

## Problem

Older versions of the KuzuMemory installation scripts used the deprecated command format:
```json
"args": ["mcp", "serve"]
```

The current version only requires:
```json
"args": ["mcp"]
```

This script automatically updates all kuzu-memory MCP entries to use the correct format.

## Usage

### Basic Usage

```bash
# Fix the default configuration file (~/.claude.json)
python3 scripts/fix_mcp_config.py

# Fix the Claude Desktop configuration
python3 scripts/fix_mcp_config.py --config ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Preview Changes (Dry Run)

```bash
# See what would be changed without modifying the file
python3 scripts/fix_mcp_config.py --dry-run --verbose
```

### Validate Configuration

```bash
# Check if configuration needs fixing
python3 scripts/fix_mcp_config.py --validate
```

### Custom Configuration File

```bash
# Fix a configuration file at a custom location
python3 scripts/fix_mcp_config.py --config /path/to/claude.json
```

## Options

- `--config PATH` - Path to claude.json file (default: `~/.claude.json`)
- `--dry-run` - Show what would be changed without modifying the file
- `--validate` - Validate configuration without making changes
- `--verbose` - Enable detailed output

## Safety Features

1. **Automatic Backup**: Creates a timestamped backup before any changes
   - Backup location: Same directory as config file
   - Format: `config_name.backup_YYYYMMDD_HHMMSS`

2. **Idempotent**: Safe to run multiple times
   - Won't create backups if no changes are needed
   - Detects already-fixed configurations

3. **Error Handling**: Gracefully handles:
   - Missing configuration files
   - Invalid JSON
   - Permission errors
   - Backup failures

## What It Does

1. Loads the Claude Desktop configuration file
2. Searches for all kuzu-memory MCP server entries
3. Identifies entries with outdated `["mcp", "serve"]` arguments
4. Updates them to use `["mcp"]` while preserving other arguments
5. Saves the corrected configuration with a backup

## Examples

### Example 1: Fix Standard Installation

```bash
$ python3 scripts/fix_mcp_config.py --verbose

============================================================
  KuzuMemory MCP Configuration Fixer
============================================================

ℹ Configuration file: /Users/masa/.claude.json
ℹ Loading configuration...
ℹ Searching for kuzu-memory MCP entries...
✓ Found 1 kuzu-memory MCP entry/entries
ℹ Entry 'kuzu-memory' needs fixing
ℹ   Current args: ['mcp', 'serve']
⚠ Found 1 entry/entries that need fixing
ℹ Creating backup before making changes...
✓ Created backup: /Users/masa/.claude.backup_20251102_123456
ℹ Applying fixes...
✓ Fixed entry 'kuzu-memory':
ℹ   ['mcp', 'serve'] → ['mcp']
ℹ Writing updated configuration...

============================================================
  Configuration Fixed Successfully!
============================================================

✓ Fixed 1 argument(s) in 1 entry/entries
ℹ Backup saved to: /Users/masa/.claude.backup_20251102_123456
ℹ
ℹ Next steps:
ℹ 1. Restart Claude Desktop to load the updated configuration
ℹ 2. The kuzu-memory MCP server should now work correctly
```

### Example 2: Dry Run

```bash
$ python3 scripts/fix_mcp_config.py --dry-run

============================================================
  KuzuMemory MCP Configuration Fixer
============================================================

ℹ Configuration file: /Users/masa/.claude.json
ℹ Loading configuration...
ℹ Searching for kuzu-memory MCP entries...
✓ Found 1 kuzu-memory MCP entry/entries
⚠ Found 1 entry/entries that need fixing
⚠ DRY RUN - No changes will be made
ℹ
ℹ Entry 'kuzu-memory':
⚠   Old args: ['mcp', 'serve']
✓   New args: ['mcp']
ℹ
```

### Example 3: Already Fixed

```bash
$ python3 scripts/fix_mcp_config.py

============================================================
  KuzuMemory MCP Configuration Fixer
============================================================

ℹ Configuration file: /Users/masa/.claude.json
ℹ Loading configuration...
ℹ Searching for kuzu-memory MCP entries...
✓ Found 1 kuzu-memory MCP entry/entries
✓ All kuzu-memory entries are already correct!
ℹ No changes needed.
```

## Configuration Detection

The script automatically detects kuzu-memory MCP servers by:

1. **Server name**: Entries with "kuzu-memory" in the name
2. **Command**: Commands containing "kuzu"
3. **Arguments**: Arguments containing "kuzu_memory" module references

## Exit Codes

- `0` - Success (fixes applied or no changes needed)
- `1` - Error occurred (see error message for details)

## Common Issues

### File Not Found
```
✗ Configuration file not found: /Users/masa/.claude.json
This is normal if you haven't configured Claude Desktop yet.
```

**Solution**: Ensure Claude Desktop is installed and configured, or specify the correct config path with `--config`.

### Invalid JSON
```
✗ Configuration file contains invalid JSON:
  Expecting ',' delimiter: line 5 column 3 (char 123)
```

**Solution**: Fix the JSON syntax errors manually, or restore from a backup if available.

### Permission Denied
```
✗ Permission denied: [Errno 13] Permission denied: '/Users/masa/.claude.json'
Try running with appropriate permissions
```

**Solution**: Check file permissions or run with appropriate user privileges.

## Integration with Installation Scripts

This script is designed to work alongside the existing installation scripts:

- `install-claude-desktop.py` - May create configurations with old format
- `install-claude-desktop-home.py` - Alternative installation location

Run this fix script after installation to ensure the configuration uses the current command format.

## Technical Details

### Before
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp", "serve"],
      "env": {
        "KUZU_MEMORY_DB": "/Users/masa/.kuzu-memory/memorydb",
        "KUZU_MEMORY_MODE": "mcp"
      }
    }
  }
}
```

### After
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": ["mcp"],
      "env": {
        "KUZU_MEMORY_DB": "/Users/masa/.kuzu-memory/memorydb",
        "KUZU_MEMORY_MODE": "mcp"
      }
    }
  }
}
```

## Related Files

- `/scripts/install-claude-desktop.py` - Main installation script (deprecated, now uses correct format)
- `/scripts/install-claude-desktop-home.py` - Alternative installation script
- `/kuzu_memory/mcp/run_server.py` - MCP server implementation

## Version History

- **1.0.0** (2025-11-02) - Initial release
  - Automatic backup creation
  - Idempotent operation
  - Dry-run support
  - Validation mode
  - Comprehensive error handling
