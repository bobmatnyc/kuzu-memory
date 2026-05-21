#!/usr/bin/env python3
"""
Comprehensive functionality test for KuzuMemory.

Tests core memory operations, recall functionality, and Auggie integration
with real-world scenarios.
"""

import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Import KuzuMemory components
try:
    from kuzu_memory import KuzuMemory
    from kuzu_memory.integrations.auggie import AuggieIntegration

    print("✅ Successfully imported KuzuMemory components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure KuzuMemory is properly installed: pip install -e .")
    sys.exit(1)


def test_basic_memory_operations():
    """Test basic memory storage and retrieval."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("\n🧪 Testing Basic Memory Operations")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_memories.db"

        try:
            with KuzuMemory(db_path=db_path) as memory:
                user_id = "test-user"

                # Test 1: Store memories
                print("📝 Storing test memories...")
                test_memories = [
                    "My name is Alice Johnson and I work at TechCorp as a Senior Python Developer.",
                    "I prefer FastAPI for backend APIs and React for frontend applications.",
                    "We decided to use PostgreSQL as our main database with Redis for caching.",
                    "I always write comprehensive unit tests using pytest before deploying code.",
                    "Currently working on a microservices architecture using Docker and Kubernetes.",
                ]

                stored_memory_ids = []
                for i, content in enumerate(test_memories):
                    memory_ids = memory.generate_memories(
                        content=content,
                        user_id=user_id,
                        session_id=f"test-session-{i}",
                        source="functionality_test",
                    )
                    stored_memory_ids.extend(memory_ids)
                    print(f"  ✓ Stored: {content[:50]}... ({len(memory_ids)} memories)")

                print(f"📊 Total memories stored: {len(stored_memory_ids)}")

                # Test 2: Recall memories
                print("\n🔍 Testing memory recall...")
                test_queries = [
                    "What's my name and where do I work?",
                    "What technologies do I prefer?",
                    "What database are we using?",
                    "How do I test my code?",
                    "What architecture am I working on?",
                ]

                recall_results = []
                for query in test_queries:
                    start_time = time.time()
                    context = memory.attach_memories(prompt=query, user_id=user_id, max_memories=5)
                    recall_time = (time.time() - start_time) * 1000

                    recall_results.append(
                        {
                            "query": query,
                            "memories_found": len(context.memories),
                            "confidence": context.confidence,
                            "recall_time_ms": recall_time,
                            "strategy": context.strategy_used,
                        }
                    )

                    print(f"  🔍 Query: {query}")
                    print(
                        f"     Memories: {len(context.memories)}, Confidence: {context.confidence:.2f}"
                    )
                    print(f"     Time: {recall_time:.1f}ms, Strategy: {context.strategy_used}")

                    # Show top memory
                    if context.memories:
                        top_memory = context.memories[0]
                        print(f"     Top: {top_memory.content[:60]}...")

                # Test 3: Performance validation
                print("\n⚡ Performance Analysis:")
                avg_recall_time = sum(r["recall_time_ms"] for r in recall_results) / len(
                    recall_results
                )
                max_recall_time = max(r["recall_time_ms"] for r in recall_results)

                print(f"  Average recall time: {avg_recall_time:.1f}ms")
                print(f"  Max recall time: {max_recall_time:.1f}ms")
                print("  Target: <10ms average, <20ms max")

                # Performance assertions
                if avg_recall_time < 10.0:
                    print("  ✅ Average recall time meets target")
                else:
                    print("  ⚠️  Average recall time exceeds target")

                if max_recall_time < 20.0:
                    print("  ✅ Max recall time meets target")
                else:
                    print("  ⚠️  Max recall time exceeds target")

                # Test 4: Memory statistics
                memory.get_statistics()
                print("\n📊 Memory Statistics:")
                print(f"  Total memories: {len(stored_memory_ids)}")
                print(f"  Recall operations: {len(test_queries)}")
                print(
                    f"  Average confidence: {sum(r['confidence'] for r in recall_results) / len(recall_results):.2f}"
                )

                return True

        except Exception as e:
            print(f"❌ Error in basic memory operations: {e}")
            return False


def test_auggie_integration():
    """Test Auggie integration functionality."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("\n🤖 Testing Auggie Integration")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "auggie_test_memories.db"

        try:
            with KuzuMemory(db_path=db_path) as memory:
                # Initialize Auggie integration
                auggie = AuggieIntegration(
                    memory, config={"max_context_memories": 8, "enable_learning": True}
                )

                print("✅ Auggie integration initialized")
                print(f"📋 Default rules loaded: {len(auggie.rule_engine.rules)}")

                user_id = "auggie-test-user"

                # Test 1: Build user profile
                print("\n📝 Building user profile...")
                profile_data = [
                    "My name is Sarah Chen and I'm a Senior Software Engineer at DataFlow Inc.",
                    "I prefer Python for backend development and React for frontend applications.",
                    "I always write comprehensive unit tests before deploying to production.",
                    "We decided to use PostgreSQL as our main database with Redis for caching.",
                    "Currently working on the CustomerAnalytics microservice using FastAPI.",
                ]

                for data in profile_data:
                    memory.generate_memories(data, user_id=user_id)
                    print(f"  ✓ Stored: {data[:60]}...")

                # Test 2: Prompt enhancement
                print("\n🚀 Testing prompt enhancement...")
                test_prompts = [
                    "How do I write a Python function?",
                    "What's the best way to handle database connections?",
                    "Help me debug this authentication issue",
                    "What testing framework should I use?",
                    "How do I deploy a microservice?",
                ]

                enhancement_results = []
                for prompt in test_prompts:
                    start_time = time.time()
                    enhancement = auggie.enhance_prompt(prompt, user_id)
                    enhancement_time = (time.time() - start_time) * 1000

                    original_length = len(enhancement["original_prompt"])
                    enhanced_length = len(enhancement["enhanced_prompt"])
                    enhancement_ratio = enhanced_length / original_length

                    executed_rules = enhancement["rule_modifications"].get("executed_rules", [])

                    enhancement_results.append(
                        {
                            "prompt": prompt,
                            "enhancement_ratio": enhancement_ratio,
                            "rules_applied": len(executed_rules),
                            "enhancement_time_ms": enhancement_time,
                            "context_summary": enhancement["context_summary"],
                        }
                    )

                    print(f"  🔍 Prompt: {prompt}")
                    print(f"     Enhancement: {enhancement_ratio:.1f}x longer")
                    print(f"     Rules applied: {len(executed_rules)}")
                    print(f"     Context: {enhancement['context_summary']}")
                    print(f"     Time: {enhancement_time:.1f}ms")

                # Test 3: Response learning
                print("\n🧠 Testing response learning...")
                learning_scenarios = [
                    {
                        "prompt": "What database should I use for my project?",
                        "ai_response": "For your project, I'd recommend PostgreSQL since you mentioned you're already using it at DataFlow Inc.",
                        "user_feedback": None,
                    },
                    {
                        "prompt": "How do I test React components?",
                        "ai_response": "You can use Jest and React Testing Library for testing React components.",
                        "user_feedback": "Actually, I prefer using Cypress for end-to-end testing of React components.",
                    },
                    {
                        "prompt": "What's the best Python web framework?",
                        "ai_response": "Django is a great choice for Python web development.",
                        "user_feedback": "Correction: I prefer FastAPI for API development because it's faster and has better async support.",
                    },
                ]

                learning_results = []
                for scenario in learning_scenarios:
                    learning_result = auggie.learn_from_interaction(
                        prompt=scenario["prompt"],
                        ai_response=scenario["ai_response"],
                        user_feedback=scenario["user_feedback"],
                        user_id=user_id,
                    )

                    learning_results.append(learning_result)

                    print(f"  💬 Prompt: {scenario['prompt']}")
                    print(f"     Quality score: {learning_result.get('quality_score', 0):.2f}")
                    print(
                        f"     Memories created: {len(learning_result.get('extracted_memories', []))}"
                    )

                    if scenario["user_feedback"]:
                        corrections = learning_result.get("corrections", [])
                        print(f"     Corrections found: {len(corrections)}")

                # Test 4: Custom rule creation
                print("\n⚙️ Testing custom rule creation...")
                custom_rule_id = auggie.create_custom_rule(
                    name="Prioritize FastAPI for Sarah",
                    description="When Sarah asks about Python web frameworks, prioritize FastAPI",
                    rule_type="context_enhancement",
                    conditions={
                        "user_id": user_id,
                        "prompt_category": "coding",
                        "prompt": {"contains": "framework"},
                    },
                    actions={
                        "add_context": "User prefers FastAPI for API development due to performance and async support",
                        "memory_types": ["preference"],
                    },
                    priority="high",
                )

                print(f"  ✅ Created custom rule: {custom_rule_id}")

                # Test the custom rule
                test_prompt = "What Python web framework should I use for my new API?"
                enhancement = auggie.enhance_prompt(test_prompt, user_id)

                executed_rules = enhancement["rule_modifications"].get("executed_rules", [])
                custom_rule_applied = any(
                    rule["rule_id"] == custom_rule_id for rule in executed_rules
                )

                print("  🔍 Testing custom rule:")
                print(f"     Prompt: {test_prompt}")
                print(f"     Custom rule applied: {'✅' if custom_rule_applied else '❌'}")

                # Test 5: Integration statistics
                print("\n📊 Integration statistics:")
                stats = auggie.get_integration_statistics()

                print(f"  Prompts enhanced: {stats['integration']['prompts_enhanced']}")
                print(f"  Responses learned: {stats['integration']['responses_learned']}")
                print(f"  Rules triggered: {stats['integration']['rules_triggered']}")
                print(f"  Memories created: {stats['integration']['memories_created']}")

                # Performance analysis
                avg_enhancement_time = sum(
                    r["enhancement_time_ms"] for r in enhancement_results
                ) / len(enhancement_results)
                avg_enhancement_ratio = sum(
                    r["enhancement_ratio"] for r in enhancement_results
                ) / len(enhancement_results)

                print("\n⚡ Auggie Performance:")
                print(f"  Average enhancement time: {avg_enhancement_time:.1f}ms")
                print(f"  Average enhancement ratio: {avg_enhancement_ratio:.1f}x")
                print(
                    f"  Rules per enhancement: {sum(r['rules_applied'] for r in enhancement_results) / len(enhancement_results):.1f}"
                )

                return True

        except Exception as e:
            print(f"❌ Error in Auggie integration: {e}")
            import traceback

            traceback.print_exc()
            return False


