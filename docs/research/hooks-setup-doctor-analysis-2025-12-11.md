# KuzuMemory Hooks Implementation Analysis

**Date**: 2025-12-11
**Researcher**: Claude Research Agent
**Purpose**: Analyze current hooks implementation, setup service, and doctor command architecture

---

## Executive Summary

KuzuMemory implements a sophisticated hooks system for AI tool integrations with three distinct hook types:

1. **Claude Code Hooks**: Event-driven hooks (UserPromptSubmit, Stop, etc.) via `.claude/settings.local.json`
2. **Git Hooks**: Post-commit hooks for automatic memory synchronization
3. **Auggie Rules**: Markdown-based rules system (treated as "hooks" conceptually)

The setup service intelligently orchestrates initialization, while the doctor command provides comprehensive diagnostics. However, **hooks verification is currently missing** from both the setup workflow and doctor diagnostics.

---

## 1. Current Hooks Architecture

### 1.1 Hook Types and Locations

#### Claude Code Hooks (Event-Based)
- **Config Location**: `.claude/settings.local.json` or `~/.claude.json` (project-specific)
- **Implementation**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/claude_hooks.py`
- **Valid Events** (from line 31-41):
  ```python
  VALID_CLAUDE_CODE_EVENTS = {
      "UserPromptSubmit",   # User submits prompt
      "PreToolUse",         # Before tool use
      "PostToolUse",        # After tool use
      "Stop",               # Claude finishes
      "SubagentStop",       # Subagent stops
      "Notification",       # Notifications
      "SessionStart",       # Session start
      "SessionEnd",         # Session end
      "PreCompact",         # Before compaction
  }
  ```

- **Hook Commands** (from `hooks_commands.py`):
  - `kuzu-memory hooks enhance` - Enhance prompts with context (UserPromptSubmit)
  - `kuzu-memory hooks learn` - Learn from conversations (Stop event)
  - `kuzu-memory hooks session-start` - Track session start

#### Git Hooks (Post-Commit)
- **Location**: `.git/hooks/post-commit`
- **Implementation**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/git_commands.py` (lines 257-298)
- **Hook Script**:
  ```bash
  #!/bin/sh
  # KuzuMemory git post-commit hook
  # Auto-sync commits to memory system

  kuzu-memory git sync --incremental --quiet 2>/dev/null || true
  ```

- **Installation**: Via `kuzu-memory git install-hooks`
- **Status Check**: Via `kuzu-memory git status`

#### Auggie Rules (Markdown-Based)
- **Location**: `.augment/rules/` directory
- **Implementation**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/auggie_rules_v2.py`
- **Not technically "hooks"**: Uses markdown files for context injection

### 1.2 Hook Management CLI

**Unified Hooks Command Group**: `kuzu-memory hooks` (`/src/kuzu_memory/cli/hooks_commands.py`)

#### Available Commands:
1. **`hooks status`** (lines 49-120)
   - Shows installation status for all hook systems
   - Checks file presence for Claude Code and Auggie
   - Uses `HookSystem` enum for iteration

2. **`hooks install <system>`** (lines 123-261)
   - Installs hooks for specified system (claude-code, auggie)
   - Always updates existing (no `--force` flag needed)
   - Delegates to installers via registry

3. **`hooks list`** (lines 264-299)
   - Lists available hook systems with types

4. **`hooks enhance`** (lines 302-399)
   - Called by Claude Code UserPromptSubmit event
   - Reads JSON from stdin, enhances prompt with memories

5. **`hooks learn`** (lines 486-697)
   - Called by Claude Code Stop event
   - Extracts last assistant message, stores as memory

6. **`hooks session-start`** (lines 402-483)
   - Called by Claude Code SessionStart event
   - Records session initiation

---

## 2. Setup Service Architecture

### 2.1 Setup Service Location and Purpose

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/services/setup_service.py`

**Design Pattern**: Thin Service Wrapper (lines 23-43)
- Delegates to `project_setup` utilities
- Provides lifecycle management via `BaseService`
- Injects configuration from `ConfigService`

### 2.2 Current Setup Workflow

