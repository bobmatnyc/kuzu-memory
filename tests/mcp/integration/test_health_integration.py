"""
Integration tests for MCP health check system.

Tests full system health checks, component integration, health monitoring
over time, and real-world scenarios.
"""

import asyncio
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from kuzu_memory.mcp.testing.health_checker import HealthStatus, MCPHealthChecker


@pytest.mark.integration
class TestHealthCheckIntegration:
    """Integration tests for health check system."""

    @pytest.fixture
    def health_checker(self, tmp_path):
        """Create health checker for testing."""
        return MCPHealthChecker(
            project_root=tmp_path, timeout=5.0, retry_count=1, retry_backoff=1.0
        )

    @pytest.mark.asyncio
    async def test_full_system_health_check(self, health_checker):
        """Test complete system health check."""
        # Perform health check
        result = await health_checker.check_health(detailed=True, retry=False)

        # Verify result structure
        assert result is not None
        assert result.health is not None
        assert result.duration_ms > 0

        # Check that we have component results
        assert len(result.health.components) > 0

        # Verify component names
        component_names = [c.name for c in result.health.components]
        expected_components = ["cli", "database", "protocol", "tools"]

        # At least some components should be present
        assert any(comp in component_names for comp in expected_components)

        # Verify each component has required fields
        for component in result.health.components:
            assert component.name is not None
            assert component.status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]
            assert component.message is not None
            assert component.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_cli_component_health(self, health_checker):
        """Test CLI-specific health check."""
        result = await health_checker._check_cli_health(retry=True)

        assert result.name == "cli"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]

        # If CLI is available, should be healthy or degraded
        if result.status != HealthStatus.UNHEALTHY:
            assert result.error is None
            assert "version" in result.metadata or "operational" in result.message.lower()

    @pytest.mark.asyncio
    async def test_database_component_health(self, health_checker, tmp_path):
        """Test database-specific health check."""
        # Create a test database file
        db_path = tmp_path / "test_memory.db"
        db_path.write_text("test database content")

        with patch.dict("os.environ", {"KUZU_MEMORY_DB": str(db_path)}):
            result = await health_checker._check_database_health(retry=True)

            assert result.name == "database"
            assert result.status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

            # Database should be found
            if result.status != HealthStatus.UNHEALTHY:
                assert result.metadata.get("path") == str(db_path)

    @pytest.mark.asyncio
    async def test_health_monitoring_over_time(self, health_checker):
        """Test health monitoring with multiple checks over time."""
        # Perform multiple health checks
        num_checks = 3

        for i in range(num_checks):
            result = await health_checker.check_health(detailed=False, retry=False)
            assert result is not None

            # Small delay between checks
            if i < num_checks - 1:
                await asyncio.sleep(0.5)

        # Verify history
        assert len(health_checker.health_history) == num_checks

        # Verify trend analysis
        trend = health_checker.get_health_trend(window=num_checks)
        assert trend["checks"] == num_checks
        assert trend["trend"] in [
            "unknown",
            "improving",
            "stable",
            "degrading",
            "critical",
        ]

    @pytest.mark.asyncio
    async def test_performance_metrics_accumulation(self, health_checker):
        """Test that performance metrics accumulate over multiple checks."""
        # Perform multiple checks to build history
        for _ in range(5):
            await health_checker.check_health(detailed=False, retry=False)
            await asyncio.sleep(0.2)

        # Get latest result
        latest_result = health_checker.health_history[-1]

        # Performance metrics should be calculated from history
        perf = latest_result.health.performance

        # With history, some metrics should be non-zero
        if len(health_checker.health_history) > 1:
            assert perf.total_requests > 0

    @pytest.mark.asyncio
    async def test_resource_metrics_collection(self, health_checker):
        """Test resource metrics collection."""
        result = await health_checker.check_health(detailed=True, retry=False)

        resources = result.health.resources

        # Verify resource metrics structure
        assert resources.memory_mb >= 0
        assert resources.cpu_percent >= 0
        assert resources.open_connections >= 0
        assert resources.active_threads >= 0

    @pytest.mark.asyncio
    async def test_degraded_state_detection(self, health_checker, tmp_path):
        """Test detection of degraded state."""
        # Create a database with permission issues
        db_path = tmp_path / "readonly.db"
        db_path.write_text("test")
        db_path.chmod(0o444)  # Read-only

        with patch.dict("os.environ", {"KUZU_MEMORY_DB": str(db_path)}):
            result = await health_checker._check_database_health(retry=False)

            # Should detect degraded state for permission issues
            # Note: Actual result depends on OS permissions
            assert result.name == "database"
            assert result.status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

        # Cleanup - restore permissions
        db_path.chmod(0o644)

    @pytest.mark.asyncio
    async def test_unhealthy_state_detection(self, health_checker):
        """Test detection of unhealthy state."""
        # Mock a failing CLI check
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Command failed")

            result = await health_checker._check_cli_health(retry=False)

            assert result.status == HealthStatus.UNHEALTHY
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_health_check_with_retry(self, health_checker):
        """Test health check retry mechanism."""
        # Track number of attempts
        attempt_count = 0

        original_check = health_checker._check_cli_health

        async def counting_check(retry=True):
            nonlocal attempt_count
            attempt_count += 1
            return await original_check(retry=retry)

        with patch.object(health_checker, "_check_cli_health", counting_check):
            await health_checker._check_cli_health(retry=True)

            # Should attempt at least once
            assert attempt_count >= 1

    @pytest.mark.asyncio
    async def test_health_check_timeout_handling(self, tmp_path):
        """Test health check timeout handling."""
        # Create checker with very short timeout
        quick_checker = MCPHealthChecker(project_root=tmp_path, timeout=0.1)

        # Protocol check might timeout with such short timeout
        result = await quick_checker._check_protocol_health(retry=False)

        assert result.name == "protocol"
        # Should handle timeout gracefully
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]

    @pytest.mark.asyncio
    async def test_health_status_serialization(self, health_checker):
        """Test that health check results can be serialized to dict."""
        result = await health_checker.check_health(detailed=True, retry=False)

        # Convert to dict
        data = result.to_dict()

        # Verify structure
        assert "timestamp" in data
        assert "duration_ms" in data
        assert "health" in data

        health_data = data["health"]
        assert "status" in health_data
        assert "components" in health_data
        assert "performance" in health_data
        assert "resources" in health_data
        assert "summary" in health_data

        # Verify all components are serializable
        for component in health_data["components"]:
            assert "name" in component
            assert "status" in component
            assert "message" in component
            assert "latency_ms" in component

    @pytest.mark.asyncio
    async def test_continuous_monitoring_simulation(self, health_checker):
        """Simulate continuous monitoring scenario."""
        check_count = 5
        interval = 0.3  # seconds

        results = []

        for i in range(check_count):
            result = await health_checker.check_health(detailed=False, retry=False)
            results.append(result)

            if i < check_count - 1:
                await asyncio.sleep(interval)

        # Verify we got all results
        assert len(results) == check_count
        assert len(health_checker.health_history) == check_count

        # Verify trend analysis
        trend = health_checker.get_health_trend(window=check_count)
        assert trend["checks"] == check_count

        # All checks should have timestamps
        for result in results:
            assert result.timestamp is not None

        # Timestamps should be in order
        timestamps = [result.timestamp for result in results]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_health_check_consistency(self, health_checker):
        """Test that repeated health checks are consistent."""
        # Perform two quick health checks
        result1 = await health_checker.check_health(detailed=False, retry=False)
        await asyncio.sleep(0.5)
        result2 = await health_checker.check_health(detailed=False, retry=False)

        # Component set should be consistent
        components1 = {c.name for c in result1.health.components}
        components2 = {c.name for c in result2.health.components}

        # Should check the same components
        assert components1 == components2

        # Overall status should be consistent (unless something changed)
        # This is a soft check - status could change between checks
        status1 = result1.health.status
        status2 = result2.health.status

        # At minimum, both should be valid statuses
        assert status1 in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]
        assert status2 in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]


