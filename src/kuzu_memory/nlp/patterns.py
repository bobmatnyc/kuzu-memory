"""
Pattern definitions for NLP classification.

Contains patterns, keywords, and training data for memory type
classification, entity extraction, and intent detection.
"""

import re
from typing import Any

from ..core.models import MemoryType

# Memory type indicator patterns (regex)
MEMORY_TYPE_PATTERNS: dict[MemoryType, list[str]] = {
    MemoryType.EPISODIC: [
        r"\byesterday\b",
        r"\blast week\b",
        r"\bremember when\b",
        r"\bthat time\b",
        r"\bwent to\b",
        r"\bhappened\b",
        r"\bexperienced\b",
        r"\bdiscussed\b",
        r"\bmentioned\b",
        r"\bsaid\b",
        r"\bdecided to\b",
        r"\bevent\b",
    ],
    MemoryType.SEMANTIC: [
        r"\bis a\b",
        r"\bare\b",
        r"\bfact:\b",
        r"\bdefined as\b",
        r"\bmeans\b",
        r"\bcapital of\b",
        r"\bequals\b",
        r"\bmy name is\b",
        r"\bproject name is\b",
        r"\bcompany is\b",
        r"\bthe system\b.*\bis\b",
    ],
    MemoryType.PROCEDURAL: [
        r"\bhow to\b",
        r"\bsteps to\b",
        r"\bprocess for\b",
        r"\bmethod for\b",
        r"\bprocedure\b",
        r"\bfirst\b.*\bthen\b",
        r"\binstruction(s)?\b",
        r"\brecipe\b",
        r"\balgorithm\b",
        r"\bworkflow\b",
        r"\bsolution is\b",
    ],
    MemoryType.WORKING: [
        r"\bneed to\b",
        r"\btodo\b",
        r"\btask\b",
        r"\bcurrently\b",
        r"\bworking on\b",
        r"\bin progress\b",
        r"\bby tomorrow\b",
        r"\bdeadline\b",
        r"\bfinish\b",
        r"\bcomplete\b",
        r"\bright now\b",
    ],
    MemoryType.SENSORY: [
        r"\bsmells?\b",
        r"\btastes?\b",
        r"\bsounds?\b",
        r"\blooks?\b",
        r"\bfeels?\b",
        r"\btexture\b",
        r"\bcolor(ed)?\b",
        r"\bbright\b",
        r"\bsoft\b",
        r"\bloud\b",
        r"\bsweet\b",
        r"\bsmell(ing)?\b",
        r"\btaste\b",
        r"\bsound(ing)?\b",
        r"\blook(ing)?\b",
        r"\bfeel(ing)?\b",
        r"\btouch\b",
        r"\bhear(ing)?\b",
        r"\bsee(ing)?\b",
    ],
    MemoryType.PREFERENCE: [
        r"\bprefer(s|red)?\b",
        r"\blike(s)?\b",
        r"\bdon't like\b",
        r"\bfavorite\b",
        r"\blove(s)?\b",
        r"\bhate(s)?\b",
        r"\bchoose\b",
        r"\bideal\b",
        r"\balways use(s)?\b",
        r"\bbetter than\b",
        r"\binstead of\b",
        r"\brather than\b",
        r"\bcan't stand\b",
    ],
}


# Simple keyword indicators for memory types
def get_memory_type_indicators() -> dict[MemoryType, list[str]]:
    """Get simple keyword indicators for each memory type."""
    return {
        MemoryType.EPISODIC: [
            "yesterday",
            "last week",
            "remember",
            "happened",
            "went",
            "experienced",
            "event",
            "discussed",
            "mentioned",
            "said",
            "decided",
            "that time",
            "once",
            "when I",
            "we did",
        ],
        MemoryType.SEMANTIC: [
            "is a",
            "are",
            "fact",
            "defined",
            "means",
            "equals",
            "capital",
            "my name",
            "project is",
            "company is",
            "system is",
            "truth",
            "always",
            "never",
            "definition",
        ],
        MemoryType.PROCEDURAL: [
            "how to",
            "steps",
            "process",
            "method",
            "procedure",
            "first",
            "then",
            "instruction",
            "recipe",
            "algorithm",
            "workflow",
            "template",
            "pattern",
            "solution",
            "fix",
        ],
        MemoryType.WORKING: [
            "need to",
            "todo",
            "task",
            "currently",
            "working on",
            "in progress",
            "deadline",
            "finish",
            "complete",
            "right now",
            "pending",
            "ongoing",
            "active",
            "urgent",
            "priority",
        ],
        MemoryType.SENSORY: [
            "smells",
            "tastes",
            "sounds",
            "looks",
            "feels",
            "texture",
            "color",
            "bright",
            "soft",
            "loud",
            "sweet",
            "rough",
            "smooth",
            "warm",
            "cold",
        ],
        MemoryType.PREFERENCE: [
            "prefer",
            "like",
            "don't like",
            "favorite",
            "love",
            "hate",
            "choose",
            "ideal",
            "always use",
            "better",
            "instead of",
            "rather than",
            "enjoy",
            "want",
            "dislike",
            "avoid",
            "opt for",
        ],
    }


