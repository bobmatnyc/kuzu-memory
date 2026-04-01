"""
Unit tests for the rule-based knowledge type classifier.

Tests cover:
- Each classification category (rule, gotcha, architecture, pattern, convention)
- Prefix-based triggers ("Rule:", "Gotcha:", etc.)
- Keyword-based triggers for each category
- Edge cases: empty string, whitespace-only, very long content, mixed signals
- The classify_if_unset helper
- Performance: each call must complete in < 1ms
"""

from __future__ import annotations

import time

import pytest

from kuzu_memory.core.knowledge_classifier import classify_if_unset, classify_knowledge_type

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _assert_fast(content: str, max_ms: float = 1.0) -> None:
    """Assert the classifier runs in under *max_ms* milliseconds."""
    start = time.perf_counter()
    classify_knowledge_type(content)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < max_ms, f"Classifier took {elapsed_ms:.2f}ms (limit {max_ms}ms)"


# ---------------------------------------------------------------------------
# Default / fallback
# ---------------------------------------------------------------------------


class TestDefaultNote:
    def test_empty_string(self) -> None:
        assert classify_knowledge_type("") == "note"

    def test_whitespace_only(self) -> None:
        assert classify_knowledge_type("   \n\t  ") == "note"

    def test_generic_observation(self) -> None:
        assert classify_knowledge_type("Today I worked on the auth module.") == "note"

    def test_random_sentence(self) -> None:
        assert classify_knowledge_type("The meeting went well.") == "note"


# ---------------------------------------------------------------------------
# RULE classification
# ---------------------------------------------------------------------------


class TestRuleClassification:
    def test_prefix_Rule_colon(self) -> None:
        assert classify_knowledge_type("Rule: always sanitize user input") == "rule"

    def test_prefix_RULE_colon(self) -> None:
        assert classify_knowledge_type("RULE: never bypass auth") == "rule"

    def test_keyword_always(self) -> None:
        assert classify_knowledge_type("You should always use the context manager here.") == "rule"

    def test_keyword_never(self) -> None:
        assert classify_knowledge_type("Never call close() directly on the pool.") == "rule"

    def test_keyword_must(self) -> None:
        assert classify_knowledge_type("Writes must be serialized with RLock.") == "rule"

    def test_keyword_must_not(self) -> None:
        assert classify_knowledge_type("You must not open two writers simultaneously.") == "rule"

    def test_keyword_required(self) -> None:
        assert classify_knowledge_type("Two-factor auth is required for all admin users.") == "rule"

    def test_keyword_mandatory(self) -> None:
        assert classify_knowledge_type("Code review is mandatory before merging.") == "rule"

    def test_keyword_do_not(self) -> None:
        assert classify_knowledge_type("Do not import KuzuMemory directly in CLI.") == "rule"

    def test_keyword_dont_ever(self) -> None:
        assert classify_knowledge_type("Don't ever disable the write lock.") == "rule"

    def test_keyword_enforced(self) -> None:
        assert classify_knowledge_type("Type checking is enforced in CI.") == "rule"

    def test_keyword_strict(self) -> None:
        assert classify_knowledge_type("Run mypy in strict mode on all modules.") == "rule"

    def test_keyword_forbidden(self) -> None:
        assert classify_knowledge_type("Direct DB access is forbidden in the CLI layer.") == "rule"

    def test_keyword_prohibited(self) -> None:
        assert classify_knowledge_type("Storing secrets in env is prohibited here.") == "rule"

    def test_case_insensitive_always(self) -> None:
        assert classify_knowledge_type("ALWAYS validate before storing.") == "rule"


# ---------------------------------------------------------------------------
# GOTCHA classification
# ---------------------------------------------------------------------------