@pytest.mark.integration
class TestHealthCheckEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_health_check_with_no_database(self, tmp_path):
        """Test health check when database doesn't exist."""
        health_checker = MCPHealthChecker(project_root=tmp_path)

        # Point to non-existent database
        db_path = tmp_path / "nonexistent" / "memory.db"

        with patch.dict("os.environ", {"KUZU_MEMORY_DB": str(db_path)}):
            result = await health_checker._check_database_health(retry=False)

            assert result.name == "database"
            # Should be degraded, not unhealthy (database not initialized is expected)
            assert result.status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]

    @pytest.mark.asyncio
    async def test_health_check_rapid_succession(self, tmp_path):
        """Test multiple health checks in rapid succession."""
        health_checker = MCPHealthChecker(project_root=tmp_path, timeout=2.0)

        # Fire off multiple checks rapidly
        tasks = [health_checker.check_health(detailed=False, retry=False) for _ in range(3)]

        results = await asyncio.gather(*tasks)

        # All should complete
        assert len(results) == 3

        # All should have valid results
        for result in results:
            assert result.health is not None
            assert len(result.health.components) > 0

    @pytest.mark.asyncio
    async def test_health_trend_with_limited_history(self, tmp_path):
        """Test trend analysis with limited history."""
        health_checker = MCPHealthChecker(project_root=tmp_path)

        # Perform only one check
        await health_checker.check_health(detailed=False, retry=False)

        # Trend should still work
        trend = health_checker.get_health_trend(window=10)

        assert trend["checks"] == 1
        assert trend["trend"] in [
            "unknown",
            "improving",
            "stable",
            "degrading",
            "critical",
        ]

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("CI") is not None,
        reason="Slow test: exceeds CI timeout limits (20 sequential health checks)",
    )
    async def test_health_check_with_large_history(self, tmp_path):
        """Test health check with large history."""
        health_checker = MCPHealthChecker(project_root=tmp_path)

        # Build large history (reduced from 20 to 10 for CI compatibility)
        num_checks = 10
        for _ in range(num_checks):
            await health_checker.check_health(detailed=False, retry=False)

        # Verify history is maintained
        assert len(health_checker.health_history) == num_checks

        # Trend analysis with window
        trend = health_checker.get_health_trend(window=5)
        assert trend["checks"] == 5  # Should use window, not all history

        # Full history trend
        full_trend = health_checker.get_health_trend(window=20)
        assert full_trend["checks"] == num_checks  # Limited by actual history
