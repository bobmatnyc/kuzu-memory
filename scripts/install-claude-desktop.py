#!/usr/bin/env python3
"""
KuzuMemory Claude Desktop MCP Installer

⚠️  DEPRECATION NOTICE ⚠️
This standalone script is DEPRECATED and will be REMOVED in v2.0.0 (planned: 2026 Q1).

Please use the integrated CLI command instead:
    kuzu-memory install claude-desktop [options]

For help with the new command:
    kuzu-memory install --help
    kuzu-memory list-installers

Migration Examples:
    OLD: python scripts/install-claude-desktop.py
    NEW: kuzu-memory install claude-desktop

    OLD: python scripts/install-claude-desktop.py --dry-run
    NEW: kuzu-memory install claude-desktop --dry-run

    OLD: python scripts/install-claude-desktop.py --memory-db ~/custom
    NEW: kuzu-memory install claude-desktop --memory-db ~/custom

REMOVAL TIMELINE: This script will be removed in v2.0.0 (2026 Q1)
This script still works for backward compatibility but is no longer maintained.
---

This script configures Claude Desktop to use KuzuMemory via the Model Context Protocol (MCP).
It automatically detects the pipx-installed kuzu-memory and sets up the JSON-RPC configuration.

Usage:
    python scripts/install-claude-desktop.py [options]

Options:
    --backup-dir PATH    Custom backup directory (default: ~/.kuzu-memory-backups)
    --memory-db PATH     Custom memory database path (default: ~/.kuzu-memory/memorydb)
    --force             Force installation even if configuration exists
    --uninstall         Remove KuzuMemory from Claude Desktop configuration
    --dry-run           Show what would be done without making changes
    --verbose           Enable verbose output
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class Colors:
    """Terminal color codes for pretty output."""
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    BOLD = '\033[1m'


class ClaudeDesktopInstaller:
    """Installer for KuzuMemory MCP integration with Claude Desktop."""

    def __init__(
        self,
        backup_dir: Optional[Path] = None,
        memory_db: Optional[Path] = None,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the installer.

        Args:
            backup_dir: Directory for config backups
            memory_db: Path to memory database
            force: Force installation even if config exists
            dry_run: Show what would be done without making changes
            verbose: Enable verbose output
        """
        self.backup_dir = backup_dir or Path.home() / ".kuzu-memory-backups"
        self.memory_db = memory_db or Path.home() / ".kuzu-memory" / "memorydb"
        self.force = force
        self.dry_run = dry_run
        self.verbose = verbose

        # Detect platform-specific paths
        self.config_path = self._get_claude_config_path()
        self.kuzu_command = None
        self.pipx_venv_path = None

    def _log(self, message: str, level: str = "info"):
        """Print colored log message."""
        if level == "error":
            print(f"{Colors.RED}✗ {message}{Colors.RESET}")
        elif level == "success":
            print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")
        elif level == "warning":
            print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")
        elif level == "header":
            print(f"\n{Colors.CYAN}{'='*60}")
            print(f"  {message}")
            print(f"{'='*60}{Colors.RESET}\n")
        elif self.verbose or level == "info":
            print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

    def _get_claude_config_path(self) -> Path:
        """Get the Claude Desktop configuration file path based on the platform."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif system == "Linux":
            # Check both possible locations
            xdg_config = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
            return Path(xdg_config) / "Claude" / "claude_desktop_config.json"
        elif system == "Windows":
            appdata = os.getenv("APPDATA")
            if appdata:
                return Path(appdata) / "Claude" / "claude_desktop_config.json"
            return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        else:
            raise OSError(f"Unsupported operating system: {system}")

    def _find_kuzu_memory(self) -> Tuple[Optional[str], Optional[Path]]:
        """
        Find the kuzu-memory installation.

        Returns:
            Tuple of (command_path, pipx_venv_path) or (None, None) if not found
        """
        # First, try to find via pipx
        try:
            # Check if pipx is installed
            pipx_result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                check=False
            )

            if pipx_result.returncode == 0:
                pipx_data = json.loads(pipx_result.stdout)
                venvs = pipx_data.get("venvs", {})

                if "kuzu-memory" in venvs:
                    venv_info = venvs["kuzu-memory"]

                    # Get the actual binary path
                    apps = venv_info["metadata"]["main_package"]["apps"]
                    app_paths = venv_info["metadata"]["main_package"]["app_paths"]

                    if apps and app_paths:
                        # First app should be kuzu-memory
                        app_name = apps[0]

                        # Extract the path from the first app_paths entry
                        # The structure is [{"__Path__": "/path/to/app", "__type__": "Path"}]
                        if isinstance(app_paths, list) and app_paths:
                            app_path_dict = app_paths[0]
                            app_path = app_path_dict.get("__Path__") if isinstance(app_path_dict, dict) else str(app_path_dict)
                        else:
                            app_path = str(app_paths)

                        self._log(f"Found pipx installation: {app_name} at {app_path}", "info")

                        # Get the Python interpreter from the venv
                        # The app path is typically: ~/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory
                        # We need: ~/.local/pipx/venvs/kuzu-memory
                        pipx_venv_dir = Path(app_path).parent.parent
                        return str(app_path), pipx_venv_dir
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
            if self.verbose:
                self._log(f"Could not detect pipx installation: {e}", "warning")

        # Fall back to checking PATH
        try:
            result = subprocess.run(
                ["which", "kuzu-memory"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                kuzu_path = result.stdout.strip()
                self._log(f"Found kuzu-memory in PATH: {kuzu_path}", "info")
                return kuzu_path, None
        except subprocess.SubprocessError:
            pass

        # Check common installation directories
        common_paths = [
            Path.home() / ".local" / "bin" / "kuzu-memory",
            Path("/usr/local/bin/kuzu-memory"),
            Path("/opt/homebrew/bin/kuzu-memory"),
        ]

        for path in common_paths:
            if path.exists():
                self._log(f"Found kuzu-memory at: {path}", "info")
                return str(path), None

        return None, None

    def _backup_config(self, config_path: Path) -> Optional[Path]:
        """
        Create a backup of the existing configuration.

        Args:
            config_path: Path to the configuration file

        Returns:
            Path to the backup file or None if no backup was needed
        """
        if not config_path.exists():
            return None

        if self.dry_run:
            self._log(f"Would backup: {config_path}", "info")
            return None

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        # Copy the file
        shutil.copy2(config_path, backup_path)
        self._log(f"Created backup: {backup_path}", "success")

        return backup_path

    def _create_mcp_config(self) -> Dict[str, Any]:
        """
        Create the MCP server configuration for KuzuMemory.

        Returns:
            Dictionary with MCP server configuration
        """
        # Determine the best command to use
        if self.pipx_venv_path:
            # Use the pipx virtual environment's Python
            python_path = self.pipx_venv_path / "bin" / "python"
            if not python_path.exists():
                # Windows path
                python_path = self.pipx_venv_path / "Scripts" / "python.exe"

            return {
                "command": str(python_path),
                "args": ["-m", "kuzu_memory.mcp.run_server"],
                "env": {
                    "KUZU_MEMORY_DB": str(self.memory_db),
                    "KUZU_MEMORY_MODE": "mcp"
                }
            }
        elif self.kuzu_command:
            # Use the kuzu-memory command directly with MCP mode
            return {
                "command": self.kuzu_command,
                "args": ["mcp", "serve"],
                "env": {
                    "KUZU_MEMORY_DB": str(self.memory_db),
                    "KUZU_MEMORY_MODE": "mcp"
                }
            }
        else:
            # Fallback to assuming kuzu-memory is in PATH
            return {
                "command": "kuzu-memory",
                "args": ["mcp", "serve"],
                "env": {
                    "KUZU_MEMORY_DB": str(self.memory_db),
                    "KUZU_MEMORY_MODE": "mcp"
                }
            }

    def _update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the Claude Desktop configuration with KuzuMemory MCP server.

        Args:
            config: Existing configuration dictionary

        Returns:
            Updated configuration dictionary
        """
        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Check if kuzu-memory already exists
        if "kuzu-memory" in config["mcpServers"] and not self.force:
            self._log("KuzuMemory MCP server already configured", "warning")
            self._log("Use --force to overwrite existing configuration", "info")
            return config

        # Add or update the kuzu-memory server
        config["mcpServers"]["kuzu-memory"] = self._create_mcp_config()

        return config

    def install(self) -> bool:
        """
        Install KuzuMemory MCP integration for Claude Desktop.

        Returns:
            True if installation was successful, False otherwise
        """
        self._log("KuzuMemory Claude Desktop MCP Installer", "header")

        # Step 1: Find kuzu-memory installation
        self._log("Detecting kuzu-memory installation...", "info")
        self.kuzu_command, self.pipx_venv_path = self._find_kuzu_memory()

        if not self.kuzu_command and not self.pipx_venv_path:
            self._log("KuzuMemory is not installed", "error")
            self._log("Please install it first with: pipx install kuzu-memory", "info")
            return False

        # Step 2: Check Claude Desktop configuration
        self._log(f"Claude Desktop config path: {self.config_path}", "info")

        if not self.config_path.parent.exists():
            if self.dry_run:
                self._log(f"Would create directory: {self.config_path.parent}", "info")
            else:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                self._log(f"Created directory: {self.config_path.parent}", "success")

        # Step 3: Load or create configuration
        config = {}
        if self.config_path.exists():
            self._log("Found existing Claude Desktop configuration", "info")

            # Create backup
            backup_path = self._backup_config(self.config_path)

            # Load existing config
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                self._log(f"Failed to parse existing config: {e}", "error")
                if backup_path:
                    self._log(f"Restore from backup: {backup_path}", "info")
                return False
        else:
            self._log("Creating new Claude Desktop configuration", "info")

        # Step 4: Update configuration
        config = self._update_config(config)

        # Step 5: Write configuration
        if self.dry_run:
            self._log("Dry run - would write configuration:", "info")
            print(json.dumps(config, indent=2))
        else:
            try:
                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                self._log(f"Updated configuration: {self.config_path}", "success")
            except IOError as e:
                self._log(f"Failed to write configuration: {e}", "error")
                return False

        # Step 6: Create memory database directory
        if not self.memory_db.parent.exists():
            if self.dry_run:
                self._log(f"Would create memory database directory: {self.memory_db.parent}", "info")
            else:
                self.memory_db.parent.mkdir(parents=True, exist_ok=True)
                self._log(f"Created memory database directory: {self.memory_db.parent}", "success")

        # Success message
        self._log("Installation Complete!", "header")
        self._log("KuzuMemory MCP server has been configured for Claude Desktop", "success")
        self._log("", "info")
        self._log("Next steps:", "info")
        self._log("1. Restart Claude Desktop to load the new configuration", "info")
        self._log("2. KuzuMemory tools will be available in your conversations", "info")
        self._log("", "info")
        self._log("Available MCP tools:", "info")
        self._log("  • kuzu_enhance - Enhance prompts with project context", "info")
        self._log("  • kuzu_learn - Store learnings asynchronously", "info")
        self._log("  • kuzu_recall - Query specific memories", "info")
        self._log("  • kuzu_remember - Store important information", "info")
        self._log("  • kuzu_stats - Get memory system statistics", "info")

        return True

    def uninstall(self) -> bool:
        """
        Remove KuzuMemory MCP integration from Claude Desktop.

        Returns:
            True if uninstallation was successful, False otherwise
        """
        self._log("KuzuMemory Claude Desktop MCP Uninstaller", "header")

        if not self.config_path.exists():
            self._log("No Claude Desktop configuration found", "warning")
            return True

        # Backup before modifying
        backup_path = self._backup_config(self.config_path)

        try:
            # Load configuration
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Check if kuzu-memory exists
            if "mcpServers" in config and "kuzu-memory" in config["mcpServers"]:
                if self.dry_run:
                    self._log("Would remove kuzu-memory from configuration", "info")
                else:
                    del config["mcpServers"]["kuzu-memory"]

                    # Remove empty mcpServers section
                    if not config["mcpServers"]:
                        del config["mcpServers"]

                    # Write updated configuration
                    with open(self.config_path, 'w') as f:
                        json.dump(config, f, indent=2)

                    self._log("Removed KuzuMemory from Claude Desktop configuration", "success")
            else:
                self._log("KuzuMemory not found in configuration", "info")

            return True

        except (json.JSONDecodeError, IOError) as e:
            self._log(f"Failed to update configuration: {e}", "error")
            if backup_path:
                self._log(f"Restore from backup: {backup_path}", "info")
            return False

    def validate(self) -> bool:
        """
        Validate the current installation.

        Returns:
            True if installation is valid, False otherwise
        """
        self._log("Validating KuzuMemory MCP Installation", "header")

        # Check kuzu-memory installation
        self.kuzu_command, self.pipx_venv_path = self._find_kuzu_memory()
        if not self.kuzu_command and not self.pipx_venv_path:
            self._log("KuzuMemory is not installed", "error")
            return False
        self._log("KuzuMemory installation found", "success")

        # Check Claude Desktop configuration
        if not self.config_path.exists():
            self._log("Claude Desktop configuration not found", "error")
            return False

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            if "mcpServers" not in config or "kuzu-memory" not in config["mcpServers"]:
                self._log("KuzuMemory not configured in Claude Desktop", "error")
                return False

            mcp_config = config["mcpServers"]["kuzu-memory"]
            self._log("KuzuMemory MCP configuration found", "success")

            if self.verbose:
                self._log("Configuration details:", "info")
                print(json.dumps(mcp_config, indent=2))

        except (json.JSONDecodeError, IOError) as e:
            self._log(f"Failed to read configuration: {e}", "error")
            return False

        # Check memory database directory
        if self.memory_db.parent.exists():
            self._log(f"Memory database directory exists: {self.memory_db.parent}", "success")
        else:
            self._log(f"Memory database directory not found: {self.memory_db.parent}", "warning")

        self._log("", "info")
        self._log("Validation successful! ✨", "success")
        self._log("KuzuMemory MCP integration is properly configured", "info")

        return True


