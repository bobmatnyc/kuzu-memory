"""
Auggie Integration Version Management and Migration System.

Handles version detection, upgrade notifications, and automatic migration
of Auggie integration rules.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuggieVersion:
    """Version information for Auggie integration."""

    def __init__(self, major: int, minor: int, patch: int) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AuggieVersion):
            return False
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __lt__(self, other: AuggieVersion) -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch

    def __le__(self, other: AuggieVersion) -> bool:
        return self == other or self < other

    def __gt__(self, other: AuggieVersion) -> bool:
        return not self <= other

    def __ge__(self, other: AuggieVersion) -> bool:
        return not self < other

    @classmethod
    def from_string(cls, version_str: str) -> AuggieVersion | None:
        """Parse version string like '1.0.0' into AuggieVersion."""
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if match:
            return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return None


# Current version of Auggie integration rules
CURRENT_VERSION = AuggieVersion(2, 0, 0)  # v2.0.0 with v1.4.0 improvements

# Version history
VERSION_HISTORY = {
    "1.0.0": {
        "date": "2025-09-15",
        "description": "Initial Auggie integration with basic rules",
        "files": [
            "AGENTS.md",
            ".augment/rules/kuzu-memory-integration.md",
            ".augment/rules/memory-quick-reference.md",
        ],
    },
    "2.0.0": {
        "date": "2025-10-25",
        "description": "Enhanced rules with Claude Code hooks insights, performance patterns, and auto-migration",
        "files": [
            "AGENTS.md",
            ".augment/rules/kuzu-memory-integration.md",
            ".augment/rules/memory-quick-reference.md",
        ],
        "changes": [
            "Added concrete success metrics",
            "Enhanced trigger patterns with negative examples",
            "Added decision tree for storage",
            "Added deduplication patterns from Claude Code hooks",
            "Added performance optimization patterns",
            "Added real-world examples from v1.4.0",
            "Added monitoring and feedback loop",
            "Added failure recovery patterns",
        ],
    },
}


class AuggieVersionDetector:
    """Detects installed version of Auggie integration."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.version_file = project_root / ".augment" / ".kuzu-version"

    def get_installed_version(self) -> AuggieVersion | None:
        """
        Get the currently installed version.

        Returns:
            AuggieVersion if found, None if not installed or no version file
        """
        if not self.version_file.exists():
            # Try to detect from file content patterns
            return self._detect_version_from_content()

        try:
            with open(self.version_file) as f:
                data = json.load(f)
                version_str = data.get("version", "")
                return AuggieVersion.from_string(version_str)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read version file: {e}")
            return self._detect_version_from_content()

    def _detect_version_from_content(self) -> AuggieVersion | None:
        """
        Detect version from file content patterns.

        v1.0.0 rules don't have success metrics or decision trees.
        v2.0.0 rules have "Success Indicators" and "Decision Tree" sections.
        """
        integration_file = self.project_root / ".augment" / "rules" / "kuzu-memory-integration.md"

        if not integration_file.exists():
            return None

        try:
            with open(integration_file) as f:
                content = f.read()

            # Check for v2.0.0 markers
            if "Success Indicators" in content or "Decision Tree" in content:
                return AuggieVersion(2, 0, 0)

            # Check for v1.0.0 markers
            if "Automatic Memory Enhancement" in content:
                return AuggieVersion(1, 0, 0)

            return None
        except OSError as e:
            logger.warning(f"Failed to read integration file for version detection: {e}")
            return None

    def write_version(self, version: AuggieVersion) -> bool:
        """
        Write version information to version file.

        Args:
            version: Version to write

        Returns:
            True if successful, False otherwise
        """
        try:
            self.version_file.parent.mkdir(parents=True, exist_ok=True)

            version_data = {
                "version": str(version),
                "installed_at": datetime.now().isoformat(),
                "kuzu_memory_version": "1.4.0",  # KuzuMemory version that installed this
            }

            with open(self.version_file, "w") as f:
                json.dump(version_data, f, indent=2)

            logger.info(f"Wrote version {version} to {self.version_file}")
            return True
        except OSError as e:
            logger.error(f"Failed to write version file: {e}")
            return False

    def needs_upgrade(self) -> bool:
        """
        Check if upgrade is needed.

        Returns:
            True if current installation is older than CURRENT_VERSION
        """
        installed = self.get_installed_version()
        if installed is None:
            return False  # Not installed, not an upgrade
        return installed < CURRENT_VERSION

    def get_upgrade_info(self) -> dict[str, Any]:
        """
        Get information about available upgrade.

        Returns:
            Dictionary with upgrade information
        """
        installed = self.get_installed_version()
        if installed is None or installed >= CURRENT_VERSION:
            return {"needs_upgrade": False}

        return {
            "needs_upgrade": True,
            "current_version": str(installed),
            "latest_version": str(CURRENT_VERSION),
            "changes": VERSION_HISTORY.get(str(CURRENT_VERSION), {}).get("changes", []),
            "description": VERSION_HISTORY.get(str(CURRENT_VERSION), {}).get("description", ""),
        }


