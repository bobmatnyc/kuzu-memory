# KuzuMemory: Coding Tools Only

## Decision: Focus on Development Environments

As of this update, KuzuMemory **no longer supports Claude Desktop** as an installation target. We are focusing exclusively on coding/development tools where KuzuMemory provides the most value.

## Why This Change?

### 1. **Context Matters**
KuzuMemory is designed for **project-specific memory** - storing context about codebases, technical decisions, and development patterns. This makes sense in coding environments where you're actively working on projects, not in general-purpose chat applications.

### 2. **Reduced Complexity**
Supporting Claude Desktop added:
- Extra configuration files to manage
- Separate installation paths
- Confusion about where KuzuMemory was active
- Maintenance overhead

### 3. **Better Focus**
By focusing on coding tools, we can:
- Optimize for developer workflows
- Integrate deeply with IDE features
- Provide better context from project files
- Streamline installation and configuration

## Supported Platforms (Coding Tools Only)

✅ **Fully Supported:**
- **Claude Code** (VS Code with Claude extension) - MCP + hooks integration
- **Cursor IDE** - MCP server integration
- **VS Code** (with Claude extension) - MCP server integration
- **Windsurf IDE** - MCP server integration
- **Codex** - MCP server integration
- **Auggie** - AI-native code editor with MCP support

❌ **No Longer Supported:**
- Claude Desktop (general chat application)

## Installation

```bash
# Install for Claude Code (recommended)
kuzu-memory install claude-code

# Install for Cursor IDE
kuzu-memory install cursor

# Install for VS Code
kuzu-memory install vscode

# Install for Windsurf
kuzu-memory install windsurf

# See all available integrations
kuzu-memory install --help
```

## What About Claude Desktop Users?

If you were using KuzuMemory with Claude Desktop:

1. **Switch to Claude Code** (recommended)
   - Same Claude model (Sonnet 4.5)
   - Better coding features
   - Project-aware context
   - Installation: `kuzu-memory install claude-code`

2. **Manually Configure MCP** (advanced)
   - You can still manually configure MCP servers in Claude Desktop
   - See: [Claude Desktop MCP Documentation](https://docs.anthropic.com/claude/docs/mcp)
   - However, we won't provide automated installation or support

## Migration Guide

### From Claude Desktop to Claude Code

**Step 1: Remove from Claude Desktop**
```bash
# Backup config
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json.backup

# Manually edit the config to remove kuzu-memory entry
# Or just let it be - it won't interfere
```

**Step 2: Install for Claude Code**
```bash
cd /path/to/your/project
kuzu-memory install claude-code
```

**Step 3: Verify**
- Open VS Code with Claude Code extension
- Check that MCP server shows as connected
- Try using kuzu-memory tools: `kuzu_stats`, `kuzu_enhance`, etc.

## Configuration Cleanup

The following configuration changes were made:

### Removed:
- `~/Library/Application Support/Claude/claude_desktop_config.json` - kuzu-memory entry removed
- `kuzu-memory install claude-desktop` command - no longer available
- Claude Desktop installer registration in code

### Preserved:
- All project-specific `.claude.json` configurations (Claude Code)
- Project hooks in `.claude/hooks/`
- Database files in `/Users/masa/.kuzu-memory/`

## Why Coding Tools Are Better for KuzuMemory

| Feature | Claude Desktop | Coding Tools (Claude Code, Cursor, etc.) |
|---------|----------------|------------------------------------------|
| **Project Context** | ❌ Not project-aware | ✅ Automatically scoped to project |
| **File Integration** | ❌ Manual file references | ✅ Direct file access and editing |
| **Memory Scope** | ❌ Global, not project-specific | ✅ Project-specific memory database |
| **Development Flow** | ❌ Context switching required | ✅ Integrated in coding workflow |
| **Git Integration** | ❌ No git awareness | ✅ Git-aware context enhancement |
| **Hooks Support** | ❌ No hook system | ✅ Pre/post-prompt hooks for context |

## Technical Details

### Code Changes
1. **Removed from `AVAILABLE_INTEGRATIONS`**
   - File: `src/kuzu_memory/cli/install_unified.py:24`
   - Change: Removed "claude-desktop" from list

2. **Removed from Registry**
   - File: `src/kuzu_memory/installers/registry.py:46`
   - Change: Commented out `SmartClaudeDesktopInstaller` registration

3. **Removed Next Steps**
   - File: `src/kuzu_memory/cli/install_unified.py:290-293`
   - Change: Removed Claude Desktop post-install instructions

### Backward Compatibility

If someone tries to install with the old command:
```bash
kuzu-memory install claude-desktop
```

They will see:
```
❌ No installer found for: claude-desktop

💡 Available integrations:
  • claude-code
  • codex
  • cursor
  • vscode
  • windsurf
  • auggie
  • auggie-mcp
```

## Rationale Summary

**Focus on Development**: KuzuMemory excels in development environments where it can provide:
- Project-scoped memory
- Codebase-aware context
- Git integration
- IDE integration
- Developer workflow optimization

**Not a General Chat Tool**: Claude Desktop is for general conversations. KuzuMemory's strength is in coding workflows, not general chat.

**Simpler is Better**: By removing Claude Desktop support, we:
- Reduce configuration complexity
- Focus testing and QA efforts
- Improve developer experience
- Streamline documentation

## Questions?

If you have questions about this change:
1. Check the [Installation Guide](docs/installation.md)
2. See [Supported Platforms](docs/platforms.md)
3. Open an issue: https://github.com/kuzu-memory/kuzu-memory/issues

---

**TL;DR**: KuzuMemory now focuses exclusively on coding tools (Claude Code, Cursor, VS Code, etc.) where it provides the most value. Claude Desktop support has been removed to reduce complexity and improve focus on development workflows.
