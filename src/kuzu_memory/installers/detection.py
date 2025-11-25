"""
AI system auto-detection for KuzuMemory MCP installers.

Detects which AI coding assistants are installed or configured in the project.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DetectedSystem:
    """Information about a detected AI system."""

    name: str
    installer_name: str
    config_type: str  # "project" or "global"
    config_path: Path
    exists: bool  # True if config file exists
    can_install: bool  # True if installation is possible
    notes: str = ""


class AISystemDetector:
    """
    Detects installed AI coding assistants and their MCP configurations.

    Supports both project-specific and global configurations.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """
        Initialize detector.

        Args:
            project_root: Project root directory (optional for global detection)
        """
        self.project_root = project_root or Path.cwd()

    def detect_all(self) -> list[DetectedSystem]:
        """
        Detect all AI systems (both project and global).

        Returns:
            List of detected systems
        """
        detected: list[Any] = []

        # Detect project-specific systems
        detected.extend(self._detect_project_systems())

        # Detect global systems
        detected.extend(self._detect_global_systems())

        # Sort by name
        detected.sort(key=lambda x: x.name)

        return detected

    def _detect_project_systems(self) -> list[DetectedSystem]:
        """Detect project-specific AI systems."""
        systems: list[Any] = []

        # Cursor IDE (.cursor/mcp.json)
        cursor_path = self.project_root / ".cursor" / "mcp.json"
        systems.append(
            DetectedSystem(
                name="Cursor IDE",
                installer_name="cursor",
                config_type="project",
                config_path=cursor_path,
                exists=cursor_path.exists(),
                can_install=self.project_root.exists(),
                notes="Project-specific MCP configuration",
            )
        )

        # VS Code (.vscode/mcp.json)
        vscode_path = self.project_root / ".vscode" / "mcp.json"
        systems.append(
            DetectedSystem(
                name="VS Code (Claude Extension)",
                installer_name="vscode",
                config_type="project",
                config_path=vscode_path,
                exists=vscode_path.exists(),
                can_install=self.project_root.exists(),
                notes="Project-specific MCP configuration",
            )
        )

        # Roo Code (.roo/mcp.json)
        roo_path = self.project_root / ".roo" / "mcp.json"
        systems.append(
            DetectedSystem(
                name="Roo Code",
                installer_name="roo-code",
                config_type="project",
                config_path=roo_path,
                exists=roo_path.exists(),
                can_install=self.project_root.exists(),
                notes="Project-specific MCP configuration (not yet implemented)",
            )
        )

        # Continue (.continue/config.yaml)
        continue_path = self.project_root / ".continue" / "config.yaml"
        systems.append(
            DetectedSystem(
                name="Continue",
                installer_name="continue",
                config_type="project",
                config_path=continue_path,
                exists=continue_path.exists(),
                can_install=self.project_root.exists(),
                notes="Project-specific configuration (not yet implemented)",
            )
        )

        # JetBrains Junie (.junie/mcp/mcp.json)
        junie_path = self.project_root / ".junie" / "mcp" / "mcp.json"
        systems.append(
            DetectedSystem(
                name="JetBrains Junie",
                installer_name="junie",
                config_type="project",
                config_path=junie_path,
                exists=junie_path.exists(),
                can_install=self.project_root.exists(),
                notes="Project-specific MCP configuration (not yet implemented)",
            )
        )

        return systems

    def _detect_global_systems(self) -> list[DetectedSystem]:
        """Detect globally-installed AI systems."""
        systems: list[Any] = []
        home = Path.home()

        # Windsurf (~/.codeium/windsurf/mcp_config.json)
        windsurf_path = home / ".codeium" / "windsurf" / "mcp_config.json"
        windsurf_dir = home / ".codeium" / "windsurf"
        systems.append(
            DetectedSystem(
                name="Windsurf IDE",
                installer_name="windsurf",
                config_type="global",
                config_path=windsurf_path,
                exists=windsurf_path.exists(),
                can_install=windsurf_dir.exists(),
                notes="Global (user-wide) MCP configuration",
            )
        )

        # Cursor global (~/.cursor/mcp.json)
        cursor_global_path = home / ".cursor" / "mcp.json"
        cursor_global_dir = home / ".cursor"
        systems.append(
            DetectedSystem(
                name="Cursor IDE (Global)",
                installer_name="cursor-global",
                config_type="global",
                config_path=cursor_global_path,
                exists=cursor_global_path.exists(),
                can_install=cursor_global_dir.exists(),
                notes="Global (user-wide) MCP configuration (not yet implemented)",
            )
        )

        return systems

    def detect_installed(self) -> list[DetectedSystem]:
        """
        Detect AI systems that are actively installed/configured.

        Returns:
            List of systems with existing configurations
        """
        all_systems = self.detect_all()
        return [s for s in all_systems if s.exists]

    def detect_available(self) -> list[DetectedSystem]:
        """
        Detect AI systems that can be installed.

        Returns:
            List of systems where installation is possible
        """
        all_systems = self.detect_all()
        return [s for s in all_systems if s.can_install]

    def has_system(self, installer_name: str) -> bool:
        """
        Check if a specific AI system is detected.

        Args:
            installer_name: Installer name to check

        Returns:
            True if system is detected and can be installed
        """
        available = self.detect_available()
        return any(s.installer_name == installer_name for s in available)

    def get_system(self, installer_name: str) -> DetectedSystem | None:
        """
        Get information about a specific AI system.

        Args:
            installer_name: Installer name

        Returns:
            DetectedSystem or None if not found
        """
        all_systems = self.detect_all()
        for system in all_systems:
            if system.installer_name == installer_name:
                return system
        return None

    def get_recommended_systems(self) -> list[DetectedSystem]:
        """
        Get recommended systems to install.

        Returns systems that:
        1. Can be installed (directories exist)
        2. Don't have existing MCP configs

        Returns:
            List of recommended systems
        """
        all_systems = self.detect_all()
        return [s for s in all_systems if s.can_install and not s.exists]


def detect_ai_systems(project_root: Path | None = None) -> list[str]:
    """
    Detect installed AI systems by checking for config files.

    Args:
        project_root: Project root directory (optional)

    Returns:
        List of installer names for detected systems
    """
    detector = AISystemDetector(project_root)
    available = detector.detect_available()
    return [s.installer_name for s in available]


def get_installed_systems(project_root: Path | None = None) -> list[str]:
    """
    Get AI systems with existing MCP configurations.

    Args:
        project_root: Project root directory (optional)

    Returns:
        List of installer names for installed systems
    """
    detector = AISystemDetector(project_root)
    installed = detector.detect_installed()
    return [s.installer_name for s in installed]


def get_system_info(installer_name: str, project_root: Path | None = None) -> dict[str, Any] | None:
    """
    Get detailed information about an AI system.

    Args:
        installer_name: Installer name
        project_root: Project root directory (optional)

    Returns:
        Dictionary with system information or None if not found
    """
    detector = AISystemDetector(project_root)
    system = detector.get_system(installer_name)

    if not system:
        return None

    return {
        "name": system.name,
        "installer_name": system.installer_name,
        "config_type": system.config_type,
        "config_path": str(system.config_path),
        "exists": system.exists,
        "can_install": system.can_install,
        "notes": system.notes,
    }
