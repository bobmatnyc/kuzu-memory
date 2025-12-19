"""
Auto-tuning service for KuzuMemory.

Automatically adjusts performance parameters and triggers maintenance
operations based on database size and usage patterns.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kuzu_memory.core.config import KuzuMemoryConfig
    from kuzu_memory.core.memory import KuzuMemory

logger = logging.getLogger(__name__)


@dataclass
class AutoTuneResult:
    """Result of auto-tuning operation."""

    success: bool
    memory_count: int
    db_size_mb: float
    actions_taken: list[str]
    warnings: list[str]
    pruned_count: int = 0
    new_timeout_ms: int | None = None
    execution_time_ms: float = 0


class AutoTuneService:
    """
    Automatic performance tuning and maintenance for KuzuMemory.

    Performs the following on startup or on-demand:
    - Checks database size and memory count
    - Adjusts query timeouts based on database size
    - Triggers automatic pruning if thresholds exceeded
    - Warns about potential performance issues
    """

    # Thresholds for automatic actions
    MEMORY_COUNT_WARN = 50_000  # Warn at 50k memories
    MEMORY_COUNT_PRUNE = 100_000  # Auto-prune at 100k memories
    MEMORY_COUNT_CRITICAL = 250_000  # Aggressive prune at 250k
    MEMORY_COUNT_EMERGENCY = 500_000  # Emergency prune at 500k

    # Timeout scaling based on memory count
    BASE_TIMEOUT_MS = 5000
    TIMEOUT_PER_10K_MEMORIES = 1000  # Add 1 second per 10k memories
    MAX_TIMEOUT_MS = 60000  # 60 seconds max

    # Database size thresholds (MB)
    DB_SIZE_WARN_MB = 500
    DB_SIZE_PRUNE_MB = 1000
    DB_SIZE_CRITICAL_MB = 2500

    def __init__(
        self,
        memory: "KuzuMemory",
        config: "KuzuMemoryConfig | None" = None,
    ) -> None:
        """
        Initialize auto-tune service.

        Args:
            memory: KuzuMemory instance to tune
            config: Optional configuration override
        """
        self.memory = memory
        self.config = config or memory.config

    def get_database_stats(self) -> tuple[int, float]:
        """
        Get current database statistics.

        Returns:
            Tuple of (memory_count, db_size_mb)
        """
        # Get memory count with a simple, fast query
        try:
            count_query = "MATCH (m:Memory) RETURN count(m) AS cnt"
            result = self.memory.memory_store.db_adapter.execute_query(count_query)
            memory_count = result[0]["cnt"] if result else 0
        except Exception as e:
            logger.warning(f"Failed to get memory count: {e}")
            memory_count = 0

        # Get database size
        db_path = Path(self.memory.db_path)
        db_size_mb = 0.0
        try:
            if db_path.exists():
                if db_path.is_dir():
                    db_size_mb = sum(
                        f.stat().st_size for f in db_path.rglob("*") if f.is_file()
                    ) / (1024 * 1024)
                else:
                    db_size_mb = db_path.stat().st_size / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Failed to get database size: {e}")

        return memory_count, db_size_mb

    def calculate_optimal_timeout(self, memory_count: int) -> int:
        """
        Calculate optimal query timeout based on memory count.

        Args:
            memory_count: Number of memories in database

        Returns:
            Optimal timeout in milliseconds
        """
        # Scale timeout with database size
        additional_timeout = (memory_count // 10_000) * self.TIMEOUT_PER_10K_MEMORIES
        optimal = self.BASE_TIMEOUT_MS + additional_timeout
        return min(optimal, self.MAX_TIMEOUT_MS)

    def select_prune_strategy(self, memory_count: int) -> tuple[str, dict]:
        """
        Select appropriate pruning strategy based on database size.

        Args:
            memory_count: Number of memories in database

        Returns:
            Tuple of (strategy_name, strategy_kwargs)
        """
        if memory_count >= self.MEMORY_COUNT_EMERGENCY:
            # Emergency: prune 40% using percentage strategy
            return "percentage", {"percentage": 40.0}
        elif memory_count >= self.MEMORY_COUNT_CRITICAL:
            # Critical: prune 30% using percentage strategy
            return "percentage", {"percentage": 30.0}
        elif memory_count >= self.MEMORY_COUNT_PRUNE:
            # Normal auto-prune: prune 20% using percentage strategy
            return "percentage", {"percentage": 20.0}
        else:
            return "safe", {}

    def run(
        self,
        auto_prune: bool = True,
        auto_adjust_timeout: bool = True,
        dry_run: bool = False,
    ) -> AutoTuneResult:
        """
        Run auto-tuning checks and optimizations.

        Args:
            auto_prune: If True, automatically prune when thresholds exceeded
            auto_adjust_timeout: If True, adjust query timeout based on size
            dry_run: If True, report what would be done without doing it

        Returns:
            AutoTuneResult with details of actions taken
        """
        start_time = time.time()
        actions: list[str] = []
        warnings: list[str] = []
        pruned_count = 0
        new_timeout: int | None = None

        try:
            # Get current stats
            memory_count, db_size_mb = self.get_database_stats()
            logger.info(f"Auto-tune: {memory_count:,} memories, {db_size_mb:.1f} MB database")

            # Check for warnings
            if memory_count >= self.MEMORY_COUNT_WARN:
                warnings.append(
                    f"High memory count: {memory_count:,} memories "
                    f"(threshold: {self.MEMORY_COUNT_WARN:,})"
                )

            if db_size_mb >= self.DB_SIZE_WARN_MB:
                warnings.append(
                    f"Large database size: {db_size_mb:.1f} MB "
                    f"(threshold: {self.DB_SIZE_WARN_MB} MB)"
                )

            # Adjust timeout if needed
            if auto_adjust_timeout:
                optimal_timeout = self.calculate_optimal_timeout(memory_count)
                current_timeout = self.config.storage.query_timeout_ms

                if optimal_timeout > current_timeout:
                    if not dry_run:
                        self.config.storage.query_timeout_ms = optimal_timeout
                        new_timeout = optimal_timeout
                    actions.append(
                        f"{'Would adjust' if dry_run else 'Adjusted'} query timeout: "
                        f"{current_timeout}ms → {optimal_timeout}ms"
                    )

            # Auto-prune if needed
            if auto_prune and memory_count >= self.MEMORY_COUNT_PRUNE:
                strategy_name, strategy_kwargs = self.select_prune_strategy(memory_count)

                if memory_count >= self.MEMORY_COUNT_EMERGENCY:
                    pct = strategy_kwargs.get("percentage", "N/A")
                    actions.append(
                        f"🚨 EMERGENCY: {memory_count:,} memories - running {strategy_name} prune ({pct}%)"
                    )
                elif memory_count >= self.MEMORY_COUNT_CRITICAL:
                    pct = strategy_kwargs.get("percentage", "N/A")
                    actions.append(
                        f"⚠️ CRITICAL: {memory_count:,} memories - running {strategy_name} prune ({pct}%)"
                    )
                else:
                    actions.append(
                        f"📊 Auto-prune triggered: {memory_count:,} memories - running {strategy_name} prune"
                    )

                if not dry_run:
                    pruned_count = self._execute_prune(strategy_name, strategy_kwargs, memory_count)
                    actions.append(f"Pruned {pruned_count:,} memories")
                else:
                    # Estimate what would be pruned
                    estimated = self._estimate_prune(strategy_name, strategy_kwargs, memory_count)
                    actions.append(f"Would prune approximately {estimated:,} memories")

            execution_time_ms = (time.time() - start_time) * 1000

            return AutoTuneResult(
                success=True,
                memory_count=memory_count,
                db_size_mb=db_size_mb,
                actions_taken=actions,
                warnings=warnings,
                pruned_count=pruned_count,
                new_timeout_ms=new_timeout,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f"Auto-tune failed: {e}", exc_info=True)
            execution_time_ms = (time.time() - start_time) * 1000
            return AutoTuneResult(
                success=False,
                memory_count=0,
                db_size_mb=0,
                actions_taken=[*actions, f"Error: {e}"],
                warnings=warnings,
                execution_time_ms=execution_time_ms,
            )

    def _execute_prune(
        self, strategy_name: str, strategy_kwargs: dict, current_count: int
    ) -> int:
        """Execute pruning operation."""
        from kuzu_memory.core.prune import MemoryPruner, PercentagePruningStrategy

        try:
            pruner = MemoryPruner(self.memory)

            # For percentage strategy, create a new instance with specified percentage
            if strategy_name == "percentage":
                percentage = strategy_kwargs.get("percentage", 30.0)
                pruner.strategies["percentage"] = PercentagePruningStrategy(
                    percentage=percentage
                )

            result = pruner.prune(
                strategy_name=strategy_name,
                execute=True,
                create_backup=True,  # Always backup
            )
            return result.memories_pruned
        except Exception as e:
            logger.error(f"Prune execution failed: {e}")
            return 0

    def _estimate_prune(
        self, strategy_name: str, strategy_kwargs: dict, current_count: int
    ) -> int:
        """Estimate how many memories would be pruned."""
        # For percentage strategy, use the percentage directly
        if strategy_name == "percentage":
            percentage = strategy_kwargs.get("percentage", 30.0)
            return int(current_count * (percentage / 100.0))

        # Rough estimates based on strategy
        estimates = {
            "safe": 0.07,  # ~7% reduction
            "intelligent": 0.20,  # ~20% reduction
            "aggressive": 0.40,  # ~40% reduction
        }
        rate = estimates.get(strategy_name, 0.10)
        return int(current_count * rate)


def run_startup_autotune(
    memory: "KuzuMemory",
    quiet: bool = False,
) -> AutoTuneResult:
    """
    Run auto-tuning on startup.

    This is a convenience function to be called during KuzuMemory initialization.

    Args:
        memory: KuzuMemory instance
        quiet: If True, suppress non-critical output

    Returns:
        AutoTuneResult with details
    """
    service = AutoTuneService(memory)
    result = service.run(auto_prune=True, auto_adjust_timeout=True)

    if not quiet:
        if result.warnings:
            for warning in result.warnings:
                logger.warning(f"Auto-tune: {warning}")

        if result.actions_taken:
            for action in result.actions_taken:
                logger.info(f"Auto-tune: {action}")

    return result
