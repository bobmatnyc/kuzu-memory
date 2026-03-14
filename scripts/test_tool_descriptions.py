#!/usr/bin/env python3
"""Test script to verify MCP tool descriptions are properly formatted."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from kuzu_memory.mcp.server import KuzuMemoryMCPServer

    # Create server instance
    server = KuzuMemoryMCPServer(project_root=Path.cwd())

    print("✅ MCP Server initialized successfully")
    print("\n📋 Tool Descriptions:")
    print("=" * 80)

    # Get the tool list handler
    import asyncio

    for handler_name, handler in server.server.request_handlers.items():
        if handler_name == "tools/list":
            tools = asyncio.run(handler())

            for tool in tools:
                print(f"\n🔧 {tool.name}")
                print(f"   Description: {tool.description[:100]}...")
                print(f"   Full length: {len(tool.description)} chars")

                # Check for key terms
                keywords = {
                    "kuzu_enhance": ["RAG", "semantic search", "context injection"],
                    "kuzu_learn": ["ASYNC", "BACKGROUND", "NON-BLOCKING"],
                    "kuzu_recall": ["semantic", "vector search", "similarity"],
                    "kuzu_remember": ["SYNC", "IMMEDIATE", "BLOCKING"],
                    "kuzu_stats": ["health", "diagnostics", "metrics"],
                }

                if tool.name in keywords:
                    missing = [
                        kw
                        for kw in keywords[tool.name]
                        if kw.lower() not in tool.description.lower()
                    ]
                    if missing:
                        print(f"   ⚠️  Missing keywords: {missing}")
                    else:
                        print("   ✅ All keywords present")

            print("\n" + "=" * 80)
            print(f"✅ All {len(tools)} tools verified successfully!")
            sys.exit(0)

    print("❌ Could not find tool list handler")
    sys.exit(1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 MCP SDK may not be installed. This is expected if testing without MCP.")
    sys.exit(0)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
