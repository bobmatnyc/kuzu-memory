"""Test that classifier module has fast imports (lazy loading)."""

import time


def test_classifier_import_is_fast() -> None:
    """Test that importing MemoryClassifier is fast (<50ms)."""
    start = time.perf_counter()

    # This should be fast because dependencies are lazy loaded
    from kuzu_memory.nlp.classifier import MemoryClassifier

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should be significantly faster than 800ms (original timing)
    # Target: <50ms (same as recall operation target)
    assert elapsed_ms < 50, f"Import took {elapsed_ms:.1f}ms, expected <50ms"

    # Creating instance should also be fast (no heavy init)
    start = time.perf_counter()
    classifier = MemoryClassifier()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 50, f"Instantiation took {elapsed_ms:.1f}ms, expected <50ms"

    # Verify classifier is created but not initialized
    assert classifier.initialized is False
    assert classifier.classifier is None


def test_classifier_lazy_loads_on_first_use() -> None:
    """Test that dependencies load lazily on first classify() call."""
    from kuzu_memory.nlp.classifier import MemoryClassifier

    classifier = MemoryClassifier()

    # Should not be initialized yet
    assert classifier.initialized is False

    # First classify() call triggers lazy load
    result = classifier.classify("Python is a programming language")

    # Now it should be initialized
    assert classifier.initialized is True

    # Result should still be valid
    assert result.memory_type is not None
    assert result.confidence > 0


def test_module_level_import_is_fast() -> None:
    """Test that module-level import (from memory_enhancer) is fast."""
    start = time.perf_counter()

    # This is how memory_enhancer imports it
    from kuzu_memory.nlp.classifier import MemoryClassifier  # noqa: F401

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should be very fast - just loading class definition
    assert elapsed_ms < 50, f"Module import took {elapsed_ms:.1f}ms, expected <50ms"
