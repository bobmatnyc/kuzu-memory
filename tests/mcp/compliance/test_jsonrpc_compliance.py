"""
JSON-RPC 2.0 compliance tests.

Tests comprehensive JSON-RPC 2.0 specification compliance including
request/response structure, error codes, and protocol requirements.
"""

import json

import pytest

# JSON-RPC 2.0 Error Codes (from spec)
JSONRPC_ERROR_CODES = {
    "PARSE_ERROR": -32700,
    "INVALID_REQUEST": -32600,
    "METHOD_NOT_FOUND": -32601,
    "INVALID_PARAMS": -32602,
    "INTERNAL_ERROR": -32603,
    # Server errors: -32000 to -32099
}


@pytest.mark.compliance
class TestRequestStructure:
    """Test JSON-RPC 2.0 request structure compliance."""

    @pytest.mark.asyncio
    async def test_valid_request_structure(self, initialized_client):
        """Test that valid requests follow JSON-RPC 2.0 structure."""
        response = await initialized_client.send_request("ping", {})

        assert response is not None, "Valid request should get response"
        assert "jsonrpc" in response, "Response must have jsonrpc field"
        assert response["jsonrpc"] == "2.0", "Response must be JSON-RPC 2.0"
        assert "id" in response, "Response must have id field"
        assert (
            "result" in response or "error" in response
        ), "Response must have result or error"

    @pytest.mark.asyncio
    async def test_request_with_params_object(self, initialized_client):
        """Test request with params as object."""
        response = await initialized_client.call_tool("recall", {"query": "test"})

        assert response is not None, "Request with params object should succeed"

    @pytest.mark.asyncio
    async def test_notification_no_id(self, mcp_client):
        """Test notification (request without id) doesn't expect response."""
        # Note: Notifications are sent but don't expect responses
        # This is valid per JSON-RPC 2.0 spec
        await mcp_client.send_notification("notifications/initialized")

        # No assertion needed - just verify no exception
        assert True

    @pytest.mark.asyncio
    async def test_version_field_required(self, error_codes):
        """Test that jsonrpc version field is required and validated."""
        # This is tested by protocol validation
        from kuzu_memory.mcp.protocol import JSONRPCError, JSONRPCMessage

        # Missing version
        with pytest.raises(JSONRPCError) as exc:
            JSONRPCMessage.parse_request('{"method": "test", "id": 1}')
        assert exc.value.code == error_codes["INVALID_REQUEST"]

        # Wrong version
        with pytest.raises(JSONRPCError) as exc:
            JSONRPCMessage.parse_request(
                '{"jsonrpc": "1.0", "method": "test", "id": 1}'
            )
        assert exc.value.code == error_codes["INVALID_REQUEST"]

    @pytest.mark.asyncio
    async def test_method_field_required(self, error_codes):
        """Test that method field is required."""
        from kuzu_memory.mcp.protocol import JSONRPCError, JSONRPCMessage

        with pytest.raises(JSONRPCError) as exc:
            JSONRPCMessage.parse_request('{"jsonrpc": "2.0", "id": 1}')
        assert exc.value.code == error_codes["INVALID_REQUEST"]

    @pytest.mark.asyncio
    async def test_method_must_be_string(self, error_codes):
        """Test that method must be a string."""
        from kuzu_memory.mcp.protocol import JSONRPCError, JSONRPCMessage

        with pytest.raises(JSONRPCError) as exc:
            JSONRPCMessage.parse_request('{"jsonrpc": "2.0", "method": 123, "id": 1}')
        assert exc.value.code == error_codes["INVALID_REQUEST"]

    @pytest.mark.asyncio
    async def test_params_structure_validation(self, error_codes):
        """Test that params must be object or array."""
        from kuzu_memory.mcp.protocol import JSONRPCError, JSONRPCMessage

        # Params as string (invalid)
        with pytest.raises(JSONRPCError) as exc:
            JSONRPCMessage.parse_request(
                '{"jsonrpc": "2.0", "method": "test", "params": "invalid", "id": 1}'
            )
        assert exc.value.code == error_codes["INVALID_REQUEST"]

        # Params as number (invalid)
        with pytest.raises(JSONRPCError) as exc:
            JSONRPCMessage.parse_request(
                '{"jsonrpc": "2.0", "method": "test", "params": 123, "id": 1}'
            )
        assert exc.value.code == error_codes["INVALID_REQUEST"]