def test_memory_persistence():
    """Test memory persistence across sessions."""
    import pytest

    pytest.skip("Standalone test file - functionality tested in proper test suite")
    print("\n💾 Testing Memory Persistence")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "persistence_test.db"
        user_id = "persistence-user"

        try:
            # Session 1: Store memories
            print("📝 Session 1: Storing memories...")
            with KuzuMemory(db_path=db_path) as memory1:
                test_content = "I'm a data scientist specializing in machine learning and Python."
                memory_ids = memory1.generate_memories(test_content, user_id=user_id)
                print(f"  ✓ Stored {len(memory_ids)} memories")

                # Verify immediate recall
                context = memory1.attach_memories("What's my specialization?", user_id=user_id)
                print(f"  ✓ Immediate recall: {len(context.memories)} memories found")

            # Session 2: Verify persistence
            print("\n🔍 Session 2: Verifying persistence...")
            with KuzuMemory(db_path=db_path) as memory2:
                context = memory2.attach_memories("What's my specialization?", user_id=user_id)

                if len(context.memories) > 0:
                    print(f"  ✅ Persistence verified: {len(context.memories)} memories recalled")
                    print(f"     Content: {context.memories[0].content[:60]}...")
                    return True
                else:
                    print("  ❌ Persistence failed: No memories found")
                    return False

        except Exception as e:
            print(f"❌ Error in persistence test: {e}")
            return False