**Setup Command**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/setup_commands.py`

#### Phase Breakdown:

**PHASE 1: Project Detection & Initialization** (lines 117-171)
```
1. Detect project root via find_project_root()
2. Check if db_path exists (already_initialized)
3. Initialize database if needed (via ctx.invoke(init))
```

**PHASE 2: AI Tool Detection & Installation** (lines 174-268)
```
1. Detect installed systems via _detect_installed_systems()
2. Check health status (healthy, needs_repair)
3. Install/update integration if needed
```

**PHASE 2.5: Git Hooks Installation** (lines 270-291)
```
1. Check if --with-git-hooks flag provided
2. Detect git repository via _detect_git_repository()
3. Install git hooks via _install_git_hooks()
```

**PHASE 3: Verification & Completion** (lines 293-353)
```
1. Build completion message
2. Display status (db, git hooks, next steps)
```

### 2.3 Missing: Claude Code Hooks Verification

**CRITICAL GAP**: The setup command installs **git hooks** (Phase 2.5) but **does NOT verify or install Claude Code hooks** in the integration installation phase.

**Current Flow**:
```
setup --integration claude-code --with-git-hooks
  ↓
Phase 1: Initialize DB ✓
  ↓
Phase 2: Install claude-code integration (MCP only) ✓
  ↓
Phase 2.5: Install git hooks (if --with-git-hooks) ✓
  ↓
Phase 3: Verify and complete
  ❌ NO Claude Code hooks verification
```

**Expected Flow**:
```
setup --integration claude-code --with-git-hooks
  ↓
Phase 1: Initialize DB ✓
  ↓
Phase 2: Install claude-code integration (MCP + hooks) ✓
  ↓
Phase 2.5: Install git hooks (if --with-git-hooks) ✓
  ↓
Phase 3: Verify all hooks (Claude Code + git) ✓
```

### 2.4 SetupService Methods

**Key Methods** (from `setup_service.py`):

1. **`initialize_project()`** (lines 135-224)
   - Creates project structure
   - Initializes database
   - Returns setup result dict

2. **`verify_setup()`** (lines 252-319)
   - Checks memories directory exists
   - Checks database exists
   - Checks git repository
   - **Missing**: Hooks verification

3. **`initialize_hooks()`** (lines 357-377)
   - **PLACEHOLDER**: Returns False (not implemented)
   - Comment: "Placeholder for future git hook integration"

4. **`validate_project_structure()`** (lines 379-421)
   - Validates directories and permissions
   - **Missing**: Hooks validation

---

## 3. Doctor Command Architecture

### 3.1 Doctor Command Structure

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/doctor_commands.py`

**Design**: Service-Oriented with DiagnosticService (lines 7-17)

#### Main Doctor Command (lines 39-119)
- Flags: `--fix`, `--verbose`, `--output`, `--format`
- **NEW FLAGS**: `--hooks/--no-hooks`, `--server-lifecycle/--no-server-lifecycle`
- Delegates to subcommands or runs full diagnostics

#### Subcommands:

1. **`doctor diagnose`** (lines 122-260)
   - Full diagnostic suite
   - Uses `MCPDiagnostics.run_full_diagnostics()`
   - Supports auto-fix, hooks checking, server lifecycle
   - **Passes `check_hooks` parameter to diagnostics**

2. **`doctor mcp`** (lines 262-395)
   - MCP installation diagnostics
   - Uses `DiagnosticService.check_mcp_installation()`
   - Tests protocol compliance with `--full`

3. **`doctor connection`** (lines 398-471)
   - Database and MCP server connectivity
   - Uses `DiagnosticService.check_database_health()`

4. **`doctor health`** (lines 474-639)
   - Quick health check
   - Uses `MCPHealthChecker.check_health()`
   - Supports continuous monitoring mode

