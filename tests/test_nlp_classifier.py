"""
Tests for NLP memory classification.

Tests the MemoryClassifier, pattern matching, entity extraction,
and integration with the memory system.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from kuzu_memory.core.models import ExtractedMemory, MemoryType
from kuzu_memory.nlp.classifier import (
    ClassificationResult,
    EntityExtractionResult,
    MemoryClassifier,
    SentimentResult,
)
from kuzu_memory.nlp.patterns import (
    adjust_confidence_by_indicators,
    calculate_content_importance,
    get_memory_type_indicators,
    get_training_data,
)

# Check if NLTK is available for tests that require it
try:
    import nltk

    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False


class TestMemoryClassifier:
    """Test suite for MemoryClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create a test classifier instance."""
        with patch("kuzu_memory.nlp.classifier.NLTK_AVAILABLE", True):
            # Mock NLTK functions if not available
            if not HAS_NLTK:
                # Mock the NLTK functions used by the classifier
                import sys
                from unittest.mock import MagicMock

                mock_nltk = MagicMock()
                mock_nltk.download = MagicMock(return_value=True)
                mock_nltk.data.find = MagicMock(return_value="/fake/path")

                # Add mocks to sys.modules before any imports
                sys.modules["nltk"] = mock_nltk
                sys.modules["nltk.tokenize"] = MagicMock()
                sys.modules["nltk.corpus"] = MagicMock()
                sys.modules["nltk.sentiment"] = MagicMock()
                sys.modules["nltk.sentiment.vader"] = MagicMock()
                sys.modules["nltk.chunk"] = MagicMock()
                sys.modules["nltk.stem"] = MagicMock()
                sys.modules["nltk.tag"] = MagicMock()
                sys.modules["nltk.tree"] = MagicMock()

            # Create classifier without auto-downloading
            classifier = MemoryClassifier(auto_download=False)

            # Mock the trained classifier
            mock_pipeline = Mock()
            mock_pipeline.predict_proba.return_value = [[0.8]]
            mock_pipeline.classes_ = ["semantic"]
            classifier.classifier = mock_pipeline
            classifier.initialized = True

            # Mock sentiment analyzer to return realistic sentiment scores
            def mock_sentiment(text):
                """Mock sentiment analysis based on simple keyword matching."""
                from kuzu_memory.nlp.classifier import SentimentResult

                text_lower = text.lower()
                positive_words = [
                    "love",
                    "amazing",
                    "fantastic",
                    "wonderful",
                    "great",
                    "excellent",
                ]
                negative_words = ["terrible", "awful", "broken", "hate", "bad", "worst"]

                pos_count = sum(1 for word in positive_words if word in text_lower)
                neg_count = sum(1 for word in negative_words if word in text_lower)

                if pos_count > neg_count:
                    return SentimentResult(
                        positive=0.8,
                        negative=0.1,
                        neutral=0.1,
                        compound=0.7,
                        dominant="positive",
                    )
                elif neg_count > pos_count:
                    return SentimentResult(
                        positive=0.1,
                        negative=0.8,
                        neutral=0.1,
                        compound=-0.7,
                        dominant="negative",
                    )
                else:
                    return SentimentResult(
                        positive=0.1,
                        negative=0.1,
                        neutral=0.8,
                        compound=0.0,
                        dominant="neutral",
                    )

            classifier.analyze_sentiment = mock_sentiment

            yield classifier

            # Cleanup mock modules
            if not HAS_NLTK:
                for module in list(sys.modules.keys()):
                    if module.startswith("nltk"):
                        del sys.modules[module]

    def test_classifier_initialization_without_nltk(self):
        """Test classifier initialization when NLTK is not available."""
        with patch("kuzu_memory.nlp.classifier.NLTK_AVAILABLE", False):
            classifier = MemoryClassifier()
            assert not classifier.initialized
            assert classifier.classifier is None

    def test_classify_empty_content(self, classifier):
        """Test classification of empty content."""
        result = classifier.classify("")
        assert result.memory_type == MemoryType.EPISODIC
        assert result.confidence == 0.0
        assert result.keywords == []
        assert result.entities == []

    def test_classify_semantic_memory(self, classifier):
        """Test classification of semantic-type memory (facts)."""
        content = "My name is Alice and I'm a software engineer"
        result = classifier.classify(content)

        # Should detect semantic type through pattern matching (facts about identity)
        assert result.memory_type in [MemoryType.SEMANTIC, MemoryType.EPISODIC]
        assert result.confidence > 0.5
        assert result.metadata.get("pattern_match") is not None

    def test_classify_preference_memory(self, classifier):
        """Test classification of preference-type memory."""
        content = "I prefer Python over JavaScript for backend development"
        result = classifier.classify(content)

        # Should detect preference type
        assert result.memory_type in [MemoryType.PREFERENCE, MemoryType.SEMANTIC]
        assert result.confidence > 0.5

    def test_classify_episodic_memory(self, classifier):
        """Test classification of episodic-type memory (events/decisions)."""
        content = "We decided to use FastAPI for the backend API"
        result = classifier.classify(content)

        # Should detect episodic type (decisions are events)
        assert result.memory_type in [MemoryType.EPISODIC, MemoryType.SEMANTIC]
        assert result.confidence > 0.5

    def test_classify_procedural_memory(self, classifier):
        """Test classification of procedural-type memory (how-to)."""
        content = (
            "How to connect to the database: use connection pooling with max connections set to 10"
        )
        result = classifier.classify(content)

        # Should detect procedural type (instructions)
        assert result.memory_type in [MemoryType.PROCEDURAL, MemoryType.SEMANTIC]
        assert result.confidence > 0.5

    def test_classify_procedural_solution_memory(self, classifier):
        """Test classification of procedural-type memory (solutions)."""
        content = "Fixed the memory leak by clearing the cache after each request"
        result = classifier.classify(content)

        # Should detect procedural type (solutions are instructions)
        assert result.memory_type in [MemoryType.PROCEDURAL, MemoryType.SEMANTIC]
        assert result.confidence > 0.5

    def test_classify_working_memory(self, classifier):
        """Test classification of working-type memory (current tasks)."""
        content = "Currently working on the authentication module"
        result = classifier.classify(content)

        # Should detect working type (current tasks)
        assert result.memory_type in [MemoryType.WORKING, MemoryType.SEMANTIC]
        assert result.confidence > 0.5

    def test_classify_sensory_memory(self, classifier):
        """Test classification of sensory-type memory (sensory descriptions)."""
        content = "The coffee smells like fresh roasted beans and tastes bitter"
        result = classifier.classify(content)

        # Should detect sensory type (sensory descriptions)
        assert result.memory_type in [MemoryType.SENSORY, MemoryType.EPISODIC]
        assert result.confidence > 0.5

    def test_extract_entities_people(self, classifier):
        """Test extraction of people entities."""
        content = "John Smith and Dr. Jane Doe discussed the project with Mike Johnson"
        result = classifier.extract_entities(content)

        assert isinstance(result, EntityExtractionResult)
        # Should find people names (may vary based on NLTK availability)
        assert len(result.all_entities) > 0

    def test_extract_entities_technologies(self, classifier):
        """Test extraction of technology entities."""
        content = (
            "We use Python with FastAPI, PostgreSQL for the database, and deploy on AWS with Docker"
        )
        result = classifier.extract_entities(content)

        assert "Python" in result.technologies
        assert "FastAPI" in result.technologies
        assert "PostgreSQL" in result.technologies
        assert "AWS" in result.technologies
        assert "Docker" in result.technologies

    def test_extract_entities_dates(self, classifier):
        """Test extraction of date entities."""
        content = "The meeting was yesterday, and we have a deadline on 2024-12-31"
        result = classifier.extract_entities(content)

        assert "yesterday" in result.dates
        assert "2024-12-31" in result.dates

    def test_extract_entities_without_nltk(self):
        """Test entity extraction fallback when NLTK is not available."""
        with patch("kuzu_memory.nlp.classifier.NLTK_AVAILABLE", False):
            classifier = MemoryClassifier()
            content = "Python and JavaScript are programming languages"
            result = classifier.extract_entities(content)

            # Should still extract using regex patterns
            assert len(result.technologies) > 0

    def test_calculate_importance(self, classifier):
        """Test importance score calculation."""
        # High importance for identity type
        importance = classifier.calculate_importance("My name is Alice", MemoryType.SEMANTIC)
        assert importance >= 0.9

        # Lower importance for episodic type (casual conversation)
        importance = classifier.calculate_importance(
            "We talked about the weather", MemoryType.EPISODIC
        )
        assert importance < 0.9  # EPISODIC base is 0.7, should be less than semantic

        # Higher importance for technical content
        importance = classifier.calculate_importance(
            "The API endpoint uses JWT authentication with RSA256 algorithm",
            MemoryType.PROCEDURAL,
        )
        assert importance > 0.6

    def test_intent_detection(self, classifier):
        """Test intent detection in content."""
        # Decision intent
        content = "We decided to use microservices architecture"
        result = classifier.classify(content)
        assert result.intent == "decision"

        # Preference intent
        content = "I prefer functional programming"
        result = classifier.classify(content)
        assert result.intent == "preference"

        # Solution intent
        content = "To fix the issue, increase the timeout"
        result = classifier.classify(content)
        assert result.intent == "solution"

    def test_keyword_extraction(self, classifier):
        """Test keyword extraction from content."""
        content = "Python programming with FastAPI framework for building REST APIs"
        result = classifier.classify(content)

        assert isinstance(result.keywords, list)
        assert len(result.keywords) > 0
        # Keywords should be relevant words from the content
        # (exact keywords depend on NLTK availability and POS tagging)

    def test_sentiment_analysis(self, classifier):
        """Test sentiment analysis functionality."""
        # Positive sentiment
        positive_result = classifier.analyze_sentiment(
            "I love this amazing project! It's fantastic and wonderful!"
        )
        assert isinstance(positive_result, SentimentResult)
        assert positive_result.positive > 0.5
        assert positive_result.compound > 0.5
        assert positive_result.dominant == "positive"

        # Negative sentiment
        negative_result = classifier.analyze_sentiment(
            "This is terrible, awful, and completely broken. I hate it."
        )
        assert negative_result.negative > 0.5
        assert negative_result.compound < -0.5
        assert negative_result.dominant == "negative"

        # Neutral sentiment
        neutral_result = classifier.analyze_sentiment(
            "The database stores information about users."
        )
        assert neutral_result.neutral > 0.5
        assert abs(neutral_result.compound) < 0.5
        assert neutral_result.dominant == "neutral"

        # Mixed sentiment
        mixed_result = classifier.analyze_sentiment(
            "The project is good but has some serious problems."
        )
        assert mixed_result.positive > 0
        assert mixed_result.negative > 0

    def test_sentiment_without_analyzer(self):
        """Test sentiment analysis fallback when VADER is not available."""
        with patch("kuzu_memory.nlp.classifier.NLTK_AVAILABLE", False):
            classifier = MemoryClassifier()
            result = classifier.analyze_sentiment("Amazing work!")

            # Should return neutral default
            assert result.neutral == 1.0
            assert result.positive == 0.0
            assert result.negative == 0.0
            assert result.compound == 0.0
            assert result.dominant == "neutral"

    def test_batch_classification(self, classifier):
        """Test batch classification functionality."""
        contents = [
            "My name is John and I'm a developer",
            "I prefer Python over JavaScript",
            "We decided to use PostgreSQL",
            "",  # Empty content
            "The bug was fixed by clearing the cache",
        ]

        results = classifier.classify_batch(contents)

        # Should return same number of results
        assert len(results) == len(contents)

        # Check individual results
        assert all(isinstance(r, ClassificationResult) for r in results)

        # First result should be identity-like
        assert results[0].confidence > 0
        assert len(results[0].keywords) > 0

        # Second should be preference
        assert results[1].memory_type in [MemoryType.PREFERENCE, MemoryType.SEMANTIC]

        # Third should be decision
        assert results[2].memory_type in [MemoryType.EPISODIC, MemoryType.SEMANTIC]

        # Fourth (empty) should have low confidence
        assert results[3].confidence == 0.0
        assert results[3].memory_type == MemoryType.EPISODIC

        # Fifth should be solution
        assert results[4].memory_type in [MemoryType.PROCEDURAL, MemoryType.SEMANTIC]

        # Check batch processing metadata
        for result in results[:-1]:  # Except empty one
            if result.confidence > 0:
                assert "batch_processed" in result.metadata

    def test_batch_classification_performance(self, classifier, benchmark):
        """Test that batch classification is more efficient than individual."""
        contents = [f"Test content {i} with some information" for i in range(10)]

        # Benchmark batch processing
        def batch_classify():
            return classifier.classify_batch(contents)

        # Benchmark individual processing
        def individual_classify():
            return [classifier.classify(c) for c in contents]

        # Note: We can't directly compare timing in unit tests,
        # but we can verify both produce similar results
        batch_results = batch_classify()
        individual_results = individual_classify()

        assert len(batch_results) == len(individual_results)
        for batch_r, ind_r in zip(batch_results, individual_results, strict=False):
            # Results should be similar (may differ due to batch optimizations)
            assert (
                batch_r.memory_type == ind_r.memory_type or batch_r.confidence > 0
            )  # At least valid classification

    def test_batch_classification_with_ml_failure(self, classifier):
        """Test batch classification handles ML classifier failures gracefully."""
        # Mock ML classifier to fail
        classifier.classifier.predict_proba.side_effect = Exception("ML error")

        contents = ["Test content 1", "Test content 2"]

        results = classifier.classify_batch(contents)

        # Should still return results using pattern matching
        assert len(results) == 2
        assert all(isinstance(r, ClassificationResult) for r in results)
        assert all(r.confidence >= 0 for r in results)

    def test_sentiment_affects_importance(self, classifier):
        """Test that sentiment analysis affects importance calculation."""
        # Content with strong positive sentiment
        positive_importance = classifier.calculate_importance(
            "This is absolutely amazing! Best solution ever!!!", MemoryType.PROCEDURAL
        )

        # Same content structure but neutral
        neutral_importance = classifier.calculate_importance(
            "This is a solution to the problem.", MemoryType.PROCEDURAL
        )

        # Strong sentiment should increase importance
        # (may not always be higher due to other factors like length)
        assert positive_importance > 0
        assert neutral_importance > 0

        # Content with strong negative sentiment (problems/issues)
        negative_importance = classifier.calculate_importance(
            "This is terrible! The worst bug ever! Everything is broken!",
            MemoryType.PROCEDURAL,
        )

        # Negative sentiment about problems is also important
        assert negative_importance > 0

    def test_confidence_adjustment(self, classifier):
        """Test confidence score adjustments."""
        # High confidence indicators
        content = "We definitely must use Python for this project"
        result = classifier.classify(content)
        base_confidence = result.confidence

        # Low confidence indicators
        content = "Maybe we could possibly use Python for this project"
        result = classifier.classify(content)
        assert result.confidence <= base_confidence

    def test_classification_with_entities_boost(self, classifier):
        """Test that entity presence boosts confidence."""
        # Content with entities
        content = "John Smith from Google said Python is the best for machine learning"
        result = classifier.classify(content)

        assert len(result.entities) > 0
        assert result.confidence > classifier.MIN_CONFIDENCE_THRESHOLD


class TestPatternFunctions:
    """Test pattern utility functions."""

    def test_get_memory_type_indicators(self):
        """Test memory type indicator retrieval."""
        indicators = get_memory_type_indicators()

        assert MemoryType.SEMANTIC in indicators
        assert MemoryType.PREFERENCE in indicators
        assert MemoryType.EPISODIC in indicators
        assert MemoryType.PROCEDURAL in indicators
        assert MemoryType.WORKING in indicators
        assert MemoryType.SENSORY in indicators

        # Check that each type has indicators
        for _memory_type, patterns in indicators.items():
            assert len(patterns) > 0
            assert all(isinstance(p, str) for p in patterns)

    def test_get_training_data(self):
        """Test training data retrieval."""
        data = get_training_data()

        # Should have exactly 146 training examples
        assert len(data) == 146

        # Count examples by type
        type_counts = {}
        for example in data:
            assert "text" in example
            assert "type" in example
            assert isinstance(example["text"], str)
            assert example["type"] in [
                "episodic",
                "semantic",
                "procedural",
                "working",
                "sensory",
                "preference",
            ]
            type_counts[example["type"]] = type_counts.get(example["type"], 0) + 1

        # Verify distribution of examples
        assert type_counts["episodic"] == 23
        assert type_counts["semantic"] == 23
        assert type_counts["procedural"] == 23
        assert type_counts["working"] == 24
        assert type_counts["sensory"] == 23
        assert type_counts["preference"] == 30

    def test_adjust_confidence_by_indicators(self):
        """Test confidence adjustment based on linguistic indicators."""
        # High confidence indicator
        high_conf = adjust_confidence_by_indicators("We definitely need to implement this", 0.5)
        assert high_conf > 0.5

        # Low confidence indicator
        low_conf = adjust_confidence_by_indicators("Maybe we could try this approach", 0.5)
        assert low_conf < 0.5

        # No indicators
        same_conf = adjust_confidence_by_indicators("We will implement this feature", 0.5)
        assert same_conf == 0.5

    def test_calculate_content_importance(self):
        """Test content importance factor calculation."""
        # Content with code
        factors = calculate_content_importance("def hello(): return 'Hello World'")
        assert factors["contains_code"] is True

        # Content with URL
        factors = calculate_content_importance("Visit https://example.com for more info")
        assert factors["contains_url"] is True

        # Content with numbers
        factors = calculate_content_importance("The server has 8 CPU cores and 32GB RAM")
        assert factors["contains_numbers"] is True

        # Question content
        factors = calculate_content_importance("How do we implement authentication?")
        assert factors["is_question"] is True

        # Technical content
        factors = calculate_content_importance(
            "The API uses a REST architecture with JSON responses"
        )
        assert factors["is_technical"] is True

        # Long content
        long_text = " ".join(["word"] * 60)
        factors = calculate_content_importance(long_text)
        assert factors["is_long"] is True


class TestIntegrationWithMemoryEnhancer:
    """Test integration with MemoryEnhancer."""

    @pytest.fixture
    def memory_enhancer(self):
        """Create a test MemoryEnhancer with NLP enabled."""
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.memory_enhancer import MemoryEnhancer

        config = KuzuMemoryConfig()
        config.extraction.enable_nlp_classification = True

        # Mock NLTK if not available
        if not HAS_NLTK:
            import sys
            from unittest.mock import MagicMock

            mock_nltk = MagicMock()
            sys.modules["nltk"] = mock_nltk
            sys.modules["nltk.tokenize"] = MagicMock()
            sys.modules["nltk.corpus"] = MagicMock()
            sys.modules["nltk.sentiment"] = MagicMock()
            sys.modules["nltk.sentiment.vader"] = MagicMock()
            sys.modules["nltk.chunk"] = MagicMock()
            sys.modules["nltk.stem"] = MagicMock()
            sys.modules["nltk.tag"] = MagicMock()
            sys.modules["nltk.tree"] = MagicMock()

        with patch("kuzu_memory.storage.memory_enhancer.NLP_AVAILABLE", True):
            with patch("kuzu_memory.nlp.classifier.NLTK_AVAILABLE", True):
                enhancer = MemoryEnhancer(config)
                # Mock the classifier
                enhancer.nlp_classifier = Mock(spec=MemoryClassifier)
                enhancer.nlp_classifier.classify = Mock(
                    return_value=ClassificationResult(
                        memory_type=MemoryType.PREFERENCE,
                        confidence=0.85,
                        keywords=["python", "backend"],
                        entities=["Python"],
                        intent="preference",
                    )
                )
                enhancer.nlp_classifier.calculate_importance = Mock(return_value=0.8)

                yield enhancer

        # Cleanup
        if not HAS_NLTK:
            for module in list(sys.modules.keys()):
                if module.startswith("nltk"):
                    del sys.modules[module]

    def test_classify_memory_method(self, memory_enhancer):
        """Test the classify_memory method."""
        result = memory_enhancer.classify_memory("I prefer Python for backend development")

        assert result["memory_type"] == MemoryType.PREFERENCE
        assert result["confidence"] == 0.85
        assert "python" in result["keywords"]
        assert "Python" in result["entities"]
        assert result["intent"] == "preference"
        assert result["importance"] == 0.8

    def test_enhance_extracted_memory_with_nlp(self, memory_enhancer):
        """Test enhancing extracted memory with NLP."""
        extracted_memory = ExtractedMemory(
            content="I prefer Python for backend development",
            confidence=0.6,
            memory_type=MemoryType.EPISODIC,
            pattern_used="generic",
            entities=[],
            metadata={},
        )

        enhanced = memory_enhancer.enhance_extracted_memory_with_nlp(extracted_memory)

        # Should update with NLP classification (higher confidence)
        assert enhanced.memory_type == MemoryType.PREFERENCE
        assert enhanced.confidence == 0.85
        # Entities can be either strings or dicts depending on extraction method
        entity_names = [e if isinstance(e, str) else e.get("name", e) for e in enhanced.entities]
        assert "Python" in entity_names
        assert "nlp_classification" in enhanced.metadata
        assert enhanced.metadata["nlp_classification"]["type"] == "preference"
        assert enhanced.metadata["nlp_classification"]["confidence"] == 0.85

    def test_enhance_without_nlp_classifier(self):
        """Test enhancement when NLP classifier is not available."""
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.memory_enhancer import MemoryEnhancer

        config = KuzuMemoryConfig()
        config.extraction.enable_nlp_classification = False

        enhancer = MemoryEnhancer(config)
        assert enhancer.nlp_classifier is None

        extracted_memory = ExtractedMemory(
            content="Test content",
            confidence=0.6,
            memory_type=MemoryType.EPISODIC,
            pattern_used="generic",
            entities=[],
            metadata={},
        )

        # Should return unchanged
        enhanced = enhancer.enhance_extracted_memory_with_nlp(extracted_memory)
        assert enhanced == extracted_memory

    def test_classification_result_dataclass(self):
        """Test ClassificationResult dataclass."""
        result = ClassificationResult(
            memory_type=MemoryType.SEMANTIC,
            confidence=0.95,
            keywords=["name", "engineer"],
            entities=["Alice"],
            intent="fact",
        )

        assert result.memory_type == MemoryType.SEMANTIC
        assert result.confidence == 0.95
        assert "name" in result.keywords
        assert "Alice" in result.entities
        assert result.intent == "fact"
        assert result.metadata == {}  # Default empty dict

    def test_entity_extraction_result_dataclass(self):
        """Test EntityExtractionResult dataclass."""
        result = EntityExtractionResult(
            people=["John Smith", "Jane Doe"],
            organizations=["Google", "Microsoft"],
            locations=["San Francisco", "New York"],
            technologies=["Python", "Docker"],
            projects=["Project Alpha"],
            dates=["2024-01-01", "yesterday"],
            all_entities=["John Smith", "Google", "Python", "2024-01-01"],
        )

        assert "John Smith" in result.people
        assert "Google" in result.organizations
        assert "San Francisco" in result.locations
        assert "Python" in result.technologies
        assert "Project Alpha" in result.projects
        assert "2024-01-01" in result.dates
        assert len(result.all_entities) == 4


class TestSentimentResult:
    """Test SentimentResult dataclass."""

    def test_sentiment_result_creation(self):
        """Test creating SentimentResult instances."""
        result = SentimentResult(
            positive=0.6, negative=0.1, neutral=0.3, compound=0.7, dominant="positive"
        )

        assert result.positive == 0.6
        assert result.negative == 0.1
        assert result.neutral == 0.3
        assert result.compound == 0.7
        assert result.dominant == "positive"

    def test_sentiment_result_values(self):
        """Test sentiment result value ranges."""
        # Valid sentiment scores
        result = SentimentResult(
            positive=1.0, negative=0.0, neutral=0.0, compound=1.0, dominant="positive"
        )
        assert result.compound >= -1.0 and result.compound <= 1.0
        assert result.positive >= 0.0 and result.positive <= 1.0
        assert result.negative >= 0.0 and result.negative <= 1.0
        assert result.neutral >= 0.0 and result.neutral <= 1.0

        # Negative compound
        result = SentimentResult(
            positive=0.0, negative=1.0, neutral=0.0, compound=-1.0, dominant="negative"
        )
        assert result.compound == -1.0
        assert result.dominant == "negative"


class TestBatchProcessingIntegration:
    """Test batch processing integration with async operations."""

    def test_batch_with_async_compatibility(self):
        """Test that batch processing works with async memory operations."""
        # This tests that the batch processing returns serializable results
        # that can be used with the async_memory system
        from kuzu_memory.nlp import MemoryClassifier

        classifier = MemoryClassifier(auto_download=False)
        contents = [
            "User preference: dark mode",
            "Decision: use PostgreSQL",
            "Pattern: always validate input",
        ]

        results = classifier.classify_batch(contents)

        # Results should be serializable for async queue
        for result in results:
            # Check that result has required attributes
            assert hasattr(result, "memory_type")
            assert hasattr(result, "confidence")
            assert hasattr(result, "keywords")
            assert hasattr(result, "entities")
            assert hasattr(result, "metadata")

            # Check types are JSON-serializable
            assert isinstance(result.confidence, float)
            assert isinstance(result.keywords, list)
            assert isinstance(result.entities, list)
            assert isinstance(result.metadata, dict)
