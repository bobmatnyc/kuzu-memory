# Subservient Mode Hook Installation Analysis

**Date:** 2026-02-09
**Issue:** #18 - Skip hook installation in subservient mode
**Related:** #16 - Implement subservient mode for MPM integration
**Status:** Research Complete - Ready for Implementation

---

## Executive Summary

This research identifies the integration points for implementing subservient mode detection in kuzu-memory's hook installation system. The primary goal is to prevent duplicate hook installations when kuzu-memory is managed by a parent framework (like Claude MPM).

**Key Findings:**
- Hook installation happens in 3 locations: `setup_commands.py`, `hooks_commands.py`, and `claude_hooks.py`
- Existing config loading infrastructure (`ConfigLoader`) can be extended for `.kuzu-memory-config`
- Environment variable detection pattern already exists (`KUZU_MEMORY_*` prefix)
- Multiple detection methods should work together (env var → config file → flag)

---

## 1. Hook Installation Flow

### Current Architecture

```
User Command
    ↓
kuzu-memory setup [--skip-install]
    ↓
setup_commands.py::setup()
    ↓
    ├─→ init (database initialization)
    ├─→ _install_integration() (AI tool integrations)
    ├─→ ClaudeHooksInstaller.install() (Claude Code hooks)
    └─→ _install_git_hooks() (git post-commit hooks)
```

### Critical Files

#### 1. **`src/kuzu_memory/cli/setup_commands.py`** (Primary Entry Point)
- **Line 228-356:** AI tool installation phase
- **Line 323-356:** Claude Code hooks installation (Phase 2.25)
- **Line 357-379:** Git hooks installation (Phase 2.5)
- **Current Flag:** `--skip-install` (line 41-44) - skips ALL installations

**Integration Point:**
```python
# Line 228-230
if skip_install:
    rich_print("\n⏭️  Skipping AI tool installation (--skip-install)", style="yellow")
else:
    # Install hooks...
```

#### 2. **`src/kuzu_memory/cli/hooks_commands.py`** (Hook Installation Commands)
- **Line 270-408:** `install_hooks()` command - installs hooks for specific systems
- **Line 196-268:** `hooks_status()` - checks installation status
- **Current Options:** `--dry-run`, `--verbose`, `--project`

**Integration Point:**
```python
# Line 275 (install_hooks function signature)
def install_hooks(system: str, dry_run: bool, verbose: bool, project: str | None) -> None:
```

#### 3. **`src/kuzu_memory/installers/claude_hooks.py`** (Hook Installer Implementation)
- **Line 1187-1533:** `install()` method - actual hook installation logic
- **Line 293-312:** `check_prerequisites()` - validation before installation
- **Current Flags:** `force`, `dry_run`, `verbose`

**Integration Point:**
```python
# Line 1187 (install method signature)
def install(
    self,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    **kwargs: Any,
) -> InstallationResult:
```

---

## 2. Detection Methods (Priority Order)

### Priority 1: Environment Variable
**Variable:** `KUZU_MEMORY_MODE=subservient`

**Rationale:**
- Easy to set during installation: `KUZU_MEMORY_MODE=subservient uv tool install kuzu-memory`
- Follows existing `KUZU_MEMORY_*` prefix pattern (see `config_loader.py` line 31)
- No file system changes required
- Works in CI/CD and container environments

**Implementation Pattern (from `config_loader.py`):**
```python
import os

def is_subservient_mode() -> bool:
    """Check if running in subservient mode via environment variable."""
    mode = os.getenv("KUZU_MEMORY_MODE", "").lower()
    return mode in ("subservient", "managed", "delegated")
```

### Priority 2: Config File Detection
**File:** `.kuzu-memory-config` (project root)

**Format (YAML):**
```yaml
# .kuzu-memory-config
mode: subservient
managed_by: claude-mpm
version: "1.0"
```

**Rationale:**
- Persistent configuration (survives shell sessions)
- Discoverable during project analysis
- Can store additional metadata (managed_by, version)
- Follows existing config file patterns

