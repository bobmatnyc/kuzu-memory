#!/usr/bin/env python3
"""
Test our exact schema creation step by step.
"""

import tempfile
from pathlib import Path
import kuzu

def test_schema_creation():
    """Test our schema creation step by step."""
    import pytest
    pytest.skip("Standalone test file - schema tested in integration tests")

    print("🧪 Testing Schema Creation")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        try:
            # Create database and connection
            database = kuzu.Database(str(db_path))
            connection = kuzu.Connection(database)
            
            print("✅ Database and connection created")
            
            # Test each table creation individually
            tables = [
                ("SchemaVersion", """
                    CREATE NODE TABLE IF NOT EXISTS SchemaVersion (
                        version STRING PRIMARY KEY,
                        created_at TIMESTAMP,
                        description STRING
                    )
                """),
                ("Memory", """
                    CREATE NODE TABLE IF NOT EXISTS Memory (
                        id STRING PRIMARY KEY,
                        content STRING,
                        content_hash STRING,
                        created_at TIMESTAMP,
                        valid_from TIMESTAMP,
                        valid_to TIMESTAMP,
                        accessed_at TIMESTAMP,
                        access_count INT32 DEFAULT 0,
                        memory_type STRING,
                        importance FLOAT DEFAULT 0.5,
                        confidence FLOAT DEFAULT 1.0,
                        source_type STRING DEFAULT 'conversation',
                        agent_id STRING DEFAULT 'default',
                        user_id STRING,
                        session_id STRING,
                        metadata STRING DEFAULT '{}'
                    )
                """),
                ("Entity", """
                    CREATE NODE TABLE IF NOT EXISTS Entity (
                        id STRING PRIMARY KEY,
                        name STRING,
                        entity_type STRING,
                        normalized_name STRING,
                        first_seen TIMESTAMP,
                        last_seen TIMESTAMP,
                        mention_count INT32 DEFAULT 1,
                        confidence FLOAT DEFAULT 1.0
                    )
                """),
                ("Session", """
                    CREATE NODE TABLE IF NOT EXISTS Session (
                        id STRING PRIMARY KEY,
                        user_id STRING,
                        agent_id STRING DEFAULT 'default',
                        created_at TIMESTAMP,
                        last_activity TIMESTAMP,
                        memory_count INT32 DEFAULT 0,
                        metadata STRING DEFAULT '{}'
                    )
                """)
            ]
            
            # Create node tables
            for table_name, ddl in tables:
                print(f"\n📝 Creating {table_name} table...")
                try:
                    result = connection.execute(ddl.strip())
                    print(f"✅ {table_name} table created")
                except Exception as e:
                    print(f"❌ {table_name} table failed: {e}")
                    return False
            
            # Test relationship tables
            relationships = [
                ("MENTIONS", """
                    CREATE REL TABLE IF NOT EXISTS MENTIONS (
                        FROM Memory TO Entity,
                        confidence FLOAT DEFAULT 1.0,
                        position_start INT32,
                        position_end INT32,
                        extraction_method STRING DEFAULT 'pattern'
                    )
                """),
                ("RELATES_TO", """
                    CREATE REL TABLE IF NOT EXISTS RELATES_TO (
                        FROM Memory TO Memory,
                        relationship_type STRING,
                        strength FLOAT DEFAULT 1.0,
                        created_at TIMESTAMP
                    )
                """),
                ("BELONGS_TO_SESSION", """
                    CREATE REL TABLE IF NOT EXISTS BELONGS_TO_SESSION (
                        FROM Memory TO Session,
                        created_at TIMESTAMP
                    )
                """),
                ("CO_OCCURS_WITH", """
                    CREATE REL TABLE IF NOT EXISTS CO_OCCURS_WITH (
                        FROM Entity TO Entity,
                        co_occurrence_count INT32 DEFAULT 1,
                        last_co_occurrence TIMESTAMP
                    )
                """)
            ]
            
            # Create relationship tables
            for rel_name, ddl in relationships:
                print(f"\n📝 Creating {rel_name} relationship...")
                try:
                    result = connection.execute(ddl.strip())
                    print(f"✅ {rel_name} relationship created")
                except Exception as e:
                    print(f"❌ {rel_name} relationship failed: {e}")
                    print(f"   DDL: {ddl.strip()}")
                    return False
            
            # Test some indices
            indices = [
                ("idx_memory_content_hash", "CREATE INDEX IF NOT EXISTS idx_memory_content_hash ON Memory(content_hash)"),
                ("idx_memory_type", "CREATE INDEX IF NOT EXISTS idx_memory_type ON Memory(memory_type)"),
                ("idx_entity_name", "CREATE INDEX IF NOT EXISTS idx_entity_name ON Entity(name)")
            ]
            
            for idx_name, ddl in indices:
                print(f"\n📝 Creating {idx_name} index...")
                try:
                    result = connection.execute(ddl)
                    print(f"✅ {idx_name} index created")
                except Exception as e:
                    print(f"❌ {idx_name} index failed: {e}")
                    # Indices failing is not critical
            
            print(f"\n🎉 Schema creation completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_schema_creation()
    if success:
        print("\n🎉 Schema creation works!")
    else:
        print("\n❌ Schema creation failed!")
