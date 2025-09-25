#!/usr/bin/env python3
"""
Minimal test to validate core KuzuMemory functionality.
"""

import sys
import tempfile
import time
import logging
from pathlib import Path
from datetime import datetime

# Enable debug logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_direct_imports():
    """Test importing components directly."""
    import pytest
    pytest.skip("Standalone test file - functionality tested in unit tests")

    print("🧪 Testing Direct Imports")
    print("=" * 40)
    
    try:
        # Import directly from core modules
        from kuzu_memory.core.memory import KuzuMemory
        from kuzu_memory.core.models import Memory, MemoryType, MemoryContext
        from kuzu_memory.core.config import KuzuMemoryConfig
        
        print("✅ Direct imports successful")
        return True, (KuzuMemory, Memory, MemoryType, MemoryContext, KuzuMemoryConfig)
        
    except Exception as e:
        print(f"❌ Direct imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_basic_functionality():
    """Test basic memory operations."""
    import pytest
    pytest.skip("Standalone test file - functionality tested in integration tests")
    print("\n🧪 Testing Basic Memory Operations")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_memories.db"
        
        try:
            # Create configuration
            config = KuzuMemoryConfig()
            
            # Initialize KuzuMemory
            memory = KuzuMemory(db_path=db_path, config=config)
            
            print("✅ KuzuMemory initialized successfully")
            
            user_id = "test-user"
            
            # Test 1: Store a memory
            print("\n📝 Testing memory storage...")
            test_content = "My name is Alice Johnson and I work at TechCorp as a Senior Python Developer."
            
            start_time = time.time()
            memory_ids = memory.generate_memories(
                content=test_content,
                user_id=user_id,
                session_id="test-session",
                source="functionality_test"
            )
            storage_time = (time.time() - start_time) * 1000
            
            print(f"  ✅ Stored memory in {storage_time:.1f}ms")
            print(f"  📊 Generated {len(memory_ids)} memory IDs")
            
            # Test 2: Recall memories
            print("\n🔍 Testing memory recall...")
            test_query = "What's my name and where do I work?"
            
            start_time = time.time()
            context = memory.attach_memories(
                prompt=test_query,
                user_id=user_id,
                max_memories=5
            )
            recall_time = (time.time() - start_time) * 1000
            
            print(f"  ✅ Recalled memories in {recall_time:.1f}ms")
            print(f"  📊 Found {len(context.memories)} memories")
            print(f"  🎯 Confidence: {context.confidence:.2f}")
            print(f"  📈 Strategy: {context.strategy_used}")
            
            if context.memories:
                top_memory = context.memories[0]
                print(f"  🔝 Top memory: {top_memory.content[:60]}...")
            
            # Test 3: Performance validation
            print(f"\n⚡ Performance Analysis:")
            print(f"  Storage time: {storage_time:.1f}ms")
            print(f"  Recall time: {recall_time:.1f}ms")
            
            # Performance assertions
            storage_ok = storage_time < 50.0  # 50ms for storage
            recall_ok = recall_time < 20.0    # 20ms for recall
            
            print(f"  Storage performance: {'✅' if storage_ok else '⚠️'} ({'OK' if storage_ok else 'SLOW'})")
            print(f"  Recall performance: {'✅' if recall_ok else '⚠️'} ({'OK' if recall_ok else 'SLOW'})")
            
            # Test 4: Memory content validation
            print(f"\n🔍 Content Validation:")
            if context.memories:
                found_name = "alice" in context.memories[0].content.lower()
                found_company = "techcorp" in context.memories[0].content.lower()
                found_role = "python" in context.memories[0].content.lower()
                
                print(f"  Name found: {'✅' if found_name else '❌'}")
                print(f"  Company found: {'✅' if found_company else '❌'}")
                print(f"  Role found: {'✅' if found_role else '❌'}")
                
                content_ok = found_name and found_company and found_role
            else:
                content_ok = False
                print("  ❌ No memories found for validation")
            
            # Close memory
            memory.close()
            
            # Overall success
            success = len(memory_ids) > 0 and len(context.memories) > 0 and content_ok
            
            print(f"\n🎯 Overall Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error in basic functionality test: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_memory_persistence():
    """Test memory persistence across sessions."""
    import pytest
    pytest.skip("Standalone test file - functionality tested in integration tests")
    print("\n🧪 Testing Memory Persistence")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "persistence_test.db"
        user_id = "persistence-user"
        
        try:
            config = KuzuMemoryConfig()
            
            # Session 1: Store memories
            print("📝 Session 1: Storing memories...")
            memory1 = KuzuMemory(db_path=db_path, config=config)
            
            test_content = "I'm a data scientist specializing in machine learning and Python."
            memory_ids = memory1.generate_memories(test_content, user_id=user_id)
            print(f"  ✓ Stored {len(memory_ids)} memories")
            
            # Verify immediate recall
            context = memory1.attach_memories("What's my specialization?", user_id=user_id)
            print(f"  ✓ Immediate recall: {len(context.memories)} memories found")
            
            memory1.close()
            
            # Session 2: Verify persistence
            print("\n🔍 Session 2: Verifying persistence...")
            memory2 = KuzuMemory(db_path=db_path, config=config)
            
            context = memory2.attach_memories("What's my specialization?", user_id=user_id)
            
            if len(context.memories) > 0:
                print(f"  ✅ Persistence verified: {len(context.memories)} memories recalled")
                print(f"     Content: {context.memories[0].content[:60]}...")
                success = True
            else:
                print("  ❌ Persistence failed: No memories found")
                success = False
            
            memory2.close()
            return success
                
        except Exception as e:
            print(f"❌ Error in persistence test: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run minimal functionality tests."""
    print("🧪 KuzuMemory Minimal Functionality Test")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Direct imports
    import_success, components = test_direct_imports()
    if not import_success:
        print("\n❌ Import test failed. Cannot proceed with functionality tests.")
        return 1
    
    KuzuMemory, Memory, MemoryType, MemoryContext, KuzuMemoryConfig = components
    
    # Test 2: Basic functionality
    basic_success = test_basic_functionality(KuzuMemory, Memory, MemoryType, MemoryContext, KuzuMemoryConfig)
    
    # Test 3: Persistence
    persistence_success = test_memory_persistence(KuzuMemory, Memory, MemoryType, MemoryContext, KuzuMemoryConfig)
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    tests = [
        ("Import Test", import_success),
        ("Basic Functionality", basic_success),
        ("Memory Persistence", persistence_success)
    ]
    
    passed_tests = sum(1 for _, success in tests if success)
    total_tests = len(tests)
    
    print(f"🎯 Results: {passed_tests}/{total_tests} tests passed")
    
    for test_name, success in tests:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
    
    if passed_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! KuzuMemory core functionality is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
