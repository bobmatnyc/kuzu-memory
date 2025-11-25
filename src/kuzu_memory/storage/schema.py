"""
Database schema definition for KuzuMemory.

Defines the Kuzu graph database schema including node tables, relationship tables,
and indices for optimal performance. Includes version management for migrations.
"""

from __future__ import annotations

# Database schema version for migration support
SCHEMA_VERSION = "1.0"

# Core schema definition
SCHEMA_DDL = """
CREATE NODE TABLE IF NOT EXISTS SchemaVersion (
    version STRING PRIMARY KEY,
    created_at TIMESTAMP,
    description STRING
);

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
);

CREATE NODE TABLE IF NOT EXISTS Entity (
    id STRING PRIMARY KEY,
    name STRING,
    entity_type STRING,
    normalized_name STRING,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    mention_count INT32 DEFAULT 1,
    confidence FLOAT DEFAULT 1.0
);

CREATE NODE TABLE IF NOT EXISTS Session (
    id STRING PRIMARY KEY,
    user_id STRING,
    agent_id STRING DEFAULT 'default',
    created_at TIMESTAMP,
    last_activity TIMESTAMP,
    memory_count INT32 DEFAULT 0,
    metadata STRING DEFAULT '{}'
);

CREATE REL TABLE IF NOT EXISTS MENTIONS (
    FROM Memory TO Entity,
    confidence FLOAT DEFAULT 1.0,
    position_start INT32,
    position_end INT32,
    extraction_method STRING DEFAULT 'pattern'
);

CREATE REL TABLE IF NOT EXISTS RELATES_TO (
    FROM Memory TO Memory,
    relationship_type STRING,
    strength FLOAT DEFAULT 1.0,
    created_at TIMESTAMP
);

CREATE REL TABLE IF NOT EXISTS BELONGS_TO_SESSION (
    FROM Memory TO Session,
    created_at TIMESTAMP
);

CREATE REL TABLE IF NOT EXISTS CO_OCCURS_WITH (
    FROM Entity TO Entity,
    co_occurrence_count INT32 DEFAULT 1,
    last_co_occurrence TIMESTAMP
);
"""

# Performance indices (Kuzu doesn't support IF NOT EXISTS for indices)
INDICES_DDL = """
"""

# Initial data insertion
INITIAL_DATA_DDL = f"""
CREATE (sv:SchemaVersion {{version: '{SCHEMA_VERSION}', description: 'Initial KuzuMemory schema with memory, entity, and session tracking'}});
"""

# Full schema (combines all DDL)
FULL_SCHEMA_DDL = SCHEMA_DDL + "\n" + INDICES_DDL + "\n" + INITIAL_DATA_DDL

# Common queries for schema operations
SCHEMA_QUERIES = {
    "get_schema_version": """
        MATCH (sv:SchemaVersion)
        RETURN sv.version, sv.created_at, sv.description
        ORDER BY sv.created_at DESC
        LIMIT 1
    """,
    "check_table_exists": """
        CALL SHOW_TABLES()
        RETURN name WHERE name = $table_name
    """,
    "get_memory_count": """
        MATCH (m:Memory)
        RETURN COUNT(m) as count
    """,
    "get_entity_count": """
        MATCH (e:Entity)
        RETURN COUNT(e) as count
    """,
    "get_session_count": """
        MATCH (s:Session)
        RETURN COUNT(s) as count
    """,
    "get_database_stats": """
        MATCH (m:Memory)
        WITH COUNT(m) as memory_count
        MATCH (e:Entity)
        WITH memory_count, COUNT(e) as entity_count
        MATCH (s:Session)
        WITH memory_count, entity_count, COUNT(s) as session_count
        MATCH ()-[r]->()
        RETURN memory_count, entity_count, session_count, COUNT(r) as relationship_count
    """,
    "cleanup_expired_memories": """
        MATCH (m:Memory)
        WHERE m.valid_to IS NOT NULL AND m.valid_to < $current_time
        DELETE m
    """,
    "get_memory_types_distribution": """
        MATCH (m:Memory)
        WHERE m.valid_to IS NULL OR m.valid_to > $current_time
        RETURN m.memory_type, COUNT(m) as count
        ORDER BY count DESC
    """,
    "get_top_entities": """
        MATCH (e:Entity)
        RETURN e.name, e.entity_type, e.mention_count
        ORDER BY e.mention_count DESC
        LIMIT $limit
    """,
    "find_duplicate_content_hashes": """
        MATCH (m:Memory)
        WITH m.content_hash, COUNT(m) as count, COLLECT(m.id) as memory_ids
        WHERE count > 1
        RETURN m.content_hash, count, memory_ids
    """,
    "get_recent_memories": """
        MATCH (m:Memory)
        WHERE m.created_at > $since_time
        AND (m.valid_to IS NULL OR m.valid_to > $current_time)
        RETURN m
        ORDER BY m.created_at DESC
        LIMIT $limit
    """,
    "get_memories_by_importance": """
        MATCH (m:Memory)
        WHERE (m.valid_to IS NULL OR m.valid_to > $current_time)
        AND m.importance >= $min_importance
        RETURN m
        ORDER BY m.importance DESC, m.created_at DESC
        LIMIT $limit
    """,
}

# Migration queries for schema updates
MIGRATION_QUERIES = {
    "1.0_to_1.1": [
        # Example migration - add new fields or indices
        "ALTER TABLE Memory ADD COLUMN tags STRING DEFAULT '[]'",
        "CREATE INDEX IF NOT EXISTS idx_memory_tags ON Memory(tags)",
    ]
}


def get_schema_ddl() -> str:
    """Get the complete schema DDL."""
    return FULL_SCHEMA_DDL


def get_schema_version() -> str:
    """Get the current schema version."""
    return SCHEMA_VERSION


def get_query(query_name: str) -> str:
    """
    Get a predefined query by name.

    Args:
        query_name: Name of the query to retrieve

    Returns:
        Query string

    Raises:
        KeyError: If query name is not found
    """
    if query_name not in SCHEMA_QUERIES:
        available_queries = ", ".join(SCHEMA_QUERIES.keys())
        raise KeyError(f"Query '{query_name}' not found. Available queries: {available_queries}")

    return SCHEMA_QUERIES[query_name]


def get_migration_queries(from_version: str, to_version: str) -> list[str]:
    """
    Get migration queries between schema versions.

    Args:
        from_version: Source schema version
        to_version: Target schema version

    Returns:
        List of migration queries to execute

    Raises:
        ValueError: If migration path is not supported
    """
    migration_key = f"{from_version}_to_{to_version}"

    if migration_key not in MIGRATION_QUERIES:
        available_migrations = ", ".join(MIGRATION_QUERIES.keys())
        raise ValueError(
            f"Migration from {from_version} to {to_version} not supported. "
            f"Available migrations: {available_migrations}"
        )

    return MIGRATION_QUERIES[migration_key]


def validate_schema_compatibility(current_version: str, required_version: str) -> bool:
    """
    Check if current schema version is compatible with required version.

    Args:
        current_version: Current database schema version
        required_version: Required schema version

    Returns:
        True if compatible, False otherwise
    """
    # For now, only exact version matches are supported
    # In the future, this could support backward compatibility rules
    return current_version == required_version
