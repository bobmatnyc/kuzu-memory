#!/usr/bin/env python3
"""
Run the MCP server for KuzuMemory.

This script is called by the MCP integration to provide memory operations.
Implements JSON-RPC 2.0 protocol for communication with Claude Code.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from kuzu_memory.__version__ import __version__

from .protocol import (
    BatchRequestHandler,
    JSONRPCError,
    JSONRPCErrorCode,
    JSONRPCMessage,
    JSONRPCProtocol,
)
from .server import KuzuMemoryMCPServer as MCPServer

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """Handle MCP protocol communication with JSON-RPC 2.0."""

    def __init__(self, server: MCPServer) -> None:
        """Initialize with MCP server."""
        self.server = server
        self.protocol = JSONRPCProtocol()
        self.running = True

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Handle a JSON-RPC request."""
        # Check for error from parsing
        if "error" in request and "method" not in request:
            return JSONRPCMessage.create_response(request.get("id"), error=request["error"])

        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        # Check if it's a notification (no response needed)
        is_notification = JSONRPCMessage.is_notification(request)

        try:
            # Handle different MCP methods
            if method == "initialize":
                # Initialize handshake - support multiple protocol versions
                client_protocol_version = params.get("protocolVersion", "2025-06-18")

                # List of supported protocol versions (latest first)
                supported_versions = ["2025-06-18", "2024-11-05"]

                # Use client's version if supported, otherwise use latest supported
                if client_protocol_version in supported_versions:
                    response_version = client_protocol_version
                else:
                    # Log warning but continue with latest supported version (first in list)
                    logger.warning(
                        f"Client requested unsupported protocol version {client_protocol_version}, "
                        f"using {supported_versions[0]}"
                    )
                    response_version = supported_versions[0]

                result = {
                    "protocolVersion": response_version,
                    "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
                    "serverInfo": {"name": "kuzu-memory-mcp", "version": __version__},
                }
                return JSONRPCMessage.create_response(request_id, result)

            elif method == "tools/list":
                # Return list of available tools
                tools = self._format_tools_for_mcp()
                result = {"tools": tools}
                return JSONRPCMessage.create_response(request_id, result)

            elif method == "tools/call":
                # Call a specific tool
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})

                if not tool_name:
                    raise JSONRPCError(
                        JSONRPCErrorCode.INVALID_PARAMS,
                        "Missing 'name' in tool call parameters",
                    )

                # Execute tool and format response
                result = await self._execute_tool(tool_name, tool_args)
                return JSONRPCMessage.create_response(request_id, result)

            elif method == "notifications/initialized":
                # Client has been initialized (notification)
                logger.info("Client initialized")
                return None  # No response for notifications

            elif method == "shutdown":
                # Shutdown the server
                self.running = False
                # Also signal the protocol to stop
                self.protocol.running = False
                return JSONRPCMessage.create_response(request_id, {})

            elif method == "ping":
                # Health check - support both simple and detailed modes
                detailed = params.get("detailed", False)

                if detailed:
                    # Return detailed health information
                    try:
                        from .testing.health_checker import MCPHealthChecker

                        health_checker = MCPHealthChecker(project_root=Path.cwd(), timeout=2.0)
                        health_result = await health_checker.check_health(
                            detailed=False, retry=False
                        )

                        return JSONRPCMessage.create_response(
                            request_id,
                            {
                                "pong": True,
                                "health": health_result.health.to_dict(),
                                "duration_ms": health_result.duration_ms,
                            },
                        )
                    except Exception as e:
                        logger.warning(f"Detailed health check failed: {e}")
                        # Fall back to simple ping
                        return JSONRPCMessage.create_response(
                            request_id,
                            {
                                "pong": True,
                                "health": {
                                    "status": "degraded",
                                    "error": str(e),
                                },
                            },
                        )
                else:
                    # Simple ping response (backward compatible)
                    return JSONRPCMessage.create_response(request_id, {"pong": True})

            else:
                # Unknown method
                if is_notification:
                    logger.warning(f"Unknown notification method: {method}")
                    return None
                else:
                    raise JSONRPCError(
                        JSONRPCErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}"
                    )

        except JSONRPCError as e:
            if is_notification:
                logger.error(f"Error in notification handler: {e}")
                return None
            return JSONRPCMessage.create_response(request_id, error=e)

        except Exception as e:
            logger.error(f"Internal error handling request: {e}", exc_info=True)
            if is_notification:
                return None
            return JSONRPCMessage.create_response(
                request_id,
                error=JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Internal error: {e!s}"),
            )

    async def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and format the response for MCP."""
        # Map tool names to server methods
        if not hasattr(self.server, tool_name):
            raise JSONRPCError(JSONRPCErrorCode.METHOD_NOT_FOUND, f"Tool not found: {tool_name}")

        try:
            # Get the tool method
            tool_method = getattr(self.server, tool_name)

            # Execute the tool
            result = tool_method(**arguments)

            # Format response according to MCP spec
            if isinstance(result, dict) and "success" in result:
                if result["success"]:
                    # Success response - format as MCP content
                    content = []

                    # Determine the main content based on tool type
                    if tool_name == "enhance":
                        text = result.get("enhanced_prompt", "")
                    elif tool_name in ["recall", "recent"]:
                        memories = result.get("memories", [])
                        if isinstance(memories, list):
                            text = json.dumps(memories, indent=2)
                        else:
                            text = str(memories)
                    elif tool_name == "stats":
                        stats = result.get("stats", {})
                        if isinstance(stats, dict):
                            text = json.dumps(stats, indent=2)
                        else:
                            text = str(stats)
                    elif tool_name == "project":
                        text = result.get("project_info", "")
                    else:
                        text = result.get("message", result.get("output", str(result)))

                    content.append({"type": "text", "text": text})

                    return {"content": content}
                else:
                    # Error in tool execution
                    error_msg = result.get("error", "Tool execution failed")
                    raise JSONRPCError(JSONRPCErrorCode.TOOL_EXECUTION_ERROR, error_msg)
            else:
                # Unexpected result format - convert to text
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                json.dumps(result)
                                if isinstance(result, dict | list)
                                else str(result)
                            ),
                        }
                    ]
                }

        except TypeError as e:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                f"Invalid parameters for tool '{tool_name}': {e!s}",
            )
        except Exception as e:
            raise JSONRPCError(
                JSONRPCErrorCode.TOOL_EXECUTION_ERROR,
                f"Error executing tool '{tool_name}': {e!s}",
            )

    def _format_tools_for_mcp(self) -> list[dict[str, Any]]:
        """Format tools for MCP protocol."""

        # Define tools with MCP-compatible schema
        tool_definitions = [
            {
                "name": "enhance",
                "description": "Enhance prompts with relevant project context from memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to enhance with context",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["plain", "json", "markdown"],
                            "default": "plain",
                            "description": "Output format",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20,
                            "default": 5,
                            "description": "Maximum number of memories to include",
                        },
                    },
                    "required": ["prompt"],
                },
            },
            {
                "name": "learn",
                "description": "Store a learning asynchronously (non-blocking)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content to learn",
                        },
                        "source": {
                            "type": "string",
                            "default": "mcp",
                            "description": "Source of the learning",
                        },
                        "quiet": {
                            "type": "boolean",
                            "default": True,
                            "description": "Run quietly without output",
                        },
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "recall",
                "description": "Query memories for relevant information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 5,
                            "description": "Maximum number of results",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "plain", "markdown"],
                            "default": "json",
                            "description": "Output format",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "remember",
                "description": "Store a direct memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content to remember",
                        },
                        "source": {
                            "type": "string",
                            "default": "mcp",
                            "description": "Source of the memory",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID to group related memories",
                        },
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "stats",
                "description": "Get memory system statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "default": False,
                            "description": "Show detailed statistics",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "plain"],
                            "default": "json",
                            "description": "Output format",
                        },
                    },
                },
            },
            {
                "name": "recent",
                "description": "Get recent memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of recent memories to retrieve",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "plain", "list"],
                            "default": "json",
                            "description": "Output format",
                        },
                    },
                },
            },
            {
                "name": "cleanup",
                "description": "Clean up expired memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "force": {
                            "type": "boolean",
                            "default": False,
                            "description": "Force cleanup without confirmation",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "default": False,
                            "description": "Preview what would be cleaned",
                        },
                    },
                },
            },
            {
                "name": "project",
                "description": "Get project information and memory status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "verbose": {
                            "type": "boolean",
                            "default": False,
                            "description": "Show detailed project information",
                        }
                    },
                },
            },
            {
                "name": "init",
                "description": "Initialize memory system for a new project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path (current directory if not specified)",
                        },
                        "force": {
                            "type": "boolean",
                            "default": False,
                            "description": "Force initialization even if already initialized",
                        },
                    },
                },
            },
        ]

        return tool_definitions

    async def run(self) -> None:
        """Run the MCP protocol handler with JSON-RPC 2.0."""
        # Initialize protocol
        await self.protocol.initialize()

        logger.info("MCP server started, waiting for JSON-RPC messages...")

        while self.running:
            try:
                # Read next message
                message = await self.protocol.read_message()
                if message is None:
                    break  # EOF

                # Check for batch requests (message could be list or dict)
                if BatchRequestHandler.is_batch(message):
                    # Type narrowing: if is_batch returns True, message is a list
                    assert isinstance(message, list)
                    # Process batch
                    responses = await BatchRequestHandler.process_batch(
                        message, self.handle_request
                    )
                    if responses:
                        # Batch responses are a list, but write_message expects dict
                        # Write each response individually
                        for response in responses:
                            self.protocol.write_message(response)
                else:
                    # Type narrowing: if not a batch, message is a dict
                    assert isinstance(message, dict)
                    # Process single request
                    response_or_none = await self.handle_request(message)
                    if response_or_none is not None:
                        self.protocol.write_message(response_or_none)

                    # Check if we should stop after processing
                    if not self.running:
                        break  # type: ignore[unreachable]  # self.running can be modified by signal handlers

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                # Send error response if possible (with a dummy ID since we don't have a request)
                error_response = JSONRPCMessage.create_response(
                    1,  # Use dummy ID for unhandled errors
                    error=JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Server error: {e!s}"),
                )
                if error_response is not None:
                    self.protocol.write_message(error_response)

        logger.info("MCP server shutting down")
        self.protocol.close()


async def main() -> None:
    """Main entry point for MCP server."""
    # Get project root from environment or current directory
    import os

    project_root_str = os.environ.get("KUZU_MEMORY_PROJECT")
    if project_root_str:
        project_root = Path(project_root_str)
    else:
        project_root = Path.cwd()

    # Create MCP server
    server = MCPServer(project_root=project_root)

    # Create and run protocol handler
    handler = MCPProtocolHandler(server)

    try:
        await handler.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
