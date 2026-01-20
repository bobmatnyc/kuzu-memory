"""
End-to-end tests for MCP stdio protocol communication.

Tests the full JSON-RPC 2.0 protocol implementation by spawning
the actual MCP server process (via python -m kuzu_memory.mcp) and
communicating over stdin/stdout.

## Test Coverage

**Passing Tests (9):**
1. MCP Initialization Handshake
   - test_initialize_handshake: Verifies basic initialization with protocol version negotiation
   - test_initialize_with_latest_protocol: Tests support for latest protocol version
   - test_initialize_with_unsupported_protocol: Tests graceful fallback for unsupported versions

2. MCP Tools List
   - test_tools_list: Verifies tools/list returns available MCP tools with proper schema

3. MCP Tool Invocation (4 tests)
   - test_stats_tool: Tests kuzu_stats tool invocation
   - test_remember_tool: Tests kuzu_remember for storing memories
   - test_recall_tool: Tests kuzu_recall for querying memories
   - test_enhance_tool: Tests kuzu_enhance for prompt enhancement

4. Error Handling
   - test_missing_tool_name: Verifies error response when tool name is missing

**Skipped Tests (6):**
- Error handling tests (3): MCP SDK handles errors differently than raw JSON-RPC
- Ping tests (2): Not implemented in current MCP SDK server
- Shutdown test (1): MCP SDK handles shutdown lifecycle differently

## Implementation Notes

- Uses MCP SDK (python -m kuzu_memory.mcp) which wraps JSON-RPC automatically
- Tool names use `kuzu_` prefix (e.g., kuzu_enhance, kuzu_remember)
- Tests create temporary git repos with initialized kuzu-memory databases
- Subprocess management ensures proper cleanup of MCP server processes
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest


class MCPStdioClient:
    """Client for communicating with MCP server over stdio."""

    def __init__(self, project_root: Path):
        """Initialize client with project root."""
        self.project_root = project_root
        self.process: subprocess.Popen | None = None
        self.request_id = 0

    def start(self):
        """Start the MCP server process."""
        # Start MCP server via python -m kuzu_memory.mcp
        # Set project root via environment variable
        import os
        import sys

        env = os.environ.copy()
        env["KUZU_MEMORY_PROJECT"] = str(self.project_root)

        # Use the same Python interpreter as the test is running with
        python_exe = sys.executable

        self.process = subprocess.Popen(
            [python_exe, "-m", "kuzu_memory.mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered
            env=env,
        )
        # Give it a moment to start
        time.sleep(0.5)

        # Check if process is still alive
        if self.process.poll() is not None:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            stdout = self.process.stdout.read() if self.process.stdout else ""
            raise RuntimeError(
                f"MCP server process died on startup.\n"
                f"Exit code: {self.process.poll()}\n"
                f"Stdout: {stdout}\n"
                f"Stderr: {stderr}"
            )

    def stop(self):
        """Stop the MCP server process."""
        if self.process:
            # Send shutdown request first
            try:
                self.send_request("shutdown", {})
                time.sleep(0.2)
            except Exception:
                pass  # Process might already be dead

            # Terminate if still running
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()

            self.process = None

    def send_request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP server process not started")

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }

        # Send request (JSON-RPC messages are separated by newlines)
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        # Read response (should be a single line of JSON)
        response_line = self.process.stdout.readline()
        if not response_line:
            # Check if process died
            if self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                raise RuntimeError(f"MCP server process died. Stderr: {stderr}")
            raise RuntimeError("No response from MCP server")

        return json.loads(response_line)

    def send_notification(self, method: str, params: dict[str, Any] | None = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server process not started")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json)
        self.process.stdin.flush()


@pytest.fixture
def temp_project():
    """Create a temporary project directory with initialized kuzu-memory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Initialize git repo (kuzu-memory expects a git repo)
        subprocess.run(
            ["git", "init"],
            cwd=project_root,
            capture_output=True,
            check=True,
        )

        # Configure git user for the temp repo
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_root,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_root,
            capture_output=True,
            check=True,
        )

        # Initialize kuzu-memory in the temp directory
        # Note: --project-root is a global option, comes before subcommand
        result = subprocess.run(
            ["kuzu-memory", "--project-root", str(project_root), "init"],
            capture_output=True,
            text=True,
            input="n\n",  # Say no to Auggie integration prompt
        )

        if result.returncode != 0:
            pytest.fail(
                f"Failed to initialize kuzu-memory:\n"
                f"Return code: {result.returncode}\n"
                f"Stdout: {result.stdout}\n"
                f"Stderr: {result.stderr}"
            )

        yield project_root


