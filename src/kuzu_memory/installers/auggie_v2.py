"""
Auggie/Claude Installer for KuzuMemory v2.0

Enhanced installer with version detection and auto-migration support.
Incorporates insights from Claude Code hooks v1.4.0.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .auggie_rules_v2 import (
    get_agents_md_v2,
    get_integration_rules_v2,
    get_quick_reference_v2,
)
from .auggie_versions import (
    CURRENT_VERSION,
    AuggieRuleMigrator,
    AuggieVersionDetector,
)
from .base import BaseInstaller, InstallationError, InstallationResult

logger = logging.getLogger(__name__)


class AuggieInstallerV2(BaseInstaller):
    """
    Enhanced Auggie installer with version detection and auto-migration.

    Features:
    - Detects existing installations
    - Automatic backup before upgrade
    - Seamless migration from v1.0.0 to v2.0.0
    - Improved rules based on Claude Code hooks insights
    """

    @property
    def ai_system_name(self) -> str:
        return "Auggie/Claude"

    @property
    def required_files(self) -> list[str]:
        return [
            "AGENTS.md",
            ".augment/rules/kuzu-memory-integration.md",
            ".augment/rules/memory-quick-reference.md",
        ]

    @property
    def description(self) -> str:
        return (
            "Sets up enhanced Augment rules for KuzuMemory integration (v2.0.0). "
            "Includes performance patterns, decision trees, and real-world examples."
        )

    def check_prerequisites(self) -> list[str]:
        """Check Auggie-specific prerequisites."""
        errors = super().check_prerequisites()

        # Check if KuzuMemory is initialized
        kuzu_dir = self.project_root / "kuzu-memories"
        if not kuzu_dir.exists():
            errors.append("KuzuMemory not initialized. Run 'kuzu-memory init' first.")

        return errors

    def install(
        self,
        force: bool = False,
        auto_migrate: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
        **kwargs: Any,
    ) -> InstallationResult:
        """
        Install or upgrade Auggie integration.

        Automatically updates existing installations (no force flag needed).
        Previous versions are backed up before updating.

        Args:
            auto_migrate: Automatically migrate from older versions (default: True)
            dry_run: If True, show what would be done without making changes
            verbose: If True, enable verbose output
            **kwargs: Additional options (for compatibility)

        Returns:
            InstallationResult with installation/upgrade details
        """
        try:
            if dry_run:
                logger.info("DRY RUN MODE - No changes will be made")

            # Check prerequisites
            errors = self.check_prerequisites()
            if errors:
                raise InstallationError(f"Prerequisites not met: {'; '.join(errors)}")

            # Check for existing installation and version
            detector = AuggieVersionDetector(self.project_root)
            installed_version = detector.get_installed_version()

            # Handle upgrade scenario
            if installed_version:
                if installed_version >= CURRENT_VERSION:
                    # Already at latest version - reinstall/update
                    logger.info(
                        f"Already at latest version {CURRENT_VERSION}. Updating installation."
                    )
                    # Continue with installation to update files
                else:
                    # Upgrade needed
                    if auto_migrate:
                        logger.info(
                            f"Detected v{installed_version}, upgrading to v{CURRENT_VERSION}"
                        )
                        return self._upgrade_installation(
                            installed_version, detector, dry_run=dry_run
                        )
                    else:
                        return InstallationResult(
                            success=False,
                            ai_system=self.ai_system_name,
                            files_created=[],
                            files_modified=[],
                            backup_files=[],
                            message=f"Upgrade available ({installed_version} → {CURRENT_VERSION}). "
                            f"Run with auto_migrate=True to upgrade.",
                            warnings=[],
                        )

            # Fresh install - check if files exist without version
            if not installed_version:
                existing_files: list[Any] = []
                for file_pattern in self.required_files:
                    file_path = self.project_root / file_pattern
                    if file_path.exists():
                        existing_files.append(str(file_path))

                if existing_files:
                    # Files exist but no version - update them
                    logger.info(
                        f"Auggie files exist without version marker. Updating to v{CURRENT_VERSION}."
                    )
                    # Create backups of existing files
                    for file_path_str in existing_files:
                        if not dry_run:
                            file_path = Path(file_path_str)
                            backup_path = self.create_backup(file_path)
                            if backup_path:
                                self.backup_files.append(backup_path)

            # Perform installation
            self._install_agents_md()
            self._install_integration_rules()
            self._install_quick_reference()

            # Write version file
            detector.write_version(CURRENT_VERSION)

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=f"Successfully installed Auggie integration v{CURRENT_VERSION}",
                warnings=self.warnings,
            )

        except Exception as e:
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=f"Installation failed: {e}",
                warnings=self.warnings,
            )

    def _upgrade_installation(
        self,
        from_version: dict[str, Any],
        detector: AuggieVersionDetector,
        dry_run: bool = False,
    ) -> InstallationResult:
        """
        Upgrade from existing version to current version.

        Args:
            from_version: Version being upgraded from
            detector: Version detector instance
            dry_run: If True, show what would be done without making changes

        Returns:
            InstallationResult with upgrade details
        """
        try:
            logger.info(f"Starting upgrade from {from_version} to {CURRENT_VERSION}")

            # Create migrator and backup
            migrator = AuggieRuleMigrator(self.project_root)
            migration_info = migrator.migrate()

            if not migration_info.get("success"):
                raise InstallationError(migration_info.get("message", "Migration failed"))

            backup_path = Path(migration_info.get("backup_path", ""))

            # Install new version
            self._install_agents_md()
            self._install_integration_rules()
            self._install_quick_reference()

            # Update version file
            detector.write_version(CURRENT_VERSION)

            changes = migration_info.get("changes", [])
            changes_summary = "\n  • ".join(changes) if changes else "See documentation"

            return InstallationResult(
                success=True,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=[backup_path] if backup_path else [],
                message=f"Successfully upgraded from v{from_version} to v{CURRENT_VERSION}\n\n"
                f"Backup created at: {backup_path}\n\n"
                f"What's New:\n  • {changes_summary}",
                warnings=self.warnings,
            )

        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            return InstallationResult(
                success=False,
                ai_system=self.ai_system_name,
                files_created=self.files_created,
                files_modified=self.files_modified,
                backup_files=self.backup_files,
                message=f"Upgrade failed: {e}. Your original files are backed up.",
                warnings=self.warnings,
            )

    def _install_agents_md(self) -> None:
        """Install the main AGENTS.md file with v2.0.0 content."""
        agents_path = self.project_root / "AGENTS.md"
        if not self.write_file(agents_path, get_agents_md_v2()):
            raise InstallationError("Failed to create AGENTS.md")

    def _install_integration_rules(self) -> None:
        """Install detailed integration rules with v2.0.0 content."""
        rules_dir = self.project_root / ".augment" / "rules"
        rules_path = rules_dir / "kuzu-memory-integration.md"
        if not self.write_file(rules_path, get_integration_rules_v2()):
            raise InstallationError("Failed to create integration rules")

    def _install_quick_reference(self) -> None:
        """Install quick reference guide with v2.0.0 content."""
        rules_dir = self.project_root / ".augment" / "rules"
        reference_path = rules_dir / "memory-quick-reference.md"
        if not self.write_file(reference_path, get_quick_reference_v2()):
            raise InstallationError("Failed to create quick reference")

    def check_upgrade_available(self) -> dict[str, Any]:
        """
        Check if an upgrade is available.

        Returns:
            Dictionary with upgrade information
        """
        detector = AuggieVersionDetector(self.project_root)
        return detector.get_upgrade_info()
