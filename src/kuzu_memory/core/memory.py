"""
Main KuzuMemory API class.

Provides the primary interface for memory operations with the two main methods:
attach_memories() and generate_memories() with performance targets of <10ms and <20ms.
"""

import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .config import KuzuMemoryConfig
from .models import MemoryContext, Memory
from ..storage.kuzu_adapter import create_kuzu_adapter
from ..storage.memory_store import MemoryStore
from ..recall.coordinator import RecallCoordinator
from ..utils.exceptions import (
    KuzuMemoryError,
    DatabaseError,
    ConfigurationError,
    PerformanceError,
    ValidationError,
)
# Removed validation import to avoid circular dependency

logger = logging.getLogger(__name__)


class KuzuMemory:
    """
    Main interface for KuzuMemory operations.
    
    Provides fast, offline memory capabilities for AI applications with
    two primary methods: attach_memories() and generate_memories().
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize KuzuMemory.
        
        Args:
            db_path: Path to database file (default: .kuzu_memory/memories.db)
            config: Optional configuration dict or KuzuMemoryConfig object
            
        Raises:
            ConfigurationError: If configuration is invalid
            DatabaseError: If database initialization fails
        """
        try:
            # Set up database path
            db_path_resolved = db_path or Path(".kuzu_memory/memories.db")
            if isinstance(db_path_resolved, str):
                db_path_resolved = Path(db_path_resolved)
            self.db_path = db_path_resolved
            
            # Set up configuration
            if isinstance(config, KuzuMemoryConfig):
                self.config = config
            elif isinstance(config, dict):
                self.config = KuzuMemoryConfig.from_dict(config)
            elif config is None:
                self.config = KuzuMemoryConfig.default()
            else:
                raise ConfigurationError(f"Invalid config type: {type(config)}")
            
            # Validate configuration
            self.config.validate()
            
            # Initialize components
            self._initialize_components()
            
            # Track initialization time
            self._initialized_at = datetime.now()
            
            logger.info(f"KuzuMemory initialized with database at {self.db_path}")
            
        except Exception as e:
            if isinstance(e, (ConfigurationError, DatabaseError)):
                raise
            raise KuzuMemoryError(f"Failed to initialize KuzuMemory: {e}")
    
    def _initialize_components(self) -> None:
        """Initialize internal components."""
        try:
            # Initialize database adapter (CLI or Python API based on config)
            self.db_adapter = create_kuzu_adapter(self.db_path, self.config)
            if hasattr(self.db_adapter, 'initialize'):
                self.db_adapter.initialize()
            
            # Initialize memory store
            self.memory_store = MemoryStore(self.db_adapter, self.config)
            
            # Initialize recall coordinator
            self.recall_coordinator = RecallCoordinator(self.db_adapter, self.config)
            
            # Performance tracking
            self._performance_stats = {
                'attach_memories_calls': 0,
                'generate_memories_calls': 0,
                'avg_attach_time_ms': 0.0,
                'avg_generate_time_ms': 0.0,
                'total_memories_generated': 0,
                'total_memories_recalled': 0,
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to initialize components: {e}")
    
    def attach_memories(
        self,
        prompt: str,
        max_memories: int = 10,
        strategy: str = "auto",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: str = "default"
    ) -> MemoryContext:
        """
        PRIMARY API METHOD 1: Retrieve relevant memories for a prompt.
        
        Args:
            prompt: User input to find memories for
            max_memories: Maximum number of memories to return
            strategy: Recall strategy (auto|keyword|entity|temporal)
            user_id: Optional user ID for filtering
            session_id: Optional session ID for filtering
            agent_id: Agent ID for filtering
            
        Returns:
            MemoryContext object containing:
                - original_prompt: The input prompt
                - enhanced_prompt: Prompt with memories injected
                - memories: List of relevant Memory objects
                - confidence: Confidence score (0-1)
                
        Performance Requirement: Must complete in <10ms
        
        Raises:
            ValidationError: If input parameters are invalid
            RecallError: If memory recall fails
            PerformanceError: If operation exceeds 10ms
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not prompt or not prompt.strip():
                raise ValidationError("prompt", prompt, "cannot be empty")
            
            if max_memories <= 0:
                raise ValidationError("max_memories", str(max_memories), "must be positive")
            
            if strategy not in ["auto", "keyword", "entity", "temporal"]:
                raise ValidationError("strategy", strategy, "must be one of: auto, keyword, entity, temporal")
            
            # Execute recall
            context = self.recall_coordinator.attach_memories(
                prompt=prompt,
                max_memories=max_memories,
                strategy=strategy,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id
            )
            
            # Update performance statistics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_attach_stats(execution_time_ms, len(context.memories))
            
            # Check performance requirement
            if execution_time_ms > self.config.performance.max_recall_time_ms:
                if self.config.performance.enable_performance_monitoring:
                    raise PerformanceError(
                        f"attach_memories took {execution_time_ms:.1f}ms, exceeding target of {self.config.performance.max_recall_time_ms}ms"
                    )
                else:
                    logger.warning(f"attach_memories took {execution_time_ms:.1f}ms (target: {self.config.performance.max_recall_time_ms}ms)")
            
            logger.debug(f"attach_memories completed in {execution_time_ms:.1f}ms with {len(context.memories)} memories")
            
            return context
            
        except Exception as e:
            if isinstance(e, (ValidationError, PerformanceError)):
                raise
            raise KuzuMemoryError(f"attach_memories failed: {e}")
    
    def generate_memories(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "conversation",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: str = "default"
    ) -> List[str]:
        """
        PRIMARY API METHOD 2: Extract and store memories from content.
        
        Args:
            content: Text to extract memories from (usually LLM response)
            metadata: Additional context (user_id, session_id, etc.)
            source: Origin of content
            user_id: Optional user ID
            session_id: Optional session ID
            agent_id: Agent ID
            
        Returns:
            List of created memory IDs
            
        Performance Requirement: Must complete in <20ms
        
        Raises:
            ValidationError: If input parameters are invalid
            ExtractionError: If memory extraction fails
            PerformanceError: If operation exceeds 20ms
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not content or not content.strip():
                return []  # Empty content is valid, just return empty list
            
            # Basic content validation
            if len(content) > 100000:  # 100KB limit
                raise ValidationError("Content exceeds maximum length")
            
            # Execute memory generation
            memory_ids = self.memory_store.generate_memories(
                content=content,
                metadata=metadata,
                source=source,
                user_id=user_id,
                session_id=session_id,
                agent_id=agent_id
            )
            
            # Update performance statistics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_generate_stats(execution_time_ms, len(memory_ids))
            
            # Check performance requirement
            if execution_time_ms > self.config.performance.max_generation_time_ms:
                if self.config.performance.enable_performance_monitoring:
                    raise PerformanceError(
                        f"generate_memories took {execution_time_ms:.1f}ms, exceeding target of {self.config.performance.max_generation_time_ms}ms"
                    )
                else:
                    logger.warning(f"generate_memories took {execution_time_ms:.1f}ms (target: {self.config.performance.max_generation_time_ms}ms)")
            
            logger.debug(f"generate_memories completed in {execution_time_ms:.1f}ms with {len(memory_ids)} memories")
            
            return memory_ids
            
        except Exception as e:
            if isinstance(e, (ValidationError, PerformanceError)):
                raise
            raise KuzuMemoryError(f"generate_memories failed: {e}")
    
    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        Get a specific memory by its ID.
        
        Args:
            memory_id: Memory ID to retrieve
            
        Returns:
            Memory object or None if not found
        """
        try:
            return self.memory_store.get_memory_by_id(memory_id)
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None
    
    def cleanup_expired_memories(self) -> int:
        """
        Clean up expired memories based on retention policies.

        Returns:
            Number of memories cleaned up
        """
        try:
            return self.memory_store.cleanup_expired_memories()
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return 0

    def get_recent_memories(self, limit: int = 10, **filters) -> List[Memory]:
        """
        Get recent memories, optionally filtered.

        Args:
            limit: Maximum number of memories to return
            **filters: Optional filters (e.g., memory_type, user_id)

        Returns:
            List of recent memories
        """
        try:
            return self.memory_store.get_recent_memories(limit=limit, **filters)
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []

    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        Get a specific memory by ID.

        Args:
            memory_id: Memory ID to retrieve

        Returns:
            Memory object or None if not found
        """
        try:
            return self.memory_store.get_memory_by_id(memory_id)
        except Exception as e:
            logger.error(f"Failed to get memory by ID: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the memory system.
        
        Returns:
            Dictionary with statistics from all components
        """
        try:
            return {
                'system_info': {
                    'initialized_at': self._initialized_at.isoformat(),
                    'db_path': str(self.db_path),
                    'config_version': self.config.version,
                },
                'performance_stats': self._performance_stats.copy(),
                'storage_stats': self.memory_store.get_storage_statistics(),
                'recall_stats': self.recall_coordinator.get_recall_statistics(),
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'error': str(e)}
    
    def _update_attach_stats(self, execution_time_ms: float, memories_count: int) -> None:
        """Update attach_memories performance statistics."""
        self._performance_stats['attach_memories_calls'] += 1
        self._performance_stats['total_memories_recalled'] += memories_count
        
        # Update average time
        total_calls = self._performance_stats['attach_memories_calls']
        current_avg = self._performance_stats['avg_attach_time_ms']
        new_avg = ((current_avg * (total_calls - 1)) + execution_time_ms) / total_calls
        self._performance_stats['avg_attach_time_ms'] = new_avg
    
    def _update_generate_stats(self, execution_time_ms: float, memories_count: int) -> None:
        """Update generate_memories performance statistics."""
        self._performance_stats['generate_memories_calls'] += 1
        self._performance_stats['total_memories_generated'] += memories_count
        
        # Update average time
        total_calls = self._performance_stats['generate_memories_calls']
        current_avg = self._performance_stats['avg_generate_time_ms']
        new_avg = ((current_avg * (total_calls - 1)) + execution_time_ms) / total_calls
        self._performance_stats['avg_generate_time_ms'] = new_avg
    
    def close(self) -> None:
        """
        Close the KuzuMemory instance and clean up resources.
        """
        try:
            if hasattr(self, 'db_adapter'):
                self.db_adapter.close()
            logger.info("KuzuMemory closed successfully")
        except Exception as e:
            logger.error(f"Error closing KuzuMemory: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"KuzuMemory(db_path='{self.db_path}', initialized_at='{self._initialized_at}')"
