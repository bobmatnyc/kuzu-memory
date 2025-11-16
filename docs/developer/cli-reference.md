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

## 🩺 **Diagnostic Commands**

### **`kuzu-memory doctor`**
Comprehensive system diagnostics and health checks.

**Usage:**
```bash
kuzu-memory doctor [SUBCOMMAND] [OPTIONS]
```

**Subcommands:**
- `diagnose` - Run full diagnostic suite (default)
- `health` - Quick health check
- `mcp` - MCP-specific diagnostics
- `connection` - Test MCP connection

**Global Options:**
- `--verbose`, `-v` - Enable verbose output
- `--output FILE`, `-o FILE` - Save report to file
- `--format FORMAT`, `-f FORMAT` - Output format: text, json, html (default: text)
- `--fix` - Attempt automatic fixes
- `--hooks/--no-hooks` - Enable/disable hooks diagnostics (default: enabled)
- `--server-lifecycle/--no-server-lifecycle` - Enable/disable server lifecycle tests (default: enabled)
- `--project-root PATH` - Specify project root directory

**Examples:**
```bash
# Run full diagnostics (29 checks, ~4.5s)
kuzu-memory doctor

# Same as above (explicit)
kuzu-memory doctor diagnose

# With verbose output
kuzu-memory doctor --verbose

# Skip server lifecycle checks (faster, ~1.6s)
kuzu-memory doctor --no-server-lifecycle

# Skip hooks checks (~3.0s)
kuzu-memory doctor --no-hooks

# Core configuration only (~0.25s)
kuzu-memory doctor --no-hooks --no-server-lifecycle

# Auto-fix issues
kuzu-memory doctor --fix

# JSON output for automation
kuzu-memory doctor --format json --output diagnostics.json

# HTML report
kuzu-memory doctor --format html --output report.html
```

**Output:**
```
🔍 Running full diagnostics...

=== Configuration Checks (11/11 passed) ===
✅ memory_database_directory: Found at /project/kuzu-memory/
✅ memory_database_file: Database initialized and accessible
✅ memory_database_initialization: Schema v1.4 initialized
✅ project_info_file: Found at /project/PROJECT.md
ℹ️ memory_readme_file: Not found (optional)
✅ kuzu_memory_config: Valid configuration
ℹ️ claude_code_config_exists: Not configured
✅ claude_code_config_valid: Valid MCP configuration
✅ mcp_server_configured: kuzu-memory server ready
ℹ️ claude_instructions_file: Not found (optional)
ℹ️ mcp_environment_variables: No environment variables set

=== Hooks Diagnostics (12/12 passed) ===
✅ hooks_config_exists: Found at .claude/settings.local.json
✅ hooks_config_valid: Valid hooks configuration
✅ hooks_event_names: Valid events (UserPromptSubmit, Stop)
✅ hooks_command_paths: Valid paths
✅ hooks_executable_exists: Found at /usr/local/bin/kuzu-memory
✅ hooks_absolute_paths: All commands use absolute paths
✅ hooks_no_duplicates: No duplicate hooks
✅ hook_session_start_execution: Hook executed (0.3s)
✅ hook_enhance_execution: Enhanced prompt (0.8s)
✅ hook_learn_execution: Learning queued
✅ hook_project_root_detection: Detected /project
✅ hook_log_directory: Writable at .kuzu-memory/logs/

=== Server Lifecycle Checks (7/7 passed) ===
✅ server_startup: Server started (PID: 12345, 1.2s)
✅ server_protocol_init: Protocol initialized (v2024-11-05, 0.5s)
✅ server_ping_response: Pong received (18ms)
✅ server_tools_list: 4 tools available
✅ server_shutdown_graceful: Clean shutdown (0.8s)
✅ server_cleanup_resources: All resources released
✅ server_restart_recovery: Server restarted (1.1s)

✅ All diagnostics passed successfully! (29/29 checks, 4.5s)
```

**What Gets Tested:**