# Entity extraction patterns
ENTITY_PATTERNS: dict[str, list[str]] = {
    "person": [
        r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b",  # Full names
        r"\b(Dr\.|Mr\.|Mrs\.|Ms\.) ([A-Z][a-z]+)\b",  # Titles
    ],
    "organization": [
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|LLC|Ltd|Corp|Company|Team|Department))\b",
        r"\b(Google|Microsoft|Amazon|Apple|Facebook|Meta|OpenAI|Anthropic)\b",
    ],
    "location": [
        r"\b([A-Z][a-z]+,\s+[A-Z]{2})\b",  # City, State
        r"\b(New York|San Francisco|London|Tokyo|Berlin|Paris)\b",
    ],
    "technology": [
        r"\b(Python|JavaScript|TypeScript|Java|C\+\+|C#|Go|Rust|Swift|Kotlin)\b",
        r"\b(React|Vue|Angular|Django|Flask|FastAPI|Spring|Node\.js|Express)\b",
        r"\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|SQLite|DynamoDB)\b",
        r"\b(AWS|Azure|GCP|Docker|Kubernetes|Jenkins|GitHub|GitLab)\b",
        r"\b(TensorFlow|PyTorch|scikit-learn|Pandas|NumPy|NLTK|spaCy)\b",
    ],
    "project": [
        r"\b([A-Z][a-z]+[A-Z][a-z]+)\b",  # CamelCase
        r"\b([A-Z][a-z]+-[A-Z][a-z]+)\b",  # Hyphenated
    ],
    "date": [
        r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(yesterday|today|tomorrow|last week|next month)\b",
    ],
}


# Intent keywords for classification
INTENT_KEYWORDS: dict[str, list[str]] = {
    "decision": [
        "decide",
        "choose",
        "select",
        "pick",
        "opt for",
        "go with",
        "settle on",
        "determine",
        "conclude",
    ],
    "preference": [
        "prefer",
        "like",
        "favor",
        "enjoy",
        "love",
        "want",
        "wish",
        "desire",
        "would rather",
    ],
    "solution": [
        "solve",
        "fix",
        "resolve",
        "address",
        "handle",
        "workaround",
        "remedy",
        "correct",
        "repair",
    ],
    "pattern": [
        "how to",
        "steps",
        "process",
        "method",
        "way to",
        "procedure",
        "technique",
        "approach",
        "recipe",
    ],
    "fact": [
        "is",
        "are",
        "was",
        "were",
        "fact",
        "truth",
        "actually",
        "really",
        "indeed",
    ],
    "observation": [
        "notice",
        "observe",
        "see",
        "find",
        "discover",
        "realize",
        "recognize",
        "detect",
        "spot",
    ],
    "status": [
        "currently",
        "now",
        "at present",
        "ongoing",
        "in progress",
        "working on",
        "active",
        "pending",
    ],
}


