# Setup Command Analysis

**Date**: 2025-12-04
**Ticket Context**: User mentioned "we should be able to just use the 'setup' command to fix installations"
**Research Question**: What does the `setup` command do and how does it relate to installation fixes?

---

## Executive Summary

**Key Findings**:

1. ✅ **`setup` command EXISTS** and is the **RECOMMENDED** installation method
2. ✅ **Auto-detects** installed systems and intelligently updates them
3. ❌ **Does NOT install git hooks** - this is separate functionality
4. ⚠️ **Gap identified**: Setup command focuses on MCP/Claude Code integration, but git hooks are a separate concern

**Recommendation**: The `setup` command is NOT a complete solution for all installation issues. It handles:
- Database initialization
- MCP server configuration
- AI tool integration detection and updates

But it does NOT handle:
- Git hooks installation (requires separate `kuzu-memory git install-hooks`)
- Git commit message enhancement
- Pre-commit hook setup

---

## 1. Setup Command Functionality

### 1.1 What `setup` Does

From CLI help output:
```
🚀 Smart setup - Initialize and configure KuzuMemory (RECOMMENDED).

This is the ONE command to get KuzuMemory ready in your project.
It intelligently handles both new setups and updates to existing installations.

🎯 WHAT IT DOES:
  1. Detects project root automatically
  2. Initializes memory database (if needed)
  3. Auto-detects installed AI tools
  4. Installs/updates integrations intelligently
  5. Verifies everything is working
```

### 1.2 Setup Command Options

```bash
kuzu-memory setup [OPTIONS]

Options:
  --skip-install          Skip AI tool installation (init only)
  --integration [...]     Specific integration to install (auto-detects if not specified)
  --force                 Force reinstall even if already configured
  --dry-run               Preview changes without modifying files
```

### 1.3 Implementation Analysis

**Source File**: `src/kuzu_memory/cli/setup_commands.py`

**Workflow**:

```
PHASE 1: PROJECT DETECTION & INITIALIZATION
├── Detect project root
├── Check if database already initialized
├── Initialize/update database (if needed or --force)
└── Handle initialization errors gracefully

PHASE 2: AI TOOL DETECTION & INSTALLATION
├── Skip if --skip-install flag set
├── Detect installed systems using _detect_installed_systems()
├── For each detected system:
│   ├── Check health status (healthy, needs_repair, broken)
│   ├── Identify which integration to update
│   └── Install/update if needed or --force
└── Guide user to install if nothing detected

PHASE 3: VERIFICATION & COMPLETION
├── Build completion message
├── Show next steps
└── Report file paths and status
```

**Key Functions**:
- `_detect_installed_systems(project_root)`: Scans for existing installations
- `_install_integration(ctx, integration_name, project_root, force)`: Delegates to `install_command`
- Auto-selects first detected system for repair/reinstall

---

## 2. Comparison: Setup vs Install vs Git Commands

### 2.1 Setup Command

**Purpose**: One-command initialization and configuration
**What it does**:
- ✅ Initialize database (`kuzu-memories/`)
- ✅ Detect installed AI tools (Claude Code, Cursor, VS Code, etc.)
- ✅ Install/update MCP server configuration
- ✅ Create `.claude/settings.local.json` with hooks config
- ✅ Auto-repair broken MCP configs across projects
- ❌ Does NOT install git hooks

**When to use**:
- First-time setup
- Updating existing installation
- Repairing broken MCP configurations
- Switching between AI tools

### 2.2 Install Command

**Purpose**: Install/update specific AI tool integration
**What it does**:
- ✅ Install MCP server for specific tool
- ✅ Configure tool-specific settings
- ✅ For `claude-code`: MCP + hooks configuration
- ✅ Auto-repair broken MCP configs
- ❌ Does NOT install git hooks

**When to use**:
- Installing specific integration manually
- Forcing reinstall of one tool
- Switching from one tool to another

### 2.3 Git Commands

**Purpose**: Git integration for commit message enhancement
**What it does**:
- ✅ Install git hooks (`prepare-commit-msg`)
- ✅ Enhance commit messages with context
- ✅ Sync commit history with memories
- ✅ Separate from MCP/Claude Code integration

**Commands**:
```bash
kuzu-memory git install-hooks    # Install git hooks
kuzu-memory git uninstall-hooks  # Remove git hooks
kuzu-memory git sync             # Sync commit history
```