**Integration with Existing ConfigLoader:**

`ConfigLoader` (line 34-42 in `config_loader.py`) already searches:
```python
self.default_config_paths = [
    Path.home() / ".kuzu-memory" / "config.yaml",  # User-level
    Path.home() / ".kuzu-memory" / "config.yml",
    Path("kuzu_memory_config.yaml"),                # Project-level (legacy)
    Path("kuzu_memory_config.yml"),
    Path(".kuzu_memory/config.yaml"),               # Legacy
    Path("/etc/kuzu_memory/config.yaml"),           # System-level
]
```

**New Search Path:**
```python
# Add to default_config_paths
Path(".kuzu-memory-config"),  # Subservient mode indicator (project root)
```

**Implementation Pattern:**
```python
from pathlib import Path
import yaml

def detect_subservient_config(project_root: Path) -> dict[str, str] | None:
    """Check for .kuzu-memory-config file indicating subservient mode."""
    config_path = project_root / ".kuzu-memory-config"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                if config.get("mode") in ("subservient", "managed"):
                    return {
                        "mode": config.get("mode"),
                        "managed_by": config.get("managed_by", "unknown"),
                    }
        except Exception as e:
            # Log but don't fail - treat as normal mode
            logger.debug(f"Failed to parse .kuzu-memory-config: {e}")
    return None
```

### Priority 3: Installation Flag
**Flag:** `--skip-install` (ALREADY EXISTS)

**Current Behavior (line 41-44, `setup_commands.py`):**
```python
@click.option(
    "--skip-install",
    is_flag=True,
    help="Skip AI tool installation (init only)",
)
```

**Enhancement:** Rename/alias to `--subservient` or `--managed-by`:
```python
@click.option(
    "--subservient",
    is_flag=True,
    help="Subservient mode: skip hook installation (managed by parent framework)",
)
@click.option(
    "--managed-by",
    type=str,
    help="Indicate parent framework managing hooks (e.g., 'claude-mpm')",
)
```

---

## 3. Recommended Integration Points

### A. Create Subservient Mode Detection Utility

**New File:** `src/kuzu_memory/utils/subservient.py`

```python
"""Subservient mode detection for managed installations."""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def is_subservient_mode(project_root: Optional[Path] = None) -> bool:
    """
    Check if kuzu-memory is running in subservient mode.

    Detection order:
    1. Environment variable: KUZU_MEMORY_MODE=subservient
    2. Config file: .kuzu-memory-config with mode=subservient

    Args:
        project_root: Project root to check for config file

    Returns:
        True if subservient mode detected, False otherwise
    """
    # Priority 1: Environment variable
    env_mode = os.getenv("KUZU_MEMORY_MODE", "").lower()
    if env_mode in ("subservient", "managed", "delegated"):
        logger.info(f"Subservient mode detected via KUZU_MEMORY_MODE={env_mode}")
        return True

    # Priority 2: Config file (if project_root provided)
    if project_root:
        config_data = get_subservient_config(project_root)
        if config_data:
            logger.info(
                f"Subservient mode detected via .kuzu-memory-config "
                f"(managed_by: {config_data.get('managed_by', 'unknown')})"
            )
            return True

    return False


def get_subservient_config(project_root: Path) -> Optional[Dict[str, str]]:
    """
    Read subservient mode configuration from .kuzu-memory-config.

    Args:
        project_root: Project root directory

    Returns:
        Dict with 'mode' and 'managed_by' keys, or None if not in subservient mode
    """
    config_path = project_root / ".kuzu-memory-config"
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            logger.warning(f".kuzu-memory-config is not a valid YAML dict")
            return None

        mode = config.get("mode", "").lower()
        if mode in ("subservient", "managed"):
            return {
                "mode": mode,
                "managed_by": config.get("managed_by", "unknown"),
                "version": config.get("version", "1.0"),
            }

    except Exception as e:
        logger.debug(f"Failed to parse .kuzu-memory-config: {e}")

    return None


def create_subservient_config(
    project_root: Path,
    managed_by: str = "unknown",
) -> Path:
    """
    Create .kuzu-memory-config file to mark subservient mode.

    Args:
        project_root: Project root directory
        managed_by: Name of parent framework managing this installation

    Returns:
        Path to created config file
    """
    config_path = project_root / ".kuzu-memory-config"

    config = {
        "mode": "subservient",
        "managed_by": managed_by,
        "version": "1.0",
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)

    logger.info(f"Created subservient config at {config_path} (managed_by={managed_by})")
    return config_path
```

