# MCP Installer Adapter - Usage Guide

The `MCPInstallerAdapter` bridges the vendored `py-mcp-installer-service` submodule with kuzu-memory's existing `BaseInstaller` interface.

## Overview

The adapter provides:
- **Auto-detection** of AI platforms (Cursor, Claude Code, VS Code, etc.)
- **Smart installation** method selection (uv run, pipx, direct)
- **Comprehensive diagnostics** via `MCPDoctor`
- **Configuration inspection** via `MCPInspector`
- **Unified interface** compatible with kuzu-memory's installer system

## Prerequisites

Ensure the submodule is initialized:

```bash
git submodule update --init --recursive
```

## Basic Usage

### Auto-Detection and Installation

```python
from pathlib import Path
from kuzu_memory.installers import MCPInstallerAdapter

# Auto-detect platform and install
adapter = MCPInstallerAdapter(project_root=Path.cwd())
result = adapter.install()

if result.success:
    print(f"✓ Installed to {result.ai_system}")
    print(f"  Files modified: {result.files_modified}")
else:
    print(f"✗ Installation failed: {result.message}")
```

### Force Specific Platform

```python
from py_mcp_installer import Platform

# Force installation for Cursor
adapter = MCPInstallerAdapter(
    project_root=Path.cwd(),
    platform=Platform.CURSOR
)
result = adapter.install()
```

### Using String Platform Name

```python
# String platform names are also supported
adapter = MCPInstallerAdapter(
    project_root=Path.cwd(),
    platform="cursor"  # "claude-code", "cursor", "auggie", etc.
)
```

### Custom Installation Options

```python
result = adapter.install(
    server_name="custom-server",
    command="python",
    args=["-m", "my_server"],
    env={"API_KEY": "secret"},
    description="My custom MCP server",
    scope="global",  # "project" or "global"
    method="python_module"  # "uv_run", "pipx", "direct", "python_module"
)
```

## Advanced Features

### Dry-Run Mode

Preview changes without modifying files:

```python
adapter = MCPInstallerAdapter(
    project_root=Path.cwd(),
    dry_run=True
)
result = adapter.install()
# No files are actually modified
```

### Detect Existing Installation

```python
installed_system = adapter.detect_installation()

print(f"AI System: {installed_system.ai_system}")
print(f"Is Installed: {installed_system.is_installed}")
print(f"Health Status: {installed_system.health_status}")
print(f"Has MCP: {installed_system.has_mcp}")
print(f"Files Present: {installed_system.files_present}")
print(f"Files Missing: {installed_system.files_missing}")
```

### Run Diagnostics

```python
# Quick diagnostics (config file checks only)
diagnostics = adapter.run_diagnostics(full=False)

# Full diagnostics (includes server connectivity tests)
diagnostics = adapter.run_diagnostics(full=True)

print(f"Status: {diagnostics['status']}")
print(f"Checks Total: {diagnostics['checks_total']}")
print(f"Checks Passed: {diagnostics['checks_passed']}")
print(f"Checks Failed: {diagnostics['checks_failed']}")

for issue in diagnostics['issues']:
    print(f"  - {issue['severity']}: {issue['message']}")
    if issue['fix_suggestion']:
        print(f"    Fix: {issue['fix_suggestion']}")
```

### Inspect Configuration

```python
inspection = adapter.inspect_config()

print(f"Platform: {inspection['platform']}")
print(f"Config Path: {inspection['config_path']}")
print(f"Is Valid: {inspection['is_valid']}")
print(f"Server Count: {inspection['server_count']}")
print(f"Servers: {', '.join(inspection['server_names'])}")

for issue in inspection['issues']:
    print(f"  - {issue['severity']}: {issue['message']}")
```

### Uninstall Server

```python
result = adapter.uninstall(server_name="kuzu-memory")

if result.success:
    print("✓ Uninstalled successfully")
else:
    print(f"✗ Uninstallation failed: {result.message}")
```

## Integration with Existing Installers

The adapter implements `BaseInstaller` and can be used with kuzu-memory's installer registry:

```python
from kuzu_memory.installers import InstallerRegistry

# Register the adapter
InstallerRegistry.register("mcp-adapter", MCPInstallerAdapter)

# Use via registry
installer = InstallerRegistry.get_installer("mcp-adapter", project_root=Path.cwd())
result = installer.install()
```

## Supported Platforms

The adapter supports all platforms from `py-mcp-installer-service`:

