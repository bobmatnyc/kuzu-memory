# Setup Command Git Hooks Integration Design

**Research Date**: 2025-12-04
**Author**: Research Agent
**Status**: Design Complete
**Epic**: Setup Command Enhancement with Git Hooks

## Executive Summary

This research analyzes the current `kuzu-memory setup` command architecture and designs enhancements to automatically install git hooks and provide repair functionality. The design maintains backward compatibility while consolidating installation workflows into a single, intelligent command.

**Key Findings**:
- ✅ Current setup command is well-structured with 3-phase workflow
- ✅ Git hooks installation exists as separate `git install-hooks` command
- ✅ Installer architecture supports extension without breaking changes
- ✅ Integration can be added as Phase 2.5 in existing workflow
- ✅ Repair functionality already partially exists via `--force` flag

**Recommendation**: Add git hooks as **optional** (opt-in) feature in setup with `--with-git-hooks` flag to maintain conservative defaults and backward compatibility.

---

## 1. Current Setup Command Architecture

### 1.1 File Location
**Path**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/setup_commands.py`

### 1.2 Current Workflow (3 Phases)

```python
# PHASE 1: PROJECT DETECTION & INITIALIZATION
1. Detect project root (find_project_root())
2. Check if memory database exists (db_path.exists())
3. Initialize database if needed (ctx.invoke(init, force=force))

# PHASE 2: AI TOOL DETECTION & INSTALLATION
4. Detect installed AI systems (_detect_installed_systems())
5. Check health status (healthy, needs_repair, broken)
6. Install/update integration (_install_integration())
   - Forwards to install_unified.install_command()

# PHASE 3: VERIFICATION & COMPLETION
7. Build completion message
8. Display next steps to user
```

### 1.3 Existing Flags

| Flag | Purpose | Current Behavior |
|------|---------|------------------|
| `--skip-install` | Skip AI tool installation | Only runs Phase 1 (init) |
| `--integration <name>` | Target specific integration | Forces specific tool install |
| `--force` | Force reinstall | Re-runs even if exists (repair mode) |
| `--dry-run` | Preview changes | No file modifications |

### 1.4 Key Integration Points

```python
# Line 306-337: _install_integration() helper
def _install_integration(ctx, integration_name, project_root, force=False):
    """Install or update an AI tool integration."""
    from .install_unified import install_command

    ctx.invoke(
        install_command,
        integration=integration_name,
        force=force,
        dry_run=False,
        verbose=False,
    )
```

**Critical Insight**: Setup delegates to `install_unified.install_command()` which uses the installer registry pattern. Git hooks can follow the same pattern.

---

## 2. Git Hooks Installation Analysis

### 2.1 Current Implementation

**Location**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/git_commands.py`

**Command**: `kuzu-memory git install-hooks`

### 2.2 Git Hooks Architecture

```python
@git.command()
@click.option("--force", is_flag=True, help="Overwrite existing hooks")
def install_hooks(ctx: click.Context, force: bool) -> None:
    """Install git post-commit hook for automatic sync."""

    # 1. Find .git directory (searches up to 5 levels)
    git_dir = project_root / ".git"
    if not git_dir.exists():
        # Search parent directories
        for _ in range(5):
            if (current / ".git").exists():
                git_dir = current / ".git"
                break

    # 2. Create hooks directory
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    # 3. Write hook script
    hook_file = hooks_dir / "post-commit"
    hook_content = """#!/bin/sh
# KuzuMemory git post-commit hook
# Auto-sync commits to memory system

kuzu-memory git sync --incremental --quiet 2>/dev/null || true
"""
    hook_file.write_text(hook_content)
    hook_file.chmod(0o755)  # Make executable
```

### 2.3 Hook Functionality

**Purpose**: Automatically sync git commits to memory after each commit

**Hook Type**: `post-commit` (runs after successful commit)

**Command Executed**: `kuzu-memory git sync --incremental --quiet`

**Error Handling**: Silent failure with `|| true` (non-blocking)

### 2.4 Requirements Analysis

| Requirement | Met | Notes |
|-------------|-----|-------|
| Git repository detection | ✅ | Searches up to 5 parent directories |
| Idempotent (safe to run multiple times) | ⚠️ | Overwrites hook without backup unless `--force` |
| Backup existing hooks | ❌ | Directly overwrites without backup |
| Validation | ⚠️ | Checks for "KuzuMemory" in hook before uninstall |

**Critical Gap**: Hook installation doesn't create backups of existing hooks (unlike installer pattern which uses `create_backup()`).

---

## 3. Installer Architecture

