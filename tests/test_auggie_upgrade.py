"""
Tests for Auggie installer version detection and auto-migration.
"""

import json
import tempfile
from pathlib import Path

import pytest

from kuzu_memory.installers.auggie_v2 import AuggieInstallerV2
from kuzu_memory.installers.auggie_versions import (
    CURRENT_VERSION,
    AuggieVersion,
    AuggieVersionDetector,
)


class TestAuggieVersionDetection:
    """Test version detection functionality."""

    def test_parse_version_string(self):
        """Test parsing version strings."""
        v = AuggieVersion.from_string("1.2.3")
        assert v is not None
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert str(v) == "1.2.3"

    def test_version_comparison(self):
        """Test version comparison operators."""
        v1 = AuggieVersion(1, 0, 0)
        v2 = AuggieVersion(2, 0, 0)
        v3 = AuggieVersion(2, 0, 0)

        assert v1 < v2
        assert v2 > v1
        assert v2 == v3
        assert v2 >= v3
        assert v1 <= v2

    def test_detect_no_installation(self, tmp_path):
        """Test detection when nothing is installed."""
        detector = AuggieVersionDetector(tmp_path)
        assert detector.get_installed_version() is None

    def test_detect_from_version_file(self, tmp_path):
        """Test detection from .augment/.kuzu-version file."""
        version_dir = tmp_path / ".augment"
        version_dir.mkdir(parents=True)

        version_file = version_dir / ".kuzu-version"
        version_data = {"version": "1.0.0", "installed_at": "2025-09-15T10:00:00"}

        with open(version_file, "w") as f:
            json.dump(version_data, f)

        detector = AuggieVersionDetector(tmp_path)
        version = detector.get_installed_version()

        assert version is not None
        assert version == AuggieVersion(1, 0, 0)

    def test_detect_from_content_v1(self, tmp_path):
        """Test detection from file content for v1.0.0."""
        rules_dir = tmp_path / ".augment" / "rules"
        rules_dir.mkdir(parents=True)

        integration_file = rules_dir / "kuzu-memory-integration.md"
        # v1.0.0 content (no success indicators)
        content = """# KuzuMemory Integration Rules

## Automatic Memory Enhancement

### Rule: Enhance Technical Questions
"""
        with open(integration_file, "w") as f:
            f.write(content)

        detector = AuggieVersionDetector(tmp_path)
        version = detector.get_installed_version()

        assert version is not None
        assert version == AuggieVersion(1, 0, 0)

    def test_detect_from_content_v2(self, tmp_path):
        """Test detection from file content for v2.0.0."""
        rules_dir = tmp_path / ".augment" / "rules"
        rules_dir.mkdir(parents=True)

        integration_file = rules_dir / "kuzu-memory-integration.md"
        # v2.0.0 content (has success indicators)
        content = """# KuzuMemory Integration Rules (v2.0.0)

## Success Indicators

You're using KuzuMemory correctly when:
- ✅ Enhancement adds 2-5 relevant memories
"""
        with open(integration_file, "w") as f:
            f.write(content)

        detector = AuggieVersionDetector(tmp_path)
        version = detector.get_installed_version()

        assert version is not None
        assert version == AuggieVersion(2, 0, 0)

    def test_write_version_file(self, tmp_path):
        """Test writing version file."""
        detector = AuggieVersionDetector(tmp_path)
        version = AuggieVersion(2, 0, 0)

        success = detector.write_version(version)
        assert success

        version_file = tmp_path / ".augment" / ".kuzu-version"
        assert version_file.exists()

        with open(version_file) as f:
            data = json.load(f)
            assert data["version"] == "2.0.0"
            assert "installed_at" in data

    def test_needs_upgrade(self, tmp_path):
        """Test checking if upgrade is needed."""
        detector = AuggieVersionDetector(tmp_path)

        # Write old version
        detector.write_version(AuggieVersion(1, 0, 0))

        assert detector.needs_upgrade() is True

        # Write current version
        detector.write_version(CURRENT_VERSION)

        assert detector.needs_upgrade() is False

    def test_get_upgrade_info(self, tmp_path):
        """Test getting upgrade information."""
        detector = AuggieVersionDetector(tmp_path)

        # No installation
        info = detector.get_upgrade_info()
        assert info["needs_upgrade"] is False

        # Old version
        detector.write_version(AuggieVersion(1, 0, 0))
        info = detector.get_upgrade_info()

        assert info["needs_upgrade"] is True
        assert info["current_version"] == "1.0.0"
        assert info["latest_version"] == str(CURRENT_VERSION)
        assert "changes" in info


