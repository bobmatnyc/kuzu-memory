# 🤖 KuzuMemory Claude Code Integration

Enhance Claude Code/Desktop with persistent, project-specific memory using KuzuMemory hooks.

## 🚀 Quick Start

```bash
# Install KuzuMemory
pip install kuzu-memory

# Set up Claude integration
kuzu-memory claude install

# Test the integration
kuzu-memory claude test
```

## 📋 Features

### **Automatic Memory Learning**
- Learns from your conversations with Claude
- Tracks file operations and code changes
- Remembers project decisions and preferences
- Stores technical context and patterns

### **Context Enhancement**
- Enhances prompts with relevant project context (<100ms)
- Provides semantic memory recall
- Maintains conversation continuity
- Shares team knowledge through git

### **MCP Server Integration**
- Native Claude Desktop support via Model Context Protocol
- Async operations for non-blocking learning
- Multiple tools exposed (enhance, learn, recall, stats)
- Project-scoped memory isolation

## 🛠️ Installation Methods

### **Method 1: CLI Command** (Recommended)
```bash
kuzu-memory claude install
```

### **Method 2: Interactive Wizard**
```bash
kuzu-memory claude wizard
```
Follow the interactive prompts to configure your integration.

### **Method 3: Standalone Script**
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/kuzu-memory/main/scripts/install-claude-hooks.sh | bash
```

### **Method 4: Manual Installation**
1. Initialize KuzuMemory in your project:
   ```bash
   kuzu-memory init
   ```

2. Install MCP configuration:
   ```bash
   kuzu-memory claude install --mcp-only
   ```

3. Verify installation:
   ```bash
   kuzu-memory claude status
   ```

## 📁 Project Structure

After installation, your project will have:

```
your-project/
├── kuzu-memories/          # Memory database (git-committed)
│   └── memories.db
├── .claude-mpm/           # Claude project manager config
│   └── config/
├── CLAUDE.md              # Project context for Claude
└── CLAUDE.local.md        # Personal notes (gitignored)
```

## 🔧 Configuration

### **MCP Server Configuration**

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

### **Project Configuration**

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

## 🎯 Usage Examples

### **Check Installation Status**
```bash
kuzu-memory claude status
```

### **Test Integration**
```bash
kuzu-memory claude test
```

### **View Memory Statistics**
```bash
kuzu-memory stats
```

### **Manual Memory Management**
```bash
# Add specific knowledge
kuzu-memory remember "We use PostgreSQL for the main database"

# Query memories
kuzu-memory recall "database"

# Learn from file
kuzu-memory learn-from-file README.md
```

## 🔍 How It Works

### **1. Prompt Enhancement** (Pre-message Hook)
When you send a message to Claude, KuzuMemory:
1. Analyzes your prompt for relevant keywords/entities
2. Retrieves relevant memories (<100ms)
3. Enhances the prompt with context
4. Passes enhanced prompt to Claude

### **2. Continuous Learning** (Post-message Hook)
After Claude responds, KuzuMemory:
1. Extracts learnable patterns from the conversation
2. Identifies decisions, preferences, and facts
3. Stores new memories asynchronously
4. Deduplicates against existing memories

### **3. Tool Tracking** (Tool-call Hook)
When Claude uses tools, KuzuMemory:
1. Records file access patterns
2. Tracks code modifications
3. Notes frequently used commands
4. Builds project activity map

## 🎨 Advanced Features

### **Memory Types**
- **IDENTITY**: Who you are, your role (never expires)
- **PREFERENCE**: Your coding preferences (never expires)
- **DECISION**: Technical decisions made (90 days)
- **PATTERN**: Code patterns used (30 days)
- **STATUS**: Current work status (6 hours)

### **Recall Strategies**
- **Auto**: Intelligent strategy selection
- **Keyword**: Exact term matching
- **Entity**: Entity-based recall
- **Temporal**: Recent memories first
- **Semantic**: Vector similarity (future)

### **Performance Optimization**
- Connection pooling for fast database access
- LRU caching for frequent queries
- Async learning to avoid blocking
- CLI adapter mode for 2-3x speedup

## 🐛 Troubleshooting

### **"Claude hooks not installed"**
```bash
kuzu-memory claude install --force
```

### **"Database not initialized"**
```bash
kuzu-memory init
```

### **"MCP server not responding"**
```bash
# Check if server is running
ps aux | grep kuzu-memory

# Restart Claude Desktop
# The MCP server starts automatically
```

### **"Permission denied"**
```bash
# Fix permissions
chmod +x ~/.local/bin/kuzu-memory
```

## 🔐 Security & Privacy

- **Local-first**: All memories stored locally in your project
- **No external APIs**: No data sent to external services
- **Respects .gitignore**: Sensitive files not indexed
- **Credential filtering**: Never stores passwords/keys
- **Project isolation**: Memories scoped per project

## 📊 Performance Metrics

| Operation | Target | Actual |
|-----------|--------|--------|
| Prompt Enhancement | <100ms | ~50ms |
| Memory Learning | Async | Non-blocking |
| Memory Recall | <100ms | ~40ms |
| Database Query | <50ms | ~20ms |

## 🤝 Contributing

Contributions welcome! Areas of interest:
- Vector embeddings for semantic search
- Cross-IDE support (VS Code extension)
- Memory visualization dashboard
- Advanced learning algorithms

## 📄 License

MIT License - See LICENSE file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/kuzu-memory/issues)
- **Discord**: [Join our community](https://discord.gg/kuzu-memory)

---

**KuzuMemory**: Giving Claude a memory, one conversation at a time. 🧠✨