### 3.1 Installer Registry Pattern

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/registry.py`

```python
class InstallerRegistry:
    def __init__(self):
        self._installers: dict[str, type[BaseInstaller]] = {}
        self._register_builtin_installers()

    def register(self, name: str, installer_class: type[BaseInstaller]):
        """Register an installer."""
        self._installers[name.lower()] = installer_class

    def get_installer(self, name: str, project_root: Path) -> BaseInstaller | None:
        """Get installer instance by name."""
        installer_class = self._installers.get(name.lower())
        if installer_class:
            return installer_class(project_root)
        return None
```

**Registered Installers**:
- `claude-code` → `ClaudeHooksInstaller` (MCP + hooks)
- `cursor` → `CursorInstaller` (MCP only)
- `vscode` → `VSCodeInstaller` (MCP only)
- `windsurf` → `WindsurfInstaller` (MCP only)
- `auggie` → `AuggieInstaller` (rules)
- `auggie-mcp` → `AuggieMCPInstaller` (MCP)

### 3.2 BaseInstaller Interface

**File**: `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/base.py`

```python
class BaseInstaller(ABC):
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.backup_dir: Path = self.project_root / ".kuzu-memory-backups"
        self.files_created: list[Path] = []
        self.files_modified: list[Path] = []
        self.backup_files: list[Path] = []
        self.warnings: list[str] = []

    @abstractmethod
    def ai_system_name(self) -> str: pass

    @abstractmethod
    def required_files(self) -> list[str]: pass

    @abstractmethod
    def description(self) -> str: pass

    def check_prerequisites(self) -> list[str]: ...

    def create_backup(self, file_path: Path) -> Path | None:
        """Create backup of existing file."""
        if not file_path.exists():
            return None

        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(file_path, backup_path)
        self.backup_files.append(backup_path)
        return backup_path

    def install(self, dry_run: bool = False, verbose: bool = False) -> InstallationResult: ...
```

**Key Features**:
- Automatic backup creation with timestamps
- Track files created/modified/backed up
- Prerequisite checking
- Dry-run support
- Verbose logging

### 3.3 Installation Result Pattern

```python
@dataclass
class InstallationResult:
    success: bool
    ai_system: str
    files_created: list[Path]
    files_modified: list[Path]
    backup_files: list[Path]
    message: str
    warnings: list[str]
```

**Benefits**:
- Structured result reporting
- Clear success/failure status
- Detailed file tracking
- Warning collection

---

## 4. Integration Design

### 4.1 Proposed Workflow Enhancement

**Option 1: Default Installation (Aggressive)**
```python
# PHASE 2.5: GIT HOOKS INSTALLATION (NEW)
# After AI tool installation, before verification
if not skip_install and git_repo_detected:
    rich_print("\n🪝 Installing git hooks...", style="cyan")
    _install_git_hooks(ctx, project_root, force=force)
```

**Option 2: Opt-In Installation (Conservative - RECOMMENDED)**
```python
# PHASE 2.5: GIT HOOKS INSTALLATION (NEW)
# Only install if explicitly requested
if with_git_hooks and git_repo_detected:
    rich_print("\n🪝 Installing git hooks...", style="cyan")
    _install_git_hooks(ctx, project_root, force=force)
elif not with_git_hooks and git_repo_detected:
    rich_print("\n💡 Tip: Add --with-git-hooks to auto-sync commits", style="dim")
```

**Recommendation**: Use **Option 2 (opt-in)** to maintain conservative defaults and avoid surprising users with automatic git hook installation.

### 4.2 New CLI Flags

```python
@click.option(
    "--with-git-hooks",
    is_flag=True,
    help="Install git post-commit hooks for auto-sync (requires git repo)",
)
@click.option(
    "--no-git-hooks",
    is_flag=True,
    help="Skip git hooks installation (default)",
)
```

**Usage Examples**:
```bash
# Install with git hooks
kuzu-memory setup --with-git-hooks

# Explicitly skip git hooks (default behavior)
kuzu-memory setup --no-git-hooks

# Setup for specific integration with git hooks
kuzu-memory setup --integration claude-code --with-git-hooks

# Repair installation including git hooks
kuzu-memory setup --force --with-git-hooks
```

### 4.3 Git Repository Detection

```python
def _detect_git_repository(project_root: Path) -> bool:
    """
    Detect if project is a git repository.

    Searches up to 5 parent directories for .git/

    Returns:
        True if git repository detected
    """
    current = project_root
    for _ in range(5):
        if (current / ".git").exists():
            return True
        if current == current.parent:
            break
        current = current.parent
    return False
