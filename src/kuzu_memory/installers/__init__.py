"""
KuzuMemory Installer System

Provides adapter-based installers for different AI systems.
Each installer sets up the appropriate integration files and configuration.
"""

from .base import BaseInstaller, InstallationResult, InstallationError
from .auggie import AuggieInstaller
from .universal import UniversalInstaller
from .claude_hooks import ClaudeHooksInstaller
from .registry import InstallerRegistry, get_installer, list_installers, has_installer

__all__ = [
    'BaseInstaller',
    'InstallationResult',
    'InstallationError',
    'AuggieInstaller',
    'UniversalInstaller',
    'ClaudeHooksInstaller',
    'InstallerRegistry',
    'get_installer',
    'list_installers',
    'has_installer',
]
