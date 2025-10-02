#!/usr/bin/env python3
"""
KuzuMemory Claude Desktop Home Installation Script

⚠️  DEPRECATION NOTICE ⚠️
This standalone script is DEPRECATED and will be REMOVED in v2.0.0 (planned: 2026 Q1).

Please use the integrated CLI command instead:
    kuzu-memory install claude-desktop-home [options]

For help with the new command:
    kuzu-memory install --help
    kuzu-memory list-installers

Migration Examples:
    OLD: python scripts/install-claude-desktop-home.py
    NEW: kuzu-memory install claude-desktop-home

    OLD: python scripts/install-claude-desktop-home.py --mode standalone
    NEW: kuzu-memory install claude-desktop-home --mode standalone

    OLD: python scripts/install-claude-desktop-home.py --dry-run --verbose
    NEW: kuzu-memory install claude-desktop-home --dry-run --verbose

REMOVAL TIMELINE: This script will be removed in v2.0.0 (2026 Q1)
This script still works for backward compatibility but is no longer maintained.
---

Installs kuzu-memory entirely within ~/.kuzu-memory/ directory without requiring pipx.
Supports both wrapper mode (uses existing system package) and standalone mode (local copy).

Directory structure created:
~/.kuzu-memory/
├── bin/
│   ├── kuzu-memory-mcp-server    # Python launcher
│   └── run-mcp-server.sh         # Shell wrapper fallback
├── lib/
│   └── kuzu_memory/              # Package files (standalone mode only)
├── memorydb/                      # Database storage
├── config.yaml                    # Configuration
├── .version                       # Installation version
└── .installation_type             # "standalone" or "wrapper"

Usage:
    python scripts/install-claude-desktop-home.py [options]

Options:
    --mode {auto|wrapper|standalone}  Installation mode (default: auto)
    --backup-dir PATH                 Custom backup directory
    --force                           Force installation even if exists
    --uninstall                       Remove installation
    --update                          Update existing installation
    --dry-run                         Show what would be done
    --verbose                         Enable verbose output
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
from typing import Any, Dict, Optional, Tuple


class Colors:
    """Terminal color codes for pretty output."""

    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"


class HomeInstaller:
    """Installer for KuzuMemory in ~/.kuzu-memory/ directory."""

    def __init__(
        self,
        mode: str = "auto",
        backup_dir: Optional[Path] = None,
        force: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the home installer.

        Args:
            mode: Installation mode (auto, wrapper, standalone)
            backup_dir: Directory for config backups
            force: Force installation even if exists
            dry_run: Show what would be done without making changes
            verbose: Enable verbose output
        """
        self.mode = mode
        self.backup_dir = backup_dir or Path.home() / ".kuzu-memory-backups"
        self.force = force
        self.dry_run = dry_run
        self.verbose = verbose

        # Installation directories
        self.install_root = Path.home() / ".kuzu-memory"
        self.bin_dir = self.install_root / "bin"
        self.lib_dir = self.install_root / "lib"
        self.db_dir = self.install_root / "memorydb"
        self.config_file = self.install_root / "config.yaml"
        self.version_file = self.install_root / ".version"
        self.type_file = self.install_root / ".installation_type"

        # Claude Desktop config
        self.claude_config_path = self._get_claude_config_path()

        # System installation detection
        self.system_python: Optional[str] = None
        self.system_package_path: Optional[Path] = None

    def _log(self, message: str, level: str = "info") -> None:
        """Print colored log message."""
        if level == "error":
            print(f"{Colors.RED}✗ {message}{Colors.RESET}")
        elif level == "success":
            print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")
        elif level == "warning":
            print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")
        elif level == "header":
            print(f"\n{Colors.CYAN}{'=' * 60}")
            print(f"  {message}")
            print(f"{'=' * 60}{Colors.RESET}\n")
        elif self.verbose or level == "info":
            print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

    def _get_claude_config_path(self) -> Path:
        """Get the Claude Desktop configuration file path based on the platform."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        elif system == "Linux":
            xdg_config = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
            return Path(xdg_config) / "Claude" / "claude_desktop_config.json"
        elif system == "Windows":
            appdata = os.getenv("APPDATA")
            if appdata:
                return Path(appdata) / "Claude" / "claude_desktop_config.json"
            return (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Claude"
                / "claude_desktop_config.json"
            )
        else:
            raise OSError(f"Unsupported operating system: {system}")

    def _find_system_installation(self) -> Tuple[Optional[str], Optional[Path]]:
        """
        Find system installation of kuzu-memory.

        Returns:
            Tuple of (python_executable, package_path) or (None, None) if not found
        """
        # Try common Python executables
        python_candidates = ["python3", "python", sys.executable]

        for python_exe in python_candidates:
            try:
                # Check if kuzu_memory is importable
                result = subprocess.run(
                    [
                        python_exe,
                        "-c",
                        "import kuzu_memory; print(kuzu_memory.__file__)",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    package_path = Path(result.stdout.strip()).parent
                    self._log(
                        f"Found system installation: {package_path} (Python: {python_exe})",
                        "success",
                    )
                    return python_exe, package_path

            except (subprocess.SubprocessError, FileNotFoundError):
                continue

        # Try pipx installation
        try:
            result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                pipx_data = json.loads(result.stdout)
                if "kuzu-memory" in pipx_data.get("venvs", {}):
                    venv_info = pipx_data["venvs"]["kuzu-memory"]
                    python_path = Path(venv_info["metadata"]["python_path"])

                    # Get package location
                    pkg_result = subprocess.run(
                        [
                            str(python_path),
                            "-c",
                            "import kuzu_memory; print(kuzu_memory.__file__)",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if pkg_result.returncode == 0:
                        package_path = Path(pkg_result.stdout.strip()).parent
                        self._log(
                            f"Found pipx installation: {package_path}", "success"
                        )
                        return str(python_path), package_path

        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            pass

        return None, None

    def _detect_installation_mode(self) -> str:
        """
        Detect the best installation mode.

        Returns:
            Installation mode: "wrapper" or "standalone"
        """
        if self.mode != "auto":
            return self.mode

        # Check for system installation
        python_exe, package_path = self._find_system_installation()

        if python_exe and package_path:
            self._log("System installation found - using wrapper mode", "info")
            self.system_python = python_exe
            self.system_package_path = package_path
            return "wrapper"
        else:
            self._log("No system installation - using standalone mode", "info")
            return "standalone"

    def _get_package_version(self) -> str:
        """Get the current package version."""
        try:
            if self.system_python:
                result = subprocess.run(
                    [
                        self.system_python,
                        "-c",
                        "import kuzu_memory; print(kuzu_memory.__version__)",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except subprocess.SubprocessError:
            pass

        # Fallback to reading from project
        version_path = Path(__file__).parent.parent / "VERSION"
        if version_path.exists():
            return version_path.read_text().strip()

        return "unknown"

    def _create_launcher_scripts(self, installation_type: str) -> None:
        """Create launcher scripts in bin directory."""
        if self.dry_run:
            self._log(f"Would create launcher scripts for {installation_type}", "info")
            return

        self.bin_dir.mkdir(parents=True, exist_ok=True)

        # Determine Python executable and module path
        if installation_type == "wrapper":
            python_exe = self.system_python or "python3"
            module_import = "from kuzu_memory.mcp.run_server import main"
        else:
            # Standalone mode - create custom Python path
            python_exe = sys.executable
            module_import = f"""
