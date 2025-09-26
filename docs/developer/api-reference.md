# API Reference

**Complete reference for KuzuMemory CLI commands and Python API**

---

## 📋 **CLI Command Reference**

### **Global Options**

Available for all commands:
```bash
kuzu-memory [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--version` | Show version and exit | - |
| `--debug` | Enable debug logging | False |
| `--config PATH` | Path to configuration file | Auto-detect |
| `--db-path PATH` | Database path override | `kuzu-memories/` |
| `--project-root PATH` | Project root directory | Auto-detect |
| `--quiet` | Suppress non-error output | False |

---

## 🧠 **Memory Commands**

### **enhance**
Enhance prompts with relevant memories.

```bash
kuzu-memory enhance [OPTIONS] TEXT
```

**Arguments:**
- `TEXT`: Prompt text to enhance with memories

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--format` | Choice | Output format: `plain`, `json`, `markdown` | `plain` |
| `--limit` | Integer | Maximum memories to include | 5 |
| `--min-relevance` | Float | Minimum relevance score (0-1) | 0.3 |
| `--include-source` | Flag | Include source information | False |
| `--memory-types` | List | Filter by memory types | All types |

**Examples:**
```bash
# Basic enhancement
kuzu-memory enhance "How do I set up authentication?"

# JSON output for API integration
kuzu-memory enhance "Database setup?" --format json

# Limit memories and set minimum relevance
kuzu-memory enhance "API patterns?" --limit 3 --min-relevance 0.5

# Filter by memory types
kuzu-memory enhance "Architecture?" --memory-types decision,pattern
```

**Output Formats:**

*Plain (default):*
```
Enhanced prompt with 3 relevant memories:

How do I set up authentication?

Context from memories:
- We use JWT tokens for authentication
- Auth middleware is in src/middleware/auth.py
- Database stores user sessions in redis

