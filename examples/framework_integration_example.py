"""
Example: Integrating KuzuMemory into an AI Framework

This example demonstrates how to integrate KuzuMemory as a backend service
in your AI framework with subservient mode (framework manages hooks).

Run:
    python examples/framework_integration_example.py
"""

import asyncio
import tempfile
from pathlib import Path

from kuzu_memory import (
    KuzuMemoryClient,
    create_subservient_config,
    enable_subservient_mode,
    is_subservient_mode,
)


class AIFramework:
    """Example AI framework with KuzuMemory integration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.memory = None
        self.session_id = "example-session"

    @classmethod
    async def setup(cls, project_root: Path, framework_name: str = "ai-framework") -> "AIFramework":
        """
        Setup framework with subservient mode.

        This is typically called during framework installation/initialization.
        """
        print(f"🔧 Setting up {framework_name}...\n")

        # Enable subservient mode (prevents kuzu-memory from managing hooks)
        result = enable_subservient_mode(project_root=project_root, managed_by=framework_name)

        print(f"✅ Subservient mode enabled")
        print(f"   Config file: {result['config_path']}")
        print(f"   Managed by: {framework_name}\n")

        # Verify subservient mode is active
        if not is_subservient_mode(project_root):
            raise RuntimeError("Failed to enable subservient mode")

        # Create and initialize framework
        framework = cls(project_root)
        await framework.start()
        return framework

    async def start(self):
        """Initialize memory backend."""
        print("🚀 Starting memory backend...")

        # Initialize KuzuMemory client
        self.memory = KuzuMemoryClient(project_root=self.project_root)
        await self.memory.__aenter__()

        # Get initial stats
        stats = self.memory.get_stats()
        print(f"✅ Memory backend initialized")
        print(f"   Database: {self.memory.db_path}")
        print(f"   Existing memories: {stats['memory_count']}\n")

    async def stop(self):
        """Cleanup resources."""
        if self.memory:
            await self.memory.__aexit__(None, None, None)
            print("✅ Memory backend cleaned up")

    async def chat(self, user_message: str) -> str:
        """
        Process user message with memory context.

        This demonstrates the RAG (Retrieval-Augmented Generation) pattern:
        1. Retrieve relevant memories
        2. Enhance prompt with context
        3. Generate response (simulated)
        4. Store interaction for future context
        """
        print(f"\n👤 User: {user_message}")

        # Enhance prompt with relevant memories
        context = await self.memory.enhance(prompt=user_message, max_memories=5)

        print(f"   📚 Enhanced with {len(context.memories)} memories")
        if context.memories:
            print("   Relevant context:")
            for memory in context.memories[:3]:  # Show first 3
                preview = memory.content[:60] + "..." if len(memory.content) > 60 else memory.content
                print(f"     - {preview}")

        # Simulate LLM response (replace with your actual LLM call)
        response = self._generate_response(user_message, context)

        # Store interaction as memory for future context
        await self.memory.learn(
            content=f"User asked: {user_message}\nAssistant responded: {response}",
            source="framework-chat",
            session_id=self.session_id,
        )

        print(f"🤖 Assistant: {response}")
        return response

    def _generate_response(self, user_message: str, context) -> str:
        """
        Simulate LLM response generation.

        In a real implementation, this would:
        1. Send context.enhanced_prompt to your LLM
        2. Return the LLM's response
        """
        if context.memories:
            return f"Based on our conversation history, {user_message.lower()}"
        else:
            return f"I'll help with {user_message.lower()}"

    async def demonstrate_memory_operations(self):
        """Demonstrate various memory operations."""
        print("\n" + "=" * 60)
        print("🧠 Demonstrating Memory Operations")
        print("=" * 60)

        # 1. Store some initial memories
        print("\n1️⃣  Storing domain knowledge...")
        await self.memory.learn("The user prefers Python for backend development", source="preference")
        await self.memory.learn("The user is working on a FastAPI project", source="context")
        await self.memory.learn("The user follows TDD (Test-Driven Development)", source="practice")
        print("✅ Stored 3 initial memories")

        # 2. Query memories
        print("\n2️⃣  Querying memories...")
        memories = await self.memory.recall("What programming language does the user prefer?", max_memories=3)
        print(f"✅ Found {len(memories)} relevant memories:")
        for memory in memories:
            print(f"   - {memory.content}")

        # 3. Get statistics
        print("\n3️⃣  Memory statistics:")
        stats = self.memory.get_stats()
        print(f"   Total memories: {stats['memory_count']}")
        print(f"   Database size: {stats['database_size_bytes'] / 1024:.2f} KB")

        # 4. Recent memories
        print("\n4️⃣  Recent memories:")
        recent = await self.memory.get_recent_memories(limit=3)
        print(f"   Last {len(recent)} memories:")
        for memory in recent:
            preview = memory.content[:60] + "..." if len(memory.content) > 60 else memory.content
            print(f"   - {preview}")


async def main():
    """
    Main demonstration of framework integration.

    This shows the complete lifecycle:
    1. Setup with subservient mode
    2. Memory operations
    3. Chat with context
    4. Cleanup
    """
    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        print("=" * 60)
        print("KuzuMemory Framework Integration Example")
        print("=" * 60 + "\n")

        # Setup framework
        framework = await AIFramework.setup(project_root=project_root, framework_name="example-framework")

        try:
            # Demonstrate memory operations
            await framework.demonstrate_memory_operations()

            # Interactive chat with memory context
            print("\n" + "=" * 60)
            print("💬 Chat with Memory Context")
            print("=" * 60)

            await framework.chat("What should I use for my web API?")
            await framework.chat("What did I just ask about?")
            await framework.chat("What development practices do I follow?")

        finally:
            # Cleanup
            print("\n" + "=" * 60)
            print("🧹 Cleanup")
            print("=" * 60 + "\n")
            await framework.stop()

        print("\n" + "=" * 60)
        print("✅ Example completed successfully!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
