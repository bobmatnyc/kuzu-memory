#!/usr/bin/env python3
"""
Debug memory generation process.
"""

import sys
import tempfile
import time
import logging
from pathlib import Path

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def debug_memory_generation():
    """Debug the memory generation process step by step."""
    print("🔍 Debugging Memory Generation Process")
    print("=" * 50)
    
    try:
        from kuzu_memory.core.memory import KuzuMemory
        from kuzu_memory.core.config import KuzuMemoryConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "debug_memories.db"
            
            # Create configuration with relaxed performance limits
            config = KuzuMemoryConfig()
            config.performance.max_recall_time_ms = 100.0
            config.performance.max_generation_time_ms = 200.0
            
            # Initialize KuzuMemory
            memory = KuzuMemory(db_path=db_path, config=config)
            
            print("✅ KuzuMemory initialized successfully")
            
            # Test different content types
            test_cases = [
                {
                    "name": "Simple Identity",
                    "content": "My name is Alice Johnson and I work at TechCorp as a Senior Python Developer.",
                    "user_id": "test-user-1"
                },
                {
                    "name": "Technical Preference", 
                    "content": "I prefer FastAPI for backend APIs and React for frontend applications.",
                    "user_id": "test-user-2"
                },
                {
                    "name": "Decision Record",
                    "content": "We decided to use PostgreSQL as our main database with Redis for caching.",
                    "user_id": "test-user-3"
                },
                {
                    "name": "Process Description",
                    "content": "I always write comprehensive unit tests using pytest before deploying code.",
                    "user_id": "test-user-4"
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                print(f"\n📝 Test Case {i+1}: {test_case['name']}")
                print(f"Content: {test_case['content']}")
                print(f"User ID: {test_case['user_id']}")
                
                try:
                    start_time = time.time()
                    memory_ids = memory.generate_memories(
                        content=test_case['content'],
                        user_id=test_case['user_id'],
                        session_id=f"debug-session-{i+1}",
                        source="debug_test"
                    )
                    generation_time = (time.time() - start_time) * 1000
                    
                    print(f"  ✅ Generated {len(memory_ids)} memories in {generation_time:.1f}ms")
                    
                    if memory_ids:
                        print(f"  📋 Memory IDs: {memory_ids}")
                        
                        # Test immediate recall
                        recall_query = f"What do you know about {test_case['user_id']}?"
                        context = memory.attach_memories(
                            prompt=recall_query,
                            user_id=test_case['user_id'],
                            max_memories=3
                        )
                        
                        print(f"  🔍 Recall test: Found {len(context.memories)} memories")
                        if context.memories:
                            for j, mem in enumerate(context.memories):
                                print(f"    {j+1}. {mem.content[:50]}...")
                    else:
                        print("  ⚠️  No memories generated - investigating...")
                        
                        # Check if content was processed
                        print("  🔍 Checking extraction process...")
                        
                        # Try to query database directly
                        try:
                            query_result = memory.db_adapter.execute_query(
                                f"MATCH (m:Memory {{user_id: '{test_case['user_id']}'}}) RETURN m.content, m.id"
                            )
                            if query_result:
                                print(f"    Database contains {len(query_result)} memories for this user")
                                for result in query_result:
                                    print(f"      - {result.get('m.content', 'No content')[:50]}...")
                            else:
                                print("    No memories found in database for this user")
                        except Exception as e:
                            print(f"    Database query failed: {e}")
                    
                except Exception as e:
                    print(f"  ❌ Error generating memories: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Final database check
            print(f"\n🗄️  Final Database State:")
            try:
                total_memories = memory.db_adapter.execute_query("MATCH (m:Memory) RETURN COUNT(m) as count")
                if total_memories and len(total_memories) > 0:
                    count = total_memories[0].get('count', 0)
                    print(f"  Total memories in database: {count}")
                    
                    if count > 0:
                        # Get sample memories
                        sample_memories = memory.db_adapter.execute_query(
                            "MATCH (m:Memory) RETURN m.content, m.user_id, m.created_at LIMIT 5"
                        )
                        print(f"  Sample memories:")
                        for mem in sample_memories:
                            content = mem.get('m.content', 'No content')
                            user_id = mem.get('m.user_id', 'No user')
                            print(f"    - [{user_id}] {content[:60]}...")
                else:
                    print("  Could not query total memory count")
            except Exception as e:
                print(f"  Database query failed: {e}")
            
            memory.close()
            
            print(f"\n🎯 Debug Summary:")
            print(f"  - Memory generation process completed")
            print(f"  - Check individual test cases above for details")
            
            return True
            
    except Exception as e:
        print(f"❌ Error in debug process: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = debug_memory_generation()
    if success:
        print("\n🎉 Debug process completed!")
    else:
        print("\n❌ Debug process failed!")
    sys.exit(0 if success else 1)
