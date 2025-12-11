"""
Claude Desktop MCP Installers

Provides installers for integrating KuzuMemory with Claude Desktop via MCP.
Supports both pipx-based and home directory installations.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseInstaller, InstallationResult
from .json_utils import fix_broken_mcp_args

logger = logging.getLogger(__name__)


class ClaudeDesktopPipxInstaller(BaseInstaller):
    """
    Installer for Claude Desktop using pipx-installed kuzu-memory.

    Configures Claude Desktop to use KuzuMemory via MCP protocol
    by detecting and using the pipx-installed package.
    """

    def __init__(self, project_root: Path, **kwargs: Any) -> None:
        """Initialize the installer."""
        super().__init__(project_root)

        # Configuration options
        backup_dir_arg: Path | str | None = kwargs.get("backup_dir")
        memory_db_arg: Path | str | None = kwargs.get("memory_db")
        self.backup_dir = (
            Path(backup_dir_arg) if backup_dir_arg else Path.home() / ".kuzu-memory-backups"
        )
        self.memory_db = (
            Path(memory_db_arg) if memory_db_arg else Path.home() / ".kuzu-memory" / "memorydb"
        )
        self.force: bool = kwargs.get("force", False)
        self.dry_run: bool = kwargs.get("dry_run", False)
        self.verbose: bool = kwargs.get("verbose", False)

        # Platform-specific paths
        self.config_path = self._get_claude_config_path()
        self.kuzu_command: str | None = None
        self.pipx_venv_path: Path | None = None

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system."""
        return "Claude Desktop (pipx)"

    @property
    def description(self) -> str:
        """Description of the installer."""
        return "Configure Claude Desktop to use pipx-installed KuzuMemory via MCP"

    @property
    def required_files(self) -> list[str]:
        """Required files (none for system-level installation)."""
        return []

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
            return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        else:
            raise OSError(f"Unsupported operating system: {system}")

    def _find_kuzu_memory(self) -> tuple[str | None, Path | None]:
        """
        Find the kuzu-memory installation.

        Returns:
            Tuple of (command_path, pipx_venv_path) or (None, None) if not found
        """
        # First, try to find via pipx
        try:
            pipx_result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            if pipx_result.returncode == 0:
                pipx_data = json.loads(pipx_result.stdout)
                venvs = pipx_data.get("venvs", {})

                if "kuzu-memory" in venvs:
                    venv_info = venvs["kuzu-memory"]
                    apps = venv_info["metadata"]["main_package"]["apps"]
                    app_paths = venv_info["metadata"]["main_package"]["app_paths"]

                    if apps and app_paths:
                        app_path: str
                        if isinstance(app_paths, list) and app_paths:
                            app_path_dict = app_paths[0]
                            app_path_raw: Any = (
                                app_path_dict.get("__Path__")
                                if isinstance(app_path_dict, dict)
                                else str(app_path_dict)
                            )
                            app_path = str(app_path_raw) if app_path_raw is not None else ""
                        else:
                            app_path = str(app_paths)

                        if app_path:
                            logger.info(f"Found pipx installation at {app_path}")
                            pipx_venv_dir = Path(app_path).parent.parent
                            return str(app_path), pipx_venv_dir
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Could not detect pipx installation: {e}")

        # Fall back to checking PATH
        try:
            result = subprocess.run(
                ["which", "kuzu-memory"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            if result.returncode == 0:
                kuzu_path = result.stdout.strip()
                logger.info(f"Found kuzu-memory in PATH: {kuzu_path}")
                return kuzu_path, None
        except subprocess.SubprocessError:
            pass

        return None, None

    def _backup_config(self, config_path: Path) -> Path | None:
        """Create a backup of the existing configuration."""
        if not config_path.exists():
            return None

        if self.dry_run:
            logger.info(f"Would backup: {config_path}")
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(config_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

        return backup_path

    def _get_global_config_path(self) -> Path:
        """
        Get the global configuration file path.

        Returns:
            Path to global config.yaml in ~/.kuzu-memory/
        """
        return Path.home() / ".kuzu-memory" / "config.yaml"

    def _create_global_config(self) -> str:
        """
        Create global configuration file content.

        Returns:
            YAML configuration content for global installation
        """
        db_path = self.memory_db
        return f"""# KuzuMemory Global Configuration
# For Claude Desktop integration

version: "1.0"
debug: false
log_level: "INFO"

# Database location (global)
database:
  path: {db_path}

# Storage configuration
storage:
  max_size_mb: 50.0
  auto_compact: true
  backup_on_corruption: true
  connection_pool_size: 5
  query_timeout_ms: 5000

# Memory recall configuration
recall:
  max_memories: 10
  default_strategy: "auto"
  strategies:
    - "keyword"
    - "entity"
    - "temporal"
  strategy_weights:
    keyword: 0.4
    entity: 0.4
    temporal: 0.2
  min_confidence_threshold: 0.1
  enable_caching: true
  cache_size: 1000
  cache_ttl_seconds: 300

# Memory extraction configuration
extraction:
  min_memory_length: 5
  max_memory_length: 1000
  enable_entity_extraction: true
  enable_pattern_compilation: true
  enable_nlp_classification: true

# Performance monitoring
performance:
  max_recall_time_ms: 200.0
  max_generation_time_ms: 1000.0
  enable_performance_monitoring: true
  log_slow_operations: true
  enable_metrics_collection: false

# Memory retention
retention:
  enable_auto_cleanup: true
  cleanup_interval_hours: 24
  max_total_memories: 100000
  cleanup_batch_size: 1000
"""

    def _create_mcp_config(self) -> dict[str, Any]:
        """Create the MCP server configuration for KuzuMemory."""
        # Use the unified 'kuzu-memory mcp' command for all installations
        # This provides a consistent interface across all MCP clients
        return {
            "command": "kuzu-memory",
            "args": ["mcp"],
            "env": {
                "KUZU_MEMORY_DB": str(self.memory_db),
                "KUZU_MEMORY_MODE": "mcp",
            },
        }

    def install(self, force: bool = False, **kwargs: Any) -> InstallationResult:
        """Install Claude Desktop MCP integration."""
        try:
            # Update options from kwargs
            self.force = force or kwargs.get("force", self.force)
            self.dry_run = kwargs.get("dry_run", self.dry_run)

            # Find kuzu-memory installation
            self.kuzu_command, self.pipx_venv_path = self._find_kuzu_memory()

            if not self.kuzu_command and not self.pipx_venv_path:
                return InstallationResult(
                    success=False,
                    ai_system=self.ai_system_name,
                    message="KuzuMemory is not installed. Install it with: pipx install kuzu-memory",
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    warnings=["No kuzu-memory installation found"],
                )

            # Ensure config directory exists
            if not self.config_path.parent.exists():
                if not self.dry_run:
                    self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Load or create configuration
            config: dict[str, Any] = {}
            backup_path = None
            if self.config_path.exists():
                backup_path = self._backup_config(self.config_path)
                try:
                    with open(self.config_path) as f:
                        config = json.load(f)
                except json.JSONDecodeError as e:
                    return InstallationResult(
                        success=False,
                        ai_system=self.ai_system_name,
                        message=f"Failed to parse existing config: {e}",
                        files_created=[],
                        files_modified=[],
                        backup_files=[],
                        warnings=[f"Backup available at: {backup_path}" if backup_path else ""],
                    )

            # Auto-fix broken MCP configurations
            config, fixes = fix_broken_mcp_args(config)
            if fixes:
                logger.info(f"Auto-fixed {len(fixes)} broken MCP configuration(s)")
                for fix in fixes:
                    logger.debug(fix)

            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Check if already configured
            if "kuzu-memory" in config["mcpServers"] and not self.force:
                return InstallationResult(
                    success=False,
                    ai_system=self.ai_system_name,
                    message="KuzuMemory MCP server already configured",
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    warnings=["Use --force to overwrite existing configuration"],
                )

            # Add/update the configuration
            config["mcpServers"]["kuzu-memory"] = self._create_mcp_config()

            # Write configuration
            if not self.dry_run:
                with open(self.config_path, "w") as f:
                    json.dump(config, f, indent=2)

            # Create memory database directory
            if not self.memory_db.parent.exists() and not self.dry_run:
                self.memory_db.parent.mkdir(parents=True, exist_ok=True)

            # Create global config.yaml
            created_files: list[Path] = []
            modified_files: list[Path] = []
            global_config_path = self._get_global_config_path()

            if not self.dry_run:
                if global_config_path.exists():
                    logger.info(f"Global config already exists at {global_config_path}, preserving")
                    modified_files.append(global_config_path)
                else:
                    global_config_path.parent.mkdir(parents=True, exist_ok=True)
                    global_config_path.write_text(self._create_global_config())
                    created_files.append(global_config_path)
                    logger.info(f"Created global config at {global_config_path}")

            # Initialize global database if needed
            if not self.dry_run and not (self.memory_db / "memories.db").exists():
                try:
                    from ..core.memory import KuzuMemory

                    memory = KuzuMemory(db_path=self.memory_db / "memories.db")
                    memory.close()
                    logger.info(f"Initialized global database at {self.memory_db}")
                except Exception as e:
                    logger.warning(f"Failed to initialize database: {e}")

            if not self.config_path.exists():
                created_files.append(self.config_path)
            else:
                modified_files.append(self.config_path)

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                message="Claude Desktop MCP integration installed successfully",
                files_created=created_files,
                files_modified=modified_files,
                backup_files=[backup_path] if backup_path else [],
                warnings=[
                    "Restart Claude Desktop to load the new configuration",
                    "Available MCP tools: kuzu_enhance, kuzu_learn, kuzu_recall, kuzu_remember, kuzu_stats",
                    f"Global config: {global_config_path}",
                    f"Global database: {self.memory_db}",
                ],
            )

        except Exception as e:
            logger.exception("Installation failed")
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                message=f"Installation failed: {e}",
                files_created=[],
                files_modified=[],
                backup_files=[],
                warnings=[],
            )

    def uninstall(self, **kwargs: Any) -> InstallationResult:
        """Remove Claude Desktop MCP integration."""
        try:
            if not self.config_path.exists():
                return InstallationResult(
                    success=True,
                    ai_system=self.ai_system_name,
                    message="No Claude Desktop configuration found",
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    warnings=[],
                )

            # Backup before modifying
            backup_path = self._backup_config(self.config_path)

            # Load configuration
            with open(self.config_path) as f:
                config = json.load(f)

            # Check if kuzu-memory exists
            if "mcpServers" in config and "kuzu-memory" in config["mcpServers"]:
                if not self.dry_run:
                    del config["mcpServers"]["kuzu-memory"]

                    # Remove empty mcpServers section
                    if not config["mcpServers"]:
                        del config["mcpServers"]

                    # Write updated configuration
                    with open(self.config_path, "w") as f:
                        json.dump(config, f, indent=2)

                return InstallationResult(
                    success=True,
                    ai_system=self.ai_system_name,
                    message="Removed KuzuMemory from Claude Desktop configuration",
                    files_created=[],
                    files_modified=[self.config_path],
                    backup_files=[backup_path] if backup_path else [],
                    warnings=[],
                )
            else:
                return InstallationResult(
                    success=True,
                    ai_system=self.ai_system_name,
                    message="KuzuMemory not found in configuration",
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    warnings=[],
                )

        except (OSError, json.JSONDecodeError) as e:
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                message=f"Failed to update configuration: {e}",
                files_created=[],
                files_modified=[],
                backup_files=[],
                warnings=[],
            )

    def get_status(self) -> dict[str, Any]:
        """Get installation status."""
        status = {
            "installed": False,
            "config_exists": self.config_path.exists(),
            "kuzu_installed": False,
            "configured_in_claude": False,
        }

        # Check for kuzu-memory installation
        kuzu_command, pipx_venv = self._find_kuzu_memory()
        status["kuzu_installed"] = bool(kuzu_command or pipx_venv)

        # Check Claude Desktop config
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = json.load(f)
                status["configured_in_claude"] = (
                    "mcpServers" in config and "kuzu-memory" in config["mcpServers"]
                )
            except (OSError, json.JSONDecodeError):
                pass

        status["installed"] = status["kuzu_installed"] and status["configured_in_claude"]

        return status