```

### 4.4 Git Hooks Installation Helper

```python
def _install_git_hooks(
    ctx: click.Context,
    project_root: Path,
    force: bool = False
) -> None:
    """
    Install git post-commit hooks for automatic sync.

    Args:
        ctx: Click context
        project_root: Project root directory
        force: Force overwrite existing hooks
    """
    try:
        # Delegate to git install-hooks command
        from .git_commands import install_hooks as git_install_hooks_cmd

        ctx.invoke(git_install_hooks_cmd, force=force)

        rich_print("✅ Git hooks installed successfully", style="green")

    except SystemExit as e:
        # install-hooks may exit - capture and handle
        if e.code != 0:
            rich_print("⚠️  Git hooks installation failed", style="yellow")
            rich_print(
                "   You can install manually: kuzu-memory git install-hooks",
                style="dim"
            )
    except Exception as e:
        rich_print(f"⚠️  Git hooks warning: {e}", style="yellow")
        rich_print(
            "   You can install manually: kuzu-memory git install-hooks",
            style="dim"
        )
```

**Error Handling**: Non-blocking - setup continues even if git hooks fail.

---

## 5. Repair Functionality Design

### 5.1 Current Repair Behavior

The `--force` flag already provides basic repair functionality:

```python
# Line 148-160 in setup_commands.py
if not already_initialized or force:
    if dry_run:
        rich_print("\n[DRY RUN] Would initialize memory database at:", style="yellow")
    else:
        rich_print("\n⚙️  Initializing memory database...", style="cyan")
        ctx.invoke(init, force=force)

# Line 198-210: Reinstall logic
if needs_update or force:
    action = "Reinstalling" if force else "Updating"
    if dry_run:
        rich_print(f"\n[DRY RUN] Would {action.lower()} integration: {target_integration}")
    else:
        rich_print(f"\n⚙️  {action} {target_integration} integration...")
        _install_integration(ctx, target_integration, project_root, force=True)
```

**Current Repair Actions**:
1. Reinitialize database if needed
2. Reinstall AI tool integration
3. Skip repairs if already healthy (unless `--force`)

### 5.2 Enhanced Repair with Git Hooks

```python
# Enhanced Phase 2.5 with repair detection
if with_git_hooks and git_repo_detected:
    # Check if git hooks need repair
    git_dir = _find_git_directory(project_root)
    hook_file = git_dir / "hooks" / "post-commit"

    needs_git_repair = (
        not hook_file.exists() or  # Missing
        force  # Force reinstall
    )

    if needs_git_repair:
        action = "Installing" if not hook_file.exists() else "Reinstalling"
        rich_print(f"\n🪝 {action} git hooks...", style="cyan")
        _install_git_hooks(ctx, project_root, force=force)
    else:
        rich_print("\n✅ Git hooks already installed", style="green")
```

### 5.3 Repair Detection Logic

```python
def _detect_repair_needs(project_root: Path, with_git_hooks: bool) -> dict[str, bool]:
    """
    Detect what needs repair in the project.

    Returns:
        Dictionary of repair needs:
        - database_repair: True if database needs initialization/repair
        - integration_repair: True if AI integration needs repair
        - git_hooks_repair: True if git hooks need installation/repair
    """
    from ..utils.project_setup import get_project_db_path

    repair_needs = {
        "database_repair": False,
        "integration_repair": False,
        "git_hooks_repair": False,
    }

    # Check database
    db_path = get_project_db_path(project_root)
    if not db_path.exists():
        repair_needs["database_repair"] = True

    # Check integrations
    installed_systems = _detect_installed_systems(project_root)
    if any(s.health_status == "needs_repair" for s in installed_systems):
        repair_needs["integration_repair"] = True

    # Check git hooks (if requested)
    if with_git_hooks and _detect_git_repository(project_root):
        git_dir = _find_git_directory(project_root)
        hook_file = git_dir / "hooks" / "post-commit"
        if not hook_file.exists():
            repair_needs["git_hooks_repair"] = True

    return repair_needs
```

---

## 6. Backward Compatibility Analysis

### 6.1 Existing Commands (No Breaking Changes)

| Command | Status | Notes |
|---------|--------|-------|
| `kuzu-memory setup` | ✅ Works exactly as before | Default behavior unchanged |
| `kuzu-memory setup --force` | ✅ Works exactly as before | Still repairs database and integrations |
| `kuzu-memory git install-hooks` | ✅ Still works independently | Can be used manually |
| `kuzu-memory install <integration>` | ✅ Still works | Unified install command unchanged |

### 6.2 New Commands (Additive Only)

| Command | Purpose | Breaking Change |
|---------|---------|-----------------|
| `kuzu-memory setup --with-git-hooks` | Install with git hooks | ❌ No (opt-in) |
| `kuzu-memory setup --no-git-hooks` | Explicitly skip git hooks | ❌ No (already default) |
| `kuzu-memory setup --force --with-git-hooks` | Repair including git hooks | ❌ No (extends existing --force) |

### 6.3 Migration Path

**Users upgrading from v1.5.3 to v1.6.0**:

```bash
# Old workflow (still works)
kuzu-memory setup
kuzu-memory git install-hooks

