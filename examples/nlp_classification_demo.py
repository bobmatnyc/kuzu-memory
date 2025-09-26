#!/usr/bin/env python3
"""
Demo script showing NLP memory classification in KuzuMemory.

This demonstrates how memories are automatically classified using
natural language processing techniques.
"""

import sys
from pathlib import Path

# Add parent directory to path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kuzu_memory.nlp.classifier import MemoryClassifier
from kuzu_memory.core.models import MemoryType


def print_classification(content: str, result):
    """Pretty print classification result."""
    print(f"\n📝 Content: '{content[:60]}{'...' if len(content) > 60 else ''}'")
    print(f"   Type: {result.memory_type.value}")
    print(f"   Confidence: {result.confidence:.2%}")
    if result.intent:
        print(f"   Intent: {result.intent}")
    if result.keywords:
        print(f"   Keywords: {', '.join(result.keywords[:5])}")
    if result.entities:
        print(f"   Entities: {', '.join(result.entities[:5])}")
    print()


def main():
    """Run NLP classification demo."""
    print("=" * 70)
    print("KuzuMemory NLP Classification Demo")
    print("=" * 70)

    # Initialize classifier (will download NLTK data if needed)
    print("\n🔄 Initializing NLP classifier...")
    try:
        classifier = MemoryClassifier(auto_download=True)
        print("✅ Classifier initialized successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize with NLTK: {e}")
        print("   Falling back to pattern-based classification")
        classifier = MemoryClassifier(auto_download=False)

    # Test various memory types
    test_cases = [
        # Semantic memories (facts/knowledge)
        "My name is Alice and I'm a senior software engineer at TechCorp",
        "The project is called KuzuMemory, a graph-based memory system",
        "We are a team of five developers working on AI applications",

        # Preference memories
        "I prefer Python over JavaScript for backend development",
        "The team likes using Docker for containerization",
        "We always use pytest for unit testing our Python code",

        # Episodic memories (events/experiences)
        "We decided to use FastAPI for building the REST API",
        "The architecture will follow a microservices pattern",
        "Going with PostgreSQL as our primary database",

        # Procedural memories (patterns/how-to)
        "How to deploy: First build the Docker image, then push to registry, finally update k8s",
        "The process for code review: create PR, get approval, merge to main",
        "Steps to set up the dev environment: install Python 3.11, create venv, install deps",

        # Procedural memories (solutions/instructions)
        "Fixed the memory leak by implementing proper connection pooling",
        "Resolved the timeout issue by adding async processing",
        "The workaround is to use environment variables for configuration",

        # Working memories (current tasks)
        "Currently working on implementing the authentication module",
        "The migration to the new database is in progress",
        "TODO: Add error handling for network failures",

        # Episodic memories (contextual experiences)
        "John mentioned that the deadline is next Friday",
        "We discussed improving the performance in today's standup",
        "The client asked about adding real-time notifications"
    ]

    print("\n" + "=" * 70)
    print("Testing Memory Classification")
    print("=" * 70)

    for content in test_cases:
        result = classifier.classify(content)
        print_classification(content, result)

    # Extract entities from complex content
    print("\n" + "=" * 70)
    print("Entity Extraction Example")
    print("=" * 70)

    complex_content = """
    Dr. John Smith from Google and Jane Doe from Microsoft met yesterday
    to discuss the new Python-based machine learning framework. They decided
    to use TensorFlow with Docker containers deployed on AWS. The project,
    called DataFlow Pipeline, is scheduled for release on 2024-12-31.
    """

    entities = classifier.extract_entities(complex_content)
    print(f"\n📝 Content: Complex technical discussion")
    print(f"\n👥 People: {', '.join(entities.people) if entities.people else 'None found'}")
    print(f"🏢 Organizations: {', '.join(entities.organizations) if entities.organizations else 'None found'}")
    print(f"📍 Locations: {', '.join(entities.locations) if entities.locations else 'None found'}")
    print(f"💻 Technologies: {', '.join(entities.technologies) if entities.technologies else 'None found'}")
    print(f"📁 Projects: {', '.join(entities.projects) if entities.projects else 'None found'}")
    print(f"📅 Dates: {', '.join(entities.dates) if entities.dates else 'None found'}")

    # Calculate importance scores
    print("\n" + "=" * 70)
    print("Importance Scoring Example")
    print("=" * 70)

    importance_tests = [
        ("User's email is john@example.com", MemoryType.IDENTITY),
        ("Maybe we should consider using Redis", MemoryType.DECISION),
        ("The critical security fix must be deployed immediately", MemoryType.SOLUTION),
        ("Just chatting about the weather", MemoryType.EPISODIC)
    ]

    for content, mem_type in importance_tests:
        importance = classifier.calculate_importance(content, mem_type)
        print(f"\n📝 '{content[:40]}...'")
        print(f"   Type: {mem_type.value}")
        print(f"   Importance: {importance:.2f} / 1.00")

    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()