"""
Auggie Integration for KuzuMemory.

Main integration interface that coordinates rules engine and memory learning.
Refactored to use modular components for better maintainability.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..utils.exceptions import KuzuMemoryError
from .auggie_memory import MemorySynchronizer, ResponseLearner
from .auggie_rules import AuggieRuleEngine, RuleType

logger = logging.getLogger(__name__)


class AuggieIntegration:
    """
    Main Auggie integration class that coordinates rule engine and learning.

    Provides intelligent memory-driven prompt modification and response learning
    through integration with Auggie's rules system.
    """

    def __init__(
        self,
        kuzu_memory: Any = None,
        project_root: Path | None = None,
        memory_system: Any = None,
        config: Any = None,
    ) -> None:
        """Initialize Auggie integration with project context."""
        self.project_root = project_root or Path.cwd()

        # Accept either memory_system or kuzu_memory parameter for backwards compatibility
        # kuzu_memory is the primary parameter for test compatibility
        if kuzu_memory is not None:
            self.memory_system = kuzu_memory
            self.kuzu_memory = kuzu_memory  # Alias for test compatibility
        elif memory_system is not None:
            self.memory_system = memory_system
            self.kuzu_memory = memory_system  # Alias for test compatibility
        else:
            self.memory_system = None
            self.kuzu_memory = None

        # Initialize components
        self.rule_engine = AuggieRuleEngine()
        self.response_learner = ResponseLearner()

        # Memory synchronizer (initialized when memory system is available)
        self.memory_synchronizer = None
        if self.memory_system:
            self.memory_synchronizer = MemorySynchronizer(self.memory_system)

        # Integration statistics
        self.integration_stats: dict[str, Any] = {
            "prompts_enhanced": 0,
            "responses_learned": 0,
            "rules_executed": 0,
            "patterns_discovered": 0,
            "last_activity": None,
            "integration_started": datetime.now(),
        }

        # Configuration
        default_config = {
            "auto_learning": True,
            "rule_execution_timeout": 5.0,
            "max_context_memories": 10,
            "learning_threshold": 0.7,
            "sync_interval_hours": 24,
        }

        # Merge user-provided config with defaults
        self.config = default_config.copy()
        if config:
            self.config.update(config)

        logger.info("Auggie integration initialized")

    def is_auggie_project(self) -> bool:
        """Check if the current project has Auggie integration setup."""
        auggie_indicators = [
            self.project_root / ".augment",
            self.project_root / "AGENTS.md",
            self.project_root / ".augment" / "rules",
            self.project_root / "auggie.json",
        ]

        return any(indicator.exists() for indicator in auggie_indicators)

    def is_integration_active(self) -> bool:
        """Check if Auggie integration is active and working."""
        try:
            # Check if rule engine is functional
            if not self.rule_engine.rules:
                return False

            # Check if we have recent activity
            if self.integration_stats["last_activity"]:
                last_activity = datetime.fromisoformat(self.integration_stats["last_activity"])
                if datetime.now() - last_activity > timedelta(days=7):
                    return False

            return True
        except Exception:
            return False

    def setup_project_integration(self) -> None:
        """Set up Auggie integration for the current project."""
        try:
            augment_dir = self.project_root / ".augment"
            augment_dir.mkdir(exist_ok=True)

            rules_dir = augment_dir / "rules"
            rules_dir.mkdir(exist_ok=True)

            # Create basic configuration
            config_path = augment_dir / "kuzu-memory-config.json"
            if not config_path.exists():
                config_data = {
                    "integration_type": "kuzu-memory",
                    "auto_learning": True,
                    "rule_execution": True,
                    "memory_sync": True,
                    "created": datetime.now().isoformat(),
                }

                with config_path.open("w") as f:
                    json.dump(config_data, f, indent=2)

            logger.info("Auggie project integration set up successfully")

        except Exception as e:
            logger.error(f"Failed to set up Auggie integration: {e}")
            raise KuzuMemoryError(f"Integration setup failed: {e}")

    def enhance_prompt(
        self,
        prompt: str,
        user_id: str = "default",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Enhance a prompt using Auggie rules and memory context.

        Args:
            prompt: Original prompt to enhance
            user_id: User identifier for context
            context: Additional context information

        Returns:
            Dictionary with enhanced prompt and metadata, or None if no enhancement
        """
        try:
            self.integration_stats["prompts_enhanced"] += 1
            self.integration_stats["last_activity"] = datetime.now().isoformat()

            # Prepare context for rule engine
            rule_context = {
                "prompt": prompt,
                "user_id": user_id,
                "prompt_length": len(prompt),
                "timestamp": datetime.now().isoformat(),
                **(context or {}),
            }

            # Add memory context if available
            if self.memory_system:
                try:
                    # Use attach_memories which returns AttachResult with memories
                    attach_result = self.memory_system.attach_memories(
                        prompt, max_memories=self.config["max_context_memories"]
                    )
                    relevant_memories = attach_result.memories if attach_result else []
                    rule_context["memories"] = [
                        {
                            "content": mem.content,
                            "type": mem.memory_type.value,
                            "relevance": getattr(mem, "relevance_score", 0.0),
                            "source": mem.source,
                        }
                        for mem in relevant_memories
                    ]
                    rule_context["memories_available"] = len(relevant_memories)
                except Exception as e:
                    logger.warning(f"Failed to get memory context: {e}")
                    rule_context["memories"] = []
                    rule_context["memories_available"] = 0

            # Execute context enhancement rules
            modifications = self.rule_engine.execute_rules(
                rule_context,
                rule_types=[RuleType.CONTEXT_ENHANCEMENT, RuleType.PROMPT_MODIFICATION],
            )

            self.integration_stats["rules_executed"] += 1

            if not modifications:
                return None

            # Build enhanced prompt
            enhanced_prompt = prompt
            added_context = []

            # Apply context additions
            if "added_context" in modifications:
                for context_addition in modifications["added_context"]:
                    if "max_memories" in context_addition:
                        max_memories = context_addition["max_memories"]
                        relevant_memories = rule_context.get("memories", [])[:max_memories]

                        if relevant_memories:
                            context_text = "\n".join(
                                [
                                    (
                                        f"• {mem['content'][:200]}..."
                                        if len(mem["content"]) > 200
                                        else f"• {mem['content']}"
                                    )
                                    for mem in relevant_memories
                                ]
                            )
                            added_context.append(f"Relevant context:\n{context_text}")

            # Apply prompt modifications
            if "prompt_modifications" in modifications:
                for modification in modifications["prompt_modifications"]:
                    if "prefix" in modification:
                        enhanced_prompt = f"{modification['prefix']} {enhanced_prompt}"
                    if "suffix" in modification:
                        enhanced_prompt = f"{enhanced_prompt} {modification['suffix']}"

            # Construct final enhanced prompt
            if added_context:
                context_section = "\n\n".join(added_context)
                enhanced_prompt = f"{context_section}\n\nQuestion: {enhanced_prompt}"

            return {
                "enhanced_prompt": enhanced_prompt,
                "original_prompt": prompt,
                "context": "\n\n".join(added_context) if added_context else "",
                "memories_count": rule_context.get("memories_available", 0),
                "rules_applied": len([r for r in modifications if modifications[r]]),
                "modifications": modifications,
            }

        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            return None

    def learn_from_conversation(self, conversation_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Learn from a complete conversation interaction.

        Args:
            conversation_data: Dictionary containing prompt, response, feedback, etc.

        Returns:
            Learning results or None if learning failed
        """
        try:
            if not self.config["auto_learning"]:
                return None

            self.integration_stats["responses_learned"] += 1
            self.integration_stats["last_activity"] = datetime.now().isoformat()

            prompt = conversation_data.get("prompt", "")
            response = conversation_data.get("response", "")
            feedback = conversation_data.get("feedback")
            user_id = conversation_data.get("user_id", "default")

            # Prepare context for learning
            learning_context = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "response_length": len(response),
                "prompt_length": len(prompt),
            }

            # Process the interaction for learning
            learning_results = self.response_learner.process_interaction(
                prompt,
                response,
                learning_context,
                (
                    {"score": 0.8} if feedback else None
                ),  # Default positive feedback if none provided
            )

            # Update integration statistics
            self.integration_stats["patterns_discovered"] += len(
                learning_results.get("patterns_discovered", [])
            )

            # Sync to memory system if available and configured
            if (
                self.memory_synchronizer
                and learning_results.get("patterns_discovered")
                and len(learning_results["patterns_discovered"]) > 0
            ):
                try:
                    self.memory_synchronizer.sync_learned_patterns_to_memory(self.response_learner)
                except Exception as e:
                    logger.warning(f"Failed to sync patterns to memory: {e}")

            return {
                "success": True,
                "learning_results": learning_results,
                "memory_id": f"learning_{datetime.now().timestamp()}",
                "patterns_count": len(learning_results.get("patterns_discovered", [])),
                "rules_updated": len(learning_results.get("patterns_updated", [])),
            }

        except Exception as e:
            logger.error(f"Error learning from conversation: {e}")
            return None

    def get_rules_summary(self) -> dict[str, Any]:
        """Get summary information about current rules."""
        try:
            augment_dir = self.project_root / ".augment"
            rules_dir = augment_dir / "rules"

            rule_files = []
            if rules_dir.exists():
                for rule_file in rules_dir.glob("*.md"):
                    rule_files.append(
                        {
                            "path": str(rule_file.relative_to(self.project_root)),
                            "name": rule_file.name,
                            "last_modified": datetime.fromtimestamp(
                                rule_file.stat().st_mtime
                            ).isoformat(),
                            "size": rule_file.stat().st_size,
                        }
                    )

            engine_rules = self.rule_engine.get_rule_statistics()

            return {
                "files": rule_files,
                "memory_rules": [
                    {
                        "id": rule.id,
                        "name": rule.name,
                        "description": rule.description,
                        "type": rule.rule_type.value,
                        "enabled": rule.enabled,
                        "usage_count": rule.execution_count,
                    }
                    for rule in self.rule_engine.rules.values()
                ],
                "active_count": engine_rules["enabled_rules"],
                "total_count": engine_rules["total_rules"],
                "statistics": engine_rules,
            }

        except Exception as e:
            logger.error(f"Error getting rules summary: {e}")
            return {}

    def get_integration_stats(self) -> dict[str, Any]:
        """Get comprehensive integration statistics."""
        stats = self.integration_stats.copy()

        # Add component statistics
        stats["rule_engine"] = self.rule_engine.get_rule_statistics()
        stats["response_learner"] = self.response_learner.get_learning_statistics()

        # Add synchronization status
        if self.memory_synchronizer:
            stats["memory_sync"] = self.memory_synchronizer.get_sync_status()

        # Calculate derived metrics
        if stats["prompts_enhanced"] > 0:
            stats["enhancement_rate"] = (stats["rules_executed"] / stats["prompts_enhanced"]) * 100
        else:
            stats["enhancement_rate"] = 0.0

        # Add health information
        stats["health"] = {
            "rule_engine": "healthy" if self.rule_engine.rules else "inactive",
            "learning_system": ("healthy" if stats["responses_learned"] > 0 else "inactive"),
            "memory_sync": "healthy" if self.memory_synchronizer else "unavailable",
        }

        return stats

    def update_configuration(self, config_updates: dict[str, Any]) -> None:
        """Update integration configuration."""
        self.config.update(config_updates)
        logger.info(f"Configuration updated: {config_updates}")

    def get_recommendations(self) -> list[dict[str, Any]]:
        """Get recommendations for improving integration effectiveness."""
        recommendations = []

        try:
            # Get recommendations from response learner
            learning_recommendations = self.response_learner.get_recommendations()
            recommendations.extend(learning_recommendations)

            # Add integration-specific recommendations
            if self.integration_stats["prompts_enhanced"] == 0:
                recommendations.append(
                    {
                        "type": "integration_usage",
                        "message": "No prompts have been enhanced yet. Try using the enhance functionality.",
                        "priority": "high",
                    }
                )

            if not self.memory_system:
                recommendations.append(
                    {
                        "type": "memory_system",
                        "message": "Memory system not connected. Consider initializing memory integration.",
                        "priority": "medium",
                    }
                )

            # Rule-based recommendations
            rule_stats = self.rule_engine.get_rule_statistics()
            if rule_stats["total_executions"] == 0:
                recommendations.append(
                    {
                        "type": "rule_execution",
                        "message": "No rules have been executed. Check rule conditions and contexts.",
                        "priority": "medium",
                    }
                )

        except Exception as e:
            logger.warning(f"Error generating recommendations: {e}")

        return recommendations

    def export_integration_data(self, file_path: str) -> None:
        """Export all integration data to a file."""
        try:
            export_data = {
                "integration_stats": self.integration_stats,
                "configuration": self.config,
                "rules_summary": self.get_rules_summary(),
                "learning_stats": self.response_learner.get_learning_statistics(),
                "export_timestamp": datetime.now().isoformat(),
            }

            with open(file_path, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Integration data exported to {file_path}")

        except Exception as e:
            logger.error(f"Error exporting integration data: {e}")

    def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Clean up old integration data."""
        try:
            # Clean up rule engine history
            self.rule_engine.cleanup_old_history(days_to_keep)

            # Clean up learning data
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # Remove old feedback history
            self.response_learner.feedback_history = [
                record
                for record in self.response_learner.feedback_history
                if datetime.fromisoformat(record["timestamp"]) > cutoff_date
            ]

            logger.info(f"Cleaned up integration data older than {days_to_keep} days")

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
