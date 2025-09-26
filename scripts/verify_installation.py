#!/usr/bin/env python
"""Verify KuzuMemory installation for Claude Code."""

import json
import subprocess
import sys
from pathlib import Path

def check_installation():
    """Check if KuzuMemory is properly installed."""
    print("KuzuMemory Claude Code Integration Verification")
    print("=" * 50)

    errors = []
    warnings = []
    successes = []

    # 1. Check if kuzu-memory CLI is accessible
    try:
        result = subprocess.run(
            ["kuzu-memory", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            successes.append(f"✓ CLI installed: {result.stdout.strip()}")
        else:
            errors.append("✗ CLI not working properly")
    except FileNotFoundError:
        errors.append("✗ kuzu-memory CLI not found in PATH")
    except Exception as e:
        errors.append(f"✗ CLI error: {e}")

    # 2. Check if database is initialized
    db_paths = [
        Path.cwd() / "kuzu-memories",
        Path.cwd() / ".kuzu-memory"
    ]
    db_found = False
    for db_path in db_paths:
        if db_path.exists():
            successes.append(f"✓ Database found: {db_path}")
            db_found = True
            break
    if not db_found:
        warnings.append("⚠ Database not initialized (run: kuzu-memory init)")

    # 3. Check Claude MPM configuration
    mpm_config = Path.cwd() / ".claude-mpm" / "config.json"
    if mpm_config.exists():
        try:
            with open(mpm_config) as f:
                config = json.load(f)
            if config.get("memory", {}).get("provider") == "kuzu-memory":
                successes.append("✓ Claude MPM configured for kuzu-memory")
            else:
                warnings.append("⚠ Claude MPM not using kuzu-memory provider")
        except Exception as e:
            warnings.append(f"⚠ Error reading MPM config: {e}")
    else:
        warnings.append("⚠ Claude MPM config not found")

    # 4. Check MCP configuration
    mcp_config = Path.cwd() / ".claude" / "kuzu-memory-mcp.json"
    if mcp_config.exists():
        try:
            with open(mcp_config) as f:
                config = json.load(f)
            if "kuzu-memory" in config.get("mcpServers", {}):
                successes.append("✓ MCP server configured")
            else:
                errors.append("✗ MCP server not configured properly")
        except Exception as e:
            errors.append(f"✗ Error reading MCP config: {e}")
    else:
        warnings.append("⚠ MCP configuration not found")

    # 5. Test MCP server
    try:
        # Import and test MCP server initialization
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from kuzu_memory.integrations.mcp_server import KuzuMemoryMCPServer, MCP_AVAILABLE

        if MCP_AVAILABLE:
            server = KuzuMemoryMCPServer()
            successes.append(f"✓ MCP server can initialize (project: {server.project_root.name})")
        else:
            warnings.append("⚠ MCP SDK not installed (pip install mcp)")
    except ImportError as e:
        warnings.append(f"⚠ MCP server import issue: {e}")
    except Exception as e:
        errors.append(f"✗ MCP server error: {e}")

    # 6. Test basic memory operations
    try:
        # Test enhance
        result = subprocess.run(
            ["kuzu-memory", "enhance", "test", "--format", "plain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            successes.append("✓ Memory enhance working")
    except:
        warnings.append("⚠ Memory enhance not tested")

    # Print results
    print("\nResults:")
    print("-" * 50)

    for success in successes:
        print(success)

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(warning)

    if errors:
        print("\nErrors:")
        for error in errors:
            print(error)

    # Summary
    print("\n" + "=" * 50)
    if errors:
        print("Status: ❌ Installation has errors")
        print("\nTo fix:")
        if "CLI not found" in str(errors):
            print("  1. Run: pip install kuzu-memory")
        if "MCP" in str(errors):
            print("  2. Run: kuzu-memory claude install")
        return 1
    elif warnings:
        print("Status: ⚠️  Installation working with warnings")
        print("\nOptional fixes:")
        if "Database not initialized" in str(warnings):
            print("  - Run: kuzu-memory init")
        if "MCP SDK" in str(warnings):
            print("  - Run: pip install mcp")
        return 0
    else:
        print("Status: ✅ Installation complete and verified!")
        return 0

if __name__ == "__main__":
    sys.exit(check_installation())