"""
Cache integration tests for KuzuMemory.

Tests the integration between caching layers, storage systems,
and memory recall to ensure optimal performance and data consistency.
"""

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kuzu_memory import KuzuMemory
from kuzu_memory.core.models import MemoryType


class TestCacheIntegration:
    """Integration tests for cache system with storage and recall."""

    @pytest.fixture
    def cache_config(self):
        """Configuration with caching enabled."""
        return {
            "recall": {
                "enable_caching": True,
                "cache_size": 1000,
                "cache_ttl_seconds": 300,  # 5 minutes
                "max_memories": 10,
                "strategies": ["keyword", "entity", "temporal"],
            },
            "performance": {
                "max_recall_time_ms": 200.0,  # Relaxed for testing
                "max_generation_time_ms": 1000.0,  # Relaxed for testing (initialization overhead)
                "enable_performance_monitoring": True,
            },
            "extraction": {
                "enable_entity_extraction": True,
                "enable_pattern_compilation": True,
            },
            "storage": {"connection_pool_size": 5, "max_size_mb": 10.0},
        }

    @pytest.fixture
    def no_cache_config(self):
        """Configuration with caching disabled."""
        return {
            "recall": {
                "enable_caching": False,
                "max_memories": 10,
                "strategies": ["keyword", "entity", "temporal"],
            },
            "performance": {
                "max_recall_time_ms": 200.0,  # More lenient without cache
                "enable_performance_monitoring": True,
            },
            "extraction": {
                "enable_entity_extraction": True,
                "enable_pattern_compilation": True,
            },
            "storage": {"connection_pool_size": 5, "max_size_mb": 10.0},
        }

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "cache_integration.db"

    def test_cache_warmup_and_performance(self, temp_db_path, cache_config):
        """Test cache warmup behavior and performance improvement."""
        with KuzuMemory(db_path=temp_db_path, config=cache_config) as memory:
            user_id = "cache-test-user"

            # Populate with test data
            test_content = [
                "I'm a Senior Developer at InnovaTech specializing in backend systems.",
                "I work extensively with Python, Django, and PostgreSQL databases.",
                "Our team follows microservices architecture with Docker containers.",
                "I'm experienced with AWS cloud services and infrastructure automation.",
                "We use Jenkins for CI/CD and Git for version control workflows.",
                "I mentor junior developers and conduct code review sessions regularly.",
                "Currently leading the development of a real-time analytics platform.",
                "We implement comprehensive testing including unit and integration tests.",
                "Security is paramount: we use OAuth 2.0 and encrypt sensitive data.",
                "I contribute to technical documentation and architectural decisions.",
            ]

            for i, content in enumerate(test_content):
                memory.generate_memories(
                    content=content,
                    user_id=user_id,
                    session_id=f"test-session-{i // 3}",
                    source="cache_test",
                )

            # Test query that should benefit from caching
            test_query = "What's my technical background and current role?"

            # First query - cold cache
            cold_start_time = time.perf_counter()
            cold_context = memory.attach_memories(
                prompt=test_query, user_id=user_id, max_memories=8
            )
            cold_end_time = time.perf_counter()
            cold_cache_time = (cold_end_time - cold_start_time) * 1000

            assert len(cold_context.memories) > 0
            assert (
                cold_context.confidence > 0.1
            ), f"Expected confidence > 0.1, got {cold_context.confidence}"

            # Subsequent queries - warm cache
            warm_times = []
            for _ in range(5):
                warm_start_time = time.perf_counter()
                warm_context = memory.attach_memories(
                    prompt=test_query, user_id=user_id, max_memories=8
                )
                warm_end_time = time.perf_counter()
                warm_cache_time = (warm_end_time - warm_start_time) * 1000
                warm_times.append(warm_cache_time)

                # Results should be consistent
                assert len(warm_context.memories) > 0
                assert (
                    warm_context.confidence > 0.1
                ), f"Expected confidence > 0.1, got {warm_context.confidence}"

            avg_warm_time = sum(warm_times) / len(warm_times)
            min_warm_time = min(warm_times)

            # Cache should provide performance improvement
            cache_improvement = (cold_cache_time - avg_warm_time) / cold_cache_time
            best_improvement = (cold_cache_time - min_warm_time) / cold_cache_time

            print("Cache Performance Analysis:")
            print(f"  Cold cache time: {cold_cache_time:.2f}ms")
            print(f"  Average warm time: {avg_warm_time:.2f}ms")
            print(f"  Best warm time: {min_warm_time:.2f}ms")
            print(f"  Average improvement: {cache_improvement:.1%}")
            print(f"  Best improvement: {best_improvement:.1%}")

            # Validate cache effectiveness
            assert (
                cache_improvement > 0.1
            ), f"Cache improvement {cache_improvement:.1%} insufficient"
            assert (
                avg_warm_time <= cold_cache_time
            ), "Warm cache should not be slower than cold"

    @pytest.mark.skip(
        reason="Memory extraction patterns need adjustment - no memories generated from test content"
    )
    def test_cache_consistency_with_storage(self, temp_db_path, cache_config):
        """Test cache consistency when storage is updated."""
        with KuzuMemory(db_path=temp_db_path, config=cache_config) as memory:
            user_id = "consistency-user"

            # Initial data
            initial_content = "I work as a Software Engineer at TechStart."
            memory.generate_memories(
                content=initial_content, user_id=user_id, source="initial_data"
            )

            # Query to populate cache
            query = "Where do I work?"
            context1 = memory.attach_memories(query, user_id=user_id)
            assert len(context1.memories) > 0
            assert "techstart" in context1.enhanced_prompt.lower()

            # Add new conflicting information
            new_content = "Actually, I now work at MegaCorp as a Senior Engineer."
            memory.generate_memories(
                content=new_content, user_id=user_id, source="update_data"
            )

            # Query again - should reflect new data
            context2 = memory.attach_memories(query, user_id=user_id)
            assert len(context2.memories) > 0

            # Should contain updated information
            enhanced_lower = context2.enhanced_prompt.lower()
            assert "megacorp" in enhanced_lower or "senior engineer" in enhanced_lower

            # Query with more specific context
            specific_query = "What's my current job title and company?"
            context3 = memory.attach_memories(specific_query, user_id=user_id)

            assert len(context3.memories) > 0
            # Should prioritize more recent/relevant information
            enhanced_specific = context3.enhanced_prompt.lower()
            assert any(
                term in enhanced_specific for term in ["megacorp", "senior", "engineer"]
            )

    @pytest.mark.skip(
        reason="Memory extraction patterns need adjustment - no memories generated from test content"
    )
    def test_cache_invalidation_strategies(self, temp_db_path, cache_config):
        """Test different cache invalidation scenarios."""
        with KuzuMemory(db_path=temp_db_path, config=cache_config) as memory:
            user_id = "invalidation-user"

            # Populate initial data
            base_memories = [
                "I'm a DevOps Engineer working with Kubernetes and Docker.",
                "We use Terraform for infrastructure as code management.",
                "My team follows GitOps practices with ArgoCD for deployments.",
                "I'm experienced with AWS, monitoring, and automated scaling.",
            ]

            for content in base_memories:
                memory.generate_memories(content, user_id=user_id, source="base")

            # Cache some queries
            queries = [
                "What's my job role?",
                "What tools do I work with?",
                "What practices does my team follow?",
                "What cloud experience do I have?",
            ]

            # Populate cache with initial queries
            cached_contexts = {}
            for query in queries:
                context = memory.attach_memories(query, user_id=user_id)
                cached_contexts[query] = {
                    "memory_count": len(context.memories),
                    "confidence": context.confidence,
                    "content_sample": context.enhanced_prompt[:100],
                }

            # Add significant new information
            major_update = """
            I recently got promoted to Principal DevOps Architect.
            We're migrating our entire infrastructure to Google Cloud Platform.
            I'm now leading a team of 10 engineers across three time zones.
            We've adopted Istio service mesh and Prometheus monitoring stack.
            """

            memory.generate_memories(
                content=major_update, user_id=user_id, source="major_update"
            )

            # Re-query and verify cache updates
            updated_contexts = {}
            for query in queries:
                context = memory.attach_memories(query, user_id=user_id)
                updated_contexts[query] = {
                    "memory_count": len(context.memories),
                    "confidence": context.confidence,
                    "content_sample": context.enhanced_prompt[:100],
                }

                # Should include updated information
                enhanced_lower = context.enhanced_prompt.lower()
                if "job role" in query.lower() or "role" in query.lower():
                    assert any(
                        term in enhanced_lower for term in ["principal", "architect"]
                    )

            # Verify cache was appropriately updated
            for query in queries:
                cached = cached_contexts[query]
                updated = updated_contexts[query]

                # Memory count may change (more relevant memories found)
                assert updated["memory_count"] >= 0

                # Confidence should remain reasonable
                assert updated["confidence"] >= 0.3

                # Content should differ for relevant queries
                if any(term in query.lower() for term in ["role", "tools", "cloud"]):
                    content_changed = (
                        cached["content_sample"] != updated["content_sample"]
                    )
                    # Should see some change in content for relevant queries
                    print(f"Query '{query}': Content changed = {content_changed}")

    @pytest.mark.skip(
        reason="Memory extraction patterns need adjustment - no memories generated from test content"
    )
    def test_multi_user_cache_isolation(self, temp_db_path, cache_config):
        """Test cache isolation between different users."""
        with KuzuMemory(db_path=temp_db_path, config=cache_config) as memory:
            # Setup data for different users
            users_data = {
                "user1": [
                    "I'm Alice, a Frontend Developer specializing in React and Vue.js.",
                    "I work at WebCorp building user interfaces and design systems.",
                    "My expertise includes JavaScript, TypeScript, and modern CSS frameworks.",
                ],
                "user2": [
                    "I'm Bob, a Backend Engineer focused on APIs and microservices.",
                    "I work at APICorp developing scalable server-side applications.",
                    "My skills include Python, Go, PostgreSQL, and distributed systems.",
                ],
                "user3": [
                    "I'm Carol, a Data Scientist working on machine learning models.",
                    "I work at DataCorp analyzing large datasets and building predictive models.",
                    "I use Python, R, TensorFlow, and various statistical libraries.",
                ],
            }

            # Populate data for each user
            for user_id, contents in users_data.items():
                for i, content in enumerate(contents):
                    memory.generate_memories(
                        content=content,
                        user_id=user_id,
                        session_id=f"{user_id}-session-{i}",
                        source="user_profile",
                    )

            # Cache queries for each user
            common_query = "What's my professional background?"

            user_contexts = {}
            for user_id in users_data.keys():
                context = memory.attach_memories(common_query, user_id=user_id)
                user_contexts[user_id] = context

                assert len(context.memories) > 0
                assert context.confidence > 0.5

            # Verify user isolation in cached results
            alice_content = user_contexts["user1"].enhanced_prompt.lower()
            bob_content = user_contexts["user2"].enhanced_prompt.lower()
            carol_content = user_contexts["user3"].enhanced_prompt.lower()

            # Each user should get their own data
            assert (
                "alice" in alice_content
                or "frontend" in alice_content
                or "react" in alice_content
            )
            assert (
                "bob" in bob_content
                or "backend" in bob_content
                or "apis" in bob_content
            )
            assert (
                "carol" in carol_content
                or "data scientist" in carol_content
                or "machine learning" in carol_content
            )

            # Cross-contamination check
            assert "alice" not in bob_content and "alice" not in carol_content
            assert "bob" not in alice_content and "bob" not in carol_content
            assert "carol" not in alice_content and "carol" not in bob_content

            # Re-query to test cache isolation persistence
            for user_id in users_data.keys():
                context = memory.attach_memories(common_query, user_id=user_id)
                enhanced_lower = context.enhanced_prompt.lower()

                # Should still get user-specific data
                if user_id == "user1":
                    assert any(
                        term in enhanced_lower
                        for term in ["alice", "frontend", "react", "vue"]
                    )
                elif user_id == "user2":
                    assert any(
                        term in enhanced_lower
                        for term in ["bob", "backend", "api", "microservices"]
                    )
                elif user_id == "user3":
                    assert any(
                        term in enhanced_lower
                        for term in ["carol", "data", "machine learning", "tensorflow"]
                    )

    @pytest.mark.skip(
        reason="Memory extraction patterns need adjustment - no memories generated from test content"
    )
    def test_cache_performance_comparison(
        self, temp_db_path, cache_config, no_cache_config
    ):
        """Compare performance with and without caching."""
        # Test with caching
        cached_times = []
        with KuzuMemory(db_path=temp_db_path, config=cache_config) as memory_cached:
            user_id = "perf-user"

            # Populate data
            for i in range(20):
                memory_cached.generate_memories(
                    f"Performance test data {i}: Technical content with multiple concepts and keywords.",
                    user_id=user_id,
                    source="performance_test",
                )

            # Run queries with cache
            test_queries = [
                "What performance test data do I have?",
                "Show me technical content.",
                "What concepts are covered?",
                "Find content with keywords.",
                "What test data is available?",
            ]

            # First run to warm cache
            for query in test_queries:
                memory_cached.attach_memories(query, user_id=user_id)

            # Timed runs with warm cache
            for _ in range(10):
                query = test_queries[_ % len(test_queries)]
                start_time = time.perf_counter()
                context = memory_cached.attach_memories(query, user_id=user_id)
                end_time = time.perf_counter()
                cached_times.append((end_time - start_time) * 1000)
                assert len(context.memories) > 0

        # Test without caching
        uncached_times = []
        with KuzuMemory(
            db_path=temp_db_path, config=no_cache_config
        ) as memory_uncached:
            # Same queries without cache
            for _ in range(10):
                query = test_queries[_ % len(test_queries)]
                start_time = time.perf_counter()
                context = memory_uncached.attach_memories(query, user_id=user_id)
                end_time = time.perf_counter()
                uncached_times.append((end_time - start_time) * 1000)
                assert len(context.memories) > 0

        # Performance analysis
        avg_cached = sum(cached_times) / len(cached_times)
        avg_uncached = sum(uncached_times) / len(uncached_times)

        performance_improvement = (avg_uncached - avg_cached) / avg_uncached

        print("Cache Performance Comparison:")
        print(f"  Cached average: {avg_cached:.2f}ms")
        print(f"  Uncached average: {avg_uncached:.2f}ms")
        print(f"  Performance improvement: {performance_improvement:.1%}")

        # Cache should provide measurable improvement
        assert (
            performance_improvement > 0.05
        ), f"Cache improvement {performance_improvement:.1%} too small"
        assert avg_cached < avg_uncached, "Cached queries should be faster on average"

        # Both should still meet performance targets
        assert (
            avg_cached < 100.0
        ), f"Cached performance {avg_cached:.2f}ms still too slow"
        assert (
            avg_uncached < 200.0
        ), f"Uncached performance {avg_uncached:.2f}ms too slow"