### B. Integrate into `setup_commands.py`

**Location:** Line 228-356 (AI tool installation phase)

**Before:**
```python
if skip_install:
    rich_print("\n⏭️  Skipping AI tool installation (--skip-install)", style="yellow")
else:
    rich_print("\n🔍 Detecting installed AI tools...", style="cyan")
    # ... installation logic ...
```

**After:**
```python
from ..utils.subservient import is_subservient_mode, get_subservient_config

# Check for subservient mode before installation
if is_subservient_mode(project_root):
    config = get_subservient_config(project_root)
    managed_by = config.get("managed_by", "parent framework") if config else "parent framework"
    rich_print(
        f"\n📦 Subservient mode detected - hooks managed by {managed_by}",
        style="cyan"
    )
    rich_print("   Skipping hook installation (managed externally)", style="dim")
    skip_install = True  # Force skip

if skip_install:
    rich_print("\n⏭️  Skipping AI tool installation (--skip-install)", style="yellow")
else:
    rich_print("\n🔍 Detecting installed AI tools...", style="cyan")
    # ... installation logic ...
```

### C. Integrate into `hooks_commands.py::install_hooks()`

**Location:** Line 275-408

**Before:**
```python
def install_hooks(system: str, dry_run: bool, verbose: bool, project: str | None) -> None:
    """Install hooks for specified system."""
    # ... validation ...

    # Perform installation
    result = installer.install(dry_run=dry_run, verbose=verbose)
```

**After:**
```python
from ..utils.subservient import is_subservient_mode, get_subservient_config

def install_hooks(system: str, dry_run: bool, verbose: bool, project: str | None) -> None:
    """Install hooks for specified system."""
    # ... determine project_root ...

    # Check for subservient mode
    if is_subservient_mode(project_root):
        config = get_subservient_config(project_root)
        managed_by = config.get("managed_by", "parent framework") if config else "parent framework"
        console.print(
            f"\n📦 [cyan]Subservient Mode Detected[/cyan]\n"
            f"   Hooks are managed by: {managed_by}\n"
            f"   Skipping installation to avoid conflicts.\n\n"
            f"💡 To install hooks manually, unset KUZU_MEMORY_MODE or remove .kuzu-memory-config"
        )
        sys.exit(0)  # Graceful exit

    # ... validation ...

    # Perform installation
    result = installer.install(dry_run=dry_run, verbose=verbose)
```

### D. Integrate into `claude_hooks.py::install()`

**Location:** Line 1187-1533 (install method)

**Before:**
```python
def install(
    self,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    **kwargs: Any,
) -> InstallationResult:
    """Install Claude Code hooks for KuzuMemory."""
    try:
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        # Check prerequisites
        errors = self.check_prerequisites()
```

**After:**
```python
from ..utils.subservient import is_subservient_mode, get_subservient_config

def install(
    self,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    **kwargs: Any,
) -> InstallationResult:
    """Install Claude Code hooks for KuzuMemory."""
    try:
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        # Check for subservient mode
        if is_subservient_mode(self.project_root):
            config = get_subservient_config(self.project_root)
            managed_by = config.get("managed_by", "parent framework") if config else "parent framework"

            message = (
                f"Subservient mode detected - hooks managed by {managed_by}. "
                "Installation skipped to avoid conflicts."
            )

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=[],
                backup_files=[],
                message=message,
                warnings=["Hooks not installed - running in subservient mode"],
            )

        # Check prerequisites
        errors = self.check_prerequisites()
```

---

## 4. Testing Strategy

