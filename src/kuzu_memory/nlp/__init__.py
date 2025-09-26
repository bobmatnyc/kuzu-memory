"""
NLP components for KuzuMemory.

Provides natural language processing capabilities for automatic
memory classification, entity extraction, sentiment analysis, and intent detection.
"""

from .classifier import (
    MemoryClassifier,
    ClassificationResult,
    EntityExtractionResult,
    SentimentResult
)
from .patterns import (
    MEMORY_TYPE_PATTERNS,
    ENTITY_PATTERNS,
    INTENT_KEYWORDS,
    get_memory_type_indicators
)

__all__ = [
    "MemoryClassifier",
    "ClassificationResult",
    "EntityExtractionResult",
    "SentimentResult",
    "MEMORY_TYPE_PATTERNS",
    "ENTITY_PATTERNS",
    "INTENT_KEYWORDS",
    "get_memory_type_indicators"
]