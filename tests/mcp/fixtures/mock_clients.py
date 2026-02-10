"""
Mock MCP Client Simulators for Testing.

Provides mock client implementations for testing MCP server behavior,
connection handling, and protocol compliance.
"""

import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ClientRequest:
    """Represents a client request with response tracking."""

    request_id: str | int
    method: str
    params: dict[str, Any] | None = None
    sent_at: float = 0.0
    response: dict[str, Any] | None = None
    received_at: float = 0.0
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        """Calculate request duration in milliseconds."""
        if self.received_at > 0:
            return (self.received_at - self.sent_at) * 1000
        return 0.0

    @property
    def success(self) -> bool:
        """Check if request was successful."""
        return self.response is not None and "error" not in self.response


@dataclass
class ClientSession:
    """Tracks a client session with statistics."""

    session_id: str
    requests: list[ClientRequest] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total_requests(self) -> int:
        """Total number of requests in session."""
        return len(self.requests)

    @property
    def successful_requests(self) -> int:
        """Count of successful requests."""
        return sum(1 for r in self.requests if r.success)

    @property
    def failed_requests(self) -> int:
        """Count of failed requests."""
        return self.total_requests - self.successful_requests

    @property
    def average_duration_ms(self) -> float:
        """Average request duration in milliseconds."""
        if not self.requests:
            return 0.0
        total = sum(r.duration_ms for r in self.requests if r.duration_ms > 0)
        count = sum(1 for r in self.requests if r.duration_ms > 0)
        return total / count if count > 0 else 0.0