Original prompt: How do I set up authentication?
```

*JSON:*
```json
{
  "enhanced_prompt": "How do I set up authentication?\\n\\nContext:...",
  "original_prompt": "How do I set up authentication?",
  "memories_used": [
    {
      "id": "mem-123",
      "content": "We use JWT tokens for authentication",
      "relevance": 0.89,
      "memory_type": "decision",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "metadata": {
    "query_time_ms": 45,
    "memories_found": 3,
    "memories_used": 3
  }
}
```

### **learn**
Store new memories asynchronously.

```bash
kuzu-memory learn [OPTIONS] CONTENT
```

**Arguments:**
- `CONTENT`: Memory content to store

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--source` | String | Source identifier | `cli` |
| `--memory-type` | Choice | Memory type (see types below) | `context` |
| `--importance` | Float | Importance score (0-1) | Auto-determined |
| `--confidence` | Float | Confidence score (0-1) | 1.0 |
| `--expires-in` | String | Expiration (e.g., "30d", "6h") | Type default |
| `--tags` | List | Comma-separated tags | None |
| `--batch` | Flag | Process multiple memories from stdin | False |
| `--force` | Flag | Skip deduplication | False |

**Memory Types:**
- `identity`: Core facts (never expire)
- `preference`: User/system preferences (never expire)
- `decision`: Architectural decisions (90 days)
- `pattern`: Code patterns (30 days)
- `solution`: Problem solutions (60 days)
- `status`: Current status (6 hours)
- `context`: Session context (1 day)

**Examples:**
```bash
# Basic learning
kuzu-memory learn "We use PostgreSQL for main database"

# With specific type and source
kuzu-memory learn "API uses RESTful design" --memory-type decision --source team-meeting

# Set custom expiration
kuzu-memory learn "Server maintenance tonight" --memory-type status --expires-in 12h

# Batch learning from file
cat project-notes.txt | kuzu-memory learn --batch --source documentation

# High importance memory
kuzu-memory learn "Critical: Database passwords in env vars" --importance 1.0 --memory-type identity
```

### **remember**
Store important memories (alias for learn with high importance).

```bash
kuzu-memory remember [OPTIONS] CONTENT
```

Equivalent to `learn` with `--importance 0.9` and `--memory-type decision`.

### **recall**
Query memories by content or tags.

```bash
kuzu-memory recall [OPTIONS] [QUERY]
```

**Arguments:**
- `QUERY`: Optional search query

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--format` | Choice | Output format | `list` |
| `--limit` | Integer | Maximum results | 10 |
| `--memory-types` | List | Filter by types | All |
| `--source` | String | Filter by source | All |
| `--min-relevance` | Float | Minimum relevance (0-1) | 0.0 |
| `--sort-by` | Choice | Sort: `relevance`, `date`, `importance` | `relevance` |
| `--tags` | List | Filter by tags | All |

**Examples:**
```bash
# General recall
kuzu-memory recall "database setup"

# Recent decisions
kuzu-memory recall --memory-types decision --sort-by date

# High-confidence solutions
kuzu-memory recall "error handling" --memory-types solution --min-relevance 0.7

# Specific source
kuzu-memory recall --source team-meeting --format json
```

### **recent**
Show recently created or accessed memories.

```bash
kuzu-memory recent [OPTIONS]
```

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--limit` | Integer | Number of memories | 10 |
| `--hours` | Integer | Within last N hours | 24 |
| `--format` | Choice | Output format | `list` |
| `--sort-by` | Choice | Sort: `created`, `accessed` | `created` |

---

## 🏗️ **Project Commands**

### **init**
Initialize KuzuMemory for a project.

```bash
kuzu-memory init [OPTIONS]
```

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--force` | Flag | Overwrite existing database | False |
| `--config-template` | String | Config template to use | `default` |
| `--db-path` | Path | Custom database path | `kuzu-memories/` |

**Examples:**
```bash
# Basic initialization
kuzu-memory init

# Force reinitialize
kuzu-memory init --force

# Custom database path
kuzu-memory init --db-path ./custom-memories
```

### **project**
Show project information and statistics.

```bash
kuzu-memory project [OPTIONS]
```

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--format` | Choice | Output format | `text` |
| `--verbose` | Flag | Detailed information | False |

### **stats**
Display system statistics and performance metrics.

```bash
kuzu-memory stats [OPTIONS]
```

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--format` | Choice | Output format | `text` |
| `--detailed` | Flag | Include detailed metrics | False |
| `--history` | Flag | Include historical data | False |

**Sample Output:**
```
KuzuMemory Statistics
=====================

Memory Count: 42
Database Size: 2.3 MB
Project: my-ai-project

Performance Metrics:
  Average Query Time: 35ms
  Average Learn Time: 120ms
  Cache Hit Rate: 78%

Memory Types:
  decision: 8 memories
  pattern: 12 memories
  context: 15 memories
  solution: 7 memories

Recent Activity (24h):
  Memories Created: 5
  Queries Executed: 23
  Cache Hits: 18
```

### **cleanup**
Remove expired or old memories.

```bash
kuzu-memory cleanup [OPTIONS]
```

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--older-than` | String | Remove memories older than (e.g., "30d") | Type defaults |
| `--memory-types` | List | Cleanup specific types | All |
| `--dry-run` | Flag | Show what would be removed | False |
| `--force` | Flag | Skip confirmation | False |

### **create-config**
Create configuration file template.

```bash
kuzu-memory create-config [OPTIONS] [PATH]
```

**Arguments:**
- `PATH`: Config file path (default: `kuzu-config.json`)

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--template` | String | Template name | `default` |
| `--overwrite` | Flag | Overwrite existing file | False |

---

## 🔧 **Utility Commands**

### **optimize**
Optimize system performance.

```bash
kuzu-memory optimize [OPTIONS]
```

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--enable-cli` | Flag | Enable CLI adapter | False |
| `--rebuild-index` | Flag | Rebuild search index | False |
| `--compact-db` | Flag | Compact database | False |

### **setup**
Interactive setup wizard.

```bash
kuzu-memory setup [OPTIONS]
```

**Options:**
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--non-interactive` | Flag | Skip prompts | False |

### **examples**
Show usage examples.

```bash
kuzu-memory examples [TOPIC]
```

**Topics:**
- `basic`: Basic usage examples
- `integration`: AI integration examples
- `advanced`: Advanced configuration examples

---

## 🤖 **Integration Commands**

### **mcp**
Model Context Protocol server operations.

```bash
kuzu-memory mcp [COMMAND]
```

**Sub-commands:**
- `start`: Start MCP server
- `stop`: Stop MCP server
- `status`: Show server status
- `test`: Test server functionality

### **claude-group**
Claude-specific integration commands.

```bash
kuzu-memory claude [COMMAND]
```

### **auggie**
Auggie integration commands.

```bash
kuzu-memory auggie [COMMAND]
```

---

## 🐍 **Python API**

### **Core Classes**

#### **KuzuMemory**
Main API class for memory operations.

```python
from kuzu_memory.core.memory import KuzuMemory
from pathlib import Path

# Initialize
memory = KuzuMemory(
    db_path=Path("./memories"),
    config={"max_memory_age_days": 30}
)

# Generate memories from content
memories = await memory.generate_memories(
    content="User prefers detailed error messages",
    source_type="user-feedback"
)

# Attach relevant memories to prompts
context = await memory.attach_memories(
    prompt="How should I handle API errors?",
    max_memories=5,
    min_relevance=0.3
)
```

#### **Memory Model**
Core memory data structure.

```python
from kuzu_memory.core.models import Memory, MemoryType
from datetime import datetime, timedelta

memory = Memory(
    content="We use JWT for authentication",
    memory_type=MemoryType.DECISION,
    importance=0.9,
    confidence=1.0,
    source_type="team-meeting",
    valid_to=datetime.now() + timedelta(days=90)
)
```

#### **MemoryContext**
Context structure for enhanced prompts.

```python
from kuzu_memory.core.models import MemoryContext

context = MemoryContext(
    original_prompt="How do I authenticate users?",
    enhanced_prompt="...",  # Prompt with memories
    memories=[memory1, memory2],
    metadata={
        "query_time_ms": 45,
        "memories_found": 5,
        "memories_used": 2
    }
)
```

### **Async Operations**

#### **AsyncMemorySystem**
Non-blocking memory operations.

```python
from kuzu_memory.async_memory.system import AsyncMemorySystem

async_memory = AsyncMemorySystem()

# Queue learning task (non-blocking)
await async_memory.queue_learning(
    content="New pattern learned",
    priority="normal"
)

# Check queue status
status = await async_memory.get_queue_status()
print(f"Pending tasks: {status.pending_count}")
```

### **Storage Adapters**

#### **KuzuAdapter**
Low-level database operations.

```python
from kuzu_memory.storage.kuzu_adapter import KuzuAdapter

adapter = KuzuAdapter(db_path="./memories")

# Store memory
await adapter.store_memory(memory)

# Query memories
memories = await adapter.query_memories(
    query="authentication",
    limit=10,
    min_relevance=0.3
)

# Performance stats
stats = await adapter.get_performance_stats()
```

### **Integration Utilities**

#### **CLIAdapter**
High-performance CLI integration.

```python
from kuzu_memory.storage.kuzu_cli_adapter import CLIAdapter

cli_adapter = CLIAdapter()

# Enhanced CLI operations with caching
result = await cli_adapter.enhance_prompt(
    "How do I handle errors?",
    format_type="plain",
    use_cache=True
)
```

---

## 📊 **Response Schemas**

### **Enhanced Prompt Response (JSON)**
```json
{
  "enhanced_prompt": "string",
  "original_prompt": "string",
  "memories_used": [
    {
      "id": "string",
      "content": "string",
      "relevance": "float",
      "memory_type": "string",
      "importance": "float",
      "created_at": "datetime",
      "source_type": "string"
    }
  ],
  "metadata": {
    "query_time_ms": "integer",
    "memories_found": "integer",
    "memories_used": "integer",
    "cache_hit": "boolean"
  }
}
```

### **Memory List Response (JSON)**
```json
{
  "memories": [
    {
      "id": "string",
      "content": "string",
      "memory_type": "string",
      "importance": "float",
      "confidence": "float",
      "created_at": "datetime",
      "accessed_at": "datetime",
      "access_count": "integer",
      "source_type": "string",
      "tags": ["string"],
      "valid_to": "datetime|null"
    }
  ],
  "metadata": {
    "total_count": "integer",
    "query_time_ms": "integer",
    "has_more": "boolean"
  }
}
```

### **Statistics Response (JSON)**
```json
{
  "memory_count": "integer",
  "database_size_mb": "float",
  "project_name": "string",
  "performance": {
    "avg_query_time_ms": "float",
    "avg_learn_time_ms": "float",
    "cache_hit_rate": "float",
    "queries_per_hour": "float"
  },
  "memory_types": {
    "decision": "integer",
    "pattern": "integer",
    "context": "integer",
    "solution": "integer"
  },
  "activity_24h": {
    "memories_created": "integer",
    "queries_executed": "integer",
    "cache_hits": "integer"
  }
}
```

---

## ⚡ **Performance Targets**

| Operation | Target | Typical | Notes |
|-----------|---------|---------|-------|
| `enhance` | <100ms | ~45ms | Synchronous, real-time |
| `learn` | <200ms | ~120ms | Asynchronous by default |
| `recall` | <150ms | ~65ms | Depends on query complexity |
| Database queries | <10ms | ~8ms | Single query operations |
| CLI startup | <50ms | ~25ms | Command initialization |

---

## 🚨 **Error Codes**

| Code | Description | Common Causes |
|------|-------------|---------------|
| 1 | General CLI error | Invalid arguments, permission issues |
| 2 | Database error | Corrupt database, disk full |
| 3 | Configuration error | Invalid config, missing files |
| 4 | Validation error | Invalid input, constraint violation |
| 5 | Performance error | Operation timeout, resource limits |
| 10 | Network error | MCP server issues |
| 20 | Integration error | External system failures |

---

## 🔍 **Advanced Usage**

### **Batch Operations**
```bash
# Batch learning from file
echo -e "Memory 1\\nMemory 2\\nMemory 3" | kuzu-memory learn --batch

# Batch export
kuzu-memory recall --format json --limit 1000 > memories.json

# Import memories
cat memories.json | kuzu-memory learn --batch --format json
```

### **Pipeline Integration**
```bash
# CI/CD pipeline
kuzu-memory learn "Build completed successfully" --source ci-cd --expires-in 1h

# Monitoring alerts
kuzu-memory learn "High CPU usage detected" --importance 0.8 --memory-type status
```

### **Custom Memory Types**
```python
from kuzu_memory.core.models import MemoryType

# Extend memory types (advanced usage)
class CustomMemoryType(MemoryType):
    ALERT = "alert"
    METRIC = "metric"
```

---

## 🤝 **API Support**

For questions about the API:
- **Documentation**: This reference and [Architecture Guide](architecture.md)
- **Examples**: See [Integration Guide](integration-guide.md)
- **Issues**: GitHub Issues for bug reports
- **Performance**: [Performance Guide](performance.md)

**Complete API reference for KuzuMemory!** 🧠⚡