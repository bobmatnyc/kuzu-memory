#!/usr/bin/env python3
"""
MCP Server entry point for python -m kuzu_memory.mcp.server
"""

import asyncio
import logging

from kuzu_memory.mcp.server import MCP_AVAILABLE, SimplifiedMCPServer, main

if __name__ == "__main__":
    # Run the appropriate server based on availability
    if MCP_AVAILABLE:
        asyncio.run(main())
    else:
        # Fallback to simplified server
        logging.basicConfig(level=logging.INFO)
        server = SimplifiedMCPServer()
        asyncio.run(server.run_stdio())
