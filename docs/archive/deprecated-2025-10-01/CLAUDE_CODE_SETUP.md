# KuzuMemory Claude Code Integration

## 🚀 Quick Installation

### One-Line Install (Recommended)
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/kuzu-memory/main/scripts/install-claude-code.sh | bash
```

### Manual Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/kuzu-memory.git
cd kuzu-memory

# Run the wrapper installer
./kuzu-memory-wrapper.sh install

# Or use the Python installer with Claude Code support
python install.py
```

## 🎯 What This Provides

Once installed, Claude Code will have access to these MCP tools:

### Memory Operations
- **`enhance`** - Enhance prompts with relevant project context
- **`learn`** - Store learnings asynchronously (non-blocking)
- **`recall`** - Query memories for relevant information
- **`remember`** - Store direct memories

### Project Management
- **`init`** - Initialize a new project memory store
- **`project`** - Get project information
- **`stats`** - Get memory system statistics
- **`recent`** - Get recent memories
- **`cleanup`** - Clean up expired memories

## 📋 Usage in Claude Code

Once installed, you can use KuzuMemory tools directly in Claude Code:

### Example Conversations

```
User: Remember that this project uses FastAPI with PostgreSQL

Claude: I'll store that project information for you.
[Uses remember tool: "This project uses FastAPI with PostgreSQL"]
✓ Stored project information in memory

User: How should I structure my API endpoints?

Claude: Let me enhance your question with project context first.
[Uses enhance tool to get relevant context]
Based on your project setup with FastAPI and PostgreSQL...
[Provides contextual answer]
```

### Automatic Context Enhancement

Claude Code will automatically:
1. Enhance prompts with relevant project context
2. Learn from your conversations and corrections
3. Recall relevant information when needed
4. Maintain project-specific knowledge

## 🔧 Configuration

### MCP Server Configuration

The installer creates an MCP configuration at:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### Custom Configuration

You can customize the MCP server by editing `~/.config/kuzu-memory/mcp_server_config.json`:

```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "~/.local/bin/kuzu-memory-mcp",
      "args": [],
      "env": {
        "KUZU_MEMORY_HOME": "~/.local/kuzu-memory",
        "KUZU_MEMORY_PROJECT": "${PROJECT_ROOT}"
      }
    }
  }
}
```

## 🛠 Manual Setup

If automatic installation doesn't work:

### 1. Install KuzuMemory
```bash
pip install kuzu-memory
# or for development
pip install -e .
```

### 2. Create MCP Wrapper
Create `~/.local/bin/kuzu-memory-mcp`:
```bash
#!/bin/bash
exec python -m kuzu_memory.mcp.run_server "$@"
```

### 3. Configure Claude Code
Add to Claude's configuration:
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "~/.local/bin/kuzu-memory-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

### 4. Restart Claude Code
Restart Claude Code to load the new MCP server.

## 🧪 Testing the Integration

### Verify Installation
```bash
# Check if kuzu-memory is installed
kuzu-memory --version

# Test MCP server directly
python -m kuzu_memory.mcp.run_server
```

### Test in Claude Code
1. Open Claude Code
2. Start a new conversation
3. Try: "Use kuzu-memory to remember that I prefer TypeScript"
4. Then: "What are my preferences?"

## 🆘 Troubleshooting

### MCP Server Not Found
- Ensure `~/.local/bin` is in your PATH
- Check that `kuzu-memory-mcp` is executable
- Verify Python environment is correct

### Claude Code Not Loading Tools
- Restart Claude Code after configuration
- Check logs in Claude Code developer console
- Verify JSON configuration is valid

### Memory Operations Failing
- Initialize project first: `kuzu-memory init`
- Check database permissions in `kuzu-memories/` directory
- Verify Python dependencies are installed

## 📊 Performance

KuzuMemory MCP integration provides:
- **<100ms response time** for context retrieval
- **Async learning** that doesn't block conversations
- **Project-specific memory** that's git-committed
- **Zero-config operation** with sensible defaults

## 🔒 Security

- Memories are stored locally in your project
- No external API calls or data transmission
- Git-integrated for team collaboration
- Respects `.gitignore` patterns

## 📚 Advanced Features

### Custom Memory Types
Configure retention policies in `~/.config/kuzu-memory/config.json`:
```json
{
  "memory": {
    "retention_days": {
      "identity": -1,     // Never expire
      "preference": -1,   // Never expire
      "decision": 90,     // 90 days
      "pattern": 30,      // 30 days
      "general": 30       // 30 days
    }
  }
}
```

### Performance Tuning
```json
{
  "performance": {
    "max_response_time_ms": 100,
    "async_learning": true,
    "connection_pooling": true,
    "cache_enabled": true
  }
}
```

## 🤝 Contributing

Help improve the Claude Code integration:
1. Report issues on GitHub
2. Submit PRs for enhancements
3. Share your use cases and feedback

## 📄 License

MIT License - See LICENSE file for details

---

**KuzuMemory + Claude Code = Smarter AI Conversations** 🧠🤖✨