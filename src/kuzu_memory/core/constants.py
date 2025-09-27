"""
Configuration constants and default values for KuzuMemory.

Central location for all magic numbers and configuration defaults.
"""

from typing import Final

# Performance thresholds (in milliseconds)
ATTACH_MEMORIES_TARGET_MS: Final[int] = 10
GENERATE_MEMORIES_TARGET_MS: Final[int] = 20
SLOW_QUERY_THRESHOLD_MS: Final[int] = 1000  # 1 second
VERY_SLOW_QUERY_THRESHOLD_MS: Final[int] = 2000  # 2 seconds

# Cache configuration
DEFAULT_CACHE_SIZE: Final[int] = 256
DEFAULT_CACHE_TTL_SECONDS: Final[int] = 60
MEMORY_BY_ID_CACHE_SIZE: Final[int] = 512
MEMORY_BY_ID_CACHE_TTL: Final[int] = 120

# Query limits and batch sizes
DEFAULT_MEMORY_LIMIT: Final[int] = 10
MAX_MEMORY_LIMIT: Final[int] = 100
DEFAULT_BATCH_SIZE: Final[int] = 100
MAX_BATCH_SIZE: Final[int] = 1000
DEFAULT_DEDUPLICATION_DAYS: Final[int] = 30
DEFAULT_SEARCH_WORD_COUNT: Final[int] = 5

# Memory retention periods (in days)
SEMANTIC_RETENTION_DAYS: Final[int] = -1  # Never expires
PROCEDURAL_RETENTION_DAYS: Final[int] = -1  # Never expires
PREFERENCE_RETENTION_DAYS: Final[int] = -1  # Never expires
EPISODIC_RETENTION_DAYS: Final[int] = 30
WORKING_RETENTION_DAYS: Final[int] = 1
SENSORY_RETENTION_HOURS: Final[float] = 6

# File size limits
MAX_FILE_SIZE_LINES: Final[int] = 800
WARNING_FILE_SIZE_LINES: Final[int] = 600

# Query performance tracking
MAX_SLOW_QUERIES_TO_TRACK: Final[int] = 10
QUERY_STATS_HISTORY_SIZE: Final[int] = 100

# Default configuration values
DEFAULT_AGENT_ID: Final[str] = "default"
DEFAULT_SOURCE_TYPE: Final[str] = "conversation"
DEFAULT_MEMORY_TYPE: Final[str] = "EPISODIC"
DEFAULT_RECALL_STRATEGY: Final[str] = "auto"

# Memory importance and confidence defaults
DEFAULT_IMPORTANCE: Final[float] = 0.5
DEFAULT_CONFIDENCE: Final[float] = 1.0
MIN_IMPORTANCE: Final[float] = 0.0
MAX_IMPORTANCE: Final[float] = 1.0
MIN_CONFIDENCE: Final[float] = 0.0
MAX_CONFIDENCE: Final[float] = 1.0

# Entity extraction
DEFAULT_ENTITY_CONFIDENCE: Final[float] = 0.8
DEFAULT_ENTITY_TYPE: Final[str] = "extracted"
DEFAULT_EXTRACTION_METHOD: Final[str] = "pattern"

# Database connection
CONNECTION_POOL_SIZE: Final[int] = 5
CONNECTION_TIMEOUT_SECONDS: Final[int] = 30
QUERY_TIMEOUT_SECONDS: Final[int] = 10

# Temporal decay
DEFAULT_DECAY_FACTOR: Final[float] = 0.9
MIN_DECAY_FACTOR: Final[float] = 0.0
MAX_DECAY_FACTOR: Final[float] = 1.0

# Validation
MAX_CONTENT_LENGTH: Final[int] = 10000  # Characters
MAX_METADATA_SIZE: Final[int] = 5000  # Bytes
MAX_ID_LENGTH: Final[int] = 128

# Logging
LOG_PERFORMANCE_THRESHOLD_MS: Final[int] = 100
LOG_BATCH_OPERATIONS: Final[bool] = True