def main():
    """Run comprehensive functionality tests."""
    print("🧪 KuzuMemory Comprehensive Functionality Test")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_results = []

    # Run all tests
    tests = [
        ("Basic Memory Operations", test_basic_memory_operations),
        ("Auggie Integration", test_auggie_integration),
        ("Memory Persistence", test_memory_persistence),
    ]

    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"🧪 Running: {test_name}")
        print(f"{'=' * 60}")

        start_time = time.time()
        try:
            success = test_func()
            duration = time.time() - start_time

            test_results.append({"name": test_name, "success": success, "duration": duration})

            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{status} - {test_name} ({duration:.1f}s)")

        except Exception as e:
            duration = time.time() - start_time
            test_results.append(
                {
                    "name": test_name,
                    "success": False,
                    "duration": duration,
                    "error": str(e),
                }
            )
            print(f"\n❌ FAILED - {test_name} ({duration:.1f}s)")
            print(f"Error: {e}")

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 TEST SUMMARY")
    print(f"{'=' * 60}")

    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["success"])
    total_time = sum(r["duration"] for r in test_results)

    print(f"🎯 Results: {passed_tests}/{total_tests} tests passed")
    print(f"⏱️  Total time: {total_time:.1f}s")

    for result in test_results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {result['name']}: {result['duration']:.1f}s")
        if not result["success"] and "error" in result:
            print(f"     Error: {result['error']}")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! KuzuMemory is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