### 3.2 DiagnosticService Methods

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/services/diagnostic_service.py`

**Design Pattern**: Async Thin Orchestrator (lines 33-52)

#### Async Diagnostic Methods (7 methods):

1. **`run_full_diagnostics()`** (lines 136-208)
   - Aggregates all checks
   - Calls `MCPDiagnostics.run_full_diagnostics(check_hooks=True)`
   - Returns comprehensive report

2. **`check_configuration()`** (lines 210-258)
   - Config file validity
   - Required keys present
   - Paths accessible

3. **`check_database_health()`** (lines 260-328)
   - Database connectivity
   - Memory count, size, schema version

4. **`check_mcp_server_health()`** (lines 330-386)
   - MCP config exists and valid
   - Server entry present

5. **`check_git_integration()`** (lines 388-447)
   - Git availability
   - **Hooks installation check** (lines 433-436):
     ```python
     hooks_path = project_root / ".git" / "hooks" / "post-commit"
     hooks_installed = hooks_path.exists()
     ```

6. **`check_mcp_installation()`** (lines 449-546)
   - Uses `MCPInstallerAdapter`
   - Platform detection, command accessibility

7. **`get_system_info()`** (lines 548-605)
   - Version info, platform details

8. **`verify_dependencies()`** (lines 607-671)
   - Required packages installed

#### Sync Method:
- **`format_diagnostic_report()`** (lines 677-847)
  - Formats results as human-readable report

### 3.3 What Doctor Currently Checks

**Git Hooks**: ✅ YES
- `check_git_integration()` checks `.git/hooks/post-commit` exists (line 436)
- Reports in diagnostic output (lines 769-781)

**Claude Code Hooks**: ❌ NO
- Not checked in any diagnostic method
- Not included in `run_full_diagnostics()`
- Not part of `check_configuration()`

**Auggie Rules**: ❌ NO
- Not checked in diagnostics

---

## 4. Integration Points and Gaps

### 4.1 How Hooks Integrate with MCP Server

**MCP Server**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/server.py`
- Provides tools via stdio protocol
- No direct hooks integration

**Claude Code Hooks** → Call CLI commands:
- `UserPromptSubmit` → `kuzu-memory hooks enhance` (stdin/stdout)
- `Stop` → `kuzu-memory hooks learn` (stdin/stdout)

**Git Hooks** → Call CLI commands:
- `post-commit` → `kuzu-memory git sync --incremental --quiet`

### 4.2 Environment Variables

**For Claude Code Hooks** (from `claude_hooks.py` lines 106-109):
```python
"env": {
    "KUZU_MEMORY_PROJECT_ROOT": str(self.project_root),
    "KUZU_MEMORY_DB": str(db_path),
}
```

**For Hook Logging** (from `hooks_commands.py` line 322):
```python
log_dir = Path(os.getenv("KUZU_HOOK_LOG_DIR", "/tmp"))
```

### 4.3 Current Gaps

#### Gap 1: Setup Service Missing Hooks Verification
- **Location**: `setup_service.py` `initialize_hooks()` (line 357)
- **Status**: Placeholder returning False
- **Impact**: No automated hooks installation during setup

#### Gap 2: Setup Command Missing Hooks Phase
- **Location**: `setup_commands.py` Phase 2
- **Issue**: Only installs MCP, not hooks
- **Fix Needed**: Add hooks installation to integration installation

#### Gap 3: Doctor Missing Claude Code Hooks Check
- **Location**: `diagnostic_service.py` (no method exists)
- **Issue**: Only checks git hooks, not Claude Code hooks
- **Fix Needed**: Add `check_claude_code_hooks()` method

#### Gap 4: Incomplete Hooks Status
- **Location**: `hooks_commands.py` `hooks_status()` (lines 49-120)
- **Issue**: Only checks file presence, not configuration validity
- **Fix Needed**: Verify hook commands are configured in `.claude/settings.local.json`

---

## 5. Specific Recommendations

### 5.1 Setup Service Enhancements

**Add to `SetupService` (`setup_service.py`)**:

```python
def verify_claude_code_hooks(self, project_root: Path) -> dict[str, Any]:
    """
    Verify Claude Code hooks are properly configured.

    Returns:
        Dict with keys:
        - configured: bool
        - events_configured: List[str]
        - missing_events: List[str]
        - issues: List[str]
    """
    settings_path = project_root / ".claude" / "settings.local.json"

    if not settings_path.exists():
        return {
            "configured": False,
            "events_configured": [],
            "missing_events": ["UserPromptSubmit", "Stop"],
            "issues": ["settings.local.json not found"],
        }

    # Load and verify hooks configuration
    try:
        with open(settings_path) as f:
            settings = json.load(f)

        hooks = settings.get("hooks", {})
        configured_events = list(hooks.keys())

        # Check required events
        required_events = ["UserPromptSubmit", "Stop"]
        missing = [e for e in required_events if e not in configured_events]

        # Verify hook commands exist
        issues = []
        for event, config in hooks.items():
            if "command" not in config:
                issues.append(f"{event}: missing 'command' field")
            elif not config["command"].startswith("kuzu-memory"):
                issues.append(f"{event}: not using kuzu-memory command")

        return {
            "configured": len(missing) == 0 and len(issues) == 0,
            "events_configured": configured_events,
            "missing_events": missing,
            "issues": issues,
        }
    except Exception as e:
        return {
            "configured": False,
            "events_configured": [],
            "missing_events": required_events,
            "issues": [f"Failed to read settings: {e}"],
        }
```

