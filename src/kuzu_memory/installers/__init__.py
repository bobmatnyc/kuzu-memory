"""
KuzuMemory Installer System

Provides adapter-based installers for different AI systems.
Each installer sets up the appropriate integration files and configuration.
"""

from .auggie import AuggieInstaller
from .auggie_mcp_installer import AuggieMCPInstaller
from .base import BaseInstaller, InstallationError, InstallationResult, InstalledSystem
from .claude_desktop import ClaudeDesktopHomeInstaller, ClaudeDesktopPipxInstaller
from .claude_hooks import ClaudeHooksInstaller
from .cursor_installer import CursorInstaller
from .detection import AISystemDetector, DetectedSystem, detect_ai_systems
from .mcp_installer_adapter import (
    HAS_MCP_INSTALLER,
    MCPInstallerAdapter,
    create_mcp_installer_adapter,
    is_mcp_installer_available,
)
from .registry import (
    InstallerRegistry,
    get_best_installer,
    get_installer,
    has_installer,
    list_installers,
)
from .universal import UniversalInstaller
from .vscode_installer import VSCodeInstaller
from .windsurf_installer import WindsurfInstaller

__all__ = [
    "HAS_MCP_INSTALLER",
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
    "InstalledSystem",
    "InstallerRegistry",
    "MCPInstallerAdapter",
    "UniversalInstaller",
    "VSCodeInstaller",
    "WindsurfInstaller",
    "create_mcp_installer_adapter",
    "detect_ai_systems",
    "get_best_installer",
    "get_installer",
    "has_installer",
    "is_mcp_installer_available",
    "list_installers",
]
