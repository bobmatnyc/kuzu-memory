# NLP Memory Classification

KuzuMemory includes an intelligent NLP-based classification system that automatically categorizes memories, extracts entities, and determines importance scores using natural language processing techniques.

## Overview

The NLP classification system follows a multi-stage pipeline similar to the TypeScript implementation:

1. **Pattern Matching** - Quick detection of memory type indicators
2. **Entity Extraction** - Identification of people, organizations, technologies, etc.
3. **Intent Detection** - Understanding the purpose or action in the content
4. **Machine Learning** - Naive Bayes classification with confidence scoring
5. **Importance Calculation** - Context-aware importance scoring

## Features

### Automatic Memory Type Detection

The classifier can automatically detect seven types of memories:

- **Identity** - User/system facts (names, roles, descriptions)
- **Preference** - Settings and preferences
- **Decision** - Architectural and design decisions
- **Pattern** - Code patterns and procedures
- **Solution** - Problem-solution pairs
- **Status** - Current state (expires quickly)
- **Context** - Session context (expires daily)

### Entity Extraction

Extracts named entities from memory content:

- People names
- Organizations
- Locations
- Technologies and programming languages
- Project names
- Date references

### Intent Detection

Identifies the intent or purpose:

- Decision-making
- Preferences
- Solutions
- Patterns/procedures
- Facts/observations
- Status updates

### Confidence Scoring

Multi-factor confidence calculation:

- Pattern matching confidence
- ML classifier confidence
- Entity presence boost
- Linguistic indicator adjustments

## Installation

### Basic Installation

The NLP features are included in the standard installation:

```bash
pip install kuzu-memory
```

### With NLP Dependencies

To enable full NLP capabilities:

```bash
pip install kuzu-memory[nlp]
```

This installs:
- NLTK for natural language processing
- scikit-learn for machine learning classification

### NLTK Data Download

The classifier will automatically attempt to download required NLTK data on first use. To manually download:

```python
import nltk
nltk.download('punkt')          # Tokenization
nltk.download('averaged_perceptron_tagger')  # POS tagging
nltk.download('maxent_ne_chunker')          # Named entity recognition
nltk.download('words')                      # Word corpus
nltk.download('stopwords')                  # Stop words
```

## Usage

### Basic Classification

```python
from kuzu_memory.nlp.classifier import MemoryClassifier

# Initialize classifier
classifier = MemoryClassifier(auto_download=True)

# Classify content
result = classifier.classify("I prefer Python for backend development")

print(f"Type: {result.memory_type}")        # MemoryType.PREFERENCE
print(f"Confidence: {result.confidence}")    # 0.85
print(f"Intent: {result.intent}")           # "preference"
print(f"Keywords: {result.keywords}")       # ["python", "backend", "development"]
print(f"Entities: {result.entities}")       # ["Python"]
```

### Entity Extraction

```python
# Extract entities
content = "John Smith from Google discussed Python with the team"
entities = classifier.extract_entities(content)

print(f"People: {entities.people}")         # ["John Smith"]
print(f"Organizations: {entities.organizations}")  # ["Google"]
print(f"Technologies: {entities.technologies}")    # ["Python"]
```

### Importance Scoring

```python
from kuzu_memory.core.models import MemoryType

# Calculate importance
importance = classifier.calculate_importance(
    content="Critical security fix for authentication",
    memory_type=MemoryType.SOLUTION
)
print(f"Importance: {importance}")  # 0.85
```

### Integration with Memory System

The NLP classifier is automatically integrated when enabled in configuration:

```python
from kuzu_memory import KuzuMemory

# Initialize with NLP enabled (default)
memory = KuzuMemory()

# Memories are automatically classified
memory.remember("We decided to use FastAPI for the API")

# The memory is stored with:
# - Type: DECISION
# - Confidence: 0.9
# - Entities: ["FastAPI"]
# - Intent: "decision"
```

### Configuration

