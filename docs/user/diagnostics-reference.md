# Diagnostics Reference

**Complete reference for all KuzuMemory diagnostic checks**

---

## Table of Contents

- [Overview](#overview)
- [Configuration Checks (11)](#configuration-checks-11)
- [Hooks Diagnostics (12)](#hooks-diagnostics-12)
- [Server Lifecycle Checks (7)](#server-lifecycle-checks-7)
- [Severity Levels](#severity-levels)
- [Auto-Fix Capabilities](#auto-fix-capabilities)
- [Performance Benchmarks](#performance-benchmarks)
- [CI/CD Integration](#cicd-integration)

---

## Overview

The `kuzu-memory doctor` command runs **29 comprehensive diagnostic checks** across three categories:

1. **Configuration Checks** (11) - Core system configuration validation
2. **Hooks Diagnostics** (12) - Claude Code hooks system testing
3. **Server Lifecycle Checks** (7) - MCP server lifecycle validation

### Quick Reference

| Category | Checks | Avg Time | Can Skip? |
|----------|--------|----------|-----------|
| Configuration | 11 | ~0.25s | No |
| Hooks | 12 | ~1.6s | Yes (`--no-hooks`) |
| Server Lifecycle | 7 | ~3.0s | Yes (`--no-server-lifecycle`) |
| **Total** | **29** | **~4.5s** | - |

---

## Configuration Checks (11)

Core configuration validation for project setup.

### memory_database_directory

**What It Tests**: Verifies that the project memory database directory exists

**Severity**: ERROR

**Path Checked**: `kuzu-memory/` or `.kuzu-memory/` in project root

**Success Criteria**:
- Directory exists
- Directory is readable and writable

**Common Failure Reasons**:
- Project not initialized
- Directory was deleted
- Incorrect permissions

**Fix Suggestion**:
```bash
kuzu-memory init
```

**Example Output**:
```
✅ memory_database_directory: Found at /project/kuzu-memory/
```

---

### memory_database_file

**What It Tests**: Verifies that the Kuzu database file exists and is valid

**Severity**: CRITICAL

**Path Checked**: `kuzu-memory/` (Kuzu database directory structure)

**Success Criteria**:
- Database directory structure exists
- Database is accessible and not corrupted

**Common Failure Reasons**:
- Database never initialized
- Database corruption
- File permissions issue

**Fix Suggestion**:
```bash
kuzu-memory init --force
```

**Example Output**:
```
✅ memory_database_file: Database initialized and accessible
```

---

### memory_database_initialization

**What It Tests**: Verifies that the database schema is properly initialized

**Severity**: CRITICAL

**Tables Checked**:
- Memory nodes table
- Relationship tables
- Schema version metadata

**Success Criteria**:
- All required tables exist
- Schema version matches expected version
- Database is queryable

**Common Failure Reasons**:
- Incomplete initialization
- Schema migration needed
- Database corruption

**Fix Suggestion**:
```bash
kuzu-memory init --force
```

**Example Output**:
```
✅ memory_database_initialization: Schema v1.4 initialized
```

---

### project_info_file

**What It Tests**: Checks for PROJECT.md file with project metadata

**Severity**: WARNING

**Path Checked**: `PROJECT.md` in project root

**Success Criteria**:
- File exists and is readable
- Contains valid project information

**Common Failure Reasons**:
- File not created during initialization
- File was deleted
- Wrong project directory

**Fix Suggestion**:
```bash
# File is optional, but recommended for better context
echo "# Project Name\nDescription" > PROJECT.md
```

**Example Output**:
```
✅ project_info_file: Found at /project/PROJECT.md
⚠️ project_info_file: File not found (optional)
```

---

### memory_readme_file

**What It Tests**: Checks for README.md in memory directory

**Severity**: INFO

**Path Checked**: `kuzu-memory/README.md`

**Success Criteria**:
- File exists (optional)

**Common Failure Reasons**:
- Not created (this is informational only)

**Fix Suggestion**:
None - this is informational only

**Example Output**:
```
ℹ️ memory_readme_file: Not found (optional documentation)
```

---

### kuzu_memory_config

**What It Tests**: Validates kuzu-memory configuration file

**Severity**: WARNING

**Path Checked**: `kuzu-memory/config.yaml` or `.kuzu-memory/config.yaml`

**Success Criteria**:
- File exists and is valid YAML
- Contains required configuration keys
- Values are within acceptable ranges

**Common Failure Reasons**:
- Invalid YAML syntax
- Missing required keys
- Invalid configuration values

**Fix Suggestion**:
```bash
kuzu-memory init --force
```

**Example Output**:
```
✅ kuzu_memory_config: Valid configuration
⚠️ kuzu_memory_config: Using default config (file not found)
```

---

### claude_code_config_exists

**What It Tests**: Checks if Claude Code configuration file exists

**Severity**: INFO

**Path Checked**: `.claude/config.local.json`

**Success Criteria**:
- File exists (optional - only needed for Claude Code integration)

**Common Failure Reasons**:
- Claude Code integration not installed
- Wrong project directory

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code
```

**Example Output**:
```
✅ claude_code_config_exists: Found at .claude/config.local.json
ℹ️ claude_code_config_exists: Not configured (run install command if needed)
```

---

### claude_code_config_valid

**What It Tests**: Validates Claude Code MCP configuration syntax and structure

**Severity**: ERROR (if file exists)

**Validates**:
- JSON syntax is valid
- `mcpServers` object exists
- `kuzu-memory` server entry exists
- Required fields present (command, args)

**Success Criteria**:
- Valid JSON structure
- Required fields present and correct type
- Server command path is valid

**Common Failure Reasons**:
- Invalid JSON syntax
- Missing required fields
- Incorrect server configuration

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code --force
```

**Example Output**:
```
✅ claude_code_config_valid: Valid MCP server configuration
❌ claude_code_config_valid: Invalid JSON syntax
```

---

### mcp_server_configured

**What It Tests**: Verifies MCP server is properly configured in Claude Code

**Severity**: INFO

**Checks**:
- `kuzu-memory` entry in mcpServers
- Command path is accessible
- Args include project root

**Success Criteria**:
- Server configured with correct command
- Project root argument present
- Command is executable

**Common Failure Reasons**:
- MCP server not installed
- Incorrect command path
- Missing project-root argument

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code
```

**Example Output**:
```
✅ mcp_server_configured: kuzu-memory server ready
ℹ️ mcp_server_configured: Not configured
```

---

### claude_instructions_file

**What It Tests**: Checks for CLAUDE.md instructions file

**Severity**: INFO

**Path Checked**: `CLAUDE.md` in project root

**Success Criteria**:
- File exists (optional)

**Common Failure Reasons**:
- Not created (optional file)

**Fix Suggestion**:
None - this is optional

**Example Output**:
```
ℹ️ claude_instructions_file: Not found (optional)
```

---

### mcp_environment_variables

**What It Tests**: Validates MCP-related environment variables

**Severity**: INFO

**Checks**:
- `KUZU_MEMORY_PROJECT_ROOT` if set
- Other kuzu-memory environment variables

**Success Criteria**:
- Variables are correctly set (if needed)
- No conflicting values

**Common Failure Reasons**:
- Incorrect paths in environment variables
- Conflicting configurations

**Fix Suggestion**:
```bash
# Usually not needed, remove if causing issues
unset KUZU_MEMORY_PROJECT_ROOT
```

**Example Output**:
```
ℹ️ mcp_environment_variables: No environment variables set
```

---

## Hooks Diagnostics (12)

Claude Code hooks system validation and testing.

### hooks_config_exists

**What It Tests**: Verifies hooks configuration in Claude Code settings

**Severity**: INFO

**Path Checked**: `.claude/settings.local.json`

**Success Criteria**:
- File exists
- Contains hooks configuration

**Common Failure Reasons**:
- Hooks not installed
- Wrong project directory

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code
```

**Example Output**:
```
✅ hooks_config_exists: Found at .claude/settings.local.json
ℹ️ hooks_config_exists: No hooks configured
```

---

### hooks_config_valid

**What It Tests**: Validates hooks configuration JSON syntax and structure

**Severity**: ERROR (if hooks configured)

**Validates**:
- Valid JSON syntax
- Hooks array exists
- Hook entries have required fields

**Success Criteria**:
- Valid JSON structure
- All hooks have name and event
- Commands are properly formatted

**Common Failure Reasons**:
- Invalid JSON syntax
- Missing required fields
- Malformed hook entries

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code --force
```

**Example Output**:
```
✅ hooks_config_valid: Valid hooks configuration
❌ hooks_config_valid: JSON syntax error at line 15
```

---

### hooks_event_names

**What It Tests**: Validates that hook event names are correct

**Severity**: ERROR

**Expected Events**:
- `UserPromptSubmit` (for enhancement)
- `Stop` (for learning)

**Success Criteria**:
- Event names match expected values exactly
- No typos or incorrect casing

**Common Failure Reasons**:
- Typo in event name
- Wrong event type
- Case sensitivity issue

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code --force
```

**Example Output**:
```
✅ hooks_event_names: Valid events (UserPromptSubmit, Stop)
❌ hooks_event_names: Invalid event 'UserPromptSubmited' (typo)
```

---

### hooks_command_paths

**What It Tests**: Verifies hook command paths are valid

**Severity**: ERROR

**Checks**:
- Command includes valid executable path
- Path exists and is accessible

**Success Criteria**:
- Command uses absolute path to kuzu-memory
- Executable exists and has execute permissions

**Common Failure Reasons**:
- Relative path used instead of absolute
- Executable not found
- Permission denied

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code --force
```

**Example Output**:
```
✅ hooks_command_paths: Valid paths (/usr/local/bin/kuzu-memory)
❌ hooks_command_paths: Command not found: kuzu-memory
```

---

### hooks_executable_exists

**What It Tests**: Verifies kuzu-memory executable exists at hook path

**Severity**: ERROR

**Checks**:
- File exists at specified path
- File is executable
- File is the kuzu-memory binary

**Success Criteria**:
- Executable found
- Execute permissions set
- Correct binary (can run --version)

**Common Failure Reasons**:
- Binary moved or deleted
- Incorrect path in configuration
- Permission issues

**Fix Suggestion**:
```bash
which kuzu-memory  # Find correct path
kuzu-memory install add claude-code --force
```

**Example Output**:
```
✅ hooks_executable_exists: Found at /usr/local/bin/kuzu-memory
❌ hooks_executable_exists: Not found at /old/path/kuzu-memory
```

---

### hooks_absolute_paths

**What It Tests**: Ensures all hook commands use absolute paths

**Severity**: ERROR

**Checks**:
- Commands start with `/` (absolute path)
- No relative paths like `./` or `../`

**Success Criteria**:
- All commands use absolute paths
- Paths are properly formatted

**Common Failure Reasons**:
- Relative paths used
- Shell commands without full path

**Fix Suggestion**:
```bash
kuzu-memory install add claude-code --force
```

**Example Output**:
```
✅ hooks_absolute_paths: All commands use absolute paths
❌ hooks_absolute_paths: Relative path found: ./kuzu-memory
```

---

### hooks_no_duplicates

**What It Tests**: Checks for duplicate hook entries

**Severity**: WARNING

**Checks**:
- No duplicate event handlers
- Unique hook names

**Success Criteria**:
- Each event handled once
- No duplicate configurations

**Common Failure Reasons**:
- Multiple install attempts
- Manual configuration errors

**Fix Suggestion**:
```bash
# Edit .claude/settings.local.json and remove duplicates
kuzu-memory install add claude-code --force
```

**Example Output**:
```
✅ hooks_no_duplicates: No duplicate hooks
⚠️ hooks_no_duplicates: UserPromptSubmit handled twice
```

---

### hook_session_start_execution

**What It Tests**: Tests session-start hook execution (if configured)

**Severity**: WARNING

**Tests**:
- Hook command runs successfully
- Returns valid output
- Completes in reasonable time (<5s)

**Success Criteria**:
- Command executes without error
- Output is valid (if any)
- Performance acceptable

**Common Failure Reasons**:
- Command path incorrect
- Database not initialized
- Timeout

**Fix Suggestion**:
```bash
# Check hook manually
/usr/local/bin/kuzu-memory hooks session-start
```

**Example Output**:
```
✅ hook_session_start_execution: Hook executed successfully (0.3s)
⚠️ hook_session_start_execution: Hook timed out after 5s
```

---

### hook_enhance_execution

**What It Tests**: Tests enhance hook (UserPromptSubmit) execution

**Severity**: ERROR

**Tests**:
- Hook enhances test prompt
- Returns enhanced output
- Performance meets target (<2s)

**Success Criteria**:
- Enhancement successful
- Output includes test prompt
- Reasonable performance

**Common Failure Reasons**:
- Command error
- Database connection failed
- Performance degradation

**Fix Suggestion**:
```bash
# Test manually
echo "test prompt" | /usr/local/bin/kuzu-memory hooks enhance
```

**Example Output**:
```
✅ hook_enhance_execution: Enhanced prompt successfully (0.8s)
❌ hook_enhance_execution: Command failed: database locked
```

---

### hook_learn_execution

**What It Tests**: Tests learn hook (Stop) execution

**Severity**: ERROR

**Tests**:
- Hook processes learning request
- Stores memory asynchronously
- Returns success status

**Success Criteria**:
- Learning queued successfully
- No immediate errors
- Async processing starts

**Common Failure Reasons**:
- Command error
- Database write failed
- Invalid input format

**Fix Suggestion**:
```bash
# Test manually
echo '{"memory": "test"}' | /usr/local/bin/kuzu-memory hooks learn
```

**Example Output**:
```
✅ hook_learn_execution: Learning queued successfully
❌ hook_learn_execution: Failed to store memory
```

---

### hook_project_root_detection

**What It Tests**: Verifies hooks correctly detect project root

**Severity**: ERROR

**Tests**:
- Hook can determine project root
- Uses correct database path
- No path resolution errors

**Success Criteria**:
- Project root correctly identified
- Database path correct
- No path errors

**Common Failure Reasons**:
- Working directory issues
- Path resolution failures
- Symlink problems

**Fix Suggestion**:
```bash
# Check project structure
pwd
ls -la kuzu-memory/
```

**Example Output**:
```
✅ hook_project_root_detection: Detected /correct/path
❌ hook_project_root_detection: Failed to detect project root
```

---

### hook_log_directory

**What It Tests**: Checks if hook log directory exists and is writable

**Severity**: WARNING

**Path Checked**: `.kuzu-memory/logs/` or configured log path

**Success Criteria**:
- Directory exists
- Directory is writable
- Logs can be created

**Common Failure Reasons**:
- Directory not created
- Permission denied
- Disk full

**Fix Suggestion**:
```bash
mkdir -p .kuzu-memory/logs
chmod 755 .kuzu-memory/logs
```

**Example Output**:
```
✅ hook_log_directory: Writable at .kuzu-memory/logs/
⚠️ hook_log_directory: Not found, logs disabled
```

---

### hook_cache_directory

**What It Tests**: Checks if hook cache directory exists and is writable

**Severity**: INFO

**Path Checked**: `.kuzu-memory/cache/` or configured cache path

**Success Criteria**:
- Directory exists (optional)
- Directory is writable if it exists

**Common Failure Reasons**:
- Directory not created (OK)
- Permission issues

**Fix Suggestion**:
```bash
mkdir -p .kuzu-memory/cache
chmod 755 .kuzu-memory/cache
```

**Example Output**:
```
ℹ️ hook_cache_directory: Not found (caching disabled)
```

---

## Server Lifecycle Checks (7)

MCP server startup, operation, and shutdown validation.

### server_startup

**What It Tests**: Verifies MCP server can start successfully

**Severity**: CRITICAL

**Tests**:
- Server process launches
- Process ID obtained
- stdio streams connected
- Startup completes in reasonable time

**Success Criteria**:
- Server starts without error
- Process running and responsive
- Startup time < 5s

**Common Failure Reasons**:
- Binary not found
- Port already in use
- Database locked
- Insufficient permissions

**Fix Suggestion**:
```bash
# Kill any hanging processes
pkill -f "kuzu-memory mcp"

# Check binary
which kuzu-memory
kuzu-memory --version

# Test manually
kuzu-memory mcp serve --project-root /path/to/project
```

**Example Output**:
```
✅ server_startup: Server started successfully (PID: 12345, 1.2s)
❌ server_startup: Failed to start (timeout after 10s)
```

---

### server_protocol_init

**What It Tests**: Tests MCP protocol initialization handshake

**Severity**: CRITICAL

**Tests**:
- Initialize request succeeds
- Protocol version compatible
- Server capabilities reported
- Handshake completes < 2s

**Success Criteria**:
- Initialize response received
- Protocol version supported
- Capabilities include tools
- Reasonable latency

**Common Failure Reasons**:
- Protocol mismatch
- Timeout during handshake
- Invalid response format
- Communication error

**Fix Suggestion**:
```bash
# Check server logs
cat .kuzu-memory/logs/mcp-server.log

# Test connection manually
kuzu-memory doctor connection --verbose
```

**Example Output**:
```
✅ server_protocol_init: Protocol initialized (v2024-11-05, 0.5s)
❌ server_protocol_init: Protocol version mismatch
```

---

### server_ping_response

**What It Tests**: Tests basic server responsiveness with ping

**Severity**: ERROR

**Tests**:
- Ping request sends successfully
- Pong response received
- Roundtrip time < 100ms

**Success Criteria**:
- Server responds to ping
- Response format valid
- Low latency

**Common Failure Reasons**:
- Server not responsive
- Communication failure
- Performance degradation

**Fix Suggestion**:
```bash
# Restart server
kuzu-memory doctor connection --verbose
```

**Example Output**:
```
✅ server_ping_response: Pong received (18ms)
❌ server_ping_response: No response (timeout)
```

---

### server_tools_list

**What It Tests**: Verifies tools/list request works

**Severity**: ERROR

**Tests**:
- tools/list request succeeds
- Expected tools present (enhance, recall, learn, stats)
- Tool schemas valid

**Success Criteria**:
- All 4 tools discovered
- Valid tool definitions
- Correct schemas

**Common Failure Reasons**:
- Tool registration failed
- Invalid tool definitions
- Server initialization incomplete

**Fix Suggestion**:
```bash
# Check server startup
kuzu-memory doctor --verbose
```

**Example Output**:
```
✅ server_tools_list: 4 tools available
❌ server_tools_list: Only 2 tools found (expected 4)
```

---

### server_shutdown_graceful

**What It Tests**: Tests graceful server shutdown

**Severity**: WARNING

**Tests**:
- Shutdown request accepted
- Server exits cleanly
- Resources released
- Shutdown time < 3s

**Success Criteria**:
- Clean shutdown
- No hanging processes
- Quick completion

**Common Failure Reasons**:
- Server hangs
- Resources not released
- Zombie processes

**Fix Suggestion**:
```bash
# Force kill if needed
pkill -9 -f "kuzu-memory mcp"
```

**Example Output**:
```
✅ server_shutdown_graceful: Clean shutdown (0.8s)
⚠️ server_shutdown_graceful: Timeout, process killed
```

---

### server_cleanup_resources

**What It Tests**: Verifies server cleans up resources after shutdown

**Severity**: WARNING

**Tests**:
- No zombie processes
- Lock files removed
- Temporary files cleaned
- Connections closed

**Success Criteria**:
- All resources released
- No zombie processes
- Clean state

**Common Failure Reasons**:
- Process didn't fully exit
- Lock files remain
- Resource leaks

**Fix Suggestion**:
```bash
# Clean up manually
pkill -9 -f "kuzu-memory mcp"
rm -f .kuzu-memory/*.lock
```

**Example Output**:
```
✅ server_cleanup_resources: All resources released
⚠️ server_cleanup_resources: Found zombie process (PID: 12346)
```

---

### server_restart_recovery

**What It Tests**: Tests server can restart after shutdown

**Severity**: ERROR

**Tests**:
- Server can restart
- State recovers correctly
- No startup errors
- Restart time acceptable

**Success Criteria**:
- Successful restart
- State intact
- Normal operation resumes

**Common Failure Reasons**:
- Lock files prevent restart
- Corrupted state
- Port still in use

**Fix Suggestion**:
```bash
# Clean state before restart
rm -f .kuzu-memory/*.lock
kuzu-memory doctor --verbose
```

**Example Output**:
```
✅ server_restart_recovery: Server restarted successfully (1.1s)
❌ server_restart_recovery: Restart failed (port in use)
```

---

## Severity Levels

### SUCCESS (✅)
- **Meaning**: Check passed completely
- **Action Required**: None
- **Exit Code Impact**: Does not affect exit code

### INFO (ℹ️)
- **Meaning**: Informational message, not an error
- **Action Required**: None (optional feature)
- **Exit Code Impact**: Does not affect exit code
- **Examples**: Optional files not found, features not configured

### WARNING (⚠️)
- **Meaning**: Issue detected but not critical
- **Action Required**: Monitor, consider fixing
- **Exit Code Impact**: Returns exit code 1
- **Examples**: Performance degradation, missing optional features

### ERROR (❌)
- **Meaning**: Problem that should be fixed
- **Action Required**: Fix recommended
- **Exit Code Impact**: Returns exit code 1
- **Examples**: Configuration errors, failed functionality

### CRITICAL (🔴)
- **Meaning**: Serious issue requiring immediate attention
- **Action Required**: Fix immediately
- **Exit Code Impact**: Returns exit code 1
- **Examples**: Database not initialized, server won't start

---

## Auto-Fix Capabilities

### What Auto-Fix Can Do

**Configuration Files**:
- Create missing configuration files
- Fix JSON syntax errors (by regenerating)
- Add missing required fields
- Update paths to correct values

**Directories**:
- Create missing database directories
- Create log directories
- Set correct permissions

**Database**:
- Initialize database if missing
- Recreate corrupted database

**Example**:
```bash
# Run with interactive auto-fix prompt
kuzu-memory doctor

# Auto-fix immediately without prompt
kuzu-memory doctor --fix

# Run specific checks with auto-fix
kuzu-memory doctor mcp --fix
```

### What Auto-Fix Cannot Do

**Manual Intervention Required**:
- Install kuzu-memory binary if missing
- Fix system-level permissions (requires sudo)
- Recover lost data
- Fix network connectivity
- Resolve disk space issues
- Install system dependencies

**For These Issues**:
- Follow the "Fix:" suggestions in error messages
- Refer to the troubleshooting guide
- Check installation documentation

---

## Performance Benchmarks

Based on QA testing on standard hardware:

### Full Diagnostics (29 checks)
```bash
kuzu-memory doctor
```
- **Time**: ~4.5 seconds
- **Breakdown**:
  - Configuration: ~0.25s (11 checks)
  - Hooks: ~1.6s (12 checks)
  - Server Lifecycle: ~3.0s (7 checks)

### Selective Testing

**Core Configuration Only**:
```bash
kuzu-memory doctor --no-hooks --no-server-lifecycle
```
- **Time**: ~0.25 seconds
- **Checks**: 11

**Hooks Only**:
```bash
kuzu-memory doctor --no-server-lifecycle
```
- **Time**: ~1.6 seconds
- **Checks**: 23 (11 core + 12 hooks)

**Server Lifecycle Only**:
```bash
kuzu-memory doctor --no-hooks
```
- **Time**: ~3.0 seconds
- **Checks**: 18 (11 core + 7 server)

### Performance Targets

| Check Type | Target Time | Typical Time |
|------------|-------------|--------------|
| Configuration check | <50ms | ~20ms |
| Hook execution test | <2s | ~0.5s |
| Server startup | <5s | ~1.2s |
| Protocol init | <2s | ~0.5s |
| Full diagnostics | <10s | ~4.5s |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: KuzuMemory Health Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # Run daily at 6 AM
    - cron: '0 6 * * *'

jobs:
  diagnostics:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install KuzuMemory
        run: |
          pip install kuzu-memory

      - name: Initialize Project
        run: |
          kuzu-memory init

      - name: Run Full Diagnostics
        run: |
          kuzu-memory doctor --format json --output diagnostics.json
        continue-on-error: true

      - name: Check Results
        run: |
          cat diagnostics.json
          # Parse JSON and fail if critical errors
          python -c "
          import json
          import sys
          with open('diagnostics.json') as f:
              report = json.load(f)
              if report.get('has_critical_errors'):
                  print('CRITICAL ERRORS DETECTED')
                  sys.exit(1)
          "

      - name: Upload Diagnostics Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: diagnostics-report
          path: diagnostics.json
```

### GitLab CI Example

```yaml
kuzu-memory-diagnostics:
  stage: test
  image: python:3.11
  script:
    - pip install kuzu-memory
    - kuzu-memory init
    - kuzu-memory doctor --format json --output diagnostics.json
  artifacts:
    reports:
      junit: diagnostics.json
    when: always
  allow_failure: true
```

### Jenkins Example

```groovy
pipeline {
    agent any

    stages {
        stage('Install') {
            steps {
                sh 'pip install kuzu-memory'
            }
        }

        stage('Initialize') {
            steps {
                sh 'kuzu-memory init'
            }
        }

        stage('Diagnostics') {
            steps {
                sh 'kuzu-memory doctor --format json --output diagnostics.json'
            }
        }

        stage('Publish Results') {
            steps {
                archiveArtifacts artifacts: 'diagnostics.json'
                publishHTML([
                    reportDir: '.',
                    reportFiles: 'diagnostics.json',
                    reportName: 'KuzuMemory Diagnostics'
                ])
            }
        }
    }

    post {
        always {
            script {
                def diagnostics = readJSON file: 'diagnostics.json'
                if (diagnostics.has_critical_errors) {
                    currentBuild.result = 'UNSTABLE'
                }
            }
        }
    }
}
```

### Pre-commit Hook Example

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run quick diagnostics before commit
kuzu-memory doctor --no-server-lifecycle --quiet

if [ $? -ne 0 ]; then
    echo "❌ KuzuMemory diagnostics failed"
    echo "Run 'kuzu-memory doctor' to see details"
    exit 1
fi

echo "✅ KuzuMemory diagnostics passed"
```

### Docker Health Check

```dockerfile
FROM python:3.11-slim

# Install KuzuMemory
RUN pip install kuzu-memory

# Initialize
RUN kuzu-memory init

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD kuzu-memory doctor health --json || exit 1

CMD ["kuzu-memory", "mcp", "serve"]
```

---

## Related Documentation

- [MCP Testing Guide](MCP_TESTING_GUIDE.md) - Complete MCP testing procedures
- [MCP Diagnostics](MCP_DIAGNOSTICS.md) - MCP-specific diagnostics
- [Troubleshooting Guide](developer/troubleshooting.md) - General troubleshooting
- [CLI Reference](developer/cli-reference.md) - Complete CLI documentation

---

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Total Checks**: 29 (11 configuration + 12 hooks + 7 server lifecycle)