**Update `verify_setup()` to include hooks**:

```python
def verify_setup(self) -> dict[str, Any]:
    """Verify current setup including hooks."""
    # ... existing checks ...

    # Check Claude Code hooks
    claude_hooks = self.verify_claude_code_hooks(self.project_root)
    if not claude_hooks["configured"]:
        issues.append("Claude Code hooks not configured")
        suggestions.append("Run 'kuzu-memory hooks install claude-code'")

    # Check git hooks
    git_hooks_path = project_root / ".git" / "hooks" / "post-commit"
    if not git_hooks_path.exists():
        issues.append("Git hooks not installed")
        suggestions.append("Run 'kuzu-memory git install-hooks' for auto-sync")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "claude_hooks": claude_hooks,
        "git_hooks_installed": git_hooks_path.exists(),
        # ... existing fields ...
    }
```

### 5.2 Setup Command Integration

**Modify `setup_commands.py` Phase 2** (after line 226):

```python
# Phase 2: AI Tool Detection & Installation
# ... existing code ...

# After installing integration, verify hooks
if target_integration == "claude-code":
    rich_print("\n🪝 Verifying Claude Code hooks...", style="cyan")

    # Check if hooks are configured
    hooks_status_result = _check_claude_hooks_status(project_root)

    if not hooks_status_result["configured"]:
        rich_print("   Claude Code hooks not configured", style="yellow")
        if click.confirm("Install Claude Code hooks?", default=True):
            _install_claude_hooks(ctx, project_root)
        else:
            rich_print("   Skipping hooks installation", style="dim")
    else:
        rich_print("   ✅ Claude Code hooks configured", style="green")
```

**Add helper functions**:

```python
def _check_claude_hooks_status(project_root: Path) -> dict[str, Any]:
    """Check Claude Code hooks configuration status."""
    from ..services import SetupService, ConfigService

    config_service = ConfigService(project_root)
    config_service.initialize()

    try:
        with SetupService(config_service) as setup:
            return setup.verify_claude_code_hooks(project_root)
    finally:
        config_service.cleanup()

def _install_claude_hooks(ctx: click.Context, project_root: Path) -> None:
    """Install Claude Code hooks via hooks command."""
    from .hooks_commands import install_hooks as hooks_install_cmd

    ctx.invoke(hooks_install_cmd, system="claude-code", dry_run=False, verbose=False, project=str(project_root))
```

### 5.3 Doctor Command Enhancements

**Add to `DiagnosticService` (`diagnostic_service.py`)**:

```python
async def check_claude_code_hooks(self) -> dict[str, Any]:
    """
    Check Claude Code hooks configuration and health.

    Verifies hooks are installed, configured correctly, and accessible.

    Returns:
        Claude Code hooks health with keys:
        - configured: bool
        - settings_path: str
        - events_configured: List[str]
        - missing_events: List[str]
        - command_accessible: bool
        - issues: List[str]
    """
    self._check_initialized()

    project_root = self._config_service.get_project_root()
    settings_path = project_root / ".claude" / "settings.local.json"

    issues = []
    configured = False
    events_configured = []
    missing_events = ["UserPromptSubmit", "Stop"]
    command_accessible = False

    # Check if settings file exists
    if not settings_path.exists():
        issues.append("Claude Code settings.local.json not found")
    else:
        try:
            # Load hooks configuration
            with open(settings_path) as f:
                settings = json.load(f)

            hooks = settings.get("hooks", {})
            events_configured = list(hooks.keys())

            # Check required events
            missing_events = [e for e in ["UserPromptSubmit", "Stop"] if e not in events_configured]

            if missing_events:
                issues.append(f"Missing hook events: {', '.join(missing_events)}")

            # Verify hook commands
            for event, config in hooks.items():
                if "command" not in config:
                    issues.append(f"{event}: missing 'command' field")
                elif not config["command"].startswith("kuzu-memory"):
                    issues.append(f"{event}: not using kuzu-memory command")

            configured = len(missing_events) == 0 and all(
                "command" in hooks[e] for e in ["UserPromptSubmit", "Stop"]
            )

        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in settings.local.json: {e}")
        except Exception as e:
            issues.append(f"Failed to read settings: {e}")

    # Check if kuzu-memory command is accessible
    import shutil
    command_accessible = shutil.which("kuzu-memory") is not None
    if not command_accessible:
        issues.append("kuzu-memory command not found in PATH")

    return {
        "configured": configured,
        "settings_path": str(settings_path),
        "events_configured": events_configured,
        "missing_events": missing_events,
        "command_accessible": command_accessible,
        "issues": issues,
    }
```