### Test Case 1: Environment Variable Detection
```bash
# Set subservient mode
export KUZU_MEMORY_MODE=subservient

# Attempt hook installation
kuzu-memory setup

# Expected Output:
# 📦 Subservient mode detected - hooks managed by parent framework
#    Skipping hook installation (managed externally)

# Verify no hooks installed
ls .claude/hooks/  # Should be empty or absent
```

### Test Case 2: Config File Detection
```bash
# Create subservient config
cat > .kuzu-memory-config <<EOF
mode: subservient
managed_by: claude-mpm
version: "1.0"
EOF

# Attempt hook installation
kuzu-memory setup

# Expected Output:
# 📦 Subservient mode detected - hooks managed by claude-mpm
#    Skipping hook installation (managed externally)

# Verify no hooks installed
test ! -d .claude/hooks && echo "✅ No hooks directory"
```

### Test Case 3: Normal Mode (Baseline)
```bash
# Ensure no subservient indicators
unset KUZU_MEMORY_MODE
rm -f .kuzu-memory-config

# Install hooks normally
kuzu-memory setup

# Expected Output:
# 🪝 Installing Claude Code hooks and MCP...
#   ✅ Claude Code hooks and MCP configured

# Verify hooks installed
ls .claude/hooks/  # Should contain hook files
cat .claude/settings.local.json  # Should have hooks config
```

### Test Case 4: CLI Flag Override
```bash
# Use --skip-install flag directly
kuzu-memory setup --skip-install

# Expected Output:
# ⏭️  Skipping AI tool installation (--skip-install)

# Verify no hooks
test ! -d .claude/hooks && echo "✅ No hooks directory"
```

---

## 5. Implementation Checklist

- [ ] Create `src/kuzu_memory/utils/subservient.py` with detection utilities
- [ ] Add `is_subservient_mode()` function
- [ ] Add `get_subservient_config()` function
- [ ] Add `create_subservient_config()` function
- [ ] Integrate detection into `setup_commands.py::setup()` (line 228)
- [ ] Integrate detection into `hooks_commands.py::install_hooks()` (line 275)
- [ ] Integrate detection into `claude_hooks.py::install()` (line 1187)
- [ ] Add unit tests for `subservient.py` functions
- [ ] Add integration tests for setup with subservient mode
- [ ] Update README.md with subservient mode documentation
- [ ] Update CLAUDE.md with subservient mode usage
- [ ] Test with environment variable: `KUZU_MEMORY_MODE=subservient`
- [ ] Test with config file: `.kuzu-memory-config`
- [ ] Test with CLI flag: `--skip-install`
- [ ] Verify no hooks installed in subservient mode
- [ ] Verify graceful exit messages

---

## 6. Documentation Updates

### README.md Section
```markdown
### Subservient Mode (Managed Installations)

If kuzu-memory is installed by a parent framework (like Claude MPM), you can prevent
duplicate hook installations by enabling **subservient mode**:

**Option 1: Environment Variable**
```bash
export KUZU_MEMORY_MODE=subservient
kuzu-memory setup  # Skips hook installation
```

**Option 2: Config File**
Create `.kuzu-memory-config` in your project root:
```yaml
mode: subservient
managed_by: claude-mpm
version: "1.0"
```

**Option 3: CLI Flag**
```bash
kuzu-memory setup --skip-install  # Skip all hook installations
```

In subservient mode:
- Database initialization still happens (memory storage)
- Hook installation is skipped (managed by parent)
- MCP tools remain available
- No hook conflicts occur
```

### CLAUDE.md Section
```markdown
## Subservient Mode Integration

KuzuMemory can detect when it's managed by a parent framework and will skip
hook installation automatically. This prevents duplicate hooks and conflicts.

Detection methods:
1. `KUZU_MEMORY_MODE=subservient` environment variable
2. `.kuzu-memory-config` file in project root
3. `--skip-install` flag during setup

Parent frameworks should set one of these indicators during installation.
```

---

## 7. Edge Cases and Considerations

