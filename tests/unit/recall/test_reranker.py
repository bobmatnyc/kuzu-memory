"""
Unit tests for LLMReranker.

All tests use mocking so no real Anthropic API calls are made.
"""

from __future__ import annotations

import json
from concurrent.futures import TimeoutError as FuturesTimeoutError
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.core.config import RerankingConfig
from kuzu_memory.core.models import Memory
from kuzu_memory.recall.reranker import LLMReranker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(content: str, memory_id: str | None = None) -> Memory:
    """Create a minimal Memory for testing."""
    m = Memory(content=content)
    if memory_id is not None:
        object.__setattr__(m, "id", memory_id)
    return m


def _make_candidates(n: int = 5) -> list[Memory]:
    return [_make_memory(f"memory content {i}", memory_id=f"id-{i}") for i in range(n)]


def _disabled_config(**kwargs: object) -> RerankingConfig:
    return RerankingConfig(enabled=False, **kwargs)  # type: ignore[arg-type]


def _enabled_config(**kwargs: object) -> RerankingConfig:
    return RerankingConfig(enabled=True, **kwargs)  # type: ignore[arg-type]


def _fake_anthropic_response(ordered_ids: list[str]) -> MagicMock:
    """Build a mock Anthropic Messages.create() return value."""
    block = MagicMock()
    block.text = json.dumps(ordered_ids)
    response = MagicMock()
    response.content = [block]
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRerankDisabled:
    def test_reranker_returns_original_order_when_disabled(self) -> None:
        """When enabled=False, rerank() returns candidates[:limit] unchanged."""
        cfg = _disabled_config()
        reranker = LLMReranker(cfg)
        candidates = _make_candidates(5)
        result = reranker.rerank("test query", candidates, limit=3)

        assert result == candidates[:3]
        assert len(result) == 3

    def test_disabled_reranker_makes_no_api_call(self) -> None:
        """No anthropic import or network call should happen when disabled."""
        cfg = _disabled_config()
        reranker = LLMReranker(cfg)
        candidates = _make_candidates(3)

        with patch("builtins.__import__") as mock_import:
            reranker.rerank("query", candidates, limit=3)
            # anthropic should not have been imported
            imported_names = [call.args[0] for call in mock_import.call_args_list]
            assert "anthropic" not in imported_names


class TestRerankEnabled:
    def test_reranker_calls_llm_and_reorders(self) -> None:
        """LLM response is used to reorder the candidates."""
        candidates = _make_candidates(4)  # id-0 … id-3
        # LLM says: id-3 is most relevant, then id-1, id-0, id-2
        ordered_ids = ["id-3", "id-1", "id-0", "id-2"]

        mock_response = _fake_anthropic_response(ordered_ids)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = _enabled_config(model="claude-haiku-4-5", timeout_ms=2000)
        reranker = LLMReranker(cfg)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = reranker.rerank("test query", candidates, limit=4)

        result_ids = [m.id for m in result]
        assert result_ids == ordered_ids

    def test_reranker_limits_to_requested_limit(self) -> None:
        """Result length is capped at *limit* even if LLM returns all IDs."""
        candidates = _make_candidates(5)
        ordered_ids = [f"id-{i}" for i in range(5)]

        mock_response = _fake_anthropic_response(ordered_ids)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = _enabled_config(timeout_ms=2000)
        reranker = LLMReranker(cfg)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = reranker.rerank("query", candidates, limit=3)

        assert len(result) == 3


