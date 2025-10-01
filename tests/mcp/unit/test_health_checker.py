"""
Unit tests for MCP health checker.

Tests component health checks, performance metrics, resource metrics,
and health status determination logic.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kuzu_memory.mcp.testing.health_checker import (
    ComponentHealth,
    HealthCheckResult,
    HealthStatus,
    MCPHealthChecker,
    PerformanceMetrics,
    ResourceMetrics,
    SystemHealth,
)


class TestDataClasses:
    """Test data class functionality."""

    def test_performance_metrics_to_dict(self):
        """Test PerformanceMetrics.to_dict()."""
        metrics = PerformanceMetrics(
            latency_p50_ms=10.5,
            latency_p95_ms=50.2,
            latency_p99_ms=100.8,
            throughput_ops_per_sec=100.0,
            error_rate=0.05,
            total_requests=1000,
            failed_requests=50,
            average_latency_ms=15.3,
        )

        result = metrics.to_dict()

        assert result["latency_p50_ms"] == 10.5
        assert result["latency_p95_ms"] == 50.2
        assert result["latency_p99_ms"] == 100.8
        assert result["throughput_ops_per_sec"] == 100.0
        assert result["error_rate"] == 0.05
        assert result["total_requests"] == 1000
        assert result["failed_requests"] == 50
        assert result["average_latency_ms"] == 15.3

    def test_resource_metrics_to_dict(self):
        """Test ResourceMetrics.to_dict()."""
        metrics = ResourceMetrics(
            memory_mb=150.5, cpu_percent=25.3, open_connections=5, active_threads=10
        )

        result = metrics.to_dict()

        assert result["memory_mb"] == 150.5
        assert result["cpu_percent"] == 25.3
        assert result["open_connections"] == 5
        assert result["active_threads"] == 10

    def test_component_health_to_dict(self):
        """Test ComponentHealth.to_dict()."""
        component = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="Component is healthy",
            latency_ms=10.5,
            metadata={"test": "data"},
        )

        result = component.to_dict()

        assert result["name"] == "test_component"
        assert result["status"] == "healthy"
        assert result["message"] == "Component is healthy"
        assert result["latency_ms"] == 10.5
        assert result["error"] is None
        assert result["metadata"] == {"test": "data"}

    def test_component_health_with_error(self):
        """Test ComponentHealth with error."""
        component = ComponentHealth(
            name="failing_component",
            status=HealthStatus.UNHEALTHY,
            message="Component failed",
            error="Connection timeout",
        )

        result = component.to_dict()

        assert result["status"] == "unhealthy"
        assert result["error"] == "Connection timeout"

    def test_system_health_counts(self):
        """Test SystemHealth component counts."""
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("comp2", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("comp3", HealthStatus.DEGRADED, "Slow"),
            ComponentHealth("comp4", HealthStatus.UNHEALTHY, "Failed"),
        ]

        system = SystemHealth(status=HealthStatus.DEGRADED, components=components)

        assert system.healthy_count == 2
        assert system.degraded_count == 1
        assert system.unhealthy_count == 1

    def test_system_health_to_dict(self):
        """Test SystemHealth.to_dict()."""
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("comp2", HealthStatus.DEGRADED, "Slow"),
        ]

        performance = PerformanceMetrics(average_latency_ms=25.0)
        resources = ResourceMetrics(memory_mb=100.0)

        system = SystemHealth(
            status=HealthStatus.DEGRADED,
            components=components,
            performance=performance,
            resources=resources,
        )

        result = system.to_dict()

        assert result["status"] == "degraded"
        assert "timestamp" in result
        assert len(result["components"]) == 2
        assert result["performance"]["average_latency_ms"] == 25.0
        assert result["resources"]["memory_mb"] == 100.0
        assert result["summary"]["healthy"] == 1
        assert result["summary"]["degraded"] == 1
        assert result["summary"]["total"] == 2

    def test_health_check_result_to_dict(self):
        """Test HealthCheckResult.to_dict()."""
        system = SystemHealth(
            status=HealthStatus.HEALTHY,
            components=[ComponentHealth("comp1", HealthStatus.HEALTHY, "OK")],
        )

        result = HealthCheckResult(health=system, duration_ms=150.5)

        data = result.to_dict()

        assert "timestamp" in data
        assert data["duration_ms"] == 150.5
        assert data["health"]["status"] == "healthy"


class TestMCPHealthChecker:
    """Test MCPHealthChecker functionality."""

    @pytest.fixture
    def health_checker(self, tmp_path):
        """Create health checker instance."""
        return MCPHealthChecker(
            project_root=tmp_path, timeout=2.0, retry_count=2, retry_backoff=1.2
        )

    def test_initialization(self, health_checker, tmp_path):
        """Test health checker initialization."""
        assert health_checker.project_root == tmp_path
        assert health_checker.timeout == 2.0
        assert health_checker.retry_count == 2
        assert health_checker.retry_backoff == 1.2
        assert health_checker.health_history == []

    def test_latency_to_status_healthy(self, health_checker):
        """Test latency to status conversion - healthy."""
        status = health_checker._latency_to_status(30.0)
        assert status == HealthStatus.HEALTHY

    def test_latency_to_status_degraded(self, health_checker):
        """Test latency to status conversion - degraded."""
        status = health_checker._latency_to_status(75.0)
        assert status == HealthStatus.DEGRADED

    def test_latency_to_status_unhealthy(self, health_checker):
        """Test latency to status conversion - unhealthy."""
        status = health_checker._latency_to_status(250.0)
        assert status == HealthStatus.UNHEALTHY

    def test_determine_overall_status_all_healthy(self, health_checker):
        """Test overall status determination - all healthy."""
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("comp2", HealthStatus.HEALTHY, "OK"),
        ]

        performance = PerformanceMetrics(error_rate=0.001)
        resources = ResourceMetrics(memory_mb=50.0, cpu_percent=20.0)

        status = health_checker._determine_overall_status(
            components, performance, resources
        )

        assert status == HealthStatus.HEALTHY

    def test_determine_overall_status_has_unhealthy(self, health_checker):
        """Test overall status determination - has unhealthy component."""
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("comp2", HealthStatus.UNHEALTHY, "Failed"),
        ]

        performance = PerformanceMetrics(error_rate=0.001)
        resources = ResourceMetrics(memory_mb=50.0)

        status = health_checker._determine_overall_status(
            components, performance, resources
        )

        assert status == HealthStatus.UNHEALTHY

    def test_determine_overall_status_high_error_rate(self, health_checker):
        """Test overall status determination - high error rate."""
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY, "OK"),
        ]

        performance = PerformanceMetrics(error_rate=0.15)  # 15% error rate
        resources = ResourceMetrics(memory_mb=50.0)

        status = health_checker._determine_overall_status(
            components, performance, resources
        )

        assert status == HealthStatus.UNHEALTHY

    def test_determine_overall_status_high_memory(self, health_checker):
        """Test overall status determination - high memory usage."""
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY, "OK"),
        ]

        performance = PerformanceMetrics(error_rate=0.001)
        resources = ResourceMetrics(memory_mb=600.0)  # Over threshold

        status = health_checker._determine_overall_status(
            components, performance, resources
        )

        assert status == HealthStatus.UNHEALTHY

    def test_determine_overall_status_degraded(self, health_checker):
        """Test overall status determination - degraded."""
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("comp2", HealthStatus.DEGRADED, "Slow"),
        ]

        performance = PerformanceMetrics(error_rate=0.001)
        resources = ResourceMetrics(memory_mb=50.0)

        status = health_checker._determine_overall_status(
            components, performance, resources
        )

        assert status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_check_cli_health_success(self, health_checker):
        """Test CLI health check - success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="kuzu-memory 1.1.7\n", stderr=""
            )

            result = await health_checker._check_cli_health(retry=False)

            assert result.name == "cli"
            assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            assert "1.1.7" in result.message or "operational" in result.message.lower()
            assert result.error is None

    @pytest.mark.asyncio
    async def test_check_cli_health_failure(self, health_checker):
        """Test CLI health check - failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("Command not found")

            result = await health_checker._check_cli_health(retry=False)

            assert result.name == "cli"
            assert result.status == HealthStatus.UNHEALTHY
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_check_database_health_exists(self, health_checker, tmp_path):
        """Test database health check - database exists."""
        # Create a mock database file
        db_path = tmp_path / "memory.db"
        db_path.write_text("mock database")

        with patch.dict("os.environ", {"KUZU_MEMORY_DB": str(db_path)}):
            result = await health_checker._check_database_health(retry=False)

            assert result.name == "database"
            assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            assert result.metadata["path"] == str(db_path)

    @pytest.mark.asyncio
    async def test_check_database_health_not_exists(self, health_checker, tmp_path):
        """Test database health check - database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        with patch.dict("os.environ", {"KUZU_MEMORY_DB": str(db_path)}):
            result = await health_checker._check_database_health(retry=False)

            assert result.name == "database"
            assert result.status == HealthStatus.DEGRADED
            assert "not initialized" in result.message.lower()

    @pytest.mark.asyncio
    async def test_collect_performance_metrics_empty_history(self, health_checker):
        """Test performance metrics collection - empty history."""
        metrics = await health_checker._collect_performance_metrics()

        assert metrics.total_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.error_rate == 0.0

    @pytest.mark.asyncio
    async def test_collect_performance_metrics_with_history(self, health_checker):
        """Test performance metrics collection - with history."""
        # Add some mock history
        for i in range(5):
            components = [
                ComponentHealth(
                    "comp1",
                    HealthStatus.HEALTHY if i < 4 else HealthStatus.UNHEALTHY,
                    "OK",
                    latency_ms=10.0 + i * 5,
                )
            ]
            system = SystemHealth(status=HealthStatus.HEALTHY, components=components)
            result = HealthCheckResult(health=system, duration_ms=100.0)
            health_checker.health_history.append(result)

        metrics = await health_checker._collect_performance_metrics()

        assert metrics.total_requests == 5
        assert metrics.failed_requests == 1
        assert metrics.error_rate == 0.2  # 1/5
        assert metrics.average_latency_ms > 0

    @pytest.mark.asyncio
    async def test_collect_resource_metrics_no_psutil(self, health_checker):
        """Test resource metrics collection - psutil not available."""
        with patch("kuzu_memory.mcp.testing.health_checker.psutil", None):
            metrics = await health_checker._collect_resource_metrics()

            # Should return empty metrics without errors
            assert metrics.memory_mb == 0.0
            assert metrics.cpu_percent == 0.0

    @pytest.mark.asyncio
    async def test_collect_resource_metrics_with_psutil(self, health_checker):
        """Test resource metrics collection - with psutil."""
        mock_process = MagicMock()
        mock_process.memory_info.return_value = MagicMock(
            rss=100 * 1024 * 1024
        )  # 100 MB
        mock_process.cpu_percent.return_value = 25.5
        mock_process.connections.return_value = [1, 2, 3]  # 3 connections
        mock_process.num_threads.return_value = 5

        with patch("kuzu_memory.mcp.testing.health_checker.psutil") as mock_psutil:
            mock_psutil.Process.return_value = mock_process

            metrics = await health_checker._collect_resource_metrics()

            assert metrics.memory_mb == 100.0
            assert metrics.cpu_percent == 25.5
            assert metrics.open_connections == 3
            assert metrics.active_threads == 5

    def test_get_health_trend_no_history(self, health_checker):
        """Test health trend analysis - no history."""
        trend = health_checker.get_health_trend()

        assert trend["trend"] == "unknown"
        assert trend["checks"] == 0

    def test_get_health_trend_improving(self, health_checker):
        """Test health trend analysis - improving."""
        # Add all healthy checks
        for _ in range(5):
            system = SystemHealth(
                status=HealthStatus.HEALTHY,
                components=[ComponentHealth("comp1", HealthStatus.HEALTHY, "OK")],
            )
            result = HealthCheckResult(health=system, duration_ms=100.0)
            health_checker.health_history.append(result)

        trend = health_checker.get_health_trend(window=5)

        assert trend["trend"] in ["improving", "stable"]
        assert trend["checks"] == 5
        assert trend["healthy"] == 5

    def test_get_health_trend_degrading(self, health_checker):
        """Test health trend analysis - degrading."""
        # Add mix of healthy and degraded checks
        for i in range(5):
            status = HealthStatus.HEALTHY if i < 3 else HealthStatus.DEGRADED
            system = SystemHealth(
                status=status,
                components=[ComponentHealth("comp1", status, "Message")],
            )
            result = HealthCheckResult(health=system, duration_ms=100.0)
            health_checker.health_history.append(result)

        trend = health_checker.get_health_trend(window=5)

        assert trend["trend"] == "degrading"
        assert trend["healthy"] == 3
        assert trend["degraded"] == 2

    def test_get_health_trend_critical(self, health_checker):
        """Test health trend analysis - critical."""
        # Add mostly unhealthy checks
        for i in range(5):
            status = HealthStatus.UNHEALTHY if i < 4 else HealthStatus.HEALTHY
            system = SystemHealth(
                status=status,
                components=[ComponentHealth("comp1", status, "Message")],
            )
            result = HealthCheckResult(health=system, duration_ms=100.0)
            health_checker.health_history.append(result)

        trend = health_checker.get_health_trend(window=5)

        assert trend["trend"] == "critical"
        assert trend["unhealthy"] == 4
        assert trend["health_rate"] < 0.5


