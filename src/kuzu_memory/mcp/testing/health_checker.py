"""
MCP Health Check System.

Comprehensive health monitoring for MCP server components including CLI,
database, protocol, and tool execution with performance metrics and resource tracking.
"""

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None  # Optional dependency  # type: ignore[assignment]  # Intentional None assignment for optional dependency

from .connection_tester import MCPConnectionTester

logger = logging.getLogger(__name__)


# Health check thresholds
HEALTH_THRESHOLDS: dict[str, dict[str, float]] = {
    "latency_ms": {
        "healthy": 200,  # <200ms = healthy (allows subprocess overhead)
        "degraded": 500,  # 200-500ms = degraded (slower but acceptable)
        "unhealthy": 1000,  # >1000ms = unhealthy (unacceptably slow)
    },
    "error_rate": {
        "healthy": 0.01,  # <1% = healthy
        "degraded": 0.05,  # 1-5% = degraded
        "unhealthy": 0.10,  # >10% = unhealthy
    },
    "memory_mb": {
        "healthy": 100,
        "degraded": 200,
        "unhealthy": 500,
    },
    "cpu_percent": {
        "healthy": 50,
        "degraded": 75,
        "unhealthy": 90,
    },
}


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"  # All components operational
    DEGRADED = "degraded"  # Some components slow or partial failures
    UNHEALTHY = "unhealthy"  # Critical components failed


@dataclass
class PerformanceMetrics:
    """Performance metrics for health monitoring."""

    latency_p50_ms: float = 0.0  # Median latency
    latency_p95_ms: float = 0.0  # 95th percentile
    latency_p99_ms: float = 0.0  # 99th percentile
    throughput_ops_per_sec: float = 0.0  # Operations per second
    error_rate: float = 0.0  # Percentage of failed operations
    total_requests: int = 0
    failed_requests: int = 0
    average_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "throughput_ops_per_sec": self.throughput_ops_per_sec,
            "error_rate": self.error_rate,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "average_latency_ms": self.average_latency_ms,
        }


@dataclass
class ResourceMetrics:
    """Resource usage metrics."""

    memory_mb: float = 0.0  # Memory usage in MB
    cpu_percent: float = 0.0  # CPU usage percentage
    open_connections: int = 0  # Number of open connections
    active_threads: int = 0  # Number of active threads

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "open_connections": self.open_connections,
            "active_threads": self.active_threads,
        }


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: str
    latency_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class SystemHealth:
    """Overall system health status."""

    status: HealthStatus
    components: list[ComponentHealth] = field(default_factory=list)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    resources: ResourceMetrics = field(default_factory=ResourceMetrics)
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def healthy_count(self) -> int:
        """Count of healthy components."""
        return sum(1 for c in self.components if c.status == HealthStatus.HEALTHY)

    @property
    def degraded_count(self) -> int:
        """Count of degraded components."""
        return sum(1 for c in self.components if c.status == HealthStatus.DEGRADED)

    @property
    def unhealthy_count(self) -> int:
        """Count of unhealthy components."""
        return sum(1 for c in self.components if c.status == HealthStatus.UNHEALTHY)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "components": [c.to_dict() for c in self.components],
            "performance": self.performance.to_dict(),
            "resources": self.resources.to_dict(),
            "summary": {
                "healthy": self.healthy_count,
                "degraded": self.degraded_count,
                "unhealthy": self.unhealthy_count,
                "total": len(self.components),
            },
        }


@dataclass
class HealthCheckResult:
    """Complete health check result with timestamp."""

    health: SystemHealth
    duration_ms: float
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "health": self.health.to_dict(),
        }


