#!/usr/bin/env python3
"""
Example: Using MCPInstallerAdapter to install kuzu-memory MCP server.

This example demonstrates the various capabilities of the MCPInstallerAdapter,
which wraps the py-mcp-installer-service submodule.
"""

from pathlib import Path

from kuzu_memory.installers import (
    MCPInstallerAdapter,
    create_mcp_installer_adapter,
    is_mcp_installer_available,
)


def main() -> None:
    """Run MCP installer adapter examples."""
    print("=" * 60)
    print("MCP Installer Adapter Examples")
    print("=" * 60)

    # Check if submodule is available
    if not is_mcp_installer_available():
        print("\n❌ py-mcp-installer-service is not available!")
        print("   Please initialize the submodule:")
        print("   git submodule update --init --recursive")
        return

    print("\n✅ py-mcp-installer-service is available")

    # Example 1: Auto-detection
    print("\n" + "=" * 60)
    print("Example 1: Auto-detect platform and preview installation")
    print("=" * 60)

    adapter = MCPInstallerAdapter(
        project_root=Path.cwd(),
        dry_run=True,  # Preview only
        verbose=True,
    )

    print(f"\nDetected platform: {adapter.ai_system_name}")
    print(f"Platform info: {adapter.platform_info}")

    # Example 2: Install with dry-run
    print("\n" + "=" * 60)
    print("Example 2: Preview installation (dry-run)")
    print("=" * 60)

    result = adapter.install()
    print(f"\nSuccess: {result.success}")
    print(f"Message: {result.message}")
    print(f"AI System: {result.ai_system}")
    print(f"Files that would be modified: {result.files_modified}")

    # Example 3: Detect existing installation
    print("\n" + "=" * 60)
    print("Example 3: Detect existing installation")
    print("=" * 60)

    installed_system = adapter.detect_installation()
    print(f"\nAI System: {installed_system.ai_system}")
    print(f"Is Installed: {installed_system.is_installed}")
    print(f"Health Status: {installed_system.health_status}")
    print(f"Has MCP: {installed_system.has_mcp}")
    print(f"Files Present: {installed_system.files_present}")
    print(f"Files Missing: {installed_system.files_missing}")
    print(f"Details: {installed_system.details}")

    # Example 4: Run quick diagnostics
    print("\n" + "=" * 60)
    print("Example 4: Run quick diagnostics")
    print("=" * 60)

    try:
        diagnostics = adapter.run_diagnostics(full=False)
        print(f"\nStatus: {diagnostics['status']}")
        print(f"Platform: {diagnostics['platform']}")
        print(f"Checks Total: {diagnostics['checks_total']}")
        print(f"Checks Passed: {diagnostics['checks_passed']}")
        print(f"Checks Failed: {diagnostics['checks_failed']}")

        if diagnostics['issues']:
            print("\nIssues found:")
            for issue in diagnostics['issues']:
                print(f"  - [{issue['severity']}] {issue['message']}")
                if issue['fix_suggestion']:
                    print(f"    Fix: {issue['fix_suggestion']}")

        if diagnostics['recommendations']:
            print("\nRecommendations:")
            for rec in diagnostics['recommendations']:
                print(f"  - {rec}")
    except Exception as e:
        print(f"Diagnostics failed: {e}")

    # Example 5: Inspect configuration
    print("\n" + "=" * 60)
    print("Example 5: Inspect configuration")
    print("=" * 60)

    try:
        inspection = adapter.inspect_config()
        print(f"\nPlatform: {inspection['platform']}")
        print(f"Config Path: {inspection['config_path']}")
        print(f"Is Valid: {inspection['is_valid']}")
        print(f"Server Count: {inspection['server_count']}")
        print(f"Servers: {', '.join(inspection['server_names'])}")
        print(f"Summary: {inspection['summary']}")

        if inspection['issues']:
            print("\nValidation issues:")
            for issue in inspection['issues']:
                print(f"  - [{issue['severity']}] {issue['message']}")
    except Exception as e:
        print(f"Inspection failed: {e}")

    # Example 6: Platform-specific installation
    print("\n" + "=" * 60)
    print("Example 6: Force specific platform (Cursor)")
    print("=" * 60)

    try:
        cursor_adapter = MCPInstallerAdapter(
            project_root=Path.cwd(),
            platform="cursor",  # Force Cursor platform
            dry_run=True,
        )
        print(f"\nForced platform: {cursor_adapter.ai_system_name}")
        result = cursor_adapter.install()
        print(f"Installation preview: {result.message}")
    except Exception as e:
        print(f"Platform-specific installation failed: {e}")

    # Example 7: Factory function
    print("\n" + "=" * 60)
    print("Example 7: Using factory function")
    print("=" * 60)

    adapter_from_factory = create_mcp_installer_adapter(
        project_root=Path.cwd(),
        platform="claude-code",
        dry_run=True,
    )
    print(f"\nAdapter created via factory: {adapter_from_factory.ai_system_name}")

    # Example 8: Custom installation options
    print("\n" + "=" * 60)
    print("Example 8: Custom installation options")
    print("=" * 60)

    result = adapter.install(
        server_name="kuzu-memory-custom",
        command="python",
        args=["-m", "kuzu_memory.mcp.server"],
        env={"CUSTOM_VAR": "value"},
        description="Custom KuzuMemory installation",
        scope="project",
        method="python_module",
    )
    print(f"\nCustom installation preview: {result.message}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nNote: All examples ran in dry-run mode (no files modified)")
    print("To actually install, create adapter without dry_run=True")


if __name__ == "__main__":
    main()
