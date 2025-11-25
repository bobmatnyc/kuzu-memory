"""
Metrics collection and aggregation system.

Collects metrics from various components and provides
consolidated reporting and analysis.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..caching import EmbeddingsCache, MemoryCache
from ..connection_pool import KuzuConnectionPool
from .performance_monitor import PerformanceMonitor


class MetricsCollector:
    """
    Centralized metrics collection from all KuzuMemory components.

    Aggregates metrics from:
    - Performance monitor
    - Caches (memory, embeddings)
    - Connection pools
    - Storage systems
    """

    def __init__(
        self,
        performance_monitor: PerformanceMonitor,
        memory_cache: MemoryCache | None = None,
        embeddings_cache: EmbeddingsCache | None = None,
        connection_pool: KuzuConnectionPool | None = None,
    ) -> None:
        """
        Initialize metrics collector.

        Args:
            performance_monitor: Performance monitoring system
            memory_cache: Memory cache instance
            embeddings_cache: Embeddings cache instance
            connection_pool: Database connection pool
        """
        self.performance_monitor = performance_monitor
        self.memory_cache = memory_cache
        self.embeddings_cache = embeddings_cache
        self.connection_pool = connection_pool

    async def collect_all_metrics(self) -> dict[str, Any]:
        """Collect metrics from all components."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "performance": {},
            "cache": {},
            "database": {},
            "system_health": {},
        }

        # Collect performance metrics
        try:
            perf_summary = await self.performance_monitor.get_summary()
            metrics["performance"] = perf_summary
        except Exception as e:
            metrics["performance"] = {"error": str(e)}

        # Collect cache metrics
        try:
            cache_metrics = await self._collect_cache_metrics()
            metrics["cache"] = cache_metrics
        except Exception as e:
            metrics["cache"] = {"error": str(e)}

        # Collect database metrics
        try:
            db_metrics = await self._collect_database_metrics()
            metrics["database"] = db_metrics
        except Exception as e:
            metrics["database"] = {"error": str(e)}

        # Calculate system health
        try:
            health = await self._calculate_system_health(metrics)
            metrics["system_health"] = health
        except Exception as e:
            metrics["system_health"] = {"error": str(e)}

        return metrics

    async def _collect_cache_metrics(self) -> dict[str, Any]:
        """Collect metrics from all cache systems."""
        cache_metrics = {}

        if self.memory_cache:
            memory_stats = await self.memory_cache.get_stats()
            cache_metrics["memory_cache"] = memory_stats

        if self.embeddings_cache:
            embeddings_stats = await self.embeddings_cache.get_stats()
            cache_metrics["embeddings_cache"] = embeddings_stats

        # Calculate combined cache statistics
        if cache_metrics:
            cache_metrics["combined"] = await self._calculate_combined_cache_stats(cache_metrics)

        return cache_metrics

    async def _collect_database_metrics(self) -> dict[str, Any]:
        """Collect metrics from database systems."""
        db_metrics = {}

        if self.connection_pool:
            pool_stats = await self.connection_pool.get_stats()
            health_check = await self.connection_pool.health_check()

            db_metrics["connection_pool"] = pool_stats
            db_metrics["health_check"] = health_check

        return db_metrics

    async def _calculate_combined_cache_stats(
        self, cache_metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate combined statistics across all caches."""
        combined = {
            "total_size": 0,
            "total_hits": 0,
            "total_misses": 0,
            "combined_hit_rate": 0.0,
            "cache_types": (
                len(cache_metrics) - 1 if "combined" in cache_metrics else len(cache_metrics)
            ),
        }

        for cache_name, stats in cache_metrics.items():
            if cache_name == "combined" or isinstance(stats, str):
                continue

            if "memory_cache" in stats:
                # Handle nested cache structure
                memory_stats = stats["memory_cache"]
                combined["total_hits"] += memory_stats.get("hits", 0)
                combined["total_misses"] += memory_stats.get("misses", 0)
            else:
                # Handle flat cache structure
                combined["total_hits"] += stats.get("hits", 0)
                combined["total_misses"] += stats.get("misses", 0)

            combined["total_size"] += stats.get("size", stats.get("total_size", 0))

        # Calculate combined hit rate
        total_requests = combined["total_hits"] + combined["total_misses"]
        if total_requests > 0:
            combined["combined_hit_rate"] = combined["total_hits"] / total_requests

        return combined

    async def _calculate_system_health(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Calculate overall system health from collected metrics."""
        health: dict[str, Any] = {
            "status": "healthy",
            "score": 100,
            "issues": [],
            "recommendations": [],
        }

        # Check performance metrics
        performance = metrics.get("performance", {})
        if "violations" in performance:
            violations = performance["violations"]
            critical_violations = [v for v in violations if v.get("severity") == "critical"]
            warning_violations = [v for v in violations if v.get("severity") == "warning"]

            if critical_violations:
                health["status"] = "unhealthy"
                health["score"] -= len(critical_violations) * 30
                health["issues"].extend([f"Critical: {v['metric']}" for v in critical_violations])

            if warning_violations:
                health["score"] -= len(warning_violations) * 10
                health["issues"].extend([f"Warning: {v['metric']}" for v in warning_violations])

        # Check cache health
        cache = metrics.get("cache", {})
        combined_cache = cache.get("combined", {})
        hit_rate = combined_cache.get("combined_hit_rate", 1.0)

        if hit_rate < 0.5:  # <50% hit rate
            health["status"] = "degraded"
            health["score"] -= 20
            health["issues"].append("Low cache hit rate")
            health["recommendations"].append("Consider increasing cache size or adjusting TTL")

        # Check database health
        database = metrics.get("database", {})
        if database.get("health_check", {}).get("unhealthy_removed", 0) > 0:
            health["score"] -= 15
            health["issues"].append("Unhealthy database connections detected")

        pool_stats = database.get("connection_pool", {})
        utilization = pool_stats.get("utilization", 0)
        if utilization > 0.9:  # >90% pool utilization
            health["score"] -= 10
            health["issues"].append("High database connection pool utilization")
            health["recommendations"].append("Consider increasing connection pool size")

        # Determine final status based on score
        if health["score"] < 50:
            health["status"] = "unhealthy"
        elif health["score"] < 80:
            health["status"] = "degraded"

        return health

    async def get_performance_summary(self, period_hours: int = 1) -> dict[str, Any]:
        """Get performance summary for a specific time period."""
        period = timedelta(hours=period_hours)
        summary = await self.performance_monitor.get_summary(period)

        # Add threshold violations
        violations = await self.performance_monitor.check_performance_thresholds()
        summary["threshold_violations"] = violations

        return summary

    async def get_cache_efficiency_report(self) -> dict[str, Any]:
        """Get detailed cache efficiency report."""
        cache_metrics = await self._collect_cache_metrics()

        report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "efficiency_analysis": {},
            "recommendations": [],
        }

        # Analyze memory cache efficiency
        if "memory_cache" in cache_metrics:
            memory_cache = cache_metrics["memory_cache"]
            memory_hit_rate = memory_cache.get("combined_hit_rate", 0)

            report["efficiency_analysis"]["memory_cache"] = {
                "hit_rate": memory_hit_rate,
                "efficiency": (
                    "high"
                    if memory_hit_rate > 0.8
                    else "medium"
                    if memory_hit_rate > 0.5
                    else "low"
                ),
                "total_size": memory_cache.get("memory_cache", {}).get("size", 0),
            }

            if memory_hit_rate < 0.7:
                report["recommendations"].append(
                    "Memory cache hit rate is below optimal. Consider increasing cache size or adjusting retention policies."
                )

        # Analyze embeddings cache efficiency
        if "embeddings_cache" in cache_metrics:
            embeddings_cache = cache_metrics["embeddings_cache"]
            embeddings_hit_rate = embeddings_cache.get("combined_hit_rate", 0)

            report["efficiency_analysis"]["embeddings_cache"] = {
                "hit_rate": embeddings_hit_rate,
                "efficiency": (
                    "high"
                    if embeddings_hit_rate > 0.8
                    else "medium"
                    if embeddings_hit_rate > 0.5
                    else "low"
                ),
                "estimated_memory_mb": embeddings_cache.get("estimated_memory_mb", 0),
            }

            if embeddings_hit_rate < 0.6:
                report["recommendations"].append(
                    "Embeddings cache hit rate is low. Consider increasing cache size or longer TTL for embeddings."
                )

        return report

    async def get_database_health_report(self) -> dict[str, Any]:
        """Get detailed database health report."""
        db_metrics = await self._collect_database_metrics()

        report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "connection_pool": {},
            "health_status": "unknown",
            "recommendations": [],
        }

        if "connection_pool" in db_metrics:
            pool_stats = db_metrics["connection_pool"]
            health_check = db_metrics.get("health_check", {})

            report["connection_pool"] = {
                "utilization": pool_stats.get("utilization", 0),
                "active_connections": pool_stats.get("active_connections", 0),
                "available_connections": pool_stats.get("available_connections", 0),
                "total_connections": pool_stats.get("pool_size", 0),
                "created_connections": pool_stats.get("created_connections", 0),
                "destroyed_connections": pool_stats.get("destroyed_connections", 0),
            }

            # Determine health status
            utilization = pool_stats.get("utilization", 0)
            unhealthy_count = health_check.get("unhealthy_removed", 0)

            if unhealthy_count > 0:
                report["health_status"] = "degraded"
                report["recommendations"].append(
                    f"Removed {unhealthy_count} unhealthy connections. Check database connectivity."
                )
            elif utilization > 0.9:
                report["health_status"] = "stressed"
                report["recommendations"].append(
                    "Connection pool utilization is very high. Consider increasing pool size."
                )
            elif utilization > 0.7:
                report["health_status"] = "busy"
                report["recommendations"].append(
                    "Connection pool utilization is high. Monitor for potential bottlenecks."
                )
            else:
                report["health_status"] = "healthy"

        return report

    async def export_metrics_report(
        self, format_type: str = "json", include_detailed: bool = True
    ) -> str:
        """Export comprehensive metrics report."""
        # Collect all metrics
        all_metrics = await self.collect_all_metrics()

        if include_detailed:
            # Add detailed reports
            all_metrics["detailed_reports"] = {
                "cache_efficiency": await self.get_cache_efficiency_report(),
                "database_health": await self.get_database_health_report(),
                "performance_summary": await self.get_performance_summary(),
            }

        # Export in requested format
        return await self.performance_monitor.export_metrics(format_type, data=all_metrics)