class TestHealthCheckIntegration:
    """Integration tests for health check system."""

    @pytest.mark.asyncio
    async def test_full_health_check_structure(self, tmp_path):
        """Test full health check returns correct structure."""
        health_checker = MCPHealthChecker(project_root=tmp_path, timeout=1.0)

        # Mock components to avoid actual server startup
        with (
            patch.object(health_checker, "_check_protocol_health") as mock_protocol,
            patch.object(health_checker, "_check_tools_health") as mock_tools,
        ):

            mock_protocol.return_value = ComponentHealth(
                "protocol", HealthStatus.HEALTHY, "OK", latency_ms=10.0
            )
            mock_tools.return_value = ComponentHealth(
                "tools", HealthStatus.HEALTHY, "OK", latency_ms=15.0
            )

            result = await health_checker.check_health(detailed=True, retry=False)

            # Verify result structure
            assert isinstance(result, HealthCheckResult)
            assert isinstance(result.health, SystemHealth)
            assert result.duration_ms > 0
            assert "timestamp" in result.to_dict()

            # Verify components (at least CLI and database should be checked)
            assert len(result.health.components) >= 2
            component_names = [c.name for c in result.health.components]
            assert "cli" in component_names or "database" in component_names

            # Verify performance and resource metrics
            assert isinstance(result.health.performance, PerformanceMetrics)
            assert isinstance(result.health.resources, ResourceMetrics)

    @pytest.mark.asyncio
    async def test_health_check_adds_to_history(self, tmp_path):
        """Test that health checks are added to history."""
        health_checker = MCPHealthChecker(project_root=tmp_path, timeout=1.0)

        initial_count = len(health_checker.health_history)

        # Mock to avoid actual checks
        with (
            patch.object(health_checker, "_check_protocol_health") as mock_protocol,
            patch.object(health_checker, "_check_tools_health") as mock_tools,
        ):

            mock_protocol.return_value = ComponentHealth(
                "protocol", HealthStatus.HEALTHY, "OK"
            )
            mock_tools.return_value = ComponentHealth(
                "tools", HealthStatus.HEALTHY, "OK"
            )

            await health_checker.check_health(detailed=True, retry=False)

            assert len(health_checker.health_history) == initial_count + 1