# Training data for ML classifier (146 examples total)
def get_training_data() -> list[dict[str, Any]]:
    """Get training examples for memory type classification.

    Returns 146 training examples across 6 cognitive memory types:
    - EPISODIC: 23 examples (personal experiences and events)
    - SEMANTIC: 23 examples (facts and knowledge)
    - PROCEDURAL: 23 examples (instructions and how-to)
    - WORKING: 24 examples (tasks and current focus)
    - SENSORY: 23 examples (sensory descriptions)
    - PREFERENCE: 30 examples (preferences and choices)
    """
    return [
        # Episodic examples (23 - personal experiences and events)
        {"text": "Yesterday I went to the park with my family", "type": "episodic"},
        {"text": "Last week we had a meeting about the roadmap", "type": "episodic"},
        {"text": "Remember when we fixed that critical bug?", "type": "episodic"},
        {"text": "That time the server crashed during deployment", "type": "episodic"},
        {"text": "We decided to use FastAPI for the backend", "type": "episodic"},
        {"text": "John mentioned the deadline is next week", "type": "episodic"},
        {"text": "The meeting went well and everyone agreed", "type": "episodic"},
        {"text": "I experienced some issues with the login system", "type": "episodic"},
        {"text": "We discussed the architecture yesterday", "type": "episodic"},
        {"text": "The team had a retrospective meeting on Friday", "type": "episodic"},
        {"text": "Last month we launched the new feature", "type": "episodic"},
        {"text": "I remember the first day at this company", "type": "episodic"},
        {"text": "We encountered a memory leak last Tuesday", "type": "episodic"},
        {"text": "The client visited our office yesterday", "type": "episodic"},
        {"text": "That presentation went better than expected", "type": "episodic"},
        {"text": "We celebrated the project completion last week", "type": "episodic"},
        {"text": "The system crashed during the demo", "type": "episodic"},
        {"text": "Yesterday's standup revealed some blockers", "type": "episodic"},
        {"text": "We onboarded three new developers last month", "type": "episodic"},
        {"text": "The migration happened over the weekend", "type": "episodic"},
        {"text": "I attended the conference last Thursday", "type": "episodic"},
        {"text": "The team went for lunch together today", "type": "episodic"},
        {"text": "We discovered the bug during testing yesterday", "type": "episodic"},
        # Semantic examples (23 - facts and knowledge)
        {"text": "Paris is the capital of France", "type": "semantic"},
        {"text": "Python is a programming language", "type": "semantic"},
        {"text": "My name is Alice and I'm a software engineer", "type": "semantic"},
        {"text": "The user's name is Bob Johnson", "type": "semantic"},
        {"text": "This project is called KuzuMemory", "type": "semantic"},
        {"text": "The company is based in San Francisco", "type": "semantic"},
        {"text": "Our system is built with Python and FastAPI", "type": "semantic"},
        {"text": "Water freezes at 0 degrees Celsius", "type": "semantic"},
        {"text": "The speed of light equals 299,792,458 m/s", "type": "semantic"},
        {"text": "HTTP status 404 means Not Found", "type": "semantic"},
        {"text": "Git is a version control system", "type": "semantic"},
        {"text": "The database is PostgreSQL version 14", "type": "semantic"},
        {"text": "Our API uses REST architecture", "type": "semantic"},
        {"text": "The application runs on port 8000", "type": "semantic"},
        {"text": "JavaScript is a dynamically typed language", "type": "semantic"},
        {"text": "The Earth orbits around the Sun", "type": "semantic"},
        {"text": "Docker is a containerization platform", "type": "semantic"},
        {"text": "The team has 12 members", "type": "semantic"},
        {"text": "Our office is on the 5th floor", "type": "semantic"},
        {"text": "The product is called DataSync Pro", "type": "semantic"},
        {"text": "Python was created by Guido van Rossum", "type": "semantic"},
        {"text": "The server has 16GB of RAM", "type": "semantic"},
        {"text": "JSON stands for JavaScript Object Notation", "type": "semantic"},
        # Procedural examples (23 - instructions and how-to)
        {
            "text": "To make coffee, first boil water then add coffee grounds",
            "type": "procedural",
        },
        {
            "text": "How to connect to the database: use connection pooling",
            "type": "procedural",
        },
        {"text": "Steps to deploy: 1. Build 2. Test 3. Deploy", "type": "procedural"},
        {
            "text": "The process for code review involves PR approval",
            "type": "procedural",
        },
        {
            "text": "Method for handling errors: try-catch with logging",
            "type": "procedural",
        },
        {
            "text": "First install dependencies, then run the build script",
            "type": "procedural",
        },
        {
            "text": "Recipe: Mix flour and eggs, then bake for 30 minutes",
            "type": "procedural",
        },
        {
            "text": "Instructions: Press the button then wait 5 seconds",
            "type": "procedural",
        },
        {"text": "The solution is to use async operations", "type": "procedural"},
        {"text": "To fix the bug, clear the cache and restart", "type": "procedural"},
        {
            "text": "How to set up authentication: configure JWT tokens",
            "type": "procedural",
        },
        {"text": "Algorithm: Sort the array then binary search", "type": "procedural"},
        {
            "text": "Workflow: Design, implement, test, deploy, monitor",
            "type": "procedural",
        },
        {"text": "To optimize queries, add proper indexes", "type": "procedural"},
        {
            "text": "Pattern for error handling: log, notify, recover",
            "type": "procedural",
        },
        {"text": "How to debug: reproduce, isolate, fix, verify", "type": "procedural"},
        {
            "text": "Template for API endpoints: validate, process, respond",
            "type": "procedural",
        },
        {
            "text": "Steps for migration: backup, migrate, validate",
            "type": "procedural",
        },
        {"text": "To improve performance, use caching and CDN", "type": "procedural"},
        {
            "text": "Method to scale: horizontal scaling with load balancer",
            "type": "procedural",
        },
        {"text": "How to write tests: arrange, act, assert", "type": "procedural"},
        {
            "text": "Process for releases: branch, test, merge, tag",
            "type": "procedural",
        },
        {"text": "To secure the API, implement rate limiting", "type": "procedural"},
        # Working examples (24 - tasks and current focus)
        {"text": "Need to finish the report by tomorrow", "type": "working"},
        {"text": "Currently working on the authentication module", "type": "working"},
        {"text": "TODO: implement error handling", "type": "working"},
        {"text": "The migration is in progress", "type": "working"},
        {"text": "Task: Update the documentation", "type": "working"},
        {"text": "Right now I'm debugging the API", "type": "working"},
        {"text": "This feature is pending review", "type": "working"},
        {"text": "Urgent: Fix the login bug today", "type": "working"},
        {"text": "Working on optimizing the database queries", "type": "working"},
        {"text": "Need to complete the sprint by Friday", "type": "working"},
        {"text": "Currently refactoring the payment module", "type": "working"},
        {"text": "Task in progress: implement caching", "type": "working"},
        {"text": "Deadline for the feature is next week", "type": "working"},
        {"text": "I'm investigating the performance issue", "type": "working"},
        {"text": "Ongoing: database schema migration", "type": "working"},
        {"text": "Priority: resolve customer complaints", "type": "working"},
        {"text": "Active task: writing unit tests", "type": "working"},
        {"text": "Need to review pull requests today", "type": "working"},
        {"text": "Currently setting up CI/CD pipeline", "type": "working"},
        {"text": "Working on the mobile app integration", "type": "working"},
        {"text": "Must finish the security audit this week", "type": "working"},
        {"text": "In the middle of debugging the race condition", "type": "working"},
        {"text": "TODO: update all package dependencies", "type": "working"},
        {"text": "Pending task: configure monitoring alerts", "type": "working"},
        # Sensory examples (23 - sensory descriptions)
        {"text": "The coffee smells like fresh roasted beans", "type": "sensory"},
        {"text": "The interface looks bright and colorful", "type": "sensory"},
        {"text": "The alarm sounds very loud and harsh", "type": "sensory"},
        {"text": "The fabric feels soft and smooth", "type": "sensory"},
        {"text": "The food tastes sweet and spicy", "type": "sensory"},
        {"text": "The room is painted bright yellow", "type": "sensory"},
        {"text": "The texture is rough and bumpy", "type": "sensory"},
        {"text": "It sounds like thunder in the distance", "type": "sensory"},
        {"text": "The water feels cold on my skin", "type": "sensory"},
        {"text": "The UI has a dark blue color scheme", "type": "sensory"},
        {"text": "The notification sound is gentle and pleasant", "type": "sensory"},
        {"text": "The keyboard feels mechanical and clicky", "type": "sensory"},
        {"text": "The screen looks too bright in dark mode", "type": "sensory"},
        {"text": "The fan sounds like it's running constantly", "type": "sensory"},
        {"text": "The new logo is colorful and vibrant", "type": "sensory"},
        {"text": "The error beep is sharp and annoying", "type": "sensory"},
        {"text": "The material feels lightweight and durable", "type": "sensory"},
        {"text": "The animation looks smooth and fluid", "type": "sensory"},
        {"text": "The coffee tastes bitter and strong", "type": "sensory"},
        {"text": "The office smells like fresh paint", "type": "sensory"},
        {"text": "The buttons feel responsive and tactile", "type": "sensory"},
        {"text": "The background music sounds relaxing", "type": "sensory"},
        {"text": "The design looks clean and minimalist", "type": "sensory"},
        # Preference examples (30 - preferences and choices)
        {"text": "I prefer Python over JavaScript for backend", "type": "preference"},
        {"text": "The user likes dark mode interfaces", "type": "preference"},
        {"text": "We always use pytest for testing", "type": "preference"},
        {"text": "TypeScript is better than plain JavaScript", "type": "preference"},
        {"text": "I love working with React for frontend", "type": "preference"},
        {"text": "The team favors microservices architecture", "type": "preference"},
        {"text": "I'd rather use PostgreSQL instead of MySQL", "type": "preference"},
        {"text": "I hate debugging CSS issues", "type": "preference"},
        {"text": "We prefer tabs over spaces for indentation", "type": "preference"},
        {"text": "I prefer dark mode for coding", "type": "preference"},
        {"text": "We prefer Git over SVN for version control", "type": "preference"},
        {"text": "I like Python more than Java", "type": "preference"},
        {"text": "We choose AWS over Azure for cloud services", "type": "preference"},
        {"text": "I don't like working with legacy code", "type": "preference"},
        {"text": "The ideal solution would use GraphQL", "type": "preference"},
        {"text": "We always use 4 spaces for indentation", "type": "preference"},
        {"text": "I prefer TDD approach for development", "type": "preference"},
        {"text": "My favorite framework is Django", "type": "preference"},
        {"text": "We hate dealing with CORS issues", "type": "preference"},
        {"text": "I choose VS Code over other editors", "type": "preference"},
        {"text": "The team prefers agile methodology", "type": "preference"},
        {"text": "I like functional programming paradigm", "type": "preference"},
        {"text": "We don't like monolithic architectures", "type": "preference"},
        {"text": "Docker is our preferred containerization tool", "type": "preference"},
        {"text": "I love using type hints in Python", "type": "preference"},
        {"text": "We prefer REST APIs over SOAP", "type": "preference"},
        {"text": "I hate verbose configuration files", "type": "preference"},
        {"text": "The ideal database would be NoSQL", "type": "preference"},
        {"text": "We choose Linux servers over Windows", "type": "preference"},
        {"text": "I prefer automated testing over manual", "type": "preference"},
    ]


