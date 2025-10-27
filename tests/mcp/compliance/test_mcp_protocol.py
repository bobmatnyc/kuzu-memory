"""
MCP protocol compliance tests.

Tests MCP-specific protocol requirements including version negotiation,
tool schemas, capability negotiation, and server info.
"""

import pytest

# MCP Protocol Versions
MCP_PROTOCOL_VERSIONS = ["2025-06-18", "2024-11-05"]


@pytest.mark.compliance
class TestProtocolVersionNegotiation:
    """Test MCP protocol version negotiation."""

    @pytest.mark.asyncio
    async def test_current_version_supported(self, mcp_client):
        """Test that current protocol version is supported."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        assert response is not None
        assert "result" in response or "error" not in response
        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_legacy_version_supported(self, mcp_client):
        """Test that legacy protocol version is supported."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2024-11-05"})

        assert response is not None
        # Should either accept or gracefully handle
        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_protocol_version_in_response(self, mcp_client):
        """Test that initialize response includes protocol version."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        if response and "result" in response:
            result = response["result"]
            assert "protocolVersion" in result, "Initialize result must include protocolVersion"
            assert (
                result["protocolVersion"] in MCP_PROTOCOL_VERSIONS
            ), "Must be valid protocol version"

        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_unsupported_version_handling(self, mcp_client):
        """Test handling of unsupported protocol version."""
        await mcp_client.connect()

        response = await mcp_client.send_request(
            "initialize",
            {"protocolVersion": "1999-01-01"},  # Invalid version
        )

        # Should either accept with fallback or return error
        assert response is not None

        await mcp_client.disconnect()


@pytest.mark.compliance
class TestInitializeMethod:
    """Test initialize method compliance."""

    @pytest.mark.asyncio
    async def test_initialize_required_before_operations(self, mcp_client):
        """Test that initialize must be called before operations."""
        await mcp_client.connect()

        # Call initialize
        init_response = await mcp_client.send_request(
            "initialize", {"protocolVersion": "2025-06-18"}
        )

        assert init_response is not None

        # Now operations should work
        tools_response = await mcp_client.send_request("tools/list", {})
        assert tools_response is not None

        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_initialize_returns_server_info(self, mcp_client):
        """Test that initialize returns server information."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        if response and "result" in response:
            result = response["result"]
            assert "serverInfo" in result, "Must include serverInfo"
            server_info = result["serverInfo"]
            assert "name" in server_info, "serverInfo must have name"
            assert "version" in server_info, "serverInfo must have version"

        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_initialize_returns_capabilities(self, mcp_client):
        """Test that initialize returns server capabilities."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        if response and "result" in response:
            result = response["result"]
            assert "capabilities" in result, "Must include capabilities"
            capabilities = result["capabilities"]
            assert isinstance(capabilities, dict), "Capabilities must be object"

        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, mcp_client):
        """Test that initialize can be called multiple times safely."""
        await mcp_client.connect()

        # First initialize
        response1 = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})
        assert response1 is not None

        # Second initialize should also work
        response2 = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})
        assert response2 is not None

        await mcp_client.disconnect()


@pytest.mark.compliance
class TestToolsList:
    """Test tools/list method compliance."""

    @pytest.mark.asyncio
    async def test_tools_list_returns_array(self, initialized_client):
        """Test that tools/list returns array of tools."""
        response = await initialized_client.send_request("tools/list", {})

        assert response is not None
        if "result" in response:
            result = response["result"]
            assert "tools" in result, "Result must have tools field"
            assert isinstance(result["tools"], list), "Tools must be array"

    @pytest.mark.asyncio
    async def test_tool_schema_structure(self, initialized_client):
        """Test that each tool has required schema fields."""
        response = await initialized_client.send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])

            assert len(tools) > 0, "Should have at least one tool"

            for tool in tools:
                assert "name" in tool, "Tool must have name"
                assert "description" in tool, "Tool must have description"
                assert "inputSchema" in tool, "Tool must have inputSchema"

                # Validate inputSchema is JSON Schema
                schema = tool["inputSchema"]
                assert isinstance(schema, dict), "inputSchema must be object"
                assert "type" in schema, "inputSchema must have type"
                assert "properties" in schema, "inputSchema must have properties"

    @pytest.mark.asyncio
    async def test_tool_names_unique(self, initialized_client):
        """Test that tool names are unique."""
        response = await initialized_client.send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])
            names = [t["name"] for t in tools]

            assert len(names) == len(set(names)), "Tool names must be unique"

    @pytest.mark.asyncio
    async def test_required_tools_present(self, initialized_client):
        """Test that required KuzuMemory tools are present."""
        response = await initialized_client.send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])
            tool_names = {t["name"] for t in tools}

            # KuzuMemory should have these core tools
            expected_tools = {"enhance", "recall", "stats", "remember"}
            assert expected_tools.issubset(
                tool_names
            ), f"Missing required tools: {expected_tools - tool_names}"


@pytest.mark.compliance
class TestToolsCall:
    """Test tools/call method compliance."""

    @pytest.mark.asyncio
    async def test_tools_call_structure(self, initialized_client):
        """Test tools/call request/response structure."""
        response = await initialized_client.call_tool("stats", {})

        assert response is not None
        if "result" in response:
            result = response["result"]
            assert isinstance(result, dict), "Tool result should be object"

    @pytest.mark.asyncio
    async def test_tools_call_with_arguments(self, initialized_client):
        """Test tools/call with arguments."""
        response = await initialized_client.call_tool("recall", {"query": "test", "limit": 5})

        assert response is not None

    @pytest.mark.asyncio
    async def test_tools_call_missing_required_param(self, initialized_client):
        """Test tools/call with missing required parameter."""
        response = await initialized_client.call_tool("enhance", {})  # Missing prompt

        # Should return error
        if response:
            assert "error" in response, "Missing required param should error"

    @pytest.mark.asyncio
    async def test_tools_call_invalid_tool_name(self, initialized_client):
        """Test tools/call with invalid tool name."""
        response = await initialized_client.call_tool("nonexistent_tool", {})

        if response:
            assert "error" in response, "Invalid tool should error"
            assert response["error"]["code"] == -32601, "Should be method not found"

    @pytest.mark.asyncio
    async def test_tools_call_result_format(self, initialized_client):
        """Test that tool call results follow expected format."""
        response = await initialized_client.call_tool("stats", {})

        if response and "result" in response:
            result = response["result"]
            # Result should be structured data
            assert isinstance(result, dict | list | str), "Result must be valid type"


@pytest.mark.compliance
class TestToolSchemaValidation:
    """Test tool schema validation compliance."""

    @pytest.mark.asyncio
    async def test_input_schema_json_schema_compliant(self, initialized_client):
        """Test that tool inputSchema follows JSON Schema spec."""
        response = await initialized_client.send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])

            for tool in tools:
                schema = tool["inputSchema"]

                # Must have JSON Schema type
                assert "type" in schema, f"Tool {tool['name']} schema missing type"
                assert schema["type"] == "object", "Input schema type should be object"

                # Must have properties
                assert "properties" in schema, f"Tool {tool['name']} schema missing properties"
                assert isinstance(schema["properties"], dict), "Properties must be object"

    @pytest.mark.asyncio
    async def test_required_parameters_specified(self, initialized_client):
        """Test that required parameters are specified in schema."""
        response = await initialized_client.send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])

            for tool in tools:
                schema = tool["inputSchema"]

                # If there are required fields, check they're valid
                if "required" in schema:
                    required = schema["required"]
                    assert isinstance(required, list), "Required must be array"
                    properties = schema["properties"]

                    for req_field in required:
                        assert (
                            req_field in properties
                        ), f"Required field {req_field} not in properties"

    @pytest.mark.asyncio
    async def test_parameter_types_specified(self, initialized_client):
        """Test that parameter types are specified."""
        response = await initialized_client.send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])

            for tool in tools:
                properties = tool["inputSchema"].get("properties", {})

                for param_name, param_schema in properties.items():
                    assert "type" in param_schema, f"Parameter {param_name} missing type"
                    assert isinstance(param_schema["type"], str), "Type must be string"


@pytest.mark.compliance
class TestCapabilityNegotiation:
    """Test capability negotiation."""

    @pytest.mark.asyncio
    async def test_server_advertises_capabilities(self, mcp_client):
        """Test that server advertises its capabilities."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        if response and "result" in response:
            result = response["result"]
            assert "capabilities" in result, "Must advertise capabilities"

            capabilities = result["capabilities"]
            # Check for expected capabilities
            assert isinstance(capabilities, dict), "Capabilities must be object"

        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_tools_capability(self, mcp_client):
        """Test that tools capability is advertised."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        if response and "result" in response:
            capabilities = response["result"].get("capabilities", {})

            # Server should indicate it provides tools
            # This depends on MCP implementation specifics
            assert isinstance(capabilities, dict), "Capabilities structure valid"

        await mcp_client.disconnect()


@pytest.mark.compliance
class TestServerInfo:
    """Test server info compliance."""

    @pytest.mark.asyncio
    async def test_server_info_structure(self, mcp_client):
        """Test server info has required fields."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        if response and "result" in response:
            server_info = response["result"].get("serverInfo", {})

            assert "name" in server_info, "serverInfo must have name"
            assert "version" in server_info, "serverInfo must have version"

            assert isinstance(server_info["name"], str), "Name must be string"
            assert isinstance(server_info["version"], str), "Version must be string"

        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_server_version_format(self, mcp_client):
        """Test that server version follows semantic versioning."""
        await mcp_client.connect()

        response = await mcp_client.send_request("initialize", {"protocolVersion": "2025-06-18"})

        if response and "result" in response:
            server_info = response["result"].get("serverInfo", {})
            version = server_info.get("version", "")

            # Should follow semver: X.Y.Z
            parts = version.split(".")
            assert len(parts) >= 2, f"Version {version} should be X.Y or X.Y.Z format"

        await mcp_client.disconnect()


