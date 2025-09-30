# CLI Reference

## 🎯 **Command Overview**

KuzuMemory provides a comprehensive CLI interface for all memory operations. All commands are designed for both human use and programmatic integration.

```bash
kuzu-memory [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

### **Global Options**
- `--project PATH` - Specify project directory (default: auto-detect)
- `--debug` - Enable debug output
- `--quiet` - Suppress non-essential output
- `--help` - Show help message

---

## 📋 **Core Commands**

### **`kuzu-memory init`**
Initialize memory system for a project.

**Usage:**
```bash
kuzu-memory init [OPTIONS]
```

**Options:**
- `--force` - Reinitialize existing project
- `--template TEMPLATE` - Use specific project template

**Examples:**
```bash
# Initialize in current directory
kuzu-memory init

# Force reinitialize
kuzu-memory init --force

# Initialize with template
kuzu-memory init --template python-web
```

**Output:**
```
🎯 Initializing KuzuMemory for project: my-project
✅ Created kuzu-memories/ directory
✅ Initialized database schema
✅ Created configuration file
✅ Project ready for memory operations
```

---

### **`kuzu-memory enhance`**
Enhance prompts with project context (synchronous, fast).

**Usage:**
```bash
kuzu-memory enhance PROMPT [OPTIONS]
```

**Options:**
- `--format FORMAT` - Output format: `plain`, `json`, `context` (default: `context`)
- `--max-memories N` - Maximum memories to include (default: 5)
- `--confidence-threshold N` - Minimum confidence threshold (default: 0.3)

**Examples:**
```bash
# Basic enhancement
kuzu-memory enhance "How do I structure an API endpoint?"

# Plain format for AI integration
kuzu-memory enhance "How do I deploy this app?" --format plain

# JSON format for programmatic use
kuzu-memory enhance "What database should I use?" --format json

# Limit context size
kuzu-memory enhance "How do I test this?" --max-memories 3
```

**Output Formats:**

**Context Format (default):**
```
🧠 Enhanced with 3 memories (confidence: 0.85)

## Relevant Context:
1. Project uses FastAPI as web framework
2. Database is PostgreSQL with SQLAlchemy
3. Team prefers async/await patterns

## User Question:
How do I structure an API endpoint?
```

**Plain Format:**
```
## Relevant Context:
1. Project uses FastAPI as web framework
2. Database is PostgreSQL with SQLAlchemy
3. Team prefers async/await patterns

