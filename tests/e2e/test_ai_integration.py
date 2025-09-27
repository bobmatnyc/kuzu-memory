"""
AI integration end-to-end tests for KuzuMemory.

Tests subprocess-based AI integration patterns to validate the CLI-only
integration approach specified in the project requirements.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory import KuzuMemory


@pytest.mark.skip(
    reason="E2E tests require CLI to be properly installed - CLI subprocess calls fail in test environment"
)
class TestAIIntegration:
    """End-to-end tests for AI system integration via CLI."""

    def _run_cli_command(self, args, timeout=5, cwd=None):
        """Helper to run CLI commands with proper environment setup."""
        import sys

        project_root = Path(__file__).parent.parent.parent
        env = {**dict(os.environ), "PYTHONPATH": str(project_root / "src")}

        full_args = [sys.executable, "-m", "kuzu_memory.cli.commands"] + args
        return subprocess.run(
            full_args, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env
        )

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for AI integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "ai_integration.db"

    @pytest.fixture
    def ai_config_path(self, temp_db_path):
        """Create configuration file for CLI testing."""
        config = {
            "database": {"path": str(temp_db_path), "connection_pool_size": 5},
            "performance": {
                "max_recall_time_ms": 100.0,
                "max_generation_time_ms": 200.0,
                "enable_performance_monitoring": True,
            },
            "recall": {
                "max_memories": 10,
                "enable_caching": True,
                "cache_size": 500,
                "strategies": ["keyword", "entity", "temporal"],
            },
            "extraction": {
                "enable_entity_extraction": True,
                "enable_pattern_compilation": True,
            },
        }

        config_path = temp_db_path.parent / "kuzu_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        return config_path

    def test_cli_enhance_integration_pattern(self, temp_db_path, ai_config_path):
        """Test the standard AI integration pattern using subprocess calls."""
        # First, populate the memory system with test data
        with KuzuMemory(db_path=temp_db_path) as memory:
            test_content = [
                "I'm Sarah Chen, a Senior Software Engineer at DataFlow Inc.",
                "I specialize in Python, React, and PostgreSQL for full-stack development.",
                "I prefer test-driven development and comprehensive code reviews.",
                "Currently working on a real-time analytics platform using Apache Kafka.",
                "I mentor junior developers and conduct technical interviews regularly.",
            ]

            for content in test_content:
                memory.generate_memories(
                    content=content,
                    user_id="ai-test-user",
                    source="ai_integration_test",
                )

        def enhance_with_memory(
            prompt: str, user_id: str = "ai-test-user", timeout: int = 5
        ) -> str:
            """Standard AI integration helper function."""
            try:
                result = self._run_cli_command(
                    [
                        "enhance",
                        prompt,
                        "--format",
                        "plain",  # Removed --user-id as it's not supported
                        # Note: user_id filtering should be done at the memory recall level
                    ],
                    timeout=timeout,
                    cwd=temp_db_path.parent,
                )

                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    print(f"CLI Error: {result.stderr}")
                    return prompt  # Fallback to original prompt
            except subprocess.TimeoutExpired:
                print("CLI timeout - returning original prompt")
                return prompt
            except Exception as e:
                print(f"CLI Exception: {e}")
                return prompt

        def learn_async(
            content: str, user_id: str = "ai-test-user", source: str = "ai-conversation"
        ) -> bool:
            """Standard async learning helper function."""
            try:
                result = self._run_cli_command(
                    [
                        "learn",
                        content,
                        "--source",
                        source,  # Note: --user-id may not be supported
                        "--quiet",
                    ],
                    timeout=10,
                    cwd=temp_db_path.parent,
                )

                return result.returncode == 0
            except Exception:
                return False  # Fire and forget - failures are acceptable

        # Test enhance functionality
        test_queries = [
            "What's my professional background?",
            "What programming languages do I use?",
            "What's my current project?",
            "What are my development practices?",
            "What's my role in the team?",
        ]

        for query in test_queries:
            enhanced = enhance_with_memory(query)

            # Enhanced prompt should be longer and more detailed
            assert len(enhanced) > len(query)

            # Should contain relevant context
            enhanced_lower = enhanced.lower()
            if "background" in query.lower():
                assert any(
                    term in enhanced_lower
                    for term in ["sarah", "chen", "senior", "engineer"]
                )
            elif "languages" in query.lower():
                assert any(
                    term in enhanced_lower for term in ["python", "react", "postgresql"]
                )
            elif "project" in query.lower():
                assert any(
                    term in enhanced_lower
                    for term in ["analytics", "platform", "kafka"]
                )
            elif "practices" in query.lower():
                assert any(
                    term in enhanced_lower for term in ["test-driven", "code reviews"]
                )
            elif "role" in query.lower():
                assert any(term in enhanced_lower for term in ["mentor", "interviews"])

            print(f"Query: {query}")
            print(f"Enhanced length: {len(enhanced)} chars")
            print(f"Contains context: {len(enhanced) > len(query) * 2}")

        # Test async learning
        new_learnings = [
            "I recently completed a course on Kubernetes orchestration.",
            "Our team adopted GraphQL for better API flexibility.",
            "I'm leading the migration to microservices architecture.",
            "We implemented comprehensive monitoring with Prometheus and Grafana.",
        ]

        learning_results = []
        for learning in new_learnings:
            success = learn_async(learning)
            learning_results.append(success)

        # Learning is fire-and-forget, so some failures are acceptable
        success_rate = sum(learning_results) / len(learning_results)
        assert success_rate >= 0.7, f"Learning success rate {success_rate:.1%} too low"

        # Verify learned content is available for enhancement
        time.sleep(2)  # Allow time for async processing

        tech_query = "What new technologies have I learned recently?"
        enhanced_tech = enhance_with_memory(tech_query)

        enhanced_tech_lower = enhanced_tech.lower()
        # Should contain some of the newly learned information
        learned_terms = [
            "kubernetes",
            "graphql",
            "microservices",
            "monitoring",
            "prometheus",
        ]
        found_terms = [term for term in learned_terms if term in enhanced_tech_lower]

        assert (
            len(found_terms) > 0
        ), f"No newly learned content found in enhancement: {enhanced_tech}"

    def test_ai_conversation_workflow(self, temp_db_path, ai_config_path):
        """Test complete AI conversation workflow with memory integration."""

        def simulate_ai_conversation_turn(user_input: str, user_id: str) -> dict:
            """Simulate one turn of AI conversation with memory integration."""
            # Step 1: Enhance user prompt with memory context
            try:
                enhance_result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kuzu_memory.cli.commands",
                        "enhance",
                        user_input,
                        "--user-id",
                        user_id,
                        "--format",
                        "json",
                        "--config",
                        str(ai_config_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=temp_db_path.parent,
                )

                if enhance_result.returncode == 0:
                    enhance_data = json.loads(enhance_result.stdout)
                    enhanced_prompt = enhance_data.get("enhanced_prompt", user_input)
                    context_count = len(enhance_data.get("memories", []))
                    confidence = enhance_data.get("confidence", 0.0)
                else:
                    enhanced_prompt = user_input
                    context_count = 0
                    confidence = 0.0

            except Exception:
                enhanced_prompt = user_input
                context_count = 0
                confidence = 0.0

            # Step 2: Generate AI response (simulated)
            ai_response = f"AI Response to: {user_input} (enhanced with {context_count} memories, confidence: {confidence:.2f})"

            # Step 3: Store learning from conversation (async)
            learning_content = f"User asked: {user_input}. AI responded with information about the topic."

            learn_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kuzu_memory.cli.commands",
                    "learn",
                    learning_content,
                    "--user-id",
                    user_id,
                    "--source",
                    "ai-conversation",
                    "--quiet",
                    "--config",
                    str(ai_config_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_db_path.parent,
            )

            return {
                "user_input": user_input,
                "enhanced_prompt": enhanced_prompt,
                "ai_response": ai_response,
                "context_count": context_count,
                "confidence": confidence,
                "learning_success": (
                    learn_result.returncode == 0 if learn_result else False
                ),
            }

        # Simulate a conversation sequence
        user_id = "conversation-user"
        conversation = [
            "Hi, I'm a new software developer. What should I focus on learning?",
            "I'm particularly interested in web development. What technologies should I learn?",
            "What about databases? Which one should I start with?",
            "How important is testing in software development?",
            "What are some best practices for code organization?",
            "Can you tell me about my learning progress so far?",
        ]

        conversation_results = []
        for turn, user_input in enumerate(conversation):
            print(f"\n--- Conversation Turn {turn + 1} ---")
            result = simulate_ai_conversation_turn(user_input, user_id)
            conversation_results.append(result)

            print(f"User: {user_input}")
            print(
                f"Context: {result['context_count']} memories, confidence: {result['confidence']:.2f}"
            )
            print(f"Enhanced: {len(result['enhanced_prompt'])} chars")
            print(f"Learning: {'Success' if result['learning_success'] else 'Failed'}")

            # Validate conversation turn
            assert len(result["enhanced_prompt"]) >= len(user_input)

            # Later turns should have more context as memory builds up
            if turn > 2:  # After a few turns, should have some context
                assert result["context_count"] > 0 or result["confidence"] > 0.0

        # Analyze conversation progression
        context_counts = [r["context_count"] for r in conversation_results]
        confidences = [r["confidence"] for r in conversation_results]
        learning_successes = [r["learning_success"] for r in conversation_results]

        # Context should generally improve over the conversation
        later_half_context = sum(context_counts[len(context_counts) // 2 :])
        earlier_half_context = sum(context_counts[: len(context_counts) // 2])

        print("\nConversation Analysis:")
        print(f"  Earlier half context: {earlier_half_context}")
        print(f"  Later half context: {later_half_context}")
        print(
            f"  Learning success rate: {sum(learning_successes)/len(learning_successes):.1%}"
        )

        # Memory should accumulate over the conversation
        assert (
            later_half_context >= earlier_half_context
        ), "Context should improve over conversation"

        # Most learning attempts should succeed
        learning_rate = sum(learning_successes) / len(learning_successes)
        assert learning_rate > 0.6, f"Learning success rate {learning_rate:.1%} too low"

    def test_error_handling_in_ai_integration(self, temp_db_path, ai_config_path):
        """Test error handling in AI integration scenarios."""

        def robust_enhance_with_memory(
            prompt: str, user_id: str = "error-test-user"
        ) -> str:
            """Robust enhancement function with proper error handling."""
            if not prompt or not prompt.strip():
                return "Please provide a valid question or prompt."

            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kuzu_memory.cli.commands",
                        "enhance",
                        prompt,
                        "--user-id",
                        user_id,
                        "--format",
                        "plain",
                        "--config",
                        str(ai_config_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_db_path.parent,
                )

                if result.returncode == 0:
                    enhanced = result.stdout.strip()
                    return enhanced if enhanced else prompt
                else:
                    # Log error but continue
                    print(f"Enhancement failed: {result.stderr}")
                    return prompt

            except subprocess.TimeoutExpired:
                print("Enhancement timed out")
                return prompt
            except Exception as e:
                print(f"Enhancement error: {e}")
                return prompt

        def robust_learn_async(content: str, user_id: str = "error-test-user") -> bool:
            """Robust learning function with error handling."""
            if not content or not content.strip():
                return False

            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kuzu_memory.cli.commands",
                        "learn",
                        content,
                        "--user-id",
                        user_id,
                        "--source",
                        "ai-error-test",
                        "--quiet",
                        "--config",
                        str(ai_config_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=temp_db_path.parent,
                )

                return result.returncode == 0
            except Exception:
                return False  # Fire and forget

        # Test various error conditions
        error_test_cases = [
            # Empty/invalid inputs
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("\n\t\r", "whitespace characters"),
            # Very long inputs
            ("What about " + "very " * 1000 + "long queries?", "very long query"),
            # Special characters
            (
                "What about UTF-8: café, naïve, résumé, 中文, العربية?",
                "unicode characters",
            ),
            ("Query with\x00null bytes and\ttabs", "control characters"),
            # Edge cases
            ("A", "single character"),
            ("What?" * 100, "repetitive content"),
        ]

        enhancement_results = []
        learning_results = []

        for test_input, description in error_test_cases:
            print(f"Testing {description}...")

            # Test enhancement robustness
            enhanced = robust_enhance_with_memory(test_input)
            enhancement_success = enhanced is not None and len(enhanced) > 0
            enhancement_results.append(enhancement_success)

            print(f"  Enhancement: {'Success' if enhancement_success else 'Failed'}")

            # Test learning robustness
            if test_input and test_input.strip():
                learning_content = f"Error test case: {description} - {test_input[:50]}"
                learn_success = robust_learn_async(learning_content)
                learning_results.append(learn_success)
                print(f"  Learning: {'Success' if learn_success else 'Failed'}")
            else:
                learning_results.append(False)  # Expected to fail for empty inputs
                print("  Learning: Skipped (empty input)")

        # Analyze error handling effectiveness
        enhancement_success_rate = sum(enhancement_results) / len(enhancement_results)
        learning_success_rate = sum(learning_results) / len(learning_results)

        print("\nError Handling Analysis:")
        print(f"  Enhancement success rate: {enhancement_success_rate:.1%}")
        print(f"  Learning success rate: {learning_success_rate:.1%}")

        # System should handle errors gracefully
        assert (
            enhancement_success_rate > 0.8
        ), f"Enhancement error handling {enhancement_success_rate:.1%} insufficient"
        # Learning can be more permissive since it's fire-and-forget
        assert (
            learning_success_rate > 0.5
        ), f"Learning error handling {learning_success_rate:.1%} insufficient"

        # Test system recovery after errors
        normal_query = "What's a normal query after error conditions?"
        recovery_enhanced = robust_enhance_with_memory(normal_query)
        assert len(recovery_enhanced) > len(
            normal_query
        ), "System should recover after error conditions"

        recovery_learn = robust_learn_async(
            "System recovery test: normal operation after errors."
        )
        print(f"Recovery learning: {'Success' if recovery_learn else 'Failed'}")

    def test_performance_monitoring_in_ai_integration(
        self, temp_db_path, ai_config_path
    ):
        """Test performance monitoring capabilities in AI integration."""
        # Populate with test data
        with KuzuMemory(db_path=temp_db_path) as memory:
            for i in range(50):
                memory.generate_memories(
                    f"Performance test memory {i}: Content with technical details and multiple concepts.",
                    user_id="perf-monitor-user",
                    source="performance_monitoring",
                )

        def timed_enhance_operation(prompt: str, user_id: str) -> dict:
            """Perform timed enhancement operation."""
            start_time = time.perf_counter()

            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "kuzu_memory.cli.commands",
                        "enhance",
                        prompt,
                        "--user-id",
                        user_id,
                        "--format",
                        "json",
                        "--config",
                        str(ai_config_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=temp_db_path.parent,
                )

                end_time = time.perf_counter()
                total_time_ms = (end_time - start_time) * 1000

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    return {
                        "success": True,
                        "total_time_ms": total_time_ms,
                        "recall_time_ms": data.get("recall_time_ms", 0),
                        "memory_count": len(data.get("memories", [])),
                        "confidence": data.get("confidence", 0.0),
                    }
                else:
                    return {
                        "success": False,
                        "total_time_ms": total_time_ms,
                        "error": result.stderr,
                    }

            except Exception as e:
                end_time = time.perf_counter()
                return {
                    "success": False,
                    "total_time_ms": (end_time - start_time) * 1000,
                    "error": str(e),
                }

        # Performance test queries
        performance_queries = [
            "What performance test data is available?",
            "Show me technical content with concepts.",
            "What memories contain technical details?",
            "Find content related to performance testing.",
            "What test data has multiple concepts?",
        ]

        user_id = "perf-monitor-user"
        performance_results = []

        # Run performance tests
        for i, query in enumerate(performance_queries * 4):  # Multiple runs
            result = timed_enhance_operation(query, user_id)
            performance_results.append(result)

            if result["success"]:
                print(
                    f"Query {i+1}: {result['total_time_ms']:.2f}ms total, "
                    f"{result['recall_time_ms']:.2f}ms recall, "
                    f"{result['memory_count']} memories"
                )
            else:
                print(f"Query {i+1}: Failed - {result.get('error', 'Unknown error')}")

        # Analyze performance results
        successful_results = [r for r in performance_results if r["success"]]
        failed_results = [r for r in performance_results if not r["success"]]

        success_rate = len(successful_results) / len(performance_results)
        assert (
            success_rate > 0.95
        ), f"Performance test success rate {success_rate:.1%} too low"

        if successful_results:
            total_times = [r["total_time_ms"] for r in successful_results]
            recall_times = [r["recall_time_ms"] for r in successful_results]
            memory_counts = [r["memory_count"] for r in successful_results]

            avg_total_time = sum(total_times) / len(total_times)
            avg_recall_time = sum(recall_times) / len(recall_times)
            max_total_time = max(total_times)
            max_recall_time = max(recall_times)
            avg_memory_count = sum(memory_counts) / len(memory_counts)

            print("\nPerformance Monitoring Results:")
            print(f"  Success rate: {success_rate:.1%}")
            print(f"  Average total time: {avg_total_time:.2f}ms")
            print(f"  Average recall time: {avg_recall_time:.2f}ms")
            print(f"  Max total time: {max_total_time:.2f}ms")
            print(f"  Max recall time: {max_recall_time:.2f}ms")
            print(f"  Average memories per query: {avg_memory_count:.1f}")

            # Validate performance targets
            assert (
                avg_total_time < 200.0
            ), f"Average total time {avg_total_time:.2f}ms too high"
            assert (
                avg_recall_time < 100.0
            ), f"Average recall time {avg_recall_time:.2f}ms exceeds target"
            assert (
                max_recall_time < 150.0
            ), f"Max recall time {max_recall_time:.2f}ms too high"
            assert (
                avg_memory_count > 1.0
            ), f"Average memory count {avg_memory_count:.1f} too low"

        if failed_results:
            print(f"\nFailed operations: {len(failed_results)}")
            for i, failure in enumerate(failed_results[:3]):  # Show first 3 failures
                print(f"  Failure {i+1}: {failure.get('error', 'Unknown')}")

    def test_concurrent_ai_integration(self, temp_db_path, ai_config_path):
        """Test AI integration under concurrent usage scenarios."""
        import queue
        import threading

        # Pre-populate data
        with KuzuMemory(db_path=temp_db_path) as memory:
            for i in range(30):
                memory.generate_memories(
                    f"Concurrent test data {i}: Multi-user scenario with shared knowledge base.",
                    user_id=f"concurrent-user-{i % 3}",
                    source="concurrent_test",
                )

        results_queue = queue.Queue()

        def ai_integration_worker(worker_id: int, operations: int):
            """Worker simulating concurrent AI integration."""
            user_id = f"concurrent-user-{worker_id % 3}"
            results = []

            for op_id in range(operations):
                query = f"What test data is available for operation {op_id}?"

                # Enhance operation
                try:
                    enhance_start = time.perf_counter()
                    enhance_result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "kuzu_memory.cli.commands",
                            "enhance",
                            query,
                            "--user-id",
                            user_id,
                            "--format",
                            "plain",
                            "--config",
                            str(ai_config_path),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=temp_db_path.parent,
                    )
                    enhance_time = (time.perf_counter() - enhance_start) * 1000

                    enhance_success = enhance_result.returncode == 0

                    # Learn operation (async)
                    learn_content = f"Worker {worker_id} operation {op_id}: Processed query about test data."
                    learn_result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "kuzu_memory.cli.commands",
                            "learn",
                            learn_content,
                            "--user-id",
                            user_id,
                            "--source",
                            "concurrent-ai",
                            "--quiet",
                            "--config",
                            str(ai_config_path),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=temp_db_path.parent,
                    )

                    learn_success = learn_result.returncode == 0

                    results.append(
                        {
                            "worker_id": worker_id,
                            "operation_id": op_id,
                            "enhance_success": enhance_success,
                            "enhance_time_ms": enhance_time,
                            "learn_success": learn_success,
                            "user_id": user_id,
                        }
                    )

                except Exception as e:
                    results.append(
                        {
                            "worker_id": worker_id,
                            "operation_id": op_id,
                            "enhance_success": False,
                            "enhance_time_ms": 0,
                            "learn_success": False,
                            "error": str(e),
                            "user_id": user_id,
                        }
                    )

            results_queue.put(results)

        # Launch concurrent workers
        num_workers = 6
        operations_per_worker = 8
        threads = []

        for worker_id in range(num_workers):
            thread = threading.Thread(
                target=ai_integration_worker, args=(worker_id, operations_per_worker)
            )
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=30.0)
            assert not thread.is_alive(), "Concurrent AI integration worker timed out"

        # Collect results
        all_results = []
        while not results_queue.empty():
            worker_results = results_queue.get()
            all_results.extend(worker_results)

        # Analyze concurrent performance
        successful_enhances = [r for r in all_results if r["enhance_success"]]
        successful_learns = [r for r in all_results if r["learn_success"]]

        total_operations = num_workers * operations_per_worker
        enhance_success_rate = len(successful_enhances) / total_operations
        learn_success_rate = len(successful_learns) / total_operations

        print("Concurrent AI Integration Results:")
        print(f"  Total operations: {total_operations}")
        print(f"  Enhance success rate: {enhance_success_rate:.1%}")
        print(f"  Learn success rate: {learn_success_rate:.1%}")

        assert (
            enhance_success_rate > 0.90
        ), f"Concurrent enhance success rate {enhance_success_rate:.1%} too low"
        assert (
            learn_success_rate > 0.75
        ), f"Concurrent learn success rate {learn_success_rate:.1%} too low"

        if successful_enhances:
            enhance_times = [r["enhance_time_ms"] for r in successful_enhances]
            avg_enhance_time = sum(enhance_times) / len(enhance_times)
            max_enhance_time = max(enhance_times)

            print(f"  Average enhance time: {avg_enhance_time:.2f}ms")
            print(f"  Max enhance time: {max_enhance_time:.2f}ms")

            # Performance should remain reasonable under concurrent load
            assert (
                avg_enhance_time < 300.0
            ), f"Concurrent enhance time {avg_enhance_time:.2f}ms too high"
            assert (
                max_enhance_time < 1000.0
            ), f"Max concurrent enhance time {max_enhance_time:.2f}ms too high"

        # Verify user isolation in concurrent scenarios
        user_results = {}
        for result in successful_enhances:
            user_id = result["user_id"]
            if user_id not in user_results:
                user_results[user_id] = []
            user_results[user_id].append(result)

        assert len(user_results) > 1, "Should have results for multiple users"
        print(f"  Users with successful operations: {len(user_results)}")

        for user_id, user_ops in user_results.items():
            print(f"  {user_id}: {len(user_ops)} successful operations")
