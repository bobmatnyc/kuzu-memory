#!/usr/bin/env python3
"""
Simple test to isolate import issues.
"""

import traceback

print("Testing imports...")

try:
    print("1. Testing basic imports...")
    print("   ✅ Models imported successfully")
except Exception as e:
    print(f"   ❌ Models import failed: {e}")
    traceback.print_exc()

try:
    print("2. Testing config import...")
    print("   ✅ Config imported successfully")
except Exception as e:
    print(f"   ❌ Config import failed: {e}")
    traceback.print_exc()

try:
    print("3. Testing main KuzuMemory import...")
    print("   ✅ KuzuMemory imported successfully")
except Exception as e:
    print(f"   ❌ KuzuMemory import failed: {e}")
    traceback.print_exc()

try:
    print("4. Testing Auggie integration import...")
    print("   ✅ Auggie integration imported successfully")
except Exception as e:
    print(f"   ❌ Auggie integration import failed: {e}")
    traceback.print_exc()

print("Import test completed.")
