"""
Unit tests for MCP JSON-RPC 2.0 protocol implementation.

Tests protocol parsing, validation, error handling, and message creation.
"""

import json
import sys
from pathlib import Path

# Add src to path (must be before other imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import pytest  # noqa: E402

from kuzu_memory.mcp.protocol import (  # noqa: E402
    BatchRequestHandler,
    JSONRPCError,
    JSONRPCErrorCode,
    JSONRPCMessage,
)


class TestJSONRPCErrorCode:
    """Test JSON-RPC error code enumeration."""

    def test_standard_error_codes(self) -> None:
        """Test standard JSON-RPC 2.0 error codes."""
        assert JSONRPCErrorCode.PARSE_ERROR == -32700
        assert JSONRPCErrorCode.INVALID_REQUEST == -32600
        assert JSONRPCErrorCode.METHOD_NOT_FOUND == -32601
        assert JSONRPCErrorCode.INVALID_PARAMS == -32602
        assert JSONRPCErrorCode.INTERNAL_ERROR == -32603

    def test_custom_error_codes(self) -> None:
        """Test custom MCP error codes."""
        assert JSONRPCErrorCode.TOOL_EXECUTION_ERROR == -32001
        assert JSONRPCErrorCode.INITIALIZATION_ERROR == -32002
        assert JSONRPCErrorCode.TIMEOUT_ERROR == -32003

    def test_error_code_ranges(self) -> None:
        """Test error code ranges are within spec."""
        # Server errors should be in -32099 to -32000 range
        assert -32099 <= JSONRPCErrorCode.TOOL_EXECUTION_ERROR <= -32000
        assert -32099 <= JSONRPCErrorCode.INITIALIZATION_ERROR <= -32000
        assert -32099 <= JSONRPCErrorCode.TIMEOUT_ERROR <= -32000


class TestJSONRPCError:
    """Test JSON-RPC error exception."""

    def test_error_creation(self) -> None:
        """Test creating JSON-RPC error."""
        error = JSONRPCError(JSONRPCErrorCode.METHOD_NOT_FOUND, "Method not found")

        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data is None

    def test_error_with_data(self) -> None:
        """Test error with additional data."""
        error = JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Invalid parameters",
            data={"field": "missing"},
        )

        assert error.code == -32602
        assert error.data == {"field": "missing"}

    def test_error_to_dict(self) -> None:
        """Test converting error to dictionary."""
        error = JSONRPCError(JSONRPCErrorCode.PARSE_ERROR, "Parse error")
        error_dict = error.to_dict()

        assert error_dict["code"] == -32700
        assert error_dict["message"] == "Parse error"
        assert "data" not in error_dict

    def test_error_to_dict_with_data(self) -> None:
        """Test error dictionary with data field."""
        error = JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Internal error", data={"trace": "..."}
        )
        error_dict = error.to_dict()

        assert error_dict["code"] == -32603
        assert error_dict["message"] == "Internal error"
        assert error_dict["data"] == {"trace": "..."}


