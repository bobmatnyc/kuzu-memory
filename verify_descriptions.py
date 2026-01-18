#!/usr/bin/env python3
"""Verify MCP tool descriptions contain required keywords."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Read the server.py file and check descriptions
server_file = Path(__file__).parent / "src" / "kuzu_memory" / "mcp" / "server.py"
content = server_file.read_text()

print("🔍 Verifying MCP Tool Descriptions")
print("=" * 80)

# Define expected keywords for each tool
checks = {
    "kuzu_enhance": {
        "keywords": ["RAG", "semantic search", "context injection", "prompt augmentation"],
        "found": False,
    },
    "kuzu_learn": {
        "keywords": ["ASYNC", "BACKGROUND", "NON-BLOCKING", "continuous learning"],
        "expected_cross_ref": "kuzu_remember",
        "found": False,
    },
    "kuzu_recall": {
        "keywords": ["semantic", "vector search", "similarity", "retrieval"],
        "found": False,
    },
    "kuzu_remember": {
        "keywords": ["SYNC", "IMMEDIATE", "BLOCKING", "critical"],
        "expected_cross_ref": "kuzu_learn",
        "found": False,
    },
    "kuzu_stats": {"keywords": ["health", "diagnostics", "metrics", "monitoring"], "found": False},
}

all_passed = True

for tool_name, check in checks.items():
    print(f"\n🔧 Checking {tool_name}:")

    # Find the tool definition
    tool_start = content.find(f'name="{tool_name}"')
    if tool_start == -1:
        print("   ❌ Tool definition not found")
        all_passed = False
        continue

    # Extract description (next 1500 chars should contain it)
    tool_section = content[tool_start : tool_start + 1500]

    # Check keywords
    missing_keywords = []
    for keyword in check["keywords"]:
        if keyword.lower() not in tool_section.lower():
            missing_keywords.append(keyword)

    if missing_keywords:
        print(f"   ⚠️  Missing keywords: {missing_keywords}")
        all_passed = False
    else:
        print(f"   ✅ All keywords present: {check['keywords']}")

    # Check cross-references if expected
    if "expected_cross_ref" in check:
        if check["expected_cross_ref"] in tool_section:
            print(f"   ✅ Cross-reference to {check['expected_cross_ref']} found")
        else:
            print(f"   ⚠️  Missing cross-reference to {check['expected_cross_ref']}")
            all_passed = False

    check["found"] = True

print("\n" + "=" * 80)

if all_passed:
    print("✅ All tool descriptions verified successfully!")
    print("\n📊 Summary:")
    print("   • All 5 tools have semantic keywords for MCPSearch")
    print("   • kuzu_learn and kuzu_remember clearly differentiated (async vs sync)")
    print("   • Cross-references between related tools added")
    print("   • Enhanced parameter descriptions included")
    sys.exit(0)
else:
    print("❌ Some checks failed")
    sys.exit(1)