def main():
    """Main entry point for the installer."""
    parser = argparse.ArgumentParser(
        description="Install KuzuMemory MCP integration for Claude Desktop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install with default settings
  python scripts/install-claude-desktop.py

  # Install with custom memory database location
  python scripts/install-claude-desktop.py --memory-db ~/my-memories/db

  # Validate existing installation
  python scripts/install-claude-desktop.py --validate

  # Uninstall KuzuMemory from Claude Desktop
  python scripts/install-claude-desktop.py --uninstall

  # Dry run to see what would be done
  python scripts/install-claude-desktop.py --dry-run
"""
    )

    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Directory for configuration backups (default: ~/.kuzu-memory-backups)"
    )
    parser.add_argument(
        "--memory-db",
        type=Path,
        help="Path to memory database (default: ~/.kuzu-memory/memorydb)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force installation even if configuration exists"
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove KuzuMemory from Claude Desktop configuration"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the current installation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Create installer
    installer = ClaudeDesktopInstaller(
        backup_dir=args.backup_dir,
        memory_db=args.memory_db,
        force=args.force,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    # Execute requested action
    try:
        if args.validate:
            success = installer.validate()
        elif args.uninstall:
            success = installer.uninstall()
        else:
            success = installer.install()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Installation cancelled by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Installation failed: {e}{Colors.RESET}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Print deprecation warning
    print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  DEPRECATION WARNING ⚠️{Colors.RESET}")
    print(f"{Colors.YELLOW}This standalone script is deprecated. Please use:{Colors.RESET}")
    print(f"{Colors.CYAN}    kuzu-memory install claude-desktop{Colors.RESET}")
    print(f"{Colors.YELLOW}For more options: {Colors.CYAN}kuzu-memory install --help{Colors.RESET}")
    print(f"{Colors.YELLOW}Continuing with legacy installation...{Colors.RESET}\n")

    main()