**Configuration Checks (11):**
- Database directory and files
- Project metadata files
- Configuration validity
- Claude Code MCP setup
- Environment variables

**Hooks Diagnostics (12):**
- Hook configuration validity
- Event name validation
- Command path verification
- Hook execution tests
- Environment setup

**Server Lifecycle (7):**
- Server startup
- Protocol initialization
- Ping/pong communication
- Tools discovery
- Graceful shutdown
- Resource cleanup
- Restart recovery

**Performance Benchmarks:**
- Full diagnostics: ~4.5s (29 checks)
- Hooks only: ~1.6s (12 checks)
- Server only: ~3.0s (7 checks)
- Core only: ~0.25s (11 checks)

---

### **`kuzu-memory doctor diagnose`**
Run full diagnostic suite (default command).

**Usage:**
```bash
kuzu-memory doctor diagnose [OPTIONS]
```

**Options:**
Same as main `doctor` command.

**Examples:**
```bash
# Explicit diagnose command
kuzu-memory doctor diagnose

# With auto-fix
kuzu-memory doctor diagnose --fix

# Selective testing
kuzu-memory doctor diagnose --no-server-lifecycle
```

---

### **`kuzu-memory doctor health`**
Quick health check for continuous monitoring.

**Usage:**
```bash
kuzu-memory doctor health [OPTIONS]
```

**Options:**
- `--detailed` - Show detailed health information
- `--json` - Output in JSON format
- `--continuous` - Continuous monitoring mode
- `--interval SECONDS` - Check interval (default: 5)
- `--project-root PATH` - Specify project root

**Examples:**
```bash
# Quick health check
kuzu-memory doctor health

# Detailed status
kuzu-memory doctor health --detailed

# JSON output
kuzu-memory doctor health --json

# Continuous monitoring (every 5 seconds)
kuzu-memory doctor health --continuous

# Custom interval (every 30 seconds)
kuzu-memory doctor health --continuous --interval 30
```

**Output:**
```
🏥 System Health: ✅ HEALTHY
Check Duration: 45.23ms
Timestamp: 2025-11-07 14:30:45
```

**Output (Detailed):**
```
=== System Health Status ===

Connection Status: ✅ HEALTHY
  Latency: 23ms
  Success Rate: 100%
  Last Response: 2025-11-07 14:30:45

Resource Usage: ✅ HEALTHY
  Memory: 15MB
  Connections: 2
  Queue Depth: 0

Tool Status: ✅ HEALTHY
  - enhance: Available (avg: 45ms)
  - recall: Available (avg: 3ms)
  - learn: Available (async)
  - stats: Available (avg: 10ms)

Overall Status: ✅ HEALTHY
Uptime: 2h 15m
```

**Output (JSON):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T14:30:45Z",
  "connection": {
    "status": "healthy",
    "latency_ms": 23,
    "success_rate": 1.0
  },
  "resources": {
    "memory_mb": 15,
    "connections": 2
  },
  "overall": "healthy"
}
```

---

### **`kuzu-memory doctor mcp`**
MCP-specific diagnostics for server configuration and tools.

**Usage:**
```bash
kuzu-memory doctor mcp [OPTIONS]
```

**Options:**
- `--verbose`, `-v` - Show detailed output
- `--output FILE` - Save report to file
- `--project-root PATH` - Specify project root

**Examples:**
```bash
# MCP diagnostics
kuzu-memory doctor mcp

# Verbose output
kuzu-memory doctor mcp --verbose

# Save report
kuzu-memory doctor mcp --output mcp-report.txt
```

**Output:**
```
🔍 Running MCP diagnostics...

Configuration:
✅ claude_code_config_valid: Valid MCP configuration
✅ mcp_server_configured: kuzu-memory server ready

Tools:
✅ tools_discovery: 4 tools found
✅ tool_schemas_valid: All schemas valid
✅ tool_execution: All tools callable

