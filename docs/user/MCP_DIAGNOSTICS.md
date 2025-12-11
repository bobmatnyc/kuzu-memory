# MCP Diagnostics Reference

**Command Reference for MCP Testing and Diagnostic Tools**

---

## Table of Contents

- [Overview](#overview)
- [Diagnostic Commands](#diagnostic-commands)
- [Health Check Commands](#health-check-commands)
- [Configuration Validation](#configuration-validation)
- [Connection Testing](#connection-testing)
- [Tool Validation](#tool-validation)
- [Report Formats](#report-formats)
- [Exit Codes](#exit-codes)
- [Auto-Fix Capabilities](#auto-fix-capabilities)
- [Examples](#examples)

---

## Overview

The MCP diagnostic framework provides automated testing, validation, and troubleshooting for the KuzuMemory MCP server.

### Scope: Project-Level Only

**The `doctor` command checks PROJECT-LEVEL configurations only**:

✅ **What Doctor Checks**:
- Project memory database (`kuzu-memory/`)
- Claude Code MCP configuration (`.claude/config.local.json`)
- MCP server configuration and connectivity
- Claude Code hooks (if configured)

❌ **What Doctor Does NOT Check**:
- Claude Desktop configuration (user home directory)
- Global installations in `~/Library/Application Support/Claude/`
- User-level configurations

**For Claude Desktop setup issues**, use the install command instead:
```bash
kuzu-memory install add claude-desktop
```

### Command Structure

```bash
kuzu-memory doctor [subcommand] [options]
```

### Available Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| `doctor` | Run diagnostic tests | `kuzu-memory doctor [subcommand]` |
| `doctor health` | Check server health | `kuzu-memory doctor health [options]` |
| `doctor mcp` | MCP diagnostics | `kuzu-memory doctor mcp [options]` |
| `doctor connection` | Test connections | `kuzu-memory doctor connection [options]` |

---

## Diagnostic Commands

### Full Diagnostics

**Run complete diagnostic suite**

```bash
kuzu-memory doctor [options]
```

**What It Tests** (Project-Level Only):
- Project memory database configuration
- Claude Code MCP configuration (`.claude/config.local.json`)
- MCP server connectivity
- Protocol initialization
- Tool discovery and execution
- Performance metrics
- Error handling

**Note**: Does NOT check Claude Desktop user-level config (`~/Library/Application Support/Claude/`)

**Interactive Fix Prompt**: If issues are detected with suggested fixes, you'll be prompted:
```
💡 Found 3 issue(s) with suggested fixes available.
Would you like to attempt automatic fixes? [Y/n]:
```

**Options**:
- `--verbose`, `-v` - Show detailed diagnostic information
- `--output FILE` - Save report to file
- `--format [text|json|html]` - Report format (default: text)
- `--fix` - Attempt automatic fixes immediately (skips interactive prompt)
- `--timeout SECONDS` - Timeout for tests (default: 30)

**Examples**:
```bash
# Basic diagnostics
kuzu-memory doctor

# Verbose output
kuzu-memory doctor -v

# Save report to file
kuzu-memory doctor --output diagnostics.txt

# JSON format for automation
kuzu-memory doctor --format json --output diagnostics.json

# HTML report
kuzu-memory doctor --format html --output report.html

# Run with auto-fix
kuzu-memory doctor --fix

# Increase timeout
kuzu-memory doctor --timeout 60
```

**Output**:
```
=== MCP Diagnostics Report ===
Date: 2025-10-01 10:30:45
Status: PASSED

Configuration: ✅ PASS
  - Config file: ~/.config/Claude/claude_desktop_config.json
  - Syntax: Valid JSON
  - Required fields: Present
  - Paths: Accessible

Connection: ✅ PASS
  - Server startup: Success (2.3s)
  - Protocol init: Success (0.5s)
  - Communication: Bidirectional
  - Latency: 45ms (target: <100ms)

Tools: ✅ PASS
  - Discovery: 4 tools found
  - Schemas: All valid
  - Execution: All tools callable
  - Error handling: Proper

Performance: ✅ PASS
  - Recall latency: 3ms (target: <100ms)
  - Enhance latency: 42ms (target: <200ms)
  - Learn latency: async
  - Stats latency: 8ms (target: <100ms)

Overall: ✅ HEALTHY
All checks passed (4/4)
```

**Exit Codes**:
- `0` - All checks passed
- `1` - Some checks failed (warnings)
- `2` - Critical checks failed (errors)

---

### Configuration Diagnostics

**Validate MCP configuration (Project-Level Only)**

```bash
kuzu-memory doctor config [options]
```

**What It Checks** (Project-Level):
- Claude Code MCP configuration file (`.claude/config.local.json`)
- JSON syntax validity
- Required fields present
- MCP server path correct
- Project root path configuration
- Environment variables set
- File permissions correct

**Note**: Does NOT check Claude Desktop config. For Claude Desktop, use:
```bash
kuzu-memory install add claude-desktop
```

**Options**:
- `--verbose`, `-v` - Show detailed configuration
- `--fix` - Attempt to fix configuration issues
- `--output FILE` - Save configuration report
- `--format [text|json]` - Report format

**Examples**:
```bash
# Check configuration
kuzu-memory doctor config

# Verbose output
kuzu-memory doctor config -v

# Fix configuration issues
kuzu-memory doctor config --fix

# Export configuration report
kuzu-memory doctor config --format json --output config-status.json
```

**Output**:
```
Configuration Validation
========================

File Location: ~/.config/Claude/claude_desktop_config.json
Status: ✅ Valid

Structure:
  ✅ Valid JSON syntax
  ✅ MCP servers section present
  ✅ kuzu-memory entry found

Settings:
  ✅ Command: pipx run --spec kuzu-memory kuzu-memory mcp serve
  ✅ Args: --project-root /path/to/project
  ✅ Environment variables: Not required

Paths:
  ✅ kuzu-memory: /usr/local/bin/kuzu-memory
  ✅ Project root: /path/to/project
  ✅ Database: /path/to/project/.kuzu_memory/kuzu.db

Permissions:
  ✅ Config file: Read/Write
  ✅ Project root: Read/Write
  ✅ Database directory: Read/Write

Result: ✅ PASS (all checks passed)
```

**Common Issues & Fixes**:

| Issue | Symptom | Auto-Fix Action |
|-------|---------|-----------------|
| Missing config | File not found | Create default configuration |
| Invalid JSON | Parse error | Restore from backup |
| Wrong server path | Command not found | Update to correct pipx command |
| Missing args | Server fails | Add required arguments |
| Permission denied | Can't read/write | Fix file permissions |

---

### Connection Diagnostics

**Test MCP server connectivity**

```bash
kuzu-memory doctor connection [options]
```

**What It Tests**:
- Server process startup
- stdio communication
- Protocol handshake (initialize)
- Request/response cycle
- Error handling
- Connection recovery
- Latency measurement

**Options**:
- `--verbose`, `-v` - Show detailed connection logs
- `--timeout SECONDS` - Connection timeout (default: 10)
- `--retries N` - Retry attempts (default: 3)
- `--output FILE` - Save connection test report

**Examples**:
```bash
# Test connection
kuzu-memory doctor connection

# With verbose logging
kuzu-memory doctor connection -v

# Custom timeout
kuzu-memory doctor connection --timeout 20

# With retries
kuzu-memory doctor connection --retries 5

# Save test results
kuzu-memory doctor connection --output connection-test.txt
```

**Output**:
```
Connection Testing
==================

Server Startup:
  ✅ Process started (PID: 12345)
  ✅ Ready in 2.3s

Protocol Initialization:
  ✅ Request sent
  ✅ Response received (500ms)
  ✅ Protocol version: 2025-06-18
  ✅ Server: kuzu-memory v1.1.6
  ✅ Capabilities: tools

Communication:
  ✅ stdio streams: Connected
  ✅ Request transmission: Success
  ✅ Response reception: Success
  ✅ Bidirectional: Confirmed

Latency:
  ✅ Connection: 107ms (target: <500ms)
  ✅ Initialize: 45ms (target: <200ms)
  ✅ Ping roundtrip: 18ms (target: <50ms)

Error Handling:
  ✅ Invalid request: Proper error code (-32600)
  ✅ Unknown method: Proper error code (-32601)
  ✅ Invalid params: Proper error code (-32602)

Result: ✅ PASS (all tests passed)
```

**Test Sequence**:
1. Start server process
2. Establish stdio connection
3. Send initialize request
4. Validate initialize response
5. Test ping (basic roundtrip)
6. Test error scenarios
7. Measure latencies
8. Shutdown server

---

### Tool Validation

**Validate MCP tools**

```bash
kuzu-memory doctor tools [options]
```

**What It Tests**:
- Tool discovery (tools/list)
- Tool count
- Tool schemas (JSON Schema compliance)
- Required parameters
- Tool execution
- Response formats
- Error handling

**Options**:
- `--verbose`, `-v` - Show detailed tool information
- `--tool NAME` - Test specific tool only
- `--skip-execution` - Skip tool execution tests
- `--output FILE` - Save tool validation report

**Examples**:
```bash
# Validate all tools
kuzu-memory doctor tools

# Test specific tool
kuzu-memory doctor tools --tool enhance

# Skip execution (schema only)
kuzu-memory doctor tools --skip-execution

# Verbose output
kuzu-memory doctor tools -v

# Save report
kuzu-memory doctor tools --output tool-validation.txt
```

**Output**:
```
Tool Validation
===============

Discovery:
  ✅ tools/list: Success
  ✅ Tool count: 4
  ✅ Tool names: enhance, recall, learn, stats

Schema Validation:
  ✅ enhance
    - Input schema: Valid JSON Schema
    - Required params: prompt
    - Optional params: limit, agent_id
  ✅ recall
    - Input schema: Valid JSON Schema
    - Required params: query
    - Optional params: limit, agent_id
  ✅ learn
    - Input schema: Valid JSON Schema
    - Required params: memory
    - Optional params: source, session_id
  ✅ stats
    - Input schema: Valid JSON Schema
    - Required params: None
    - Optional params: validate

Tool Execution:
  ✅ enhance: Success (42ms)
    - Input: {"prompt": "test", "limit": 5}
    - Output: Enhanced prompt with context
  ✅ recall: Success (3ms)
    - Input: {"query": "test", "limit": 10}
    - Output: 0 memories found
  ✅ learn: Success (async)
    - Input: {"memory": "test fact"}
    - Output: Memory queued for learning
  ✅ stats: Success (8ms)
    - Input: {}
    - Output: Statistics object

Error Handling:
  ✅ Missing required param: Proper error (-32602)
  ✅ Invalid param type: Proper error (-32602)
  ✅ Unknown tool: Proper error (-32601)

Result: ✅ PASS (all tools valid and executable)
```

**Tools Tested**:

| Tool | Required Params | Optional Params | Expected Behavior |
|------|----------------|-----------------|-------------------|
| enhance | prompt | limit, agent_id | Return enhanced prompt |
| recall | query | limit, agent_id | Return memory list |
| learn | memory | source, session_id | Queue for async learning |
| stats | - | validate | Return statistics object |

---

## Health Check Commands

### Quick Health Check

**Check server health status**

```bash
kuzu-memory doctor health [options]
```

**What It Checks**:
- Server responsiveness
- Connection latency
- Memory usage
- Tool availability
- Error rate
- Uptime

**Options**:
- `--detailed` - Show detailed health information
- `--json` - Output in JSON format
- `--continuous` - Continuous monitoring mode
- `--interval SECONDS` - Check interval for continuous mode (default: 10)
- `--alert-on-failure` - Alert on health check failure
- `--log-file FILE` - Log health checks to file

**Examples**:
```bash
# Quick health check
kuzu-memory doctor health

# Detailed status
kuzu-memory doctor health --detailed

# JSON output
kuzu-memory doctor health --json

# Continuous monitoring (every 10 seconds)
kuzu-memory doctor health --continuous

# Custom interval (every 5 seconds)
kuzu-memory doctor health --continuous --interval 5

# Log to file
kuzu-memory doctor health --continuous --log-file health.log

# Alert on failure
kuzu-memory doctor health --alert-on-failure
```

**Output (Basic)**:
```
MCP Server Health: ✅ HEALTHY
  Connection: OK (23ms)
  Memory Usage: 15MB
  Tools: 4 available
  Uptime: 2h 15m
```

**Output (Detailed)**:
```
=== MCP Server Health Status ===

Connection Status: ✅ HEALTHY
  - Latency: 23ms (target: <100ms)
  - Success Rate: 100% (100/100 requests)
  - Last Response: 2025-10-01 10:30:45

Resource Usage: ✅ HEALTHY
  - Memory: 15MB (target: <50MB)
  - Connections: 2 (max: 10)
  - Queue Depth: 0

Tool Status: ✅ HEALTHY
  - enhance: Available (avg: 45ms)
  - recall: Available (avg: 3ms)
  - learn: Available (async)
  - stats: Available (avg: 10ms)

Performance: ✅ HEALTHY
  - Throughput: 95 ops/sec (target: >50)
  - Error Rate: 0.1% (target: <1%)
  - Avg Latency: 28ms (target: <100ms)

Overall Status: ✅ HEALTHY
Uptime: 2h 15m
Last Check: 2025-10-01 10:30:45
```

**Output (JSON)**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-01T10:30:45Z",
  "connection": {
    "status": "healthy",
    "latency_ms": 23,
    "success_rate": 1.0,
    "last_response": "2025-10-01T10:30:45Z"
  },
  "resources": {
    "status": "healthy",
    "memory_mb": 15,
    "connections": 2,
    "max_connections": 10,
    "queue_depth": 0
  },
  "tools": {
    "status": "healthy",
    "available": ["enhance", "recall", "learn", "stats"],
    "latencies": {
      "enhance": 45,
      "recall": 3,
      "stats": 10
    }
  },
  "performance": {
    "status": "healthy",
    "throughput_ops_sec": 95,
    "error_rate": 0.001,
    "avg_latency_ms": 28
  },
  "uptime_seconds": 8100
}
```

**Output (Continuous)**:
```
Monitoring MCP Server Health (Ctrl+C to stop)
Interval: 10 seconds

[10:30:45] ✅ HEALTHY - Latency: 23ms, Memory: 15MB
[10:30:55] ✅ HEALTHY - Latency: 25ms, Memory: 15MB
[10:31:05] ✅ HEALTHY - Latency: 22ms, Memory: 16MB
[10:31:15] ⚠️  WARNING - Latency: 150ms, Memory: 16MB
[10:31:25] ✅ HEALTHY - Latency: 24ms, Memory: 15MB
^C
Monitoring stopped.
```

**Health Levels**:

| Status | Symbol | Criteria | Action |
|--------|--------|----------|--------|
| Healthy | ✅ | All metrics within target | None |
| Warning | ⚠️ | Metrics exceed target but < critical | Monitor closely |
| Critical | ❌ | Metrics exceed critical threshold | Immediate attention |

---

## Configuration Validation

### Configuration File Structure

**Project-Level Configuration**: `.claude/config.local.json` (Claude Code)

The `doctor` command validates the Claude Code MCP configuration file located at `.claude/config.local.json` in your project root.

**Example structure**:
```json
{
  "mcpServers": {
    "kuzu-memory": {
      "command": "kuzu-memory",
      "args": [
        "mcp",
        "serve",
        "--project-root",
        "/path/to/project"
      ],
      "env": {}
    }
  }
}
```

**Note**: For Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`), use the install command:
```bash
kuzu-memory install add claude-desktop
```

### Validation Checks

**File Existence** (Project-Level):
- Config file at `.claude/config.local.json` (project root)
- Project memory database directory (`kuzu-memory/`)
- Backup files if created by doctor command

**JSON Syntax**:
- Valid JSON format
- No trailing commas
- Proper quote escaping

**Required Fields**:
- `mcpServers` object
- `kuzu-memory` entry
- `command` field (string)
- `args` array

**Optional Fields**:
- `env` object (environment variables)

**Path Validation** (Project-Level):
- `command` executable exists and is accessible
- `project-root` directory exists and is writable
- Project memory database directory exists or can be created

**Permissions** (Project-Level):
- Config file (`.claude/config.local.json`) readable by user
- Project root writable by user
- Project memory database directory (`kuzu-memory/`) writable by user

---

## Connection Testing

### Connection Test Sequence

1. **Server Startup**
   - Launch server process
   - Verify process running
   - Check stdio streams connected

2. **Protocol Initialization**
   - Send initialize request
   - Validate response structure
   - Check protocol version
   - Verify server capabilities

3. **Basic Communication**
   - Send ping request
   - Verify response received
   - Measure roundtrip time

4. **Error Handling**
   - Test invalid request
   - Test unknown method
   - Test invalid parameters
   - Verify error codes

5. **Performance**
   - Measure connection latency
   - Measure initialization time
   - Measure ping roundtrip

6. **Cleanup**
   - Shutdown server gracefully
   - Verify process terminated

### Latency Thresholds

| Metric | Target | Critical | Unit |
|--------|--------|----------|------|
| Connection | 100 | 500 | ms |
| Initialize | 200 | 500 | ms |
| Ping roundtrip | 50 | 200 | ms |

---

## Tool Validation

### Tool Schema Requirements

**JSON Schema Compliance**:
- Must be valid JSON Schema (Draft 7 or later)
- Must include `type: "object"`
- Must include `properties` for parameters
- Must include `required` array if applicable

**Required Fields**:
- `name` - Tool name (string)
- `description` - Tool description (string)
- `inputSchema` - JSON Schema object

**Example Tool Schema**:
```json
{
  "name": "enhance",
  "description": "Enhance a prompt with relevant memories",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "The prompt to enhance"
      },
      "limit": {
        "type": "integer",
        "description": "Maximum memories to retrieve",
        "default": 10
      }
    },
    "required": ["prompt"]
  }
}
```

### Tool Execution Testing

**Test Cases**:
1. Valid input - All required parameters
2. Valid input - With optional parameters
3. Missing required parameter - Should return error -32602
4. Invalid parameter type - Should return error -32602
5. Unknown tool name - Should return error -32601

**Response Validation**:
- Response must be valid JSON-RPC 2.0
- Must include `id` matching request
- Must include `result` or `error` (not both)
- Result format must match tool specification

---

## Report Formats

### Text Format

**Human-readable format**:
- Section headers with symbols
- Hierarchical structure
- Status indicators (✅ ❌ ⚠️)
- Metrics with units
- Summary at end

**Example**:
```
=== MCP Diagnostics Report ===
Date: 2025-10-01 10:30:45

Configuration: ✅ PASS
  - File: ~/.config/Claude/claude_desktop_config.json
  - Syntax: Valid

Connection: ✅ PASS
  - Latency: 45ms

Tools: ✅ PASS
  - Count: 4

Overall: ✅ HEALTHY
```

### JSON Format

**Machine-readable format**:
- Structured data
- Parseable by automation
- Includes timestamps
- Includes all metrics

**Example**:
```json
{
  "timestamp": "2025-10-01T10:30:45Z",
  "status": "passed",
  "checks": {
    "configuration": {
      "status": "pass",
      "file": "~/.config/Claude/claude_desktop_config.json",
      "syntax": "valid"
    },
    "connection": {
      "status": "pass",
      "latency_ms": 45
    },
    "tools": {
      "status": "pass",
      "count": 4
    }
  },
  "overall": "healthy"
}
```

### HTML Format

**Interactive format**:
- Visual styling
- Expandable sections
- Charts and graphs
- Color-coded status
- Print-friendly

**Features**:
- Bootstrap styling
- Collapsible sections
- Performance charts
- Error details with stack traces
- Summary dashboard

---

## Exit Codes

### Standard Exit Codes

| Code | Status | Meaning | Example |
|------|--------|---------|---------|
| 0 | Success | All checks passed | `kuzu-memory doctor` |
| 1 | Warning | Some checks failed, non-critical | Latency exceeds target |
| 2 | Error | Critical checks failed | Server won't start |
| 3 | Usage Error | Invalid command/options | Unknown option |

### Using Exit Codes

**In Scripts**:
```bash
#!/bin/bash

# Run diagnostics
kuzu-memory doctor
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "All checks passed"
elif [ $EXIT_CODE -eq 1 ]; then
    echo "Warning: Some issues detected"
    # Send alert
elif [ $EXIT_CODE -eq 2 ]; then
    echo "Error: Critical issues detected"
    # Escalate
    exit 1
fi
```

**In CI/CD**:
```yaml
- name: Run MCP Diagnostics
  run: |
    kuzu-memory doctor
    # Will fail pipeline if exit code != 0
```

**In Monitoring**:
```bash
# Continuous monitoring with alerting
while true; do
    kuzu-memory doctor health --json > health.json
    if [ $? -ne 0 ]; then
        # Send alert
        curl -X POST https://alerts.example.com \
            -d @health.json
    fi
    sleep 60
done
```

---

## Auto-Fix Capabilities

### What Auto-Fix Can Do

**Configuration Issues**:
- Create missing config file
- Fix JSON syntax errors
- Add missing required fields
- Update server command path
- Set correct permissions

**File Issues**:
- Create missing directories
- Set file permissions
- Create backup configurations

**Server Issues**:
- Kill hanging processes
- Clear lock files
- Reset database connections

### What Auto-Fix Cannot Do

**Data Issues**:
- Recover corrupted data
- Restore deleted data
- Fix application logic errors

**System Issues**:
- Install missing system dependencies
- Fix network connectivity
- Resolve disk space issues

**Permission Issues**:
- Fix system-level permissions (requires sudo)
- Modify other users' files

### Using Auto-Fix

**Interactive Mode**:
```bash
# Prompt before each fix
kuzu-memory doctor --fix --interactive
```

**Automatic Mode**:
```bash
# Apply all fixes automatically
kuzu-memory doctor --fix
```

**Dry Run**:
```bash
# Show what would be fixed without applying
kuzu-memory doctor --fix --dry-run
```

**Selective Fixes**:
```bash
# Fix only configuration issues
kuzu-memory doctor config --fix

# Fix only connection issues
kuzu-memory doctor connection --fix
```

---

## Examples

### Example 1: Complete Diagnostic Check

```bash
# Run full diagnostics with verbose output and save report
kuzu-memory doctor -v --output full-diagnostics.txt

# Check exit code
if [ $? -eq 0 ]; then
    echo "All diagnostics passed"
else
    echo "Some diagnostics failed - check full-diagnostics.txt"
fi
```

### Example 2: Automated Health Monitoring

```bash
# Monitor health every 30 seconds and log to file
kuzu-memory doctor health --continuous --interval 30 --log-file health-monitor.log
```

### Example 3: CI/CD Pipeline

```bash
# In .github/workflows/test.yml
- name: MCP Diagnostics
  run: |
    kuzu-memory doctor --format json --output diagnostics.json

- name: Upload Diagnostics
  uses: actions/upload-artifact@v3
  with:
    name: mcp-diagnostics
    path: diagnostics.json
```

### Example 4: Troubleshooting

```bash
# Step 1: Check configuration
kuzu-memory doctor config -v

# Step 2: Test connection
kuzu-memory doctor connection -v

# Step 3: Validate tools
kuzu-memory doctor tools -v

# Step 4: Run full diagnostics with fix
kuzu-memory doctor --fix -v --output troubleshooting.txt
```

### Example 5: Performance Validation

```bash
# Check health and validate performance
kuzu-memory doctor health --detailed

# If latency is high, run full diagnostics
if kuzu-memory doctor health --json | jq '.connection.latency_ms > 100'; then
    echo "High latency detected - running diagnostics"
    kuzu-memory doctor -v
fi
```

---

## Related Documentation

- [MCP Testing Guide](MCP_TESTING_GUIDE.md) - Complete testing procedures
- [MCP Phase 5 Implementation](MCP_PHASE5_IMPLEMENTATION_REPORT.md) - Implementation details
- [Claude Desktop Setup](CLAUDE_DESKTOP_SETUP.md) - Installation guide
- [Project Instructions](../CLAUDE.md) - Main project documentation

---

**Version**: 1.0.0
**Last Updated**: 2025-10-01
**Status**: Production Ready