**Update `run_full_diagnostics()` to include Claude Code hooks**:

```python
async def run_full_diagnostics(self) -> dict[str, Any]:
    """Run comprehensive diagnostics including hooks."""
    # ... existing code ...

    # Add Claude Code hooks check
    claude_hooks_results = await self.check_claude_code_hooks()

    # Update all_healthy calculation
    all_healthy = (
        config_results.get("valid", False)
        and db_results.get("connected", False)
        and mcp_results.get("configured", False)
        and claude_hooks_results.get("configured", False)  # NEW
        and not report.has_critical_errors
    )

    return {
        "all_healthy": all_healthy,
        # ... existing fields ...
        "claude_code_hooks": claude_hooks_results,  # NEW
    }
```

**Update `format_diagnostic_report()` to include hooks section**:

```python
def format_diagnostic_report(self, results: dict[str, Any]) -> str:
    """Format diagnostic results including hooks status."""
    # ... existing sections ...

    # Claude Code Hooks Section
    lines.append("\n" + "=" * 70)
    lines.append("CLAUDE CODE HOOKS")
    lines.append("-" * 70)
    hooks = results.get("claude_code_hooks", {})
    hooks_configured = hooks.get("configured", False)
    lines.append(f"Status: {'✓ Configured' if hooks_configured else '✗ Not Configured'}")
    lines.append(f"Settings Path: {hooks.get('settings_path', 'N/A')}")
    lines.append(f"Events Configured: {', '.join(hooks.get('events_configured', []))}")
    if hooks.get("missing_events"):
        lines.append(f"Missing Events: {', '.join(hooks['missing_events'])}")
    lines.append(f"Command Accessible: {hooks.get('command_accessible', False)}")
    if hooks.get("issues"):
        lines.append("\nIssues:")
        for issue in hooks["issues"]:
            lines.append(f"  • {issue}")

    # ... rest of report ...
```

### 5.4 Priority Implementation Order

**HIGH PRIORITY** (Immediate impact):
1. Add `check_claude_code_hooks()` to DiagnosticService
2. Update `doctor diagnose` to include Claude Code hooks check
3. Update `format_diagnostic_report()` to display hooks status

**MEDIUM PRIORITY** (Setup enhancement):
4. Add `verify_claude_code_hooks()` to SetupService
5. Update `setup verify_setup()` to check hooks
6. Modify `setup` command to prompt for hooks installation

**LOW PRIORITY** (Polish):
7. Enhance `hooks status` to validate configuration (not just file presence)
8. Add `--verify-hooks` flag to setup command for explicit control

---

## 6. Files to Modify

### Immediate Changes (High Priority):

1. **`src/kuzu_memory/services/diagnostic_service.py`**
   - Add `check_claude_code_hooks()` method (async)
   - Update `run_full_diagnostics()` to call it
   - Update `format_diagnostic_report()` to include hooks section

2. **`src/kuzu_memory/cli/doctor_commands.py`**
   - Ensure `--hooks` flag is passed correctly to diagnostics
   - Update documentation to mention Claude Code hooks checking

### Medium Priority Changes:

3. **`src/kuzu_memory/services/setup_service.py`**
   - Add `verify_claude_code_hooks()` method
   - Update `verify_setup()` to include hooks checks
   - Implement `initialize_hooks()` (currently placeholder)

4. **`src/kuzu_memory/cli/setup_commands.py`**
   - Add hooks verification after integration installation (Phase 2)
   - Add helper functions `_check_claude_hooks_status()` and `_install_claude_hooks()`
   - Update completion message to show hooks status

### Low Priority Changes:

5. **`src/kuzu_memory/cli/hooks_commands.py`**
   - Enhance `hooks_status()` to validate config (not just file existence)
   - Add `--verify` flag for detailed configuration validation

---

## 7. Testing Considerations

### Test Coverage Needed:

1. **Unit Tests**:
   - `test_verify_claude_code_hooks()` - Various config states
   - `test_check_claude_code_hooks()` - Async diagnostic method
   - `test_format_diagnostic_report_with_hooks()` - Report formatting