✅ MCP diagnostics passed (6/6 checks)
```

---

### **`kuzu-memory doctor connection`**
Test MCP server connection and protocol.

**Usage:**
```bash
kuzu-memory doctor connection [OPTIONS]
```

**Options:**
- `--verbose`, `-v` - Show detailed connection logs
- `--output FILE` - Save connection test report
- `--project-root PATH` - Specify project root

**Examples:**
```bash
# Test connection
kuzu-memory doctor connection

# With verbose logging
kuzu-memory doctor connection --verbose

# Save results
kuzu-memory doctor connection --output connection-test.txt
```

**Output:**
```
🔗 Testing MCP server connection...

Server Startup:
✅ server_startup: Server started (PID: 12345, 1.2s)

Protocol:
✅ server_protocol_init: Protocol initialized (0.5s)
✅ server_ping_response: Pong received (18ms)

Communication:
✅ stdio_connection: Bidirectional
✅ jsonrpc_compliance: JSON-RPC 2.0 compliant

✅ Connection tests passed (5/5 checks)
```

---

### **`kuzu-memory repair`**
Auto-fix broken MCP configurations across all detected frameworks.

**Usage:**
```bash
kuzu-memory repair [OPTIONS]
```

**Options:**
- `--project-root PATH` - Specify project root directory
- `--verbose` - Show detailed repair information

**What it fixes:**
- Broken `["mcp", "serve"]` args → `["mcp"]` (common MCP startup issue)
- Auto-detects Claude Code, Claude Desktop, Cursor, VS Code, Windsurf
- Creates backups before making changes
- Shows clear before/after comparison

**Examples:**
```bash
# Auto-detect and repair all installed systems
kuzu-memory repair
# 🔧 Scanning for MCP configurations...
#
# ╭─── 📦 Found 2 systems ─────────────────────────╮
# │ • Claude Code    (.claude/config.local.json)  │
# │ • Claude Desktop (~/.config/Claude/config.json)│
# ╰────────────────────────────────────────────────╯
#
# 🔍 Checking Claude Code configuration...
# ⚠️  Found broken args: ["mcp", "serve"]
# ✅ Fixed: ["mcp"]
# 📄 Backup: .claude/config.local.json.backup-20251115-223045
#
# 🔍 Checking Claude Desktop configuration...
# ✅ Configuration OK (no changes needed)
#
# ✅ Repair complete! 1 configuration fixed.

# Show detailed repair information
kuzu-memory repair --verbose
# Shows full JSON diffs before/after changes
```

**When to use:**
- MCP server fails to start with args-related errors
- After upgrading from older KuzuMemory versions
- When integrations stop working unexpectedly
- To verify configurations across multiple systems

**Safety:**
- Always creates timestamped backups before changes
- Never modifies configurations that are already correct
- Atomic operations (all or nothing)
- Can be run multiple times safely (idempotent)

**Output:**
The command provides clear feedback about:
- Which systems were detected
- What issues were found
- What changes were made
- Where backups were saved

**Related commands:**
- `kuzu-memory doctor` - Diagnose issues
- `kuzu-memory install <system>` - Reinstall from scratch

---

### **`kuzu-memory update`**
Check for and install kuzu-memory updates from PyPI.

**Usage:**
```bash
kuzu-memory update [OPTIONS]
```

**Options:**
- `--check-only` - Only check for updates without upgrading
- `--pre` - Include pre-release versions
- `--format [text|json]` - Output format (default: text)
- `--quiet`, `-q` - Silent mode, no output unless update available

**Exit Codes:**
- `0` - No update available or upgrade successful
- `1` - Error occurred
- `2` - Update available (with --check-only)

**Examples:**

Basic check and upgrade:
```bash
kuzu-memory update
# 🔍 Checking for updates...
#
# ╭─── 📦 Update Available ────────────────────────────╮
# │ Current version: 1.4.46                            │
# │ Latest version:  1.4.50                            │
# │ Update type:     🔧 Patch                          │
# │ Released:        2025-11-10                        │
# │                                                    │
# │ Release notes:   https://pypi.org/project/...      │
# │                                                    │
# │ To upgrade, run:                                   │
# │   pip install --upgrade kuzu-memory                │
# │                                                    │
# │ Or use: kuzu-memory update (without --check-only) │
# ╰────────────────────────────────────────────────────╯
#
# 🚀 Upgrade now? (y/N): y
# 📦 Upgrading kuzu-memory...
# ✅ Successfully upgraded to the latest version!
```

Check only (no upgrade):
```bash
kuzu-memory update --check-only
# 📦 Update Available
# Current version: 1.4.46
# Latest version:  1.4.50
# Update type:     🔧 Patch
# Released:        2025-11-10
```

Already up to date:
```bash
kuzu-memory update --check-only
# ✅ You are running the latest version!
# Current version: 1.4.46
# Latest version:  1.4.46
```

Include pre-releases:
```bash
kuzu-memory update --pre
# Checks for beta, alpha, and release candidate versions
```

JSON output for automation:
```bash
kuzu-memory update --check-only --format json
{
  "current_version": "1.4.46",
  "latest_version": "1.4.50",
  "update_available": true,
  "version_type": "patch",
  "release_date": "2025-11-10",
  "release_url": "https://pypi.org/project/kuzu-memory/1.4.50/",
  "error": null
}
```

Silent mode for scripts:
```bash
#!/bin/bash
kuzu-memory update --check-only --quiet
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
  echo "Update available!"
  # Send notification
  kuzu-memory update --check-only --format json | mail -s "Update Available" admin@example.com
