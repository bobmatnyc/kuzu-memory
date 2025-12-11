#!/usr/bin/env python3
"""
Test the Kuzu CLI adapter implementation.
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path


def check_kuzu_cli():
    """Check if Kuzu CLI is available."""
    print("🔍 Checking for Kuzu CLI...")

    try:
        result = subprocess.run(["kuzu", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Kuzu CLI found: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Kuzu CLI error: {result.stderr}")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ Kuzu CLI not found: {e}")
        print("💡 Install with: brew install kuzu (macOS) or download from GitHub")
        return False


def test_cli_adapter():
    """Test the CLI adapter functionality."""
    import pytest

    pytest.skip("Standalone test file - CLI tested in unit/integration tests")

    print("\n🧪 Testing CLI Adapter")
    print("=" * 40)

    try:
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.kuzu_cli_adapter import KuzuCLIAdapter

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_cli.db"
            config = KuzuMemoryConfig()

            print(f"📁 Using database: {db_path}")

            # Test 1: Initialize adapter
            print("\n1️⃣ Testing adapter initialization...")
            adapter = KuzuCLIAdapter(db_path, config)
            print("✅ CLI adapter initialized")

            # Test 2: Simple query
            print("\n2️⃣ Testing simple query...")
            try:
                # Create a simple table
                create_query = """
                CREATE NODE TABLE TestNode (
                    id STRING PRIMARY KEY,
                    name STRING
                )
                """

                result = adapter.execute_query(create_query)
                print(f"✅ Table creation: {result}")

                # Insert data
                insert_query = """
                CREATE (n:TestNode {id: 'test1', name: 'Test Node'})
                """

                result = adapter.execute_query(insert_query)
                print(f"✅ Data insertion: {result}")

                # Query data
                select_query = """
                MATCH (n:TestNode)
                RETURN n.id, n.name
                """

                result = adapter.execute_query(select_query)
                print(f"✅ Data query: {result}")

            except Exception as e:
                print(f"❌ Query test failed: {e}")
                return False

            # Test 3: Performance comparison
            print("\n3️⃣ Testing performance...")

            # Test CLI adapter performance
            start_time = time.time()
            for i in range(10):
                query = f"CREATE (n:TestNode {{id: 'perf{i}', name: 'Performance Test {i}'}})"
                adapter.execute_query(query)
            cli_time = (time.time() - start_time) * 1000

            print(f"✅ CLI adapter: 10 queries in {cli_time:.1f}ms")

            adapter.close()

            return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_integration():
    """Test CLI adapter integration with KuzuMemory."""
    import pytest

    pytest.skip("Standalone test file - integration tested in proper test suite")
    print("\n🔗 Testing KuzuMemory Integration")
    print("=" * 40)

    try:
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.core.memory import KuzuMemory

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "integration_test.db"

            # Test with CLI adapter enabled
            config = KuzuMemoryConfig()
            config.storage.use_cli_adapter = True
            config.performance.max_recall_time_ms = 100.0
            config.performance.max_generation_time_ms = 200.0

            print("🚀 Testing with CLI adapter enabled...")

            with KuzuMemory(db_path=db_path, config=config) as memory:
                print("✅ KuzuMemory initialized with CLI adapter")

                # Test memory generation
                start_time = time.time()
                memory_ids = memory.generate_memories(
                    "I'm testing the CLI adapter for better performance",
                    user_id="cli-test",
                )
                generation_time = (time.time() - start_time) * 1000

                print(f"✅ Generated {len(memory_ids)} memories in {generation_time:.1f}ms")

                # Test memory recall
                start_time = time.time()
                context = memory.attach_memories("What am I testing?", user_id="cli-test")
                recall_time = (time.time() - start_time) * 1000

                print(f"✅ Recalled {len(context.memories)} memories in {recall_time:.1f}ms")

                if context.memories:
                    print(f"📋 Top memory: {context.memories[0].content[:50]}...")

            # Compare with Python API
            print("\n🐍 Testing with Python API...")

            config.storage.use_cli_adapter = False
            db_path2 = Path(temp_dir) / "python_test.db"

            with KuzuMemory(db_path=db_path2, config=config) as memory:
                print("✅ KuzuMemory initialized with Python API")

                # Test memory generation
                start_time = time.time()
                memory_ids = memory.generate_memories(
                    "I'm testing the Python API for comparison", user_id="python-test"
                )
                python_generation_time = (time.time() - start_time) * 1000

                print(f"✅ Generated {len(memory_ids)} memories in {python_generation_time:.1f}ms")

                # Performance comparison
                if generation_time > 0 and python_generation_time > 0:
                    speedup = python_generation_time / generation_time
                    print(f"📊 CLI adapter is {speedup:.1f}x faster than Python API")

            return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run CLI adapter tests."""
    print("🧪 KuzuMemory CLI Adapter Test Suite")
    print("=" * 60)

    # Check prerequisites
    if not check_kuzu_cli():
        print("\n❌ Kuzu CLI not available - skipping CLI adapter tests")
        print("💡 Install Kuzu CLI to test this feature")
        return 1

    # Run tests
    tests = [("CLI Adapter", test_cli_adapter), ("Integration", test_integration)]

    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"\n✅ {test_name} test passed")
                passed += 1
            else:
                print(f"\n❌ {test_name} test failed")
        except Exception as e:
            print(f"\n❌ {test_name} test error: {e}")

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 TEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"🎯 Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 ALL TESTS PASSED!")
        print("✅ CLI adapter is working correctly")
        print("🚀 KuzuMemory can now use native Kuzu CLI for optimal performance")
        return 0
    else:
        print(f"⚠️  {len(tests) - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