### Edge Case 1: Partial Installation
**Scenario:** User manually installs hooks before enabling subservient mode

**Solution:**
- Add `uninstall_hooks()` command to remove existing hooks
- Detect existing hooks during subservient mode setup
- Warn user: "Existing hooks detected. Run `kuzu-memory uninstall-hooks` to remove."

### Edge Case 2: Mode Transition
**Scenario:** User switches from normal to subservient mode (or vice versa)

**Solution:**
- Subservient → Normal: Remove `.kuzu-memory-config`, run `kuzu-memory setup --force`
- Normal → Subservient: Create `.kuzu-memory-config`, run `kuzu-memory uninstall-hooks`

### Edge Case 3: Multiple Indicators
**Scenario:** Both env var and config file set with different values

**Priority:** Environment variable takes precedence (more explicit)

```python
# Priority order in is_subservient_mode():
# 1. KUZU_MEMORY_MODE env var (explicit override)
# 2. .kuzu-memory-config file (persistent config)
# 3. --skip-install flag (command-line)
```

### Edge Case 4: Invalid Config File
**Scenario:** `.kuzu-memory-config` exists but has syntax errors

**Solution:** Log warning, treat as normal mode (fail-safe)

```python
try:
    config = yaml.safe_load(f)
except yaml.YAMLError as e:
    logger.warning(f"Invalid .kuzu-memory-config: {e}. Treating as normal mode.")
    return None
```

---

## 8. Related Issues and Dependencies

### Dependencies
- **#16:** Implement subservient mode for MPM integration (parent issue)
- Existing config loading infrastructure (`ConfigLoader` in `config_loader.py`)
- Existing environment variable handling patterns

### Blocks
- None - this is a standalone feature enhancement

### Future Enhancements
- Add `kuzu-memory status --mode` to show current mode
- Add `kuzu-memory uninstall-hooks` command
- Add mode transition helpers: `kuzu-memory enable-subservient`, `kuzu-memory disable-subservient`

---

## 9. File Summary

### Files to Create
1. `src/kuzu_memory/utils/subservient.py` - Detection utilities
2. `tests/unit/test_subservient.py` - Unit tests
3. `tests/integration/test_subservient_mode.py` - Integration tests

### Files to Modify
1. `src/kuzu_memory/cli/setup_commands.py` - Add detection at line 228
2. `src/kuzu_memory/cli/hooks_commands.py` - Add detection at line 275
3. `src/kuzu_memory/installers/claude_hooks.py` - Add detection at line 1187
4. `README.md` - Add subservient mode documentation
5. `CLAUDE.md` - Add integration notes

### Estimated Lines of Code
- New utility file: ~150 lines
- Integration changes: ~30 lines total
- Tests: ~200 lines
- Documentation: ~100 lines

**Total:** ~480 lines of new/modified code

---

## 10. Implementation Priority

**Priority Level:** High (Critical for #16)

**Estimated Effort:** 2-3 hours
- 30 min: Create `subservient.py` utility
- 30 min: Integrate into 3 installation points
- 45 min: Write tests
- 30 min: Update documentation
- 15 min: Manual testing

**Risk Level:** Low
- No breaking changes (additive feature)
- Graceful fallback to normal mode
- Well-defined integration points

---

## Conclusion

**Ready for Implementation:** ✅

All integration points identified, detection methods defined, and implementation strategy clear. The feature can be implemented incrementally:

1. **Phase 1:** Create `subservient.py` utility (standalone)
2. **Phase 2:** Integrate into `setup_commands.py` (highest priority)
3. **Phase 3:** Integrate into `hooks_commands.py` and `claude_hooks.py`
4. **Phase 4:** Add tests and documentation

**Next Steps:**
1. Review this research document with team
2. Create implementation tasks in GitHub
3. Begin Phase 1 (utility creation)
4. Test with actual Claude MPM integration

**Related Files:**
- Research document: `docs/research/subservient-mode-hook-installation-analysis-2026-02-09.md`
- Issue tracker: GitHub #18
- Parent issue: GitHub #16