class TestJSONRPCMessage:
    """Test JSON-RPC message handler."""

    def test_parse_valid_request(self) -> None:
        """Test parsing valid JSON-RPC request."""
        raw = json.dumps({"jsonrpc": "2.0", "method": "test_method", "id": 1})

        message = JSONRPCMessage.parse_request(raw)

        assert message["jsonrpc"] == "2.0"
        assert message["method"] == "test_method"
        assert message["id"] == 1

    def test_parse_request_with_params(self) -> None:
        """Test parsing request with parameters."""
        raw = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "test",
                "params": {"arg": "value"},
                "id": 1,
            }
        )

        message = JSONRPCMessage.parse_request(raw)

        assert message["params"] == {"arg": "value"}

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON raises error."""
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request("not valid json")

        assert exc_info.value.code == JSONRPCErrorCode.PARSE_ERROR

    def test_parse_missing_jsonrpc(self) -> None:
        """Test missing jsonrpc field raises error."""
        raw = json.dumps({"method": "test", "id": 1})

        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request(raw)

        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST
        assert "version" in exc_info.value.message.lower()

    def test_parse_wrong_jsonrpc_version(self) -> None:
        """Test wrong JSON-RPC version raises error."""
        raw = json.dumps({"jsonrpc": "1.0", "method": "test", "id": 1})

        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request(raw)

        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_parse_missing_method(self) -> None:
        """Test missing method field raises error."""
        raw = json.dumps({"jsonrpc": "2.0", "id": 1})

        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request(raw)

        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST
        assert "method" in exc_info.value.message.lower()

    def test_parse_invalid_method_type(self) -> None:
        """Test non-string method raises error."""
        raw = json.dumps({"jsonrpc": "2.0", "method": 123, "id": 1})

        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request(raw)

        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_parse_invalid_params_type(self) -> None:
        """Test invalid params type raises error."""
        raw = json.dumps({"jsonrpc": "2.0", "method": "test", "params": "string", "id": 1})

        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request(raw)

        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_parse_params_as_list(self) -> None:
        """Test params can be a list."""
        raw = json.dumps({"jsonrpc": "2.0", "method": "test", "params": [1, 2, 3], "id": 1})

        message = JSONRPCMessage.parse_request(raw)
        assert message["params"] == [1, 2, 3]

    def test_create_success_response(self) -> None:
        """Test creating success response."""
        response = JSONRPCMessage.create_response(1, result={"status": "ok"})

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"] == {"status": "ok"}
        assert "error" not in response

    def test_create_error_response(self) -> None:
        """Test creating error response."""
        error = JSONRPCError(JSONRPCErrorCode.METHOD_NOT_FOUND, "Not found")
        response = JSONRPCMessage.create_response(1, error=error)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "result" not in response

    def test_create_response_with_null_result(self) -> None:
        """Test response with null result uses empty dict."""
        response = JSONRPCMessage.create_response(1, result=None)

        assert response["result"] == {}

    def test_create_notification_response_is_none(self) -> None:
        """Test notification (no ID) returns None."""
        response = JSONRPCMessage.create_response(None, result={"data": "test"})

        assert response is None

    def test_create_notification(self) -> None:
        """Test creating notification message."""
        notification = JSONRPCMessage.create_notification("test_method")

        assert notification["jsonrpc"] == "2.0"
        assert notification["method"] == "test_method"
        assert "id" not in notification
        assert "params" not in notification

    def test_create_notification_with_params(self) -> None:
        """Test notification with parameters."""
        notification = JSONRPCMessage.create_notification("test_method", {"arg": "value"})

        assert notification["params"] == {"arg": "value"}

    def test_is_notification(self) -> None:
        """Test identifying notification messages."""
        notification = {"jsonrpc": "2.0", "method": "test"}
        request = {"jsonrpc": "2.0", "method": "test", "id": 1}

        assert JSONRPCMessage.is_notification(notification) is True
        assert JSONRPCMessage.is_notification(request) is False

    def test_response_with_string_id(self) -> None:
        """Test response with string ID."""
        response = JSONRPCMessage.create_response("req-123", result={"ok": True})

        assert response["id"] == "req-123"


class TestBatchRequestHandler:
    """Test batch request handling."""

    def test_is_batch_true(self) -> None:
        """Test identifying batch requests."""
        batch = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2},
        ]

        assert BatchRequestHandler.is_batch(batch) is True

    def test_is_batch_false(self) -> None:
        """Test single request is not batch."""
        single = {"jsonrpc": "2.0", "method": "test", "id": 1}

        assert BatchRequestHandler.is_batch(single) is False

    def test_is_batch_empty_list(self) -> None:
        """Test empty list is still a batch."""
        assert BatchRequestHandler.is_batch([]) is True

    @pytest.mark.asyncio
    async def test_process_batch_success(self) -> None:
        """Test processing batch of successful requests."""
        messages = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "test2", "id": 2},
        ]

        async def mock_handler(msg):
            return JSONRPCMessage.create_response(msg["id"], result={"method": msg["method"]})

        responses = await BatchRequestHandler.process_batch(messages, mock_handler)

        assert len(responses) == 2
        assert responses[0]["id"] == 1
        assert responses[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_process_batch_with_notifications(self) -> None:
        """Test batch with notifications (no response)."""
        messages = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "notification"},  # No ID
            {"jsonrpc": "2.0", "method": "test2", "id": 2},
        ]

        async def mock_handler(msg):
            if "id" in msg:
                return JSONRPCMessage.create_response(msg["id"], result={})
            return None

        responses = await BatchRequestHandler.process_batch(messages, mock_handler)

        # Only 2 responses (notification should not have response)
        assert len(responses) == 2

    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self) -> None:
        """Test batch with some errors."""
        messages = [
            {"jsonrpc": "2.0", "method": "test1", "id": 1},
            {"jsonrpc": "2.0", "method": "error", "id": 2},
        ]

        async def mock_handler(msg):
            if msg["method"] == "error":
                raise JSONRPCError(JSONRPCErrorCode.METHOD_NOT_FOUND, "Not found")
            return JSONRPCMessage.create_response(msg["id"], result={})

        responses = await BatchRequestHandler.process_batch(messages, mock_handler)

        assert len(responses) == 2
        assert "result" in responses[0]
        assert "error" in responses[1]
        assert responses[1]["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_process_batch_empty(self) -> None:
        """Test processing empty batch returns None."""
        responses = await BatchRequestHandler.process_batch([], lambda x: x)

        assert responses is None

    @pytest.mark.asyncio
    async def test_process_batch_all_notifications(self) -> None:
        """Test batch of only notifications returns None."""
        messages = [
            {"jsonrpc": "2.0", "method": "notif1"},
            {"jsonrpc": "2.0", "method": "notif2"},
        ]

        async def mock_handler(msg):
            return None  # Notifications don't return responses

        responses = await BatchRequestHandler.process_batch(messages, mock_handler)

        assert responses is None


class TestProtocolCompliance:
    """Test JSON-RPC 2.0 protocol compliance."""

    def test_required_fields_in_request(self) -> None:
        """Test all required request fields are validated."""
        # Valid request
        valid = json.dumps({"jsonrpc": "2.0", "method": "test", "id": 1})
        message = JSONRPCMessage.parse_request(valid)
        assert "jsonrpc" in message
        assert "method" in message

    def test_optional_fields_allowed(self) -> None:
        """Test optional fields are allowed."""
        with_params = json.dumps({"jsonrpc": "2.0", "method": "test", "params": {}, "id": 1})
        message = JSONRPCMessage.parse_request(with_params)
        assert "params" in message

        without_params = json.dumps({"jsonrpc": "2.0", "method": "test", "id": 1})
        message2 = JSONRPCMessage.parse_request(without_params)
        assert "params" not in message2

    def test_response_mutual_exclusivity(self) -> None:
        """Test response has either result or error, not both."""
        # Success response
        success = JSONRPCMessage.create_response(1, result={"ok": True})
        assert "result" in success
        assert "error" not in success

        # Error response
        error_obj = JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, "Error")
        error_response = JSONRPCMessage.create_response(1, error=error_obj)
        assert "error" in error_response
        assert "result" not in error_response

    def test_id_types_supported(self) -> None:
        """Test various ID types are supported."""
        # Number ID
        req1 = json.dumps({"jsonrpc": "2.0", "method": "test", "id": 123})
        msg1 = JSONRPCMessage.parse_request(req1)
        assert msg1["id"] == 123

        # String ID
        req2 = json.dumps({"jsonrpc": "2.0", "method": "test", "id": "abc-123"})
        msg2 = JSONRPCMessage.parse_request(req2)
        assert msg2["id"] == "abc-123"

        # Null ID (notification)
        req3 = json.dumps({"jsonrpc": "2.0", "method": "test"})
        msg3 = JSONRPCMessage.parse_request(req3)
        assert "id" not in msg3


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_parse_error_on_malformed_json(self) -> None:
        """Test parse error for malformed JSON."""
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request("{invalid json")

        assert exc_info.value.code == JSONRPCErrorCode.PARSE_ERROR

    def test_invalid_request_error(self) -> None:
        """Test invalid request error."""
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request(json.dumps({"method": "test"}))

        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST

    def test_error_message_formatting(self) -> None:
        """Test error messages are descriptive."""
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCMessage.parse_request(json.dumps({"jsonrpc": "2.0", "id": 1}))

        assert "method" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_batch_handles_internal_errors(self) -> None:
        """Test batch handles unexpected internal errors."""
        messages = [{"jsonrpc": "2.0", "method": "test", "id": 1}]

        async def failing_handler(msg):
            raise RuntimeError("Unexpected error")

        responses = await BatchRequestHandler.process_batch(messages, failing_handler)

        assert len(responses) == 1
        assert "error" in responses[0]
        assert responses[0]["error"]["code"] == JSONRPCErrorCode.INTERNAL_ERROR