# New workflow (single command)
kuzu-memory setup --with-git-hooks

# Old repair workflow (still works)
kuzu-memory setup --force
kuzu-memory git install-hooks --force

# New repair workflow (single command)
kuzu-memory setup --force --with-git-hooks
```

**No breaking changes**: All existing workflows continue to function.

---

## 7. CLI Interface Changes

### 7.1 Updated Help Text

```python
@click.command()
@click.option("--skip-install", is_flag=True, help="Skip AI tool installation (init only)")
@click.option("--integration", type=click.Choice([...]), help="Specific integration to install")
@click.option("--force", is_flag=True, help="Force reinstall even if already configured")
@click.option("--dry-run", is_flag=True, help="Preview changes without modifying files")
@click.option(
    "--with-git-hooks",
    is_flag=True,
    help="Install git post-commit hooks for auto-sync (requires git repo)"
)
@click.pass_context
def setup(
    ctx: click.Context,
    skip_install: bool,
    integration: str | None,
    force: bool,
    dry_run: bool,
    with_git_hooks: bool,
) -> None:
    """
    🚀 Smart setup - Initialize and configure KuzuMemory (RECOMMENDED).

    This is the ONE command to get KuzuMemory ready in your project.
    It intelligently handles both new setups and updates to existing installations.

    \b
    🎯 WHAT IT DOES:
      1. Detects project root automatically
      2. Initializes memory database (if needed)
      3. Auto-detects installed AI tools
      4. Installs/updates integrations intelligently
      5. Installs git hooks (if --with-git-hooks)
      6. Verifies everything is working

    \b
    🚀 EXAMPLES:
      # Smart setup (recommended - auto-detects everything)
      kuzu-memory setup

      # Setup with git hooks for auto-sync
      kuzu-memory setup --with-git-hooks

      # Setup for specific integration with git hooks
      kuzu-memory setup --integration claude-code --with-git-hooks

      # Initialize only (skip AI tool installation)
      kuzu-memory setup --skip-install

      # Force reinstall everything including git hooks
      kuzu-memory setup --force --with-git-hooks

      # Preview what would happen
      kuzu-memory setup --dry-run --with-git-hooks

    \b
    💡 TIP:
      For most users, just run 'kuzu-memory setup' with no arguments.
      Add --with-git-hooks to enable automatic commit syncing.

    \b
    ⚙️  ADVANCED USAGE:
      If you need granular control, you can still use:
      • kuzu-memory init                # Just initialize
      • kuzu-memory install <tool>      # Just install integration
      • kuzu-memory git install-hooks   # Just install git hooks
    """
```

### 7.2 Updated Completion Message

```python
# Build completion message with git hooks info
next_steps = []

if skip_install:
    next_steps.append("• Install AI tool: kuzu-memory install <integration>")

if with_git_hooks and git_hooks_installed:
    next_steps.append("✅ Git hooks installed - commits will auto-sync to memory")
elif not with_git_hooks and git_repo_detected:
    next_steps.append("💡 Enable auto-sync: kuzu-memory git install-hooks")

next_steps.extend([
    "• Store your first memory: kuzu-memory memory store 'Important info'",
    "• View status: kuzu-memory status",
    "• Get help: kuzu-memory help",
])

rich_panel(
    "Setup Complete! 🎉\n\n"
    f"📁 Project: {project_root}\n"
    f"🗄️  Database: {db_path}\n"
    f"📂 Memories: {memories_dir}\n"
    f"🪝 Git Hooks: {'✅ Installed' if git_hooks_installed else '❌ Not installed'}\n\n"
    "Next steps:\n" + "\n".join(next_steps),
    title="✅ KuzuMemory Ready",
    style="green",
)
```

---

## 8. Test Coverage Recommendations

### 8.1 Unit Tests

**File**: `tests/unit/cli/test_setup_commands.py`

```python
def test_setup_with_git_hooks_in_git_repo(tmp_path):
    """Test setup with --with-git-hooks in git repository."""
    # Initialize git repo
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Run setup with git hooks
    result = runner.invoke(setup, ["--with-git-hooks"], obj={"project_root": tmp_path})

    assert result.exit_code == 0
    assert "Git hooks installed" in result.output

    # Verify hook file exists
    hook_file = git_dir / "hooks" / "post-commit"
    assert hook_file.exists()
    assert hook_file.is_file()
    assert "kuzu-memory git sync" in hook_file.read_text()