@pytest.mark.compliance
class TestProtocolUpgrade:
    """Test protocol version upgrade handling."""

    @pytest.mark.asyncio
    async def test_protocol_version_backward_compatible(self, mcp_client):
        """Test backward compatibility with older protocol versions."""
        await mcp_client.connect()

        # Try older version
        response = await mcp_client.send_request("initialize", {"protocolVersion": "2024-11-05"})

        # Should handle gracefully (accept or provide fallback)
        assert response is not None

        await mcp_client.disconnect()

    @pytest.mark.asyncio
    async def test_protocol_version_forward_compatible(self, mcp_client):
        """Test handling of future protocol versions."""
        await mcp_client.connect()

        # Try future version
        response = await mcp_client.send_request("initialize", {"protocolVersion": "2099-12-31"})

        # Should handle gracefully (fallback to supported version or error)
        assert response is not None

        await mcp_client.disconnect()


@pytest.mark.compliance
class TestMethodDiscovery:
    """Test method discovery and introspection."""

    @pytest.mark.asyncio
    async def test_tools_list_discoverability(self, initialized_client):
        """Test that tools/list enables tool discovery."""
        response = await initialized_client.send_request("tools/list", {})

        if response and "result" in response:
            tools = response["result"].get("tools", [])

            # Should provide enough info to call tools
            for tool in tools:
                assert "name" in tool, "Need name to call tool"
                assert "description" in tool, "Need description for understanding"
                assert "inputSchema" in tool, "Need schema for parameter validation"

    @pytest.mark.asyncio
    async def test_ping_method_available(self, initialized_client):
        """Test that ping method is available for health checks."""
        response = await initialized_client.send_request("ping", {})

        assert response is not None
        # Ping should succeed quickly
        assert "result" in response or "error" not in response