**When to use**:
- Want git commit message enhancement
- Need to repair git hooks
- Updating git integration independently

---

## 3. Doctor Command Functionality

### 3.1 What `doctor` Does

From CLI help:
```
🩺 Diagnose and fix PROJECT issues.

Run comprehensive diagnostics to identify and fix issues with PROJECT-LEVEL
configurations only:
- Project memory database (kuzu-memories/)
- Claude Code MCP configuration (.claude/config.local.json)
- Claude Code hooks (if configured)
- MCP server lifecycle (startup, health, shutdown)

Does NOT check user-level configurations:
- Claude Desktop (use install commands instead)
- Global home directory configurations
```

### 3.2 Doctor Command Options

```bash
kuzu-memory doctor [OPTIONS] [COMMAND]

Options:
  --fix                           Auto-fix detected issues
  -v, --verbose                   Verbose output
  -o, --output PATH               Save report to file
  -f, --format [text|json|html]   Output format
  --hooks / --no-hooks            Run hooks diagnostics
  --server-lifecycle / --no-server-lifecycle
                                  Run server lifecycle diagnostics
  --project-root PATH             Project root directory

Commands:
  connection   Test database and MCP server connection
  diagnose     Run full diagnostic suite
  health       Quick health check
  mcp          MCP-specific diagnostics
```

### 3.3 Doctor vs Setup

| Feature | `doctor` | `setup` |
|---------|----------|---------|
| **Purpose** | Diagnose & fix issues | Initialize & configure |
| **Database** | Check health | Create/initialize |
| **MCP Config** | Validate & fix | Create/update |
| **Hooks** | Verify working | Install/update |
| **Auto-fix** | `--fix` flag | Always installs |
| **Reporting** | Detailed diagnostics | Brief status |
| **Git Hooks** | ❌ Not covered | ❌ Not covered |

---

## 4. Installation Workflow Gap Analysis

### 4.1 Current Workflow (Multiple Commands)

**Scenario 1: Fresh Installation**
```bash
# Step 1: Initialize and install integration
kuzu-memory setup --integration claude-code

# Step 2: Install git hooks (SEPARATE)
kuzu-memory git install-hooks
```

**Scenario 2: Repair Broken Installation**
```bash
# Option A: Use setup with --force
kuzu-memory setup --force

# Option B: Use doctor with --fix
kuzu-memory doctor --fix

# Still need: Install git hooks separately
kuzu-memory git install-hooks
```

### 4.2 User Expectation vs Reality

**User Statement**: "we should be able to just use the 'setup' command to fix installations"

**Reality Check**:
- ✅ `setup` DOES fix MCP/Claude Code integration issues
- ✅ `setup` DOES auto-detect and repair broken configs
- ❌ `setup` DOES NOT fix git hooks
- ❌ `setup` DOES NOT provide complete installation repair

**Gap**: Setup command is **incomplete** for full installation repair

### 4.3 Why Git Hooks Are Separate

**Design Decision Analysis**:

1. **Different Concerns**:
   - MCP/Claude Code: AI tool integration
   - Git Hooks: Version control enhancement
   - Not all users want both

2. **Optional Nature**:
   - Git hooks are optional
   - MCP integration is core
   - Separation allows choice

3. **Different Installers**:
   - `ClaudeHooksInstaller`: Handles MCP + Claude Code hooks
   - Git commands: Separate git integration layer

4. **Architecture**:
   ```
   setup command
   └── install_command
       └── ClaudeHooksInstaller.install()
           ├── MCP server config ✓
           ├── .claude/settings.local.json ✓
           ├── Claude Code hooks config ✓
           └── Git hooks ✗ (separate concern)
   ```

---

## 5. Recommendations

### 5.1 Short-Term Improvements

**Option 1: Enhanced Setup Command**
Add `--with-git-hooks` flag to setup command:
```bash
kuzu-memory setup --with-git-hooks
```

**Implementation**:
```python
# In setup_commands.py
@click.option("--with-git-hooks", is_flag=True, help="Also install git hooks")
def setup(..., with_git_hooks: bool):
    # ... existing setup logic ...

    if with_git_hooks and not skip_install:
        # After AI tool installation
        _install_git_hooks(ctx, project_root, dry_run)
```

**Option 2: Setup + Doctor Integration**
Make `setup --force` also check and fix git hooks:
```bash
kuzu-memory setup --force --fix-all
```