class TestGotchaClassification:
    def test_prefix_Bug_colon(self) -> None:
        assert classify_knowledge_type("Bug: the parser fails on UTF-16 input") == "gotcha"

    def test_prefix_Fix_colon(self) -> None:
        assert classify_knowledge_type("Fix: added is_dir() guard to MCP tools") == "gotcha"

    def test_prefix_Gotcha_colon(self) -> None:
        assert classify_knowledge_type("Gotcha: Kuzu enforces single-writer") == "gotcha"

    def test_keyword_bug(self) -> None:
        assert classify_knowledge_type("There was a bug in the parser for nested JSON.") == "gotcha"

    def test_keyword_gotcha(self) -> None:
        assert (
            classify_knowledge_type("gotcha — passing a directory to KuzuAdapter crashes.")
            == "gotcha"
        )

    def test_keyword_watch_out(self) -> None:
        assert classify_knowledge_type("Watch out for the GIL when using threads here.") == "gotcha"

    def test_keyword_careful(self) -> None:
        assert classify_knowledge_type("Be careful about the order of cleanup calls.") == "gotcha"

    def test_keyword_warning(self) -> None:
        assert classify_knowledge_type("Warning: the pool silently drops connections.") == "gotcha"

    def test_keyword_caveat(self) -> None:
        assert classify_knowledge_type("Caveat: this only works with ASCII paths.") == "gotcha"

    def test_keyword_pitfall(self) -> None:
        assert (
            classify_knowledge_type("A common pitfall is forgetting to call initialize().")
            == "gotcha"
        )

    def test_keyword_broken(self) -> None:
        assert classify_knowledge_type("The retry logic was broken after the refactor.") == "gotcha"

    def test_keyword_crash(self) -> None:
        assert classify_knowledge_type("Opening two writers causes a crash on macOS.") == "gotcha"

    def test_keyword_deadlock(self) -> None:
        assert classify_knowledge_type("Using Lock instead of RLock causes a deadlock.") == "gotcha"

    def test_keyword_race_condition(self) -> None:
        assert classify_knowledge_type("There is a race condition in the queue flush.") == "gotcha"

    def test_keyword_unexpected(self) -> None:
        assert classify_knowledge_type("It unexpectedly deletes the temp file on exit.") == "gotcha"

    def test_keyword_surprisingly(self) -> None:
        assert (
            classify_knowledge_type("Surprisingly, the sort is not stable by default.") == "gotcha"
        )

    def test_keyword_counter_intuitive(self) -> None:
        assert (
            classify_knowledge_type("The API is counter-intuitive: close() opens a new session.")
            == "gotcha"
        )


# ---------------------------------------------------------------------------
# ARCHITECTURE classification
# ---------------------------------------------------------------------------


class TestArchitectureClassification:
    def test_prefix_Architecture_colon(self) -> None:
        assert (
            classify_knowledge_type("Architecture: the MCP server is single-process")
            == "architecture"
        )

    def test_prefix_Design_colon(self) -> None:
        assert (
            classify_knowledge_type("Design: we chose a layered approach for the CLI")
            == "architecture"
        )

    def test_keyword_architecture(self) -> None:
        assert (
            classify_knowledge_type("The architecture uses a service-oriented design.")
            == "architecture"
        )

    def test_keyword_design_decision(self) -> None:
        assert (
            classify_knowledge_type(
                "A key design decision was to embed Kuzu instead of running it separately."
            )
            == "architecture"
        )

    def test_keyword_we_decided(self) -> None:
        assert (
            classify_knowledge_type("We decided to use SOA for all database access.")
            == "architecture"
        )

    def test_keyword_chose_to(self) -> None:
        assert (
            classify_knowledge_type("We chose to vendor the MCP installer as a submodule.")
            == "architecture"
        )

    def test_keyword_trade_off(self) -> None:
        assert (
            classify_knowledge_type("The trade-off is: less flexibility for much simpler code.")
            == "architecture"
        )

    def test_keyword_SOA(self) -> None:
        assert (
            classify_knowledge_type("SOA with DI is the primary architectural pattern here.")
            == "architecture"
        )

    def test_keyword_dependency_injection(self) -> None:
        assert (
            classify_knowledge_type("Dependency injection is used to wire all services.")
            == "architecture"
        )

    def test_keyword_microservice(self) -> None:
        assert (
            classify_knowledge_type("The auth microservice owns all identity data.")
            == "architecture"
        )

    def test_keyword_monolith(self) -> None:
        assert (
            classify_knowledge_type("We kept the monolith because deployment is simpler.")
            == "architecture"
        )

    def test_keyword_service_layer(self) -> None:
        assert (
            classify_knowledge_type("All DB access goes through the service layer.")
            == "architecture"
        )

    def test_keyword_module_boundary_with_decision(self) -> None:
        assert (
            classify_knowledge_type("The module boundary was a design decision to isolate the CLI.")
            == "architecture"
        )


# ---------------------------------------------------------------------------
# PATTERN classification
# ---------------------------------------------------------------------------


