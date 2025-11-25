#!/usr/bin/env python3
"""
Test MCP server stdout protocol compliance.

Ensures that:
1. stdout contains ONLY valid JSON-RPC messages
2. All logging and status messages go to stderr
3. No contamination of the JSON-RPC communication channel
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest


class MCPProtocolComplianceTest:
    """Test MCP server for stdout protocol compliance."""

    def __init__(self):
        """Initialize test harness."""
        self.process = None
        self.stdout_lines = []
        self.stderr_lines = []

    def start_mcp_server(self, capture_output=True):
        """
        Start the MCP server process.

        Args:
            capture_output: Whether to capture stdout/stderr

        Returns:
            subprocess.Popen: The server process
        """
        # Start the MCP server via CLI command
        # For testing, we need to run the development version directly
        # to ensure we test the current code changes
        import os

        project_root = Path(__file__).parent.parent
        cmd = [
            sys.executable,
            "-c",
            f"""
import sys
sys.path.insert(0, '{project_root}/src')
from kuzu_memory.cli.commands import cli
cli(['mcp', 'serve'])
""",
        ]

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=False,  # Use bytes for more control
            bufsize=0,  # Unbuffered
        )

        # Give server time to start
        time.sleep(0.5)

        return self.process

    def send_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """
        Send a JSON-RPC request and get response.

        Args:
            request: The JSON-RPC request dictionary

        Returns:
            The response dictionary or None
        """
        if not self.process:
            raise RuntimeError("Server not started")

        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        self.process.stdin.flush()

        # Read response
        response_line = self.process.stdout.readline()
        if response_line:
            return json.loads(response_line.decode())
        return None

    def capture_all_output(self, timeout: float = 2.0) -> tuple[list[str], list[str]]:
        """
        Capture all stdout and stderr output.

        Args:
            timeout: Maximum time to wait for output

        Returns:
            Tuple of (stdout_lines, stderr_lines)
        """
        import select

        stdout_lines = []
        stderr_lines = []

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if there's data available
            readable, _, _ = select.select([self.process.stdout, self.process.stderr], [], [], 0.1)

            for stream in readable:
                if stream == self.process.stdout:
                    line = stream.readline()
                    if line:
                        stdout_lines.append(line.decode().strip())
                elif stream == self.process.stderr:
                    line = stream.readline()
                    if line:
                        stderr_lines.append(line.decode().strip())

        return stdout_lines, stderr_lines

    def cleanup(self):
        """Clean up the server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def is_valid_json_rpc(line: str) -> bool:
    """
    Check if a line is a valid JSON-RPC message.

    Args:
        line: The line to check

    Returns:
        True if valid JSON-RPC, False otherwise
    """
    try:
        msg = json.loads(line)
        # Check for JSON-RPC 2.0 format
        if "jsonrpc" in msg and msg["jsonrpc"] == "2.0":
            # Must have either method (request) or result/error (response)
            return "method" in msg or "result" in msg or "error" in msg
    except (json.JSONDecodeError, TypeError):
        pass
    return False


def test_startup_message_goes_to_stderr():
    """Test that startup messages go to stderr, not stdout."""
    test = MCPProtocolComplianceTest()

    try:
        # Start server and capture initial output
        test.start_mcp_server()

        # Capture any startup output
        stdout_lines, stderr_lines = test.capture_all_output(timeout=1.0)

        # Check stdout for non-JSON-RPC content
        for line in stdout_lines:
            if line and not is_valid_json_rpc(line):
                pytest.fail(
                    f"Non-JSON-RPC content found in stdout: {line}\n"
                    "All logging must go to stderr per MCP protocol"
                )

        # Check that startup message is in stderr
        startup_found = any("Starting MCP server" in line for line in stderr_lines)

        assert startup_found, f"Startup message should be in stderr. stderr: {stderr_lines}"

    finally:
        test.cleanup()


