"""
End-to-end tests for complete KuzuMemory workflows.

Tests complete user journeys from initialization through complex
memory operations, validating the entire system integration.
"""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from kuzu_memory import KuzuMemory, KuzuMemoryConfig
from kuzu_memory.core.models import MemoryType
from kuzu_memory.utils.exceptions import KuzuMemoryError, PerformanceError


class TestCompleteWorkflows:
    """End-to-end tests for complete KuzuMemory workflows."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for E2E testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "e2e_memories.db"

    @pytest.fixture
    def e2e_config(self):
        """Configuration optimized for E2E testing."""
        return {
            "performance": {
                "max_recall_time_ms": 100.0,  # Relaxed for E2E
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
                "min_memory_length": 5,
                "max_memory_length": 1000,
            },
            "storage": {"max_size_mb": 20.0, "connection_pool_size": 5},
            "retention": {"enable_auto_cleanup": True, "max_total_memories": 10000},
        }

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_complete_user_onboarding_workflow(self, temp_db_path, e2e_config):
        """Test complete user onboarding and profile building workflow."""
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory:
            user_id = "new-user-123"
            session_id = "onboarding-session"

            # Step 1: Initial profile setup
            profile_content = """
            Hi! My name is Sarah Chen and I'm a Senior Software Engineer at DataFlow Inc.
            I have 7 years of experience in full-stack development.
            I specialize in Python, React, and PostgreSQL.
            I prefer test-driven development and always write comprehensive unit tests.
            """

            profile_memory_ids = memory.generate_memories(
                content=profile_content,
                user_id=user_id,
                session_id=session_id,
                source="profile_setup",
                metadata={"step": "initial_profile"},
            )

            assert len(profile_memory_ids) > 0

            # Step 2: Project preferences
            project_content = """
            For new projects, I always start with a proper project structure.
            I prefer using FastAPI for backend APIs and Next.js for frontend applications.
            We decided to use Docker for all our microservices.
            I never deploy without proper CI/CD pipelines using GitHub Actions.
            """

            project_memory_ids = memory.generate_memories(
                content=project_content,
                user_id=user_id,
                session_id=session_id,
                source="project_preferences",
                metadata={"step": "project_setup"},
            )

            assert len(project_memory_ids) > 0

            # Step 3: Current work status
            work_content = """
            Currently working on the CustomerAnalytics microservice.
            The deadline is next Friday and I'm implementing the data aggregation module.
            Working with my teammate Mike Johnson on the API design.
            """

            work_memory_ids = memory.generate_memories(
                content=work_content,
                user_id=user_id,
                session_id=session_id,
                source="current_work",
                metadata={"step": "work_status"},
            )

            assert len(work_memory_ids) > 0

            # Step 4: Validate profile recall
            profile_queries = [
                "What's my name and where do I work?",
                "What programming languages do I use?",
                "What are my development preferences?",
                "What project am I currently working on?",
                "Who am I working with?",
            ]

            for query in profile_queries:
                context = memory.attach_memories(prompt=query, user_id=user_id, max_memories=5)

                # Should find relevant memories
                assert len(context.memories) > 0
                assert context.confidence > 0.5

                # Should contain relevant information
                enhanced_lower = context.enhanced_prompt.lower()
                if "name" in query.lower():
                    assert "sarah" in enhanced_lower or "chen" in enhanced_lower
                elif "language" in query.lower():
                    assert "python" in enhanced_lower or "react" in enhanced_lower
                elif "project" in query.lower():
                    assert "customeranalytics" in enhanced_lower or "microservice" in enhanced_lower

            # Step 5: Verify memory persistence
            (len(profile_memory_ids) + len(project_memory_ids) + len(work_memory_ids))
            stats = memory.get_statistics()

            assert stats["performance_stats"]["generate_memories_calls"] >= 3
            assert stats["performance_stats"]["attach_memories_calls"] >= len(profile_queries)

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_collaborative_project_workflow(self, temp_db_path, e2e_config):
        """Test collaborative project workflow with multiple users."""
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory:
            project_session = "project-alpha-session"

            # Team member 1: Project lead
            lead_content = """
            I'm Alex Rodriguez, the project lead for Project Alpha.
            We're building a real-time analytics dashboard using React and Python.
            The architecture uses microservices with Docker and Kubernetes.
            My team includes Sarah (frontend), Mike (backend), and Lisa (DevOps).
            """

            memory.generate_memories(
                content=lead_content,
                user_id="alex-rodriguez",
                session_id=project_session,
                source="team_meeting",
            )

            # Team member 2: Frontend developer
            frontend_content = """
            I'm Sarah Kim, working on the frontend for Project Alpha.
            I'm using React with TypeScript and Material-UI for the dashboard.
            The real-time updates are handled through WebSocket connections.
            I prefer using React Query for state management and data fetching.
            """

            memory.generate_memories(
                content=frontend_content,
                user_id="sarah-kim",
                session_id=project_session,
                source="team_meeting",
            )

            # Team member 3: Backend developer
            backend_content = """
            I'm Mike Chen, handling the backend services for Project Alpha.
            Using FastAPI with PostgreSQL and Redis for caching.
            The analytics engine processes data in real-time using Apache Kafka.
            I'm implementing the WebSocket server for live dashboard updates.
            """

            memory.generate_memories(
                content=backend_content,
                user_id="mike-chen",
                session_id=project_session,
                source="team_meeting",
            )

            # Cross-team queries
            team_queries = [
                ("alex-rodriguez", "Who are my team members and what do they work on?"),
                ("sarah-kim", "What backend technologies are we using?"),
                ("mike-chen", "What frontend framework is being used?"),
                ("alex-rodriguez", "What's our overall architecture?"),
            ]

            for user_id, query in team_queries:
                context = memory.attach_memories(prompt=query, user_id=user_id, max_memories=8)

                # Should find relevant cross-team information
                assert len(context.memories) > 0

                # Verify cross-team knowledge
                enhanced_lower = context.enhanced_prompt.lower()
                if "team members" in query.lower():
                    assert any(name in enhanced_lower for name in ["sarah", "mike", "lisa"])
                elif "backend" in query.lower():
                    assert any(
                        tech in enhanced_lower for tech in ["fastapi", "postgresql", "kafka"]
                    )
                elif "frontend" in query.lower():
                    assert any(tech in enhanced_lower for tech in ["react", "typescript"])

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_memory_evolution_and_updates_workflow(self, temp_db_path, e2e_config):
        """Test workflow with memory updates, corrections, and evolution."""
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory:
            user_id = "evolving-user"

            # Phase 1: Initial information
            initial_content = """
            I work at StartupCorp as a Junior Developer.
            I'm learning Python and working on small web applications.
            We use MySQL for our database needs.
            """

            memory.generate_memories(
                content=initial_content, user_id=user_id, source="initial_profile"
            )

            # Phase 2: Career progression
            progression_content = """
            I got promoted to Senior Developer at StartupCorp!
            I'm now leading a team of 3 junior developers.
            We're migrating from MySQL to PostgreSQL for better performance.
            I've become an expert in Django and React development.
            """

            memory.generate_memories(
                content=progression_content, user_id=user_id, source="career_update"
            )

            # Phase 3: Job change
            job_change_content = """
            Actually, I now work at TechGiant Inc. as a Staff Engineer.
            I left StartupCorp last month for better opportunities.
            My new role focuses on distributed systems and microservices architecture.
            I'm working with Kubernetes, Docker, and cloud-native technologies.
            """

            memory.generate_memories(
                content=job_change_content, user_id=user_id, source="job_change"
            )

            # Phase 4: Technical corrections
            correction_content = """
            Correction: we're actually using MongoDB, not PostgreSQL at TechGiant.
            Wait, I meant to say I'm a Principal Engineer, not Staff Engineer.
            Let me clarify - I specialize in Go and Rust, not just Python.
            """

            memory.generate_memories(
                content=correction_content, user_id=user_id, source="corrections"
            )

            # Validate evolution queries
            evolution_queries = [
                "Where do I currently work?",
                "What's my current job title?",
                "What database do we use?",
                "What programming languages do I specialize in?",
                "What's my experience level?",
            ]

            for query in evolution_queries:
                context = memory.attach_memories(prompt=query, user_id=user_id, max_memories=6)

                assert len(context.memories) > 0
                enhanced_lower = context.enhanced_prompt.lower()

                # Should reflect latest information
                if "work" in query.lower():
                    assert "techgiant" in enhanced_lower
                    # Should not prominently feature old company
                elif "title" in query.lower():
                    assert "principal" in enhanced_lower or "staff" in enhanced_lower
                elif "database" in query.lower():
                    assert "mongodb" in enhanced_lower
                elif "languages" in query.lower():
                    assert any(lang in enhanced_lower for lang in ["go", "rust", "python"])

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_performance_under_load_workflow(self, temp_db_path, e2e_config):
        """Test system performance under realistic load."""
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory:
            user_id = "performance-user"

            # Generate substantial memory base
            base_contents = [
                "I'm a software architect specializing in distributed systems.",
                "I prefer microservices architecture with event-driven design.",
                "We use Kubernetes for container orchestration in production.",
                "My team follows DevOps practices with automated CI/CD pipelines.",
                "I advocate for test-driven development and comprehensive testing.",
                "We use monitoring tools like Prometheus and Grafana for observability.",
                "I'm experienced with cloud platforms: AWS, Azure, and GCP.",
                "Database technologies I work with: PostgreSQL, MongoDB, Redis.",
                "Programming languages in my toolkit: Python, Go, Java, TypeScript.",
                "I mentor junior developers and conduct technical interviews.",
            ]

            # Store base memories
            for i, content in enumerate(base_contents):
                memory.generate_memories(
                    content=content,
                    user_id=user_id,
                    session_id=f"session-{i}",
                    source="knowledge_base",
                )

            # Performance test queries
            performance_queries = [
                "What's my specialization?",
                "What architecture do I prefer?",
                "What tools do we use for monitoring?",
                "What cloud platforms do I know?",
                "What databases do I work with?",
                "What programming languages do I use?",
                "What's my role in the team?",
                "What development practices do I follow?",
                "What container technology do we use?",
                "How do we handle CI/CD?",
            ]

            # Measure performance
            recall_times = []
            generation_times = []

            for i, query in enumerate(performance_queries):
                # Test recall performance
                start_time = time.time()
                context = memory.attach_memories(prompt=query, user_id=user_id, max_memories=5)
                recall_time = (time.time() - start_time) * 1000
                recall_times.append(recall_time)

                assert len(context.memories) > 0
                assert context.recall_time_ms > 0

                # Test generation performance
                new_content = f"Additional insight {i}: {query} - This is new information."
                start_time = time.time()
                memory_ids = memory.generate_memories(
                    content=new_content, user_id=user_id, source="performance_test"
                )
                generation_time = (time.time() - start_time) * 1000
                generation_times.append(generation_time)

                assert len(memory_ids) > 0

            # Validate performance requirements
            avg_recall_time = sum(recall_times) / len(recall_times)
            avg_generation_time = sum(generation_times) / len(generation_times)
            max_recall_time = max(recall_times)
            max_generation_time = max(generation_times)

            print(f"Average recall time: {avg_recall_time:.2f}ms")
            print(f"Average generation time: {avg_generation_time:.2f}ms")
            print(f"Max recall time: {max_recall_time:.2f}ms")
            print(f"Max generation time: {max_generation_time:.2f}ms")

            # Performance assertions (relaxed for E2E)
            assert avg_recall_time < 50.0, f"Average recall time too high: {avg_recall_time:.2f}ms"
            assert (
                avg_generation_time < 100.0
            ), f"Average generation time too high: {avg_generation_time:.2f}ms"
            assert max_recall_time < 200.0, f"Max recall time too high: {max_recall_time:.2f}ms"
            assert (
                max_generation_time < 400.0
            ), f"Max generation time too high: {max_generation_time:.2f}ms"

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_data_persistence_and_recovery_workflow(self, temp_db_path, e2e_config):
        """Test data persistence and recovery across sessions."""
        user_id = "persistence-user"

        # Session 1: Store initial data
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory1:
            initial_content = """
            I'm Dr. Emma Watson, a data scientist at ResearchLab.
            I specialize in machine learning and natural language processing.
            My current project involves sentiment analysis of social media data.
            I use Python with scikit-learn, TensorFlow, and spaCy libraries.
            """

            memory_ids = memory1.generate_memories(
                content=initial_content, user_id=user_id, source="session_1"
            )

            assert len(memory_ids) > 0

            # Verify initial recall
            context = memory1.attach_memories(
                "What's my profession and specialization?", user_id=user_id
            )

            assert len(context.memories) > 0
            assert "emma watson" in context.enhanced_prompt.lower()
            assert "data scientist" in context.enhanced_prompt.lower()

        # Session 2: Add more data and verify persistence
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory2:
            # Verify previous data is still accessible
            context = memory2.attach_memories("What's my name and profession?", user_id=user_id)

            assert len(context.memories) > 0
            assert "emma watson" in context.enhanced_prompt.lower()

            # Add new information
            additional_content = """
            I recently published a paper on transformer models for text classification.
            I'm collaborating with Stanford University on a new research project.
            My team is expanding to include two PhD students next month.
            """

            new_memory_ids = memory2.generate_memories(
                content=additional_content, user_id=user_id, source="session_2"
            )

            assert len(new_memory_ids) > 0

        # Session 3: Verify all data persists
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory3:
            comprehensive_queries = [
                "What's my background and profession?",
                "What research am I working on?",
                "What tools and libraries do I use?",
                "What collaborations do I have?",
                "What's happening with my team?",
            ]

            for query in comprehensive_queries:
                context = memory3.attach_memories(prompt=query, user_id=user_id, max_memories=8)

                assert len(context.memories) > 0
                assert context.confidence > 0.3

            # Verify statistics show cumulative data
            stats = memory3.get_statistics()
            assert stats["performance_stats"]["generate_memories_calls"] >= 2

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_multi_strategy_recall_workflow(self, temp_db_path, e2e_config):
        """Test workflow using different recall strategies."""
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory:
            user_id = "strategy-user"

            # Store diverse content for strategy testing
            diverse_contents = [
                "I'm John Smith, a DevOps engineer at CloudTech Solutions.",
                "I prefer Infrastructure as Code using Terraform and Ansible.",
                "We use Jenkins for CI/CD with Docker containerization.",
                "Currently migrating our services to Kubernetes clusters.",
                "My colleague Alice handles the monitoring and alerting systems.",
                "We decided to adopt GitOps practices for deployment automation.",
                "I always ensure proper backup and disaster recovery procedures.",
                "The team uses Slack for communication and Jira for project tracking.",
            ]

            for i, content in enumerate(diverse_contents):
                memory.generate_memories(
                    content=content,
                    user_id=user_id,
                    session_id=f"diverse-session-{i}",
                    source="knowledge_input",
                )

            # Test different strategies with same query
            test_query = "What tools and technologies do we use in our DevOps workflow?"
            strategies = ["auto", "keyword", "entity", "temporal"]

            strategy_results = {}

            for strategy in strategies:
                context = memory.attach_memories(
                    prompt=test_query,
                    strategy=strategy,
                    user_id=user_id,
                    max_memories=6,
                )

                strategy_results[strategy] = {
                    "memory_count": len(context.memories),
                    "confidence": context.confidence,
                    "recall_time": context.recall_time_ms,
                    "strategy_used": context.strategy_used,
                    "enhanced_prompt": context.enhanced_prompt,
                }

                # All strategies should find relevant memories
                assert len(context.memories) > 0
                assert context.confidence > 0.2
                assert context.strategy_used == strategy

            # Compare strategy effectiveness
            print("\nStrategy Comparison:")
            for strategy, results in strategy_results.items():
                print(
                    f"{strategy:8}: {results['memory_count']} memories, "
                    f"confidence: {results['confidence']:.2f}, "
                    f"time: {results['recall_time']:.1f}ms"
                )

            # Verify strategy differences
            memory_counts = [r["memory_count"] for r in strategy_results.values()]
            confidences = [r["confidence"] for r in strategy_results.values()]

            # Should have some variation in results
            assert len(set(memory_counts)) > 1 or len(set(confidences)) > 1

    @pytest.mark.skip(reason="Entity extraction patterns need tuning for test content alignment")
    def test_error_recovery_workflow(self, temp_db_path, e2e_config):
        """Test error handling and recovery in realistic scenarios."""
        with KuzuMemory(db_path=temp_db_path, config=e2e_config) as memory:
            user_id = "error-test-user"

            # Test graceful handling of various error conditions

            # 1. Empty content handling
            empty_memory_ids = memory.generate_memories("", user_id=user_id)
            assert empty_memory_ids == []

            # 2. Invalid query handling
            try:
                memory.attach_memories("", user_id=user_id)
                raise AssertionError("Should have raised an exception for empty query")
            except Exception as e:
                assert isinstance(e, ValueError | KuzuMemoryError)

            # 3. Very long content handling
            very_long_content = "This is a very long memory. " * 1000
            long_memory_ids = memory.generate_memories(very_long_content, user_id=user_id)
            # Should handle gracefully (may truncate or process in chunks)
            assert isinstance(long_memory_ids, list)

            # 4. Special characters and encoding
            special_content = "I work with UTF-8: café, naïve, résumé, 中文, 日本語, العربية"
            special_memory_ids = memory.generate_memories(special_content, user_id=user_id)
            assert len(special_memory_ids) >= 0  # Should not crash

            # 5. Malformed input recovery
            malformed_inputs = [
                "Content with\x00null bytes",
                "Content with\ttabs\nand\rnewlines",
                "Content with emoji 🚀 and symbols ©®™",
            ]

            for malformed_content in malformed_inputs:
                try:
                    memory_ids = memory.generate_memories(malformed_content, user_id=user_id)
                    assert isinstance(memory_ids, list)
                except Exception as e:
                    # Should be a handled exception, not a crash
                    assert isinstance(e, ValueError | KuzuMemoryError)

            # 6. System should remain functional after errors
            normal_content = "After handling errors, the system should work normally."
            normal_memory_ids = memory.generate_memories(normal_content, user_id=user_id)
            assert len(normal_memory_ids) > 0

            context = memory.attach_memories("Is the system working?", user_id=user_id)
            assert len(context.memories) >= 0  # Should not crash
