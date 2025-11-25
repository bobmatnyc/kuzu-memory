"""
Auggie/Claude Installer for KuzuMemory

Sets up Augment rules and integration files for seamless Auggie integration.

This is a compatibility wrapper that uses the v2 installer internally.
For direct v2 access, use AuggieInstallerV2.
"""

from __future__ import annotations

import logging

from .auggie_v2 import AuggieInstallerV2

logger = logging.getLogger(__name__)


class AuggieInstaller(AuggieInstallerV2):
    """
    Installer for Auggie/Claude AI system integration.

    This is now a compatibility wrapper around AuggieInstallerV2.
    All functionality is inherited from the v2 installer which includes:
    - Version detection
    - Automatic migration from v1.0.0 to v2.0.0
    - Backup before upgrade
    - Enhanced rules based on Claude Code hooks v1.4.0 insights

    Usage:
        installer = AuggieInstaller(project_root)
        result = installer.install()  # Automatically detects and migrates

        # Force reinstall:
        result = installer.install(force=True)

        # Check for upgrades:
        upgrade_info = installer.check_upgrade_available()
    """

    pass  # All functionality inherited from AuggieInstallerV2
