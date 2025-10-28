"""
KuzuMemory Installer System

Provides adapter-based installers for different AI systems.
Each installer sets up the appropriate integration files and configuration.
"""

from .auggie import AuggieInstaller
from .auggie_mcp_installer import AuggieMCPInstaller
from .base import BaseInstaller, InstallationError, InstallationResult
from .claude_desktop import ClaudeDesktopHomeInstaller, ClaudeDesktopPipxInstaller
from .claude_hooks import ClaudeHooksInstaller
from .cursor_installer import CursorInstaller
from .detection import AISystemDetector, DetectedSystem, detect_ai_systems
from .registry import InstallerRegistry, get_installer, has_installer, list_installers
from .universal import UniversalInstaller
from .vscode_installer import VSCodeInstaller
from .windsurf_installer import WindsurfInstaller

__all__ = [
    "AISystemDetector",
    "AuggieInstaller",
    "AuggieMCPInstaller",
    "BaseInstaller",
    "ClaudeDesktopHomeInstaller",
    "ClaudeDesktopPipxInstaller",
    "ClaudeHooksInstaller",
    "CursorInstaller",
    "DetectedSystem",
    "InstallationError",
    "InstallationResult",
    "InstallerRegistry",
    "UniversalInstaller",
    "VSCodeInstaller",
    "WindsurfInstaller",
    "detect_ai_systems",
    "get_installer",
    "has_installer",
    "list_installers",
]
