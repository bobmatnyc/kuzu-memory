"""
Specialized cache for embeddings and vector similarity operations.

Optimized for storing and retrieving high-dimensional vectors used
in semantic similarity calculations.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from ..interfaces.cache import ICache
from .lru_cache import LRUCache


class EmbeddingsCache(ICache):
    """
    Specialized cache for embeddings and similarity calculations.

    Features:
    - Efficient storage of high-dimensional vectors
    - Content-based hashing for embedding deduplication
    - Similarity result caching
    - Memory-efficient numpy array storage
    """

    def __init__(
        self,
        max_embeddings: int = 10000,
        max_similarity_results: int = 5000,
        embedding_ttl: timedelta | None = timedelta(hours=24),
        similarity_ttl: timedelta | None = timedelta(hours=1),
    ):
        """
        Initialize embeddings cache.

        Args:
            max_embeddings: Maximum number of embeddings to cache
            max_similarity_results: Maximum similarity results to cache
            embedding_ttl: TTL for cached embeddings
            similarity_ttl: TTL for similarity calculation results
        """
        self._max_embeddings = max_embeddings
        self._max_similarity_results = max_similarity_results

        # Separate caches for embeddings and similarity results
        self._embedding_cache = LRUCache(max_size=max_embeddings, default_ttl=embedding_ttl)
        self._similarity_cache = LRUCache(
            max_size=max_similarity_results, default_ttl=similarity_ttl
        )

        # Content to embedding key mapping
        self._content_to_key: dict[str, str] = {}

    async def cache_embedding(
        self, content: str, embedding: np.ndarray, ttl: timedelta | None = None
    ) -> str:
        """
        Cache an embedding vector for content.

        Args:
            content: Text content the embedding represents
            embedding: High-dimensional embedding vector
            ttl: Time-to-live for the cached embedding

        Returns:
            Cache key for the embedding
        """
        # Create content-based key
        content_key = self._create_content_key(content)

        # Store embedding with metadata
        embedding_data = EmbeddingData(
            content=content,
            embedding=embedding.copy(),  # Copy to avoid external modifications
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            created_at=datetime.now(),
        )

        await self._embedding_cache.set(content_key, embedding_data, ttl)
        self._content_to_key[content] = content_key

        return content_key

    async def get_embedding(self, content: str) -> np.ndarray | None:
        """
        Get cached embedding for content.

        Args:
            content: Text content to get embedding for

        Returns:
            Embedding vector if cached, None otherwise
        """
        content_key = self._content_to_key.get(content)
        if not content_key:
            content_key = self._create_content_key(content)

        embedding_data = await self._embedding_cache.get(content_key)
        if embedding_data and isinstance(embedding_data, EmbeddingData):
            return embedding_data.embedding.copy()

        return None

    async def get_embedding_by_key(self, content_key: str) -> np.ndarray | None:
        """Get embedding by cache key."""
        embedding_data = await self._embedding_cache.get(content_key)
        if embedding_data and isinstance(embedding_data, EmbeddingData):
            return embedding_data.embedding.copy()
        return None

    async def cache_similarity_result(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: list[tuple[str, np.ndarray]],
        similarities: list[float],
        ttl: timedelta | None = None,
    ) -> str:
        """
        Cache similarity calculation results.

        Args:
            query_embedding: Query vector
            candidate_embeddings: List of (content_key, embedding) pairs
            similarities: Similarity scores corresponding to candidates
            ttl: Time-to-live for the cached result

        Returns:
            Cache key for the similarity result
        """
        # Create key based on query and candidate embeddings
        query_hash = self._hash_embedding(query_embedding)
        candidate_hashes = [self._hash_embedding(emb) for _, emb in candidate_embeddings]

        similarity_key = f"sim_{query_hash}_{hash(tuple(candidate_hashes))}"

        # Create similarity result
        result = SimilarityResult(
            query_hash=query_hash,
            candidate_keys=[key for key, _ in candidate_embeddings],
            similarities=similarities.copy(),
            calculated_at=datetime.now(),
        )

        await self._similarity_cache.set(similarity_key, result, ttl)
        return similarity_key

    async def get_similarity_result(
        self, query_embedding: np.ndarray, candidate_keys: list[str]
    ) -> list[float] | None:
        """
        Get cached similarity results.

        Args:
            query_embedding: Query vector
            candidate_keys: List of candidate content keys

        Returns:
            List of similarity scores if cached, None otherwise
        """
        query_hash = self._hash_embedding(query_embedding)
        similarity_key = f"sim_{query_hash}_{hash(tuple(candidate_keys))}"

        result = await self._similarity_cache.get(similarity_key)
        if result and isinstance(result, SimilarityResult):
            return result.similarities.copy()

        return None

    async def batch_get_embeddings(self, contents: list[str]) -> dict[str, np.ndarray]:
        """
        Get multiple embeddings in batch.

        Args:
            contents: List of content strings

        Returns:
            Dictionary mapping content to embeddings
        """
        result = {}
        for content in contents:
            embedding = await self.get_embedding(content)
            if embedding is not None:
                result[content] = embedding
        return result

    async def invalidate_content(self, content: str) -> bool:
        """
        Invalidate cached embedding for specific content.

        Args:
            content: Content to invalidate

        Returns:
            True if embedding was cached and removed
        """
        content_key = self._content_to_key.get(content)
        if content_key:
            deleted = await self._embedding_cache.delete(content_key)
            if deleted:
                self._content_to_key.pop(content, None)
            return deleted
        return False

    def _create_content_key(self, content: str) -> str:
        """Create a consistent cache key for content."""
        # Normalize content and create hash
        normalized = content.lower().strip()
        return f"emb_{hashlib.md5(normalized.encode()).hexdigest()}"

    def _hash_embedding(self, embedding: np.ndarray) -> str:
        """Create a hash of an embedding vector."""
        # Use a subset of the embedding for hashing to balance speed and uniqueness
        subset = embedding[:: max(1, len(embedding) // 100)]  # Every ~1% of values
        return hashlib.md5(subset.tobytes()).hexdigest()[:16]

    # ICache interface implementation
    async def get(self, key: str) -> Any | None:
        """Generic get from appropriate cache."""
        # Try embedding cache first
        result = await self._embedding_cache.get(key)
        if result is not None:
            return result

        # Try similarity cache
        return await self._similarity_cache.get(key)

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Generic set to appropriate cache."""
        if isinstance(value, EmbeddingData):
            await self._embedding_cache.set(key, value, ttl)
        elif isinstance(value, SimilarityResult):
            await self._similarity_cache.set(key, value, ttl)
        else:
            # Default to embedding cache
            await self._embedding_cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete from both caches."""
        deleted_embedding = await self._embedding_cache.delete(key)
        deleted_similarity = await self._similarity_cache.delete(key)
        return deleted_embedding or deleted_similarity

    async def exists(self, key: str) -> bool:
        """Check if key exists in either cache."""
        return await self._embedding_cache.exists(key) or await self._similarity_cache.exists(key)

    async def clear(self) -> None:
        """Clear both caches."""
        await self._embedding_cache.clear()
        await self._similarity_cache.clear()
        self._content_to_key.clear()

    async def get_multi(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values."""
        result = await self._embedding_cache.get_multi(keys)
        similarity_result = await self._similarity_cache.get_multi(keys)
        result.update(similarity_result)
        return result

    async def set_multi(self, items: dict[str, Any], ttl: timedelta | None = None) -> None:
        """Set multiple values."""
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_multi(self, keys: list[str]) -> int:
        """Delete multiple values."""
        embedding_deleted = await self._embedding_cache.delete_multi(keys)
        similarity_deleted = await self._similarity_cache.delete_multi(keys)
        return embedding_deleted + similarity_deleted

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        embedding_stats = await self._embedding_cache.get_stats()
        similarity_stats = await self._similarity_cache.get_stats()

        # Estimate memory usage
        total_embeddings = embedding_stats["size"]
        estimated_memory_mb = total_embeddings * 0.001  # Rough estimate

        return {
            "embedding_cache": embedding_stats,
            "similarity_cache": similarity_stats,
            "content_to_key_mappings": len(self._content_to_key),
            "estimated_memory_mb": round(estimated_memory_mb, 2),
            "total_size": embedding_stats["size"] + similarity_stats["size"],
            "combined_hit_rate": (
                (embedding_stats["hits"] + similarity_stats["hits"])
                / max(
                    1,
                    embedding_stats["hits"]
                    + embedding_stats["misses"]
                    + similarity_stats["hits"]
                    + similarity_stats["misses"],
                )
            ),
        }

    async def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        embedding_cleaned = await self._embedding_cache.cleanup_expired()
        similarity_cleaned = await self._similarity_cache.cleanup_expired()

        # Clean up content mapping if embedding cache is empty
        embedding_stats = await self._embedding_cache.get_stats()
        if embedding_stats["size"] == 0:
            self._content_to_key.clear()

        return embedding_cleaned + similarity_cleaned


class EmbeddingData:
    """Container for cached embedding data."""

    def __init__(
        self,
        content: str,
        embedding: np.ndarray,
        content_hash: str,
        created_at: datetime,
    ) -> None:
        self.content = content
        self.embedding = embedding
        self.content_hash = content_hash
        self.created_at = created_at

    def __repr__(self) -> str:
        return f"EmbeddingData(content='{self.content[:50]}...', shape={self.embedding.shape})"


class SimilarityResult:
    """Container for cached similarity calculation results."""

    def __init__(
        self,
        query_hash: str,
        candidate_keys: list[str],
        similarities: list[float],
        calculated_at: datetime,
    ) -> None:
        self.query_hash = query_hash
        self.candidate_keys = candidate_keys
        self.similarities = similarities
        self.calculated_at = calculated_at

    def __repr__(self) -> str:
        return f"SimilarityResult(query_hash='{self.query_hash}', candidates={len(self.candidate_keys)})"
