"""
Example: Using KuzuMemoryClient Python API

Demonstrates basic and advanced usage of the async Python client API.
"""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from kuzu_memory.client import KuzuMemoryClient


async def main():
    """Run comprehensive example in single context."""
    print("KuzuMemory Python Client API Examples\n")
    print("=" * 50)
    print()

    # Use single temporary directory for all examples
    with TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Single client context for all operations
        async with KuzuMemoryClient(project_root=project_root, enable_git_sync=False) as client:
            # === Basic Example ===
            print("=== Basic Example ===\n")

            # 1. Store some memories
            print("1. Storing memories...")
            await client.learn("User prefers Python for backend development")
            await client.learn("User likes FastAPI framework for REST APIs")
            await client.learn("User uses PostgreSQL for databases")
            print("   ✓ Stored 3 memories\n")

            # 2. Query memories
            print("2. Querying memories...")
            memories = await client.recall("What language does user prefer?", max_memories=2)
            print(f"   Found {len(memories)} relevant memories:")
            for memory in memories:
                print(f"   - [{memory.importance:.2f}] {memory.content}")
            print()

            # 3. Enhance a prompt with context
            print("3. Enhancing prompt...")
            context = await client.enhance("Write a REST API server", max_memories=3)
            print(f"   Retrieved {len(context.memories)} memories")
            print(f"   Confidence: {context.confidence:.2f}")
            print(f"   Recall time: {context.recall_time_ms:.2f}ms")
            print("\n   Enhanced prompt preview:")
            print(f"   {context.enhanced_prompt[:200]}...\n")

            # 4. Get statistics
            print("4. System statistics:")
            stats = client.get_stats()
            print(f"   Total memories: {stats['memory_count']}")
            print(f"   Database size: {stats['database_size_bytes'] / 1024:.2f} KB")
            print()

            # === Advanced Example ===
            print("=== Advanced Example ===\n")

            # 1. Concurrent store operations
            print("1. Storing multiple memories concurrently...")
            stored_ids = await asyncio.gather(
                client.learn("Advanced memory 1"),
                client.learn("Advanced memory 2"),
                client.learn("Advanced memory 3"),
            )
            print(f"   ✓ Stored {len(stored_ids)} memories\n")

            # 2. Get recent memories
            print("2. Getting recent memories...")
            recent = await client.get_recent_memories(limit=3)
            print(f"   Found {len(recent)} recent memories:")
            for memory in recent[:3]:  # Show first 3
                print(f"   - {memory.content}")
            print()

            # === RAG Workflow Example ===
            print("=== RAG Workflow Example ===\n")

            # Build up context
            print("1. Building project context...")
            await client.learn("Project uses microservices architecture")
            await client.learn("API authentication uses JWT tokens")
            await client.learn("Database is sharded by user_id")
            await client.learn("Caching layer uses Redis")
            print("   ✓ Stored project context\n")

            # Simulate user question
            user_question = "How should I implement user authentication?"
            print(f"2. User question: {user_question}\n")

            # Enhance with relevant context
            print("3. Retrieving relevant context...")
            rag_context = await client.enhance(user_question, max_memories=5)

            print(f"   Retrieved {len(rag_context.memories)} relevant memories:")
            for memory in rag_context.memories:
                print(f"   - {memory.content}")

            print("\n4. Enhanced prompt for LLM:")
            lines = rag_context.enhanced_prompt.split("\n")
            for line in lines[:10]:  # Show first 10 lines
                print(f"   {line}")
            print()

            # === Final Statistics ===
            print("=== Final Statistics ===\n")
            final_stats = client.get_stats()
            print(f"Total memories stored: {final_stats['memory_count']}")
            print(f"Database size: {final_stats['database_size_bytes'] / 1024:.2f} KB")
            print()

            print("=" * 50)
            print("\n✅ All examples completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
