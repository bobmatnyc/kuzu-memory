"""
NLP components for KuzuMemory.

Provides natural language processing capabilities for automatic
memory classification, entity extraction, sentiment analysis, intent detection,
and memory consolidation.
"""

from .classifier import (
    ClassificationResult,
    EntityExtractionResult,
    MemoryClassifier,
    SentimentResult,
)
from .consolidation import ConsolidationEngine, ConsolidationResult, MemoryCluster
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
    "ConsolidationEngine",
    "ConsolidationResult",
    "EntityExtractionResult",
    "MemoryClassifier",
    "MemoryCluster",
    "SentimentResult",
    "get_memory_type_indicators",
]