class MCPClientSimulator:
    """Simulates an MCP client for testing server behavior."""

    def __init__(
        self,
        server_path: str | Path | None = None,
        project_root: Path | None = None,
        timeout: float = 5.0,
    ):
        """
        Initialize MCP client simulator.

        Args:
            server_path: Path to MCP server executable
            project_root: Project root directory
            timeout: Default timeout for requests in seconds
        """
        self.server_path = self._resolve_server_path(server_path)
        self.project_root = project_root or Path.cwd()
        self.timeout = timeout
        self.process: subprocess.Popen | None = None
        self.current_session: ClientSession | None = None
        self.request_id_counter = 0

    def _resolve_server_path(self, server_path: str | Path | None) -> str:
        """Resolve server executable path."""
        if server_path:
            return str(server_path)

        # Default to module execution
        return f"{sys.executable} -m kuzu_memory.mcp.run_server"

    async def connect(self) -> bool:
        """
        Connect to MCP server.

        Returns:
            True if connection successful
        """
        try:
            cmd = (
                self.server_path.split()
                if " " in self.server_path
                else [self.server_path]
            )

            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root),
                text=True,
                encoding="utf-8",
                bufsize=1,  # Line buffered
            )

            # Wait for process to start and protocol to initialize
            # Need sufficient time for server startup to avoid race conditions with
            # notifications sent immediately after connect (before initialize)
            await asyncio.sleep(0.5)

            # Check if still running
            if self.process.poll() is not None:
                return False

            # Start new session
            import time

            self.current_session = ClientSession(
                session_id=f"session_{int(time.time())}",
                start_time=time.time(),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from MCP server gracefully."""
        if self.process:
            try:
                # Send shutdown request
                await self.send_request("shutdown", {})

                # Wait for graceful shutdown
                await asyncio.sleep(0.5)

                # Terminate if still running
                if self.process.poll() is None:
                    self.process.terminate()
                    await asyncio.sleep(0.2)

                # Kill if necessary
                if self.process.poll() is None:
                    self.process.kill()

                self.process.wait(timeout=2)

            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.process = None

                # Close session
                if self.current_session:
                    import time

                    self.current_session.end_time = time.time()

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: str | int | None = None,
    ) -> dict[str, Any] | None:
        """
        Send JSON-RPC request to server.

        Args:
            method: Method name
            params: Optional parameters
            request_id: Optional request ID (auto-generated if None)

        Returns:
            Response dictionary or None on failure
        """
        if not self.process:
            raise RuntimeError("Not connected to server")

        import time

        # Generate request ID if not provided
        if request_id is None:
            self.request_id_counter += 1
            request_id = self.request_id_counter

        # Build request
        request = {"jsonrpc": "2.0", "method": method, "id": request_id}
        if params is not None:
            request["params"] = params

        # Track request
        client_request = ClientRequest(
            request_id=request_id, method=method, params=params, sent_at=time.time()
        )

        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Read response with timeout
            response_line = await asyncio.wait_for(
                asyncio.to_thread(self.process.stdout.readline),
                timeout=self.timeout,
            )

            if not response_line:
                client_request.error = "No response received"
                return None

            response = json.loads(response_line.strip())
            client_request.response = response
            client_request.received_at = time.time()

            return response

        except TimeoutError:
            client_request.error = f"Timeout after {self.timeout}s"
            return None
        except Exception as e:
            client_request.error = str(e)
            return None
        finally:
            # Add to session
            if self.current_session:
                self.current_session.requests.append(client_request)

    async def send_notification(
        self, method: str, params: dict[str, Any] | None = None
    ) -> None:
        """
        Send JSON-RPC notification (no response expected).

        Args:
            method: Method name
            params: Optional parameters
        """
        if not self.process:
            raise RuntimeError("Not connected to server")

        notification = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            notification["params"] = params

        notification_str = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_str)
        self.process.stdin.flush()

    async def initialize(
        self, protocol_version: str = "2025-06-18"
    ) -> dict[str, Any] | None:
        """
        Send initialize request to establish protocol.

        Args:
            protocol_version: Protocol version to request

        Returns:
            Server initialization response
        """
        return await self.send_request(
            "initialize", {"protocolVersion": protocol_version}
        )

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Call a server tool.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            Tool execution response
        """
        return await self.send_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

    async def list_tools(self) -> dict[str, Any] | None:
        """
        Request list of available tools.

        Returns:
            Tools list response
        """
        return await self.send_request("tools/list", {})

    async def send_batch(
        self, requests: list[dict[str, Any]]
    ) -> list[dict[str, Any]] | None:
        """
        Send batch request to server.

        Args:
            requests: List of request dictionaries

        Returns:
            List of responses or None on error
        """
        if not self.process:
            raise RuntimeError("Not connected to server")

        try:
            # Handle empty batch - per JSON-RPC 2.0, empty array is invalid
            if not requests:
                # Send empty batch and expect error response
                batch_str = json.dumps(requests) + "\n"
                self.process.stdin.write(batch_str)
                self.process.stdin.flush()

                # Use base timeout (not scaled) for empty batch
                response_line = await asyncio.wait_for(
                    asyncio.to_thread(self.process.stdout.readline),
                    timeout=self.timeout,
                )

                if not response_line:
                    return []  # Empty batch gets empty response

                return json.loads(response_line.strip())

            # Send batch as JSON array
            batch_str = json.dumps(requests) + "\n"
            self.process.stdin.write(batch_str)
            self.process.stdin.flush()

            # Read batch response with scaled timeout
            response_line = await asyncio.wait_for(
                asyncio.to_thread(self.process.stdout.readline),
                timeout=self.timeout * len(requests),
            )

            if not response_line:
                return None

            return json.loads(response_line.strip())

        except TimeoutError:
            logger.error("Batch request timeout")
            return None
        except Exception as e:
            logger.error(f"Batch request error: {e}")
            return None

    async def send_batch_request(self, requests: list[dict]) -> list[dict]:
        """
        Send a batch of JSON-RPC requests following JSON-RPC 2.0 spec.

        This method properly handles:
        - Regular requests (with id) that get responses
        - Notifications (without id) that don't get responses
        - Error handling per request
        - Response ID matching

        Args:
            requests: List of JSON-RPC request dictionaries

        Returns:
            List of JSON-RPC response dictionaries (excluding notifications)
        """
        if not self.process:
            raise RuntimeError("Not connected to server")

        import time

        responses = []

        # Process each request individually to ensure proper JSON-RPC 2.0 semantics
        for request in requests:
            try:
                # Check if this is a notification (no id field)
                is_notification = "id" not in request

                # Track request if it has an ID
                if not is_notification:
                    client_request = ClientRequest(
                        request_id=request["id"],
                        method=request.get("method", ""),
                        params=request.get("params"),
                        sent_at=time.time(),
                    )

                # Send individual request
                request_str = json.dumps(request) + "\n"
                self.process.stdin.write(request_str)
                self.process.stdin.flush()

                # Only read response for non-notifications
                if not is_notification:
                    try:
                        response_line = await asyncio.wait_for(
                            asyncio.to_thread(self.process.stdout.readline),
                            timeout=self.timeout,
                        )

                        if response_line:
                            response = json.loads(response_line.strip())
                            responses.append(response)

                            # Update tracking
                            client_request.response = response
                            client_request.received_at = time.time()

                            # Add to session
                            if self.current_session:
                                self.current_session.requests.append(client_request)

                    except TimeoutError:
                        # Create error response for timeout
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request["id"],
                            "error": {
                                "code": -32603,
                                "message": f"Request timeout after {self.timeout}s",
                            },
                        }
                        responses.append(error_response)

                        client_request.error = f"Timeout after {self.timeout}s"
                        if self.current_session:
                            self.current_session.requests.append(client_request)

            except Exception as e:
                # Create error response for any processing error
                if "id" in request:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {e!s}",
                        },
                    }
                    responses.append(error_response)

                logger.error(f"Error processing batch request: {e}")

        return responses

    async def stress_test(
        self, num_requests: int, request_delay_ms: float = 0
    ) -> ClientSession:
        """
        Perform stress test with multiple rapid requests.

        Args:
            num_requests: Number of requests to send
            request_delay_ms: Delay between requests in milliseconds

        Returns:
            Session with stress test results
        """
        for _ in range(num_requests):
            await self.send_request("ping", {})

            if request_delay_ms > 0:
                await asyncio.sleep(request_delay_ms / 1000)

        return self.current_session

    def get_session_stats(self) -> dict[str, Any]:
        """
        Get current session statistics.

        Returns:
            Dictionary of session statistics
        """
        if not self.current_session:
            return {"error": "No active session"}

        return {
            "session_id": self.current_session.session_id,
            "total_requests": self.current_session.total_requests,
            "successful": self.current_session.successful_requests,
            "failed": self.current_session.failed_requests,
            "average_duration_ms": self.current_session.average_duration_ms,
            "duration_range_ms": {
                "min": (
                    min(
                        r.duration_ms
                        for r in self.current_session.requests
                        if r.duration_ms > 0
                    )
                    if self.current_session.requests
                    else 0.0
                ),
                "max": (
                    max(
                        r.duration_ms
                        for r in self.current_session.requests
                        if r.duration_ms > 0
                    )
                    if self.current_session.requests
                    else 0.0
                ),
            },
        }