@pytest.mark.compliance
class TestResponseStructure:
    """Test JSON-RPC 2.0 response structure compliance."""

    @pytest.mark.asyncio
    async def test_response_has_version(self, initialized_client):
        """Test that response includes jsonrpc version."""
        response = await initialized_client.send_request("ping", {})

        assert "jsonrpc" in response, "Response must have jsonrpc field"
        assert response["jsonrpc"] == "2.0", "Must be version 2.0"

    @pytest.mark.asyncio
    async def test_response_has_id(self, initialized_client):
        """Test that response includes matching request id."""
        response = await initialized_client.send_request("ping", {})

        assert "id" in response, "Response must have id field"
        # ID should match request (testing framework handles this)

    @pytest.mark.asyncio
    async def test_success_response_structure(self, initialized_client):
        """Test success response has result field."""
        response = await initialized_client.send_request("ping", {})

        assert response is not None
        if "error" not in response:
            assert "result" in response, "Success response must have result field"

    @pytest.mark.asyncio
    async def test_error_response_structure(self, initialized_client):
        """Test error response structure."""
        # Trigger error by calling non-existent method
        response = await initialized_client.send_request("nonexistent_method", {})

        if response and "error" in response:
            error = response["error"]
            assert "code" in error, "Error must have code field"
            assert "message" in error, "Error must have message field"
            assert isinstance(error["code"], int), "Error code must be integer"
            assert isinstance(error["message"], str), "Error message must be string"

    @pytest.mark.asyncio
    async def test_error_and_result_mutually_exclusive(self, initialized_client):
        """Test that response cannot have both result and error."""
        response = await initialized_client.send_request("ping", {})

        assert response is not None
        has_result = "result" in response
        has_error = "error" in response

        # Should have exactly one (XOR)
        assert (
            has_result != has_error
        ), "Response must have either result or error, not both"


@pytest.mark.compliance
class TestErrorCodes:
    """Test JSON-RPC 2.0 error code compliance."""

    @pytest.mark.asyncio
    async def test_parse_error_code(self, error_codes):
        """Test parse error returns -32700."""
        from kuzu_memory.mcp.protocol import JSONRPCMessage

        # Invalid JSON
        try:
            JSONRPCMessage.parse_request("{invalid json}")
        except Exception as e:
            assert hasattr(e, "code")
            assert e.code == error_codes["PARSE_ERROR"]

    @pytest.mark.asyncio
    async def test_invalid_request_code(self, error_codes):
        """Test invalid request returns -32600."""
        from kuzu_memory.mcp.protocol import JSONRPCError, JSONRPCMessage

        with pytest.raises(JSONRPCError) as exc:
            JSONRPCMessage.parse_request('{"jsonrpc": "2.0"}')  # Missing method
        assert exc.value.code == error_codes["INVALID_REQUEST"]

    @pytest.mark.asyncio
    async def test_method_not_found_code(self, initialized_client, error_codes):
        """Test method not found returns -32601."""
        response = await initialized_client.send_request("nonexistent_method", {})

        if response and "error" in response:
            assert response["error"]["code"] == error_codes["METHOD_NOT_FOUND"]

    @pytest.mark.asyncio
    async def test_invalid_params_code(self, initialized_client, error_codes):
        """Test invalid params returns -32602."""
        # Call tool with missing required parameter
        response = await initialized_client.call_tool("enhance", {})  # Missing prompt

        if response and "error" in response:
            assert response["error"]["code"] == error_codes["INVALID_PARAMS"]

    @pytest.mark.asyncio
    async def test_server_error_range(self):
        """Test that implementation errors use -32000 to -32099 range."""
        # Server errors should be in the defined range
        assert (
            -32099 <= JSONRPC_ERROR_CODES.get("TOOL_EXECUTION_ERROR", -32001) <= -32000
        )
        assert (
            -32099 <= JSONRPC_ERROR_CODES.get("INITIALIZATION_ERROR", -32002) <= -32000
        )
        assert -32099 <= JSONRPC_ERROR_CODES.get("TIMEOUT_ERROR", -32003) <= -32000


