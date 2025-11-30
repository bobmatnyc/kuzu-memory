"""
System utilities and detection for KuzuMemory installers.

Provides system detection, file operations, and platform-specific utilities.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SystemDetector:
    """Detects system configuration and available tools."""

    @staticmethod
    def get_system_info() -> dict[str, str]:
        """Get basic system information."""
        return {
            "platform": platform.system().lower(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0],
        }

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return platform.system().lower() == "windows"

    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS."""
        return platform.system().lower() == "darwin"

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux."""
        return platform.system().lower() == "linux"

    @staticmethod
    def find_executable(name: str) -> Path | None:
        """Find an executable in the system PATH."""
        result = shutil.which(name)
        return Path(result) if result else None

    @staticmethod
    def has_command(command: str) -> bool:
        """Check if a command is available in the system."""
        return SystemDetector.find_executable(command) is not None

    @staticmethod
    def get_shell() -> str:
        """Get the current shell name."""
        if SystemDetector.is_windows():
            return "cmd" if "COMSPEC" not in os.environ else os.environ["COMSPEC"].split("\\")[-1]
        else:
            shell = os.environ.get("SHELL", "/bin/bash")
            return shell.split("/")[-1]

    @staticmethod
    def get_python_executable() -> Path:
        """Get the current Python executable path."""
        return Path(sys.executable)

    @staticmethod
    def detect_package_managers() -> dict[str, bool]:
        """Detect available package managers."""
        managers = {
            "pip": SystemDetector.has_command("pip"),
            "pipx": SystemDetector.has_command("pipx"),
            "conda": SystemDetector.has_command("conda"),
            "poetry": SystemDetector.has_command("poetry"),
            "npm": SystemDetector.has_command("npm"),
            "yarn": SystemDetector.has_command("yarn"),
        }
        return managers


class FileOperations:
    """File and directory operations with error handling."""

    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """Ensure a directory exists, creating it if necessary."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    @staticmethod
    def backup_file(path: Path, backup_suffix: str = ".backup") -> Path | None:
        """Create a backup of a file if it exists."""
        if not path.exists():
            return None

        backup_path = path.with_suffix(path.suffix + backup_suffix)
        counter = 1

        # Find a unique backup name
        while backup_path.exists():
            backup_path = path.with_suffix(f"{path.suffix}{backup_suffix}.{counter}")
            counter += 1

        try:
            shutil.copy2(path, backup_path)
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup file {path}: {e}")
            return None

    @staticmethod
    def write_file(path: Path, content: str, backup: bool = True) -> bool:
        """Write content to a file with optional backup."""
        try:
            # Create backup if file exists and backup is requested
            backup_path = None
            if backup and path.exists():
                backup_path = FileOperations.backup_file(path)

            # Ensure parent directory exists
            if not FileOperations.ensure_directory(path.parent):
                return False

            # Write content
            path.write_text(content, encoding="utf-8")
            return True

        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            # Restore backup if write failed
            if backup_path and backup_path.exists():
                try:
                    shutil.move(str(backup_path), str(path))
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")
            return False

    @staticmethod
    def make_executable(path: Path) -> bool:
        """Make a file executable on Unix-like systems."""
        if SystemDetector.is_windows():
            return True  # Windows handles executability differently

        try:
            # Add execute permissions for user, group, and others
            current_mode = path.stat().st_mode
            new_mode = current_mode | 0o755
            path.chmod(new_mode)
            return True
        except Exception as e:
            logger.error(f"Failed to make file executable {path}: {e}")
            return False

    @staticmethod
    def find_files(directory: Path, pattern: str = "*", recursive: bool = True) -> list[Path]:
        """Find files matching a pattern in a directory."""
        try:
            if recursive:
                return list(directory.rglob(pattern))
            else:
                return list(directory.glob(pattern))
        except Exception as e:
            logger.error(f"Failed to find files in {directory}: {e}")
            return []

    @staticmethod
    def get_file_size(path: Path) -> int:
        """Get file size in bytes."""
        try:
            return path.stat().st_size
        except Exception:
            return 0


