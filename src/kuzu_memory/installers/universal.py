"""
Universal Installer for KuzuMemory

Creates generic integration files that work with any AI system.
Refactored to use modular system utilities and package managers.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseInstaller, InstallationError, InstallationResult
from .package_managers import ExampleGenerator
from .system_utils import EnvironmentValidator

logger = logging.getLogger(__name__)


class UniversalInstaller(BaseInstaller):
    """
    Universal installer for any AI system integration.

    Creates generic integration files and examples that can be
    adapted for any AI system.
    """

    @property
    def ai_system_name(self) -> str:
        return "Universal"

    @property
    def required_files(self) -> list[str]:
        return [
            "kuzu-memory-integration.md",
            "examples/python_integration.py",
            "examples/javascript_integration.js",
            "examples/shell_integration.sh",
        ]

    @property
    def description(self) -> str:
        return (
            "Creates universal integration files and examples that work with any AI system. "
            "Includes Python, JavaScript, and shell integration examples."
        )

    def install(self, force: bool = False, **kwargs: Any) -> InstallationResult:
        """
        Install universal integration files.

        Args:
            force: Force installation even if files exist
            **kwargs: Additional options
                - language: Primary language for examples (python, javascript, shell)
                - ai_system: Name of AI system for customization

        Returns:
            InstallationResult with installation details
        """
        try:
            # Check prerequisites
            errors = self.check_prerequisites()
            if errors:
                raise InstallationError(f"Prerequisites not met: {'; '.join(errors)}")

            # Get options
            primary_language = kwargs.get("language", "python")
            ai_system = kwargs.get("ai_system", "Your AI System")

            # Check if already installed and not forcing
            if not force:
                existing_files = self._check_existing_files()
                if existing_files:
                    raise InstallationError(
                        f"Universal integration already exists. Use --force to overwrite. "
                        f"Existing files: {', '.join(existing_files)}"
                    )

            # Install integration components
            self._install_integration_guide(ai_system)
            self._install_examples()

            # Add language-specific note
            if primary_language != "python":
                self.warnings.append(
                    f"Primary language set to {primary_language}. "
                    f"See examples/{primary_language}_integration for your language."
                )

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=f"Successfully installed universal integration for {ai_system}",
                warnings=self.warnings,
            )

        except Exception as e:
            logger.error(f"Universal installation failed: {e}")
            raise InstallationError(f"Installation failed: {e}")

    def check_prerequisites(self) -> list[str]:
        """Check installation prerequisites."""
        errors: list[Any] = []

        # Validate environment
        env_status = EnvironmentValidator.validate_environment(self.project_root)

        if not env_status["python_version_ok"]:
            errors.append("Python 3.8+ required")

        if not env_status["write_permissions_ok"]:
            errors.append(f"Write permissions required for {self.project_root}")

        if not env_status["disk_space_ok"]:
            errors.append("Insufficient disk space")

        if not env_status["kuzu_memory_available"]:
            self.warnings.append(
                "kuzu-memory CLI not available - examples will include installation instructions"
            )

        return errors

    def uninstall(self) -> InstallationResult:
        """Uninstall universal integration files."""
        try:
            removed_files: list[Any] = []

            # Remove main integration files
            for file_pattern in self.required_files:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    file_path.unlink()
                    removed_files.append(str(file_path))

            # Remove examples directory if empty
            examples_dir = self.project_root / "examples"
            if examples_dir.exists() and not any(examples_dir.iterdir()):
                examples_dir.rmdir()
                removed_files.append(str(examples_dir))

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=[],
                files_modified=[],
                backup_files=[],
                message=f"Successfully uninstalled universal integration. Removed {len(removed_files)} files.",
                warnings=[],
            )

        except Exception as e:
            logger.error(f"Universal uninstallation failed: {e}")
            raise InstallationError(f"Uninstallation failed: {e}")

    def _check_existing_files(self) -> list[str]:
        """Check for existing installation files."""
        existing_files: list[Any] = []
        for file_pattern in self.required_files:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                existing_files.append(str(file_path))
        return existing_files

    def _install_integration_guide(self, ai_system: str) -> None:
        """Install the main integration guide."""
        try:
            if ExampleGenerator.create_integration_guide(self.project_root, ai_system):
                guide_path = self.project_root / "kuzu-memory-integration.md"
                self.files_created.append(guide_path)
            else:
                raise InstallationError("Failed to create integration guide")

        except Exception as e:
            raise InstallationError(f"Failed to install integration guide: {e}")

    def _install_examples(self) -> None:
        """Install all integration examples."""
        examples_created = 0

        # Install Python example
        try:
            if ExampleGenerator.create_python_example(self.project_root):
                python_path = self.project_root / "examples" / "python_integration.py"
                self.files_created.append(python_path)
                examples_created += 1
        except Exception as e:
            self.warnings.append(f"Failed to create Python example: {e}")

        # Install JavaScript example
        try:
            if ExampleGenerator.create_javascript_example(self.project_root):
                js_path = self.project_root / "examples" / "javascript_integration.js"
                self.files_created.append(js_path)
                examples_created += 1
        except Exception as e:
            self.warnings.append(f"Failed to create JavaScript example: {e}")

        # Install Shell example
        try:
            if ExampleGenerator.create_shell_example(self.project_root):
                shell_path = self.project_root / "examples" / "shell_integration.sh"
                self.files_created.append(shell_path)
                examples_created += 1
        except Exception as e:
            self.warnings.append(f"Failed to create shell example: {e}")

        if examples_created == 0:
            raise InstallationError("Failed to create any integration examples")

        logger.info(f"Created {examples_created} integration examples")

    def get_status(self) -> dict[str, Any]:
        """Get installation status information."""
        status: dict[str, Any] = {
            "installed": False,
            "files_exist": [],
            "files_missing": [],
            "examples_available": [],
            "system_info": {},
        }

        # Check file existence
        for file_pattern in self.required_files:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                status["files_exist"].append(str(file_path))
            else:
                status["files_missing"].append(file_pattern)

        status["installed"] = len(status["files_missing"]) == 0

        # Check available examples
        examples_dir = self.project_root / "examples"
        if examples_dir.exists():
            for example_file in examples_dir.glob("*_integration.*"):
                status["examples_available"].append(example_file.name)

        # Get system information
        env_status = EnvironmentValidator.validate_environment(self.project_root)
        status["system_info"] = {
            "kuzu_memory_cli": env_status["kuzu_memory_available"],
            "write_permissions": env_status["write_permissions_ok"],
            "python_version": env_status["python_version_ok"],
            "platform": env_status["system_info"]["platform"],
        }

        return status

    def get_integration_info(self) -> dict[str, Any]:
        """Get information about available integrations."""
        return {
            "name": self.ai_system_name,
            "description": self.description,
            "supported_languages": ["python", "javascript", "shell"],
            "required_files": self.required_files,
            "features": [
                "Universal compatibility via CLI interface",
                "Sub-100ms context retrieval",
                "Async learning operations",
                "Project-specific memory",
                "Multiple language examples",
                "Complete integration guide",
            ],
            "prerequisites": [
                "Python 3.8+",
                "Write permissions to project directory",
                "kuzu-memory CLI (recommended)",
            ],
        }