def test_setup_with_git_hooks_not_git_repo(tmp_path):
    """Test setup with --with-git-hooks when not a git repository."""
    result = runner.invoke(setup, ["--with-git-hooks"], obj={"project_root": tmp_path})

    # Should succeed but warn about missing git
    assert result.exit_code == 0
    assert "Not a git repository" in result.output or "Git hooks skipped" in result.output

def test_setup_force_with_git_hooks_repairs_hook(tmp_path):
    """Test that --force --with-git-hooks reinstalls git hooks."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()

    # Create broken hook
    hook_file = hooks_dir / "post-commit"
    hook_file.write_text("#!/bin/sh\necho 'old hook'")

    # Run setup with force
    result = runner.invoke(
        setup,
        ["--force", "--with-git-hooks"],
        obj={"project_root": tmp_path}
    )

    assert result.exit_code == 0
    assert "kuzu-memory git sync" in hook_file.read_text()

def test_setup_dry_run_with_git_hooks(tmp_path):
    """Test --dry-run --with-git-hooks doesn't create files."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    result = runner.invoke(
        setup,
        ["--dry-run", "--with-git-hooks"],
        obj={"project_root": tmp_path}
    )

    assert result.exit_code == 0
    assert "Would install git hooks" in result.output or "[DRY RUN]" in result.output

    # Verify hook NOT created
    hook_file = git_dir / "hooks" / "post-commit"
    assert not hook_file.exists()

