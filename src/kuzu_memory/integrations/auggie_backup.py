"""
Auggie Rules Integration for KuzuMemory.

Provides intelligent memory-driven prompt modification and response learning
through integration with Auggie's rules system.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from ..core.models import MemoryContext, MemoryType

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """Types of Auggie rules for memory integration."""

    CONTEXT_ENHANCEMENT = "context_enhancement"
    PROMPT_MODIFICATION = "prompt_modification"
    RESPONSE_FILTERING = "response_filtering"
    LEARNING_TRIGGER = "learning_trigger"
    MEMORY_PRIORITIZATION = "memory_prioritization"


class RulePriority(Enum):
    """Priority levels for rule execution."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class AuggieRule:
    """Represents an Auggie rule for memory integration."""

    id: str
    name: str
    description: str
    rule_type: RuleType
    priority: RulePriority
    conditions: dict[str, Any]
    actions: dict[str, Any]
    enabled: bool = True
    created_at: datetime | None = None
    last_executed: datetime | None = None
    execution_count: int = 0
    success_rate: float = 1.0

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now()

    def matches_conditions(self, context: dict[str, Any]) -> bool:
        """Check if rule conditions match the given context."""
        try:
            for condition_key, condition_value in self.conditions.items():
                if condition_key not in context:
                    return False

                context_value = context[condition_key]

                # Handle different condition types
                if isinstance(condition_value, dict):
                    if "contains" in condition_value:
                        if condition_value["contains"].lower() not in str(context_value).lower():
                            return False
                    elif "equals" in condition_value:
                        if context_value != condition_value["equals"]:
                            return False
                    elif "greater_than" in condition_value:
                        if float(context_value) <= float(condition_value["greater_than"]):
                            return False
                    elif "less_than" in condition_value:
                        if float(context_value) >= float(condition_value["less_than"]):
                            return False
                    elif "in" in condition_value:
                        if context_value not in condition_value["in"]:
                            return False
                elif context_value != condition_value:
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error evaluating rule conditions for {self.id}: {e}")
            return False

    def execute_actions(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute rule actions and return modifications."""
        try:
            self.last_executed = datetime.now()
            self.execution_count += 1

            modifications = {}

            for action_key, action_value in self.actions.items():
                if action_key == "add_context":
                    modifications["added_context"] = action_value
                elif action_key == "modify_prompt":
                    modifications["prompt_modifications"] = action_value
                elif action_key == "set_priority":
                    modifications["memory_priority"] = action_value
                elif action_key == "filter_memories":
                    modifications["memory_filters"] = action_value
                elif action_key == "learn_from_response":
                    modifications["learning_config"] = action_value
                else:
                    modifications[action_key] = action_value

            return modifications

        except Exception as e:
            logger.error(f"Error executing rule actions for {self.id}: {e}")
            return {}


class AuggieRuleEngine:
    """Rule engine for memory-driven AI interactions."""

    def __init__(self, kuzu_memory: Any = None) -> None:
        """Initialize the rule engine."""
        self.kuzu_memory = kuzu_memory
        self.rules: dict[str, AuggieRule] = {}
        self.rule_execution_history: list[dict[str, Any]] = []
        self.learning_callbacks: list[Callable[[dict[str, Any]], None]] = []

        # Load default rules
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default Auggie rules for memory integration."""
        default_rules = [
            # Context Enhancement Rules
            AuggieRule(
                id="enhance_with_identity",
                name="Enhance with Identity Context",
                description="Add user identity information to prompts",
                rule_type=RuleType.CONTEXT_ENHANCEMENT,
                priority=RulePriority.HIGH,
                conditions={
                    "has_identity_memories": True,
                    "prompt_length": {"greater_than": 10},
                },
                actions={
                    "add_context": "Include relevant identity information from memories",
                    "memory_types": ["identity"],
                },
            ),
            # Prompt Modification Rules
            AuggieRule(
                id="personalize_coding_help",
                name="Personalize Coding Assistance",
                description="Customize coding help based on user preferences",
                rule_type=RuleType.PROMPT_MODIFICATION,
                priority=RulePriority.MEDIUM,
                conditions={
                    "prompt_category": "coding",
                    "has_preference_memories": True,
                },
                actions={
                    "modify_prompt": {
                        "add_preferences": True,
                        "include_tech_stack": True,
                        "mention_experience_level": True,
                    }
                },
            ),
            # Learning Trigger Rules
            AuggieRule(
                id="learn_from_corrections",
                name="Learn from User Corrections",
                description="Trigger learning when user corrects AI responses",
                rule_type=RuleType.LEARNING_TRIGGER,
                priority=RulePriority.CRITICAL,
                conditions={
                    "response_contains": {"contains": "actually"},
                    "user_correction": True,
                },
                actions={
                    "learn_from_response": {
                        "extract_correction": True,
                        "update_memories": True,
                        "confidence_boost": 0.9,
                    }
                },
            ),
            # Memory Prioritization Rules
            AuggieRule(
                id="prioritize_recent_decisions",
                name="Prioritize Recent Decisions",
                description="Give higher priority to recent decision memories",
                rule_type=RuleType.MEMORY_PRIORITIZATION,
                priority=RulePriority.MEDIUM,
                conditions={
                    "memory_type": "decision",
                    "memory_age_days": {"less_than": 7},
                },
                actions={"set_priority": 0.9, "boost_confidence": 0.1},
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: AuggieRule) -> None:
        """Add a rule to the engine."""
        self.rules[rule.id] = rule
        logger.info(f"Added rule: {rule.name} ({rule.id})")

    def remove_rule(self, rule_id: str) -> None:
        """Remove a rule from the engine."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed rule: {rule_id}")

    def get_applicable_rules(self, context: dict[str, Any]) -> list[AuggieRule]:
        """Get rules that apply to the given context."""
        applicable_rules = []

        for rule in self.rules.values():
            if rule.enabled and rule.matches_conditions(context):
                applicable_rules.append(rule)

        # Sort by priority
        applicable_rules.sort(key=lambda r: r.priority.value)
        return applicable_rules

    def execute_rules(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute applicable rules and return combined modifications."""
        applicable_rules = self.get_applicable_rules(context)

        # Type-safe initialization with explicit types
        context_additions: list[Any] = []
        prompt_modifications: dict[str, Any] = {}
        memory_filters: dict[str, Any] = {}
        learning_triggers: list[Any] = []
        executed_rules: list[dict[str, Any]] = []

        combined_modifications: dict[str, Any] = {
            "context_additions": context_additions,
            "prompt_modifications": prompt_modifications,
            "memory_filters": memory_filters,
            "learning_triggers": learning_triggers,
            "executed_rules": executed_rules,
        }

        for rule in applicable_rules:
            try:
                modifications = rule.execute_actions(context)

                # Combine modifications with type-safe access
                if "added_context" in modifications:
                    context_additions.append(modifications["added_context"])

                if "prompt_modifications" in modifications:
                    prompt_modifications.update(modifications["prompt_modifications"])

                if "memory_filters" in modifications:
                    memory_filters.update(modifications["memory_filters"])

                if "learning_config" in modifications:
                    learning_triggers.append(modifications["learning_config"])

                executed_rules.append(
                    {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "modifications": modifications,
                    }
                )

                # Update rule success rate
                rule.success_rate = (
                    rule.success_rate * (rule.execution_count - 1) + 1.0
                ) / rule.execution_count

            except Exception as e:
                logger.error(f"Error executing rule {rule.id}: {e}")
                # Update rule success rate for failure
                rule.success_rate = (
                    rule.success_rate * (rule.execution_count - 1) + 0.0
                ) / rule.execution_count

        # Record execution history
        self.rule_execution_history.append(
            {
                "timestamp": datetime.now(),
                "context": context,
                "applicable_rules": [r.id for r in applicable_rules],
                "modifications": combined_modifications,
            }
        )

        return combined_modifications

    def add_learning_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Add a callback for learning events."""
        self.learning_callbacks.append(callback)

    def trigger_learning(self, learning_data: dict[str, Any]) -> None:
        """Trigger learning callbacks with data."""
        for callback in self.learning_callbacks:
            try:
                callback(learning_data)
            except Exception as e:
                logger.error(f"Error in learning callback: {e}")

    def get_rule_statistics(self) -> dict[str, Any]:
        """Get statistics about rule execution."""
        stats = {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "total_executions": len(self.rule_execution_history),
            "rule_performance": {},
        }

        for rule_id, rule in self.rules.items():
            stats["rule_performance"][rule_id] = {
                "name": rule.name,
                "execution_count": rule.execution_count,
                "success_rate": rule.success_rate,
                "last_executed": (rule.last_executed.isoformat() if rule.last_executed else None),
            }

        return stats


class ResponseLearner:
    """Learns from AI responses and user feedback to improve memory system."""

    def __init__(
        self, kuzu_memory: Any = None, rule_engine: AuggieRuleEngine | None = None
    ) -> None:
        """Initialize the response learner."""
        self.kuzu_memory = kuzu_memory
        self.rule_engine = rule_engine
        self.learning_history: list[dict[str, Any]] = []

        # Learning patterns
        self.correction_patterns = [
            r"actually,?\s*(.*)",
            r"no,?\s*(.*)",
            r"correction:?\s*(.*)",
            r"wait,?\s*(.*)",
            r"sorry,?\s*(.*)",
            r"let me correct that:?\s*(.*)",
        ]

    def learn_from_response(
        self,
        original_prompt: str,
        ai_response: str,
        user_feedback: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Learn from AI response and user feedback."""
        learning_results = {
            "timestamp": datetime.now(),
            "original_prompt": original_prompt,
            "ai_response": ai_response,
            "user_feedback": user_feedback,
            "extracted_memories": [],
            "updated_rules": [],
            "confidence_adjustments": {},
        }

        try:
            # Extract new memories from response
            if self.kuzu_memory and ai_response:
                new_memories = self._extract_memories_from_response(ai_response, context)
                learning_results["extracted_memories"] = new_memories

            # Learn from user feedback/corrections
            if user_feedback:
                corrections = self._extract_corrections(user_feedback)
                learning_results["corrections"] = corrections

                # Update memories based on corrections
                if corrections and self.kuzu_memory:
                    self._apply_corrections(corrections, context)

            # Analyze response quality and adjust rules
            quality_score = self._analyze_response_quality(ai_response, user_feedback)
            learning_results["quality_score"] = quality_score

            if quality_score < 0.7:  # Poor response
                self._adjust_rules_for_poor_response(original_prompt, context)

            # Record learning event
            self.learning_history.append(learning_results)

            return learning_results

        except Exception as e:
            logger.error(f"Error in response learning: {e}")
            learning_results["error"] = str(e)
            return learning_results

    def _extract_memories_from_response(
        self, response: str, context: dict[str, Any] | None = None
    ) -> list[str]:
        """Extract new memories from AI response."""
        if not self.kuzu_memory:
            return []

        try:
            # Use KuzuMemory to extract memories from the response
            user_id = context.get("user_id", "response_learner") if context else "response_learner"
            session_id = (
                context.get("session_id", "learning_session") if context else "learning_session"
            )

            memory_ids = self.kuzu_memory.generate_memories(
                content=response,
                user_id=user_id,
                session_id=session_id,
                source="ai_response",
                metadata={"learning": True, "response_extraction": True},
            )

            return memory_ids

        except Exception as e:
            logger.error(f"Error extracting memories from response: {e}")
            return []

    def _extract_corrections(self, feedback: str) -> list[dict[str, Any]]:
        """Extract corrections from user feedback."""
        import re

        corrections = []

        for pattern in self.correction_patterns:
            matches = re.finditer(pattern, feedback, re.IGNORECASE)
            for match in matches:
                correction_text = match.group(1).strip()
                if correction_text:
                    corrections.append(
                        {
                            "pattern": pattern,
                            "correction": correction_text,
                            "confidence": 0.9,
                        }
                    )

        return corrections

    def _apply_corrections(
        self, corrections: list[dict[str, Any]], context: dict[str, Any] | None = None
    ) -> None:
        """Apply corrections by updating memories."""
        if not self.kuzu_memory:
            return

        try:
            user_id = (
                context.get("user_id", "correction_learner") if context else "correction_learner"
            )
            session_id = (
                context.get("session_id", "correction_session") if context else "correction_session"
            )

            for correction in corrections:
                # Store correction as high-confidence memory
                self.kuzu_memory.generate_memories(
                    content=correction["correction"],
                    user_id=user_id,
                    session_id=session_id,
                    source="user_correction",
                    metadata={
                        "correction": True,
                        "confidence_boost": correction["confidence"],
                        "learning_source": "user_feedback",
                    },
                )

        except Exception as e:
            logger.error(f"Error applying corrections: {e}")

    def _analyze_response_quality(self, response: str, feedback: str | None = None) -> float:
        """Analyze the quality of AI response."""
        quality_score = 0.8  # Default score

        try:
            # Negative indicators
            if feedback:
                feedback_lower = feedback.lower()
                if any(word in feedback_lower for word in ["wrong", "incorrect", "no", "actually"]):
                    quality_score -= 0.3
                if any(word in feedback_lower for word in ["correction", "fix", "mistake"]):
                    quality_score -= 0.2

            # Positive indicators
            if len(response) > 50:  # Detailed response
                quality_score += 0.1

            # Ensure score is within bounds
            quality_score = max(0.0, min(1.0, quality_score))

            return quality_score

        except Exception as e:
            logger.error(f"Error analyzing response quality: {e}")
            return 0.5

    def _adjust_rules_for_poor_response(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> None:
        """Adjust rules based on poor response quality."""
        if not self.rule_engine:
            return

        try:
            # Create a rule to improve future similar prompts
            rule_id = f"improve_response_{hash(prompt) % 10000}"

            improvement_rule = AuggieRule(
                id=rule_id,
                name="Improve Response for Similar Prompts",
                description=f"Improve responses for prompts similar to: {prompt[:50]}...",
                rule_type=RuleType.CONTEXT_ENHANCEMENT,
                priority=RulePriority.HIGH,
                conditions={
                    "prompt_similarity": {"greater_than": 0.7},
                    "context_type": (
                        context.get("context_type", "general") if context else "general"
                    ),
                },
                actions={
                    "add_context": "Include more specific context and examples",
                    "memory_types": ["preference", "pattern", "solution"],
                },
            )

            self.rule_engine.add_rule(improvement_rule)

        except Exception as e:
            logger.error(f"Error adjusting rules for poor response: {e}")

    def get_learning_statistics(self) -> dict[str, Any]:
        """Get statistics about learning activities."""
        if not self.learning_history:
            return {"total_learning_events": 0}

        stats = {
            "total_learning_events": len(self.learning_history),
            "memories_extracted": sum(
                len(event.get("extracted_memories", [])) for event in self.learning_history
            ),
            "corrections_applied": sum(
                len(event.get("corrections", [])) for event in self.learning_history
            ),
            "average_quality_score": sum(
                event.get("quality_score", 0.5) for event in self.learning_history
            )
            / len(self.learning_history),
            "recent_events": (
                self.learning_history[-5:]
                if len(self.learning_history) > 5
                else self.learning_history
            ),
        }

        return stats


class AuggieIntegration:
    """Main integration class for KuzuMemory and Auggie rules system."""

    def __init__(self, kuzu_memory: Any = None, config: dict[str, Any] | None = None) -> None:
        """Initialize the Auggie integration."""
        self.kuzu_memory = kuzu_memory
        self.config = config or {}

        # Initialize components
        self.rule_engine = AuggieRuleEngine(kuzu_memory)
        self.response_learner = ResponseLearner(kuzu_memory, self.rule_engine)

        # Set up learning callbacks
        self.rule_engine.add_learning_callback(self._handle_learning_event)

        # Integration statistics
        self.integration_stats = {
            "prompts_enhanced": 0,
            "responses_learned": 0,
            "rules_triggered": 0,
            "memories_created": 0,
        }

    def enhance_prompt(
        self, prompt: str, user_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Enhance a prompt using memories and rules."""
        try:
            # Build context for rule evaluation
            rule_context = self._build_rule_context(prompt, user_id, context)

            # Get relevant memories
            memory_context = None
            if self.kuzu_memory:
                memory_context = self.kuzu_memory.attach_memories(
                    prompt=prompt,
                    user_id=user_id,
                    max_memories=self.config.get("max_context_memories", 8),
                )
                rule_context.update(self._extract_memory_features(memory_context))

            # Execute applicable rules
            rule_modifications = self.rule_engine.execute_rules(rule_context)

            # Apply modifications to create enhanced prompt
            enhanced_prompt = self._apply_prompt_modifications(
                prompt, memory_context, rule_modifications
            )

            # Update statistics
            self.integration_stats["prompts_enhanced"] += 1
            self.integration_stats["rules_triggered"] += len(
                rule_modifications.get("executed_rules", [])
            )

            return {
                "original_prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "memory_context": memory_context,
                "rule_modifications": rule_modifications,
                "context_summary": self._generate_context_summary(
                    memory_context, rule_modifications
                ),
            }

        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            return {
                "original_prompt": prompt,
                "enhanced_prompt": prompt,  # Fallback to original
                "error": str(e),
            }

    def learn_from_interaction(
        self,
        prompt: str,
        ai_response: str,
        user_feedback: str | None = None,
        user_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Learn from a complete AI interaction."""
        try:
            # Learn from the response
            learning_context = context or {}
            learning_context.update({"user_id": user_id})

            learning_results = self.response_learner.learn_from_response(
                original_prompt=prompt,
                ai_response=ai_response,
                user_feedback=user_feedback,
                context=learning_context,
            )

            # Update statistics
            self.integration_stats["responses_learned"] += 1
            self.integration_stats["memories_created"] += len(
                learning_results.get("extracted_memories", [])
            )

            return learning_results

        except Exception as e:
            logger.error(f"Error learning from interaction: {e}")
            return {"error": str(e)}

    def _build_rule_context(
        self, prompt: str, user_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Build context for rule evaluation."""
        rule_context = {
            "prompt": prompt,
            "prompt_length": len(prompt),
            "user_id": user_id,
            "timestamp": datetime.now(),
            "has_identity_memories": False,
            "has_preference_memories": False,
            "has_decision_memories": False,
            "prompt_category": self._categorize_prompt(prompt),
        }

        if context:
            rule_context.update(context)

        return rule_context

    def _extract_memory_features(self, memory_context: MemoryContext) -> dict[str, Any]:
        """Extract features from memory context for rule evaluation."""
        if not memory_context or not memory_context.memories:
            return {}

        memory_types = [mem.memory_type for mem in memory_context.memories]

        return {
            # Note: IDENTITY/DECISION/SOLUTION/STATUS don't exist in current MemoryType enum
            # Using SEMANTIC for general knowledge, PROCEDURAL for solutions
            "has_identity_memories": MemoryType.SEMANTIC in memory_types,  # Map to SEMANTIC
            "has_preference_memories": MemoryType.PREFERENCE in memory_types,
            "has_decision_memories": MemoryType.EPISODIC in memory_types,  # Map to EPISODIC
            "has_procedural_memories": MemoryType.PROCEDURAL in memory_types,
            "has_solution_memories": MemoryType.PROCEDURAL in memory_types,  # Map to PROCEDURAL
            "has_status_memories": MemoryType.WORKING in memory_types,  # Map to WORKING
            "memory_count": len(memory_context.memories),
            "memory_confidence": memory_context.confidence,
            "recall_strategy": memory_context.strategy_used,
        }

    def _categorize_prompt(self, prompt: str) -> str:
        """Categorize the prompt for rule matching."""
        prompt_lower = prompt.lower()

        # Coding-related keywords
        coding_keywords = [
            "code",
            "programming",
            "function",
            "class",
            "debug",
            "error",
            "api",
            "database",
        ]
        if any(keyword in prompt_lower for keyword in coding_keywords):
            return "coding"

        # Question keywords
        question_keywords = ["what", "how", "why", "when", "where", "which", "who"]
        if any(keyword in prompt_lower for keyword in question_keywords):
            return "question"

        # Task keywords
        task_keywords = ["create", "build", "make", "generate", "write", "design"]
        if any(keyword in prompt_lower for keyword in task_keywords):
            return "task"

        return "general"

    def _apply_prompt_modifications(
        self,
        original_prompt: str,
        memory_context: MemoryContext,
        rule_modifications: dict[str, Any],
    ) -> str:
        """Apply rule modifications to create enhanced prompt."""
        enhanced_prompt = original_prompt

        try:
            # Add context from memories
            if memory_context and memory_context.memories:
                context_section = self._build_context_section(memory_context, rule_modifications)
                if context_section:
                    enhanced_prompt = f"{context_section}\n\n{original_prompt}"

            # Apply prompt modifications from rules
            prompt_mods = rule_modifications.get("prompt_modifications", {})

            if prompt_mods.get("add_preferences") and memory_context:
                preference_context = self._extract_preference_context(memory_context)
                if preference_context:
                    enhanced_prompt += f"\n\nRelevant preferences: {preference_context}"

            if prompt_mods.get("include_tech_stack") and memory_context:
                tech_context = self._extract_tech_context(memory_context)
                if tech_context:
                    enhanced_prompt += f"\n\nTech stack context: {tech_context}"

            if prompt_mods.get("mention_experience_level") and memory_context:
                experience_context = self._extract_experience_context(memory_context)
                if experience_context:
                    enhanced_prompt += f"\n\nExperience level: {experience_context}"

            return enhanced_prompt

        except Exception as e:
            logger.error(f"Error applying prompt modifications: {e}")
            return original_prompt

    def _build_context_section(
        self, memory_context: MemoryContext, rule_modifications: dict[str, Any]
    ) -> str:
        """Build context section from memories and rule modifications."""
        if not memory_context or not memory_context.memories:
            return ""

        context_lines = ["## Relevant Context:"]

        # Add memory-based context
        for memory in memory_context.memories[:5]:  # Limit to top 5
            context_lines.append(f"- {memory.content}")

        # Add rule-based context additions
        for addition in rule_modifications.get("context_additions", []):
            if isinstance(addition, str):
                context_lines.append(f"- {addition}")

        return "\n".join(context_lines)

    def _extract_preference_context(self, memory_context: MemoryContext) -> str:
        """Extract preference information from memory context."""
        preferences = []
        for memory in memory_context.memories:
            if memory.memory_type == MemoryType.PREFERENCE:
                preferences.append(memory.content)

        return "; ".join(preferences[:3])  # Limit to 3 preferences

    def _extract_tech_context(self, memory_context: MemoryContext) -> str:
        """Extract technology stack information from memory context."""
        tech_entities = set()
        for memory in memory_context.memories:
            if memory.entities:
                # Filter for technology-related entities
                tech_keywords = [
                    "python",
                    "javascript",
                    "react",
                    "django",
                    "postgresql",
                    "docker",
                    "kubernetes",
                ]
                for entity in memory.entities:
                    # Type narrow: entity can be str | dict[str, Any]
                    if isinstance(entity, str):
                        if any(keyword in entity.lower() for keyword in tech_keywords):
                            tech_entities.add(entity)
                    elif isinstance(entity, dict):
                        entity_text = entity.get("name") or entity.get("text", "")
                        if isinstance(entity_text, str) and any(
                            keyword in entity_text.lower() for keyword in tech_keywords
                        ):
                            tech_entities.add(entity_text)

        return ", ".join(list(tech_entities)[:5])  # Limit to 5 technologies

    def _extract_experience_context(self, memory_context: MemoryContext) -> str:
        """Extract experience level information from memory context."""
        for memory in memory_context.memories:
            # Note: IDENTITY doesn't exist, using SEMANTIC for general knowledge
            if memory.memory_type == MemoryType.SEMANTIC:
                content_lower = memory.content.lower()
                if "senior" in content_lower:
                    return "Senior level"
                elif "junior" in content_lower:
                    return "Junior level"
                elif "lead" in content_lower or "principal" in content_lower:
                    return "Leadership level"

        return "Experienced"

    def _generate_context_summary(
        self, memory_context: MemoryContext, rule_modifications: dict[str, Any]
    ) -> str:
        """Generate a summary of the context used."""
        summary_parts = []

        if memory_context and memory_context.memories:
            summary_parts.append(f"{len(memory_context.memories)} memories recalled")

            memory_types = [mem.memory_type.value for mem in memory_context.memories]
            unique_types = list(set(memory_types))
            summary_parts.append(f"Types: {', '.join(unique_types)}")

        executed_rules = rule_modifications.get("executed_rules", [])
        if executed_rules:
            summary_parts.append(f"{len(executed_rules)} rules applied")

        return " | ".join(summary_parts)

    def _handle_learning_event(self, learning_data: dict[str, Any]) -> None:
        """Handle learning events from the rule engine."""
        try:
            # Process learning data and potentially create new memories
            if self.kuzu_memory and "new_insight" in learning_data:
                self.kuzu_memory.generate_memories(
                    content=learning_data["new_insight"],
                    user_id=learning_data.get("user_id", "system"),
                    session_id="learning_session",
                    source="rule_learning",
                    metadata={"learning_event": True},
                )

        except Exception as e:
            logger.error(f"Error handling learning event: {e}")

    def get_integration_statistics(self) -> dict[str, Any]:
        """Get comprehensive integration statistics."""
        stats = {
            "integration": self.integration_stats.copy(),
            "rule_engine": self.rule_engine.get_rule_statistics(),
            "response_learner": self.response_learner.get_learning_statistics(),
        }

        return stats

    def export_rules(self, file_path: str) -> None:
        """Export rules to a JSON file."""
        try:
            rules_data = {}
            for rule_id, rule in self.rule_engine.rules.items():
                rule_dict = asdict(rule)
                # Convert datetime objects to strings
                if rule_dict["created_at"]:
                    rule_dict["created_at"] = rule_dict["created_at"].isoformat()
                if rule_dict["last_executed"]:
                    rule_dict["last_executed"] = rule_dict["last_executed"].isoformat()
                # Convert enums to strings
                rule_dict["rule_type"] = rule_dict["rule_type"].value
                rule_dict["priority"] = rule_dict["priority"].value

                rules_data[rule_id] = rule_dict

            with open(file_path, "w") as f:
                json.dump(rules_data, f, indent=2)

            logger.info(f"Rules exported to {file_path}")

        except Exception as e:
            logger.error(f"Error exporting rules: {e}")

    def import_rules(self, file_path: str) -> None:
        """Import rules from a JSON file."""
        try:
            with open(file_path) as f:
                rules_data = json.load(f)

            for _rule_id, rule_dict in rules_data.items():
                # Convert strings back to datetime objects
                if rule_dict["created_at"]:
                    rule_dict["created_at"] = datetime.fromisoformat(rule_dict["created_at"])
                if rule_dict["last_executed"]:
                    rule_dict["last_executed"] = datetime.fromisoformat(rule_dict["last_executed"])

                # Convert strings back to enums
                rule_dict["rule_type"] = RuleType(rule_dict["rule_type"])
                rule_dict["priority"] = RulePriority(rule_dict["priority"])

                # Create rule object
                rule = AuggieRule(**rule_dict)
                self.rule_engine.add_rule(rule)

            logger.info(f"Rules imported from {file_path}")

        except Exception as e:
            logger.error(f"Error importing rules: {e}")

    def create_custom_rule(
        self,
        name: str,
        description: str,
        rule_type: str,
        conditions: dict[str, Any],
        actions: dict[str, Any],
        priority: str = "medium",
    ) -> str:
        """Create a custom rule and add it to the engine."""
        try:
            rule_id = f"custom_{hash(name) % 10000}"

            custom_rule = AuggieRule(
                id=rule_id,
                name=name,
                description=description,
                rule_type=RuleType(rule_type),
                priority=RulePriority[priority.upper()],
                conditions=conditions,
                actions=actions,
            )

            self.rule_engine.add_rule(custom_rule)
            return rule_id

        except Exception as e:
            logger.error(f"Error creating custom rule: {e}")
            return None
