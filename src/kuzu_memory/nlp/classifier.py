"""
Memory classification using NLP techniques.

Implements automatic memory type detection, entity extraction, and
confidence scoring using NLTK, following the architecture from the
TypeScript implementation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nltk.stem import PorterStemmer
    from sklearn.pipeline import Pipeline

try:
    import nltk
    from nltk.chunk import ne_chunk
    from nltk.stem import PorterStemmer
    from nltk.tag import pos_tag
    from nltk.tokenize import word_tokenize
    from nltk.tree import Tree
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from ..core.models import MemoryType
from .patterns import (
    ENTITY_PATTERNS,
    INTENT_KEYWORDS,
    MEMORY_TYPE_PATTERNS,
    get_memory_type_indicators,
    get_training_data,
)

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of memory classification."""

    memory_type: MemoryType
    confidence: float
    keywords: list[str]
    entities: list[str]
    intent: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EntityExtractionResult:
    """Result of entity extraction."""

    people: list[str]
    organizations: list[str]
    locations: list[str]
    technologies: list[str]
    projects: list[str]
    dates: list[str]
    all_entities: list[str]


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""

    positive: float  # 0-1 score for positive sentiment
    negative: float  # 0-1 score for negative sentiment
    neutral: float  # 0-1 score for neutral sentiment
    compound: float  # -1 to 1 overall sentiment score
    dominant: str  # 'positive', 'negative', or 'neutral'