def test_setup_without_git_hooks_skips_installation(tmp_path):
    """Test default setup behavior skips git hooks."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    result = runner.invoke(setup, [], obj={"project_root": tmp_path})

    assert result.exit_code == 0

    # Hook should NOT be installed by default
    hook_file = git_dir / "hooks" / "post-commit"
    assert not hook_file.exists()
```

### 8.2 Integration Tests

**File**: `tests/integration/test_setup_complete.py`

```python
def test_complete_setup_workflow_with_git_hooks(tmp_project_dir):
    """Test complete setup workflow including git hooks."""
    # Initialize git
    subprocess.run(["git", "init"], cwd=tmp_project_dir, check=True)

    # Run setup with git hooks
    result = subprocess.run(
        ["kuzu-memory", "setup", "--with-git-hooks"],
        cwd=tmp_project_dir,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    # Verify database created
    db_path = tmp_project_dir / "kuzu-memories" / "memories.db"
    assert db_path.exists()

    # Verify git hook created
    hook_path = tmp_project_dir / ".git" / "hooks" / "post-commit"
    assert hook_path.exists()
    assert hook_path.stat().st_mode & 0o111  # Executable

    # Test hook executes successfully
    subprocess.run(["git", "commit", "--allow-empty", "-m", "test"], cwd=tmp_project_dir, check=True)
    # Hook should run silently (|| true prevents errors)
```

### 8.3 Doctor Command Integration

```python
# Add git hooks check to doctor diagnostics
async def check_git_hooks(self) -> DiagnosticResult:
    """Check git hooks installation status."""
    if not self._detect_git_repository():
        return DiagnosticResult(
            check="git_hooks",
            success=True,
            message="Not a git repository (git hooks not applicable)",
            severity="info"
        )

    hook_file = self._find_git_directory() / "hooks" / "post-commit"

    if not hook_file.exists():
        return DiagnosticResult(
            check="git_hooks",
            success=False,
            message="Git hooks not installed",
            severity="warning",
            fix_suggestion="Run: kuzu-memory setup --with-git-hooks"
        )

    # Verify hook content
    hook_content = hook_file.read_text()
    if "kuzu-memory git sync" not in hook_content:
        return DiagnosticResult(
            check="git_hooks",
            success=False,
            message="Git hook exists but doesn't appear to be KuzuMemory hook",
            severity="warning",
            fix_suggestion="Run: kuzu-memory git install-hooks --force"
        )

    return DiagnosticResult(
        check="git_hooks",
        success=True,
        message="Git hooks installed and configured correctly",
        severity="info"
    )
```

---

## 9. Implementation Complexity Estimate

### 9.1 Complexity Rating

| Component | Complexity | Effort (hrs) | Risk |
|-----------|------------|--------------|------|
| Git repository detection | Low | 1 | Low |
| Git hooks helper function | Low | 2 | Low |
| Setup command flag addition | Low | 1 | Low |
| Repair logic enhancement | Medium | 3 | Medium |
| CLI help text updates | Low | 1 | Low |
| Unit tests | Medium | 4 | Low |
| Integration tests | Medium | 3 | Low |
| Documentation updates | Low | 2 | Low |
| **TOTAL** | **Medium** | **17** | **Low-Medium** |

### 9.2 Risk Assessment

**Low Risks**:
- ✅ Flag addition is backward compatible
- ✅ Installer pattern is well-established
- ✅ Git hooks command already exists and tested

**Medium Risks**:
- ⚠️ Git detection across 5 parent levels could be slow
- ⚠️ Hook installation failure should not block setup
- ⚠️ Existing hooks might conflict (needs backup)

**Mitigation Strategies**:
1. Make git hooks non-blocking (already designed)
2. Add clear warning messages when git not detected
3. Implement backup for existing hooks (use installer pattern)
4. Add dry-run support for testing without side effects

### 9.3 Implementation Phases

**Phase 1: Core Functionality** (8 hours)
- [ ] Add `--with-git-hooks` flag to setup command
- [ ] Implement `_detect_git_repository()` helper
- [ ] Implement `_install_git_hooks()` helper
- [ ] Add git hooks to Phase 2.5 workflow
- [ ] Update completion message

**Phase 2: Testing** (7 hours)
- [ ] Unit tests for git detection
- [ ] Unit tests for setup with git hooks
- [ ] Unit tests for repair functionality
- [ ] Integration tests for complete workflow
- [ ] Doctor command integration

**Phase 3: Documentation** (2 hours)
- [ ] Update CLI help text
- [ ] Update README with new setup examples
- [ ] Add troubleshooting section for git hooks
- [ ] Update changelog

---

## 10. Recommended Implementation

### 10.1 Pseudocode

```python
# File: src/kuzu_memory/cli/setup_commands.py

@click.command()
@click.option("--skip-install", is_flag=True, help="Skip AI tool installation (init only)")
@click.option("--integration", type=click.Choice([...]), help="Specific integration to install")
@click.option("--force", is_flag=True, help="Force reinstall even if already configured")
@click.option("--dry-run", is_flag=True, help="Preview changes without modifying files")
@click.option(
    "--with-git-hooks",
    is_flag=True,
    help="Install git post-commit hooks for auto-sync (requires git repo)"
)
@click.pass_context
def setup(
    ctx: click.Context,
    skip_install: bool,
    integration: str | None,
    force: bool,
    dry_run: bool,
    with_git_hooks: bool,
) -> None:
    """Smart setup - Initialize and configure KuzuMemory (RECOMMENDED)."""

    # PHASE 1: PROJECT DETECTION & INITIALIZATION
    # ... (existing code unchanged)

    # PHASE 2: AI TOOL DETECTION & INSTALLATION
    # ... (existing code unchanged)

    # PHASE 2.5: GIT HOOKS INSTALLATION (NEW)
    git_hooks_installed = False
    git_repo_detected = _detect_git_repository(project_root)

    if with_git_hooks:
        if not git_repo_detected:
            rich_print(
                "\n⚠️  Git hooks requested but no git repository detected",
                style="yellow"
            )
            rich_print("   Skipping git hooks installation", style="dim")
        else:
            if dry_run:
                rich_print(
                    "\n[DRY RUN] Would install git hooks for auto-sync",
                    style="yellow"
                )
            else:
                rich_print("\n🪝 Installing git hooks...", style="cyan")
                git_hooks_installed = _install_git_hooks(
                    ctx, project_root, force=force
                )

    # PHASE 3: VERIFICATION & COMPLETION
    # ... (existing code with git hooks info added to completion message)


def _detect_git_repository(project_root: Path) -> bool:
    """Detect if project is a git repository (searches up to 5 parents)."""
    current = project_root
    for _ in range(5):
        if (current / ".git").exists():
            return True
        if current == current.parent:
            break
        current = current.parent
    return False


def _find_git_directory(project_root: Path) -> Path | None:
    """Find .git directory by searching up to 5 parent directories."""
    current = project_root
    for _ in range(5):
        git_dir = current / ".git"
        if git_dir.exists():
            return git_dir
        if current == current.parent:
            break
        current = current.parent
    return None


def _install_git_hooks(
    ctx: click.Context,
    project_root: Path,
    force: bool = False
) -> bool:
    """
    Install git post-commit hooks for automatic sync.

    Returns:
        True if hooks installed successfully, False otherwise
    """
    try:
        # Delegate to git install-hooks command
        from .git_commands import install_hooks as git_install_hooks_cmd

        ctx.invoke(git_install_hooks_cmd, force=force)
        rich_print("✅ Git hooks installed successfully", style="green")
        return True

    except SystemExit as e:
        if e.code != 0:
            rich_print("⚠️  Git hooks installation failed", style="yellow")
            rich_print(
                "   You can install manually: kuzu-memory git install-hooks",
                style="dim"
            )
        return False

    except Exception as e:
        rich_print(f"⚠️  Git hooks warning: {e}", style="yellow")
        rich_print(
            "   You can install manually: kuzu-memory git install-hooks",
            style="dim"
        )
        return False
```

### 10.2 File Changes Summary

**Files to Modify**:
1. `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/setup_commands.py`
   - Add `--with-git-hooks` flag
   - Add `_detect_git_repository()` helper
   - Add `_find_git_directory()` helper
   - Add `_install_git_hooks()` helper
   - Add Phase 2.5 to workflow
   - Update completion message

**Files to Create**:
1. `tests/unit/cli/test_setup_git_hooks.py`
   - Unit tests for git hooks integration

**Files to Update**:
1. `README.md` - Add setup examples with git hooks
2. `CHANGELOG.md` - Document new feature
3. `docs/troubleshooting.md` - Add git hooks troubleshooting

---

## 11. Backward Compatibility Verification

### 11.1 Existing User Workflows

| Workflow | Before | After | Compatible? |
|----------|--------|-------|-------------|
| Basic setup | `kuzu-memory setup` | Same | ✅ Yes (no git hooks by default) |
| Manual git hooks | `kuzu-memory git install-hooks` | Same | ✅ Yes (still works independently) |
| Force repair | `kuzu-memory setup --force` | Same | ✅ Yes (no git hooks unless requested) |
| Skip install | `kuzu-memory setup --skip-install` | Same | ✅ Yes (behavior unchanged) |

### 11.2 Breaking Change Analysis

**None identified**. All changes are additive:
- New flag: `--with-git-hooks` (opt-in)
- New helpers: internal implementation details
- New phase: conditional execution
- New tests: additional coverage

**Compatibility Score**: 100% - No breaking changes

---

## 12. Alternative Approaches Considered

### 12.1 Alternative 1: Always Install Git Hooks (Rejected)

**Approach**: Install git hooks by default if git repository detected.

**Pros**:
- Simpler CLI (no flag needed)
- Better out-of-box experience for git users
- Automatic sync without configuration

**Cons**:
- ❌ Surprising behavior (users don't expect automatic git hook installation)
- ❌ Could conflict with existing hooks
- ❌ Breaks principle of least surprise
- ❌ Makes setup less predictable

**Verdict**: Rejected - Too aggressive, violates user expectations

### 12.2 Alternative 2: Create GitHooksInstaller (Rejected)

**Approach**: Create a new `GitHooksInstaller` class following installer pattern.

**Pros**:
- Consistent with architecture
- Reusable across commands
- Better separation of concerns

**Cons**:
- ❌ Overkill for simple shell script
- ❌ Git hooks aren't an "AI system integration"
- ❌ Adds unnecessary abstraction
- ❌ Current `git install-hooks` command is sufficient

**Verdict**: Rejected - YAGNI (You Aren't Gonna Need It)

### 12.3 Alternative 3: Automatic Repair Detection (Considered)

**Approach**: Always detect repair needs and prompt user.

**Pros**:
- More interactive
- Better user guidance
- Clearer repair actions

**Cons**:
- ⚠️ Less suitable for CI/CD
- ⚠️ Requires user interaction
- ⚠️ Slower for scripted usage

**Verdict**: Considered but deferred - Keep `--force` for non-interactive repair, add interactive prompts as optional enhancement

---

## 13. Open Questions

### 13.1 Resolved Questions

1. **Should git hooks be installed by default?**
   - ❌ No - Use opt-in with `--with-git-hooks`

2. **Should existing hooks be backed up?**
   - ✅ Yes - Current `git install-hooks` should be enhanced to use installer backup pattern

3. **Should setup fail if git hooks fail?**
   - ❌ No - Non-blocking with warning message

4. **Should we support `--no-git-hooks` flag?**
   - ⚠️ Optional - Default behavior already skips, flag adds explicitness

### 13.2 Deferred Questions

1. **Should we add `--git-hooks-only` flag for repair scenarios?**
   - Status: Deferred to future enhancement
   - Reason: Users can run `kuzu-memory git install-hooks` directly

2. **Should doctor command repair git hooks automatically?**
   - Status: Deferred to doctor command enhancement
   - Reason: Doctor currently only reports, doesn't modify

3. **Should we support multiple git hooks (pre-commit, post-merge, etc.)?**
   - Status: Deferred to git sync enhancements
   - Reason: Current scope is post-commit only

---

## 14. Recommended Next Steps

### 14.1 Immediate Actions (v1.6.0)

1. **Implement core functionality** (Phase 1)
   - Add `--with-git-hooks` flag
   - Add git detection helpers
   - Add git hooks installation to workflow
   - Update completion message

2. **Add test coverage** (Phase 2)
   - Unit tests for new functionality
   - Integration tests for complete workflow
   - Edge case coverage (no git, broken hooks, etc.)

3. **Update documentation** (Phase 3)
   - CLI help text
   - README examples
   - Changelog entry

### 14.2 Future Enhancements (v1.7.0+)

1. **Enhanced git hooks installer**
   - Use installer pattern with backup
   - Support multiple hook types
   - Better conflict detection

2. **Doctor command integration**
   - Add git hooks health check
   - Suggest repair actions
   - Auto-repair capability

3. **Interactive setup wizard**
   - Prompt for git hooks during setup
   - Detect and explain existing hooks
   - Guide users through configuration

---

## 15. Conclusion

**Summary**:
The proposed design enhances the `kuzu-memory setup` command to optionally install git hooks while maintaining backward compatibility and following established architectural patterns. The opt-in approach (`--with-git-hooks`) respects user expectations while providing a streamlined workflow for users who want automatic commit syncing.

**Key Strengths**:
- ✅ Zero breaking changes
- ✅ Follows existing installer patterns
- ✅ Non-blocking error handling
- ✅ Clear user communication
- ✅ Comprehensive test coverage plan

**Implementation Risk**: **Low-Medium**

**Estimated Effort**: **17 hours** (1 week for single developer)

**Recommendation**: **Approve and implement** - This enhancement provides clear value with minimal risk.

---

## Appendix A: Code Examples

### Example 1: Basic Setup (No Git Hooks)

```bash
$ kuzu-memory setup

🚀 Smart Setup - Automated KuzuMemory Configuration

📁 Project detected: /Users/masa/Projects/my-project
✅ Memory database already initialized: /Users/masa/Projects/my-project/kuzu-memories/memories.db
🔍 Detecting installed AI tools...
   Found 1 existing installation(s)
   ✅ claude-code: healthy

✅ claude-code integration is up to date

✅ KuzuMemory Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Setup Complete! 🎉

📁 Project: /Users/masa/Projects/my-project
🗄️  Database: /Users/masa/Projects/my-project/kuzu-memories/memories.db
📂 Memories: /Users/masa/Projects/my-project/kuzu-memories
🪝 Git Hooks: ❌ Not installed

Next steps:
💡 Enable auto-sync: kuzu-memory git install-hooks
• Store your first memory: kuzu-memory memory store 'Important info'
• View status: kuzu-memory status
• Get help: kuzu-memory help
```

### Example 2: Setup with Git Hooks

```bash
$ kuzu-memory setup --with-git-hooks

🚀 Smart Setup - Automated KuzuMemory Configuration

📁 Project detected: /Users/masa/Projects/my-project
✅ Memory database already initialized
🔍 Detecting installed AI tools...
   ✅ claude-code: healthy

✅ claude-code integration is up to date

🪝 Installing git hooks...
✅ Git hooks installed successfully

✅ KuzuMemory Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Setup Complete! 🎉

📁 Project: /Users/masa/Projects/my-project
🗄️  Database: /Users/masa/Projects/my-project/kuzu-memories/memories.db
📂 Memories: /Users/masa/Projects/my-project/kuzu-memories
🪝 Git Hooks: ✅ Installed

Next steps:
✅ Git hooks installed - commits will auto-sync to memory
• Store your first memory: kuzu-memory memory store 'Important info'
• View status: kuzu-memory status
• Get help: kuzu-memory help
```

### Example 3: Repair with Git Hooks

```bash
$ kuzu-memory setup --force --with-git-hooks

🚀 Smart Setup - Automated KuzuMemory Configuration

📁 Project detected: /Users/masa/Projects/my-project
   Force flag set - will reinitialize

⚙️  Initializing memory database...
✅ Database initialized

🔍 Detecting installed AI tools...
   ⚠️ claude-code: needs_repair

⚙️  Reinstalling claude-code integration...
✅ Integration installed

🪝 Reinstalling git hooks...
✅ Git hooks installed successfully

✅ KuzuMemory Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Setup Complete! 🎉

All components have been repaired and reinstalled.
```

---

## Appendix B: Related Files

**Core Files**:
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/setup_commands.py` - Setup command
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/git_commands.py` - Git hooks installer
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/install_unified.py` - Unified install
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/base.py` - Base installer
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/installers/registry.py` - Installer registry

**Test Files**:
- `/Users/masa/Projects/kuzu-memory/tests/test_complete_setup.py` - Setup integration tests
- `/Users/masa/Projects/kuzu-memory/tests/unit/services/test_setup_service.py` - Setup unit tests

**Documentation**:
- `/Users/masa/Projects/kuzu-memory/CHANGELOG.md` - Version history
- `/Users/masa/Projects/kuzu-memory/README.md` - Main documentation

---

**End of Research Report**