class TestPatternClassification:
    def test_prefix_Pattern_colon(self) -> None:
        assert (
            classify_knowledge_type("Pattern: use retry with exponential backoff for all API calls")
            == "pattern"
        )

    def test_prefix_Approach_colon(self) -> None:
        assert (
            classify_knowledge_type("Approach: wrap all DB calls with a context manager")
            == "pattern"
        )

    def test_keyword_pattern(self) -> None:
        assert (
            classify_knowledge_type("The repository pattern keeps storage logic isolated.")
            == "pattern"
        )

    def test_keyword_approach(self) -> None:
        assert (
            classify_knowledge_type("The standard approach for async tasks is a worker pool.")
            == "pattern"
        )

    def test_keyword_technique(self) -> None:
        assert (
            classify_knowledge_type("A useful technique is to debounce writes to the graph DB.")
            == "pattern"
        )

    def test_keyword_strategy(self) -> None:
        assert classify_knowledge_type("The retry strategy uses exponential backoff.") == "pattern"

    def test_keyword_workflow(self) -> None:
        assert (
            classify_knowledge_type("The standard workflow: branch → PR → review → merge.")
            == "pattern"
        )

    def test_keyword_best_practice(self) -> None:
        # "always" (rule) beats "best practice" (pattern) per priority ordering
        assert (
            classify_knowledge_type(
                "Best practice: always close DB connections in a finally block."
            )
            == "rule"
        )

    def test_keyword_best_practice_without_rule_trigger(self) -> None:
        assert (
            classify_knowledge_type("Best practice: close DB connections in a finally block.")
            == "pattern"
        )

    def test_keyword_template(self) -> None:
        assert classify_knowledge_type("Use this template for new CLI commands.") == "pattern"

    def test_keyword_recipe(self) -> None:
        assert classify_knowledge_type("Here is the recipe for adding a new MCP tool.") == "pattern"

    def test_keyword_boilerplate(self) -> None:
        assert (
            classify_knowledge_type("Copy this boilerplate for new service classes.") == "pattern"
        )

    def test_keyword_prefer_over(self) -> None:
        assert (
            classify_knowledge_type("Prefer uv run over pip install for reproducibility.")
            == "pattern"
        )


# ---------------------------------------------------------------------------
# CONVENTION classification
# ---------------------------------------------------------------------------


class TestConventionClassification:
    def test_prefix_Convention_colon(self) -> None:
        assert (
            classify_knowledge_type("Convention: Google-style docstrings on all public APIs")
            == "convention"
        )

    def test_prefix_Standard_colon(self) -> None:
        assert (
            classify_knowledge_type("Standard: run make pre-publish before every commit")
            == "convention"
        )

    def test_keyword_convention(self) -> None:
        assert (
            classify_knowledge_type("The convention is to name test files test_<module>.py.")
            == "convention"
        )

    def test_keyword_style_guide(self) -> None:
        assert (
            classify_knowledge_type(
                "Our style guide requires 88-char line lengths (black default)."
            )
            == "convention"
        )

    def test_keyword_formatting(self) -> None:
        assert (
            classify_knowledge_type("Code formatting is handled by ruff with default settings.")
            == "convention"
        )

    def test_keyword_naming_convention(self) -> None:
        assert (
            classify_knowledge_type("Follow the naming convention: snake_case for all variables.")
            == "convention"
        )

    def test_keyword_coding_standards(self) -> None:
        # "enforced" triggers rule before "coding standards" triggers convention
        assert (
            classify_knowledge_type("Coding standards are enforced via ruff and mypy in CI.")
            == "rule"
        )

    def test_keyword_coding_standards_without_rule_trigger(self) -> None:
        assert (
            classify_knowledge_type("Coding standards: use ruff and mypy in all modules.")
            == "convention"
        )

    def test_keyword_code_review(self) -> None:
        assert (
            classify_knowledge_type("Code review is done via GitHub PRs, minimum one approval.")
            == "convention"
        )

    def test_keyword_commit_messages(self) -> None:
        assert (
            classify_knowledge_type("Commit messages follow the conventional commits format.")
            == "convention"
        )

    def test_keyword_we_use(self) -> None:
        assert (
            classify_knowledge_type("We use pytest for all unit and integration tests.")
            == "convention"
        )

    def test_keyword_our_standard(self) -> None:
        assert (
            classify_knowledge_type("Our standard is to keep files under 800 lines.")
            == "convention"
        )

    def test_keyword_project_uses(self) -> None:
        assert (
            classify_knowledge_type("This project uses ruff instead of flake8 for linting.")
            == "convention"
        )


# ---------------------------------------------------------------------------
# Priority ordering (first match wins)
# ---------------------------------------------------------------------------