def test_json_rpc_communication_clean():
    """Test that JSON-RPC communication on stdout is clean."""
    test = MCPProtocolComplianceTest()

    try:
        # Start server
        test.start_mcp_server()

        # Clear any startup output
        test.capture_all_output(timeout=0.5)

        # Send initialize request
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}

        response = test.send_request(request)

        # Verify response is valid JSON-RPC
        assert response is not None, "No response received"
        assert response.get("jsonrpc") == "2.0", "Invalid JSON-RPC version"
        assert "id" in response, "Missing id in response"
        assert response["id"] == 1, "Mismatched request id"
        assert "result" in response or "error" in response, "Response must have result or error"

        # Send tools/list request
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        response = test.send_request(request)

        # Verify response
        assert response is not None, "No response received"
        assert response.get("jsonrpc") == "2.0", "Invalid JSON-RPC version"
        assert response["id"] == 2, "Mismatched request id"

        # Capture any additional output
        stdout_lines, _stderr_lines = test.capture_all_output(timeout=0.5)

        # Verify stdout is clean (empty or only JSON-RPC)
        for line in stdout_lines:
            if line and not is_valid_json_rpc(line):
                pytest.fail(f"Non-JSON-RPC content in stdout: {line}")

    finally:
        test.cleanup()


def test_error_messages_go_to_stderr():
    """Test that error messages and logging go to stderr."""
    test = MCPProtocolComplianceTest()

    try:
        # Start server
        test.start_mcp_server()

        # Send invalid request to trigger error
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "non_existent_method",
            "params": {},
        }

        response = test.send_request(request)

        # Should get error response
        assert response is not None, "No response received"
        assert "error" in response, "Expected error response"

        # Send malformed JSON to trigger parse error
        if test.process:
            test.process.stdin.write(b"{ invalid json }\n")
            test.process.stdin.flush()

        # Wait a bit for processing
        time.sleep(0.5)

        # Read error response
        error_response_line = test.process.stdout.readline()
        if error_response_line:
            error_response = json.loads(error_response_line.decode())
            assert "error" in error_response, "Expected error response"
            assert error_response["error"]["code"] == -32700, "Expected parse error code"

        # Capture any logging output
        stdout_lines, _stderr_lines = test.capture_all_output(timeout=0.5)

        # Verify stdout only has JSON-RPC
        for line in stdout_lines:
            if line and not is_valid_json_rpc(line):
                pytest.fail(f"Non-JSON-RPC content in stdout: {line}")

    finally:
        test.cleanup()


def test_batch_requests_clean_stdout():
    """Test that batch requests maintain clean stdout."""
    test = MCPProtocolComplianceTest()

    try:
        # Start server
        test.start_mcp_server()

        # Send batch request
        batch_request = [
            {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 5, "method": "ping", "params": {}},
        ]

        batch_str = json.dumps(batch_request) + "\n"
        test.process.stdin.write(batch_str.encode())
        test.process.stdin.flush()

        # Read batch response
        response_line = test.process.stdout.readline()
        if response_line:
            batch_response = json.loads(response_line.decode())

            # Should be array of responses
            assert isinstance(batch_response, list), "Batch response should be array"
            assert len(batch_response) == 2, "Should have 2 responses"

            for response in batch_response:
                assert response.get("jsonrpc") == "2.0", "Invalid JSON-RPC version"
                assert "id" in response, "Missing id in response"

        # Capture any additional output
        stdout_lines, _stderr_lines = test.capture_all_output(timeout=0.5)

        # Verify stdout is clean
        for line in stdout_lines:
            if line and not is_valid_json_rpc(line):
                pytest.fail(f"Non-JSON-RPC content in stdout during batch: {line}")

    finally:
        test.cleanup()