class ConcurrentClientSimulator:
    """Manages multiple concurrent client connections for load testing."""

    def __init__(self, num_clients: int = 5, **client_kwargs: Any):
        """
        Initialize concurrent client simulator.

        Args:
            num_clients: Number of concurrent clients
            **client_kwargs: Arguments passed to each MCPClientSimulator
        """
        self.num_clients = num_clients
        self.clients: list[MCPClientSimulator] = [
            MCPClientSimulator(**client_kwargs) for _ in range(num_clients)
        ]

    async def connect_all(self) -> int:
        """
        Connect all clients concurrently.

        Returns:
            Number of successful connections
        """
        results = await asyncio.gather(
            *[client.connect() for client in self.clients], return_exceptions=True
        )

        return sum(1 for r in results if r is True)

    async def disconnect_all(self) -> None:
        """Disconnect all clients concurrently."""
        await asyncio.gather(
            *[client.disconnect() for client in self.clients],
            return_exceptions=True,
        )

    async def concurrent_requests(
        self, method: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any] | None]:
        """
        Send same request from all clients concurrently.

        Args:
            method: Method name
            params: Request parameters

        Returns:
            List of responses from all clients
        """
        return await asyncio.gather(
            *[client.send_request(method, params) for client in self.clients],
            return_exceptions=True,
        )

    async def load_test(self, requests_per_client: int = 10) -> dict[str, Any]:
        """
        Perform load test with all clients.

        Args:
            requests_per_client: Number of requests each client should send

        Returns:
            Aggregate statistics from all clients
        """
        # Run stress test on all clients concurrently
        sessions = await asyncio.gather(
            *[client.stress_test(requests_per_client) for client in self.clients],
            return_exceptions=True,
        )

        # Aggregate statistics
        total_requests = sum(
            s.total_requests for s in sessions if isinstance(s, ClientSession)
        )
        total_successful = sum(
            s.successful_requests for s in sessions if isinstance(s, ClientSession)
        )
        total_failed = sum(
            s.failed_requests for s in sessions if isinstance(s, ClientSession)
        )

        all_durations = [
            r.duration_ms
            for s in sessions
            if isinstance(s, ClientSession)
            for r in s.requests
            if r.duration_ms > 0
        ]

        return {
            "num_clients": self.num_clients,
            "total_requests": total_requests,
            "successful": total_successful,
            "failed": total_failed,
            "success_rate": (
                total_successful / total_requests * 100 if total_requests > 0 else 0
            ),
            "average_duration_ms": (
                sum(all_durations) / len(all_durations) if all_durations else 0
            ),
            "min_duration_ms": min(all_durations) if all_durations else 0,
            "max_duration_ms": max(all_durations) if all_durations else 0,
        }

    async def simulate_load(
        self,
        operations: list[dict[str, Any]],
        operations_per_client: int = 10,
    ) -> dict[str, Any]:
        """
        Simulate realistic load with mixed operations across clients.

        Args:
            operations: List of operations to execute (method, params, is_tool)
            operations_per_client: Number of operations each client should perform

        Returns:
            Load test results with latency distribution
        """
        import time

        async def client_worker(client: MCPClientSimulator) -> dict[str, Any]:
            """Execute operations for a single client."""
            # Connect and initialize client
            connected = await client.connect()
            if not connected:
                return {"latencies": [], "successes": 0}

            await client.initialize()
            latencies = []
            successes = 0

            try:
                for _ in range(operations_per_client):
                    for op in operations:
                        method = op.get("method", "ping")
                        params = op.get("params", {})
                        is_tool = op.get("is_tool", False)

                        start = time.perf_counter()
                        try:
                            if is_tool:
                                # Normalize tool names: add kuzu_ prefix if missing
                                tool_name = (
                                    method
                                    if method.startswith("kuzu_")
                                    else f"kuzu_{method}"
                                )
                                result = await client.call_tool(tool_name, params)
                            else:
                                result = await client.send_request(method, params)

                            latency = (time.perf_counter() - start) * 1000
                            latencies.append(latency)

                            if result is not None:
                                successes += 1
                        except Exception as e:
                            # Log errors for debugging but don't fail
                            logger.debug(f"Operation {method} failed: {e}")
            finally:
                # Cleanup
                await client.disconnect()

            return {"latencies": latencies, "successes": successes}

        # Run concurrent workers
        results = await asyncio.gather(
            *[client_worker(c) for c in self.clients], return_exceptions=True
        )

        # Aggregate results
        all_latencies = []
        total_successes = 0
        total_ops = 0

        for r in results:
            if isinstance(r, dict):
                all_latencies.extend(r["latencies"])
                total_successes += r["successes"]
                total_ops += len(r["latencies"])

        client_avg_latencies = [
            sum(r["latencies"]) / len(r["latencies"]) if r["latencies"] else 0
            for r in results
            if isinstance(r, dict) and r["latencies"]
        ]

        return {
            "success_rate": total_successes / total_ops if total_ops > 0 else 0.0,
            "throughput": (
                total_ops / (max(all_latencies) / 1000) if all_latencies else 0.0
            ),
            "avg_latency": (
                sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
            ),
            "client_latencies": client_avg_latencies,
            "total_operations": total_ops,
        }
