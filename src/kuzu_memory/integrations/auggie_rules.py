"""
Auggie Rules Engine for KuzuMemory Integration.

Handles rule management, execution, and statistics for Auggie integration.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

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

            modifications: dict[str, Any] = {}

            for action_type, action_config in self.actions.items():
                if action_type == "add_context":
                    modifications["added_context"] = modifications.get("added_context", [])
                    modifications["added_context"].append(action_config)

                elif action_type == "modify_prompt":
                    modifications["prompt_modifications"] = modifications.get(
                        "prompt_modifications", []
                    )
                    modifications["prompt_modifications"].append(action_config)

                elif action_type == "set_priority":
                    modifications["memory_priority"] = action_config

                elif action_type == "filter_memories":
                    modifications["memory_filters"] = modifications.get("memory_filters", [])
                    modifications["memory_filters"].append(action_config)

                elif action_type == "learn_pattern":
                    modifications["learning_triggers"] = modifications.get("learning_triggers", [])
                    modifications["learning_triggers"].append(action_config)

            # Update success rate based on execution success
            self.success_rate = (
                self.success_rate * (self.execution_count - 1) + 1.0
            ) / self.execution_count

            return modifications

        except Exception as e:
            logger.warning(f"Error executing rule actions for {self.id}: {e}")
            # Update success rate based on failure
            if self.execution_count > 0:
                self.success_rate = (
                    self.success_rate * (self.execution_count - 1) + 0.0
                ) / self.execution_count
            return {}


class AuggieRuleEngine:
    """Engine for managing and executing Auggie rules."""

    def __init__(self) -> None:
        self.rules: dict[str, AuggieRule] = {}
        self.execution_history: list[dict[str, Any]] = []
        self.rule_callbacks: dict[RuleType, list[Callable[..., Any]]] = {}

        # Initialize default rules
        self._initialize_default_rules()

        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.last_cleanup = datetime.now()

    def _initialize_default_rules(self) -> None:
        """Initialize default Auggie rules."""
        default_rules = [
            AuggieRule(
                id="context_relevant_memories",
                name="Context-Relevant Memory Enhancement",
                description="Enhance prompts with contextually relevant memories",
                rule_type=RuleType.CONTEXT_ENHANCEMENT,
                priority=RulePriority.HIGH,
                conditions={
                    "prompt_length": {"greater_than": 10},
                    "memories_available": {"greater_than": 0},
                },
                actions={"add_context": {"max_memories": 5, "relevance_threshold": 0.7}},
            ),
            AuggieRule(
                id="conversation_learning",
                name="Conversation Learning Trigger",
                description="Learn from successful conversation interactions",
                rule_type=RuleType.LEARNING_TRIGGER,
                priority=RulePriority.MEDIUM,
                conditions={
                    "response_quality": {"greater_than": 0.8},
                    "conversation_complete": {"equals": True},
                },
                actions={
                    "learn_pattern": {
                        "pattern_type": "conversation_success",
                        "confidence": 0.9,
                    }
                },
            ),
            AuggieRule(
                id="technical_context_priority",
                name="Technical Context Prioritization",
                description="Prioritize technical memories for code-related prompts",
                rule_type=RuleType.MEMORY_PRIORITIZATION,
                priority=RulePriority.HIGH,
                conditions={
                    "prompt": {"contains": "code"},
                    "memory_type": {"equals": "technical"},
                },
                actions={
                    "set_priority": {
                        "boost_factor": 1.5,
                        "memory_types": [
                            "code_pattern",
                            "technical_decision",
                            "bug_fix",
                        ],
                    }
                },
            ),
        ]

        for rule in default_rules:
            self.rules[rule.id] = rule

    def add_rule(self, rule: AuggieRule) -> None:
        """Add a rule to the engine."""
        self.rules[rule.id] = rule
        logger.info(f"Added rule: {rule.name} ({rule.id})")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed rule: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def execute_rules(
        self, context: dict[str, Any], rule_types: list[RuleType] | None = None
    ) -> dict[str, Any]:
        """Execute all matching rules and return aggregated modifications."""
        try:
            self.total_executions += 1

            # Filter rules by type if specified
            if rule_types:
                applicable_rules = [
                    rule
                    for rule in self.rules.values()
                    if rule.rule_type in rule_types and rule.enabled
                ]
            else:
                applicable_rules = [rule for rule in self.rules.values() if rule.enabled]

            # Sort rules by priority
            applicable_rules.sort(key=lambda r: r.priority.value)

            # Execute matching rules
            all_modifications: dict[str, Any] = {}
            executed_rules: list[dict[str, Any]] = []

            for rule in applicable_rules:
                if rule.matches_conditions(context):
                    modifications = rule.execute_actions(context)

                    # Merge modifications
                    for mod_type, mod_value in modifications.items():
                        if mod_type not in all_modifications:
                            all_modifications[mod_type] = []

                        if isinstance(mod_value, list):
                            all_modifications[mod_type].extend(mod_value)
                        else:
                            all_modifications[mod_type].append(mod_value)

                    executed_rules.append(
                        {
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "modifications": modifications,
                            "executed_at": datetime.now(),
                        }
                    )

            # Record execution
            execution_record = {
                "context": context,
                "executed_rules": executed_rules,
                "total_modifications": all_modifications,
                "executed_at": datetime.now(),
            }

            self.execution_history.append(execution_record)

            # Keep history limited
            if len(self.execution_history) > 1000:
                self.execution_history = self.execution_history[-500:]

            if executed_rules:
                self.successful_executions += 1

            return all_modifications

        except Exception as e:
            logger.error(f"Error executing rules: {e}")
            return {}

    def get_rule_statistics(self) -> dict[str, Any]:
        """Get comprehensive rule statistics."""
        stats: dict[str, Any] = {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "disabled_rules": len([r for r in self.rules.values() if not r.enabled]),
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "success_rate": (self.successful_executions / max(self.total_executions, 1)) * 100,
            "rules_by_type": {},
            "rules_by_priority": {},
            "top_executed_rules": [],
            "recent_executions": len(self.execution_history),
        }

        # Rules by type
        rules_by_type: dict[str, int] = {}
        for rule in self.rules.values():
            rule_type = rule.rule_type.value
            if rule_type not in rules_by_type:
                rules_by_type[rule_type] = 0
            rules_by_type[rule_type] += 1
        stats["rules_by_type"] = rules_by_type

        # Rules by priority
        rules_by_priority: dict[str, int] = {}
        for rule in self.rules.values():
            priority = rule.priority.name
            if priority not in rules_by_priority:
                rules_by_priority[priority] = 0
            rules_by_priority[priority] += 1
        stats["rules_by_priority"] = rules_by_priority

        # Top executed rules
        sorted_rules = sorted(self.rules.values(), key=lambda r: r.execution_count, reverse=True)

        stats["top_executed_rules"] = [
            {
                "id": rule.id,
                "name": rule.name,
                "executions": rule.execution_count,
                "success_rate": rule.success_rate,
            }
            for rule in sorted_rules[:10]
        ]

        return stats

    def get_rule_by_id(self, rule_id: str) -> AuggieRule | None:
        """Get a rule by its ID."""
        return self.rules.get(rule_id)

    def get_rules_by_type(self, rule_type: RuleType) -> list[AuggieRule]:
        """Get all rules of a specific type."""
        return [rule for rule in self.rules.values() if rule.rule_type == rule_type]

    def get_recent_executions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent rule executions."""
        return self.execution_history[-limit:]

    def cleanup_old_history(self, days_to_keep: int = 7) -> None:
        """Clean up old execution history."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        self.execution_history = [
            record for record in self.execution_history if record["executed_at"] > cutoff_date
        ]

        self.last_cleanup = datetime.now()
        logger.info(f"Cleaned up execution history older than {days_to_keep} days")

    def export_rules(self, file_path: str) -> None:
        """Export rules to a JSON file."""
        try:
            rules_data = {}
            for rule_id, rule in self.rules.items():
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
                self.add_rule(rule)

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
    ) -> str | None:
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

            self.add_rule(custom_rule)
            return rule_id

        except Exception as e:
            logger.error(f"Error creating custom rule: {e}")
            return None
