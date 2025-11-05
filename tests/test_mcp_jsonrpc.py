#!/usr/bin/env python3
"""
Test script for MCP JSON-RPC 2.0 implementation.

Tests the MCP server with sample JSON-RPC requests to verify compliance.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def send_request(process, request):
    """Send a JSON-RPC request and get response."""
    request_str = json.dumps(request) + "\n"
    process.stdin.write(request_str.encode())
    process.stdin.flush()

    # Read response
    response_line = process.stdout.readline()
    if response_line:
        return json.loads(response_line.decode())
    return None


def test_mcp_server():
    """Test the MCP server with JSON-RPC requests."""
    print("Starting MCP JSON-RPC test...")

    # Start the MCP server
    server_path = Path(__file__).parent / "src" / "kuzu_memory" / "mcp" / "run_server.py"
    process = subprocess.Popen(
        [sys.executable, str(server_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )

    try:
        # Give server time to start
        time.sleep(1)

        # Test 1: Initialize
        print("\n1. Testing initialize...")
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        response = send_request(process, request)
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"Response: {json.dumps(response, indent=2) if response else 'No response'}")

        # Test 2: List tools
        print("\n2. Testing tools/list...")
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        response = send_request(process, request)
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"Response: {json.dumps(response, indent=2) if response else 'No response'}")

        # Test 3: Call enhance tool
        print("\n3. Testing tools/call with enhance...")
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "enhance",
                "arguments": {
                    "prompt": "What database are we using?",
                    "format": "plain",
                },
            },
        }
        response = send_request(process, request)
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"Response: {json.dumps(response, indent=2) if response else 'No response'}")

        # Test 4: Notification (no response expected)
        print("\n4. Testing notification (no ID)...")
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        process.stdin.write((json.dumps(request) + "\n").encode())
        process.stdin.flush()
        print(f"Notification sent: {json.dumps(request, indent=2)}")
        print("(No response expected for notifications)")

        # Test 5: Invalid method
        print("\n5. Testing invalid method...")
        request = {"jsonrpc": "2.0", "id": 5, "method": "invalid/method", "params": {}}
        response = send_request(process, request)
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"Response: {json.dumps(response, indent=2) if response else 'No response'}")

        # Test 6: Batch request
        print("\n6. Testing batch request...")
        batch_request = [
            {"jsonrpc": "2.0", "id": 6, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 7, "method": "ping", "params": {}},
        ]
        process.stdin.write((json.dumps(batch_request) + "\n").encode())
        process.stdin.flush()
        response_line = process.stdout.readline()
        if response_line:
            batch_response = json.loads(response_line.decode())
            print(f"Batch Request: {json.dumps(batch_request, indent=2)}")
            print(f"Batch Response: {json.dumps(batch_response, indent=2)}")

        # Test 7: Shutdown
        print("\n7. Testing shutdown...")
        request = {"jsonrpc": "2.0", "id": 8, "method": "shutdown", "params": {}}
        response = send_request(process, request)
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"Response: {json.dumps(response, indent=2) if response else 'No response'}")

        print("\n✅ All tests completed!")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up
        process.terminate()
        process.wait(timeout=5)
        print("\nServer terminated.")


if __name__ == "__main__":
    test_mcp_server()
