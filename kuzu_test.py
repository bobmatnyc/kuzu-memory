#!/usr/bin/env python3
"""
Simple test to check Kuzu database functionality.
"""

import tempfile
from pathlib import Path
import kuzu

def test_kuzu_basic():
    """Test basic Kuzu functionality."""
    import pytest
    pytest.skip("Standalone test file - functionality tested in integration tests")

    print("🧪 Testing Basic Kuzu Functionality")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        try:
            # Create database and connection
            database = kuzu.Database(str(db_path))
            connection = kuzu.Connection(database)
            
            print("✅ Database and connection created")
            
            # Test 1: Create a simple node table
            print("\n📝 Creating node table...")
            result = connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS TestNode (
                    id STRING PRIMARY KEY,
                    name STRING,
                    value INT32 DEFAULT 0
                )
            """)
            print("✅ Node table created")
            
            # Test 2: Insert data
            print("\n📝 Inserting data...")
            result = connection.execute("""
                CREATE (n:TestNode {id: 'test1', name: 'Test Node', value: 42})
            """)
            print("✅ Data inserted")
            
            # Test 3: Query data
            print("\n🔍 Querying data...")
            result = connection.execute("MATCH (n:TestNode) RETURN n.id, n.name, n.value")
            
            rows = []
            while result.has_next():
                row = result.get_next()
                rows.append({
                    'id': row[0],
                    'name': row[1], 
                    'value': row[2]
                })
            
            print(f"✅ Found {len(rows)} rows")
            for row in rows:
                print(f"   {row}")
            
            # Test 4: Create another node table
            print("\n📝 Creating second node table...")
            result = connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS TestNode2 (
                    id STRING PRIMARY KEY,
                    description STRING
                )
            """)
            print("✅ Second node table created")
            
            # Test 5: Try relationship table
            print("\n📝 Creating relationship table...")
            try:
                result = connection.execute("""
                    CREATE REL TABLE IF NOT EXISTS TEST_REL (
                        FROM TestNode TO TestNode2,
                        strength FLOAT DEFAULT 1.0
                    )
                """)
                print("✅ Relationship table created")
            except Exception as e:
                print(f"❌ Relationship table failed: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_kuzu_basic()
    if success:
        print("\n🎉 Kuzu basic functionality works!")
    else:
        print("\n❌ Kuzu basic functionality failed!")