class SmartClaudeDesktopInstaller(BaseInstaller):
    """
    Smart installer for Claude Desktop that auto-detects best installation method.

    Auto-detects if pipx is available and uses pipx-based installation if possible,
    otherwise falls back to home directory installation.
    Supports --mode flag (auto|pipx|home) to override detection.
    """

    def __init__(self, project_root: Path, **kwargs: Any) -> None:
        """Initialize the smart installer."""
        super().__init__(project_root)

        # Configuration options
        self.mode: str = kwargs.get("mode", "auto")
        backup_dir_arg: Path | str | None = kwargs.get("backup_dir")
        memory_db_arg: Path | str | None = kwargs.get("memory_db")
        self.backup_dir = (
            Path(backup_dir_arg) if backup_dir_arg else Path.home() / ".kuzu-memory-backups"
        )
        self.memory_db = (
            Path(memory_db_arg) if memory_db_arg else Path.home() / ".kuzu-memory" / "memorydb"
        )
        self.force: bool = kwargs.get("force", False)
        self.dry_run: bool = kwargs.get("dry_run", False)
        self.verbose: bool = kwargs.get("verbose", False)

        # Delegate installer
        self._delegate: BaseInstaller | None = None

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system."""
        return "Claude Desktop"

    @property
    def description(self) -> str:
        """Description of the installer."""
        return "Configure Claude Desktop (auto-detects pipx or home installation)"

    @property
    def required_files(self) -> list[str]:
        """Required files (delegates to chosen installer)."""
        delegate = self._get_delegate()
        return delegate.required_files if delegate else []

    def _detect_pipx(self) -> bool:
        """Detect if pipx is available and kuzu-memory is installed."""
        try:
            result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode == 0:
                pipx_data = json.loads(result.stdout)
                venvs = pipx_data.get("venvs", {})
                return "kuzu-memory" in venvs
        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            pass
        return False

    def _get_delegate(self) -> BaseInstaller:
        """Get the appropriate delegate installer based on mode/detection."""
        if self._delegate:
            return self._delegate

        # Determine which installer to use
        use_pipx = False

        if self.mode == "pipx":
            use_pipx = True
        elif self.mode == "home":
            use_pipx = False
        else:  # auto
            use_pipx = self._detect_pipx()

        # Create delegate with shared options
        kwargs = {
            "backup_dir": self.backup_dir,
            "memory_db": self.memory_db,
            "force": self.force,
            "dry_run": self.dry_run,
            "verbose": self.verbose,
        }

        if use_pipx:
            logger.info("Using pipx-based installation")
            self._delegate = ClaudeDesktopPipxInstaller(self.project_root, **kwargs)
        else:
            logger.info("Using home directory installation")
            kwargs["mode"] = self.mode
            self._delegate = ClaudeDesktopHomeInstaller(self.project_root, **kwargs)

        return self._delegate

    def install(self, force: bool = False, **kwargs: Any) -> InstallationResult:
        """Install Claude Desktop MCP integration."""
        # Update options from kwargs
        self.force = force or kwargs.get("force", self.force)
        self.dry_run = kwargs.get("dry_run", self.dry_run)
        mode_arg: str | None = kwargs.get("mode")
        self.mode = mode_arg if mode_arg is not None else self.mode

        # Get and invoke delegate
        delegate = self._get_delegate()
        return delegate.install(**kwargs)

    def uninstall(self, **kwargs: Any) -> InstallationResult:
        """Remove Claude Desktop MCP integration."""
        delegate = self._get_delegate()
        return delegate.uninstall(**kwargs)

    def get_status(self) -> dict[str, Any]:
        """Get installation status."""
        delegate = self._get_delegate()
        status = delegate.get_status()
        status["installation_method"] = (
            "pipx" if isinstance(delegate, ClaudeDesktopPipxInstaller) else "home"
        )
        return status


class ClaudeDesktopHomeInstaller(BaseInstaller):
    """
    Installer for Claude Desktop using home directory installation.

    Installs kuzu-memory entirely within ~/.kuzu-memory/ directory
    without requiring pipx. Supports both wrapper and standalone modes.
    """

    def __init__(self, project_root: Path, **kwargs: Any) -> None:
        """Initialize the installer."""
        super().__init__(project_root)

        # Configuration options
        self.mode: str = kwargs.get("mode", "auto")
        backup_dir_arg: Path | str | None = kwargs.get("backup_dir")
        self.backup_dir = (
            Path(backup_dir_arg) if backup_dir_arg else Path.home() / ".kuzu-memory-backups"
        )
        self.force: bool = kwargs.get("force", False)
        self.dry_run: bool = kwargs.get("dry_run", False)
        self.verbose: bool = kwargs.get("verbose", False)

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
        self.system_python: str | None = None
        self.system_package_path: Path | None = None

    @property
    def ai_system_name(self) -> str:
        """Name of the AI system."""
        return "Claude Desktop (Home)"

    @property
    def description(self) -> str:
        """Description of the installer."""
        return "Install KuzuMemory in ~/.kuzu-memory/ for Claude Desktop"

    @property
    def required_files(self) -> list[str]:
        """Required files (none for system-level installation)."""
        return []

    def _get_claude_config_path(self) -> Path:
        """Get the Claude Desktop configuration file path."""
        system = platform.system()

        if system == "Darwin":
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
            return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        else:
            raise OSError(f"Unsupported operating system: {system}")

    def _find_system_installation(self) -> tuple[str | None, Path | None]:
        """Find system installation of kuzu-memory."""
        import sys as _sys

        # Try common Python executables
        python_candidates = ["python3", "python", _sys.executable]

        for python_exe in python_candidates:
            try:
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
                    logger.info(f"Found system installation: {package_path}")
                    return python_exe, package_path

            except (subprocess.SubprocessError, FileNotFoundError):
                continue

        return None, None

    def _detect_installation_mode(self) -> str:
        """Detect the best installation mode."""
        if self.mode != "auto":
            # Return the configured mode directly
            return str(self.mode)

        python_exe, package_path = self._find_system_installation()

        if python_exe and package_path:
            logger.info("System installation found - using wrapper mode")
            self.system_python = python_exe
            self.system_package_path = package_path
            return "wrapper"
        else:
            logger.info("No system installation - using standalone mode")
            return "standalone"

    def _create_launcher_scripts(self, installation_type: str) -> None:
        """Create launcher scripts in bin directory."""
        if self.dry_run:
            logger.info(f"Would create launcher scripts for {installation_type}")
            return

        self.bin_dir.mkdir(parents=True, exist_ok=True)

        # Determine module import path based on installation type
        if installation_type == "wrapper":
            # Use system installation with direct import
            module_import = "from kuzu_memory.mcp.run_server import main"
        else:
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

# Set database path
os.environ.setdefault('KUZU_MEMORY_DB', '{self.db_dir}')
os.environ['KUZU_MEMORY_MODE'] = 'mcp'

{module_import}

if __name__ == '__main__':
    main()
"""
        launcher_script.write_text(launcher_content)
        launcher_script.chmod(0o755)

    def _copy_package_standalone(self) -> None:
        """Copy package files for standalone installation."""
        if self.dry_run:
            logger.info("Would copy package files to lib directory")
            return

        # Find package in current project
        # This assumes we're running from the project directory
        import kuzu_memory

        src_package = Path(kuzu_memory.__file__).parent

        if not src_package.exists():
            raise FileNotFoundError(f"Package source not found: {src_package}")

        dest_package = self.lib_dir / "kuzu_memory"

        # Remove existing if present
        if dest_package.exists():
            shutil.rmtree(dest_package)

        # Copy package
        shutil.copytree(src_package, dest_package)
        logger.info(f"Copied package to: {dest_package}")

    def install(self, force: bool = False, **kwargs: Any) -> InstallationResult:
        """Install KuzuMemory to ~/.kuzu-memory/."""
        try:
            # Update options from kwargs
            self.force = force or kwargs.get("force", self.force)
            self.dry_run = kwargs.get("dry_run", self.dry_run)
            mode_arg: str | None = kwargs.get("mode")
            self.mode = mode_arg if mode_arg is not None else self.mode

            # Detect installation mode
            installation_type = self._detect_installation_mode()

            # Check if already installed
            if self.install_root.exists() and not self.force:
                return InstallationResult(
                    success=False,
                    ai_system=self.ai_system_name,
                    message=f"Installation already exists: {self.install_root}",
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    warnings=["Use --force to reinstall"],
                )

            # Create directory structure
            if not self.dry_run:
                self.install_root.mkdir(parents=True, exist_ok=True)
                self.db_dir.mkdir(parents=True, exist_ok=True)

            # Install based on mode
            if installation_type == "standalone":
                self._copy_package_standalone()
            else:
                if not self.system_python or not self.system_package_path:
                    return InstallationResult(
                        success=False,
                        ai_system=self.ai_system_name,
                        message="System installation not found for wrapper mode",
                        files_created=[],
                        files_modified=[],
                        backup_files=[],
                        warnings=[],
                    )

            # Create launcher scripts
            self._create_launcher_scripts(installation_type)

            # Create global configuration file
            if not self.dry_run:
                global_config_path = self._get_global_config_path()
                global_config_path.write_text(self._create_global_config())
                logger.info(f"Created global configuration at {global_config_path}")

            # Write metadata
            if not self.dry_run:
                try:
                    import kuzu_memory

                    version = kuzu_memory.__version__
                except (ImportError, AttributeError):
                    version = "unknown"
                self.version_file.write_text(version)
                self.type_file.write_text(installation_type)

            # Update Claude Desktop config
            if not self.dry_run:
                self._update_claude_config()

            global_config_path = self._get_global_config_path()

            # Initialize global database if needed
            if not self.dry_run and not (self.db_dir / "memories.db").exists():
                try:
                    from ..core.memory import KuzuMemory

                    memory = KuzuMemory(db_path=self.db_dir / "memories.db")
                    memory.close()
                    logger.info(f"Initialized global database at {self.db_dir}")
                except Exception as e:
                    logger.warning(f"Failed to initialize database: {e}")

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                message=f"Installation complete: {self.install_root}",
                files_created=[
                    self.bin_dir / "kuzu-memory-mcp-server",
                    global_config_path,
                    self.version_file,
                    self.type_file,
                ],
                files_modified=[],
                backup_files=[],
                warnings=[
                    f"Installation type: {installation_type}",
                    "Restart Claude Desktop to load the configuration",
                    f"Global config: {global_config_path}",
                    f"Global database: {self.db_dir}",
                ],
            )

        except Exception as e:
            logger.exception("Installation failed")
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                message=f"Installation failed: {e}",
                files_created=[],
                files_modified=[],
                backup_files=[],
                warnings=[],
            )

    def _get_global_config_path(self) -> Path:
        """
        Get the global configuration file path.

        Returns:
            Path to global config.yaml in ~/.kuzu-memory/
        """
        return self.install_root / "config.yaml"

    def _create_global_config(self) -> str:
        """
        Create global configuration file content.

        Returns:
            YAML configuration content for global installation
        """
        return f"""# KuzuMemory Global Configuration
# For Claude Desktop integration (Home installation)

version: "1.0"
debug: false
log_level: "INFO"

# Database location (global)
database:
  path: {self.db_dir}

# Storage configuration
storage:
  max_size_mb: 50.0
  auto_compact: true
  backup_on_corruption: true
  connection_pool_size: 5
  query_timeout_ms: 5000

# Memory recall configuration
recall:
  max_memories: 10
  default_strategy: "auto"
  strategies:
    - "keyword"
    - "entity"
    - "temporal"
  strategy_weights:
    keyword: 0.4
    entity: 0.4
    temporal: 0.2
  min_confidence_threshold: 0.1
  enable_caching: true
  cache_size: 1000
  cache_ttl_seconds: 300

# Memory extraction configuration
extraction:
  min_memory_length: 5
  max_memory_length: 1000
  enable_entity_extraction: true
  enable_pattern_compilation: true
  enable_nlp_classification: true

# Performance monitoring
performance:
  max_recall_time_ms: 200.0
  max_generation_time_ms: 1000.0
  enable_performance_monitoring: true
  log_slow_operations: true
  enable_metrics_collection: false

# Memory retention
retention:
  enable_auto_cleanup: true
  cleanup_interval_hours: 24
  max_total_memories: 100000
  cleanup_batch_size: 1000
"""

    def _update_claude_config(self) -> None:
        """Update Claude Desktop configuration."""
        self.claude_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create config
        config: dict[str, Any] = {}
        if self.claude_config_path.exists():
            try:
                with open(self.claude_config_path) as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse existing config: {e}")
                return

        # Auto-fix broken MCP configurations
        config, fixes = fix_broken_mcp_args(config)
        if fixes:
            logger.info(f"Auto-fixed {len(fixes)} broken MCP configuration(s)")
            for fix in fixes:
                logger.debug(fix)

        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Create MCP configuration
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

    def uninstall(self, **kwargs: Any) -> InstallationResult:
        """Remove installation."""
        try:
            if not self.install_root.exists():
                return InstallationResult(
                    success=True,
                    ai_system=self.ai_system_name,
                    message="No installation found",
                    files_created=[],
                    files_modified=[],
                    backup_files=[],
                    warnings=[],
                )

            # Remove from Claude Desktop config
            if self.claude_config_path.exists():
                try:
                    with open(self.claude_config_path) as f:
                        config = json.load(f)

                    if "mcpServers" in config and "kuzu-memory" in config["mcpServers"]:
                        del config["mcpServers"]["kuzu-memory"]

                        if not config["mcpServers"]:
                            del config["mcpServers"]

                        with open(self.claude_config_path, "w") as f:
                            json.dump(config, f, indent=2)

                except (OSError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to update Claude config: {e}")

            # Remove installation directory
            if not self.dry_run:
                shutil.rmtree(self.install_root)

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                message=f"Removed installation: {self.install_root}",
                files_created=[],
                files_modified=[],
                backup_files=[],
                warnings=[],
            )

        except Exception as e:
            logger.exception("Uninstallation failed")
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                message=f"Uninstallation failed: {e}",
                files_created=[],
                files_modified=[],
                backup_files=[],
                warnings=[],
            )

    def get_status(self) -> dict[str, Any]:
        """Get installation status."""
        status: dict[str, Any] = {
            "installed": self.install_root.exists(),
            "launcher_exists": (self.bin_dir / "kuzu-memory-mcp-server").exists(),
            "config_exists": self.config_file.exists(),
            "configured_in_claude": False,
        }

        # Check installation type
        if self.type_file.exists():
            status["installation_type"] = self.type_file.read_text().strip()

        # Check version
        if self.version_file.exists():
            status["version"] = self.version_file.read_text().strip()

        # Check Claude Desktop config
        if self.claude_config_path.exists():
            try:
                with open(self.claude_config_path) as f:
                    config = json.load(f)
                status["configured_in_claude"] = (
                    "mcpServers" in config and "kuzu-memory" in config["mcpServers"]
                )
            except (OSError, json.JSONDecodeError):
                pass

        return status