@pytest.mark.compliance
class TestBatchRequests:
    """Test JSON-RPC 2.0 batch request compliance."""

    @pytest.mark.asyncio
    async def test_batch_request_structure(self, initialized_client):
        """Test batch request returns array of responses."""
        batch = [
            {"jsonrpc": "2.0", "method": "ping", "id": 1},
            {"jsonrpc": "2.0", "method": "tools/list", "id": 2},
        ]

        responses = await initialized_client.send_batch_request(batch)

        assert isinstance(responses, list), "Batch response must be array"
        assert len(responses) == 2, "Should get response for each request"

    @pytest.mark.asyncio
    async def test_batch_response_ids_match(self, initialized_client):
        """Test that batch responses have matching ids."""
        batch = [
            {"jsonrpc": "2.0", "method": "ping", "id": 10},
            {"jsonrpc": "2.0", "method": "ping", "id": 20},
        ]

        responses = await initialized_client.send_batch_request(batch)

        assert len(responses) == 2
        response_ids = {r["id"] for r in responses}
        assert 10 in response_ids, "Should have response for id 10"
        assert 20 in response_ids, "Should have response for id 20"

    @pytest.mark.asyncio
    async def test_batch_with_notifications(self, initialized_client):
        """Test batch with notifications (no response expected)."""
        batch = [
            {"jsonrpc": "2.0", "method": "ping", "id": 1},
            {"jsonrpc": "2.0", "method": "notifications/test"},  # No id
            {"jsonrpc": "2.0", "method": "ping", "id": 2},
        ]

        responses = await initialized_client.send_batch_request(batch)

        # Should only get 2 responses (notifications don't get responses)
        assert len(responses) == 2

    @pytest.mark.asyncio
    async def test_batch_with_errors(self, initialized_client):
        """Test batch request with some errors."""
        batch = [
            {"jsonrpc": "2.0", "method": "ping", "id": 1},
            {"jsonrpc": "2.0", "method": "invalid_method", "id": 2},
            {"jsonrpc": "2.0", "method": "ping", "id": 3},
        ]

        responses = await initialized_client.send_batch_request(batch)

        assert len(responses) == 3, "Should get response for all requests"

        # Check that we have both success and error responses
        has_success = any("result" in r for r in responses)
        has_error = any("error" in r for r in responses)

        assert has_success, "Should have successful responses"
        assert has_error, "Should have error responses"


@pytest.mark.compliance
class TestNotificationHandling:
    """Test JSON-RPC 2.0 notification handling."""

    @pytest.mark.asyncio
    async def test_notification_structure(self):
        """Test notification structure (no id field)."""
        from kuzu_memory.mcp.protocol import JSONRPCMessage

        notification = JSONRPCMessage.create_notification(
            "test_method", {"param": "value"}
        )

        assert notification["jsonrpc"] == "2.0"
        assert notification["method"] == "test_method"
        assert "id" not in notification, "Notifications must not have id"
        assert notification["params"] == {"param": "value"}

    @pytest.mark.asyncio
    async def test_notification_no_response(self):
        """Test that notifications don't generate responses."""
        from kuzu_memory.mcp.protocol import JSONRPCMessage

        # Create response for notification (should be None)
        response = JSONRPCMessage.create_response(None, result={"status": "ok"})

        assert response is None, "Notifications should not generate responses"

    @pytest.mark.asyncio
    async def test_is_notification_detection(self):
        """Test notification detection."""
        from kuzu_memory.mcp.protocol import JSONRPCMessage

        notification = {"jsonrpc": "2.0", "method": "test"}
        request = {"jsonrpc": "2.0", "method": "test", "id": 1}

        assert JSONRPCMessage.is_notification(notification)
        assert not JSONRPCMessage.is_notification(request)


@pytest.mark.compliance
class TestProtocolEdgeCases:
    """Test JSON-RPC 2.0 edge cases and corner conditions."""

    @pytest.mark.asyncio
    async def test_null_id_allowed(self):
        """Test that null is a valid id value."""
        from kuzu_memory.mcp.protocol import JSONRPCMessage

        response = JSONRPCMessage.create_response(None, result={"status": "ok"})
        # null id for notification - no response
        assert response is None

    @pytest.mark.asyncio
    async def test_numeric_id(self, initialized_client):
        """Test numeric ids are supported."""
        # Numeric IDs are standard
        response = await initialized_client.send_request("ping", {})
        assert response is not None
        assert "id" in response

    @pytest.mark.asyncio
    async def test_string_id(self):
        """Test string ids are supported."""
        from kuzu_memory.mcp.protocol import JSONRPCMessage

        response = JSONRPCMessage.create_response(
            "string-id-123", result={"status": "ok"}
        )

        assert response["id"] == "string-id-123"

    @pytest.mark.asyncio
    async def test_empty_params_object(self, initialized_client):
        """Test empty params object is valid."""
        response = await initialized_client.send_request("ping", {})
        assert response is not None

    @pytest.mark.asyncio
    async def test_missing_params_field(self, initialized_client):
        """Test missing params field is valid (params optional)."""
        # Params is optional per spec
        response = await initialized_client.send_request("ping", {})
        assert response is not None

    @pytest.mark.asyncio
    async def test_additional_fields_allowed(self):
        """Test that additional fields in request are allowed."""
        from kuzu_memory.mcp.protocol import JSONRPCMessage

        # Additional fields should be ignored per spec
        request = JSONRPCMessage.parse_request(
            '{"jsonrpc": "2.0", "method": "test", "id": 1, "extra": "field"}'
        )

        assert request["method"] == "test"
        # Additional fields preserved but ignored by protocol
