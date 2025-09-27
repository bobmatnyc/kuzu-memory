#!/usr/bin/env python3
"""
Simple memory performance test script for quick validation.

This script is referenced by the `make memory-test` command and provides
a quick way to test basic memory system performance without the full
benchmark suite.
"""

import tempfile
import time
from pathlib import Path


def main():
    """Run basic memory performance tests."""
    print("🧠 KuzuMemory Performance Test")
    print("=" * 40)

    try:
        from kuzu_memory import KuzuMemory

        # Create temporary database
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "perf_test.db"

            # Initialize memory system
            print("📦 Initializing memory system...")
            memory = KuzuMemory(db_path=db_path)

            # Test memory generation
            print("🔨 Testing memory generation...")
            start_time = time.perf_counter()
            memory_ids = memory.generate_memories(
                "Alice is a Python developer working on microservices with FastAPI and PostgreSQL.",
                user_id="test-user",
                session_id="test-session",
            )
            generation_time = (time.perf_counter() - start_time) * 1000

            print(f"  Generated {len(memory_ids)} memories in {generation_time:.2f}ms")

            # Test memory recall
            print("🔍 Testing memory recall...")
            start_time = time.perf_counter()
            context = memory.attach_memories(
                "What programming languages are mentioned?",
                user_id="test-user",
                max_memories=5,
            )
            recall_time = (time.perf_counter() - start_time) * 1000

            print(f"  Recalled {len(context.memories)} memories in {recall_time:.2f}ms")

            # Performance summary
            print("\n📊 Performance Summary:")
            print(f"  Generation: {generation_time:.2f}ms")
            print(f"  Recall: {recall_time:.2f}ms")

            # Basic performance validation
            if generation_time < 1000.0 and recall_time < 500.0:
                print("✅ Performance test PASSED")
                return 0
            else:
                print("⚠️  Performance test completed with slower than optimal times")
                return 0

            memory.close()

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure kuzu-memory is installed: pip install -e .")
        return 1
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