# Confidence adjustment rules
CONFIDENCE_RULES = {
    "high_confidence_indicators": [
        "definitely",
        "certainly",
        "absolutely",
        "always",
        "never",
        "must",
        "required",
        "critical",
        "essential",
    ],
    "medium_confidence_indicators": [
        "usually",
        "typically",
        "generally",
        "often",
        "commonly",
        "frequently",
        "normally",
        "mostly",
    ],
    "low_confidence_indicators": [
        "maybe",
        "perhaps",
        "possibly",
        "might",
        "could",
        "sometimes",
        "occasionally",
        "rarely",
    ],
}


def adjust_confidence_by_indicators(content: str, base_confidence: float) -> float:
    """
    Adjust confidence score based on linguistic indicators.

    Args:
        content: The text content to analyze
        base_confidence: Initial confidence score

    Returns:
        Adjusted confidence score
    """
    content_lower = content.lower()

    # Check for high confidence indicators
    for indicator in CONFIDENCE_RULES["high_confidence_indicators"]:
        if indicator in content_lower:
            return min(1.0, base_confidence + 0.2)

    # Check for low confidence indicators
    for indicator in CONFIDENCE_RULES["low_confidence_indicators"]:
        if indicator in content_lower:
            return max(0.3, base_confidence - 0.2)

    # Check for medium confidence (no change needed)
    return base_confidence