## User Question:
How do I structure an API endpoint?
```

**JSON Format:**
```json
{
  "original_prompt": "How do I structure an API endpoint?",
  "enhanced_prompt": "## Relevant Context:\n1. Project uses FastAPI...",
  "memories_used": [
    {
      "content": "Project uses FastAPI as web framework",
      "confidence": 0.92,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "confidence": 0.85
}
```

---

### **`kuzu-memory learn`**
Store new memories (asynchronous by default).

**Usage:**
```bash
kuzu-memory learn CONTENT [OPTIONS]
```

**Options:**
- `--source SOURCE` - Memory source (default: `manual`)
- `--metadata JSON` - Additional metadata as JSON
- `--sync` - Use synchronous processing (for testing)
- `--quiet` - Suppress output

**Examples:**
```bash
# Basic learning
kuzu-memory learn "We decided to use FastAPI for this project"

# With source
kuzu-memory learn "User prefers TypeScript" --source user-preference

# With metadata
kuzu-memory learn "API rate limit is 1000/hour" --metadata '{"component": "api"}'

# Quiet mode for scripts
kuzu-memory learn "Team uses pytest for testing" --quiet

# Synchronous mode for testing
kuzu-memory learn "Test memory" --sync
```

**Output:**
```bash
# Default async mode
✅ Learning task c3b068ac... queued for background processing

# Sync mode
✅ Stored 2 memories
```

---

### **`kuzu-memory recall`**
Search and retrieve memories.

**Usage:**
```bash
kuzu-memory recall QUERY [OPTIONS]
```

**Options:**
- `--format FORMAT` - Output format: `table`, `json`, `list` (default: `table`)
- `--limit N` - Maximum results (default: 10)
- `--source SOURCE` - Filter by source
- `--confidence-threshold N` - Minimum confidence (default: 0.1)

**Examples:**
```bash
# Basic search
kuzu-memory recall "database setup"

# JSON output
kuzu-memory recall "testing strategy" --format json

# Filter by source
kuzu-memory recall "preferences" --source user-preference

# Limit results
kuzu-memory recall "api" --limit 5
```

**Output:**
```
📋 Found 3 memories for "database setup"

┌─────────────────────────────────────────┬────────────┬─────────────────────┐
│ Content                                 │ Confidence │ Created             │
├─────────────────────────────────────────┼────────────┼─────────────────────┤
│ Project uses PostgreSQL as database     │ 0.95       │ 2024-01-15 10:30:00 │
│ Database connection pool size is 20     │ 0.87       │ 2024-01-15 11:15:00 │
│ Use SQLAlchemy for database operations  │ 0.82       │ 2024-01-15 09:45:00 │
└─────────────────────────────────────────┴────────────┴─────────────────────┘
```

---

### **`kuzu-memory recent`**
Show recent memories.

**Usage:**
```bash
kuzu-memory recent [OPTIONS]
```

**Options:**
- `--limit N` - Number of recent memories (default: 10)
- `--format FORMAT` - Output format: `table`, `json`, `list` (default: `table`)

**Examples:**
```bash
# Show recent memories
kuzu-memory recent

# Show more memories
kuzu-memory recent --limit 20

# List format
kuzu-memory recent --format list
```

---

### **`kuzu-memory stats`**
Show memory system statistics.

**Usage:**
```bash
kuzu-memory stats [OPTIONS]
```

**Options:**
- `--format FORMAT` - Output format: `table`, `json` (default: `table`)
- `--detailed` - Show detailed statistics

**Examples:**
```bash
# Basic statistics
kuzu-memory stats

# JSON format
kuzu-memory stats --format json

# Detailed statistics
kuzu-memory stats --detailed
```

**Output:**
```
📊 KuzuMemory Statistics

Memory Database:
  Total memories: 1,247
  Memory types: factual (45%), preference (20%), decision (25%), pattern (8%), entity (2%)
  Sources: ai-conversation (67%), manual (20%), user-preference (13%)

Performance:
  Avg context retrieval: 42ms
  Cache hit rate: 87%
  Async queue size: 3 tasks

Usage (Last 24h):
  Queries: 156
  Memories learned: 23
  Enhancement requests: 89
```

---

### **`kuzu-memory project`**
Show project information.

**Usage:**
```bash
kuzu-memory project [OPTIONS]
```

**Options:**
- `--format FORMAT` - Output format: `table`, `json` (default: `table`)

**Examples:**
```bash
# Show project info
kuzu-memory project

# JSON format
kuzu-memory project --format json
```

**Output:**
```
📁 Project Information

Project: my-awesome-project
Location: /Users/dev/projects/my-awesome-project
Memory Database: kuzu-memories/database.kuzu (2.3 MB)
Configuration: kuzu-memories/config.json

Status:
  ✅ Database healthy
  ✅ Schema up to date
  ✅ Async system running
  ✅ 1,247 memories loaded
```

---

## 🔧 **Utility Commands**

### **`kuzu-memory remember`**
Quick memory storage (alias for `learn` with better UX).

**Usage:**
```bash
kuzu-memory remember CONTENT [OPTIONS]
```

**Examples:**
```bash
kuzu-memory remember "This project uses FastAPI with PostgreSQL"
```

### **`kuzu-memory forget`**
Remove memories (use with caution).

**Usage:**
```bash
kuzu-memory forget QUERY [OPTIONS]
```

**Options:**
- `--confirm` - Skip confirmation prompt
- `--dry-run` - Show what would be deleted without deleting

**Examples:**
```bash
# Remove specific memories
kuzu-memory forget "old database setup" --confirm

# Dry run to see what would be deleted
kuzu-memory forget "test memories" --dry-run
```

---

## 🎮 **Integration Examples**

### **Shell Script Integration**
```bash
#!/bin/bash

# Function to enhance prompts
enhance_prompt() {
    local prompt="$1"
    kuzu-memory enhance "$prompt" --format plain 2>/dev/null || echo "$prompt"
}

# Function to store learning
store_learning() {
    local content="$1"
    kuzu-memory learn "$content" --quiet 2>/dev/null || true
}

# Usage
USER_PROMPT="How do I deploy this application?"
ENHANCED_PROMPT=$(enhance_prompt "$USER_PROMPT")
AI_RESPONSE=$(call_ai_system "$ENHANCED_PROMPT")
store_learning "User asked about deployment: $AI_RESPONSE"
```

### **Python Integration**
```python
import subprocess
import json

def kuzu_enhance(prompt, format='plain'):
    """Enhance prompt with project context."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'enhance', prompt, '--format', format
        ], capture_output=True, text=True, check=True, timeout=5)
        return result.stdout.strip()
    except:
        return prompt

def kuzu_learn(content, source='ai-conversation'):
    """Store learning asynchronously."""
    subprocess.run([
        'kuzu-memory', 'learn', content, '--source', source, '--quiet'
    ], check=False)

def kuzu_stats():
    """Get memory statistics."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'stats', '--format', 'json'
        ], capture_output=True, text=True, check=True, timeout=5)
        return json.loads(result.stdout)
    except:
        return {}
```

---

## 🔍 **Advanced Usage**

### **Chaining Commands**
```bash
# Store and immediately verify
kuzu-memory learn "New API endpoint pattern" && kuzu-memory recent --limit 1

# Search and enhance
kuzu-memory recall "database" | head -1 | kuzu-memory enhance "How do I optimize queries?"
```

### **Batch Operations**
```bash
# Store multiple memories
echo "Memory 1" | kuzu-memory learn --source batch
echo "Memory 2" | kuzu-memory learn --source batch
echo "Memory 3" | kuzu-memory learn --source batch

# Batch enhancement
cat prompts.txt | while read prompt; do
    kuzu-memory enhance "$prompt" --format plain
done
```

### **Configuration via Environment**
```bash
export KUZU_MEMORY_PROJECT="/path/to/project"
export KUZU_MEMORY_DEBUG=1
export KUZU_MEMORY_QUIET=1

kuzu-memory stats  # Uses environment configuration
```

---

## 🆘 **Troubleshooting**

### **Common Issues**

**Command not found:**
```bash
# Check installation
which kuzu-memory
pip show kuzu-memory

# Reinstall if needed
pip install --upgrade kuzu-memory
```

**Permission errors:**
```bash
# Check directory permissions
ls -la kuzu-memories/
chmod 755 kuzu-memories/
```

**Performance issues:**
```bash
# Check system health
kuzu-memory stats --detailed

# Clear cache if needed
kuzu-memory project --clear-cache
```

**Database corruption:**
```bash
# Reinitialize database
kuzu-memory init --force

# Restore from backup
kuzu-memory restore --backup kuzu-memories/backups/latest.backup
```

### **Exit Codes**
KuzuMemory uses standard exit codes for programmatic integration:

- `0` - Success
- `1` - General error
- `2` - Invalid arguments
- `3` - Database error
- `4` - Timeout error
- `5` - Permission error

**This comprehensive CLI provides everything needed for memory operations and AI integration.** 🎯✨
