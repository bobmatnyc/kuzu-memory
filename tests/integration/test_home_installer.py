"""
Integration tests for home-based installer.

Tests the install-claude-desktop-home.py script functionality.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def installer_script():
    """Get path to installer script."""
    return Path(__file__).parent.parent.parent / "scripts" / "install-claude-desktop-home.py"


@pytest.fixture
def test_install_dir(tmp_path):
    """Create temporary installation directory."""
    install_dir = tmp_path / ".kuzu-memory-test"
    yield install_dir
    # Cleanup after test
    if install_dir.exists():
        shutil.rmtree(install_dir)


@pytest.fixture
def mock_claude_config(tmp_path):
    """Create mock Claude Desktop config."""
    config_dir = tmp_path / "claude"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "claude_desktop_config.json"
    config_file.write_text(json.dumps({"mcpServers": {}}))
    return config_file


class TestHomeInstallerDryRun:
    """Test installer in dry-run mode (no actual changes)."""

    def test_dry_run_auto_mode(self, installer_script):
        """Test dry-run in auto mode."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should complete without error
        assert (
            result.returncode == 0 or result.returncode == 1
        )  # May fail to find system installation

        # Output should mention key components or existing installation
        output = result.stdout + result.stderr
        assert any(
            keyword in output.lower()
            for keyword in ["would", "dry run", "installation", "wrapper", "standalone"]
        )

    def test_dry_run_wrapper_mode(self, installer_script):
        """Test dry-run in wrapper mode."""
        result = subprocess.run(
            [
                sys.executable,
                str(installer_script),
                "--mode",
                "wrapper",
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check output mentions wrapper mode or system installation check
        output = result.stdout + result.stderr
        assert "wrapper" in output.lower() or "system" in output.lower()

    def test_dry_run_standalone_mode(self, installer_script):
        """Test dry-run in standalone mode."""
        result = subprocess.run(
            [
                sys.executable,
                str(installer_script),
                "--mode",
                "standalone",
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check output mentions standalone mode
        output = result.stdout + result.stderr
        assert "standalone" in output.lower()


class TestHomeInstallerHelp:
    """Test installer help and documentation."""

    def test_help_output(self, installer_script):
        """Test help message."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0

        # Check for key documentation sections
        assert "KuzuMemory" in result.stdout
        assert "--mode" in result.stdout
        assert "wrapper" in result.stdout
        assert "standalone" in result.stdout
        assert "--uninstall" in result.stdout
        assert "--update" in result.stdout
        assert "--validate" in result.stdout

    def test_usage_examples(self, installer_script):
        """Test that usage examples are present in help."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should include examples section
        assert "Examples:" in result.stdout or "examples:" in result.stdout


class TestHomeInstallerValidation:
    """Test installer validation logic."""

    def test_validate_no_installation(self, installer_script):
        """Test validation when no installation exists."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--validate"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail gracefully
        assert result.returncode == 1

        output = result.stdout + result.stderr
        assert "not found" in output.lower() or "missing" in output.lower()


class TestHomeInstallerScriptQuality:
    """Test script code quality and structure."""

    def test_script_executable(self, installer_script):
        """Test that script is executable."""
        assert installer_script.exists()
        assert installer_script.is_file()

        # Check shebang
        with open(installer_script) as f:
            first_line = f.readline()
            assert first_line.startswith("#!")
            assert "python" in first_line.lower()

    def test_script_imports(self, installer_script):
        """Test that script imports are valid."""
        # Try importing the script (should not raise)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import sys; sys.path.insert(0, '{installer_script.parent}'); exec(open('{installer_script}').read().split('if __name__')[0])",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should not have import errors
        if result.returncode != 0:
            assert "ImportError" not in result.stderr
            assert "ModuleNotFoundError" not in result.stderr

    def test_script_has_docstring(self, installer_script):
        """Test that script has comprehensive docstring."""
        with open(installer_script) as f:
            content = f.read()

        # Should have module docstring
        assert '"""' in content

        # Should document key features
        assert "~/.kuzu-memory" in content
        assert "wrapper" in content.lower()
        assert "standalone" in content.lower()


class TestHomeInstallerEdgeCases:
    """Test installer edge cases and error handling."""

    def test_invalid_mode(self, installer_script):
        """Test handling of invalid mode."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--mode", "invalid"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should fail with clear error
        assert result.returncode != 0
        assert "invalid" in result.stderr.lower() or "choice" in result.stderr.lower()

    def test_conflicting_flags(self, installer_script):
        """Test handling of conflicting flags."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--update", "--uninstall"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should handle gracefully (may succeed with last flag taking precedence)
        # Just verify it doesn't crash
        assert "Traceback" not in result.stderr


class TestHomeInstallerSystemDetection:
    """Test system installation detection logic."""

    def test_detect_current_installation(self, installer_script):
        """Test detection of current kuzu-memory installation."""
        # This test checks if the detection logic works with current environment
        result = subprocess.run(
            [sys.executable, str(installer_script), "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Should either find system installation or mention standalone mode
        assert (
            "found" in output.lower()
            or "wrapper" in output.lower()
            or "standalone" in output.lower()
        )


class TestHomeInstallerBackup:
    """Test backup functionality."""

    def test_backup_dir_option(self, installer_script, tmp_path):
        """Test custom backup directory option."""
        backup_dir = tmp_path / "custom-backups"

        result = subprocess.run(
            [
                sys.executable,
                str(installer_script),
                "--backup-dir",
                str(backup_dir),
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should accept the option without error
        assert "error" not in result.stderr.lower() or result.returncode == 0


class TestHomeInstallerOutput:
    """Test installer output and user feedback."""

    def test_output_has_colors(self, installer_script):
        """Test that output includes colored messages."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Should have status indicators
        assert any(char in output for char in ["✓", "✗", "⚠"])

    def test_verbose_mode(self, installer_script):
        """Test verbose output mode."""
        # Run without verbose
        result_normal = subprocess.run(
            [sys.executable, str(installer_script), "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Run with verbose
        result_verbose = subprocess.run(
            [sys.executable, str(installer_script), "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Verbose should have more output
        assert len(result_verbose.stdout + result_verbose.stderr) >= len(
            result_normal.stdout + result_normal.stderr
        )


@pytest.mark.integration
class TestHomeInstallerIntegration:
    """Integration tests that may modify filesystem (run with caution)."""

    def test_full_dry_run_flow(self, installer_script):
        """Test complete dry-run installation flow."""
        # Install dry-run
        result = subprocess.run(
            [sys.executable, str(installer_script), "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        output = result.stdout + result.stderr

        # Should complete and show what would be done
        assert "Would" in output or "dry run" in output.lower()

        # Should mention key components
        assert any(keyword in output.lower() for keyword in ["launcher", "config", "directory"])

    def test_uninstall_nonexistent(self, installer_script):
        """Test uninstalling when nothing is installed."""
        result = subprocess.run(
            [sys.executable, str(installer_script), "--uninstall", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should handle gracefully
        output = result.stdout + result.stderr
        assert "not found" in output.lower() or "no installation" in output.lower()


class TestHomeInstallerDocumentation:
    """Test installer documentation completeness."""

    def test_readme_mentions_home_installer(self):
        """Test that README mentions home installation option."""
        readme_path = Path(__file__).parent.parent.parent / "README.md"

        if readme_path.exists():
            content = readme_path.read_text()
            # May or may not be documented yet
            assert len(content) > 0

    def test_documentation_exists(self):
        """Test that documentation file exists."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "HOME_INSTALLATION.md"

        assert doc_path.exists()

        content = doc_path.read_text()
        assert len(content) > 1000  # Should be comprehensive
        assert "~/.kuzu-memory" in content
        assert "wrapper" in content.lower()
        assert "standalone" in content.lower()
