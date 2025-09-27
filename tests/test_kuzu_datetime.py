#!/usr/bin/env python
"""Test Kuzu datetime parameter handling."""

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

# Test datetime parameter formats
now = datetime.now()
week_ago = now - timedelta(days=7)

test_params = [
    # Raw datetime object
    ({"now": now, "week_ago": week_ago}, "datetime objects"),
    # ISO format strings
    ({"now": now.isoformat(), "week_ago": week_ago.isoformat()}, "ISO strings"),
    # Timestamp integers
    (
        {
            "now": int(now.timestamp() * 1000),
            "week_ago": int(week_ago.timestamp() * 1000),
        },
        "timestamps",
    ),
]

query = """
    MATCH (m:Memory)
    WHERE m.created_at >= $week_ago AND (m.valid_to IS NULL OR m.valid_to > $now)
    RETURN count(m) as recent_count
"""

for params, desc in test_params:
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

conn.close()
