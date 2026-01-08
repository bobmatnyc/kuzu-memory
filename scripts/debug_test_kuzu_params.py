#!/usr/bin/env python
"""Test Kuzu parameter handling."""

from datetime import datetime, timedelta
from pathlib import Path

import kuzu

# Find the database
db_path = Path("kuzu-memories/memories.db")
if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

# Connect to database
db = kuzu.Database(str(db_path))
conn = kuzu.Connection(db)

# Test parameter formats
test_queries = [
    # Format 1: $param
    (
        """
        MATCH (m:Memory)
        WHERE m.created_at >= $week_ago
        RETURN count(m) as count
    """,
        {"week_ago": datetime.now() - timedelta(days=7)},
        "$ format",
    ),
    # Format 2: :param (Neo4j style)
    (
        """
        MATCH (m:Memory)
        WHERE m.created_at >= :week_ago
        RETURN count(m) as count
    """,
        {"week_ago": datetime.now() - timedelta(days=7)},
        ": format",
    ),
]

for query, params, desc in test_queries:
    print(f"\nTesting {desc}...")
    try:
        result = conn.execute(query, params)
        if result.has_next():
            row = result.get_next()
            print(f"  Success! Count: {row[0]}")
        else:
            print("  No results")
    except Exception as e:
        print(f"  Error: {e}")

# Test without parameters
print("\nTesting hardcoded values...")
try:
    week_ago = datetime.now() - timedelta(days=7)
    query = f"""
        MATCH (m:Memory)
        WHERE m.created_at >= '{week_ago.isoformat()}'
        RETURN count(m) as count
    """
    result = conn.execute(query)
    if result.has_next():
        row = result.get_next()
        print(f"  Success! Count: {row[0]}")
except Exception as e:
    print(f"  Error: {e}")

conn.close()
