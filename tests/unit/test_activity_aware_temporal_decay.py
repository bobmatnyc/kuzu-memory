"""
Tests for activity-aware temporal decay functionality.

Tests the new activity-aware recency calculation that makes recency relative
to project activity instead of absolute time.
"""

from datetime import datetime, timedelta

import pytest

from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.recall.temporal_decay import TemporalDecayEngine


class TestActivityAwareTemporalDecay:
    """Test suite for activity-aware temporal decay calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TemporalDecayEngine()
        self.current_time = datetime(2025, 2, 1, 12, 0, 0)  # Feb 1, 2025

    def test_normal_mode_without_last_activity(self):
        """Test that without project_last_activity, normal absolute time is used."""
        # Memory created 30 days ago
        memory = Memory(
            content="Test memory",
            memory_type=MemoryType.PROCEDURAL,
            created_at=self.current_time - timedelta(days=30),
        )

        # Calculate without activity-aware mode
        score = self.engine.calculate_temporal_score(memory, self.current_time)

        # Should use normal absolute time calculation
        explanation = self.engine.get_decay_explanation(memory, self.current_time)

        assert explanation["activity_aware_mode"] is False
        assert explanation["age_days"] == 30.0
        assert "activity_aware_context" not in explanation
        assert 0.0 < score <= 1.0

    def test_activity_aware_mode_with_project_gap(self):
        """Test activity-aware mode with 1-month project gap."""
        # Scenario:
        # - Project last active: Jan 1, 2025
        # - Resume project: Feb 1, 2025 (1 month gap)
        # - Memory from Dec 25, 2024 (7 days before last activity)

        project_last_activity = datetime(2025, 1, 1, 12, 0, 0)
        memory_created = datetime(2024, 12, 25, 12, 0, 0)

        memory = Memory(
            content="Memory from before gap",
            memory_type=MemoryType.PROCEDURAL,
            created_at=memory_created,
        )

        # Calculate with activity-aware mode
        score_aware = self.engine.calculate_temporal_score(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Calculate without activity-aware mode (for comparison)
        score_absolute = self.engine.calculate_temporal_score(
            memory, self.current_time, project_last_activity=None
        )

        # Get explanation
        explanation = self.engine.get_decay_explanation(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Assertions
        assert explanation["activity_aware_mode"] is True
        assert explanation["age_days"] == 7.0  # Relative to last activity
        assert explanation["activity_aware_context"]["absolute_age_days"] == 38.0
        assert explanation["activity_aware_context"]["relative_age_days"] == 7.0
        assert explanation["activity_aware_context"]["gap_duration_days"] == 31.0

        # Activity-aware score should be HIGHER (memory appears more recent)
        assert score_aware > score_absolute

    def test_recent_memory_after_gap_uses_absolute_time(self):
        """Test that memories created AFTER project resume use absolute time."""
        # Scenario:
        # - Project last active: Jan 1, 2025
        # - Memory created: Jan 25, 2025 (after resume)
        # - Current time: Feb 1, 2025

        project_last_activity = datetime(2025, 1, 1, 12, 0, 0)
        memory_created = datetime(2025, 1, 25, 12, 0, 0)

        memory = Memory(
            content="Recent memory after resume",
            memory_type=MemoryType.WORKING,
            created_at=memory_created,
        )

        # Calculate with activity-aware mode
        score = self.engine.calculate_temporal_score(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        explanation = self.engine.get_decay_explanation(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Should use absolute time (not activity-aware mode)
        assert explanation["activity_aware_mode"] is False
        assert explanation["age_days"] == 7.0  # Days since creation
        assert "activity_aware_context" not in explanation

    def test_mixed_scenario_multiple_memories(self):
        """Test mixed scenario with memories before and after project gap."""
        project_last_activity = datetime(2025, 1, 1, 12, 0, 0)

        # Memory 1: Before gap (should use activity-aware)
        memory1 = Memory(
            content="Old memory before gap",
            memory_type=MemoryType.PROCEDURAL,
            created_at=datetime(2024, 12, 20, 12, 0, 0),  # 12 days before last activity
        )

        # Memory 2: After gap (should use absolute time)
        # Use PROCEDURAL type for fair comparison (WORKING has very fast decay)
        memory2 = Memory(
            content="Recent memory after gap",
            memory_type=MemoryType.PROCEDURAL,
            created_at=datetime(2025, 1, 28, 12, 0, 0),  # 4 days ago
        )

        # Calculate scores
        score1 = self.engine.calculate_temporal_score(
            memory1, self.current_time, project_last_activity=project_last_activity
        )
        score2 = self.engine.calculate_temporal_score(
            memory2, self.current_time, project_last_activity=project_last_activity
        )

        # Get explanations
        exp1 = self.engine.get_decay_explanation(
            memory1, self.current_time, project_last_activity=project_last_activity
        )
        exp2 = self.engine.get_decay_explanation(
            memory2, self.current_time, project_last_activity=project_last_activity
        )

        # Memory 1 assertions (activity-aware)
        assert exp1["activity_aware_mode"] is True
        assert exp1["age_days"] == 12.0  # Relative to last activity
        assert exp1["activity_aware_context"]["absolute_age_days"] == 43.0

        # Memory 2 assertions (absolute time)
        assert exp2["activity_aware_mode"] is False
        assert exp2["age_days"] == 4.0  # Absolute time

        # Recent memory (4 days old) should score higher than older memory (12 days old)
        # Both using PROCEDURAL type for fair comparison
        assert score2 > score1

    def test_get_project_last_activity_helper(self):
        """Test the helper method to get project last activity time."""
        # Create memories with different timestamps
        memories = [
            Memory(
                content="Old memory",
                created_at=datetime(2024, 12, 1, 12, 0, 0),
            ),
            Memory(
                content="Recent memory",
                created_at=datetime(2025, 1, 15, 12, 0, 0),
            ),
            Memory(
                content="Middle memory",
                created_at=datetime(2024, 12, 20, 12, 0, 0),
            ),
        ]

        # Get last activity
        last_activity = TemporalDecayEngine.get_project_last_activity(memories)

        # Should return the most recent created_at
        assert last_activity == datetime(2025, 1, 15, 12, 0, 0)

    def test_get_project_last_activity_empty_list(self):
        """Test helper with empty list."""
        last_activity = TemporalDecayEngine.get_project_last_activity([])
        assert last_activity is None

    def test_get_project_last_activity_with_none_timestamps(self):
        """Test helper with some None created_at timestamps."""
        # Create memories normally (created_at defaults to now)
        # Then manually set one to None to simulate edge case
        memory1 = Memory(content="Memory 1", created_at=datetime(2025, 1, 1, 12, 0, 0))
        memory2 = Memory(content="Memory 2")
        memory2.created_at = None  # Manually set to None after creation
        memory3 = Memory(content="Memory 3", created_at=datetime(2025, 1, 10, 12, 0, 0))

        memories = [memory1, memory2, memory3]

        last_activity = TemporalDecayEngine.get_project_last_activity(memories)

        # Should ignore None timestamps and return most recent valid one
        assert last_activity == datetime(2025, 1, 10, 12, 0, 0)

    def test_backward_compatibility(self):
        """Test that existing code without project_last_activity still works."""
        memory = Memory(
            content="Test memory",
            memory_type=MemoryType.SEMANTIC,
            created_at=self.current_time - timedelta(days=10),
        )

        # Old API (no project_last_activity parameter)
        score1 = self.engine.calculate_temporal_score(memory, self.current_time)

        # New API with None (should behave identically)
        score2 = self.engine.calculate_temporal_score(
            memory, self.current_time, project_last_activity=None
        )

        # Scores should be identical
        assert score1 == score2

    def test_working_memory_fast_decay_with_activity_aware(self):
        """Test that WORKING memory still decays fast even with activity-aware mode."""
        project_last_activity = datetime(2025, 1, 1, 12, 0, 0)

        # WORKING memory from 2 days before last activity
        memory = Memory(
            content="Working memory",
            memory_type=MemoryType.WORKING,
            created_at=datetime(2024, 12, 30, 12, 0, 0),
        )

        score = self.engine.calculate_temporal_score(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        explanation = self.engine.get_decay_explanation(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Should use activity-aware mode
        assert explanation["activity_aware_mode"] is True
        assert explanation["age_days"] == 2.0

        # WORKING memory has 1-day half-life, so 2 days should decay significantly
        # Even with activity-aware mode, decay function still applies
        assert score < 0.5  # Should decay to less than 50%

    def test_semantic_memory_slow_decay_with_activity_aware(self):
        """Test that SEMANTIC memory decays slowly even with long gap."""
        project_last_activity = datetime(2025, 1, 1, 12, 0, 0)

        # SEMANTIC memory from 30 days before last activity
        memory = Memory(
            content="Important fact",
            memory_type=MemoryType.SEMANTIC,
            created_at=datetime(2024, 12, 1, 12, 0, 0),
        )

        score = self.engine.calculate_temporal_score(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        explanation = self.engine.get_decay_explanation(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Should use activity-aware mode
        assert explanation["activity_aware_mode"] is True
        assert explanation["age_days"] == 31.0  # Days before last activity

        # SEMANTIC memory has 365-day half-life and minimum score of 0.8
        # So even after 31 days, should stay very high
        assert score >= 0.8  # Minimum score for SEMANTIC

    def test_get_effective_weight_with_activity_aware(self):
        """Test get_effective_weight with activity-aware mode."""
        project_last_activity = datetime(2025, 1, 1, 12, 0, 0)

        memory = Memory(
            content="Test memory",
            memory_type=MemoryType.PROCEDURAL,
            created_at=datetime(2024, 12, 25, 12, 0, 0),
        )

        # Get effective weight with activity-aware mode
        weight = self.engine.get_effective_weight(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Weight should be base_weight * temporal_score
        base_weight = self.engine.decay_config["base_weight"]
        temporal_score = self.engine.calculate_temporal_score(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        assert weight == base_weight * temporal_score
        assert 0.0 <= weight <= 1.0

    def test_explanation_with_large_gap(self):
        """Test explanation formatting with very large project gap."""
        # 6-month gap
        project_last_activity = datetime(2024, 8, 1, 12, 0, 0)
        memory_created = datetime(2024, 7, 25, 12, 0, 0)

        memory = Memory(
            content="Memory from 6 months ago",
            memory_type=MemoryType.PROCEDURAL,
            created_at=memory_created,
        )

        explanation = self.engine.get_decay_explanation(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Check activity-aware context
        ctx = explanation["activity_aware_context"]
        assert ctx["gap_duration_days"] == pytest.approx(184.0, abs=1.0)  # ~6 months
        assert ctx["absolute_age_days"] == pytest.approx(191.0, abs=1.0)
        assert ctx["relative_age_days"] == pytest.approx(7.0, abs=1.0)
        assert ctx["age_reduction_days"] == pytest.approx(184.0, abs=1.0)

        # Should have human-readable explanation
        assert "days before" in ctx["explanation"]
        assert "instead of absolute time" in ctx["explanation"]

    def test_recent_boost_applies_with_activity_aware(self):
        """Test that recent boost still applies in activity-aware mode."""
        project_last_activity = datetime(2025, 1, 1, 12, 0, 0)

        # Memory created very close to last activity (within 24 hours)
        memory = Memory(
            content="Very recent memory",
            memory_type=MemoryType.WORKING,
            created_at=datetime(2024, 12, 31, 18, 0, 0),  # 18 hours before
        )

        explanation = self.engine.get_decay_explanation(
            memory, self.current_time, project_last_activity=project_last_activity
        )

        # Should be in activity-aware mode
        assert explanation["activity_aware_mode"] is True

        # Should have recent boost applied (within 24 hour threshold)
        assert explanation["recent_boost_applied"] is True
        assert explanation["age_hours"] < 24.0


class TestActivityAwareIntegrationScenarios:
    """Integration tests for real-world activity-aware scenarios."""

    def test_returning_to_old_project_scenario(self):
        """
        Real-world scenario: Developer returns to 3-month-old project.

        Without activity-aware: All memories appear stale (3 months old)
        With activity-aware: Memories scored relative to last activity
        """
        engine = TemporalDecayEngine()

        # Project last worked on 3 months ago
        last_activity = datetime(2024, 11, 1, 12, 0, 0)
        current_time = datetime(2025, 2, 1, 12, 0, 0)

        # Memories from the old project (all same type for fair comparison)
        memories = [
            Memory(
                content="Project architecture decision",
                memory_type=MemoryType.PROCEDURAL,
                created_at=datetime(2024, 10, 1, 12, 0, 0),  # 31 days before last
            ),
            Memory(
                content="Bug fix in authentication service",
                memory_type=MemoryType.PROCEDURAL,
                created_at=datetime(2024, 10, 25, 12, 0, 0),  # 7 days before last
            ),
            Memory(
                content="User dashboard implementation",
                memory_type=MemoryType.PROCEDURAL,
                created_at=datetime(2024, 10, 31, 12, 0, 0),  # 1 day before last
            ),
        ]

        # Calculate scores without activity-aware (old behavior)
        scores_absolute = [
            engine.calculate_temporal_score(m, current_time) for m in memories
        ]

        # Calculate scores with activity-aware (new behavior)
        scores_aware = [
            engine.calculate_temporal_score(
                m, current_time, project_last_activity=last_activity
            )
            for m in memories
        ]

        # All activity-aware scores should be higher (memories appear more recent)
        for abs_score, aware_score in zip(scores_absolute, scores_aware, strict=False):
            assert aware_score > abs_score

        # Most recent memory (1 day before last activity) should rank highest
        # Memories should be ordered by recency relative to last activity
        assert scores_aware[2] > scores_aware[1] > scores_aware[0]

    def test_active_project_scenario(self):
        """
        Scenario: Active project with no gap.

        Activity-aware should behave identically to normal mode.
        """
        engine = TemporalDecayEngine()
        current_time = datetime(2025, 2, 1, 12, 0, 0)

        # Active project - last activity was yesterday
        last_activity = current_time - timedelta(days=1)

        # Recent memories
        memories = [
            Memory(
                content="Recent change",
                memory_type=MemoryType.WORKING,
                created_at=current_time - timedelta(hours=2),
            ),
            Memory(
                content="Yesterday's work",
                memory_type=MemoryType.PROCEDURAL,
                created_at=current_time - timedelta(hours=20),
            ),
        ]

        # For active projects, activity-aware should match absolute scoring
        for memory in memories:
            score_absolute = engine.calculate_temporal_score(memory, current_time)
            score_aware = engine.calculate_temporal_score(
                memory, current_time, project_last_activity=last_activity
            )

            # Scores should be very similar (memory is after last_activity)
            # Use absolute mode for recent memories
            explanation = engine.get_decay_explanation(
                memory, current_time, project_last_activity=last_activity
            )
            assert explanation["activity_aware_mode"] is False
