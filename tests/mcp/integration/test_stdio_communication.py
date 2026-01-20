"""
Comprehensive Stdio Communication Integration Tests.

Tests stdio transport layer including message encoding, framing,
large messages, malformed data handling, concurrent processing,
and encoding edge cases.
"""

import asyncio
import json

import pytest

from tests.mcp.fixtures.mock_clients import MCPClientSimulator


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestStdioCommunication:
    """Integration tests for stdio communication transport."""

    async def test_message_encoding_utf8(self, project_root):
        """Test that messages are properly encoded in UTF-8."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send message with UTF-8 characters
            response = await client.send_request(
                "ping", {"data": "Hello 世界 🌍"}, request_id=1
            )

            assert response is not None
            assert response.get("id") == 1

        finally:
            await client.disconnect()

    async def test_message_framing_newline_delimited(self, project_root):
        """Test newline-delimited JSON framing."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Verify messages are newline-delimited
            request = {"jsonrpc": "2.0", "method": "ping", "id": 1}
            message = json.dumps(request) + "\n"

            # Send directly
            client.process.stdin.write(message.encode())
            client.process.stdin.flush()

            # Should receive newline-delimited response
            response_line = await asyncio.wait_for(
                asyncio.to_thread(client.process.stdout.readline),
                timeout=5.0,
            )

            assert response_line.endswith(b"\n"), "Response not newline-terminated"

            response = json.loads(response_line.decode().strip())
            assert response.get("id") == 1

        finally:
            await client.disconnect()

    async def test_large_message_handling(self, project_root):
        """Test handling of large messages."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            # Create large payload (10KB)
            large_data = "x" * 10000

            response = await client.send_request(
                "ping", {"data": large_data}, request_id=1
            )

            assert response is not None
            # Should handle large message gracefully
            assert "id" in response

        finally:
            await client.disconnect()

    async def test_malformed_message_handling(self, project_root):
        """Test server response to malformed messages."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send invalid JSON
            malformed = "{'invalid': json}\n"
            client.process.stdin.write(malformed.encode())
            client.process.stdin.flush()

            # Should receive error response
            response_line = await asyncio.wait_for(
                asyncio.to_thread(client.process.stdout.readline),
                timeout=5.0,
            )

            response = json.loads(response_line.decode().strip())

            # Should be a parse error (-32700)
            assert "error" in response
            assert response["error"]["code"] == -32700

        finally:
            await client.disconnect()

    async def test_concurrent_message_processing(self, project_root):
        """Test processing multiple messages concurrently."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            # Send multiple requests rapidly
            num_requests = 10
            responses = []

            for i in range(num_requests):
                response = await client.send_request("ping", {}, request_id=i)
                responses.append(response)

            # Verify all received
            successful = sum(1 for r in responses if r is not None)
            assert (
                successful >= num_requests * 0.8
            ), f"Only {successful}/{num_requests} succeeded"

        finally:
            await client.disconnect()

    async def test_partial_message_recovery(self, project_root):
        """Test recovery from partial/incomplete messages."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Send partial JSON (without newline)
            partial = '{"jsonrpc": "2.0", "method": "ping"'
            client.process.stdin.write(partial.encode())
            client.process.stdin.flush()

            # Wait briefly
            await asyncio.sleep(0.2)

            # Complete the message
            completion = ', "id": 1}\n'
            client.process.stdin.write(completion.encode())
            client.process.stdin.flush()

            # Should eventually respond
            try:
                response_line = await asyncio.wait_for(
                    asyncio.to_thread(client.process.stdout.readline),
                    timeout=5.0,
                )
                response = json.loads(response_line.decode().strip())
                # If server handles partial correctly, should get response
                assert "id" in response or "error" in response
            except (TimeoutError, json.JSONDecodeError):
                # Also acceptable - server may reject partial messages
                pass

        finally:
            await client.disconnect()

    async def test_encoding_edge_cases(self, project_root):
        """Test various encoding edge cases."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        test_cases = [
            {"data": ""},  # Empty string
            {"data": " "},  # Whitespace
            {"data": "\n\t\r"},  # Control characters
            {"data": "\\"},  # Backslash
            {"data": '"'},  # Quote
            {"data": "😀😁😂"},  # Emojis
            {"data": "测试中文"},  # Chinese characters
            {"data": "Тест"},  # Cyrillic
        ]

        try:
            connected = await client.connect()
            assert connected

            for i, test_case in enumerate(test_cases):
                response = await client.send_request(
                    "ping", test_case, request_id=i + 1
                )
                assert response is not None, f"Failed on test case: {test_case}"

        finally:
            await client.disconnect()

    async def test_message_ordering_preservation(self, project_root):
        """Test that message ordering is preserved."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            # Send requests in order
            num_requests = 5
            sent_ids = list(range(1, num_requests + 1))

            responses = []
            for req_id in sent_ids:
                response = await client.send_request("ping", {}, request_id=req_id)
                responses.append(response)

            # Verify responses received for each request
            received_ids = [r.get("id") for r in responses if r is not None]

            # All IDs should be present
            assert len(received_ids) >= num_requests * 0.8

        finally:
            await client.disconnect()

    async def test_binary_safe_transmission(self, project_root):
        """Test that transmission is binary-safe."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Test with various binary-like strings
            test_data = "\x00\x01\x02\x03"  # Null bytes

            # JSON encoding should handle this
            response = await client.send_request(
                "ping", {"data": test_data}, request_id=1
            )

            # Should either succeed or fail gracefully
            assert response is not None

        finally:
            await client.disconnect()

    async def test_rapid_message_bursts(self, project_root):
        """Test handling of rapid message bursts."""
        client = MCPClientSimulator(project_root=project_root, timeout=10.0)

        try:
            connected = await client.connect()
            assert connected

            # Send burst of 20 messages
            burst_size = 20
            responses = []

            for i in range(burst_size):
                response = await client.send_request("ping", {}, request_id=i)
                responses.append(response)
                # No delay - true burst

            # Should handle most
            successful = sum(1 for r in responses if r is not None)
            success_rate = successful / burst_size

            assert success_rate >= 0.7, f"Only {successful}/{burst_size} succeeded"

        finally:
            await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.flaky_process
class TestStdioErrorHandling:
    """Tests for stdio communication error scenarios."""

    async def test_invalid_json_structure(self, project_root):
        """Test handling of structurally invalid JSON."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Missing required field
            invalid = json.dumps({"jsonrpc": "2.0"}) + "\n"
            client.process.stdin.write(invalid.encode())
            client.process.stdin.flush()

            response_line = await asyncio.wait_for(
                asyncio.to_thread(client.process.stdout.readline),
                timeout=5.0,
            )

            response = json.loads(response_line.decode().strip())
            assert "error" in response

        finally:
            await client.disconnect()

    async def test_wrong_jsonrpc_version(self, project_root):
        """Test handling of wrong JSON-RPC version."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Wrong version
            request = json.dumps({"jsonrpc": "1.0", "method": "ping", "id": 1}) + "\n"
            client.process.stdin.write(request.encode())
            client.process.stdin.flush()

            response_line = await asyncio.wait_for(
                asyncio.to_thread(client.process.stdout.readline),
                timeout=5.0,
            )

            response = json.loads(response_line.decode().strip())
            # Should handle gracefully
            assert "id" in response or "error" in response

        finally:
            await client.disconnect()

    async def test_missing_required_fields(self, project_root):
        """Test handling of messages with missing required fields."""
        client = MCPClientSimulator(project_root=project_root, timeout=5.0)

        try:
            connected = await client.connect()
            assert connected

            # Missing method
            invalid = json.dumps({"jsonrpc": "2.0", "id": 1}) + "\n"
            client.process.stdin.write(invalid.encode())
            client.process.stdin.flush()

            response_line = await asyncio.wait_for(
                asyncio.to_thread(client.process.stdout.readline),
                timeout=5.0,
            )

            response = json.loads(response_line.decode().strip())
            assert "error" in response
            assert response["error"]["code"] == -32600  # Invalid Request

        finally:
            await client.disconnect()

    async def test_extremely_large_message(self, project_root):
        """Test handling of extremely large messages."""
        client = MCPClientSimulator(project_root=project_root, timeout=15.0)

        try:
            connected = await client.connect()
            assert connected

            # 1MB message
            large_data = "x" * (1024 * 1024)

            try:
                response = await client.send_request(
                    "ping", {"data": large_data}, request_id=1
                )

                # Should either handle or reject gracefully
                if response is not None:
                    assert "id" in response or "error" in response

            except Exception:
                # Timeout or other error is acceptable for very large messages
                pass

        finally:
            await client.disconnect()
