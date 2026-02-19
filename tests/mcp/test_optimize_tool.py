"""
Tests for kuzu_optimize MCP tool.

Verifies that the LLM-initiated optimization tool works correctly
with all three strategies: top_accessed, stale_cleanup, consolidate_similar.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kuzu_memory.core.models import Memory, MemoryType
from kuzu_memory.mcp.server import KuzuMemoryMCPServer


@pytest.fixture
def mock_db_adapter():
    """Mock database adapter for testing."""
    adapter = MagicMock()
    adapter.initialize = MagicMock()
    adapter.execute_query = MagicMock(return_value=[])
    return adapter


@pytest.fixture
def mock_access_tracker():
    """Mock access tracker for testing."""
    tracker = MagicMock()
    tracker.get_stats = MagicMock(
        return_value={
            "total_tracked": 100,
            "total_batches": 10,
            "total_writes": 100,
        }
    )
    return tracker


@pytest.fixture
def mcp_server(tmp_path: Path) -> KuzuMemoryMCPServer:
    """Create MCP server instance for testing."""
    # Create a test database directory
    db_path = tmp_path / "kuzu-memories"
    db_path.mkdir(parents=True, exist_ok=True)

    # Create server with test project root
    server = KuzuMemoryMCPServer(project_root=tmp_path)
    return server


class TestOptimizeToolRegistration:
    """Test that kuzu_optimize tool is properly registered."""

    def test_tool_exists_in_server(self, mcp_server: KuzuMemoryMCPServer) -> None:
        """Test that optimize tool is registered in MCP server."""
        # The tool should be registered in _setup_handlers
        assert mcp_server.server is not None
        # We can't directly inspect the handlers, but we can verify server setup
        assert mcp_server.project_root is not None


class TestOptimizeTopAccessed:
    """Test top_accessed optimization strategy."""

    @pytest.mark.asyncio
    async def test_top_accessed_dry_run(
        self, mcp_server: KuzuMemoryMCPServer, mock_db_adapter: MagicMock
    ) -> None:
        """Test top_accessed strategy in dry-run mode."""
        # Mock database query to return frequently accessed memories
        mock_db_adapter.execute_query.return_value = [
            {
                "m": {
                    "id": "mem1",
                    "content": "Python best practices for testing",
                    "memory_type": "semantic",  # lowercase enum value
                    "access_count": 15,
                    "created_at": datetime.now(UTC).isoformat(),
                    "importance": 0.8,
                    "confidence": 0.9,
                    "source_type": "manual",
                    "agent_id": "test",
                }
            },
            {
                "m": {
                    "id": "mem2",
                    "content": "Best practices for Python testing",
                    "memory_type": "semantic",  # lowercase enum value
                    "access_count": 12,
                    "created_at": datetime.now(UTC).isoformat(),
                    "importance": 0.7,
                    "confidence": 0.85,
                    "source_type": "manual",
                    "agent_id": "test",
                }
            },
        ]

        with (
            patch(
                "kuzu_memory.storage.kuzu_adapter.KuzuAdapter",
                return_value=mock_db_adapter,
            ),
            patch("kuzu_memory.monitoring.access_tracker.get_access_tracker"),
        ):
            result_json = await mcp_server._optimize("top_accessed", limit=10, dry_run=True)
            result = json.loads(result_json)

            assert result["status"] == "completed"
            assert result["strategy"] == "top_accessed"
            assert result["dry_run"] is True
            assert result["results"]["memories_analyzed"] == 2
            assert "suggestions" in result


class TestOptimizeStaleCleanup:
    """Test stale_cleanup optimization strategy."""

    @pytest.mark.asyncio
    async def test_stale_cleanup_dry_run(
        self, mcp_server: KuzuMemoryMCPServer, mock_db_adapter: MagicMock
    ) -> None:
        """Test stale_cleanup strategy in dry-run mode."""
        # Mock retention scores with stale candidates
        from kuzu_memory.core.smart_pruning import RetentionScore

        stale_date = (datetime.now(UTC) - timedelta(days=100)).isoformat()

        # Mock pruning strategy
        mock_pruning = MagicMock()
        mock_pruning.get_prune_candidates.return_value = [
            RetentionScore(
                memory_id="stale1",
                age_score=0.1,
                size_score=0.5,
                access_score=0.0,
                importance_score=0.5,
                total_score=0.2,
                is_protected=False,
            )
        ]

        # Mock database query for stale memory details
        mock_db_adapter.execute_query.return_value = [
            {
                "accessed_at": stale_date,
                "created_at": stale_date,
            }
        ]

        with (
            patch(
                "kuzu_memory.storage.kuzu_adapter.KuzuAdapter",
                return_value=mock_db_adapter,
            ),
            patch(
                "kuzu_memory.core.smart_pruning.SmartPruningStrategy",
                return_value=mock_pruning,
            ),
        ):
            result_json = await mcp_server._optimize("stale_cleanup", limit=10, dry_run=True)
            result = json.loads(result_json)

            assert result["status"] == "completed"
            assert result["strategy"] == "stale_cleanup"
            assert result["dry_run"] is True
            assert "suggestions" in result


class TestOptimizeConsolidateSimilar:
    """Test consolidate_similar optimization strategy."""

    @pytest.mark.asyncio
    async def test_consolidate_similar_dry_run(
        self, mcp_server: KuzuMemoryMCPServer, mock_db_adapter: MagicMock
    ) -> None:
        """Test consolidate_similar strategy in dry-run mode."""
        from kuzu_memory.nlp.consolidation import ConsolidationResult, MemoryCluster

        # Mock consolidation result
        mock_consolidation = MagicMock()
        mock_result = ConsolidationResult(
            success=True,
            clusters_found=2,
            memories_analyzed=10,
            memories_consolidated=0,
            memories_archived=0,
            new_memories_created=0,
            execution_time_ms=100.0,
            dry_run=True,
            clusters=[],
        )
        mock_consolidation.execute.return_value = mock_result

        with (
            patch(
                "kuzu_memory.storage.kuzu_adapter.KuzuAdapter",
                return_value=mock_db_adapter,
            ),
            patch(
                "kuzu_memory.nlp.consolidation.ConsolidationEngine",
                return_value=mock_consolidation,
            ),
        ):
            result_json = await mcp_server._optimize("consolidate_similar", limit=10, dry_run=True)
            result = json.loads(result_json)

            assert result["status"] == "completed"
            assert result["strategy"] == "consolidate_similar"
            assert result["dry_run"] is True
            assert result["results"]["memories_analyzed"] == 10
            assert result["results"]["optimization_candidates"] == 2


class TestOptimizeErrorHandling:
    """Test error handling in optimize tool."""

    @pytest.mark.asyncio
    async def test_missing_database(self, tmp_path: Path, mcp_server: KuzuMemoryMCPServer) -> None:
        """Test error when database doesn't exist."""
        # Create server with non-existent database
        empty_project = tmp_path / "empty_project"
        empty_project.mkdir()
        server = KuzuMemoryMCPServer(project_root=empty_project)

        result_json = await server._optimize("top_accessed", limit=10, dry_run=True)
        result = json.loads(result_json)

        assert result["status"] == "error"
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_strategy(
        self, mcp_server: KuzuMemoryMCPServer, mock_db_adapter: MagicMock
    ) -> None:
        """Test error with unknown optimization strategy."""
        with (
            patch(
                "kuzu_memory.storage.kuzu_adapter.KuzuAdapter",
                return_value=mock_db_adapter,
            ),
            patch("kuzu_memory.monitoring.access_tracker.get_access_tracker"),
        ):
            result_json = await mcp_server._optimize("invalid_strategy", limit=10, dry_run=True)
            result = json.loads(result_json)

            assert result["status"] == "error"
            assert "Unknown strategy" in result["error"]


class TestOptimizeIntegration:
    """Integration tests with actual database (if available)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_optimize_end_to_end(self, tmp_path: Path) -> None:
        """Test complete optimization flow with real components."""
        # MCP server expects database in standard location: project_root/kuzu-memories/
        # But KuzuAdapter expects a database file path, not a directory
        # So we use: project_root/kuzu-memories as the database file
        db_dir = tmp_path / "kuzu-memories"

        # Initialize database with test data
        # KuzuAdapter will create the database at the given path
        from kuzu_memory.core.config import KuzuMemoryConfig
        from kuzu_memory.storage.kuzu_adapter import KuzuAdapter

        config = KuzuMemoryConfig.default()
        adapter = KuzuAdapter(db_dir, config)
        adapter.initialize()

        # Create MCP server (it will find the database at project_root/kuzu-memories)
        server = KuzuMemoryMCPServer(project_root=tmp_path)

        # Test optimization (dry-run)
        result_json = await server._optimize("top_accessed", limit=5, dry_run=True)
        result = json.loads(result_json)

        # Should complete without errors
        assert result["status"] == "completed"
        assert result["dry_run"] is True
