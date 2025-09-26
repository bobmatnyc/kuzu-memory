#!/usr/bin/env python
"""Test KuzuMemory functionality."""

from pathlib import Path
from kuzu_memory import KuzuMemory

# Initialize
db_path = Path("kuzu-memories/kuzu_memory.db")
memory = KuzuMemory(db_path=db_path)

# Store a test memory using remember method
print("Storing test memory...")
memory_id = memory.remember(
    "KuzuMemory test: The system uses cognitive memory types including EPISODIC, SEMANTIC, and PROCEDURAL"
)
print(f"Stored memory with ID: {memory_id}")

# Try to recall
print("\nTrying to recall memories about 'cognitive memory types'...")
result = memory.attach_memories("cognitive memory types", max_memories=5)
print(f"Found {len(result.memories)} memories")
for mem in result.memories:
    print(f"  - Type: {mem.memory_type}, Content: {mem.content[:80]}...")

print("\nTest complete!")