class TestRerankFallback:
    def test_reranker_falls_back_on_timeout(self) -> None:
        """TimeoutError in ThreadPoolExecutor falls back to original order."""
        candidates = _make_candidates(4)

        mock_anthropic_module = MagicMock()

        cfg = _enabled_config(timeout_ms=100)
        reranker = LLMReranker(cfg)

        # Make the future.result() raise FuturesTimeoutError
        with patch("kuzu_memory.recall.reranker.ThreadPoolExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor.__exit__ = MagicMock(return_value=False)
            mock_future = MagicMock()
            mock_future.result.side_effect = FuturesTimeoutError("timed out")
            mock_executor.submit.return_value = mock_future
            mock_executor_cls.return_value = mock_executor

            with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
                result = reranker.rerank("query", candidates, limit=3)

        assert result == candidates[:3]

    def test_reranker_falls_back_on_api_error(self) -> None:
        """Any exception from the API falls back to original order."""
        candidates = _make_candidates(4)

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API error")
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = _enabled_config(timeout_ms=2000)
        reranker = LLMReranker(cfg)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = reranker.rerank("query", candidates, limit=3)

        assert result == candidates[:3]

    def test_reranker_falls_back_when_anthropic_not_installed(self) -> None:
        """ImportError for anthropic falls back to original order."""
        candidates = _make_candidates(4)

        cfg = _enabled_config(timeout_ms=2000)
        reranker = LLMReranker(cfg)

        # Remove anthropic from sys.modules and make import fail
        with patch.dict("sys.modules", {"anthropic": None}):  # type: ignore[dict-item]
            result = reranker.rerank("query", candidates, limit=3)

        assert result == candidates[:3]


class TestRerankPartialAndUnknownIds:
    def test_reranker_handles_partial_id_response(self) -> None:
        """LLM returns only some IDs — omitted candidates are appended."""
        candidates = _make_candidates(4)  # id-0, id-1, id-2, id-3
        # LLM only mentions id-2 and id-0
        partial_ids = ["id-2", "id-0"]

        mock_response = _fake_anthropic_response(partial_ids)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = _enabled_config(timeout_ms=2000)
        reranker = LLMReranker(cfg)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = reranker.rerank("query", candidates, limit=4)

        result_ids = [m.id for m in result]
        # First two are the LLM-ranked ones, remaining appended in original order
        assert result_ids[:2] == ["id-2", "id-0"]
        # id-1 and id-3 appended
        assert set(result_ids[2:]) == {"id-1", "id-3"}
        assert len(result) == 4

    def test_reranker_ignores_unknown_ids_in_response(self) -> None:
        """IDs returned by the LLM that are not in candidates are silently skipped."""
        candidates = _make_candidates(3)  # id-0, id-1, id-2
        # LLM hallucinates id-999
        ordered_ids = ["id-999", "id-1", "id-0", "id-2"]

        mock_response = _fake_anthropic_response(ordered_ids)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = _enabled_config(timeout_ms=2000)
        reranker = LLMReranker(cfg)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = reranker.rerank("query", candidates, limit=3)

        result_ids = [m.id for m in result]
        assert "id-999" not in result_ids
        assert set(result_ids) == {"id-0", "id-1", "id-2"}


class TestRerankContent:
    def test_reranker_truncates_content_to_200_chars(self) -> None:
        """Prompt sent to LLM must contain at most 200 chars per memory content."""
        long_content = "x" * 500
        candidates = [_make_memory(long_content, memory_id="id-0")]

        captured_prompt: list[str] = []

        def _capture_create(**kwargs: object) -> MagicMock:
            messages = kwargs.get("messages", [])
            if messages:
                captured_prompt.append(str(messages[0]["content"]))  # type: ignore[index]
            block = MagicMock()
            block.text = '["id-0"]'
            resp = MagicMock()
            resp.content = [block]
            return resp

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = _capture_create
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = _enabled_config(timeout_ms=2000)
        reranker = LLMReranker(cfg)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            reranker.rerank("query", candidates, limit=1)

        assert captured_prompt, "No prompt was captured"
        prompt_text = captured_prompt[0]
        # The content snippet in the prompt should not exceed 200 chars
        # Parse the memories JSON from the prompt to verify
        start = prompt_text.find("[{")
        end = prompt_text.rfind("}]")
        if start != -1 and end != -1:
            memories_json = json.loads(prompt_text[start : end + 2])
            for mem in memories_json:
                assert len(mem["content"]) <= 200


class TestEnvVarConfig:
    def test_env_var_enables_reranking(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """KUZU_MEMORY_RERANK=1 sets enabled=True in from_dict()."""
        monkeypatch.setenv("KUZU_MEMORY_RERANK", "1")

        from kuzu_memory.core.config import KuzuMemoryConfig

        config = KuzuMemoryConfig.from_dict({})
        assert config.recall.reranking.enabled is True

    def test_env_var_not_set_leaves_reranking_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without the env var, reranking stays disabled by default."""
        monkeypatch.delenv("KUZU_MEMORY_RERANK", raising=False)

        from kuzu_memory.core.config import KuzuMemoryConfig

        config = KuzuMemoryConfig.from_dict({})
        assert config.recall.reranking.enabled is False
