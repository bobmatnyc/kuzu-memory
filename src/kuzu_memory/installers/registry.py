"""
Installer Registry for KuzuMemory

Manages available installers and provides lookup functionality.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .auggie import AuggieInstaller
from .auggie_mcp_installer import AuggieMCPInstaller
from .base import BaseInstaller
from .claude_hooks import ClaudeHooksInstaller
from .codex_installer import CodexInstaller
from .cursor_installer import CursorInstaller
from .mcp_installer_adapter import (
    HAS_MCP_INSTALLER,
    REVERSE_PLATFORM_MAP,
    MCPInstallerAdapter,
    is_mcp_installer_available,
)
from .universal import UniversalInstaller
from .vscode_installer import VSCodeInstaller
from .windsurf_installer import WindsurfInstaller

logger = logging.getLogger(__name__)


class InstallerRegistry:
    """
    Registry of available installers for different AI systems.

    Provides lookup and discovery functionality for installers.
    """

    def __init__(self) -> None:
        """Initialize the installer registry."""
        self._installers: dict[str, type[BaseInstaller]] = {}
        self._register_builtin_installers()

    def _register_builtin_installers(self) -> None:
        """Register built-in installers."""
        # AI System Installers (ONE PATH per system)
        # NOTE: claude-desktop REMOVED - focus on coding tools only (Claude Code, VS Code, Cursor, etc.)
        self.register("auggie", AuggieInstaller)
        self.register("auggie-mcp", AuggieMCPInstaller)  # Auggie MCP server integration
        self.register("claude-code", ClaudeHooksInstaller)  # Claude Code with hooks/MCP
        # self.register("claude-desktop", SmartClaudeDesktopInstaller)  # REMOVED - coding tools only
        self.register("codex", CodexInstaller)  # Codex MCP server integration
        self.register("universal", UniversalInstaller)

        # MCP-specific installers (Priority 1)
        self.register("cursor", CursorInstaller)  # Cursor IDE MCP
        self.register("vscode", VSCodeInstaller)  # VS Code with Claude extension MCP
        self.register("windsurf", WindsurfInstaller)  # Windsurf IDE MCP

        # Legacy aliases (DEPRECATED - will show warnings)
        # These are kept for backward compatibility only
        self.register("claude", ClaudeHooksInstaller)  # DEPRECATED: Use claude-code
        self.register("claude-mcp", ClaudeHooksInstaller)  # DEPRECATED: Use claude-code
        # Claude Desktop installers REMOVED - coding tools focus
        # self.register("claude-desktop-pipx", ClaudeDesktopPipxInstaller)  # REMOVED
        # self.register("claude-desktop-home", ClaudeDesktopHomeInstaller)  # REMOVED
        self.register("generic", UniversalInstaller)  # DEPRECATED: Use universal

    def register(self, name: str, installer_class: type[BaseInstaller]) -> None:
        """
        Register an installer.

        Args:
            name: Name/identifier for the installer
            installer_class: Installer class
        """
        if not issubclass(installer_class, BaseInstaller):
            raise ValueError("Installer class must inherit from BaseInstaller")

        self._installers[name.lower()] = installer_class
        logger.debug(f"Registered installer: {name} -> {installer_class.__name__}")

    def get_installer(self, name: str, project_root: Path) -> BaseInstaller | None:
        """
        Get installer instance by name.

        Args:
            name: Name of the installer
            project_root: Project root directory

        Returns:
            Installer instance or None if not found
        """
        installer_class = self._installers.get(name.lower())
        if installer_class:
            return installer_class(project_root)
        return None

    def list_installers(self) -> list[dict[str, str]]:
        """
        List all available installers.

        Returns:
            List of installer information dictionaries
        """
        installers: list[Any] = []
        seen_classes = set()

        for name, installer_class in self._installers.items():
            # Avoid duplicates for aliases
            if installer_class in seen_classes:
                continue
            seen_classes.add(installer_class)

            # Create temporary instance to get info
            temp_instance = installer_class(Path("."))

            installers.append(
                {
                    "name": name,
                    "ai_system": temp_instance.ai_system_name,
                    "description": temp_instance.description,
                    "class": installer_class.__name__,
                }
            )

        return sorted(installers, key=lambda x: x["name"])

    def get_installer_names(self) -> list[str]:
        """
        Get list of all installer names.

        Returns:
            List of installer names
        """
        return sorted(self._installers.keys())

    def has_installer(self, name: str) -> bool:
        """
        Check if installer exists.

        Args:
            name: Installer name

        Returns:
            True if installer exists
        """
        return name.lower() in self._installers


# Global registry instance
_registry = InstallerRegistry()


def get_installer(name: str, project_root: Path) -> BaseInstaller | None:
    """
    Get installer instance by name.

    Args:
        name: Name of the installer
        project_root: Project root directory

    Returns:
        Installer instance or None if not found
    """
    return _registry.get_installer(name, project_root)


def list_installers() -> list[dict[str, str]]:
    """
    List all available installers.

    Returns:
        List of installer information dictionaries
    """
    return _registry.list_installers()


def get_installer_names() -> list[str]:
    """
    Get list of all installer names.

    Returns:
        List of installer names
    """
    return _registry.get_installer_names()


def has_installer(name: str) -> bool:
    """
    Check if installer exists.

    Args:
        name: Installer name

    Returns:
        True if installer exists
    """
    return _registry.has_installer(name)


def register_installer(name: str, installer_class: type[BaseInstaller]) -> None:
    """
    Register a custom installer.

    Args:
        name: Name/identifier for the installer
        installer_class: Installer class
    """
    _registry.register(name, installer_class)


def get_best_installer(platform: str, project_root: Path) -> BaseInstaller:
    """
    Get the best available installer for a platform.

    Prefers MCPInstallerAdapter when available as it provides:
    - Auto-detection of AI platforms
    - Smart installation method selection (uv run, pipx, direct)
    - Comprehensive diagnostics via MCPDoctor
    - Configuration inspection and validation

    Falls back to legacy installers when submodule is unavailable.

    Args:
        platform: Platform name (e.g., "cursor", "claude-code", "vscode")
        project_root: Project root directory

    Returns:
        Best available installer instance for the platform

    Raises:
        ValueError: If platform is not supported by any installer

    Example:
        >>> installer = get_best_installer("cursor", Path.cwd())
        >>> result = installer.install(force=False, dry_run=True)
    """
    platform_lower = platform.lower()

    # Try MCPInstallerAdapter if available and platform is supported
    if HAS_MCP_INSTALLER and platform_lower in REVERSE_PLATFORM_MAP:
        try:
            logger.debug(
                f"Using MCPInstallerAdapter for {platform} "
                f"(submodule available: {is_mcp_installer_available()})"
            )
            adapter = MCPInstallerAdapter(project_root, platform=platform_lower)
            return adapter
        except Exception as e:
            logger.warning(
                f"MCPInstallerAdapter failed for {platform}: {e}, falling back to legacy installer"
            )

    # Fall back to legacy installer
    logger.debug(
        f"Using legacy installer for {platform} (MCP adapter available: {HAS_MCP_INSTALLER})"
    )
    installer = get_installer(platform_lower, project_root)

    if installer is None:
        raise ValueError(
            f"No installer available for platform: {platform}. "
            f"Available platforms: {', '.join(get_installer_names())}"
        )

    return installer