import sys
sys.path.insert(0, '{self.lib_dir}')
from kuzu_memory.mcp.run_server import main
"""

        # Create Python launcher script
        launcher_script = self.bin_dir / "kuzu-memory-mcp-server"
        launcher_content = f"""#!/usr/bin/env python3
\"\"\"
KuzuMemory MCP Server Launcher
Installation type: {installation_type}
\"\"\"
import os
import sys

# Set database path
os.environ.setdefault('KUZU_MEMORY_DB', '{self.db_dir}')
os.environ['KUZU_MEMORY_MODE'] = 'mcp'

{module_import}

if __name__ == '__main__':
    main()
"""
        launcher_script.write_text(launcher_content)
        launcher_script.chmod(0o755)
        self._log(f"Created Python launcher: {launcher_script}", "success")

        # Create shell wrapper for additional compatibility
        shell_wrapper = self.bin_dir / "run-mcp-server.sh"
        shell_content = f"""#!/bin/bash
# KuzuMemory MCP Server Shell Wrapper
export KUZU_MEMORY_DB="{self.db_dir}"
export KUZU_MEMORY_MODE="mcp"

exec {python_exe} "{launcher_script}" "$@"
"""
        shell_wrapper.write_text(shell_content)
        shell_wrapper.chmod(0o755)
        self._log(f"Created shell wrapper: {shell_wrapper}", "success")

    def _copy_package_standalone(self) -> None:
        """Copy package files for standalone installation."""
        if self.dry_run:
            self._log("Would copy package files to lib directory", "info")
            return

        # Find package in current project
        project_root = Path(__file__).parent.parent
        src_package = project_root / "src" / "kuzu_memory"

        if not src_package.exists():
            raise FileNotFoundError(f"Package source not found: {src_package}")

        dest_package = self.lib_dir / "kuzu_memory"

        # Remove existing if present
        if dest_package.exists():
            shutil.rmtree(dest_package)

        # Copy package
        shutil.copytree(src_package, dest_package)
        self._log(f"Copied package to: {dest_package}", "success")

        # Copy dependencies if needed (minimal approach)
        # In production, user should have dependencies installed
        self._log("Standalone mode: ensure dependencies are available", "warning")

    def _create_config(self) -> None:
        """Create default configuration file."""
        if self.dry_run:
            self._log("Would create configuration file", "info")
            return

        config_content = f"""# KuzuMemory Configuration