# Memory importance weights by category
IMPORTANCE_WEIGHTS = {
    "contains_code": 0.1,
    "contains_url": 0.05,
    "contains_numbers": 0.05,
    "is_question": -0.1,
    "is_command": 0.15,
    "has_entities": 0.1,
    "is_long": 0.05,
    "is_technical": 0.1,
}


def calculate_content_importance(content: str) -> dict[str, bool]:
    """
    Calculate importance factors from content.

    Args:
        content: The text content to analyze

    Returns:
        Dictionary of importance factors
    """
    factors = {}

    # Check for code blocks or snippets
    factors["contains_code"] = bool(
        re.search(r"```|def |class |function |import |from |return ", content)
    )

    # Check for URLs
    factors["contains_url"] = bool(re.search(r"https?://[^\s]+", content))

    # Check for numbers/metrics
    factors["contains_numbers"] = bool(re.search(r"\b\d+\.?\d*\b", content))

    # Check if it's a question
    factors["is_question"] = "?" in content

    # Check if it's a command/instruction
    factors["is_command"] = bool(
        re.search(r"^(do |make |create |update |delete |run |execute )", content.lower())
    )

    # Check for named entities (simplified)
    factors["has_entities"] = bool(re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content))

    # Check if it's long content
    factors["is_long"] = len(content.split()) > 50

    # Check if it's technical
    tech_terms = [
        "api",
        "database",
        "server",
        "client",
        "backend",
        "frontend",
        "algorithm",
        "function",
        "method",
        "class",
        "module",
        "package",
    ]
    factors["is_technical"] = any(term in content.lower() for term in tech_terms)

    return factors