class MCPHealthChecker:
    """Comprehensive health monitoring for MCP server."""

    def __init__(
        self,
        project_root: Path | None = None,
        timeout: float = 5.0,
        retry_count: int = 3,
        retry_backoff: float = 1.5,
    ) -> None:
        """
        Initialize health checker.

        Args:
            project_root: Project root directory
            timeout: Default timeout for health checks
            retry_count: Number of retries for failed checks
            retry_backoff: Exponential backoff multiplier
        """
        self.project_root = project_root or Path.cwd()
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_backoff = retry_backoff
        self.health_history: list[HealthCheckResult] = []

    async def check_health(self, detailed: bool = True, retry: bool = True) -> HealthCheckResult:
        """
        Perform comprehensive health check.

        Args:
            detailed: Include detailed component checks
            retry: Enable retry with exponential backoff

        Returns:
            Complete health check result
        """
        start_time = time.time()

        # Perform all component checks
        components = []

        # CLI health check
        cli_health = await self._check_cli_health(retry=retry)
        components.append(cli_health)

        # Database health check
        db_health = await self._check_database_health(retry=retry)
        components.append(db_health)

        # Protocol health check
        protocol_health = await self._check_protocol_health(retry=retry)
        components.append(protocol_health)

        # Tools health check (if detailed)
        if detailed:
            tools_health = await self._check_tools_health(retry=retry)
            components.append(tools_health)

        # Collect performance metrics
        performance = await self._collect_performance_metrics()

        # Collect resource metrics
        resources = await self._collect_resource_metrics()

        # Determine overall health status
        overall_status = self._determine_overall_status(components, performance, resources)

        # Create system health
        system_health = SystemHealth(
            status=overall_status,
            components=components,
            performance=performance,
            resources=resources,
        )

        duration = (time.time() - start_time) * 1000
        result = HealthCheckResult(health=system_health, duration_ms=duration)

        # Add to history
        self.health_history.append(result)

        return result

    async def _check_cli_health(self, retry: bool = True) -> ComponentHealth:
        """Check CLI executable health."""
        start_time = time.time()

        for attempt in range(self.retry_count if retry else 1):
            try:
                # Try to find kuzu-memory executable
                result = subprocess.run(
                    ["kuzu-memory", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                latency = (time.time() - start_time) * 1000

                if result.returncode == 0:
                    version = result.stdout.strip()
                    status = self._latency_to_status(latency)

                    return ComponentHealth(
                        name="cli",
                        status=status,
                        message=f"CLI operational (v{version})",
                        latency_ms=latency,
                        metadata={"version": version, "path": "kuzu-memory"},
                    )
                else:
                    raise RuntimeError(f"CLI returned error: {result.stderr}")

            except Exception as e:
                if attempt < self.retry_count - 1 and retry:
                    # Wait with exponential backoff
                    wait_time = self.retry_backoff**attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    latency = (time.time() - start_time) * 1000
                    return ComponentHealth(
                        name="cli",
                        status=HealthStatus.UNHEALTHY,
                        message="CLI check failed",
                        latency_ms=latency,
                        error=str(e),
                    )

        # Should not reach here, but return unhealthy if it does
        return ComponentHealth(
            name="cli",
            status=HealthStatus.UNHEALTHY,
            message="CLI check failed after retries",
            latency_ms=(time.time() - start_time) * 1000,
        )

    async def _check_database_health(self, retry: bool = True) -> ComponentHealth:
        """Check database health."""
        start_time = time.time()

        for attempt in range(self.retry_count if retry else 1):
            try:
                # Build list of candidate database paths in priority order
                candidate_paths = []

                # 1. Environment variable (highest priority)
                env_db_path = os.environ.get("KUZU_MEMORY_DB")
                if env_db_path:
                    candidate_paths.append(Path(env_db_path))

                # 2. Project-local paths
                candidate_paths.extend(
                    [
                        self.project_root / "kuzu-memories" / "memories.db",
                        self.project_root / "kuzu-memories" / "memory.db",
                    ]
                )

                # 3. Default user path (fallback)
                candidate_paths.append(Path.home() / ".kuzu" / "memory.db")

                # Record all checked paths for metadata
                checked_paths = [str(path) for path in candidate_paths]

                # Find first existing, readable, writable database
                db_file: Path | None = None

                for path in candidate_paths:
                    if path.exists():
                        readable = os.access(path, os.R_OK)
                        writable = os.access(path, os.W_OK)
                        if readable and writable:
                            db_file = path
                            break

                latency = (time.time() - start_time) * 1000

                if db_file and db_file.exists():
                    # Check size and accessibility
                    db_size = db_file.stat().st_size
                    readable = os.access(db_file, os.R_OK)
                    writable = os.access(db_file, os.W_OK)

                    if readable and writable:
                        status = self._latency_to_status(latency)
                        return ComponentHealth(
                            name="database",
                            status=status,
                            message="Database accessible",
                            latency_ms=latency,
                            metadata={
                                "path": str(db_file),
                                "size_bytes": db_size,
                                "readable": readable,
                                "writable": writable,
                                "checked_paths": checked_paths,
                            },
                        )
                    else:
                        return ComponentHealth(
                            name="database",
                            status=HealthStatus.DEGRADED,
                            message="Database has permission issues",
                            latency_ms=latency,
                            metadata={
                                "path": str(db_file),
                                "readable": readable,
                                "writable": writable,
                                "checked_paths": checked_paths,
                            },
                        )
                else:
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.DEGRADED,
                        message="Database not initialized",
                        latency_ms=latency,
                        metadata={
                            "checked_paths": checked_paths,
                            "note": "No readable/writable database found in any location",
                        },
                    )

            except Exception as e:
                if attempt < self.retry_count - 1 and retry:
                    wait_time = self.retry_backoff**attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    latency = (time.time() - start_time) * 1000
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.UNHEALTHY,
                        message="Database check failed",
                        latency_ms=latency,
                        error=str(e),
                    )

        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message="Database check failed after retries",
            latency_ms=(time.time() - start_time) * 1000,
        )

    async def _check_protocol_health(self, retry: bool = True) -> ComponentHealth:
        """Check MCP protocol health."""
        start_time = time.time()
        tester = MCPConnectionTester(project_root=self.project_root, timeout=self.timeout)

        for attempt in range(self.retry_count if retry else 1):
            try:
                # Start server
                start_result = await tester.start_server()
                if not start_result.success:
                    raise RuntimeError(start_result.error or "Server failed to start")

                # Test protocol initialization
                init_msg = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {"protocolVersion": "2025-06-18"},
                }

                response = await tester._send_request(init_msg)
                latency = (time.time() - start_time) * 1000

                await tester.stop_server()

                if response and "result" in response:
                    protocol_version = response["result"].get("protocolVersion")
                    status = self._latency_to_status(latency)

                    return ComponentHealth(
                        name="protocol",
                        status=status,
                        message="Protocol compliant",
                        latency_ms=latency,
                        metadata={
                            "version": protocol_version,
                            "jsonrpc": response.get("jsonrpc"),
                        },
                    )
                else:
                    await tester.stop_server()
                    error_msg = "No result"
                    if response and isinstance(response, dict):
                        error_msg = str(response.get("error", "No result"))
                    return ComponentHealth(
                        name="protocol",
                        status=HealthStatus.UNHEALTHY,
                        message="Protocol initialization failed",
                        latency_ms=latency,
                        error=error_msg,
                    )

            except Exception as e:
                await tester.stop_server()

                if attempt < self.retry_count - 1 and retry:
                    wait_time = self.retry_backoff**attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    latency = (time.time() - start_time) * 1000
                    return ComponentHealth(
                        name="protocol",
                        status=HealthStatus.UNHEALTHY,
                        message="Protocol check failed",
                        latency_ms=latency,
                        error=str(e),
                    )

        return ComponentHealth(
            name="protocol",
            status=HealthStatus.UNHEALTHY,
            message="Protocol check failed after retries",
            latency_ms=(time.time() - start_time) * 1000,
        )

    async def _check_tools_health(self, retry: bool = True) -> ComponentHealth:
        """Check tools execution health."""
        start_time = time.time()
        tester = MCPConnectionTester(project_root=self.project_root, timeout=self.timeout)

        for attempt in range(self.retry_count if retry else 1):
            try:
                # Start server
                start_result = await tester.start_server()
                if not start_result.success:
                    raise RuntimeError("Server failed to start")

                # Initialize protocol
                init_msg = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {"protocolVersion": "2025-06-18"},
                }
                await tester._send_request(init_msg)

                # Test a simple tool (ping)
                ping_msg = {"jsonrpc": "2.0", "method": "ping", "id": 2}
                response = await tester._send_request(ping_msg)

                latency = (time.time() - start_time) * 1000

                await tester.stop_server()

                if response and "result" in response:
                    status = self._latency_to_status(latency)
                    return ComponentHealth(
                        name="tools",
                        status=status,
                        message="Tools operational",
                        latency_ms=latency,
                        metadata={"test_tool": "ping"},
                    )
                else:
                    await tester.stop_server()
                    return ComponentHealth(
                        name="tools",
                        status=HealthStatus.DEGRADED,
                        message="Tool execution degraded",
                        latency_ms=latency,
                    )

            except Exception as e:
                await tester.stop_server()

                if attempt < self.retry_count - 1 and retry:
                    wait_time = self.retry_backoff**attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    latency = (time.time() - start_time) * 1000
                    return ComponentHealth(
                        name="tools",
                        status=HealthStatus.UNHEALTHY,
                        message="Tools check failed",
                        latency_ms=latency,
                        error=str(e),
                    )

        return ComponentHealth(
            name="tools",
            status=HealthStatus.UNHEALTHY,
            message="Tools check failed after retries",
            latency_ms=(time.time() - start_time) * 1000,
        )

    async def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance metrics from recent checks."""
        metrics = PerformanceMetrics()

        # Calculate from health history if available
        if self.health_history:
            recent = self.health_history[-10:]  # Last 10 checks
            latencies = []
            total_requests = 0
            failed_requests = 0

            for check in recent:
                for component in check.health.components:
                    latencies.append(component.latency_ms)
                    total_requests += 1
                    if component.status == HealthStatus.UNHEALTHY:
                        failed_requests += 1

            if latencies:
                latencies.sort()
                metrics.latency_p50_ms = latencies[len(latencies) // 2]
                metrics.latency_p95_ms = latencies[int(len(latencies) * 0.95)]
                metrics.latency_p99_ms = latencies[int(len(latencies) * 0.99)]
                metrics.average_latency_ms = sum(latencies) / len(latencies)
                metrics.total_requests = total_requests
                metrics.failed_requests = failed_requests
                metrics.error_rate = failed_requests / total_requests if total_requests > 0 else 0.0

        return metrics

    async def _collect_resource_metrics(self) -> ResourceMetrics:
        """Collect resource usage metrics."""
        metrics = ResourceMetrics()

        if psutil is None:
            logger.warning("psutil not available, skipping resource metrics")
            return metrics

        try:
            # Get current process
            process = psutil.Process()

            # Memory usage in MB
            mem_info = process.memory_info()
            metrics.memory_mb = mem_info.rss / (1024 * 1024)

            # CPU usage
            metrics.cpu_percent = process.cpu_percent(interval=0.1)

            # Connection count
            try:
                metrics.open_connections = len(process.connections())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                metrics.open_connections = 0

            # Thread count
            metrics.active_threads = process.num_threads()

        except Exception as e:
            logger.warning(f"Failed to collect resource metrics: {e}")

        return metrics

    def _latency_to_status(self, latency_ms: float) -> HealthStatus:
        """Convert latency to health status."""
        thresholds = HEALTH_THRESHOLDS["latency_ms"]

        if latency_ms < thresholds["healthy"]:
            return HealthStatus.HEALTHY
        elif latency_ms < thresholds["degraded"]:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def _determine_overall_status(
        self,
        components: list[ComponentHealth],
        performance: PerformanceMetrics,
        resources: ResourceMetrics,
    ) -> HealthStatus:
        """
        Determine overall system health status.

        Args:
            components: Component health checks
            performance: Performance metrics
            resources: Resource metrics

        Returns:
            Overall health status
        """
        # If any component is unhealthy, system is unhealthy
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            return HealthStatus.UNHEALTHY

        # Check performance thresholds
        error_thresholds = HEALTH_THRESHOLDS["error_rate"]
        if performance.error_rate > error_thresholds["unhealthy"]:
            return HealthStatus.UNHEALTHY
        elif performance.error_rate > error_thresholds["degraded"]:
            return HealthStatus.DEGRADED

        # Check resource thresholds
        mem_thresholds = HEALTH_THRESHOLDS["memory_mb"]
        if resources.memory_mb > mem_thresholds["unhealthy"]:
            return HealthStatus.UNHEALTHY
        elif resources.memory_mb > mem_thresholds["degraded"]:
            return HealthStatus.DEGRADED

        # If any component is degraded, system is degraded
        if any(c.status == HealthStatus.DEGRADED for c in components):
            return HealthStatus.DEGRADED

        # All components healthy
        return HealthStatus.HEALTHY

    def get_health_trend(self, window: int = 10) -> dict[str, Any]:
        """
        Analyze health trend over recent checks.

        Args:
            window: Number of recent checks to analyze

        Returns:
            Health trend analysis
        """
        if not self.health_history:
            return {"trend": "unknown", "checks": 0}

        recent = self.health_history[-window:]

        healthy_count = sum(1 for check in recent if check.health.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for check in recent if check.health.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(
            1 for check in recent if check.health.status == HealthStatus.UNHEALTHY
        )

        total = len(recent)
        health_rate = healthy_count / total if total > 0 else 0.0

        if health_rate >= 0.9:
            trend = "improving" if degraded_count == 0 else "stable"
        elif health_rate >= 0.5:
            trend = "degrading"
        else:
            trend = "critical"

        return {
            "trend": trend,
            "checks": total,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "health_rate": health_rate,
        }
