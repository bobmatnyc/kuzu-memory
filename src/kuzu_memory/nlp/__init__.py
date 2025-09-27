"""
NLP components for KuzuMemory.

Provides natural language processing capabilities for automatic
memory classification, entity extraction, sentiment analysis, and intent detection.
"""

from .classifier import (
    ClassificationResult,
    EntityExtractionResult,
    MemoryClassifier,
    SentimentResult,
)
from .patterns import (
    ENTITY_PATTERNS,
    INTENT_KEYWORDS,
    MEMORY_TYPE_PATTERNS,
    get_memory_type_indicators,
)

__all__ = [
    "ENTITY_PATTERNS",
    "INTENT_KEYWORDS",
    "MEMORY_TYPE_PATTERNS",
    "ClassificationResult",
    "EntityExtractionResult",
    "MemoryClassifier",
    "SentimentResult",
    "get_memory_type_indicators",
]