2. **Integration Tests**:
   - `test_setup_with_hooks_installation()` - Full setup flow
   - `test_doctor_diagnose_hooks()` - Doctor command with hooks
   - `test_hooks_status_validation()` - Hooks status command

3. **Edge Cases**:
   - Missing `.claude/settings.local.json`
   - Partial hooks configuration (only UserPromptSubmit)
   - Invalid JSON in settings file
   - Hooks configured but kuzu-memory not in PATH

---

## 8. Architecture Strengths

### Well-Designed Aspects:

1. **Service-Oriented Architecture**:
   - Clear separation: CLI → Service → Utilities
   - Lifecycle management via BaseService
   - Dependency injection for testability

2. **Modular Hook Systems**:
   - Separate implementations for each platform
   - Registry pattern for installer discovery
   - Unified CLI interface via `hooks` group

3. **Comprehensive Doctor Command**:
   - Multiple diagnostic modes (full, mcp, connection, health)
   - Auto-fix capability
   - Multiple output formats (text, json, html)

4. **Git Hooks Integration**:
   - Already checked in `check_git_integration()`
   - Automated installation via `git install-hooks`
   - Status reporting via `git status`

---

## 9. Next Steps

### Immediate Actions:

1. **Implement Claude Code Hooks Diagnostics**:
   - Add `check_claude_code_hooks()` to DiagnosticService
   - Update doctor command to report hooks status
   - Add hooks section to diagnostic report

2. **Update Setup Flow**:
   - Add hooks verification after integration installation
   - Prompt user to install hooks if missing
   - Display hooks status in completion message

3. **Enhance Hooks Status Command**:
   - Validate configuration, not just file presence
   - Show which events are configured
   - Identify configuration issues

### Future Enhancements:

4. **Hooks Auto-Repair**:
   - Doctor `--fix` should repair broken hooks config
   - Setup should offer to fix invalid hooks

5. **Hooks Monitoring**:
   - Add hooks health to `doctor health` continuous mode
   - Track hook execution success/failure

6. **Documentation**:
   - Document hooks verification in setup guide
   - Add hooks troubleshooting to doctor docs

---

## Appendix A: Key Code Locations

### Hooks Implementation:
- **Claude Code Hooks**: `/src/kuzu_memory/installers/claude_hooks.py`
- **Hooks Commands**: `/src/kuzu_memory/cli/hooks_commands.py`
- **Git Commands**: `/src/kuzu_memory/cli/git_commands.py`
- **Hook Systems Enum**: `/src/kuzu_memory/cli/enums.py` (HookSystem)

### Setup:
- **Setup Service**: `/src/kuzu_memory/services/setup_service.py`
- **Setup Commands**: `/src/kuzu_memory/cli/setup_commands.py`

### Doctor:
- **Doctor Commands**: `/src/kuzu_memory/cli/doctor_commands.py`
- **Diagnostic Service**: `/src/kuzu_memory/services/diagnostic_service.py`

### Utilities:
- **Project Setup Utils**: `/src/kuzu_memory/utils/project_setup.py`
- **Installer Registry**: `/src/kuzu_memory/installers/registry.py`

---

## Appendix B: Hook Event Flow

### Claude Code UserPromptSubmit Event:
```
User submits prompt in Claude Code
    ↓
Claude Code triggers UserPromptSubmit hook
    ↓
Calls: kuzu-memory hooks enhance
    ↓
Reads stdin (JSON with prompt)
    ↓
Enhances prompt with memories (max 5)
    ↓
Outputs enhanced context to stdout
    ↓
Claude Code receives enhancement
    ↓
Appends to user's prompt
```

### Claude Code Stop Event:
```
Claude finishes response
    ↓
Claude Code triggers Stop hook
    ↓
Calls: kuzu-memory hooks learn
    ↓
Reads stdin (JSON with transcript_path)
    ↓
Finds last assistant message in transcript
    ↓
Stores message as memory (if not duplicate)
    ↓
Silent exit (logs to /tmp/kuzu_learn.log)
```

### Git Post-Commit Hook:
```
User commits changes
    ↓
Git triggers post-commit hook
    ↓
Calls: kuzu-memory git sync --incremental --quiet
    ↓
Syncs new commits to memory
    ↓
Updates sync state in config
    ↓
Silent exit (errors suppressed)
```

---

**End of Research Document**