| Platform | String Name | Enum |
|----------|-------------|------|
| Claude Code | `"claude-code"` | `Platform.CLAUDE_CODE` |
| Claude Desktop | `"claude-desktop"` | `Platform.CLAUDE_DESKTOP` |
| Cursor | `"cursor"` | `Platform.CURSOR` |
| Auggie | `"auggie"` | `Platform.AUGGIE` |
| Windsurf | `"windsurf"` | `Platform.WINDSURF` |
| Codex | `"codex"` | `Platform.CODEX` |
| Gemini CLI | `"gemini-cli"` | `Platform.GEMINI_CLI` |
| Antigravity | `"antigravity"` | `Platform.ANTIGRAVITY` |

## Convenience Functions

### Factory Function

```python
from kuzu_memory.installers import create_mcp_installer_adapter

adapter = create_mcp_installer_adapter(
    project_root=Path.cwd(),
    platform="cursor",
    dry_run=True,
    verbose=True
)
```

### Check Availability

```python
from kuzu_memory.installers import is_mcp_installer_available

if is_mcp_installer_available():
    print("✓ py-mcp-installer-service is available")
else:
    print("✗ Submodule not initialized")
    print("  Run: git submodule update --init --recursive")
```

## Error Handling

The adapter gracefully handles errors and missing dependencies:

```python
try:
    adapter = MCPInstallerAdapter(project_root=Path.cwd())
except RuntimeError as e:
    # py-mcp-installer-service not available
    print(f"Error: {e}")
except ValueError as e:
    # Invalid platform string
    print(f"Invalid platform: {e}")
```

## Type Annotations

The adapter is fully typed and mypy-strict compliant:

```python
from kuzu_memory.installers import (
    MCPInstallerAdapter,
    InstallationResult,
    InstalledSystem,
)

adapter: MCPInstallerAdapter = MCPInstallerAdapter(project_root=Path.cwd())
result: InstallationResult = adapter.install()
system: InstalledSystem = adapter.detect_installation()
```

## Logging

The adapter uses Python's standard logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or use verbose mode
adapter = MCPInstallerAdapter(
    project_root=Path.cwd(),
    verbose=True
)
```

## Platform Information

Access detailed platform detection information:

```python
from py_mcp_installer import PlatformInfo

info: PlatformInfo = adapter.platform_info

print(f"Platform: {info.platform.value}")
print(f"Confidence: {info.confidence:.2%}")
print(f"Config Path: {info.config_path}")
print(f"CLI Available: {info.cli_available}")
print(f"Scope Support: {info.scope_support.value}")
```

## Best Practices

1. **Check availability** before using the adapter:
   ```python
   if not is_mcp_installer_available():
       raise RuntimeError("Submodule not initialized")
   ```

2. **Use dry-run** for testing:
   ```python
   adapter = MCPInstallerAdapter(project_root=Path.cwd(), dry_run=True)
   ```

3. **Run diagnostics** after installation:
   ```python
   result = adapter.install()
   if result.success:
       diagnostics = adapter.run_diagnostics(full=True)
       if diagnostics['status'] != 'healthy':
           print("Warning: Installation may have issues")
   ```

4. **Handle errors gracefully**:
   ```python
   try:
       result = adapter.install()
       if not result.success:
           print(f"Installation failed: {result.message}")
           for warning in result.warnings:
               print(f"  Warning: {warning}")
   except Exception as e:
       print(f"Unexpected error: {e}")
   ```

## Comparison with Direct py-mcp-installer Usage

### Using py-mcp-installer directly:
```python
from py_mcp_installer import MCPInstaller

installer = MCPInstaller.auto_detect()
result = installer.install_server(
    name="kuzu-memory",
    command="kuzu-memory",
    args=["mcp"],
    env={"KUZU_MEMORY_PROJECT_ROOT": str(Path.cwd())}
)
```

### Using MCPInstallerAdapter (BaseInstaller interface):
```python
from kuzu_memory.installers import MCPInstallerAdapter

adapter = MCPInstallerAdapter(project_root=Path.cwd())
result = adapter.install()  # Auto-configures env vars
```

The adapter provides:
- **Automatic environment variable setup** for kuzu-memory
- **Compatibility** with kuzu-memory's installer system
- **Consistent API** across all installer adapters
- **Type safety** with kuzu-memory's types

## Related Documentation

- [py-mcp-installer-service](../vendor/py-mcp-installer-service/README.md)
- [BaseInstaller Interface](../src/kuzu_memory/installers/base.py)
- [Installer Registry](../src/kuzu_memory/installers/registry.py)

---

**Last Updated**: 2025-12-11
**Version**: 1.6.2
