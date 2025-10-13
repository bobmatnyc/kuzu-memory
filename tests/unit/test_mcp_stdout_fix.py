#!/usr/bin/env python3
"""
Unit test to verify MCP server stdout protocol compliance after fix.

This test ensures that the fix for redirecting startup messages to stderr
is working correctly, preventing contamination of the JSON-RPC channel.

NOTE: These tests are currently skipped as the MCP server implementation
has been refactored. The MCP server is now started via run_server.py,
not through the CLI commands. See tests/mcp/ for current MCP tests.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Skip all tests in this module as they test deprecated MCP startup mechanism
pytestmark = pytest.mark.skip(
    reason="MCP server startup mechanism changed - tests need updating. "
    "See tests/mcp/ for current MCP tests."
)


def test_mcp_startup_message_goes_to_stderr():
    """
    Test that the MCP server startup message goes to stderr, not stdout.

    This verifies the fix applied to mcp_commands.py where we changed
    the startup message to use file=sys.stderr instead of rich_print.
    """
    # Set up paths
    project_root = Path(__file__).parent.parent.parent
    src_path = project_root / "src"

    # Start MCP server directly via Python
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '{src_path}')
from kuzu_memory.cli.commands import cli
cli(['mcp', 'serve'])
""",
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )

    try:
        # Give server time to start
        time.sleep(1)

        # Send initialize request
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        request_str = json.dumps(request) + "\n"

        process.stdin.write(request_str.encode())
        process.stdin.flush()

        # Read response
        response_line = process.stdout.readline()

        # Send shutdown
        shutdown = {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": {}}
        process.stdin.write((json.dumps(shutdown) + "\n").encode())
        process.stdin.flush()

        # Wait briefly for shutdown
        time.sleep(0.5)

    finally:
        # Ensure process is terminated
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    # Get all output
    stdout_rest = process.stdout.read().decode()
    stderr_all = process.stderr.read().decode()

    # Assertions
    # 1. Response should be valid JSON-RPC
    assert response_line, "No response received from MCP server"
    response = json.loads(response_line.decode())
    assert response.get("jsonrpc") == "2.0", "Invalid JSON-RPC version"
    assert response.get("id") == 1, "Response ID mismatch"
    assert "result" in response or "error" in response, "Response missing result/error"

    # 2. Startup message should NOT be in stdout
    stdout_full = response_line.decode() + stdout_rest
    assert "Starting MCP server" not in stdout_full, (
        "Startup message found in stdout - violates MCP protocol! "
        "All logging must go to stderr."
    )

    # 3. Startup message SHOULD be in stderr
    assert "Starting MCP server" in stderr_all, (
        f"Startup message not found in stderr. stderr content: {stderr_all[:200]}"
    )

    # 4. Verify stdout contains only JSON-RPC
    for line in stdout_full.strip().split("\n"):
        if line.strip():
            # Each non-empty line should be valid JSON
            try:
                msg = json.loads(line)
                assert "jsonrpc" in msg, f"Non-JSON-RPC content in stdout: {line}"
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in stdout: {line}")


def test_mcp_error_messages_go_to_stderr():
    """Test that MCP error messages and logging go to stderr, not stdout."""
    # Set up paths
    project_root = Path(__file__).parent.parent.parent
    src_path = project_root / "src"

    # Start MCP server
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '{src_path}')
from kuzu_memory.cli.commands import cli
cli(['mcp', 'serve'])
""",
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )

    try:
        # Give server time to start
        time.sleep(1)

        # Send invalid method to trigger error
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "non_existent_method",
            "params": {},
        }
        process.stdin.write((json.dumps(request) + "\n").encode())
        process.stdin.flush()

        # Read error response
        error_response_line = process.stdout.readline()

        # Send shutdown
        shutdown = {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": {}}
        process.stdin.write((json.dumps(shutdown) + "\n").encode())
        process.stdin.flush()

        time.sleep(0.5)

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    # Get remaining output
    stdout_rest = process.stdout.read().decode()
    process.stderr.read().decode()

    # Verify error response is valid JSON-RPC
    assert error_response_line, "No error response received"
    error_response = json.loads(error_response_line.decode())
    assert error_response.get("jsonrpc") == "2.0"
    assert "error" in error_response, "Expected error response"
    assert error_response["error"]["code"] == -32601, "Expected METHOD_NOT_FOUND error"

    # Verify no error text leaked to stdout
    stdout_full = error_response_line.decode() + stdout_rest
    for line in stdout_full.strip().split("\n"):
        if line.strip():
            msg = json.loads(line)  # Should not raise - all lines must be valid JSON
            assert "jsonrpc" in msg


def test_mcp_batch_request_maintains_clean_stdout():
    """Test that batch requests maintain protocol compliance."""
    # Set up paths
    project_root = Path(__file__).parent.parent.parent
    src_path = project_root / "src"

    # Start MCP server
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, '{src_path}')
from kuzu_memory.cli.commands import cli
cli(['mcp', 'serve'])
""",
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )

    try:
        # Give server time to start
        time.sleep(1)

        # Send batch request
        batch_request = [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
        ]
        process.stdin.write((json.dumps(batch_request) + "\n").encode())
        process.stdin.flush()

        # Read batch response
        batch_response_line = process.stdout.readline()

        # Shutdown
        shutdown = {"jsonrpc": "2.0", "id": 99, "method": "shutdown", "params": {}}
        process.stdin.write((json.dumps(shutdown) + "\n").encode())
        process.stdin.flush()

        time.sleep(0.5)

    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    # Verify batch response
    assert batch_response_line, "No batch response received"
    batch_response = json.loads(batch_response_line.decode())
    assert isinstance(batch_response, list), "Batch response should be array"
    assert len(batch_response) == 2, "Should have 2 responses in batch"

    for response in batch_response:
        assert response.get("jsonrpc") == "2.0"
        assert "id" in response


if __name__ == "__main__":
    # Run tests directly if executed as script
    pytest.main([__file__, "-v"])