def test_shutdown_clean():
    """Test that shutdown maintains protocol compliance."""
    test = MCPProtocolComplianceTest()

    try:
        # Start server
        test.start_mcp_server()

        # Send shutdown request
        request = {"jsonrpc": "2.0", "id": 6, "method": "shutdown", "params": {}}

        response = test.send_request(request)

        # Should get clean response
        assert response is not None, "No shutdown response"
        assert response.get("jsonrpc") == "2.0", "Invalid JSON-RPC version"
        assert response["id"] == 6, "Mismatched request id"
        assert "result" in response, "Shutdown should return result"

        # Wait for shutdown
        test.process.wait(timeout=2)

        # Capture any final output
        final_stdout = test.process.stdout.read().decode()
        test.process.stderr.read().decode()

        # Check final stdout for cleanliness
        if final_stdout.strip():
            for line in final_stdout.strip().split("\n"):
                if line and not is_valid_json_rpc(line):
                    pytest.fail(f"Non-JSON-RPC in final stdout: {line}")

        # Shutdown messages should be in stderr if present
        if "MCP server" in final_stdout:
            pytest.fail("Server messages found in stdout instead of stderr")

    finally:
        test.cleanup()


def test_long_running_compliance():
    """Test that protocol compliance is maintained over multiple operations."""
    test = MCPProtocolComplianceTest()

    try:
        # Start server
        test.start_mcp_server()

        # Perform multiple operations
        operations = [
            ("initialize", {}),
            ("tools/list", {}),
            ("tools/call", {"name": "stats", "arguments": {"detailed": False}}),
            ("tools/call", {"name": "recall", "arguments": {"query": "test"}}),
            ("ping", {}),
        ]

        for i, (method, params) in enumerate(operations, start=1):
            request = {
                "jsonrpc": "2.0",
                "id": i + 10,
                "method": method,
                "params": params,
            }

            response = test.send_request(request)

            # Basic validation
            assert response is not None, f"No response for {method}"
            assert response.get("jsonrpc") == "2.0", f"Invalid version for {method}"
            assert response["id"] == i + 10, f"ID mismatch for {method}"

            # Brief pause between operations
            time.sleep(0.1)

        # Capture accumulated output
        stdout_lines, _stderr_lines = test.capture_all_output(timeout=0.5)

        # Final check - stdout should be clean
        for line in stdout_lines:
            if line and not is_valid_json_rpc(line):
                pytest.fail(f"Protocol violation after operations: {line}")

    finally:
        test.cleanup()


if __name__ == "__main__":
    # Run tests directly
    print("Testing MCP stdout protocol compliance...")

    tests = [
        ("Startup messages to stderr", test_startup_message_goes_to_stderr),
        ("Clean JSON-RPC communication", test_json_rpc_communication_clean),
        ("Error messages to stderr", test_error_messages_go_to_stderr),
        ("Batch requests clean", test_batch_requests_clean_stdout),
        ("Clean shutdown", test_shutdown_clean),
        ("Long running compliance", test_long_running_compliance),
    ]

    failed = []
    for name, test_func in tests:
        print(f"\nRunning: {name}...")
        try:
            import signal

            # Add timeout to prevent hanging
            def timeout_handler(signum, frame, test_name=name):
                raise TimeoutError(f"Test {test_name} timed out after 10 seconds")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)  # 10 second timeout per test

            test_func()
            signal.alarm(0)  # Cancel alarm
            print("  ✅ PASSED")
        except TimeoutError as e:
            print(f"  ⏱️ TIMEOUT: {e}")
            failed.append((name, e))
        except Exception as e:
            signal.alarm(0)  # Cancel alarm on failure
            print(f"  ❌ FAILED: {e}")
            failed.append((name, e))

    print("\n" + "=" * 60)
    if failed:
        print(f"❌ {len(failed)}/{len(tests)} tests FAILED:")
        for name, error in failed:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print(f"✅ All {len(tests)} tests PASSED!")
        print("\nMCP server is compliant with stdout protocol requirements:")
        print("  - stdout contains ONLY valid JSON-RPC messages")
        print("  - All logging and status messages go to stderr")
        print("  - No contamination of the communication channel")