Enable/disable NLP classification in config:

```python
from kuzu_memory.core.config import KuzuMemoryConfig

config = KuzuMemoryConfig()
config.extraction.enable_nlp_classification = True  # Default

memory = KuzuMemory(config=config)
```

## How It Works

### Classification Pipeline

```
Input Text
    │
    ▼
Pattern Matching ─── Check type indicators
    │
    ▼
Entity Extraction ─── Named Entity Recognition
    │
    ▼
Intent Detection ─── Identify purpose/action
    │
    ▼
ML Classification ─── Naive Bayes prediction
    │
    ▼
Confidence Score ─── Combine all signals
    │
    ▼
Final Result
```

### Pattern Matching

Quick detection using keyword indicators:

```python
IDENTITY_INDICATORS = ["my name", "i am", "user is"]
PREFERENCE_INDICATORS = ["prefer", "like", "favorite"]
DECISION_INDICATORS = ["decided", "will use", "chose"]
```

### Machine Learning

Trained Naive Bayes classifier using TF-IDF features:

1. Tokenization and preprocessing
2. TF-IDF vectorization with bigrams
3. Multinomial Naive Bayes classification
4. Probability-based confidence scoring

### Confidence Calculation

```python
final_confidence = max(
    pattern_confidence,  # From pattern matching
    ml_confidence       # From ML classifier
)

# Boost for entity presence
if entities:
    final_confidence += 0.1

# Adjust based on linguistic indicators
if "definitely" in content:
    final_confidence += 0.2
elif "maybe" in content:
    final_confidence -= 0.2
```

## Performance

- Classification: ~5-10ms per memory
- Entity extraction: ~10-20ms with NLTK
- Pattern matching fallback: ~1-2ms
- Memory overhead: ~50MB with NLTK models

## Fallback Behavior

When NLTK is not available:

1. Pattern matching still works (regex-based)
2. Basic entity extraction using patterns
3. Rule-based classification
4. Lower confidence scores

## Examples

### Identity Memory

```python
content = "My name is Alice and I'm a software engineer"
# → Type: IDENTITY, Confidence: 0.95
```

### Preference Memory

```python
content = "I prefer TypeScript over JavaScript"
# → Type: PREFERENCE, Confidence: 0.90
```

### Decision Memory

```python
content = "We decided to use microservices architecture"
# → Type: DECISION, Confidence: 0.92
```

### Pattern Memory

```python
content = "How to deploy: build, test, then push to production"
# → Type: PATTERN, Confidence: 0.88
```

## Testing

Run tests for NLP classification:

```bash
pytest tests/test_nlp_classifier.py
```

Run the demo script:

```bash
python examples/nlp_classification_demo.py
```

## Troubleshooting

### NLTK Data Not Found

If you see NLTK data errors:

```python
import nltk
nltk.download('all')  # Download all NLTK data
```

### Low Confidence Scores

- Ensure content has clear type indicators
- Add more training examples for your domain
- Check that entities are being extracted

### Performance Issues

- Disable NLP for high-throughput scenarios
- Use pattern matching only for faster classification
- Consider caching classification results

## API Reference

### MemoryClassifier

```python
class MemoryClassifier:
    def __init__(self, auto_download: bool = False)
    def classify(self, content: str) -> ClassificationResult
    def extract_entities(self, content: str) -> EntityExtractionResult
    def calculate_importance(self, content: str, memory_type: MemoryType) -> float
```

### ClassificationResult

```python
@dataclass
class ClassificationResult:
    memory_type: MemoryType
    confidence: float
    keywords: List[str]
    entities: List[str]
    intent: Optional[str]
    metadata: Dict[str, Any]
```

### EntityExtractionResult

```python
@dataclass
class EntityExtractionResult:
    people: List[str]
    organizations: List[str]
    locations: List[str]
    technologies: List[str]
    projects: List[str]
    dates: List[str]
    all_entities: List[str]
```