class ProcessRunner:
    """Execute system processes with error handling."""

    @staticmethod
    def run_command(
        command: list[str],
        cwd: Path | None = None,
        timeout: int = 30,
        capture_output: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a system command with proper error handling."""
        try:
            logger.debug(f"Running command: {' '.join(command)}")

            result = subprocess.run(
                command,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                check=check,
            )

            logger.debug(f"Command completed with return code: {result.returncode}")
            return result

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {' '.join(command)}")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed with code {e.returncode}: {' '.join(command)}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr}")
            raise
        except FileNotFoundError:
            logger.error(f"Command not found: {command[0]}")
            raise

    @staticmethod
    def run_python_command(
        module_args: list[str], cwd: Path | None = None, timeout: int = 30
    ) -> subprocess.CompletedProcess[str]:
        """Run a Python module command."""
        python_exe = SystemDetector.get_python_executable()
        command = [str(python_exe), *module_args]
        return ProcessRunner.run_command(command, cwd=cwd, timeout=timeout)

    @staticmethod
    def test_kuzu_memory_cli() -> bool:
        """Test if kuzu-memory CLI is available and working."""
        try:
            result = ProcessRunner.run_command(
                ["kuzu-memory", "--version"], timeout=10, check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def install_package(package: str, manager: str = "pip") -> bool:
        """Install a package using the specified package manager."""
        try:
            if manager == "pip":
                ProcessRunner.run_python_command(["-m", "pip", "install", package])
            elif manager == "pipx":
                ProcessRunner.run_command(["pipx", "install", package])
            elif manager == "conda":
                ProcessRunner.run_command(["conda", "install", "-y", package])
            else:
                logger.error(f"Unsupported package manager: {manager}")
                return False

            return True
        except Exception as e:
            logger.error(f"Failed to install {package} with {manager}: {e}")
            return False


class ProjectDetector:
    """Detect project types and configurations."""

    @staticmethod
    def detect_project_type(project_root: Path) -> list[str]:
        """Detect the type of project based on files present."""
        project_types: list[Any] = []

        # Python projects
        if any(
            (project_root / f).exists() for f in ["setup.py", "pyproject.toml", "requirements.txt"]
        ):
            project_types.append("python")

        # Node.js projects
        if (project_root / "package.json").exists():
            project_types.append("nodejs")

        # Git repositories
        if (project_root / ".git").exists():
            project_types.append("git")

        # Docker projects
        if any((project_root / f).exists() for f in ["Dockerfile", "docker-compose.yml"]):
            project_types.append("docker")

        # Various frameworks and tools
        framework_markers = {
            "django": ["manage.py", "django"],
            "flask": ["app.py", "wsgi.py"],
            "fastapi": ["main.py"],
            "react": ["src/App.js", "public/index.html"],
            "vue": ["src/main.js", "vue.config.js"],
            "angular": ["angular.json", "src/app"],
        }

        for framework, markers in framework_markers.items():
            if any((project_root / marker).exists() for marker in markers):
                project_types.append(framework)

        return project_types

    @staticmethod
    def find_config_files(project_root: Path) -> dict[str, Path]:
        """Find configuration files in a project."""
        config_patterns = {
            "kuzu_config": [".kuzu-memory/config.json", "kuzu-config.json"],
            "git_config": [".gitignore", ".git/config"],
            "python_config": ["pyproject.toml", "setup.py", "requirements.txt"],
            "node_config": ["package.json", ".npmrc", "yarn.lock"],
            "docker_config": ["Dockerfile", "docker-compose.yml"],
        }

        found_configs: dict[str, Any] = {}
        for config_type, patterns in config_patterns.items():
            for pattern in patterns:
                config_path = project_root / pattern
                if config_path.exists():
                    found_configs[config_type] = config_path
                    break  # Only store the first match for each type

        return found_configs

    @staticmethod
    def get_project_info(project_root: Path) -> dict[str, Any]:
        """Get comprehensive project information."""
        return {
            "root": str(project_root),
            "types": ProjectDetector.detect_project_type(project_root),
            "configs": {
                k: str(v) for k, v in ProjectDetector.find_config_files(project_root).items()
            },
            "size": len(list(project_root.rglob("*"))) if project_root.exists() else 0,
            "has_kuzu_memory": (project_root / ".kuzu-memory").exists(),
        }


class EnvironmentValidator:
    """Validate installation environment and requirements."""

    @staticmethod
    def check_python_version(min_version: tuple[int, int] = (3, 8)) -> bool:
        """Check if Python version meets requirements."""
        current_version = sys.version_info[:2]
        return current_version >= min_version

    @staticmethod
    def check_disk_space(required_mb: int = 100) -> bool:
        """Check available disk space."""
        try:
            # Get current directory disk usage
            usage = shutil.disk_usage(".")
            available_mb = usage.free / (1024 * 1024)
            return available_mb >= required_mb
        except Exception:
            return True  # Assume OK if can't check

    @staticmethod
    def check_write_permissions(path: Path) -> bool:
        """Check if we have write permissions to a path."""
        try:
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False

    @staticmethod
    def validate_environment(project_root: Path) -> dict[str, Any]:
        """Perform comprehensive environment validation."""
        return {
            "python_version_ok": EnvironmentValidator.check_python_version(),
            "disk_space_ok": EnvironmentValidator.check_disk_space(),
            "write_permissions_ok": EnvironmentValidator.check_write_permissions(project_root),
            "kuzu_memory_available": ProcessRunner.test_kuzu_memory_cli(),
            "system_info": SystemDetector.get_system_info(),
            "package_managers": SystemDetector.detect_package_managers(),
            "project_info": ProjectDetector.get_project_info(project_root),
        }
