"""
Base installer for KuzuMemory AI system integrations.

Provides common functionality for all installer adapters.
"""

from __future__ import annotations

import logging
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class InstallationError(Exception):
    """Raised when installation fails."""

    pass


@dataclass
class InstallationResult:
    """Result of an installation operation."""

    success: bool
    ai_system: str
    files_created: list[Path]
    files_modified: list[Path]
    backup_files: list[Path]
    message: str
    warnings: list[str]

    def __post_init__(self) -> None:
        """Ensure all paths are Path objects."""
        self.files_created = [Path(f) for f in self.files_created]
        self.files_modified = [Path(f) for f in self.files_modified]
        self.backup_files = [Path(f) for f in self.backup_files]


@dataclass
class InstalledSystem:
    """Information about a detected installed system."""

    name: str
    ai_system: str
    is_installed: bool
    health_status: str  # "healthy", "needs_repair", "broken"
    files_present: list[Path]
    files_missing: list[Path]
    has_mcp: bool
    details: dict[str, Any]


class BaseInstaller(ABC):
    """
    Base class for AI system installers.

    Each installer adapter inherits from this class and implements
    the specific installation logic for their AI system.
    """

    def __init__(self, project_root: Path) -> None:
        """
        Initialize installer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.backup_dir: Path = self.project_root / ".kuzu-memory-backups"
        self.files_created: list[Path] = []
        self.files_modified: list[Path] = []
        self.backup_files: list[Path] = []
        self.warnings: list[str] = []

    @property
    @abstractmethod
    def ai_system_name(self) -> str:
        """Name of the AI system this installer supports."""
        pass

    @property
    @abstractmethod
    def required_files(self) -> list[str]:
        """List of files that will be created/modified by this installer."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this installer does."""
        pass

    def check_prerequisites(self) -> list[str]:
        """
        Check if prerequisites are met for installation.

        Returns:
            List of error messages, empty if all prerequisites are met
        """
        errors = []

        # Check if project root exists and is writable
        if not self.project_root.exists():
            errors.append(f"Project root does not exist: {self.project_root}")
        elif not os.access(self.project_root, os.W_OK):
            errors.append(f"Project root is not writable: {self.project_root}")

        return errors

    def create_backup(self, file_path: Path) -> Path | None:
        """
        Create backup of existing file.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file, or None if no backup needed
        """
        if not file_path.exists():
            return None

        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)

        # Create backup with timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            self.backup_files.append(backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.warning(f"Failed to create backup of {file_path}: {e}")
            return None

    def write_file(self, file_path: Path, content: str, backup: bool = True) -> bool:
        """
        Write content to file, optionally creating backup.

        Args:
            file_path: Path to write to
            content: Content to write
            backup: Whether to create backup of existing file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if file exists and backup requested
            if backup and file_path.exists():
                self.create_backup(file_path)
                self.files_modified.append(file_path)
            else:
                self.files_created.append(file_path)

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Created/updated file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return False

    def copy_template(
        self,
        template_name: str,
        destination: Path,
        replacements: dict[str, str] | None = None,
    ) -> bool:
        """
        Copy template file with optional string replacements.

        Args:
            template_name: Name of template file
            destination: Destination path
            replacements: Dict of string replacements {old: new}

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find template file
            template_dir = Path(__file__).parent / "templates"
            template_path = template_dir / template_name

            if not template_path.exists():
                logger.error(f"Template not found: {template_path}")
                return False

            # Read template content
            with open(template_path, encoding="utf-8") as f:
                content = f.read()

            # Apply replacements
            if replacements:
                for old, new in replacements.items():
                    content = content.replace(old, new)

            # Write to destination
            return self.write_file(destination, content)

        except Exception as e:
            logger.error(f"Failed to copy template {template_name}: {e}")
            return False

    @abstractmethod
    def install(self, force: bool = False, **kwargs: Any) -> InstallationResult:
        """
        Install integration for the AI system.

        Args:
            force: Force installation even if files exist
            **kwargs: Additional installer-specific options

        Returns:
            InstallationResult with details of what was installed
        """
        pass

    def uninstall(self) -> InstallationResult:
        """
        Uninstall integration for the AI system.

        Returns:
            InstallationResult with details of what was removed
        """
        files_removed = []
        errors = []

        try:
            # Remove files that were created by this installer
            for file_pattern in self.required_files:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                        else:
                            shutil.rmtree(file_path)
                        files_removed.append(file_path)
                        logger.info(f"Removed: {file_path}")
                    except Exception as e:
                        errors.append(f"Failed to remove {file_path}: {e}")

            # Restore backups if they exist
            restored_files = []
            if self.backup_dir.exists():
                for backup_file in self.backup_dir.glob("*.backup_*"):
                    try:
                        # Extract original filename
                        original_name = backup_file.name.split(".backup_")[0]
                        original_path = self.project_root / original_name

                        # Restore backup
                        shutil.copy2(backup_file, original_path)
                        restored_files.append(original_path)

                        # Remove backup
                        backup_file.unlink()

                    except Exception as e:
                        errors.append(f"Failed to restore backup {backup_file}: {e}")

            success = len(errors) == 0
            message = f"Successfully uninstalled {self.ai_system_name} integration"
            if errors:
                message += f" with {len(errors)} errors"

            return InstallationResult(
                success=success,
                ai_system=self.ai_system_name,
                files_created=[],  # Files were removed
                files_modified=restored_files,
                backup_files=[],  # Backups were used/removed
                message=message,
                warnings=errors,
            )

        except Exception as e:
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=[],
                backup_files=[],
                message=f"Uninstallation failed: {e}",
                warnings=[],
            )

    def get_status(self) -> dict[str, Any]:
        """
        Get installation status for this AI system.

        Returns:
            Dict with installation status information
        """
        status: dict[str, Any] = {
            "ai_system": self.ai_system_name,
            "installed": True,
            "files_present": [],
            "files_missing": [],
            "has_backups": False,
        }

        # Check if required files exist
        for file_pattern in self.required_files:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                status["files_present"].append(str(file_path))
            else:
                status["files_missing"].append(str(file_path))

        # Check if any files are missing
        status["installed"] = len(status["files_missing"]) == 0

        # Check for backups
        if self.backup_dir.exists():
            backups = list(self.backup_dir.glob("*.backup_*"))
            status["has_backups"] = len(backups) > 0
            status["backup_count"] = len(backups)

        return status

    def detect_installation(self) -> InstalledSystem:
        """
        Detect if this system is installed and its health status.

        Returns:
            InstalledSystem object with detection details
        """
        files_present = []
        files_missing = []

        # Check required files
        for file_pattern in self.required_files:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                files_present.append(file_path)
            else:
                files_missing.append(file_path)

        is_installed = len(files_present) > 0
        all_files_present = len(files_missing) == 0

        # Determine health status
        if not is_installed:
            health_status = "not_installed"
        elif all_files_present:
            health_status = "healthy"
        else:
            health_status = "needs_repair"

        # Check MCP configuration (subclass can override)
        has_mcp = self._check_mcp_configured()

        return InstalledSystem(
            name=self.ai_system_name,
            ai_system=self.ai_system_name,
            is_installed=is_installed,
            health_status=health_status,
            files_present=files_present,
            files_missing=files_missing,
            has_mcp=has_mcp,
            details={
                "total_files": len(self.required_files),
                "present_count": len(files_present),
                "missing_count": len(files_missing),
            },
        )

    def _check_mcp_configured(self) -> bool:
        """
        Check if MCP server is configured for this system.

        Subclasses should override to provide specific checks.

        Returns:
            True if MCP is configured, False otherwise
        """
        return False
