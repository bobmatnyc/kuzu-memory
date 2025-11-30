"""
Auggie Memory and Learning Module for KuzuMemory Integration.

Handles response learning, pattern recognition, and memory synchronization.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from ..core.models import Memory, MemoryType

logger = logging.getLogger(__name__)


class LearningPattern:
    """Represents a learned pattern from conversations."""

    def __init__(self, pattern_id: str, pattern_type: str, pattern_data: dict[str, Any]) -> None:
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.pattern_data = pattern_data
        self.confidence = 0.5
        self.usage_count = 0
        self.created_at = datetime.now()
        self.last_used: datetime | None = None
        self.success_rate = 1.0

    def update_confidence(self, feedback_score: float) -> None:
        """Update pattern confidence based on feedback."""
        # Use exponential moving average
        alpha = 0.1  # Learning rate
        self.confidence = alpha * feedback_score + (1 - alpha) * self.confidence
        self.confidence = max(0.0, min(1.0, self.confidence))

    def record_usage(self, success: bool = True) -> None:
        """Record pattern usage and update statistics."""
        self.usage_count += 1
        self.last_used = datetime.now()

        # Update success rate
        if self.usage_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Exponential moving average for success rate
            alpha = 0.2
            new_success = 1.0 if success else 0.0
            self.success_rate = alpha * new_success + (1 - alpha) * self.success_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert pattern to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "pattern_data": self.pattern_data,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "success_rate": self.success_rate,
        }


class ResponseLearner:
    """Learns from AI responses and user interactions to improve memory integration."""

    def __init__(self) -> None:
        self.learned_patterns: dict[str, LearningPattern] = {}
        self.feedback_history: list[dict[str, Any]] = []
        self.context_patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.response_quality_cache: deque[dict[str, Any]] = deque(maxlen=100)

        # Learning statistics
        self.total_interactions = 0
        self.positive_feedback_count = 0
        self.pattern_discovery_count = 0
        self.last_learning_event: datetime | None = None

    def process_interaction(
        self,
        prompt: str,
        response: str,
        context: dict[str, Any],
        feedback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a complete interaction for learning opportunities."""
        try:
            self.total_interactions += 1
            self.last_learning_event = datetime.now()

            learning_results: dict[str, Any] = {
                "patterns_discovered": [],
                "patterns_updated": [],
                "context_learned": [],
                "quality_assessment": {},
            }

            # Extract patterns from the interaction
            patterns = self._extract_patterns(prompt, response, context)
            for pattern in patterns:
                if pattern["pattern_id"] not in self.learned_patterns:
                    # New pattern discovered
                    learning_pattern = LearningPattern(
                        pattern["pattern_id"],
                        pattern["pattern_type"],
                        pattern["pattern_data"],
                    )
                    self.learned_patterns[pattern["pattern_id"]] = learning_pattern
                    learning_results["patterns_discovered"].append(pattern["pattern_id"])
                    self.pattern_discovery_count += 1
                else:
                    # Update existing pattern
                    existing_pattern = self.learned_patterns[pattern["pattern_id"]]
                    existing_pattern.record_usage()
                    learning_results["patterns_updated"].append(pattern["pattern_id"])

            # Learn from context
            context_learning = self._learn_context_patterns(prompt, context)
            learning_results["context_learned"] = context_learning

            # Assess response quality
            quality_assessment = self._assess_response_quality(prompt, response, context)
            learning_results["quality_assessment"] = quality_assessment
            self.response_quality_cache.append(quality_assessment)

            # Process feedback if provided
            if feedback:
                self._process_feedback(feedback, learning_results)

            return learning_results

        except Exception as e:
            logger.error(f"Error processing interaction for learning: {e}")
            return {}

    def _extract_patterns(
        self, prompt: str, response: str, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract learnable patterns from the interaction."""
        patterns = []

        try:
            # Pattern 1: Successful question-answer pairs
            if len(response) > 50 and "error" not in response.lower():
                pattern_id = f"qa_pattern_{hash(prompt[:50]) % 10000}"
                patterns.append(
                    {
                        "pattern_id": pattern_id,
                        "pattern_type": "question_answer",
                        "pattern_data": {
                            "question_keywords": self._extract_keywords(prompt),
                            "response_length": len(response),
                            "context_size": len(context.get("memories", [])),
                            "response_sentiment": "positive",  # Simplified sentiment
                        },
                    }
                )

            # Pattern 2: Context usage patterns
            memories_used = context.get("memories_used", 0)
            if memories_used > 0:
                pattern_id = f"context_pattern_{hash(str(memories_used)) % 10000}"
                patterns.append(
                    {
                        "pattern_id": pattern_id,
                        "pattern_type": "context_usage",
                        "pattern_data": {
                            "memories_used": memories_used,
                            "prompt_type": self._classify_prompt_type(prompt),
                            "effectiveness": ("high" if len(response) > 100 else "medium"),
                        },
                    }
                )

            # Pattern 3: Domain-specific patterns
            domain = self._identify_domain(prompt)
            if domain:
                pattern_id = f"domain_pattern_{domain}_{hash(prompt[:30]) % 1000}"
                patterns.append(
                    {
                        "pattern_id": pattern_id,
                        "pattern_type": "domain_specific",
                        "pattern_data": {
                            "domain": domain,
                            "question_complexity": ("high" if len(prompt) > 100 else "low"),
                            "response_quality": ("high" if len(response) > 200 else "medium"),
                        },
                    }
                )

        except Exception as e:
            logger.warning(f"Error extracting patterns: {e}")

        return patterns

    def _learn_context_patterns(self, prompt: str, context: dict[str, Any]) -> list[str]:
        """Learn patterns about effective context usage."""
        learned_contexts = []

        try:
            # Analyze which types of context were most useful
            if context.get("memories"):
                for memory in context["memories"]:
                    memory_type = memory.get("type", "unknown")
                    relevance = memory.get("relevance", 0.0)

                    if relevance > 0.8:  # High relevance threshold
                        context_key = f"{memory_type}_high_relevance"
                        if context_key not in self.context_patterns:
                            self.context_patterns[context_key] = []

                        self.context_patterns[context_key].append(
                            {
                                "prompt_keywords": self._extract_keywords(prompt),
                                "memory_content": memory.get("content", "")[:100],
                                "relevance": relevance,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                        learned_contexts.append(context_key)

        except Exception as e:
            logger.warning(f"Error learning context patterns: {e}")

        return learned_contexts

    def _assess_response_quality(
        self, prompt: str, response: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Assess the quality of the AI response for learning purposes."""
        assessment = {
            "length_score": 0.0,
            "coherence_score": 0.0,
            "context_usage_score": 0.0,
            "overall_score": 0.0,
        }

        try:
            # Length-based scoring (simple heuristic)
            if len(response) < 20:
                assessment["length_score"] = 0.2
            elif len(response) < 100:
                assessment["length_score"] = 0.6
            elif len(response) < 500:
                assessment["length_score"] = 1.0
            else:
                assessment["length_score"] = 0.8  # Too long might be verbose

            # Coherence scoring (simplified)
            coherence_indicators = [
                "however",
                "therefore",
                "because",
                "additionally",
                "furthermore",
                "in conclusion",
                "for example",
                "specifically",
                "moreover",
            ]
            coherence_count = sum(
                1 for indicator in coherence_indicators if indicator in response.lower()
            )
            assessment["coherence_score"] = min(1.0, coherence_count / 3)

            # Context usage scoring
            context_memories = context.get("memories", [])
            if context_memories:
                # Check if response seems to incorporate context
                context_keywords = set()
                for memory in context_memories:
                    context_keywords.update(self._extract_keywords(memory.get("content", "")))

                response_keywords = set(self._extract_keywords(response))
                keyword_overlap = len(context_keywords.intersection(response_keywords))
                assessment["context_usage_score"] = min(
                    1.0, keyword_overlap / max(len(context_keywords), 1)
                )

            # Overall score (weighted average)
            assessment["overall_score"] = (
                0.3 * assessment["length_score"]
                + 0.4 * assessment["coherence_score"]
                + 0.3 * assessment["context_usage_score"]
            )

        except Exception as e:
            logger.warning(f"Error assessing response quality: {e}")

        return assessment

    def _process_feedback(self, feedback: dict[str, Any], learning_results: dict[str, Any]) -> None:
        """Process user feedback to improve learning."""
        try:
            self.feedback_history.append(
                {
                    "feedback": feedback,
                    "learning_results": learning_results,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Update pattern confidences based on feedback
            feedback_score = feedback.get("score", 0.5)  # Assume 0-1 scale
            if feedback_score > 0.7:
                self.positive_feedback_count += 1

            # Update patterns that were involved in this interaction
            for pattern_id in learning_results.get("patterns_updated", []):
                if pattern_id in self.learned_patterns:
                    self.learned_patterns[pattern_id].update_confidence(feedback_score)

        except Exception as e:
            logger.warning(f"Error processing feedback: {e}")

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> list[str]:
        """Extract keywords from text (simplified implementation)."""
        if not text:
            return []

        # Simple keyword extraction
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return keywords[:max_keywords]

    def _classify_prompt_type(self, prompt: str) -> str:
        """Classify the type of prompt (simplified)."""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["how", "what", "why", "when", "where"]):
            return "question"
        elif any(word in prompt_lower for word in ["create", "generate", "make", "build"]):
            return "generation"
        elif any(word in prompt_lower for word in ["explain", "describe", "tell me about"]):
            return "explanation"
        elif any(word in prompt_lower for word in ["fix", "debug", "solve", "error"]):
            return "problem_solving"
        else:
            return "general"

    def _identify_domain(self, prompt: str) -> str | None:
        """Identify the domain/topic of the prompt."""
        domain_keywords = {
            "programming": [
                "code",
                "function",
                "variable",
                "programming",
                "software",
                "development",
            ],
            "database": ["database", "sql", "query", "table", "schema", "data"],
            "web": ["html", "css", "javascript", "web", "frontend", "backend"],
            "system": ["system", "server", "deploy", "infrastructure", "devops"],
            "api": ["api", "endpoint", "rest", "http", "request", "response"],
        }

        prompt_lower = prompt.lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return domain

        return None

    def get_learning_statistics(self) -> dict[str, Any]:
        """Get comprehensive learning statistics."""
        stats = {
            "total_interactions": self.total_interactions,
            "patterns_discovered": self.pattern_discovery_count,
            "total_patterns": len(self.learned_patterns),
            "positive_feedback_rate": (
                self.positive_feedback_count / max(self.total_interactions, 1)
            )
            * 100,
            "average_response_quality": 0.0,
            "top_patterns": [],
            "domain_distribution": {},
            "context_effectiveness": {},
        }

        # Calculate average response quality
        if self.response_quality_cache:
            avg_quality = sum(
                assessment["overall_score"] for assessment in self.response_quality_cache
            )
            stats["average_response_quality"] = avg_quality / len(self.response_quality_cache)

        # Top patterns by usage
        sorted_patterns = sorted(
            self.learned_patterns.values(), key=lambda p: p.usage_count, reverse=True
        )

        stats["top_patterns"] = [
            {
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type,
                "usage_count": pattern.usage_count,
                "confidence": pattern.confidence,
                "success_rate": pattern.success_rate,
            }
            for pattern in sorted_patterns[:10]
        ]

        # Domain distribution
        domain_counts: defaultdict[str, int] = defaultdict(int)
        for pattern in self.learned_patterns.values():
            if pattern.pattern_type == "domain_specific":
                domain = pattern.pattern_data.get("domain", "unknown")
                domain_counts[domain] += 1

        stats["domain_distribution"] = dict(domain_counts)

        # Context effectiveness
        context_effectiveness = {}
        for context_type, patterns in self.context_patterns.items():
            if patterns:
                avg_relevance = sum(p.get("relevance", 0.0) for p in patterns) / len(patterns)
                context_effectiveness[context_type] = {
                    "pattern_count": len(patterns),
                    "average_relevance": avg_relevance,
                }

        stats["context_effectiveness"] = context_effectiveness

        return stats

    def get_recommendations(self) -> list[dict[str, Any]]:
        """Get recommendations based on learned patterns."""
        recommendations: list[dict[str, Any]] = []

        try:
            # Recommend high-confidence patterns
            high_confidence_patterns = [
                pattern
                for pattern in self.learned_patterns.values()
                if pattern.confidence > 0.8 and pattern.usage_count > 5
            ]

            if high_confidence_patterns:
                recommendations.append(
                    {
                        "type": "pattern_usage",
                        "message": f"Consider leveraging {len(high_confidence_patterns)} high-confidence patterns",
                        "patterns": [p.pattern_id for p in high_confidence_patterns[:5]],
                    }
                )

            # Recommend context improvements
            effective_contexts = {
                context_type: data
                for context_type, data in self.context_patterns.items()
                if len(data) > 3 and sum(p.get("relevance", 0) for p in data) / len(data) > 0.8
            }

            if effective_contexts:
                recommendations.append(
                    {
                        "type": "context_optimization",
                        "message": f"Focus on {len(effective_contexts)} highly effective context types",
                        "context_types": list(effective_contexts.keys()),
                    }
                )

            # Recommend learning opportunities
            positive_feedback_rate = (
                self.positive_feedback_count / max(self.total_interactions, 1)
            ) * 100
            if positive_feedback_rate < 70:
                recommendations.append(
                    {
                        "type": "feedback_improvement",
                        "message": "Consider collecting more user feedback to improve learning",
                        "current_rate": positive_feedback_rate,
                    }
                )

        except Exception as e:
            logger.warning(f"Error generating recommendations: {e}")

        return recommendations

    def export_learning_data(self, file_path: str) -> None:
        """Export learning data to a JSON file."""
        try:
            export_data = {
                "patterns": {
                    pattern_id: pattern.to_dict()
                    for pattern_id, pattern in self.learned_patterns.items()
                },
                "context_patterns": dict(self.context_patterns.items()),
                "statistics": self.get_learning_statistics(),
                "export_timestamp": datetime.now().isoformat(),
            }

            with open(file_path, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Learning data exported to {file_path}")

        except Exception as e:
            logger.error(f"Error exporting learning data: {e}")

    def import_learning_data(self, file_path: str) -> None:
        """Import learning data from a JSON file."""
        try:
            with open(file_path) as f:
                import_data = json.load(f)

            # Import patterns
            for pattern_id, pattern_data in import_data.get("patterns", {}).items():
                pattern = LearningPattern(
                    pattern_data["pattern_id"],
                    pattern_data["pattern_type"],
                    pattern_data["pattern_data"],
                )
                pattern.confidence = pattern_data["confidence"]
                pattern.usage_count = pattern_data["usage_count"]
                pattern.success_rate = pattern_data["success_rate"]

                if pattern_data["created_at"]:
                    pattern.created_at = datetime.fromisoformat(pattern_data["created_at"])
                if pattern_data["last_used"]:
                    pattern.last_used = datetime.fromisoformat(pattern_data["last_used"])

                self.learned_patterns[pattern_id] = pattern

            # Import context patterns
            for context_type, patterns in import_data.get("context_patterns", {}).items():
                self.context_patterns[context_type] = patterns

            logger.info(f"Learning data imported from {file_path}")

        except Exception as e:
            logger.error(f"Error importing learning data: {e}")


class MemorySynchronizer:
    """Handles synchronization between Auggie rules and KuzuMemory."""

    def __init__(self, memory_system: Any) -> None:
        self.memory_system = memory_system
        self.sync_history: list[dict[str, Any]] = []
        self.last_sync: datetime | None = None

    def sync_learned_patterns_to_memory(self, response_learner: ResponseLearner) -> None:
        """Synchronize learned patterns to memory system."""
        try:
            sync_count = 0

            for pattern in response_learner.learned_patterns.values():
                if pattern.confidence > 0.7 and pattern.usage_count > 3:
                    # Create memory from high-confidence pattern
                    memory_content = (
                        f"Learned pattern: {pattern.pattern_type} - {pattern.pattern_data}"
                    )

                    memory = Memory(
                        content=memory_content,
                        source="auggie_learning",
                        memory_type=MemoryType.PROCEDURAL,
                        metadata={
                            "pattern_id": pattern.pattern_id,
                            "confidence": pattern.confidence,
                            "usage_count": pattern.usage_count,
                            "success_rate": pattern.success_rate,
                            "auggie_generated": True,
                        },
                    )

                    self.memory_system.store_memory(memory)
                    sync_count += 1

            self.sync_history.append(
                {
                    "sync_type": "patterns_to_memory",
                    "patterns_synced": sync_count,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.last_sync = datetime.now()
            logger.info(f"Synchronized {sync_count} learned patterns to memory")

        except Exception as e:
            logger.error(f"Error syncing patterns to memory: {e}")

    def get_sync_status(self) -> dict[str, Any]:
        """Get synchronization status information."""
        return {
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "total_syncs": len(self.sync_history),
            "recent_syncs": self.sync_history[-5:] if self.sync_history else [],
        }
