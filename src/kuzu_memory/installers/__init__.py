"""
KuzuMemory Installer System

Provides adapter-based installers for different AI systems.
Each installer sets up the appropriate integration files and configuration.
"""

from .base import BaseInstaller, InstallationResult, InstallationError
from .auggie import AuggieInstaller
from .universal import UniversalInstaller
from .registry import InstallerRegistry, get_installer, list_installers, has_installer

__all__ = [
    'BaseInstaller',
    'InstallationResult',
    'InstallationError',
    'AuggieInstaller',
    'UniversalInstaller',
    'InstallerRegistry',
    'get_installer',
    'list_installers',
    'has_installer',
]
