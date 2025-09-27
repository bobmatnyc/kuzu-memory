"""
KuzuMemory Installer System

Provides adapter-based installers for different AI systems.
Each installer sets up the appropriate integration files and configuration.
"""

from .auggie import AuggieInstaller
from .base import BaseInstaller, InstallationError, InstallationResult
from .claude_hooks import ClaudeHooksInstaller
from .registry import InstallerRegistry, get_installer, has_installer, list_installers
from .universal import UniversalInstaller

__all__ = [
    "AuggieInstaller",
    "BaseInstaller",
    "ClaudeHooksInstaller",
    "InstallationError",
    "InstallationResult",
    "InstallerRegistry",
    "UniversalInstaller",
    "get_installer",
    "has_installer",
    "list_installers",
]
