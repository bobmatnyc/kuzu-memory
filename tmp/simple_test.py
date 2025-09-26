#!/usr/bin/env python3
"""
Simple test to isolate import issues.
"""

import sys
import traceback

print("Testing imports...")

try:
    print("1. Testing basic imports...")
    from kuzu_memory.core.models import Memory, MemoryType
    print("   ✅ Models imported successfully")
except Exception as e:
    print(f"   ❌ Models import failed: {e}")
    traceback.print_exc()

try:
    print("2. Testing config import...")
    from kuzu_memory.core.config import KuzuMemoryConfig
    print("   ✅ Config imported successfully")
except Exception as e:
    print(f"   ❌ Config import failed: {e}")
    traceback.print_exc()

try:
    print("3. Testing main KuzuMemory import...")
    from kuzu_memory import KuzuMemory
    print("   ✅ KuzuMemory imported successfully")
except Exception as e:
    print(f"   ❌ KuzuMemory import failed: {e}")
    traceback.print_exc()

try:
    print("4. Testing Auggie integration import...")
    from kuzu_memory.integrations.auggie import AuggieIntegration
    print("   ✅ Auggie integration imported successfully")
except Exception as e:
    print(f"   ❌ Auggie integration import failed: {e}")
    traceback.print_exc()

print("Import test completed.")
