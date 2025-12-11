"""
JSON-RPC 2.0 protocol implementation for MCP server.

Implements the JSON-RPC 2.0 specification for communication between
Claude Code and the KuzuMemory MCP server.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import select
import sys
import threading
from collections.abc import Callable
from enum import IntEnum
from queue import Empty, Queue
from typing import Any, TextIO

logger = logging.getLogger(__name__)


class JSONRPCErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 error codes."""

    # Standard errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Implementation-defined errors
    SERVER_ERROR_START = -32099
    SERVER_ERROR_END = -32000

    # Custom MCP errors
    TOOL_EXECUTION_ERROR = -32001
    INITIALIZATION_ERROR = -32002
    TIMEOUT_ERROR = -32003


class JSONRPCError(Exception):
    """JSON-RPC error with code and message."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        """Initialize JSON-RPC error."""
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-RPC error format."""
        error_dict = {"code": self.code, "message": self.message}
        if self.data is not None:
            error_dict["data"] = self.data
        return error_dict


class JSONRPCMessage:
    """JSON-RPC 2.0 message handler."""

    @staticmethod
    def parse_request(raw_message: str) -> dict[str, Any]:
        """
        Parse and validate a JSON-RPC request.

        Args:
            raw_message: Raw JSON string

        Returns:
            Parsed request dictionary

        Raises:
            JSONRPCError: If parsing or validation fails
        """
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError as e:
            raise JSONRPCError(JSONRPCErrorCode.PARSE_ERROR, f"Parse error: {e!s}")

        # Validate JSON-RPC version
        if message.get("jsonrpc") != "2.0":
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Invalid JSON-RPC version, must be '2.0'",
            )

        # Validate method
        if "method" not in message:
            raise JSONRPCError(JSONRPCErrorCode.INVALID_REQUEST, "Missing 'method' field")

        if not isinstance(message["method"], str):
            raise JSONRPCError(JSONRPCErrorCode.INVALID_REQUEST, "'method' must be a string")

        # Validate params if present
        if "params" in message:
            if not isinstance(message["params"], dict | list):
                raise JSONRPCError(
                    JSONRPCErrorCode.INVALID_REQUEST,
                    "'params' must be an object or array",
                )

        # Type narrowing: we've validated that message is a dict with required fields
        return message  # type: ignore[no-any-return]

    @staticmethod
    def create_response(
        request_id: str | int | None,
        result: Any | None = None,
        error: JSONRPCError | None = None,
    ) -> dict[str, Any] | None:
        """
        Create a JSON-RPC response.

        Args:
            request_id: ID from the request (None for notifications)
            result: Success result (mutually exclusive with error)
            error: Error result (mutually exclusive with result)

        Returns:
            JSON-RPC response dictionary
        """
        if request_id is None:
            # Notifications don't get responses
            return None

        response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}

        if error is not None:
            response["error"] = error.to_dict() if isinstance(error, JSONRPCError) else error
        else:
            response["result"] = result if result is not None else {}

        return response

    @staticmethod
    def create_notification(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Create a JSON-RPC notification (no response expected).

        Args:
            method: Method name
            params: Optional parameters

        Returns:
            JSON-RPC notification dictionary
        """
        notification: dict[str, Any] = {"jsonrpc": "2.0", "method": method}

        if params is not None:
            notification["params"] = params

        return notification

    @staticmethod
    def is_notification(message: dict[str, Any]) -> bool:
        """
        Check if a message is a notification (no ID field).

        Args:
            message: Parsed JSON-RPC message

        Returns:
            True if notification, False if request
        """
        return "id" not in message


class JSONRPCProtocol:
    """JSON-RPC 2.0 protocol handler for stdio communication."""

    reader: TextIO
    writer: TextIO
    running: bool
    _buffer: str
    _message_queue: Queue[str | None]
    _reader_thread: threading.Thread | None

    def __init__(self) -> None:
        """Initialize JSON-RPC protocol handler."""
        # Ensure text mode for stdin/stdout
        if isinstance(sys.stdin, io.BufferedReader):
            self.reader = io.TextIOWrapper(sys.stdin, encoding="utf-8")
        else:
            self.reader = sys.stdin

        if isinstance(sys.stdout, io.BufferedWriter):
            self.writer = io.TextIOWrapper(sys.stdout, encoding="utf-8", line_buffering=True)
        else:
            self.writer = sys.stdout

        self.running = True
        self._buffer = ""
        self._message_queue: Queue[str | None] = Queue()
        self._reader_thread: threading.Thread | None = None

    def _read_stdin_sync(self) -> None:
        """Synchronously read from stdin in a separate thread."""
        try:
            while self.running:
                # Use select to check if stdin has data available (with timeout)
                # This allows us to periodically check self.running
                if sys.platform == "win32":
                    # Windows doesn't support select on stdin, use blocking read
                    line = self.reader.readline()
                else:
                    # Unix-like systems: use select with timeout
                    ready, _, exceptional = select.select([self.reader], [], [self.reader], 0.5)

                    if exceptional:
                        # Exception on stdin (closed, etc)
                        self._message_queue.put(None)
                        self.running = False
                        break

                    if not ready:
                        # Timeout - check if we should continue
                        if not self.running:
                            break  # type: ignore[unreachable]  # self.running can be modified by another thread
                        continue

                    # Data is available, read it
                    line = self.reader.readline()

                if not line:  # EOF
                    # Signal EOF by putting None in queue
                    self._message_queue.put(None)
                    self.running = False  # Stop the protocol
                    break

                line = line.strip()
                if line:  # Skip empty lines
                    self._message_queue.put(line)

                # Check if we should stop
                if not self.running:
                    break  # type: ignore[unreachable]  # self.running can be modified by another thread

        except Exception as e:
            logger.error(f"Error in stdin reader thread: {e}")
            self._message_queue.put(None)
            self.running = False

    async def initialize(self) -> None:
        """Initialize stdio communication with synchronous reading thread."""
        # Start the synchronous reader thread
        self._reader_thread = threading.Thread(target=self._read_stdin_sync, daemon=True)
        self._reader_thread.start()

    async def read_message(self) -> dict[str, Any] | list[dict[str, Any]] | None:
        """
        Read a single JSON-RPC message from stdin.

        Returns:
            Parsed message (dict for single request, list for batch) or None if EOF
        """
        loop = asyncio.get_event_loop()

        while self.running:
            try:
                # Check for messages from the reader thread using executor
                line = None
                try:
                    # Helper function that handles Empty exception
                    def get_with_timeout() -> Any:
                        try:
                            return self._message_queue.get(timeout=0.1)
                        except Empty:
                            return "__EMPTY__"  # Sentinel value for empty queue

                    # Run blocking queue.get in executor to avoid blocking the event loop
                    result = await loop.run_in_executor(None, get_with_timeout)

                    if result == "__EMPTY__":
                        raise Empty()  # Re-raise for the outer handler

                    line = result
                except Empty:
                    # Check if we should stop
                    if not self.running:
                        return None  # type: ignore[unreachable]  # self.running can be modified by another thread
                    # No message yet, continue waiting
                    await asyncio.sleep(0.01)
                    continue

                if line is None:
                    # EOF signal received
                    return None

                # Parse the JSON-RPC message (could be batch or single)
                try:
                    parsed = json.loads(line)
                    # For batch requests, return the list directly
                    if isinstance(parsed, list):
                        return parsed
                    # For single requests, validate and return
                    return JSONRPCMessage.parse_request(line)
                except JSONRPCError as e:
                    # Return error as a special message
                    return {
                        "jsonrpc": "2.0",
                        "error": e.to_dict(),
                        "id": None,  # We don't know the ID yet
                    }

            except asyncio.CancelledError:
                self.running = False
                return None
            except Exception as e:
                logger.error(f"Error reading message: {e}")
                return None

        return None

    def write_message(self, message: dict[str, Any]) -> None:
        """
        Write a JSON-RPC message to stdout.

        Args:
            message: Message to send
        """
        try:
            json_str = json.dumps(message, separators=(",", ":"))
            self.writer.write(json_str + "\n")
            self.writer.flush()

            # Verify write succeeded
            if self.writer.closed:
                logger.error("Cannot write - stdout is closed")
                raise RuntimeError("stdout closed")

        except BrokenPipeError:
            logger.error("Broken pipe - client disconnected")
            self.running = False
        except Exception as e:
            logger.error(f"Error writing message: {e}")
            raise

    async def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """
        Send a JSON-RPC notification.

        Args:
            method: Method name
            params: Optional parameters
        """
        notification = JSONRPCMessage.create_notification(method, params)
        self.write_message(notification)

    def close(self) -> None:
        """Close the protocol handler."""
        self.running = False
        # Stop the reader thread
        if self._reader_thread and self._reader_thread.is_alive():
            # Put None to signal thread to exit
            self._message_queue.put(None)
            # Give thread time to exit gracefully
            self._reader_thread.join(timeout=1.0)


class BatchRequestHandler:
    """Handler for JSON-RPC batch requests."""

    @staticmethod
    def is_batch(message: Any) -> bool:
        """
        Check if a message is a batch request.

        Args:
            message: Parsed JSON message

        Returns:
            True if batch request
        """
        return isinstance(message, list)

    @staticmethod
    async def process_batch(
        messages: list[dict[str, Any]], handler_func: Callable[[dict[str, Any]], Any]
    ) -> list[dict[str, Any]] | None:
        """
        Process a batch of JSON-RPC requests.

        Args:
            messages: List of request messages
            handler_func: Async function to handle individual requests

        Returns:
            List of responses (excluding notification responses)
        """
        responses = []

        for message in messages:
            try:
                # Process request (message is already dict[str, Any] from type annotation)
                response = await handler_func(message)

                # Only include responses for non-notifications
                if response is not None:
                    responses.append(response)

            except JSONRPCError as e:
                # Include error response if there's an ID
                if isinstance(message, dict) and "id" in message:
                    responses.append(JSONRPCMessage.create_response(message["id"], error=e))
            except Exception as e:
                # Internal error
                if isinstance(message, dict) and "id" in message:
                    responses.append(
                        JSONRPCMessage.create_response(
                            message["id"],
                            error=JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, str(e)),
                        )
                    )

        return responses if responses else None