# Installation: {self.install_root}

database:
  path: {self.db_dir}

memory:
  retention_days:
    semantic: -1      # Never expire
    procedural: -1    # Never expire
    preference: -1    # Never expire
    episodic: 30
    working: 1
    sensory: 0.25     # 6 hours

performance:
  recall_threshold_ms: 100
  generation_threshold_ms: 200
  cache_enabled: true
"""
        self.config_file.write_text(config_content)
        self._log(f"Created config: {self.config_file}", "success")

    def _write_metadata(self, installation_type: str) -> None:
        """Write installation metadata."""
        if self.dry_run:
            return

        version = self._get_package_version()
        self.version_file.write_text(version)
        self.type_file.write_text(installation_type)

        self._log(f"Installation version: {version}", "info")
        self._log(f"Installation type: {installation_type}", "info")

    def _backup_config(self, config_path: Path) -> Optional[Path]:
        """Create a backup of the existing configuration."""
        if not config_path.exists():
            return None

        if self.dry_run:
            self._log(f"Would backup: {config_path}", "info")
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(config_path, backup_path)
        self._log(f"Created backup: {backup_path}", "success")

        return backup_path

    def _update_claude_config(self) -> None:
        """Update Claude Desktop configuration."""
        if self.dry_run:
            self._log("Would update Claude Desktop configuration", "info")
            return

        # Ensure parent directory exists
        self.claude_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create config
        config: Dict[str, Any] = {}
        if self.claude_config_path.exists():
            self._backup_config(self.claude_config_path)
            try:
                with open(self.claude_config_path, "r") as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                self._log(f"Failed to parse existing config: {e}", "error")
                return

        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Check if already exists
        if "kuzu-memory" in config["mcpServers"] and not self.force:
            self._log("KuzuMemory already configured", "warning")
            self._log("Use --force to overwrite", "info")
            return

        # Create MCP configuration using Python launcher
        launcher_path = self.bin_dir / "kuzu-memory-mcp-server"

        config["mcpServers"]["kuzu-memory"] = {
            "command": str(launcher_path),
            "args": [],
            "env": {
                "KUZU_MEMORY_DB": str(self.db_dir),
                "KUZU_MEMORY_MODE": "mcp",
            },
        }

        # Write updated config
        with open(self.claude_config_path, "w") as f:
            json.dump(config, f, indent=2)

        self._log(f"Updated Claude config: {self.claude_config_path}", "success")

    def install(self) -> bool:
        """
        Install KuzuMemory to ~/.kuzu-memory/.

        Returns:
            True if installation was successful, False otherwise
        """
        self._log("KuzuMemory Home Installation", "header")

        try:
            # Step 1: Detect installation mode
            installation_type = self._detect_installation_mode()
            self._log(f"Installation mode: {installation_type}", "info")

            # Step 2: Check if already installed
            if self.install_root.exists() and not self.force:
                self._log(f"Installation already exists: {self.install_root}", "warning")
                self._log("Use --force to reinstall or --update to upgrade", "info")
                return False

            # Step 3: Create directory structure
            if not self.dry_run:
                self.install_root.mkdir(parents=True, exist_ok=True)
                self.db_dir.mkdir(parents=True, exist_ok=True)

            # Step 4: Install based on mode
            if installation_type == "standalone":
                self._copy_package_standalone()
            else:
                if not self.system_python or not self.system_package_path:
                    self._log("System installation not found for wrapper mode", "error")
                    return False

            # Step 5: Create launcher scripts
            self._create_launcher_scripts(installation_type)

            # Step 6: Create configuration
            self._create_config()

            # Step 7: Write metadata
            self._write_metadata(installation_type)

            # Step 8: Update Claude Desktop config
            self._update_claude_config()

            # Success message
            self._log("Installation Complete!", "header")
            self._log(f"Installation directory: {self.install_root}", "success")
            self._log(f"Database location: {self.db_dir}", "info")
            self._log(f"Configuration: {self.config_file}", "info")
            self._log("", "info")
            self._log("Next steps:", "info")
            self._log("1. Restart Claude Desktop to load the configuration", "info")
            self._log("2. KuzuMemory tools will be available in conversations", "info")
            self._log("", "info")
            self._log("Available MCP tools:", "info")
            self._log("  • kuzu_enhance - Enhance prompts with context", "info")
            self._log("  • kuzu_learn - Store learnings asynchronously", "info")
            self._log("  • kuzu_recall - Query specific memories", "info")
            self._log("  • kuzu_remember - Store important information", "info")
            self._log("  • kuzu_stats - Get memory statistics", "info")

            return True

        except Exception as e:
            self._log(f"Installation failed: {e}", "error")
            if self.verbose:
                import traceback

                traceback.print_exc()
            return False

    def update(self) -> bool:
        """
        Update existing installation.

        Returns:
            True if update was successful, False otherwise
        """
        self._log("KuzuMemory Home Update", "header")

        if not self.install_root.exists():
            self._log("No existing installation found", "error")
            self._log("Use install command instead", "info")
            return False

        # Read current installation type
        if not self.type_file.exists():
            self._log("Installation type unknown - cannot update", "error")
            return False

        installation_type = self.type_file.read_text().strip()
        self._log(f"Current installation type: {installation_type}", "info")

        # Detect if system installation exists for wrapper mode
        if installation_type == "wrapper":
            python_exe, package_path = self._find_system_installation()
            if not python_exe or not package_path:
                self._log("System installation not found", "warning")
                self._log("Cannot update wrapper installation", "error")
                return False
            self.system_python = python_exe
            self.system_package_path = package_path

        # Recreate launcher scripts
        self._log("Updating launcher scripts...", "info")
        self._create_launcher_scripts(installation_type)

        # Update metadata
        self._write_metadata(installation_type)

        self._log("Update complete!", "success")
        return True

    def uninstall(self) -> bool:
        """
        Remove installation.

        Returns:
            True if uninstallation was successful, False otherwise
        """
        self._log("KuzuMemory Home Uninstaller", "header")

        if not self.install_root.exists():
            self._log("No installation found", "warning")
            return True

        if self.dry_run:
            self._log(f"Would remove: {self.install_root}", "info")
            self._log("Would update Claude Desktop config", "info")
            return True

        # Remove from Claude Desktop config
        if self.claude_config_path.exists():
            self._backup_config(self.claude_config_path)

            try:
                with open(self.claude_config_path, "r") as f:
                    config = json.load(f)

                if "mcpServers" in config and "kuzu-memory" in config["mcpServers"]:
                    del config["mcpServers"]["kuzu-memory"]

                    if not config["mcpServers"]:
                        del config["mcpServers"]

                    with open(self.claude_config_path, "w") as f:
                        json.dump(config, f, indent=2)

                    self._log("Removed from Claude Desktop config", "success")

            except (json.JSONDecodeError, IOError) as e:
                self._log(f"Failed to update Claude config: {e}", "warning")

        # Remove installation directory
        shutil.rmtree(self.install_root)
        self._log(f"Removed installation: {self.install_root}", "success")

        self._log("Uninstallation complete!", "success")
        return True

    def validate(self) -> bool:
        """
        Validate installation.

        Returns:
            True if installation is valid, False otherwise
        """
        self._log("KuzuMemory Home Installation Validation", "header")

        # Check installation directory
        if not self.install_root.exists():
            self._log("Installation directory not found", "error")
            return False
        self._log(f"Installation directory: {self.install_root}", "success")

        # Check installation type
        if not self.type_file.exists():
            self._log("Installation type file missing", "error")
            return False

        installation_type = self.type_file.read_text().strip()
        self._log(f"Installation type: {installation_type}", "success")

        # Check version
        if self.version_file.exists():
            version = self.version_file.read_text().strip()
            self._log(f"Installation version: {version}", "success")

        # Check launcher scripts
        launcher = self.bin_dir / "kuzu-memory-mcp-server"
        if not launcher.exists():
            self._log("Launcher script missing", "error")
            return False
        self._log(f"Launcher script: {launcher}", "success")

        # Check database directory
        if not self.db_dir.exists():
            self._log("Database directory missing", "warning")
        else:
            self._log(f"Database directory: {self.db_dir}", "success")

        # Check Claude Desktop config
        if self.claude_config_path.exists():
            try:
                with open(self.claude_config_path, "r") as f:
                    config = json.load(f)

                if "mcpServers" in config and "kuzu-memory" in config["mcpServers"]:
                    self._log("Claude Desktop configured", "success")
                    if self.verbose:
                        print(json.dumps(config["mcpServers"]["kuzu-memory"], indent=2))
                else:
                    self._log("Not configured in Claude Desktop", "warning")

            except (json.JSONDecodeError, IOError) as e:
                self._log(f"Failed to read Claude config: {e}", "warning")

        # Validate system installation for wrapper mode
        if installation_type == "wrapper":
            python_exe, package_path = self._find_system_installation()
            if python_exe and package_path:
                self._log(f"System installation valid: {package_path}", "success")
            else:
                self._log("System installation not found", "error")
                self._log("Wrapper mode requires system installation", "warning")
                return False

        self._log("", "info")
        self._log("Validation successful! ✨", "success")

        return True


def main() -> None:
    """Main entry point for the installer."""
    parser = argparse.ArgumentParser(
        description="Install KuzuMemory to ~/.kuzu-memory/ directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect mode and install
  python scripts/install-claude-desktop-home.py

  # Force wrapper mode (requires system installation)
  python scripts/install-claude-desktop-home.py --mode wrapper

  # Force standalone mode (copies package)
  python scripts/install-claude-desktop-home.py --mode standalone

  # Update existing installation
  python scripts/install-claude-desktop-home.py --update

  # Validate installation
  python scripts/install-claude-desktop-home.py --validate

  # Uninstall
  python scripts/install-claude-desktop-home.py --uninstall

  # Dry run
  python scripts/install-claude-desktop-home.py --dry-run --verbose
""",
    )

    parser.add_argument(
        "--mode",
        choices=["auto", "wrapper", "standalone"],
        default="auto",
        help="Installation mode (default: auto)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Directory for backups (default: ~/.kuzu-memory-backups)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force installation even if exists"
    )
    parser.add_argument(
        "--update", action="store_true", help="Update existing installation"
    )
    parser.add_argument(
        "--uninstall", action="store_true", help="Remove installation"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate installation"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Create installer
    installer = HomeInstaller(
        mode=args.mode,
        backup_dir=args.backup_dir,
        force=args.force,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    # Execute requested action
    try:
        if args.validate:
            success = installer.validate()
        elif args.uninstall:
            success = installer.uninstall()
        elif args.update:
            success = installer.update()
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
    print(f"{Colors.CYAN}    kuzu-memory install claude-desktop-home{Colors.RESET}")
    print(f"{Colors.YELLOW}For more options: {Colors.CYAN}kuzu-memory install --help{Colors.RESET}")
    print(f"{Colors.YELLOW}Continuing with legacy installation...{Colors.RESET}\n")

    main()