class AuggieRuleMigrator:
    """Handles migration of Auggie rules between versions."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.detector = AuggieVersionDetector(project_root)
        self.backup_dir = project_root / ".augment" / "backups"

    def create_backup(self) -> Path | None:
        """
        Create backup of current rules before migration.

        Returns:
            Path to backup directory if successful, None otherwise
        """
        installed_version = self.detector.get_installed_version()
        if not installed_version:
            logger.warning("No version detected, cannot create backup")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"v{installed_version}_{timestamp}"

        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup files
            files_to_backup = [
                self.project_root / "AGENTS.md",
                self.project_root / ".augment" / "rules" / "kuzu-memory-integration.md",
                self.project_root / ".augment" / "rules" / "memory-quick-reference.md",
            ]

            for file_path in files_to_backup:
                if file_path.exists():
                    dest = backup_path / file_path.name
                    with open(file_path) as src, open(dest, "w") as dst:
                        dst.write(src.read())
                    logger.info(f"Backed up {file_path.name} to {dest}")

            # Create backup metadata
            metadata = {
                "version": str(installed_version),
                "timestamp": timestamp,
                "backed_up_files": [f.name for f in files_to_backup if f.exists()],
            }

            with open(backup_path / "backup_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Created backup at {backup_path}")
            return backup_path

        except OSError as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def can_auto_migrate(self, from_version: AuggieVersion) -> bool:
        """
        Check if automatic migration is supported.

        Args:
            from_version: Version to migrate from

        Returns:
            True if auto-migration is supported
        """
        # Currently support migration from v1.0.0 to v2.0.0
        return from_version == AuggieVersion(1, 0, 0)

    def migrate(self, force: bool = False) -> dict[str, Any]:
        """
        Migrate rules to current version.

        Args:
            force: Force migration even if not needed

        Returns:
            Dictionary with migration result
        """
        installed_version = self.detector.get_installed_version()

        if not installed_version:
            return {
                "success": False,
                "message": "No existing installation found. Use 'install' instead of 'upgrade'.",
            }

        if installed_version >= CURRENT_VERSION and not force:
            return {
                "success": True,
                "message": f"Already at latest version {CURRENT_VERSION}",
                "version": str(CURRENT_VERSION),
            }

        if not self.can_auto_migrate(installed_version):
            return {
                "success": False,
                "message": f"Auto-migration from {installed_version} to {CURRENT_VERSION} not supported. "
                f"Please reinstall with --force.",
                "version": str(installed_version),
            }

        # Create backup
        backup_path = self.create_backup()
        if not backup_path:
            return {
                "success": False,
                "message": "Failed to create backup. Migration aborted for safety.",
            }

        logger.info(f"Starting migration from {installed_version} to {CURRENT_VERSION}")

        return {
            "success": True,
            "message": f"Ready to migrate from {installed_version} to {CURRENT_VERSION}",
            "from_version": str(installed_version),
            "to_version": str(CURRENT_VERSION),
            "backup_path": str(backup_path),
            "changes": VERSION_HISTORY.get(str(CURRENT_VERSION), {}).get("changes", []),
        }
