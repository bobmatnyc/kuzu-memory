#!/usr/bin/env python3
"""
Fix KuzuMemory MCP Server Configuration

This script fixes the outdated MCP server configuration in ~/.claude.json
by updating "args": ["mcp", "serve"] to "args": ["mcp"].

The issue stems from older installation scripts that used the deprecated
"mcp serve" command format. The current version only requires "mcp" as the
sole argument.

Usage:
    python scripts/fix_mcp_config.py [options]

Options:
    --dry-run       Show what would be changed without modifying the file
    --verbose       Enable detailed output
    --config PATH   Custom path to claude.json (default: ~/.claude.json)
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


class Colors:
    """Terminal color codes for output formatting."""
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    BOLD = '\033[1m'


class MCPConfigFixer:
    """Fixes outdated MCP server arguments in Claude Desktop configuration."""

    def __init__(self, config_path: Path = None, dry_run: bool = False, verbose: bool = False):
        """
        Initialize the fixer.

        Args:
            config_path: Path to claude.json file (default: ~/.claude.json)
            dry_run: Show changes without applying them
            verbose: Enable detailed output
        """
        self.config_path = config_path or Path.home() / ".claude.json"
        self.dry_run = dry_run
        self.verbose = verbose
        self.fixes_applied = 0

    def _log(self, message: str, level: str = "info"):
        """Print colored log message."""
        if level == "error":
            print(f"{Colors.RED}✗ {message}{Colors.RESET}")
        elif level == "success":
            print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")
        elif level == "warning":
            print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")
        elif level == "header":
            print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}")
            print(f"  {message}")
            print(f"{'='*60}{Colors.RESET}\n")
        elif self.verbose or level == "info":
            print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

    def _create_backup(self) -> Path:
        """
        Create a backup of the configuration file.

        Returns:
            Path to the backup file

        Raises:
            IOError: If backup creation fails
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_path.with_suffix(f".backup_{timestamp}")

        try:
            shutil.copy2(self.config_path, backup_path)
            self._log(f"Created backup: {backup_path}", "success")
            return backup_path
        except IOError as e:
            raise IOError(f"Failed to create backup: {e}")

    def _find_kuzu_memory_entries(self, config: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Find all kuzu-memory MCP server entries in the configuration.

        Args:
            config: The parsed configuration dictionary

        Returns:
            List of (server_name, server_config) tuples for kuzu-memory servers
        """
        entries = []

        # Check root-level mcpServers (older configuration format)
        mcp_servers = config.get("mcpServers", {})
        for server_name, server_config in mcp_servers.items():
            # Check if this is a kuzu-memory server
            if "kuzu-memory" in server_name.lower() or self._is_kuzu_memory_server(server_config):
                entries.append((server_name, server_config))

        # Check project-specific mcpServers (current configuration format)
        projects = config.get("projects", {})
        for project_path, project_config in projects.items():
            project_mcp_servers = project_config.get("mcpServers", {})
            for server_name, server_config in project_mcp_servers.items():
                # Check if this is a kuzu-memory server
                if "kuzu-memory" in server_name.lower() or self._is_kuzu_memory_server(server_config):
                    entries.append((server_name, server_config))

        return entries

    def _is_kuzu_memory_server(self, server_config: Dict[str, Any]) -> bool:
        """
        Determine if a server configuration is for kuzu-memory.

        Args:
            server_config: The server configuration dictionary

        Returns:
            True if this appears to be a kuzu-memory server
        """
        command = server_config.get("command", "")
        args = server_config.get("args", [])

        # Check command for kuzu-memory
        if isinstance(command, str) and "kuzu" in command.lower():
            return True

        # Check args for kuzu_memory module
        if isinstance(args, list):
            for arg in args:
                if isinstance(arg, str) and "kuzu_memory" in arg.lower():
                    return True

        return False

    def _needs_fix(self, server_config: Dict[str, Any]) -> bool:
        """
        Check if a server configuration needs to be fixed.

        Args:
            server_config: The server configuration dictionary

        Returns:
            True if the configuration has outdated args
        """
        args = server_config.get("args", [])

        # Check for the problematic pattern: ["mcp", "serve"]
        if isinstance(args, list) and len(args) >= 2:
            # Check for exact match or similar patterns
            if args[:2] == ["mcp", "serve"]:
                return True
            # Also check for variations
            if "mcp" in args and "serve" in args:
                return True

        return False

    def _fix_server_config(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix a server configuration by updating the args.

        Args:
            server_config: The server configuration dictionary to fix

        Returns:
            The fixed configuration dictionary
        """
        args = server_config.get("args", [])

        if not isinstance(args, list):
            self._log(f"Warning: args is not a list: {type(args)}", "warning")
            return server_config

        # Remove "serve" from args if it follows "mcp"
        new_args = []
        skip_next = False

        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue

            if arg == "mcp":
                new_args.append(arg)
                # Check if next arg is "serve" and skip it
                if i + 1 < len(args) and args[i + 1] == "serve":
                    skip_next = True
                    self.fixes_applied += 1
            else:
                new_args.append(arg)

        server_config["args"] = new_args
        return server_config

    def fix(self) -> bool:
        """
        Fix the MCP configuration file.

        Returns:
            True if successful (or no changes needed), False on error

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            json.JSONDecodeError: If configuration file is invalid JSON
            IOError: If file operations fail
        """
        self._log("KuzuMemory MCP Configuration Fixer", "header")

        # Step 1: Check if file exists
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"This is normal if you haven't configured Claude Desktop yet."
            )

        self._log(f"Configuration file: {self.config_path}", "info")

        # Step 2: Load configuration
        self._log("Loading configuration...", "info")
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in configuration file: {e}",
                e.doc,
                e.pos
            )

        # Step 3: Find kuzu-memory entries
        self._log("Searching for kuzu-memory MCP entries...", "info")
        entries = self._find_kuzu_memory_entries(config)

        if not entries:
            self._log("No kuzu-memory MCP entries found in configuration", "warning")
            self._log("Nothing to fix.", "info")
            return True

        self._log(f"Found {len(entries)} kuzu-memory MCP entry/entries", "success")

        # Step 4: Check which entries need fixing
        entries_to_fix = []
        for server_name, server_config in entries:
            if self._needs_fix(server_config):
                entries_to_fix.append((server_name, server_config))
                if self.verbose:
                    self._log(f"Entry '{server_name}' needs fixing", "info")
                    self._log(f"  Current args: {server_config.get('args')}", "info")

        if not entries_to_fix:
            self._log("All kuzu-memory entries are already correct!", "success")
            self._log("No changes needed.", "info")
            return True

        self._log(f"Found {len(entries_to_fix)} entry/entries that need fixing", "warning")

        # Step 5: Show dry-run output or create backup
        if self.dry_run:
            self._log("DRY RUN - No changes will be made", "warning")
            self._log("", "info")

            for server_name, server_config in entries_to_fix:
                old_args = server_config.get("args", [])
                temp_config = server_config.copy()
                self._fix_server_config(temp_config)
                new_args = temp_config.get("args", [])

                self._log(f"Entry '{server_name}':", "info")
                self._log(f"  Old args: {old_args}", "warning")
                self._log(f"  New args: {new_args}", "success")
                self._log("", "info")

            return True

        # Create backup before making changes
        self._log("Creating backup before making changes...", "info")
        try:
            backup_path = self._create_backup()
        except IOError as e:
            self._log(f"Failed to create backup: {e}", "error")
            self._log("Aborting to prevent data loss", "error")
            return False

        # Step 6: Apply fixes
        self._log("Applying fixes...", "info")
        self.fixes_applied = 0

        for server_name, server_config in entries_to_fix:
            old_args = server_config.get("args", []).copy()
            self._fix_server_config(server_config)
            new_args = server_config.get("args", [])

            if self.verbose:
                self._log(f"Fixed entry '{server_name}':", "success")
                self._log(f"  {old_args} → {new_args}", "info")

        # Step 7: Write updated configuration
        self._log("Writing updated configuration...", "info")
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
                f.write('\n')  # Add trailing newline
        except IOError as e:
            self._log(f"Failed to write configuration: {e}", "error")
            self._log(f"You can restore from backup: {backup_path}", "warning")
            return False

        # Step 8: Success message
        self._log("", "info")
        self._log("Configuration Fixed Successfully!", "header")
        self._log(f"Fixed {self.fixes_applied} argument(s) in {len(entries_to_fix)} entry/entries", "success")
        self._log(f"Backup saved to: {backup_path}", "info")
        self._log("", "info")
        self._log("Next steps:", "info")
        self._log("1. Restart Claude Desktop to load the updated configuration", "info")
        self._log("2. The kuzu-memory MCP server should now work correctly", "info")

        return True

    def validate(self) -> bool:
        """
        Validate the current configuration without making changes.

        Returns:
            True if configuration is valid and correct, False otherwise
        """
        self._log("Validating MCP Configuration", "header")

        if not self.config_path.exists():
            self._log(f"Configuration file not found: {self.config_path}", "error")
            return False

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            self._log(f"Invalid JSON: {e}", "error")
            return False

        self._log("Configuration file is valid JSON", "success")

        entries = self._find_kuzu_memory_entries(config)
        if not entries:
            self._log("No kuzu-memory MCP entries found", "warning")
            return True

        self._log(f"Found {len(entries)} kuzu-memory entry/entries", "success")

        all_correct = True
        for server_name, server_config in entries:
            args = server_config.get("args", [])
            needs_fix = self._needs_fix(server_config)

            self._log(f"Entry '{server_name}':", "info")
            self._log(f"  Args: {args}", "info")

            if needs_fix:
                self._log(f"  Status: NEEDS FIX", "warning")
                all_correct = False
            else:
                self._log(f"  Status: OK", "success")

        if all_correct:
            self._log("", "info")
            self._log("All configurations are correct!", "success")
        else:
            self._log("", "info")
            self._log("Some configurations need fixing", "warning")
            self._log("Run without --validate to fix them", "info")

        return all_correct


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix KuzuMemory MCP server configuration in ~/.claude.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix the configuration (creates backup automatically)
  python scripts/fix_mcp_config.py

  # Preview changes without modifying the file
  python scripts/fix_mcp_config.py --dry-run

  # Validate configuration without changes
  python scripts/fix_mcp_config.py --validate

  # Fix with verbose output
  python scripts/fix_mcp_config.py --verbose

  # Fix a custom configuration file
  python scripts/fix_mcp_config.py --config ~/custom/.claude.json

Notes:
  - A backup is created automatically before any changes
  - The script is idempotent (safe to run multiple times)
  - Use --dry-run to preview changes before applying
"""
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to claude.json file (default: ~/.claude.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying the file"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed output"
    )

    args = parser.parse_args()

    # Create fixer instance
    fixer = MCPConfigFixer(
        config_path=args.config,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    try:
        if args.validate:
            success = fixer.validate()
        else:
            success = fixer.fix()

        sys.exit(0 if success else 1)

    except FileNotFoundError as e:
        print(f"{Colors.RED}✗ {e}{Colors.RESET}")
        sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"{Colors.RED}✗ Configuration file contains invalid JSON:{Colors.RESET}")
        print(f"{Colors.RED}  {e}{Colors.RESET}")
        sys.exit(1)

    except PermissionError as e:
        print(f"{Colors.RED}✗ Permission denied: {e}{Colors.RESET}")
        print(f"{Colors.YELLOW}Try running with appropriate permissions{Colors.RESET}")
        sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.RESET}")
        sys.exit(1)

    except Exception as e:
        print(f"{Colors.RED}✗ Unexpected error: {e}{Colors.RESET}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
