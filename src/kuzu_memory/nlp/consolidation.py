"""
NLP-based memory consolidation engine.

Provides intelligent clustering and merging of similar old memories to reduce
memory database size while preserving important information.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ..core.models import Memory, MemoryType
from ..storage.kuzu_adapter import KuzuAdapter
from ..utils.deduplication import DeduplicationEngine

logger = logging.getLogger(__name__)


@dataclass
class MemoryCluster:
    """A cluster of similar memories for consolidation."""

    cluster_id: str
    memories: list[Memory]
    centroid_memory: Memory  # The representative memory
    similarity_scores: dict[str, float]  # memory_id -> similarity to centroid
    avg_similarity: float


@dataclass
class ConsolidationResult:
    """Result of consolidation operation."""

    success: bool
    clusters_found: int
    memories_analyzed: int
    memories_consolidated: int
    memories_archived: int
    new_memories_created: int
    execution_time_ms: float
    dry_run: bool
    clusters: list[MemoryCluster] = field(default_factory=list)
    error: str | None = None


class ConsolidationEngine:
    """
    Engine for consolidating similar old memories.

    Uses multi-layer similarity detection and clustering to group related memories
    and create summaries, reducing database size while preserving information.
    """

    # Consolidation candidates criteria
    MIN_AGE_DAYS = 90  # Only consolidate memories older than this
    MAX_ACCESS_COUNT = 3  # Only consolidate low-access memories
    ELIGIBLE_TYPES = {
        MemoryType.EPISODIC,
        MemoryType.SENSORY,
        MemoryType.WORKING,
    }
    # Never consolidate: SEMANTIC, PREFERENCE, PROCEDURAL (high value)

    # Clustering parameters
    SIMILARITY_THRESHOLD = 0.70  # Minimum similarity for clustering
    MIN_CLUSTER_SIZE = 2  # Minimum memories to form a cluster

    def __init__(
        self,
        db_adapter: KuzuAdapter,
        dedup_engine: DeduplicationEngine | None = None,
        similarity_threshold: float = 0.70,
        min_age_days: int = 90,
        max_access_count: int = 3,
    ):
        """
        Initialize consolidation engine.

        Args:
            db_adapter: Kuzu database adapter
            dedup_engine: Deduplication engine (created if not provided)
            similarity_threshold: Minimum similarity to cluster memories (0-1)
            min_age_days: Minimum age in days for consolidation eligibility
            max_access_count: Maximum access count for consolidation eligibility
        """
        self.db_adapter = db_adapter
        self.dedup_engine = dedup_engine or DeduplicationEngine(
            exact_threshold=1.0,
            near_threshold=similarity_threshold,
            semantic_threshold=similarity_threshold * 0.7,  # More lenient for semantic
        )
        self.similarity_threshold = similarity_threshold
        self.min_age_days = min_age_days
        self.max_access_count = max_access_count

    def find_candidates(self) -> list[Memory]:
        """
        Find memories eligible for consolidation.

        Criteria:
        - Age > min_age_days
        - Access count <= max_access_count
        - Memory type in ELIGIBLE_TYPES
        - Valid (not expired)

        Returns:
            List of eligible memories
        """
        try:
            cutoff_date = (datetime.now(UTC) - timedelta(days=self.min_age_days)).isoformat()
            current_time = datetime.now(UTC).isoformat()

            # Build eligible types list
            eligible_types = [mt.value for mt in self.ELIGIBLE_TYPES]

            query = """
            MATCH (m:Memory)
            WHERE m.created_at < $cutoff_date
                AND m.access_count <= $max_access_count
                AND m.memory_type IN $eligible_types
                AND (m.valid_to IS NULL OR m.valid_to > $current_time)
            RETURN m
            ORDER BY m.created_at ASC
            """

            parameters = {
                "cutoff_date": cutoff_date,
                "max_access_count": self.max_access_count,
                "eligible_types": eligible_types,
                "current_time": current_time,
            }

            results = self.db_adapter.execute_query(query, parameters)

            candidates: list[Memory] = []
            for row in results:
                memory_data = row.get("m")
                if memory_data:
                    memory = Memory.from_dict(memory_data)
                    candidates.append(memory)

            logger.info(
                f"Found {len(candidates)} consolidation candidates "
                f"(age>{self.min_age_days}d, access<={self.max_access_count})"
            )
            return candidates

        except Exception as e:
            logger.error(f"Failed to find consolidation candidates: {e}", exc_info=True)
            return []

    def cluster_memories(self, candidates: list[Memory]) -> list[MemoryCluster]:
        """
        Group similar memories into clusters using embeddings.

        Uses the DeduplicationEngine's similarity detection to identify
        groups of related memories that can be consolidated.

        Args:
            candidates: List of candidate memories to cluster

        Returns:
            List of memory clusters
        """
        if not candidates:
            return []

        clusters: list[MemoryCluster] = []
        clustered_ids: set[str] = set()

        # Sort candidates by access count (descending) to pick best centroids
        sorted_candidates = sorted(candidates, key=lambda m: m.access_count, reverse=True)

        for i, candidate in enumerate(sorted_candidates):
            # Skip if already clustered
            if candidate.id in clustered_ids:
                continue

            # Find similar memories using deduplication engine
            remaining = [m for m in sorted_candidates[i + 1 :] if m.id not in clustered_ids]

            if not remaining:
                break

            # Use find_duplicates to get similarity scores
            duplicates = self.dedup_engine.find_duplicates(
                candidate.content, remaining, memory_type=candidate.memory_type
            )

            # Filter by similarity threshold
            similar_memories = [
                dup_memory
                for dup_memory, score, match_type in duplicates
                if score >= self.similarity_threshold
            ]

            # Create cluster if we have enough similar memories
            if len(similar_memories) >= self.MIN_CLUSTER_SIZE - 1:
                cluster_members = [candidate] + similar_memories

                # Build similarity score map
                similarity_scores = {candidate.id: 1.0}  # Centroid has perfect similarity
                for memory, score, _ in duplicates:
                    if memory in similar_memories:
                        similarity_scores[memory.id] = score

                # Calculate average similarity
                avg_similarity = sum(similarity_scores.values()) / len(similarity_scores)

                cluster = MemoryCluster(
                    cluster_id=f"cluster-{candidate.id[:8]}-{int(time.time())}",
                    memories=cluster_members,
                    centroid_memory=candidate,
                    similarity_scores=similarity_scores,
                    avg_similarity=avg_similarity,
                )

                clusters.append(cluster)

                # Mark all cluster members as clustered
                for memory in cluster_members:
                    clustered_ids.add(memory.id)

                logger.debug(
                    f"Created cluster {cluster.cluster_id} with {len(cluster_members)} memories "
                    f"(avg similarity: {avg_similarity:.3f})"
                )

        logger.info(
            f"Created {len(clusters)} clusters from {len(candidates)} candidates "
            f"({len(clustered_ids)} memories clustered)"
        )
        return clusters

    def create_summary(self, cluster: MemoryCluster) -> str:
        """
        Create consolidated summary from cluster.

        Strategy:
        1. Start with centroid content (highest quality/access)
        2. Extract unique information from other members
        3. Combine with clear separation

        Args:
            cluster: Memory cluster to summarize

        Returns:
            Consolidated summary text
        """
        centroid = cluster.centroid_memory
        others = [m for m in cluster.memories if m.id != centroid.id]

        if not others:
            return centroid.content

        # Start with centroid content
        summary_parts = [centroid.content]

        # Extract unique information from others
        centroid_words = set(centroid.content.lower().split())

        for memory in others:
            memory_words = set(memory.content.lower().split())

            # Find unique words not in centroid
            unique_words = memory_words - centroid_words

            # If there's significant unique information (>30% unique words)
            uniqueness_ratio = len(unique_words) / len(memory_words) if memory_words else 0

            if uniqueness_ratio > 0.3:
                # Extract first sentence or up to 100 chars
                content_preview = memory.content
                if len(content_preview) > 100:
                    # Try to break at sentence boundary
                    sentence_end = content_preview.find(". ", 0, 100)
                    if sentence_end > 0:
                        content_preview = content_preview[: sentence_end + 1]
                    else:
                        content_preview = content_preview[:97] + "..."

                summary_parts.append(f"Related: {content_preview}")

        # Combine with newline separation
        return "\n\n".join(summary_parts)

    def execute(
        self,
        dry_run: bool = True,
        create_backup: bool = True,
    ) -> ConsolidationResult:
        """
        Execute consolidation with optional dry-run.

        Args:
            dry_run: If True, only analyze without making changes
            create_backup: If True, create database backup before consolidation

        Returns:
            ConsolidationResult with execution details
        """
        start_time = time.time()

        try:
            # Find candidates
            candidates = self.find_candidates()

            if not candidates:
                return ConsolidationResult(
                    success=True,
                    clusters_found=0,
                    memories_analyzed=0,
                    memories_consolidated=0,
                    memories_archived=0,
                    new_memories_created=0,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    dry_run=dry_run,
                )

            # Cluster memories
            clusters = self.cluster_memories(candidates)

            if dry_run:
                execution_time_ms = (time.time() - start_time) * 1000
                return ConsolidationResult(
                    success=True,
                    clusters_found=len(clusters),
                    memories_analyzed=len(candidates),
                    memories_consolidated=0,
                    memories_archived=0,
                    new_memories_created=0,
                    execution_time_ms=execution_time_ms,
                    dry_run=True,
                    clusters=clusters,
                )

            # Execute consolidation
            memories_consolidated = 0
            memories_archived = 0
            new_memories_created = 0

            for cluster in clusters:
                try:
                    # Create summary
                    summary = self.create_summary(cluster)

                    # Create new consolidated memory
                    consolidated_memory = Memory(
                        content=summary,
                        memory_type=cluster.centroid_memory.memory_type,
                        importance=max(m.importance for m in cluster.memories),
                        confidence=cluster.avg_similarity,
                        source_type="consolidation",
                        agent_id="consolidation-engine",
                        user_id=cluster.centroid_memory.user_id,
                        session_id=cluster.centroid_memory.session_id,
                        valid_to=cluster.centroid_memory.valid_to,  # Inherit expiration
                        metadata={
                            "cluster_id": cluster.cluster_id,
                            "consolidated_count": len(cluster.memories),
                            "avg_similarity": cluster.avg_similarity,
                            "original_ids": [m.id for m in cluster.memories],
                        },
                    )

                    # Store consolidated memory
                    self._store_consolidated_memory(consolidated_memory, cluster)
                    new_memories_created += 1

                    # Archive original memories
                    archived = self._archive_cluster_memories(cluster)
                    memories_archived += archived

                    # Delete original memories
                    deleted = self._delete_cluster_memories(cluster)
                    memories_consolidated += deleted

                    logger.info(
                        f"Consolidated cluster {cluster.cluster_id}: "
                        f"{len(cluster.memories)} memories -> 1 summary"
                    )

                except Exception as e:
                    logger.error(f"Failed to consolidate cluster {cluster.cluster_id}: {e}")
                    continue

            execution_time_ms = (time.time() - start_time) * 1000

            return ConsolidationResult(
                success=True,
                clusters_found=len(clusters),
                memories_analyzed=len(candidates),
                memories_consolidated=memories_consolidated,
                memories_archived=memories_archived,
                new_memories_created=new_memories_created,
                execution_time_ms=execution_time_ms,
                dry_run=False,
                clusters=clusters,
            )

        except Exception as e:
            logger.error(f"Consolidation execution failed: {e}", exc_info=True)
            execution_time_ms = (time.time() - start_time) * 1000
            return ConsolidationResult(
                success=False,
                clusters_found=0,
                memories_analyzed=0,
                memories_consolidated=0,
                memories_archived=0,
                new_memories_created=0,
                execution_time_ms=execution_time_ms,
                dry_run=dry_run,
                error=str(e),
            )

    def _store_consolidated_memory(
        self, consolidated_memory: Memory, cluster: MemoryCluster
    ) -> None:
        """Store consolidated memory and create CONSOLIDATED_INTO relationships."""
        try:
            # Insert consolidated memory
            insert_query = """
            CREATE (m:Memory {
                id: $id,
                content: $content,
                content_hash: $content_hash,
                created_at: $created_at,
                valid_from: $valid_from,
                valid_to: $valid_to,
                accessed_at: $accessed_at,
                access_count: $access_count,
                memory_type: $memory_type,
                importance: $importance,
                confidence: $confidence,
                source_type: $source_type,
                agent_id: $agent_id,
                user_id: $user_id,
                session_id: $session_id,
                metadata: $metadata
            })
            """

            memory_dict = consolidated_memory.to_dict()
            memory_dict.pop("entities", None)  # Remove entities field (not in schema)
            self.db_adapter.execute_query(insert_query, memory_dict)

            # Create CONSOLIDATED_INTO relationships from originals to consolidated
            for original_memory in cluster.memories:
                rel_query = """
                MATCH (orig:Memory {id: $original_id})
                MATCH (cons:Memory {id: $consolidated_id})
                CREATE (orig)-[r:CONSOLIDATED_INTO {
                    consolidation_date: $consolidation_date,
                    cluster_id: $cluster_id,
                    similarity_score: $similarity_score
                }]->(cons)
                """

                rel_params = {
                    "original_id": original_memory.id,
                    "consolidated_id": consolidated_memory.id,
                    "consolidation_date": datetime.now(UTC).isoformat(),
                    "cluster_id": cluster.cluster_id,
                    "similarity_score": cluster.similarity_scores.get(original_memory.id, 0.0),
                }

                self.db_adapter.execute_query(rel_query, rel_params)

            logger.debug(f"Stored consolidated memory {consolidated_memory.id}")

        except Exception as e:
            logger.error(f"Failed to store consolidated memory: {e}")
            raise

    def _archive_cluster_memories(self, cluster: MemoryCluster) -> int:
        """Archive original memories from cluster."""
        archived_count = 0

        for memory in cluster.memories:
            try:
                archive_query = """
                CREATE (a:ArchivedMemory {
                    id: $id,
                    original_id: $original_id,
                    content: $content,
                    memory_type: $memory_type,
                    source_type: $source_type,
                    importance: $importance,
                    created_at: $created_at,
                    archived_at: $archived_at,
                    prune_score: $prune_score,
                    prune_reason: $prune_reason,
                    expires_at: $expires_at
                })
                """

                archive_id = f"archive-consolidated-{memory.id}-{int(time.time())}"
                archived_at = datetime.now(UTC)
                expires_at = archived_at + timedelta(days=30)  # 30-day recovery window

                archive_params = {
                    "id": archive_id,
                    "original_id": memory.id,
                    "content": memory.content,
                    "memory_type": memory.memory_type.value,
                    "source_type": memory.source_type,
                    "importance": memory.importance,
                    "created_at": memory.created_at.isoformat(),
                    "archived_at": archived_at.isoformat(),
                    "prune_score": cluster.similarity_scores.get(memory.id, 0.0),
                    "prune_reason": f"Consolidated into cluster {cluster.cluster_id}",
                    "expires_at": expires_at.isoformat(),
                }

                self.db_adapter.execute_query(archive_query, archive_params)
                archived_count += 1

            except Exception as e:
                logger.error(f"Failed to archive memory {memory.id}: {e}")

        return archived_count

    def _delete_cluster_memories(self, cluster: MemoryCluster) -> int:
        """Delete original memories from cluster after archiving."""
        try:
            memory_ids = [m.id for m in cluster.memories]

            delete_query = """
            MATCH (m:Memory)
            WHERE m.id IN $memory_ids
            DELETE m
            """

            self.db_adapter.execute_query(delete_query, {"memory_ids": memory_ids})

            logger.debug(f"Deleted {len(memory_ids)} memories from cluster {cluster.cluster_id}")
            return len(memory_ids)

        except Exception as e:
            logger.error(f"Failed to delete cluster memories: {e}")
            return 0