elif [ $EXIT_CODE -eq 0 ]; then
  echo "Up to date"
else
  echo "Error checking for updates"
fi
```

**Version Types:**
- 🚀 **Major** - Breaking changes (e.g., 1.x.x → 2.0.0)
- ✨ **Minor** - New features (e.g., 1.4.x → 1.5.0)
- 🔧 **Patch** - Bug fixes (e.g., 1.4.46 → 1.4.47)

**Automation Examples:**

Cron job (daily check):
```bash
# Add to crontab: crontab -e
0 9 * * * /usr/local/bin/kuzu-memory update --check-only --quiet || echo "KuzuMemory update available" | mail -s "Update Notice" admin@example.com
```

GitHub Actions workflow:
```yaml
name: Check KuzuMemory Updates
on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM
jobs:
  check-updates:
    runs-on: ubuntu-latest
    steps:
      - name: Install kuzu-memory
        run: pip install kuzu-memory

      - name: Check for updates
        id: update-check
        run: |
          kuzu-memory update --check-only --format json > update.json
          cat update.json

      - name: Notify on update
        if: steps.update-check.outputs.exit-code == 2
        run: |
          # Send notification (Slack, email, etc.)
          echo "Update available!"
```

Docker health check:
```dockerfile
HEALTHCHECK --interval=24h --timeout=10s \
  CMD kuzu-memory update --check-only --quiet || exit 1
```

Python integration:
```python
import subprocess
import json

def check_for_updates():
    """Check if kuzu-memory update is available."""
    try:
        result = subprocess.run([
            'kuzu-memory', 'update', '--check-only', '--format', 'json', '--quiet'
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 2:
            # Update available
            data = json.loads(result.stdout)
            return {
                'available': True,
                'current': data['current_version'],
                'latest': data['latest_version'],
                'type': data['version_type']
            }
        elif result.returncode == 0:
            # Up to date
            return {'available': False}
        else:
            # Error
            return {'error': 'Failed to check for updates'}
    except Exception as e:
        return {'error': str(e)}
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
- `2` - Update available (when using `update --check-only`)
- `3` - Database error
- `4` - Timeout error
- `5` - Permission error

**Note:** Exit code `2` is specifically used by `kuzu-memory update --check-only` to indicate an update is available, allowing for easy script-based detection of updates.

**This comprehensive CLI provides everything needed for memory operations and AI integration.** 🎯✨