**Option 3: Unified Repair Command**
Create new command that truly fixes EVERYTHING:
```bash
kuzu-memory repair  # Fixes MCP + hooks + git hooks + database
```

### 5.2 Documentation Improvements

**Current State**: CLI help mentions setup as "ONE command" but doesn't clarify git hooks are separate

**Recommendations**:

1. **Update CLI Help**:
   ```
   🚀 QUICK START (RECOMMENDED):
     kuzu-memory setup                   # Smart setup (MCP + AI tools)
     kuzu-memory git install-hooks       # Optional: Git integration
   ```

2. **Add Setup Command Notes**:
   ```
   📝 NOTE:
     The setup command installs MCP server and AI tool integration.
     For git commit message enhancement, also run:
       kuzu-memory git install-hooks
   ```

3. **Create Installation Guide**:
   Document the complete installation workflow including both commands

### 5.3 Long-Term Architecture

**Proposal**: Unified Installation Service

```python
class UnifiedInstallationService:
    """Complete installation handling."""

    def install_all(self, options: InstallOptions) -> InstallResult:
        """Install everything: MCP + AI tools + git hooks"""
        results = []

        # Phase 1: Database
        results.append(self.init_database())

        # Phase 2: AI Tool Integration
        results.append(self.install_ai_tool())

        # Phase 3: Git Hooks (optional)
        if options.include_git_hooks:
            results.append(self.install_git_hooks())

        return self.aggregate_results(results)

    def repair_all(self, options: RepairOptions) -> RepairResult:
        """Repair everything: detect issues and fix"""
        issues = self.diagnose_all()
        fixes = []

        for issue in issues:
            if options.auto_fix:
                fixes.append(self.fix_issue(issue))

        return self.aggregate_fixes(fixes)
```

---

## 6. Conclusion

### 6.1 Summary of Findings

1. **Setup Command Exists**: It's the recommended installation method
2. **Intelligent Auto-Detection**: Detects and repairs existing installations
3. **Incomplete Coverage**: Does NOT handle git hooks
4. **Separate Concerns**: Git integration is architecturally separate
5. **Doctor Command**: Diagnoses issues but also doesn't cover git hooks

### 6.2 Answer to Original Question

**Q**: "Should we be able to just use the 'setup' command to fix installations?"

**A**: **Partially YES, but with caveats**:
- ✅ `setup` DOES fix MCP/Claude Code integration issues
- ✅ `setup --force` forces reinstallation of everything it handles
- ❌ `setup` does NOT fix git hooks (separate command needed)
- ❌ "just use the setup command" is **misleading** for complete installation

**Complete Installation Fix Requires**:
```bash
# Step 1: Fix MCP/AI tool integration
kuzu-memory setup --force

# Step 2: Fix git hooks (separate)
kuzu-memory git install-hooks
```

### 6.3 Actionable Next Steps

**For Users**:
1. Use `kuzu-memory setup` for MCP/AI tool installation
2. Use `kuzu-memory git install-hooks` separately for git integration
3. Use `kuzu-memory doctor --fix` for diagnostics and repairs

**For Development**:
1. Consider adding `--with-git-hooks` flag to setup command
2. Update documentation to clarify two-step installation
3. Potentially create unified `repair` command for complete fixes
4. Add clear messaging about git hooks being separate

---

## Files Analyzed

1. **`src/kuzu_memory/cli/setup_commands.py`** (339 lines)
   - Main setup command implementation
   - Auto-detection and installation logic
   - Integration with install command

2. **`src/kuzu_memory/cli/install_unified.py`** (350+ lines)
   - Unified install/uninstall commands
   - System detection logic
   - Integration registry

3. **`src/kuzu_memory/installers/claude_hooks.py`** (1183+ lines)
   - Claude Code hooks installer
   - MCP server configuration
   - Settings.local.json management
   - Legacy cleanup logic

4. **CLI Help Output**:
   - `kuzu-memory --help`
   - `kuzu-memory setup --help`
   - `kuzu-memory doctor --help`

---

## Research Metadata

- **Token Usage**: ~70,000 tokens (well within budget)
- **Files Read**: 3 source files (strategic sampling)
- **Search Strategy**: CLI help → implementation → installer details
- **Memory Efficiency**: Read file sections strategically, avoided full file loading
