"""
Advanced entity extraction for KuzuMemory.

Implements comprehensive entity extraction using expanded regex patterns
for technical terms, multi-word entities, business entities, and more.
No LLM required - uses sophisticated pattern matching only.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from re import Pattern
from typing import Any

from ..utils.validation import validate_text_input

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents an extracted entity with metadata."""

    text: str
    entity_type: str
    confidence: float = 0.9
    start_pos: int = 0
    end_pos: int = 0
    normalized_text: str = ""

    def __post_init__(self) -> None:
        if not self.normalized_text:
            self.normalized_text = self.text.lower().strip()


class EntityExtractor:
    """
    Advanced entity extractor using comprehensive regex patterns.

    Extracts entities without LLM calls using sophisticated pattern matching
    for technical terms, multi-word entities, business entities, and more.
    """

    def __init__(
        self,
        enable_compilation: bool = True,
        custom_patterns: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize entity extractor.

        Args:
            enable_compilation: Whether to pre-compile regex patterns
            custom_patterns: Optional custom entity patterns
        """
        self.enable_compilation = enable_compilation
        self.custom_patterns = custom_patterns or {}

        # Define comprehensive entity patterns
        self._define_patterns()

        # Compile patterns if enabled
        if self.enable_compilation:
            self._compile_patterns()

        # Common words to filter out (avoid false positives)
        self.COMMON_WORDS = {
            "is",
            "was",
            "the",
            "and",
            "or",
            "if",
            "then",
            "when",
            "where",
            "what",
            "who",
            "why",
            "how",
            "can",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "do",
            "does",
            "did",
            "have",
            "has",
            "had",
            "be",
            "been",
            "being",
            "am",
            "are",
            "were",
            "this",
            "that",
            "these",
            "those",
            "a",
            "an",
            "some",
            "any",
            "all",
            "each",
            "every",
            "no",
            "not",
            "only",
            "just",
            "also",
            "too",
            "very",
        }

        # Statistics
        self._extraction_stats: dict[str, Any] = {
            "total_entities": 0,
            "entity_types": {},
            "patterns_matched": {},
        }

    def _define_patterns(self) -> None:
        """Define comprehensive entity patterns."""

        # Programming languages (comprehensive)
        self.LANGUAGE_PATTERNS = [
            (
                r"\b(Python|JavaScript|TypeScript|Java|Rust|Go|Kotlin|Swift|PHP|Ruby|Scala|Clojure|Haskell|R|MATLAB|Perl|Shell|Bash|PowerShell|Dart|Elixir|Erlang|Groovy|Julia|Lua|Objective-C|Pascal|Prolog|Scheme|Smalltalk|Visual Basic)\b",
                0.95,
            ),
            (r"(?:^|\s)(C#|F#)(?=\s|$|[,\.])", 0.95),  # Special handling for # symbols
            (r"\b(VB\.NET)\b", 0.95),  # VB.NET separate pattern
            (
                r"(?:^|[^a-zA-Z])(C\+\+)(?:[^a-zA-Z]|$)",
                0.95,
            ),  # Special handling for C++
        ]

        # Technical frameworks and technologies (expanded)
        self.TECHNOLOGY_PATTERNS = [
            (
                r"\b(React(?:\s+Native)?|Vue(?:\.js)?|Angular|Svelte|Next\.js|Nuxt\.js|Gatsby|Django|Flask|FastAPI|Express(?:\.js)?|Koa|Nest\.js|Spring(?:\s+Boot)?|Rails|Laravel|Symfony|CodeIgniter|ASP\.NET|\.NET(?:\s+Core)?)\b",
                0.95,
            ),
            (
                r"\b(Docker|Kubernetes|Jenkins|GitLab|GitHub|Bitbucket|Travis|CircleCI|AWS|Azure|GCP|Google Cloud|Heroku|Vercel|Netlify|DigitalOcean|Linode)\b",
                0.95,
            ),
            (
                r"\b(MongoDB|PostgreSQL|MySQL|SQLite|Redis|Elasticsearch|Cassandra|DynamoDB|Firebase|Supabase|PlanetScale|Prisma|Sequelize|TypeORM|Mongoose)\b",
                0.95,
            ),
            (
                r"\b(Webpack|Vite|Rollup|Parcel|Babel|ESLint|Prettier|Jest|Cypress|Playwright|Selenium|Storybook|Figma|Sketch|Adobe XD)\b",
                0.90,
            ),
        ]

        # Multi-word entities (conservative patterns)
        self.COMPOUND_ENTITY_PATTERNS = [
            (
                r"(?:project|app|system|platform|service|tool|framework|library|API)\s+(?:called|named)\s+([A-Z][a-zA-Z0-9\s]+)",
                0.95,
            ),
            (
                r"\b([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+\s+(?:System|Platform|Service|Module|Dashboard))\b",
                0.90,
            ),
            (
                r"\b([A-Z][a-zA-Z]+\s+(?:Management|Processing|Analytics|Insights)(?:\s+[A-Z][a-zA-Z]+)*)\b",
                0.85,
            ),
        ]

        # Business entities (organizations, companies)
        self.ORGANIZATION_PATTERNS = [
            (
                r"\b([A-Z][a-z]+\s+(?:Corp|Inc|LLC|Ltd)\.?)\b",
                0.98,
            ),  # Match "TechCorp Inc" as a whole
            (
                r"\b([A-Z][a-z]+(?:Technologies|Systems|Solutions|Consulting|Group|Company|Corporation|Incorporated|Limited))\b",
                0.95,
            ),
            (
                r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:Corp|Inc|LLC|Ltd|Technologies|Systems|Solutions|Consulting|Group|Company)\b",
                0.95,
            ),
            (
                r"\b([A-Z][a-zA-Z]+\s+(?:Technologies|Systems|Solutions|Consulting|Group|Company|Corporation|Services))\b",
                0.93,
            ),  # "DataSoft Solutions"
            (
                r"\b([A-Z][a-zA-Z]+\s+(?:Technologies|Systems|Solutions|Consulting|Group|Company|Corporation|Services))\s+(?:is|was|are|provides|offers)",
                0.90,
            ),  # "DataSoft Solutions is"
            (
                r"\b(Google|Microsoft|Apple|Amazon|Meta|Facebook|Netflix|Tesla|Uber|Airbnb|Spotify|Slack|Zoom|Salesforce|Oracle|IBM|Intel|NVIDIA|AMD)\b",
                1.0,
            ),
        ]

        # Person names (improved patterns) - avoid matching system/business names
        self.PERSON_PATTERNS = [
            # Higher confidence for person names with descriptive verbs
            (
                r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\s+(?:works|is\s+our|is\s+a|is\s+the|said|told|mentioned|suggested|recommended|created|developed|built)",
                0.95,
            ),
            (
                r"(?:by|from|with|created by|developed by|built by|written by)\s+([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})",
                0.85,
            ),
            (
                r"(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)",
                0.98,
            ),
            # Names in lists with "and" - extract both names from pattern like "Bob Smith and Carol Davis are"
            (
                r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\s+and\s+[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\s+(?:are|were)",
                0.80,
            ),  # First name
            (
                r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\s+and\s+([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\s+(?:are|were)",
                0.80,
            ),  # Second name
        ]

        # File types (expanded)
        self.FILE_PATTERNS = [
            (
                r"\b([\w\-\.]+\.(?:py|js|ts|tsx|jsx|json|yaml|yml|md|txt|csv|sql|html|css|scss|less|xml|pdf|docx|xlsx|pptx|zip|tar|gz|log|config|env|ini|toml|lock|gitignore))\b",
                0.95,
            ),
            (
                r"\b(package\.json|requirements\.txt|Cargo\.toml|go\.mod|pom\.xml|build\.gradle|composer\.json|Gemfile|Pipfile)\b",
                1.0,
            ),
            (
                r"\b(Dockerfile|Makefile)\b",
                0.98,
            ),  # Higher confidence for special files to override technology patterns
            (r"\b(docker-compose\.ya?ml)\b", 0.98),  # Docker compose files
        ]

        # URLs and domains
        self.URL_PATTERNS = [
            (r"(https?://[^\s]+)", 0.95),
            # GitHub-style URLs with path
            (r"\b([a-zA-Z0-9]+\.com/[a-zA-Z0-9\-_/]+)", 0.92),  # github.com/user/repo
            (
                r"\b([a-zA-Z0-9]+\.[a-zA-Z0-9]+\.[a-zA-Z]{2,6})\b",
                0.90,
            ),  # subdomain.domain.com
            (
                r"\b([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*(com|org|net|edu|gov|mil|co\.uk|co\.in|io|dev|tech|app|service)[/\w\-]*)\b",
                0.85,
            ),
            (
                r"\b([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\b",
                0.75,
            ),
        ]

        # Email addresses
        self.EMAIL_PATTERNS = [
            (r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Z|a-z]{2,})\b", 0.95),
        ]

        # Version numbers
        self.VERSION_PATTERNS = [
            (r"\b(?:v|version\s*)(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?)\b", 0.90),
            (r"\b(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?)\s+(?:version|release)\b", 0.90),
            (
                r"\b(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)\b",
                0.85,
            ),  # Simple version numbers like 3.9.7
        ]

        # Dates and times
        self.DATE_PATTERNS = [
            (r"\b(\d{4}-\d{2}-\d{2})\b", 0.95),
            (r"\b(\d{1,2}/\d{1,2}/\d{4})\b", 0.90),
            (
                r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b",
                0.95,
            ),
            (r"\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\b", 0.85),
        ]

        # API endpoints and paths
        self.API_PATTERNS = [
            (r"(/api/[a-zA-Z0-9/_\-]+)", 0.90),
            (r"(/[a-zA-Z0-9/_\-]+/[a-zA-Z0-9/_\-]+)", 0.75),
        ]

        # Database and table names
        self.DATABASE_PATTERNS = [
            (r"\b([a-z_]+_(?:table|db|database|collection|index))\b", 0.85),
            (r"\b(?:table|collection|index)\s+([a-zA-Z_][a-zA-Z0-9_]*)", 0.85),
        ]

        # Environment and configuration
        self.CONFIG_PATTERNS = [
            (
                r"\b([A-Z_]+_(?:KEY|SECRET|TOKEN|URL|HOST|PORT|PASSWORD|USER|CONFIG))\b",
                0.90,
            ),
            (r"\$\{?([A-Z_][A-Z0-9_]*)\}?", 0.85),
        ]

        # Combine all patterns with their types
        self.ALL_PATTERNS = [
            (self.LANGUAGE_PATTERNS, "programming_language"),
            (self.TECHNOLOGY_PATTERNS, "technology"),
            (self.COMPOUND_ENTITY_PATTERNS, "compound_entity"),
            (self.ORGANIZATION_PATTERNS, "organization"),
            (self.PERSON_PATTERNS, "person"),
            (self.FILE_PATTERNS, "file"),
            (self.URL_PATTERNS, "url"),
            (self.EMAIL_PATTERNS, "email"),
            (self.VERSION_PATTERNS, "version"),
            (self.DATE_PATTERNS, "date"),
            (self.API_PATTERNS, "api_endpoint"),
            (self.DATABASE_PATTERNS, "database_object"),
            (self.CONFIG_PATTERNS, "configuration"),
        ]

        # Add custom patterns if provided
        if self.custom_patterns:
            for pattern_name, pattern_regex in self.custom_patterns.items():
                custom_pattern = [(pattern_regex, 0.80)]
                self.ALL_PATTERNS.append((custom_pattern, f"custom_{pattern_name}"))

    def _compile_patterns(self) -> None:
        """Pre-compile all regex patterns for performance."""
        self.compiled_patterns = []

        for pattern_group, entity_type in self.ALL_PATTERNS:
            compiled_group = []
            for pattern, confidence in pattern_group:
                try:
                    compiled_regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                    compiled_group.append((compiled_regex, confidence))
                except re.error as e:
                    logger.warning(f"Failed to compile entity pattern for {entity_type}: {e}")
                    continue

            if compiled_group:
                self.compiled_patterns.append((compiled_group, entity_type))

        logger.info(
            f"Compiled {sum(len(group) for group, _ in self.compiled_patterns)} entity patterns"
        )

    def extract_entities(self, text: str) -> list[Entity]:
        """
        Extract all entities from text using pattern matching.

        Args:
            text: Text to extract entities from

        Returns:
            List of extracted entities
        """
        if text is None:
            raise TypeError("Input text cannot be None")

        if not text or not text.strip():
            return []

        try:
            # Validate input
            clean_text = validate_text_input(text, "entity_extraction_text")

            entities = []
            patterns_to_use = (
                self.compiled_patterns if self.enable_compilation else self._get_runtime_patterns()
            )

            # Extract entities from each pattern group
            for pattern_group, entity_type in patterns_to_use:
                group_entities = self._extract_from_pattern_group(
                    clean_text, pattern_group, entity_type
                )
                entities.extend(group_entities)

            # Deduplicate and filter entities
            unique_entities = self._deduplicate_entities(entities)
            filtered_entities = self._filter_entities(unique_entities)

            # Update statistics
            self._update_extraction_stats(filtered_entities)

            return filtered_entities

        except Exception as e:
            logger.error(f"Error extracting entities from text: {e}")
            return []

    def _get_runtime_patterns(
        self,
    ) -> list[tuple[list[tuple[Pattern[str], float]], str]]:
        """Get patterns for runtime compilation (when pre-compilation is disabled)."""
        runtime_patterns = []

        for pattern_group, entity_type in self.ALL_PATTERNS:
            runtime_group = []
            for pattern, confidence in pattern_group:
                try:
                    compiled_regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                    runtime_group.append((compiled_regex, confidence))
                except re.error:
                    continue

            if runtime_group:
                runtime_patterns.append((runtime_group, entity_type))

        return runtime_patterns

    def _extract_from_pattern_group(
        self,
        text: str,
        pattern_group: list[tuple[Pattern[str], float]],
        entity_type: str,
    ) -> list[Entity]:
        """Extract entities from a specific pattern group."""
        entities = []

        for pattern_regex, confidence in pattern_group:
            matches = pattern_regex.finditer(text)

            for match in matches:
                # Extract the entity text
                if match.groups():
                    entity_text = match.group(1).strip()
                else:
                    entity_text = match.group(0).strip()

                # Skip empty or very short matches
                if not entity_text or len(entity_text) < 2:
                    continue

                # Filter out common words
                if entity_text.lower() in self.COMMON_WORDS:
                    continue

                # Clean the entity text
                cleaned_text = self._clean_entity_text(entity_text)

                if cleaned_text:
                    entity = Entity(
                        text=cleaned_text,
                        entity_type=entity_type,
                        confidence=confidence,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        normalized_text=cleaned_text.lower().strip(),
                    )
                    entities.append(entity)

        return entities

    def _clean_entity_text(self, text: str) -> str:
        """Clean and normalize entity text."""
        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove common prefixes/suffixes that don't belong to the entity
        prefixes_to_remove = ["the ", "a ", "an ", "my ", "our ", "your ", "their "]
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix):
                text = text[len(prefix) :].strip()

        # Remove trailing punctuation
        text = text.rstrip(".,!?;:")

        # Normalize whitespace
        text = " ".join(text.split())

        return text

    def _deduplicate_entities(self, entities: list[Entity]) -> list[Entity]:
        """Remove duplicate entities and handle overlaps."""
        if not entities:
            return []

        # First remove exact duplicates
        entity_groups: dict[tuple[str, str], list[Entity]] = {}
        for entity in entities:
            key = (entity.normalized_text, entity.entity_type)
            if key not in entity_groups:
                entity_groups[key] = []
            entity_groups[key].append(entity)

        # Keep the entity with highest confidence from each group
        unique_entities = []
        for group in entity_groups.values():
            if len(group) == 1:
                unique_entities.append(group[0])
            else:
                # Sort by confidence and take the best one
                best_entity = max(group, key=lambda e: e.confidence)
                unique_entities.append(best_entity)

        # Remove overlapping entities (keep higher confidence ones)
        final_entities: list[Entity] = []
        for entity in sorted(unique_entities, key=lambda e: e.confidence, reverse=True):
            # Check if this entity overlaps with any already selected entity
            overlaps = False
            for existing in final_entities:
                # Check if entities have significant text overlap
                if self._entities_overlap(entity, existing):
                    overlaps = True
                    break

            if not overlaps:
                final_entities.append(entity)

        return final_entities

    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        """Check if two entities overlap significantly."""
        # If they have the same normalized text, they overlap
        if entity1.normalized_text == entity2.normalized_text:
            return True

        # Check if one entity text is contained in the other
        text1, text2 = entity1.text.lower(), entity2.text.lower()
        if text1 in text2 or text2 in text1:
            return True

        # For position-based overlap (if we have position info)
        if entity1.start_pos and entity2.start_pos and entity1.end_pos and entity2.end_pos:
            # Check if they overlap in position
            overlap_start = max(entity1.start_pos, entity2.start_pos)
            overlap_end = min(entity1.end_pos, entity2.end_pos)
            if overlap_start < overlap_end:
                overlap_length = overlap_end - overlap_start
                min_length = min(
                    entity1.end_pos - entity1.start_pos,
                    entity2.end_pos - entity2.start_pos,
                )
                # If overlap is more than 50% of the smaller entity, consider them overlapping
                return overlap_length > min_length * 0.5

        return False

    def _filter_entities(self, entities: list[Entity]) -> list[Entity]:
        """Filter entities based on quality and relevance."""
        filtered = []

        for entity in entities:
            # Skip very short entities
            if len(entity.text) < 2:
                continue

            # Skip entities that are mostly numbers (except for versions, dates, etc.)
            if (
                entity.entity_type not in ["version", "date", "api_endpoint", "configuration"]
                and sum(1 for c in entity.text if c.isdigit()) > len(entity.text) * 0.7
            ):
                continue

            # Skip entities with very low confidence
            if entity.confidence < 0.5:
                continue

            # Skip entities that are just punctuation
            if all(not c.isalnum() for c in entity.text):
                continue

            # Skip common programming keywords that aren't meaningful as entities
            if entity.text.lower() in {
                "if",
                "else",
                "for",
                "while",
                "function",
                "class",
                "import",
                "from",
                "return",
            }:
                continue

            # Skip common abbreviations that shouldn't be organizations
            if entity.entity_type == "organization" and entity.text.upper() in {
                "API",
                "URL",
                "HTTP",
                "HTTPS",
                "JSON",
                "XML",
                "HTML",
                "CSS",
                "JS",
            }:
                continue

            filtered.append(entity)

        return filtered

    def _update_extraction_stats(self, entities: list[Entity]) -> None:
        """Update extraction statistics."""
        self._extraction_stats["total_entities"] += len(entities)

        for entity in entities:
            entity_type = entity.entity_type
            self._extraction_stats["entity_types"][entity_type] = (
                self._extraction_stats["entity_types"].get(entity_type, 0) + 1
            )

    def get_entity_statistics(self) -> dict[str, Any]:
        """Get entity extraction statistics."""
        total_patterns = sum(len(group) for group, _ in self.compiled_patterns)

        return {
            "total_patterns": total_patterns,
            "compilation_enabled": self.enable_compilation,
            "custom_patterns_count": len(self.custom_patterns),
            "extraction_stats": self._extraction_stats.copy(),
            "entity_type_distribution": self._extraction_stats["entity_types"].copy(),
            "top_entity_types": sorted(
                self._extraction_stats["entity_types"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }

    def extract_entities_by_type(self, text: str, entity_types: list[str]) -> list[Entity]:
        """
        Extract entities of specific types only.

        Args:
            text: Text to extract entities from
            entity_types: List of entity types to extract

        Returns:
            List of entities of specified types
        """
        all_entities = self.extract_entities(text)
        return [entity for entity in all_entities if entity.entity_type in entity_types]

    def find_entity_relationships(
        self, entities: list[Entity], text: str
    ) -> list[tuple[Entity, Entity, str]]:
        """
        Find relationships between entities based on proximity and context.

        Args:
            entities: List of entities to analyze
            text: Original text containing the entities

        Returns:
            List of (entity1, entity2, relationship_type) tuples
        """
        relationships = []

        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.start_pos)

        for i, entity1 in enumerate(sorted_entities):
            for entity2 in sorted_entities[i + 1 :]:
                # Check if entities are close to each other (within 50 characters)
                distance = entity2.start_pos - entity1.end_pos
                if distance > 50:
                    break  # Entities are too far apart

                # Determine relationship type based on entity types and context
                relationship_type = self._determine_relationship_type(
                    entity1, entity2, text[entity1.end_pos : entity2.start_pos]
                )

                if relationship_type:
                    relationships.append((entity1, entity2, relationship_type))

        return relationships

    def _determine_relationship_type(
        self, entity1: Entity, entity2: Entity, context: str
    ) -> str | None:
        """Determine the relationship type between two entities based on context."""
        context_lower = context.lower().strip()

        # Person-Organization relationships
        if entity1.entity_type == "person" and entity2.entity_type == "organization":
            if any(word in context_lower for word in ["works at", "at", "from", "with"]):
                return "works_at"

        # Technology-Project relationships
        if entity1.entity_type == "compound_entity" and entity2.entity_type == "technology":
            if any(word in context_lower for word in ["uses", "built with", "using", "in"]):
                return "uses_technology"

        # File-Technology relationships
        if entity1.entity_type == "file" and entity2.entity_type in [
            "programming_language",
            "technology",
        ]:
            return "implemented_in"

        # Version-Technology relationships
        if entity1.entity_type == "technology" and entity2.entity_type == "version":
            return "has_version"

        # Generic co-occurrence
        if len(context_lower) < 10:  # Very close entities
            return "co_occurs"

        return None

    def get_entity_summary(self, entities: list[Entity]) -> dict[str, Any]:
        """Get a summary of extracted entities."""
        if not entities:
            return {
                "total_count": 0,
                "types": {},
                "confidence_distribution": {},
                "top_entities": [],
            }

        # Count by type
        type_counts: dict[str, int] = {}
        for entity in entities:
            type_counts[entity.entity_type] = type_counts.get(entity.entity_type, 0) + 1

        # Confidence distribution
        confidence_ranges = {"high": 0, "medium": 0, "low": 0}
        for entity in entities:
            if entity.confidence >= 0.9:
                confidence_ranges["high"] += 1
            elif entity.confidence >= 0.7:
                confidence_ranges["medium"] += 1
            else:
                confidence_ranges["low"] += 1

        # Top entities by confidence
        top_entities = sorted(entities, key=lambda e: e.confidence, reverse=True)[:10]

        return {
            "total_count": len(entities),
            "types": type_counts,
            "confidence_distribution": confidence_ranges,
            "top_entities": [
                {
                    "text": entity.text,
                    "type": entity.entity_type,
                    "confidence": entity.confidence,
                }
                for entity in top_entities
            ],
        }

    def test_entity_pattern(
        self, pattern: str, test_text: str, entity_type: str = "test"
    ) -> list[dict[str, Any]]:
        """
        Test a specific entity pattern against text (useful for debugging).

        Args:
            pattern: Regex pattern to test
            test_text: Text to test against
            entity_type: Entity type for the pattern

        Returns:
            List of matches with details
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            matches = []

            for match in compiled_pattern.finditer(test_text):
                entity_text = match.group(1) if match.groups() else match.group(0)
                matches.append(
                    {
                        "entity_text": entity_text.strip(),
                        "full_match": match.group(0),
                        "entity_type": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                        "span": match.span(),
                    }
                )

            return matches

        except re.error as e:
            return [{"error": f"Invalid regex pattern: {e}"}]