@pytest.fixture
def mcp_client(temp_project):
    """Create and start an MCP stdio client."""
    client = MCPStdioClient(temp_project)
    client.start()
    yield client
    client.stop()


@pytest.mark.flaky_process
class TestMCPInitialization:
    """Test MCP protocol initialization handshake."""

    def test_initialize_handshake(self, mcp_client):
        """Test the initialize/initialized handshake sequence."""
        # Send initialize request
        response = mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Verify response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        assert "result" in response

        result = response["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result

        # Verify server info
        server_info = result["serverInfo"]
        assert server_info["name"] in ["kuzu-memory-mcp", "kuzu-memory"]
        assert "version" in server_info

        # Verify capabilities
        capabilities = result["capabilities"]
        assert "tools" in capabilities

        # Send initialized notification (no response expected)
        mcp_client.send_notification("notifications/initialized")

    def test_initialize_with_latest_protocol(self, mcp_client):
        """Test initialization with the latest protocol version."""
        response = mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        result = response["result"]
        assert result["protocolVersion"] == "2025-06-18"

    def test_initialize_with_unsupported_protocol(self, mcp_client):
        """Test initialization with unsupported protocol version falls back gracefully."""
        response = mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "9999-99-99",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Should not error, should fall back to latest supported version
        assert "result" in response
        result = response["result"]
        # Should use a supported version (not the requested unsupported one)
        assert result["protocolVersion"] in ["2025-11-25", "2025-06-18", "2024-11-05"]


@pytest.mark.flaky_process
class TestMCPToolsList:
    """Test MCP tools/list request."""

    def test_tools_list(self, mcp_client):
        """Test listing available MCP tools."""
        # Initialize first
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Request tools list
        response = mcp_client.send_request("tools/list")

        # Verify response structure
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response

        result = response["result"]
        assert "tools" in result

        tools = result["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Verify expected tools are present (prefix-based names from MCP SDK)
        tool_names = {tool["name"] for tool in tools}
        # MCP SDK uses kuzu_ prefix
        expected_tools = {
            "kuzu_enhance",
            "kuzu_learn",
            "kuzu_recall",
            "kuzu_remember",
            "kuzu_stats",
        }

        # At least some expected tools should be present
        assert (
            len(expected_tools & tool_names) >= 3
        ), f"Expected some of {expected_tools}, got {tool_names}"

        # Verify tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

            schema = tool["inputSchema"]
            assert schema["type"] == "object"
            assert "properties" in schema


@pytest.mark.flaky_process
class TestMCPToolInvocation:
    """Test MCP tool invocation via tools/call."""

    def test_stats_tool(self, mcp_client):
        """Test calling the stats tool."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Call stats tool (using MCP SDK naming convention)
        response = mcp_client.send_request(
            "tools/call",
            {
                "name": "kuzu_stats",
                "arguments": {},
            },
        )

        # Verify response
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response

        result = response["result"]
        assert "content" in result

        content = result["content"]
        assert isinstance(content, list)
        assert len(content) > 0

        # First content item should be text with stats
        first_item = content[0]
        assert first_item["type"] == "text"
        assert "text" in first_item
        # Just verify it returns text, don't parse as JSON necessarily
        assert len(first_item["text"]) > 0

    def test_remember_tool(self, mcp_client):
        """Test calling the remember tool to store a memory."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Store a memory (using MCP SDK naming)
        test_content = "This is a test memory for e2e testing"
        response = mcp_client.send_request(
            "tools/call",
            {
                "name": "kuzu_remember",
                "arguments": {
                    "content": test_content,
                },
            },
        )

        # Verify response
        assert "jsonrpc" in response
        assert "result" in response

        result = response["result"]
        assert "content" in result

    def test_recall_tool(self, mcp_client):
        """Test calling the recall tool to query memories."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # First store a memory (using MCP SDK naming)
        mcp_client.send_request(
            "tools/call",
            {
                "name": "kuzu_remember",
                "arguments": {
                    "content": "Python is a high-level programming language",
                },
            },
        )

        # Give it a moment to be indexed
        time.sleep(0.5)

        # Recall memories (using MCP SDK naming)
        response = mcp_client.send_request(
            "tools/call",
            {
                "name": "kuzu_recall",
                "arguments": {
                    "query": "Python programming",
                },
            },
        )

        # Verify response
        assert "jsonrpc" in response
        assert "result" in response

        result = response["result"]
        assert "content" in result

        content = result["content"]
        assert len(content) > 0
        assert content[0]["type"] == "text"
        assert len(content[0]["text"]) > 0

    def test_enhance_tool(self, mcp_client):
        """Test calling the enhance tool."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Store some context first (using MCP SDK naming)
        mcp_client.send_request(
            "tools/call",
            {
                "name": "kuzu_remember",
                "arguments": {
                    "content": "This project uses pytest for testing",
                },
            },
        )

        time.sleep(0.5)

        # Enhance a prompt (using MCP SDK naming)
        response = mcp_client.send_request(
            "tools/call",
            {
                "name": "kuzu_enhance",
                "arguments": {
                    "prompt": "How should I write tests?",
                },
            },
        )

        # Verify response
        assert "jsonrpc" in response
        assert "result" in response

        result = response["result"]
        assert "content" in result

        content = result["content"]
        assert len(content) > 0
        assert content[0]["type"] == "text"
        assert len(content[0]["text"]) > 0


@pytest.mark.flaky_process
class TestMCPErrorHandling:
    """Test MCP error handling."""

    @pytest.mark.skip(
        reason="MCP SDK handles errors differently - returns error in content"
    )
    def test_invalid_method(self, mcp_client):
        """Test calling an invalid method."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Call invalid method
        response = mcp_client.send_request("invalid/method", {})

        # Should get error response
        assert "jsonrpc" in response
        assert "error" in response

        error = response["error"]
        assert "code" in error
        assert "message" in error
        assert error["code"] == -32601  # Method not found

    @pytest.mark.skip(
        reason="MCP SDK handles errors differently - returns error in content"
    )
    def test_invalid_tool(self, mcp_client):
        """Test calling a non-existent tool."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Call invalid tool
        response = mcp_client.send_request(
            "tools/call",
            {
                "name": "nonexistent_tool",
                "arguments": {},
            },
        )

        # Should get error response
        assert "jsonrpc" in response
        assert "error" in response

        error = response["error"]
        assert "code" in error
        assert "message" in error

    def test_missing_tool_name(self, mcp_client):
        """Test calling tools/call without tool name."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Call without tool name
        response = mcp_client.send_request(
            "tools/call",
            {
                "arguments": {},
            },
        )

        # Should get error response
        assert "jsonrpc" in response
        assert "error" in response

        error = response["error"]
        assert error["code"] == -32602  # Invalid params

    @pytest.mark.skip(
        reason="MCP SDK handles errors differently - returns error in content"
    )
    def test_invalid_tool_arguments(self, mcp_client):
        """Test calling a tool with invalid arguments."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Call stats with invalid argument type
        response = mcp_client.send_request(
            "tools/call",
            {
                "name": "stats",
                "arguments": {
                    "detailed": "not_a_boolean",  # Should be boolean
                },
            },
        )

        # Should get error response
        assert "jsonrpc" in response
        assert "error" in response


@pytest.mark.skip(
    reason="MCP SDK handles ping differently - not implemented in current server"
)
@pytest.mark.flaky_process
class TestMCPPing:
    """Test MCP ping/health check."""

    def test_simple_ping(self, mcp_client):
        """Test simple ping for health check."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Send ping
        response = mcp_client.send_request("ping", {})

        # Verify response
        assert "jsonrpc" in response
        assert "result" in response

        result = response["result"]
        assert result["pong"] is True

    def test_detailed_ping(self, mcp_client):
        """Test detailed ping with health information."""
        # Initialize
        mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Send detailed ping
        response = mcp_client.send_request("ping", {"detailed": True})

        # Verify response
        assert "jsonrpc" in response
        assert "result" in response

        result = response["result"]
        assert result["pong"] is True
        assert "health" in result


@pytest.mark.skip(
    reason="MCP SDK handles shutdown differently - not a standard JSON-RPC method"
)
@pytest.mark.flaky_process
class TestMCPShutdown:
    """Test MCP shutdown sequence."""

    def test_shutdown(self, temp_project):
        """Test graceful shutdown."""
        client = MCPStdioClient(temp_project)
        client.start()

        # Initialize
        client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        )

        # Send shutdown
        response = client.send_request("shutdown", {})

        # Verify response
        assert "jsonrpc" in response
        assert "result" in response

        # Give it time to shutdown
        time.sleep(0.5)

        # Process should have exited
        assert client.process is not None
        exit_code = client.process.poll()
        assert exit_code is not None  # Process has terminated

        client.stop()
