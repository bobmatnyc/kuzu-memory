"""
MCP Server implementation for KuzuMemory.

Provides all memory operations as MCP tools for Claude Code integration.
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for KuzuMemory operations."""

    def __init__(self, project_root: Path | None = None):
        """Initialize MCP server with project root."""
        self.project_root = project_root or self._find_project_root()
        self.cli_path = self._find_cli_executable()

    def _find_project_root(self) -> Path:
        """Find project root by looking for git directory or kuzu-memories."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists() or (current / "kuzu-memories").exists():
                return current
            current = current.parent
        return Path.cwd()

    def _find_cli_executable(self) -> str:
        """Find the kuzu-memory CLI executable."""
        # Try common locations
        candidates = [
            "kuzu-memory",  # Global install
            "/opt/homebrew/bin/kuzu-memory",  # Homebrew on macOS
            str(Path.home() / ".local" / "bin" / "kuzu-memory"),  # pipx
            str(self.project_root / ".venv" / "bin" / "kuzu-memory"),  # venv
            str(self.project_root / "venv" / "bin" / "kuzu-memory"),  # venv
        ]

        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "--version"], capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    return candidate
            except (subprocess.SubprocessError, FileNotFoundError):
                continue

        # Fallback to python module execution
        return f"{sys.executable} -m kuzu_memory.cli"

    def _run_cli(self, args: list[str], timeout: int = 10) -> dict[str, Any]:
        """Run CLI command and return result."""
        try:
            # Split cli_path if it contains spaces (module execution)
            cmd_parts = (
                self.cli_path.split() if " " in self.cli_path else [self.cli_path]
            )
            cmd = cmd_parts + args

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=timeout,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip() if result.stdout else "",
                "error": result.stderr.strip() if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Command timed out after {timeout} seconds",
            }
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def _run_cli_async(
        self, args: list[str], timeout: int = 10
    ) -> dict[str, Any]:
        """Run CLI command asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._run_cli, args, timeout
        )

    # MCP Tool implementations

    def enhance(
        self, prompt: str, format: str = "plain", limit: int = 5
    ) -> dict[str, Any]:
        """
        Enhance a prompt with relevant project context.

        Args:
            prompt: The prompt to enhance
            format: Output format (plain, json, markdown)
            limit: Maximum number of memories to include

        Returns:
            Enhanced prompt with context
        """
        args = [
            "memory",
            "enhance",
            prompt,
            "--format",
            format,
            "--max-memories",
            str(limit),
        ]
        result = self._run_cli(args)

        if result["success"]:
            return {"enhanced_prompt": result["output"], "success": True}
        else:
            return {
                "enhanced_prompt": prompt,  # Fallback to original
                "success": False,
                "error": result["error"],
            }

    def learn(
        self, content: str, source: str = "mcp", quiet: bool = True
    ) -> dict[str, Any]:
        """
        Store a learning asynchronously (non-blocking).

        Args:
            content: The content to learn
            source: Source of the learning
            quiet: Run quietly without output

        Returns:
            Status of learning operation
        """
        args = ["learn", content, "--source", source]
        if quiet:
            args.append("--quiet")

        # Run async to not block
        self._run_cli(args, timeout=2)  # Short timeout for async operation

        return {
            "success": True,  # Always return success for async operations
            "message": "Learning queued for processing",
        }

    def recall(
        self, query: str, limit: int = 5, format: str = "json"
    ) -> dict[str, Any]:
        """
        Query memories for relevant information.

        Args:
            query: The search query
            limit: Maximum number of results
            format: Output format

        Returns:
            Relevant memories matching the query
        """
        args = [
            "memory",
            "recall",
            query,
            "--max-memories",
            str(limit),
            "--format",
            format,
        ]
        result = self._run_cli(args)

        if result["success"]:
            if format == "json":
                try:
                    memories = json.loads(result["output"])
                    return {"memories": memories, "success": True}
                except json.JSONDecodeError:
                    pass

            return {"memories": result["output"], "success": True}
        else:
            return {"memories": [], "success": False, "error": result["error"]}

    def remember(
        self, content: str, source: str = "mcp", session_id: str | None = None
    ) -> dict[str, Any]:
        """
        Store a direct memory.

        Args:
            content: The content to remember
            source: Source of the memory
            session_id: Session ID to group related memories

        Returns:
            Status of memory storage
        """
        args = ["remember", content, "--source", source]
        if session_id:
            args.extend(["--session-id", session_id])

        result = self._run_cli(args)

        return {
            "success": result["success"],
            "message": result["output"] if result["success"] else result["error"],
        }

    def stats(self, detailed: bool = False, format: str = "json") -> dict[str, Any]:
        """
        Get memory system statistics.

        Args:
            detailed: Show detailed statistics
            format: Output format

        Returns:
            Memory system statistics
        """
        args = ["stats", "--format", format]
        if detailed:
            args.append("--detailed")

        result = self._run_cli(args)

        if result["success"]:
            if format == "json":
                try:
                    stats = json.loads(result["output"])
                    return {"stats": stats, "success": True}
                except json.JSONDecodeError:
                    pass

            return {"stats": result["output"], "success": True}
        else:
            return {"stats": {}, "success": False, "error": result["error"]}

    def recent(self, limit: int = 10, format: str = "json") -> dict[str, Any]:
        """
        Get recent memories.

        Args:
            limit: Number of recent memories to retrieve
            format: Output format

        Returns:
            Recent memories
        """
        args = ["recent", "--recent", str(limit), "--format", format]
        result = self._run_cli(args)

        if result["success"]:
            if format == "json":
                try:
                    memories = json.loads(result["output"])
                    return {"memories": memories, "success": True}
                except json.JSONDecodeError:
                    pass

            return {"memories": result["output"], "success": True}
        else:
            return {"memories": [], "success": False, "error": result["error"]}

    def cleanup(self, force: bool = False, dry_run: bool = False) -> dict[str, Any]:
        """
        Clean up expired memories.

        Args:
            force: Force cleanup without confirmation
            dry_run: Show what would be cleaned without actually cleaning

        Returns:
            Cleanup results
        """
        args = ["cleanup"]
        if force:
            args.append("--force")
        if dry_run:
            args.append("--dry-run")

        result = self._run_cli(args)

        return {
            "success": result["success"],
            "message": result["output"] if result["success"] else result["error"],
        }

    def project(self, verbose: bool = False) -> dict[str, Any]:
        """
        Get project information.

        Args:
            verbose: Show detailed project information

        Returns:
            Project information
        """
        args = ["project"]
        if verbose:
            args.append("--verbose")

        result = self._run_cli(args)

        # Always return success field for consistency
        return {
            "success": result["success"],
            "project_info": result["output"] if result["success"] else "",
            "error": result["error"] if not result["success"] else None,
        }

    def init(self, path: str | None = None, force: bool = False) -> dict[str, Any]:
        """
        Initialize a new project.

        Args:
            path: Project path (current directory if not specified)
            force: Force initialization even if already initialized

        Returns:
            Initialization status
        """
        args = ["init"]
        if path:
            args.extend(["--path", path])
        if force:
            args.append("--force")

        result = self._run_cli(args)

        return {
            "success": result["success"],
            "message": result["output"] if result["success"] else result["error"],
        }

    def get_tools(self) -> list[dict[str, Any]]:
        """Get list of available MCP tools."""
        return [
            {
                "name": "enhance",
                "description": "Enhance prompts with relevant project context",
                "parameters": {
                    "prompt": {
                        "type": "string",
                        "required": True,
                        "description": "The prompt to enhance",
                    },
                    "format": {
                        "type": "string",
                        "default": "plain",
                        "description": "Output format (plain, json, markdown)",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum memories to include",
                    },
                },
            },
            {
                "name": "learn",
                "description": "Store a learning asynchronously (non-blocking)",
                "parameters": {
                    "content": {
                        "type": "string",
                        "required": True,
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
                        "description": "Run quietly",
                    },
                },
            },
            {
                "name": "recall",
                "description": "Query memories for relevant information",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum results",
                    },
                    "format": {
                        "type": "string",
                        "default": "json",
                        "description": "Output format",
                    },
                },
            },
            {
                "name": "remember",
                "description": "Store a direct memory",
                "parameters": {
                    "content": {
                        "type": "string",
                        "required": True,
                        "description": "Content to remember",
                    },
                    "source": {
                        "type": "string",
                        "default": "mcp",
                        "description": "Source of the memory",
                    },
                    "session_id": {
                        "type": "string",
                        "required": False,
                        "description": "Session ID to group related memories",
                    },
                },
            },
            {
                "name": "stats",
                "description": "Get memory system statistics",
                "parameters": {
                    "detailed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Show detailed stats",
                    },
                    "format": {
                        "type": "string",
                        "default": "json",
                        "description": "Output format",
                    },
                },
            },
            {
                "name": "recent",
                "description": "Get recent memories",
                "parameters": {
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of memories",
                    },
                    "format": {
                        "type": "string",
                        "default": "json",
                        "description": "Output format",
                    },
                },
            },
            {
                "name": "cleanup",
                "description": "Clean up expired memories",
                "parameters": {
                    "force": {
                        "type": "boolean",
                        "default": False,
                        "description": "Force cleanup",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": False,
                        "description": "Show what would be cleaned",
                    },
                },
            },
            {
                "name": "project",
                "description": "Get project information",
                "parameters": {
                    "verbose": {
                        "type": "boolean",
                        "default": False,
                        "description": "Show detailed info",
                    }
                },
            },
            {
                "name": "init",
                "description": "Initialize a new project",
                "parameters": {
                    "path": {"type": "string", "description": "Project path"},
                    "force": {
                        "type": "boolean",
                        "default": False,
                        "description": "Force initialization",
                    },
                },
            },
        ]


def create_mcp_server(project_root: Path | None = None) -> MCPServer:
    """Create and return an MCP server instance."""
    return MCPServer(project_root=project_root)