class TestAuggieInstallation:
    """Test Auggie installer with version detection."""

    def test_fresh_install(self, tmp_path):
        """Test fresh installation."""
        # Create kuzu-memories dir (prerequisite)
        kuzu_dir = tmp_path / "kuzu-memories"
        kuzu_dir.mkdir(parents=True)

        installer = AuggieInstallerV2(tmp_path)
        result = installer.install()

        assert result.success is True
        assert "v2.0.0" in result.message or str(CURRENT_VERSION) in result.message

        # Check files created
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / ".augment" / "rules" / "kuzu-memory-integration.md").exists()
        assert (tmp_path / ".augment" / "rules" / "memory-quick-reference.md").exists()

        # Check version file
        version_file = tmp_path / ".augment" / ".kuzu-version"
        assert version_file.exists()

        # Check content has v2 markers
        agents_file = tmp_path / "AGENTS.md"
        with open(agents_file) as f:
            content = f.read()
            assert "Success Indicators" in content
            assert "v2.0.0" in content

    def test_already_latest_version(self, tmp_path):
        """Test when already at latest version."""
        # Create kuzu-memories dir
        kuzu_dir = tmp_path / "kuzu-memories"
        kuzu_dir.mkdir(parents=True)

        # First install
        installer = AuggieInstallerV2(tmp_path)
        result1 = installer.install()
        assert result1.success is True

        # Try to install again
        result2 = installer.install()
        assert result2.success is True
        assert "Already at latest version" in result2.message

    def test_upgrade_from_v1_to_v2(self, tmp_path):
        """Test automatic upgrade from v1.0.0 to v2.0.0."""
        # Create kuzu-memories dir
        kuzu_dir = tmp_path / "kuzu-memories"
        kuzu_dir.mkdir(parents=True)

        # Create v1.0.0 installation
        rules_dir = tmp_path / ".augment" / "rules"
        rules_dir.mkdir(parents=True)

        # Write v1.0.0 content
        agents_file = tmp_path / "AGENTS.md"
        agents_file.write_text("# KuzuMemory Project Guidelines\n\nOld v1.0.0 content")

        integration_file = rules_dir / "kuzu-memory-integration.md"
        integration_file.write_text(
            "# KuzuMemory Integration Rules\n\n## Automatic Memory Enhancement"
        )

        # Write v1.0.0 version file
        detector = AuggieVersionDetector(tmp_path)
        detector.write_version(AuggieVersion(1, 0, 0))

        # Verify v1.0.0 is detected
        assert detector.get_installed_version() == AuggieVersion(1, 0, 0)

        # Run upgrade
        installer = AuggieInstallerV2(tmp_path)
        result = installer.install(auto_migrate=True)

        assert result.success is True
        assert "upgraded" in result.message.lower() or "Successfully" in result.message
        assert len(result.backup_files) > 0  # Backup was created

        # Verify v2.0.0 is now installed
        assert detector.get_installed_version() == CURRENT_VERSION

        # Check v2 content in AGENTS.md
        with open(agents_file) as f:
            content = f.read()
            assert "Success Indicators" in content
            assert "v2.0.0" in content

    def test_force_reinstall(self, tmp_path):
        """Test forcing reinstall over existing installation."""
        # Create kuzu-memories dir
        kuzu_dir = tmp_path / "kuzu-memories"
        kuzu_dir.mkdir(parents=True)

        # Create existing installation
        installer = AuggieInstallerV2(tmp_path)
        result1 = installer.install()
        assert result1.success is True

        # Force reinstall
        result2 = installer.install(force=True)
        assert result2.success is True

        # Files should still exist
        assert (tmp_path / "AGENTS.md").exists()


class TestAuggieBackup:
    """Test backup functionality during migration."""

    def test_backup_creates_files(self, tmp_path):
        """Test that backup creates all necessary files."""
        # Setup v1.0.0 installation
        kuzu_dir = tmp_path / "kuzu-memories"
        kuzu_dir.mkdir(parents=True)

        agents_file = tmp_path / "AGENTS.md"
        agents_file.write_text("Old content")

        rules_dir = tmp_path / ".augment" / "rules"
        rules_dir.mkdir(parents=True)

        integration_file = rules_dir / "kuzu-memory-integration.md"
        integration_file.write_text("Old integration")

        detector = AuggieVersionDetector(tmp_path)
        detector.write_version(AuggieVersion(1, 0, 0))

        # Run upgrade which should create backup
        installer = AuggieInstallerV2(tmp_path)
        result = installer.install(auto_migrate=True)

        assert result.success is True
        assert len(result.backup_files) > 0

        # Verify backup exists
        backup_dir = Path(result.backup_files[0])
        assert backup_dir.exists()
        assert (backup_dir / "AGENTS.md").exists()
        assert (backup_dir / "kuzu-memory-integration.md").exists()