class MemoryClassifier:
    """
    NLP-based memory classifier for automatic categorization.

    Implements a multi-stage classification pipeline:
    1. Pattern matching for type indicators
    2. Entity extraction for contextual understanding
    3. Intent detection for action-oriented memories
    4. Machine learning classification with confidence scoring
    """

    # Type annotations for instance variables
    initialized: bool
    classifier: Pipeline | None
    stemmer: PorterStemmer | None
    sentiment_analyzer: Any  # SentimentIntensityAnalyzer if available
    stop_words: set[str]

    def __init__(self, auto_download: bool = False) -> None:
        """
        Initialize the memory classifier.

        Args:
            auto_download: Whether to automatically download NLTK data
        """
        self.initialized = False
        self.classifier = None
        self.stemmer = None
        self.sentiment_analyzer = None
        self.stop_words = set()

        # Confidence thresholds
        self.PATTERN_CONFIDENCE_BOOST = 0.3
        self.ENTITY_CONFIDENCE_BOOST = 0.1
        self.MIN_CONFIDENCE_THRESHOLD = 0.5
        self.SENTIMENT_IMPORTANCE_WEIGHT = 0.15  # How much sentiment affects importance

        # Initialize NLTK components
        if NLTK_AVAILABLE:
            self._initialize_nltk(auto_download)
            self._train_classifier()

    def _initialize_nltk(self, auto_download: bool = False) -> None:
        """Initialize NLTK components and download required data."""
        try:
            # Add custom NLTK data paths
            import os

            home_nltk = os.path.expanduser("~/nltk_data")
            if os.path.exists(home_nltk):
                nltk.data.path.append(home_nltk)

            # Check for required NLTK data with correct paths
            required_data_paths = {
                "punkt": "tokenizers/punkt",
                "averaged_perceptron_tagger": "taggers/averaged_perceptron_tagger",
                "maxent_ne_chunker": "chunkers/maxent_ne_chunker",
                "words": "corpora/words",
                "stopwords": "corpora/stopwords",
                "vader_lexicon": "sentiment/vader_lexicon",
            }

            for data_item, data_path in required_data_paths.items():
                try:
                    nltk.data.find(data_path)
                except LookupError:
                    if auto_download:
                        logger.info(f"Downloading NLTK data: {data_item}")
                        nltk.download(data_item, quiet=True)
                    else:
                        # Don't warn if data exists but just has different path
                        # Try to verify the resource can actually be used
                        try:
                            if data_item == "punkt":
                                # Test punkt tokenizer
                                from nltk.tokenize import word_tokenize

                                word_tokenize("test")
                            elif data_item == "stopwords":
                                # Test stopwords
                                from nltk.corpus import stopwords as sw

                                sw.words("english")
                            elif data_item == "vader_lexicon":
                                # Test VADER sentiment
                                from nltk.sentiment.vader import (
                                    SentimentIntensityAnalyzer,
                                )

                                SentimentIntensityAnalyzer()
                        except Exception:
                            logger.warning(
                                f"NLTK data missing: {data_item}. Run with auto_download=True"
                            )

            # Initialize stop words
            try:
                from nltk.corpus import stopwords as stopwords_corpus

                self.stop_words = set(stopwords_corpus.words("english"))
            except (LookupError, ImportError):
                self.stop_words = set()

            # Initialize sentiment analyzer
            try:
                self.sentiment_analyzer = SentimentIntensityAnalyzer()
                logger.info("VADER sentiment analyzer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize sentiment analyzer: {e}")
                self.sentiment_analyzer = None

            # Initialize stemmer
            try:
                self.stemmer = PorterStemmer()
                logger.info("Porter stemmer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize stemmer: {e}")
                self.stemmer = None

            self.initialized = True
            logger.info("NLTK components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize NLTK: {e}")
            self.initialized = False

    def _train_classifier(self) -> None:
        """Train the Naive Bayes classifier with training data."""
        if not NLTK_AVAILABLE or not self.initialized:
            return

        try:
            # Get training data from patterns module
            training_data = get_training_data()

            if not training_data:
                logger.warning("No training data available for classifier")
                return

            # Prepare training samples
            X_train = []
            y_train = []

            for example in training_data:
                X_train.append(example["text"])
                y_train.append(example["type"])

            # Create and train pipeline
            classifier_pipeline = Pipeline(
                [
                    (
                        "tfidf",
                        TfidfVectorizer(max_features=100, ngram_range=(1, 2), stop_words="english"),
                    ),
                    ("clf", MultinomialNB(alpha=0.1)),
                ]
            )

            classifier_pipeline.fit(X_train, y_train)
            self.classifier = classifier_pipeline  # Assign after successful training
            logger.info(f"Classifier trained with {len(X_train)} samples")

        except Exception as e:
            logger.error(f"Failed to train classifier: {e}")
            self.classifier = None

    def classify(self, content: str) -> ClassificationResult:
        """
        Classify memory content into appropriate type.

        Uses a multi-stage approach:
        1. Check for explicit type indicators (highest confidence)
        2. Extract entities and intents for context
        3. Use ML classifier for prediction
        4. Apply confidence scoring and thresholds

        Args:
            content: The memory content to classify

        Returns:
            ClassificationResult with type, confidence, and metadata
        """
        if not content or not content.strip():
            return ClassificationResult(
                memory_type=MemoryType.EPISODIC,
                confidence=0.0,
                keywords=[],
                entities=[],
            )

        content_lower = content.lower().strip()

        # Stage 1: Pattern matching for type indicators
        pattern_type = self._check_type_indicators(content_lower)
        pattern_confidence = 0.0

        if pattern_type:
            pattern_confidence = 0.8 + self.PATTERN_CONFIDENCE_BOOST

        # Stage 2: Entity extraction
        entities_result = self.extract_entities(content)
        all_entities = entities_result.all_entities

        # Stage 3: Intent detection
        intent = self._detect_intent(content_lower)

        # Stage 4: Keyword extraction
        keywords = self._extract_keywords(content)

        # Stage 5: ML classification (if available)
        ml_type = MemoryType.EPISODIC
        ml_confidence = 0.5

        if self.classifier and NLTK_AVAILABLE:
            try:
                # Get prediction probabilities
                proba = self.classifier.predict_proba([content])[0]
                classes = self.classifier.classes_

                # Find best prediction
                max_idx = proba.argmax()
                ml_type_str = classes[max_idx]
                ml_confidence = proba[max_idx]

                # Convert to MemoryType enum
                ml_type = self._string_to_memory_type(ml_type_str)

            except Exception as e:
                logger.debug(f"ML classification failed: {e}")

        # Stage 6: Combine results with confidence weighting
        final_type = pattern_type or ml_type
        final_confidence = max(pattern_confidence, ml_confidence)

        # Boost confidence based on entity presence
        if all_entities:
            final_confidence = min(1.0, final_confidence + self.ENTITY_CONFIDENCE_BOOST)

        # Apply intent-based adjustments
        if intent:
            final_type, final_confidence = self._adjust_for_intent(
                final_type, final_confidence, intent
            )

        # Apply confidence threshold
        if final_confidence < self.MIN_CONFIDENCE_THRESHOLD:
            final_type = MemoryType.EPISODIC
            final_confidence = 0.5

        return ClassificationResult(
            memory_type=final_type,
            confidence=final_confidence,
            keywords=keywords[:10],  # Top 10 keywords
            entities=all_entities,
            intent=intent,
            metadata={
                "pattern_match": pattern_type is not None,
                "ml_confidence": ml_confidence,
                "entity_count": len(all_entities),
                "classification_method": "pattern" if pattern_type else "ml",
            },
        )

    def _check_type_indicators(self, content: str) -> MemoryType | None:
        """
        Check for explicit type indicators in content.

        Args:
            content: Lowercase content to check

        Returns:
            Detected MemoryType or None
        """
        # Check regex patterns in priority order (more specific patterns first)
        # Sensory patterns are checked before preference to avoid false matches on "like"
        priority_order = [
            MemoryType.SENSORY,  # Check sensory first (smells like, tastes like)
            MemoryType.PROCEDURAL,  # Then procedural (how to, steps)
            MemoryType.SEMANTIC,  # Then semantic (is a, are)
            MemoryType.PREFERENCE,  # Then preference (like, prefer)
            MemoryType.WORKING,  # Then working (need to, todo)
            MemoryType.EPISODIC,  # Finally episodic (general events)
        ]

        for memory_type in priority_order:
            if memory_type in MEMORY_TYPE_PATTERNS:
                for pattern in MEMORY_TYPE_PATTERNS[memory_type]:
                    if re.search(pattern, content, re.IGNORECASE):
                        return memory_type

        # Then check simple keyword indicators (less specific)
        indicators = get_memory_type_indicators()
        for memory_type in priority_order:
            if memory_type in indicators:
                for pattern in indicators[memory_type]:
                    if pattern in content:
                        return memory_type

        return None

    def extract_entities(self, content: str) -> EntityExtractionResult:
        """
        Extract named entities from content.

        Uses NLTK NER and custom patterns for:
        - People names
        - Organizations
        - Locations
        - Technologies (custom patterns)
        - Projects (custom patterns)
        - Dates

        Args:
            content: Content to extract entities from

        Returns:
            EntityExtractionResult with categorized entities
        """
        people = []
        organizations = []
        locations = []
        technologies = []
        projects = []
        dates = []

        if not NLTK_AVAILABLE or not self.initialized:
            # Fallback to regex patterns
            return self._extract_entities_regex(content)

        try:
            # Tokenize and tag
            tokens = word_tokenize(content)
            pos_tags = pos_tag(tokens)

            # Named Entity Recognition
            chunks = ne_chunk(pos_tags, binary=False)

            for chunk in chunks:
                if isinstance(chunk, Tree):
                    label = chunk.label()
                    entity = " ".join([token for token, pos in chunk.leaves()])

                    if label == "PERSON":
                        people.append(entity)
                    elif label == "ORGANIZATION":
                        organizations.append(entity)
                    elif label in ["GPE", "LOCATION"]:
                        locations.append(entity)

            # Extract technologies using patterns
            tech_matches = self._extract_technologies(content)
            technologies.extend(tech_matches)

            # Extract projects (capitalized multi-word phrases)
            project_matches = self._extract_projects(content)
            projects.extend(project_matches)

            # Extract dates using patterns
            date_matches = self._extract_dates(content)
            dates.extend(date_matches)

        except Exception as e:
            logger.debug(f"Entity extraction with NLTK failed: {e}")
            return self._extract_entities_regex(content)

        # Combine all entities
        all_entities = list(
            set(people + organizations + locations + technologies + projects + dates)
        )

        return EntityExtractionResult(
            people=list(set(people)),
            organizations=list(set(organizations)),
            locations=list(set(locations)),
            technologies=list(set(technologies)),
            projects=list(set(projects)),
            dates=list(set(dates)),
            all_entities=all_entities,
        )

    def _extract_entities_regex(self, content: str) -> EntityExtractionResult:
        """Fallback entity extraction using regex patterns."""
        people = []
        organizations = []
        locations = []
        technologies = []
        projects = []
        dates = []

        # Extract using patterns from patterns.py
        for category, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if category == "person":
                    people.extend(matches)
                elif category == "organization":
                    organizations.extend(matches)
                elif category == "location":
                    locations.extend(matches)
                elif category == "technology":
                    technologies.extend(matches)
                elif category == "project":
                    projects.extend(matches)
                elif category == "date":
                    dates.extend(matches)

        # Also use the comprehensive extraction methods
        # to catch any entities missed by the basic patterns
        tech_matches = self._extract_technologies(content)
        technologies.extend(tech_matches)

        project_matches = self._extract_projects(content)
        projects.extend(project_matches)

        date_matches = self._extract_dates(content)
        dates.extend(date_matches)

        # Combine all entities
        all_entities = list(
            set(people + organizations + locations + technologies + projects + dates)
        )

        return EntityExtractionResult(
            people=list(set(people)),
            organizations=list(set(organizations)),
            locations=list(set(locations)),
            technologies=list(set(technologies)),
            projects=list(set(projects)),
            dates=list(set(dates)),
            all_entities=all_entities,
        )

    def _extract_technologies(self, content: str) -> list[str]:
        """Extract technology names from content."""
        technologies = []

        # Common technology patterns
        tech_patterns = [
            r"\b(Python|JavaScript|TypeScript|Java|C\+\+|C#|Go|Rust|Swift|Kotlin)\b",
            r"\b(React|Vue|Angular|Django|Flask|FastAPI|Spring|Node\.js|Express)\b",
            r"\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|SQLite|DynamoDB)\b",
            r"\b(AWS|Azure|GCP|Docker|Kubernetes|Jenkins|GitHub|GitLab)\b",
            r"\b(TensorFlow|PyTorch|scikit-learn|Pandas|NumPy|NLTK|spaCy)\b",
        ]

        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            technologies.extend(matches)

        return list(set(technologies))

    def _extract_projects(self, content: str) -> list[str]:
        """Extract project names from content."""
        projects = []

        # Project name patterns (capitalized phrases)
        project_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
        matches = re.findall(project_pattern, content)

        # Filter out common false positives
        false_positives = {
            "The",
            "This",
            "That",
            "These",
            "Those",
            "We",
            "You",
            "They",
            "It",
            "I",
        }

        for match in matches:
            first_word = match.split()[0]
            if first_word not in false_positives and len(match.split()) <= 4:
                projects.append(match)

        return list(set(projects))

    def _extract_dates(self, content: str) -> list[str]:
        """Extract date references from content."""
        dates = []

        # Date patterns
        date_patterns = [
            r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            r"\b(yesterday|today|tomorrow|last\s+\w+|next\s+\w+)\b",
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dates.extend(matches)

        return list(set(dates))

    def _detect_intent(self, content: str) -> str | None:
        """
        Detect the intent or action in the content.

        Args:
            content: Lowercase content to analyze

        Returns:
            Detected intent type or None
        """
        for intent, keywords in INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    return intent
        return None

    def _extract_keywords(self, content: str) -> list[str]:
        """
        Extract important keywords from content.

        Args:
            content: Content to extract keywords from

        Returns:
            List of keywords sorted by importance
        """
        if not NLTK_AVAILABLE or not self.initialized:
            # Simple fallback: extract capitalized words
            words = re.findall(r"\b[A-Z][a-z]+\b", content)
            return list(set(words))[:10]

        try:
            # Tokenize and filter
            tokens = word_tokenize(content.lower())

            # Remove stop words and short words
            keywords = [
                word
                for word in tokens
                if word not in self.stop_words and len(word) > 3 and word.isalnum()
            ]

            # Get POS tags and filter for nouns and verbs
            pos_tags = pos_tag(keywords)
            important_words = [
                word for word, pos in pos_tags if pos.startswith("NN") or pos.startswith("VB")
            ]

            # Count frequencies (stem words if stemmer available)
            word_freq = {}
            for word in important_words:
                # Use stemmed version for frequency counting if stemmer available
                key = self.stemmer.stem(word) if self.stemmer else word
                word_freq[key] = word_freq.get(key, 0) + 1

            # Sort by frequency
            sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

            return [word for word, _ in sorted_keywords][:10]

        except Exception as e:
            logger.debug(f"Keyword extraction failed: {e}")
            # Fallback to simple capitalized word extraction
            words = re.findall(r"\b[A-Z][a-z]+\b", content)
            return list(set(words))[:10]

    def _adjust_for_intent(
        self, memory_type: MemoryType, confidence: float, intent: str
    ) -> tuple[MemoryType, float]:
        """
        Adjust memory type and confidence based on detected intent.

        Args:
            memory_type: Initial memory type
            confidence: Initial confidence
            intent: Detected intent

        Returns:
            Tuple of adjusted type and confidence
        """
        intent_type_mapping = {
            "decision": MemoryType.EPISODIC,  # Decisions are events
            "preference": MemoryType.PREFERENCE,  # Preferences unchanged
            "solution": MemoryType.PROCEDURAL,  # Solutions are instructions
            "pattern": MemoryType.PROCEDURAL,  # Patterns are procedures
            "fact": MemoryType.SEMANTIC,  # Facts are semantic knowledge
            "observation": MemoryType.EPISODIC,  # Observations are experiences
            "status": MemoryType.WORKING,  # Status is current work
        }

        if intent in intent_type_mapping:
            suggested_type = intent_type_mapping[intent]

            # Don't override SENSORY type with PREFERENCE intent
            # Sensory descriptions like "smells like" are more specific than preference
            if memory_type == MemoryType.SENSORY and suggested_type == MemoryType.PREFERENCE:
                return memory_type, confidence

            # If intent strongly suggests a different type, adjust
            if memory_type != suggested_type:
                # Average the confidence with intent confidence
                intent_confidence = 0.7
                adjusted_confidence = (confidence + intent_confidence) / 2
                return suggested_type, adjusted_confidence

        return memory_type, confidence

    def _string_to_memory_type(self, type_str: str) -> MemoryType:
        """Convert string to MemoryType enum."""
        # Direct mapping for new types
        type_mapping = {
            "episodic": MemoryType.EPISODIC,
            "semantic": MemoryType.SEMANTIC,
            "procedural": MemoryType.PROCEDURAL,
            "working": MemoryType.WORKING,
            "sensory": MemoryType.SENSORY,
            "preference": MemoryType.PREFERENCE,
        }

        # Legacy type migration
        legacy_mapping = {
            "identity": MemoryType.SEMANTIC,  # Facts about identity
            "decision": MemoryType.EPISODIC,  # Decisions are events
            "pattern": MemoryType.PROCEDURAL,  # Patterns are procedures
            "solution": MemoryType.PROCEDURAL,  # Solutions are instructions
            "status": MemoryType.WORKING,  # Status is current work
            "context": MemoryType.EPISODIC,  # Context is experiential
        }

        type_str_lower = type_str.lower()

        # Try new types first
        if type_str_lower in type_mapping:
            return type_mapping[type_str_lower]

        # Fall back to legacy mapping
        if type_str_lower in legacy_mapping:
            return legacy_mapping[type_str_lower]

        # Default to episodic
        return MemoryType.EPISODIC

    def analyze_sentiment(self, content: str) -> SentimentResult:
        """
        Analyze sentiment of content using VADER.

        VADER (Valence Aware Dictionary and sEntiment Reasoner) is particularly
        good for social media text and short sentences. It handles:
        - Emoticons and emojis
        - Capitalization for emphasis
        - Degree modifiers ("extremely", "slightly")
        - Negations
        - Punctuation for emphasis

        Args:
            content: Text to analyze

        Returns:
            SentimentResult with polarity scores
        """
        # Default neutral sentiment if analyzer not available
        if not NLTK_AVAILABLE or not self.sentiment_analyzer:
            return SentimentResult(
                positive=0.0,
                negative=0.0,
                neutral=1.0,
                compound=0.0,
                dominant="neutral",
            )

        try:
            # Get sentiment scores
            scores = self.sentiment_analyzer.polarity_scores(content)

            # Determine dominant sentiment
            dominant = "neutral"
            if scores["compound"] >= 0.05:
                dominant = "positive"
            elif scores["compound"] <= -0.05:
                dominant = "negative"

            return SentimentResult(
                positive=scores["pos"],
                negative=scores["neg"],
                neutral=scores["neu"],
                compound=scores["compound"],
                dominant=dominant,
            )
        except Exception as e:
            logger.debug(f"Sentiment analysis failed: {e}")
            return SentimentResult(
                positive=0.0,
                negative=0.0,
                neutral=1.0,
                compound=0.0,
                dominant="neutral",
            )

    def classify_batch(self, contents: list[str]) -> list[ClassificationResult]:
        """
        Classify multiple memory contents efficiently.

        Uses vectorization and batch processing where possible to
        optimize performance for multiple items.

        Args:
            contents: List of memory contents to classify

        Returns:
            List of ClassificationResult objects
        """
        if not contents:
            return []

        results = []

        # Prepare for batch ML classification if available
        ml_predictions = None
        if self.classifier and NLTK_AVAILABLE and len(contents) > 1:
            try:
                # Batch predict with ML classifier
                probas = self.classifier.predict_proba(contents)
                classes = self.classifier.classes_

                ml_predictions = []
                for proba in probas:
                    max_idx = proba.argmax()
                    ml_type_str = classes[max_idx]
                    ml_confidence = proba[max_idx]
                    ml_predictions.append(
                        {
                            "type": self._string_to_memory_type(ml_type_str),
                            "confidence": ml_confidence,
                        }
                    )
            except Exception as e:
                logger.debug(f"Batch ML classification failed: {e}")
                ml_predictions = None

        # Process each content item
        for idx, content in enumerate(contents):
            if not content or not content.strip():
                results.append(
                    ClassificationResult(
                        memory_type=MemoryType.EPISODIC,
                        confidence=0.0,
                        keywords=[],
                        entities=[],
                    )
                )
                continue

            content_lower = content.lower().strip()

            # Pattern matching
            pattern_type = self._check_type_indicators(content_lower)
            pattern_confidence = 0.8 + self.PATTERN_CONFIDENCE_BOOST if pattern_type else 0.0

            # Entity extraction (can be optimized further with batch NER)
            entities_result = self.extract_entities(content)
            all_entities = entities_result.all_entities

            # Intent detection
            intent = self._detect_intent(content_lower)

            # Keywords extraction
            keywords = self._extract_keywords(content)

            # Use batch ML prediction if available
            ml_type = MemoryType.EPISODIC
            ml_confidence = 0.5
            if ml_predictions and idx < len(ml_predictions):
                ml_type = ml_predictions[idx]["type"]
                ml_confidence = ml_predictions[idx]["confidence"]
            elif self.classifier and NLTK_AVAILABLE and not ml_predictions:
                # Fallback to individual classification if batch failed
                try:
                    proba = self.classifier.predict_proba([content])[0]
                    classes = self.classifier.classes_
                    max_idx = proba.argmax()
                    ml_type_str = classes[max_idx]
                    ml_confidence = proba[max_idx]
                    ml_type = self._string_to_memory_type(ml_type_str)
                except Exception as e:
                    logger.debug(f"Individual ML classification failed: {e}")

            # Combine results
            final_type = pattern_type or ml_type
            final_confidence = max(pattern_confidence, ml_confidence)

            # Boost confidence based on entities
            if all_entities:
                final_confidence = min(1.0, final_confidence + self.ENTITY_CONFIDENCE_BOOST)

            # Apply intent adjustments
            if intent:
                final_type, final_confidence = self._adjust_for_intent(
                    final_type, final_confidence, intent
                )

            # Apply threshold
            if final_confidence < self.MIN_CONFIDENCE_THRESHOLD:
                final_type = MemoryType.EPISODIC
                final_confidence = 0.5

            results.append(
                ClassificationResult(
                    memory_type=final_type,
                    confidence=final_confidence,
                    keywords=keywords[:10],
                    entities=all_entities,
                    intent=intent,
                    metadata={
                        "pattern_match": pattern_type is not None,
                        "ml_confidence": ml_confidence,
                        "entity_count": len(all_entities),
                        "classification_method": "pattern" if pattern_type else "ml",
                        "batch_processed": ml_predictions is not None,
                    },
                )
            )

        return results

    def calculate_importance(self, content: str, memory_type: MemoryType) -> float:
        """
        Calculate importance score for memory content.

        Uses multiple factors:
        - Memory type base importance
        - Content length and complexity
        - Entity presence
        - Keyword relevance

        Args:
            content: Memory content
            memory_type: Type of memory

        Returns:
            Importance score between 0 and 1
        """
        # Start with base importance for memory type
        base_importance = MemoryType.get_default_importance(memory_type)

        # Adjust based on content characteristics
        adjustments = []

        # Length factor (longer content might be more detailed)
        length_factor = min(len(content) / 500, 1.0) * 0.1
        adjustments.append(length_factor)

        # Entity factor (more entities = more contextual)
        entities = self.extract_entities(content)
        entity_factor = min(len(entities.all_entities) / 5, 1.0) * 0.1
        adjustments.append(entity_factor)

        # Question marks indicate queries (lower importance)
        if "?" in content:
            adjustments.append(-0.1)

        # Exclamation marks indicate emphasis (higher importance)
        if "!" in content:
            adjustments.append(0.05)

        # Technical terms increase importance
        tech_terms = self._extract_technologies(content)
        if tech_terms:
            adjustments.append(0.1)

        # Sentiment analysis adjustment
        sentiment = self.analyze_sentiment(content)

        # Strong positive or negative sentiment increases importance
        # Neutral sentiment has less impact
        sentiment_factor = 0.0
        if abs(sentiment.compound) > 0.5:  # Strong sentiment
            sentiment_factor = self.SENTIMENT_IMPORTANCE_WEIGHT
        elif abs(sentiment.compound) > 0.25:  # Moderate sentiment
            sentiment_factor = self.SENTIMENT_IMPORTANCE_WEIGHT * 0.5

        adjustments.append(sentiment_factor)

        # Calculate final importance
        final_importance = base_importance + sum(adjustments)

        # Clamp between 0 and 1
        return max(0.1, min(1.0, final_importance))
