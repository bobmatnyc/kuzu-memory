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
from .server import MCPServer, create_mcp_server

__all__ = [
    "BatchRequestHandler",
    "JSONRPCError",
    "JSONRPCErrorCode",
    "JSONRPCMessage",
    "JSONRPCProtocol",
    "MCPServer",
    "create_mcp_server",
]
