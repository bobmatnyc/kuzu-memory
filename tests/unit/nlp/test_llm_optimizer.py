"""Unit tests for LLMOptimizer in kuzu_memory.nlp.llm_optimizer."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

from kuzu_memory.nlp.llm_optimizer import (  # type: ignore[import-untyped]
    LLMOptimizer,
    _batch_limit_for_model,
)

# ---------------------------------------------------------------------------
# Helpers / minimal stubs
# ---------------------------------------------------------------------------


@dataclass
class _FakeMemory:
    id: str
    content: str


@dataclass
class _FakeCluster:
    cluster_id: str
    memories: list[_FakeMemory]
    centroid_memory: _FakeMemory
    similarity_scores: dict[str, float] = field(default_factory=dict)
    avg_similarity: float = 1.0


def _make_adapter(rows: list[dict[str, Any]] | None = None) -> MagicMock:
    """Return a mock KuzuAdapter whose execute_query yields *rows*."""
    adapter = MagicMock()
    adapter.execute_query.return_value = rows or []
    return adapter


def _make_optimizer(adapter: MagicMock, model: str = "llama3.1:8b") -> LLMOptimizer:
    return LLMOptimizer(
        adapter=adapter,
        endpoint="http://localhost:11434",
        model=model,
        timeout_ms=5000,
        max_tokens=256,
    )


# ---------------------------------------------------------------------------
# _batch_limit_for_model tests
# ---------------------------------------------------------------------------


class TestBatchLimitForModel:
    def test_2b_model_returns_5(self) -> None:
        assert _batch_limit_for_model("gemma2:2b") == 5

    def test_4b_model_returns_8(self) -> None:
        assert _batch_limit_for_model("phi4-mini:4b") == 8

    def test_8b_model_returns_15(self) -> None:
        assert _batch_limit_for_model("llama3.1:8b") == 15

    def test_unknown_model_returns_default_10(self) -> None:
        assert _batch_limit_for_model("mystery-model:13b") == 10

    def test_empty_model_name_returns_default(self) -> None:
        assert _batch_limit_for_model("") == 10

    def test_case_insensitive_matching(self) -> None:
        # model names may come in uppercase
        assert _batch_limit_for_model("Gemma2:2B") == 5


# ---------------------------------------------------------------------------
# generate_summary tests
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    def _cluster(self, contents: list[str]) -> _FakeCluster:
        memories = [_FakeMemory(id=f"mem-{i}", content=c) for i, c in enumerate(contents)]
        return _FakeCluster(
            cluster_id="cluster-abc",
            memories=memories,
            centroid_memory=memories[0],
        )

    def test_happy_path_returns_llm_response(self) -> None:
        adapter = _make_adapter()
        optimizer = _make_optimizer(adapter)
        cluster = self._cluster(["alpha", "beta", "gamma"])

        with patch(
            "kuzu_memory.nlp.llm_optimizer.LLMOptimizer._llm",
            return_value="Combined summary.",
        ):
            summary = optimizer.generate_summary(cluster)

        assert summary == "Combined summary."

    def test_fallback_to_centroid_on_exception(self) -> None:
        adapter = _make_adapter()
        optimizer = _make_optimizer(adapter)
        cluster = self._cluster(["centroid content", "other"])

        with patch(
            "kuzu_memory.nlp.llm_optimizer.LLMOptimizer._llm",
            side_effect=RuntimeError("LLM down"),
        ):
            summary = optimizer.generate_summary(cluster)

        assert summary == "centroid content"

    def test_numbered_prompt_contains_all_contents(self) -> None:
        """Verify that generate_summary passes all memory contents to the LLM."""
        adapter = _make_adapter()
        optimizer = _make_optimizer(adapter)
        cluster = self._cluster(["A", "B", "C"])

        captured_user: list[str] = []

        def _fake_llm(system: str, user: str, max_tokens: int | None = None) -> str:
            captured_user.append(user)
            return "summary"

        with patch.object(optimizer, "_llm", side_effect=_fake_llm):
            optimizer.generate_summary(cluster)

        assert "[1] A" in captured_user[0]
        assert "[2] B" in captured_user[0]
        assert "[3] C" in captured_user[0]


# ---------------------------------------------------------------------------
# reclassify_pass tests
# ---------------------------------------------------------------------------


class TestReclassifyPass:
    def test_updates_db_for_valid_category(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Always use RLock for Kuzu writes."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="rule"):
            count, _ = optimizer.reclassify_pass(limit=10, dry_run=False)

        assert count == 1
        # Two calls: one SELECT, one UPDATE
        assert adapter.execute_query.call_count == 2
        # The UPDATE call should set knowledge_type = 'rule'
        update_call = adapter.execute_query.call_args_list[1]
        assert update_call.args[1]["kt"] == "rule"

    def test_skips_note_response(self) -> None:
        """When LLM returns 'note', no UPDATE should be issued."""
        rows = [{"id": "abc12345-xxxx", "content": "Some generic note."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="note"):
            count, _ = optimizer.reclassify_pass(limit=10, dry_run=False)

        assert count == 0
        assert adapter.execute_query.call_count == 1  # Only SELECT

    def test_dry_run_does_not_write(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Use repository pattern for DB access."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="pattern"):
            count, _ = optimizer.reclassify_pass(limit=10, dry_run=True)

        # In dry_run mode the update is skipped → count stays 0
        assert count == 0
        assert adapter.execute_query.call_count == 1

    def test_handles_invalid_llm_response_gracefully(self) -> None:
        """Non-enum LLM output is normalised to 'note' — no write, no crash."""
        rows = [{"id": "abc12345-xxxx", "content": "Something."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="completely_invalid_category"):
            count, _ = optimizer.reclassify_pass(limit=10, dry_run=False)

        assert count == 0
        assert adapter.execute_query.call_count == 1

    def test_handles_llm_exception_per_row(self) -> None:
        """An LLM error on one row must not crash the whole pass."""
        rows = [
            {"id": "row1-xxxx", "content": "Row one."},
            {"id": "row2-xxxx", "content": "Row two."},
        ]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        call_count = 0

        def _side_effect(system: str, user: str, max_tokens: int | None = None) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("timeout")
            return "pattern"

        with patch.object(optimizer, "_llm", side_effect=_side_effect):
            count, _ = optimizer.reclassify_pass(limit=10, dry_run=False)

        assert count == 1  # Second row succeeds

    def test_skips_rows_with_missing_content(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": ""}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="rule") as mock_llm:
            count, _ = optimizer.reclassify_pass(limit=10, dry_run=False)

        mock_llm.assert_not_called()
        assert count == 0


# ---------------------------------------------------------------------------
# rescore_pass tests
# ---------------------------------------------------------------------------


class TestRescorePass:
    def test_updates_importance_when_different(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Critical safety rule."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="0.9"):
            count, _ = optimizer.rescore_pass(limit=10, dry_run=False)

        assert count == 1
        update_call = adapter.execute_query.call_args_list[1]
        assert abs(update_call.args[1]["score"] - 0.9) < 1e-6

    def test_clamps_score_above_1_to_1(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Anything."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="1.5"):
            _, _ = optimizer.rescore_pass(limit=10, dry_run=False)

        update_call = adapter.execute_query.call_args_list[1]
        assert update_call.args[1]["score"] == 1.0

    def test_clamps_score_below_0_to_0(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Anything."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="-0.3"):
            _, _ = optimizer.rescore_pass(limit=10, dry_run=False)

        update_call = adapter.execute_query.call_args_list[1]
        assert update_call.args[1]["score"] == 0.0

    def test_no_update_when_score_is_still_05(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Meh."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="0.5"):
            count, _ = optimizer.rescore_pass(limit=10, dry_run=False)

        assert count == 0
        assert adapter.execute_query.call_count == 1  # Only SELECT

    def test_handles_parse_error(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Something."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="not_a_number"):
            count, _ = optimizer.rescore_pass(limit=10, dry_run=False)

        assert count == 0
        assert adapter.execute_query.call_count == 1

    def test_dry_run_does_not_write(self) -> None:
        rows = [{"id": "abc12345-xxxx", "content": "Important pattern."}]
        adapter = _make_adapter(rows)
        optimizer = _make_optimizer(adapter)

        with patch.object(optimizer, "_llm", return_value="0.9"):
            count, _ = optimizer.rescore_pass(limit=10, dry_run=True)

        assert count == 0
        assert adapter.execute_query.call_count == 1


# ---------------------------------------------------------------------------
# run_all_passes tests
# ---------------------------------------------------------------------------


class TestRunAllPasses:
    def test_calls_both_sub_passes(self) -> None:
        adapter = _make_adapter()
        optimizer = _make_optimizer(adapter)

        with (
            patch.object(
                optimizer,
                "reclassify_pass",
                return_value=(3, ["  detail-a"]),
            ) as mock_rc,
            patch.object(
                optimizer,
                "rescore_pass",
                return_value=(7, ["  detail-b"]),
            ) as mock_rs,
        ):
            result = optimizer.run_all_passes(limit=50, dry_run=False)

        mock_rc.assert_called_once_with(limit=50, dry_run=False)
        mock_rs.assert_called_once_with(limit=30, dry_run=False)  # min(50,30)
        assert result.memories_reclassified == 3
        assert result.memories_rescored == 7

    def test_returns_correct_metadata(self) -> None:
        adapter = _make_adapter()
        optimizer = _make_optimizer(adapter, model="gemma3:4b")

        with (
            patch.object(optimizer, "reclassify_pass", return_value=(0, [])),
            patch.object(optimizer, "rescore_pass", return_value=(0, [])),
        ):
            result = optimizer.run_all_passes(limit=20, dry_run=True)

        assert result.success is True
        assert result.model_used == "gemma3:4b"
        assert result.provider == "local"
        assert result.dry_run is True
        assert result.summaries_generated == 0  # Not used in run_all_passes
        assert result.execution_time_ms >= 0

    def test_details_concatenated_from_both_passes(self) -> None:
        adapter = _make_adapter()
        optimizer = _make_optimizer(adapter)

        with (
            patch.object(optimizer, "reclassify_pass", return_value=(1, ["rc-line"])),
            patch.object(optimizer, "rescore_pass", return_value=(1, ["rs-line"])),
        ):
            result = optimizer.run_all_passes()

        assert "rc-line" in result.details
        assert "rs-line" in result.details

    def test_rescore_limit_capped_at_30(self) -> None:
        """rescore_pass limit must never exceed 30 regardless of top-level limit."""
        adapter = _make_adapter()
        optimizer = _make_optimizer(adapter)

        with (
            patch.object(optimizer, "reclassify_pass", return_value=(0, [])),
            patch.object(optimizer, "rescore_pass", return_value=(0, [])) as mock_rs,
        ):
            optimizer.run_all_passes(limit=100, dry_run=False)

        mock_rs.assert_called_once_with(limit=30, dry_run=False)
