#!/usr/bin/env python3
"""
Test JSON-RPC message formatting directly.
"""

import json
import sys

sys.path.insert(0, "src")

from kuzu_memory.mcp.protocol import JSONRPCError, JSONRPCErrorCode, JSONRPCMessage


def test_message_formatting():
    """Test JSON-RPC message formatting."""

    print("Testing JSON-RPC Message Formatting\n")

    # Test 1: Request parsing
    print("1. Parse valid request:")
    request = '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
    try:
        parsed = JSONRPCMessage.parse_request(request)
        print(f"✅ Parsed: {json.dumps(parsed, indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Response creation (success)
    print("\n2. Create success response:")
    response = JSONRPCMessage.create_response(
        request_id=1, result={"tools": ["enhance", "learn", "recall"]}
    )
    print(f"✅ Response: {json.dumps(response, indent=2)}")

    # Test 3: Response creation (error)
    print("\n3. Create error response:")
    error = JSONRPCError(JSONRPCErrorCode.METHOD_NOT_FOUND, "Unknown method")
    response = JSONRPCMessage.create_response(request_id=2, error=error)
    print(f"✅ Response: {json.dumps(response, indent=2)}")

    # Test 4: Notification
    print("\n4. Create notification:")
    notification = JSONRPCMessage.create_notification(
        method="notifications/initialized", params={"status": "ready"}
    )
    print(f"✅ Notification: {json.dumps(notification, indent=2)}")

    # Test 5: Check if notification
    print("\n5. Check notification detection:")
    msg_with_id = {"jsonrpc": "2.0", "method": "test", "id": 1}
    msg_no_id = {"jsonrpc": "2.0", "method": "test"}
    print(f"  Message with ID is notification: {JSONRPCMessage.is_notification(msg_with_id)}")
    print(f"  Message without ID is notification: {JSONRPCMessage.is_notification(msg_no_id)}")

    # Test 6: Parse invalid JSON-RPC version
    print("\n6. Parse invalid version:")
    invalid_request = '{"jsonrpc": "1.0", "method": "test", "id": 1}'
    try:
        JSONRPCMessage.parse_request(invalid_request)
        print("❌ Should have raised error")
    except JSONRPCError as e:
        print(f"✅ Error caught: {e.message}")

    # Test 7: Tool call response format for Claude Code
    print("\n7. Claude Code tool response format:")
    tool_response = {
        "content": [
            {
                "type": "text",
                "text": "Enhanced: What database are we using? [Context: Project uses PostgreSQL]",
            }
        ]
    }
    full_response = JSONRPCMessage.create_response(request_id=3, result=tool_response)
    print(f"✅ Tool Response: {json.dumps(full_response, indent=2)}")


if __name__ == "__main__":
    test_message_formatting()
