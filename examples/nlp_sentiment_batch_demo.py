#!/usr/bin/env python3
"""
Demonstration of sentiment analysis and batch processing features in KuzuMemory NLP.

This script shows:
1. Sentiment analysis on different types of content
2. Batch classification for efficient processing of multiple items
3. How sentiment affects importance calculation
"""

from kuzu_memory.nlp import MemoryClassifier, SentimentResult
from kuzu_memory.core.models import MemoryType


def demonstrate_sentiment_analysis():
    """Demonstrate sentiment analysis on various types of content."""
    print("\n=== Sentiment Analysis Demo ===\n")

    classifier = MemoryClassifier(auto_download=True)

    # Test different sentiment types
    test_contents = [
        ("I absolutely love this project! It's amazing and works perfectly!", "Positive"),
        ("This is terrible. Nothing works and it's completely broken.", "Negative"),
        ("The database stores user information in a table.", "Neutral"),
        ("The new feature is great, but there are still some bugs to fix.", "Mixed"),
    ]

    for content, expected in test_contents:
        sentiment = classifier.analyze_sentiment(content)
        print(f"Content: {content[:50]}...")
        print(f"Expected: {expected}")
        print(f"Result: {sentiment.dominant} (compound: {sentiment.compound:.3f})")
        print(f"  Positive: {sentiment.positive:.3f}")
        print(f"  Negative: {sentiment.negative:.3f}")
        print(f"  Neutral: {sentiment.neutral:.3f}")
        print()


def demonstrate_batch_processing():
    """Demonstrate batch processing for efficient classification."""
    print("\n=== Batch Processing Demo ===\n")

    classifier = MemoryClassifier(auto_download=True)

    # Batch of memories to classify
    memories = [
        "My name is Alice and I'm a senior developer",
        "I prefer TypeScript over JavaScript for large projects",
        "We decided to use PostgreSQL for the database",
        "The bug was fixed by increasing the timeout value",
        "Currently working on the authentication module",
        "How to deploy: Use Docker containers with Kubernetes",
        "Remember that the API key expires in 30 days",
    ]

    # Process all at once
    import time
    start_time = time.time()
    batch_results = classifier.classify_batch(memories)
    batch_time = time.time() - start_time

    # Process one by one for comparison
    start_time = time.time()
    individual_results = [classifier.classify(m) for m in memories]
    individual_time = time.time() - start_time

    print(f"Batch processing time: {batch_time:.3f}s")
    print(f"Individual processing time: {individual_time:.3f}s")
    print(f"Speedup: {individual_time/batch_time:.2f}x\n")

    # Show results
    for i, (content, result) in enumerate(zip(memories, batch_results)):
        print(f"{i+1}. {content[:40]}...")
        print(f"   Type: {result.memory_type.value}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Batch processed: {result.metadata.get('batch_processed', False)}")
        print()


def demonstrate_sentiment_impact_on_importance():
    """Show how sentiment affects memory importance calculation."""
    print("\n=== Sentiment Impact on Importance ===\n")

    classifier = MemoryClassifier(auto_download=True)

    # Test memories with different sentiments
    test_cases = [
        {
            "content": "This authentication system is absolutely brilliant! Best design ever!",
            "type": MemoryType.PROCEDURAL,  # Solutions are instructions
            "description": "Very positive solution"
        },
        {
            "content": "The authentication system handles user login.",
            "type": MemoryType.PROCEDURAL,  # Solutions are instructions
            "description": "Neutral solution"
        },
        {
            "content": "This authentication system is terrible and completely broken!",
            "type": MemoryType.PROCEDURAL,  # Solutions are instructions
            "description": "Very negative solution"
        },
    ]

    for test in test_cases:
        sentiment = classifier.analyze_sentiment(test["content"])
        importance = classifier.calculate_importance(test["content"], test["type"])

        print(f"Memory: {test['description']}")
        print(f"Content: {test['content'][:50]}...")
        print(f"Sentiment: {sentiment.dominant} (compound: {sentiment.compound:.3f})")
        print(f"Importance: {importance:.3f}")
        print()

    print("Note: Strong sentiments (positive or negative) increase importance")
    print("      because they often indicate critical feedback or strong opinions")


def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("KuzuMemory NLP: Sentiment Analysis & Batch Processing Demo")
    print("="*60)

    demonstrate_sentiment_analysis()
    demonstrate_batch_processing()
    demonstrate_sentiment_impact_on_importance()

    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60)


if __name__ == "__main__":
    main()