class TestPriorityOrdering:
    def test_rule_beats_gotcha(self) -> None:
        """'always' (rule) and 'careful' (gotcha) — rule wins."""
        assert classify_knowledge_type("Always be careful about the lock.") == "rule"

    def test_rule_beats_pattern(self) -> None:
        """'must' (rule) and 'pattern' (pattern) — rule wins."""
        assert classify_knowledge_type("You must follow this pattern.") == "rule"

    def test_gotcha_beats_architecture(self) -> None:
        """'gotcha' prefix beats architecture keyword."""
        assert (
            classify_knowledge_type(
                "Gotcha: the service layer has a deadlock risk in architecture."
            )
            == "gotcha"
        )

    def test_gotcha_beats_convention(self) -> None:
        """'warning' (gotcha) beats 'our standard' (convention)."""
        assert (
            classify_knowledge_type("Warning: our standard retry logic does not handle 429.")
            == "gotcha"
        )

    def test_architecture_beats_pattern(self) -> None:
        """'architecture' keyword beats 'pattern' keyword."""
        assert (
            classify_knowledge_type("The architecture follows the repository pattern.")
            == "architecture"
        )

    def test_pattern_beats_convention(self) -> None:
        """'best practice' (pattern) beats 'we use' (convention)."""
        assert (
            classify_knowledge_type("Best practice: we use a semaphore to limit concurrency.")
            == "pattern"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_very_long_content(self) -> None:
        """Classifier handles large content without error."""
        long_content = "This is a long note. " * 500  # ~10 KB
        result = classify_knowledge_type(long_content)
        assert result == "note"

    def test_long_rule_content(self) -> None:
        """Rule keyword found in a long string."""
        long_content = (
            "Some context. " * 200 + " You must always validate input. " + "More text. " * 200
        )
        assert classify_knowledge_type(long_content) == "rule"

    def test_content_with_newlines(self) -> None:
        assert (
            classify_knowledge_type("Background info.\nBug: found a deadlock\nMore text.")
            == "gotcha"
        )

    def test_content_with_tabs(self) -> None:
        assert classify_knowledge_type("Rule:\tNever open two writers.") == "rule"

    def test_mixed_case_prefix(self) -> None:
        assert (
            classify_knowledge_type("GOTCHA: Kuzu enforces single-writer per process.") == "gotcha"
        )

    def test_only_punctuation(self) -> None:
        result = classify_knowledge_type("!!!...???")
        assert result == "note"

    def test_unicode_content(self) -> None:
        result = classify_knowledge_type("日本語のメモ: データベース設定について")
        assert result == "note"  # No matching keywords

    def test_content_starting_with_whitespace(self) -> None:
        assert classify_knowledge_type("  Rule: always validate.") == "rule"

    def test_single_word(self) -> None:
        assert classify_knowledge_type("rule") == "note"  # No colon — keyword check

    def test_keyword_in_code_snippet(self) -> None:
        """A 'never' inside code text still triggers rule classification."""
        assert (
            classify_knowledge_type("The function `never_call_twice()` must be idempotent.")
            == "rule"
        )


# ---------------------------------------------------------------------------
# classify_if_unset
# ---------------------------------------------------------------------------


class TestClassifyIfUnset:
    def test_none_triggers_classifier(self) -> None:
        assert classify_if_unset("Always use context managers.", None) == "rule"

    def test_note_triggers_classifier(self) -> None:
        assert classify_if_unset("Always use context managers.", "note") == "rule"

    def test_note_uppercase_triggers_classifier(self) -> None:
        assert classify_if_unset("Always use context managers.", "NOTE") == "rule"

    def test_explicit_type_preserved(self) -> None:
        """If caller passes an explicit type that is not 'note', keep it."""
        assert classify_if_unset("Always use context managers.", "architecture") == "architecture"

    def test_explicit_gotcha_preserved(self) -> None:
        assert classify_if_unset("Some content with no rule keywords.", "gotcha") == "gotcha"

    def test_empty_string_treated_as_unset(self) -> None:
        assert classify_if_unset("Always validate input.", "") == "rule"

    def test_returns_note_when_no_match(self) -> None:
        assert classify_if_unset("Today I updated the README.", None) == "note"

    def test_returns_note_when_no_match_and_note_passed(self) -> None:
        assert classify_if_unset("Today I updated the README.", "note") == "note"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_short_content_fast(self) -> None:
        _assert_fast("Always use the context manager.", max_ms=1.0)

    def test_medium_content_fast(self) -> None:
        content = "We decided on a service-oriented architecture. " * 20
        _assert_fast(content, max_ms=1.0)

    def test_long_content_fast(self) -> None:
        content = "Some generic note content. " * 500  # ~13 KB
        _assert_fast(content, max_ms=3.0)  # 3ms budget for large content on slow CI

    def test_hundred_calls_fast(self) -> None:
        """100 sequential calls must finish under 50ms total."""
        contents = [
            "Always validate user input.",
            "Watch out for the race condition.",
            "We decided on SOA.",
            "Pattern: use the repository pattern.",
            "Convention: Google-style docstrings.",
            "Just a generic note.",
            "",
            "Must not open two DB connections.",
            "The bug crashes on Windows.",
            "Best practice: prefer explicit imports.",
        ] * 10
        start = time.perf_counter()
        for c in contents:
            classify_knowledge_type(c)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"100 calls took {elapsed_ms:.2f}ms (limit 50ms)"
