"""Unit tests for LocalLLMReranker."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from kuzu_memory.core.config import LocalLLMConfig
from kuzu_memory.core.models import Memory
from kuzu_memory.recall.local_reranker import LocalLLMReranker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(content: str) -> Memory:
    """Create a minimal Memory for testing."""
    return Memory(content=content, valid_to=None, user_id=None, session_id=None)  # type: ignore[call-arg]


def _make_memories(n: int) -> list[Memory]:
    return [_make_memory(f"memory content {i}") for i in range(n)]


def _config(model: str = "phi3:mini", endpoint: str = "http://localhost:11434") -> LocalLLMConfig:
    return LocalLLMConfig(
        enabled=True,
        model=model,
        endpoint=endpoint,
        timeout_ms=5000,
        max_tokens=64,
    )


# ---------------------------------------------------------------------------
# Construction — model auto-detection
# ---------------------------------------------------------------------------


def test_reranker_uses_configured_model() -> None:
    """LocalLLMReranker uses model from config when explicitly set."""
    cfg = _config(model="custom-model")
    reranker = LocalLLMReranker(cfg)
    assert reranker._model == "custom-model"


def test_reranker_auto_detects_model_when_empty() -> None:
    """LocalLLMReranker calls detect_local_llm when model is empty."""
    cfg = _config(model="")
    mock_info = MagicMock()
    mock_info.available = True
    mock_info.endpoint = "http://localhost:11434"
    mock_info.default_model = "auto-detected-model"

    with patch("kuzu_memory.integrations.local_llm.detect_local_llm", return_value=mock_info):
        reranker = LocalLLMReranker(cfg)

    assert reranker._model == "auto-detected-model"


def test_reranker_stays_empty_when_no_llm_detected() -> None:
    """LocalLLMReranker keeps empty model when detection fails."""
    cfg = _config(model="")
    mock_info = MagicMock()
    mock_info.available = False

    with patch("kuzu_memory.integrations.local_llm.detect_local_llm", return_value=mock_info):
        reranker = LocalLLMReranker(cfg)

    assert reranker._model == ""


# ---------------------------------------------------------------------------
# rerank — happy path
# ---------------------------------------------------------------------------


def test_rerank_reorders_by_llm_response() -> None:
    """rerank reorders memories according to LLM index response."""
    memories = _make_memories(3)  # [0, 1, 2]
    cfg = _config()

    with patch("kuzu_memory.integrations.local_llm.chat_completion", return_value="2,0,1"):
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("test query", memories, top_k=3)

    assert result[0] is memories[2]
    assert result[1] is memories[0]
    assert result[2] is memories[1]


def test_rerank_respects_top_k() -> None:
    """rerank returns at most top_k memories."""
    memories = _make_memories(5)
    cfg = _config()

    with patch("kuzu_memory.integrations.local_llm.chat_completion", return_value="4,3,2,1,0"):
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("query", memories, top_k=2)

    assert len(result) == 2
    assert result[0] is memories[4]
    assert result[1] is memories[3]


def test_rerank_appends_unmentioned_memories() -> None:
    """rerank appends memories not mentioned by LLM to preserve completeness."""
    memories = _make_memories(3)  # [0, 1, 2]
    cfg = _config()

    # LLM only mentions 2 of 3
    with patch("kuzu_memory.integrations.local_llm.chat_completion", return_value="2,0"):
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("query", memories, top_k=3)

    assert len(result) == 3
    assert result[0] is memories[2]
    assert result[1] is memories[0]
    assert result[2] is memories[1]  # appended unmentioned


def test_rerank_ignores_out_of_range_indices() -> None:
    """rerank silently ignores indices that exceed the memories list length."""
    memories = _make_memories(2)  # indices 0, 1 only
    cfg = _config()

    with patch("kuzu_memory.integrations.local_llm.chat_completion", return_value="1,99,0"):
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("query", memories, top_k=2)

    # Index 99 is out of range — only valid indices used
    assert result[0] is memories[1]
    assert result[1] is memories[0]


# ---------------------------------------------------------------------------
# rerank — fallback behaviour
# ---------------------------------------------------------------------------


def test_rerank_fallback_on_llm_failure() -> None:
    """rerank returns original order (truncated) when chat_completion raises."""
    memories = _make_memories(5)
    cfg = _config()

    with patch(
        "kuzu_memory.integrations.local_llm.chat_completion",
        side_effect=Exception("connection refused"),
    ):
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("query", memories, top_k=3)

    # Should return first 3 in original order
    assert result == memories[:3]


def test_rerank_empty_memories_returns_empty() -> None:
    """rerank with empty input returns empty list without calling LLM."""
    cfg = _config()

    with patch("kuzu_memory.integrations.local_llm.chat_completion") as mock_chat:
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("query", [], top_k=5)

    assert result == []
    mock_chat.assert_not_called()


def test_rerank_skips_llm_when_no_model() -> None:
    """rerank returns original order when model is empty (no LLM available)."""
    memories = _make_memories(3)
    cfg = _config(model="")

    mock_info = MagicMock()
    mock_info.available = False

    with (
        patch("kuzu_memory.integrations.local_llm.detect_local_llm", return_value=mock_info),
        patch("kuzu_memory.integrations.local_llm.chat_completion") as mock_chat,
    ):
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("query", memories, top_k=3)

    assert result == memories[:3]
    mock_chat.assert_not_called()


# ---------------------------------------------------------------------------
# rerank — non-integer response tokens are filtered
# ---------------------------------------------------------------------------


def test_rerank_filters_non_digit_tokens() -> None:
    """rerank skips non-integer tokens in LLM response."""
    memories = _make_memories(3)
    cfg = _config()

    with patch(
        "kuzu_memory.integrations.local_llm.chat_completion",
        return_value="2, foo, 0, bar, 1",
    ):
        reranker = LocalLLMReranker(cfg)
        result = reranker.rerank("query", memories, top_k=3)

    assert result[0] is memories[2]
    assert result[1] is memories[0]
    assert result[2] is memories[1]
