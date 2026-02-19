"""
MCP (Model Context Protocol) server for KuzuMemory.

Provides all memory operations as MCP tools for Claude Code integration.
Implements JSON-RPC 2.0 protocol for communication with Claude Code.
"""

from .protocol import (
    BatchRequestHandler,
    JSONRPCError,
    JSONRPCErrorCode,
    JSONRPCMessage,
    JSONRPCProtocol,
)
from .server import MCP_AVAILABLE, KuzuMemoryMCPServer, SimplifiedMCPServer, main

# Backwards compatibility aliases
MCPServer = KuzuMemoryMCPServer


def create_mcp_server(project_root: str | None = None) -> KuzuMemoryMCPServer:
    """Create and return an MCP server instance (backwards compatibility)."""
    from pathlib import Path

    return KuzuMemoryMCPServer(project_root=Path(project_root) if project_root else None)


__all__ = [
    "MCP_AVAILABLE",
    "BatchRequestHandler",
    "JSONRPCError",
    "JSONRPCErrorCode",
    "JSONRPCMessage",
    "JSONRPCProtocol",
    "KuzuMemoryMCPServer",
    "MCPServer",  # Backwards compatibility
    "SimplifiedMCPServer",
    "create_mcp_server",  # Backwards compatibility
    "main",
]
