"""Unit tests for local LLM detection and client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from kuzu_memory.integrations.local_llm import (
    _lm_studio_list_models,
    _ollama_list_models,
    _tcp_probe,
    chat_completion,
    detect_local_llm,
    stream_chat_completion,
    stream_chat_completion_full,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_http_response(payload: dict) -> MagicMock:
    """Build a mock urllib response that returns JSON."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# _tcp_probe
# ---------------------------------------------------------------------------


def test_tcp_probe_success() -> None:
    """tcp_probe returns True when socket connects successfully."""
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)

    with patch("socket.create_connection", return_value=mock_conn):
        assert _tcp_probe("localhost", 11434) is True


def test_tcp_probe_failure_oserror() -> None:
    """tcp_probe returns False on OSError (port closed)."""
    with patch("socket.create_connection", side_effect=OSError("refused")):
        assert _tcp_probe("localhost", 11434) is False


def test_tcp_probe_failure_timeout() -> None:
    """tcp_probe returns False on TimeoutError."""
    with patch("socket.create_connection", side_effect=TimeoutError("timed out")):
        assert _tcp_probe("localhost", 11434) is False


def test_tcp_probe_failure_connection_refused() -> None:
    """tcp_probe returns False on ConnectionRefusedError."""
    with patch("socket.create_connection", side_effect=ConnectionRefusedError):
        assert _tcp_probe("localhost", 11434) is False


# ---------------------------------------------------------------------------
# _ollama_list_models
# ---------------------------------------------------------------------------


def test_ollama_list_models_success() -> None:
    """_ollama_list_models returns model names from Ollama /api/tags."""
    payload = {"models": [{"name": "llama3.2:3b"}, {"name": "phi3:mini"}]}
    resp = _make_http_response(payload)

    with patch("urllib.request.urlopen", return_value=resp):
        models = _ollama_list_models("http://localhost:11434")

    assert models == ["llama3.2:3b", "phi3:mini"]


def test_ollama_list_models_empty_response() -> None:
    """_ollama_list_models returns empty list when no models present."""
    payload: dict = {"models": []}
    resp = _make_http_response(payload)

    with patch("urllib.request.urlopen", return_value=resp):
        models = _ollama_list_models("http://localhost:11434")

    assert models == []


def test_ollama_list_models_network_error() -> None:
    """_ollama_list_models returns empty list on network failure."""
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
        models = _ollama_list_models("http://localhost:11434")

    assert models == []


# ---------------------------------------------------------------------------
# _lm_studio_list_models
# ---------------------------------------------------------------------------


def test_lm_studio_list_models_success() -> None:
    """_lm_studio_list_models returns model IDs from /v1/models."""
    payload = {"data": [{"id": "lmstudio-community/Meta-Llama-3.1-8B"}]}
    resp = _make_http_response(payload)

    with patch("urllib.request.urlopen", return_value=resp):
        models = _lm_studio_list_models("http://localhost:1234")

    assert models == ["lmstudio-community/Meta-Llama-3.1-8B"]


def test_lm_studio_list_models_network_error() -> None:
    """_lm_studio_list_models returns empty list on failure."""
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        models = _lm_studio_list_models("http://localhost:1234")

    assert models == []


# ---------------------------------------------------------------------------
# detect_local_llm — Ollama path
# ---------------------------------------------------------------------------


def test_detect_ollama_with_models() -> None:
    """detect_local_llm returns Ollama provider when port open and models available."""
    with (
        patch("kuzu_memory.integrations.local_llm._tcp_probe", return_value=True),
        patch(
            "kuzu_memory.integrations.local_llm._ollama_list_models",
            return_value=["llama3.2:3b", "mistral:7b"],
        ),
    ):
        info = detect_local_llm()

    assert info.available is True
    assert info.provider == "ollama"
    assert "llama3.2:3b" in info.models
    assert info.default_model != ""


def test_detect_ollama_port_open_but_no_models() -> None:
    """detect_local_llm falls through when Ollama port is open but no models loaded."""
    with (
        patch(
            "kuzu_memory.integrations.local_llm._tcp_probe",
            side_effect=lambda host, port, **kw: port == 11434,  # Ollama open, LM Studio closed
        ),
        patch("kuzu_memory.integrations.local_llm._ollama_list_models", return_value=[]),
    ):
        info = detect_local_llm()

    # No models → falls through to LM Studio, which is also closed → not available
    assert info.available is False


# ---------------------------------------------------------------------------
# detect_local_llm — no provider
# ---------------------------------------------------------------------------


def test_detect_no_local_llm() -> None:
    """detect_local_llm returns available=False when both probes fail."""
    with patch("kuzu_memory.integrations.local_llm._tcp_probe", return_value=False):
        info = detect_local_llm()

    assert info.available is False
    assert info.provider == "none"
    assert info.endpoint == ""
    assert info.models == []
    assert info.default_model == ""


# ---------------------------------------------------------------------------
# detect_local_llm — model preference
# ---------------------------------------------------------------------------


def test_preferred_model_selection_phi() -> None:
    """detect_local_llm prefers phi over other models."""
    models = ["mistral:7b", "phi3:mini", "codellama:13b"]
    with (
        patch("kuzu_memory.integrations.local_llm._tcp_probe", return_value=True),
        patch("kuzu_memory.integrations.local_llm._ollama_list_models", return_value=models),
    ):
        info = detect_local_llm()

    assert "phi" in info.default_model.lower()


def test_preferred_model_selection_llama32() -> None:
    """detect_local_llm prefers llama3.2 when phi is not available."""
    models = ["mistral:7b", "llama3.2:3b", "codellama:13b"]
    with (
        patch("kuzu_memory.integrations.local_llm._tcp_probe", return_value=True),
        patch("kuzu_memory.integrations.local_llm._ollama_list_models", return_value=models),
    ):
        info = detect_local_llm()

    assert "llama3.2" in info.default_model.lower()


def test_preferred_model_selection_falls_back_to_first() -> None:
    """detect_local_llm uses first model when no preferred model found."""
    models = ["mistral:7b", "codellama:13b"]
    with (
        patch("kuzu_memory.integrations.local_llm._tcp_probe", return_value=True),
        patch("kuzu_memory.integrations.local_llm._ollama_list_models", return_value=models),
    ):
        info = detect_local_llm()

    assert info.default_model == "mistral:7b"


# ---------------------------------------------------------------------------
# detect_local_llm — LM Studio fallback
# ---------------------------------------------------------------------------


def test_detect_lm_studio_when_ollama_unavailable() -> None:
    """detect_local_llm falls through to LM Studio when Ollama is unavailable."""

    def probe(host: str, port: int, **kw: object) -> bool:
        return port == 1234  # Only LM Studio open

    with (
        patch("kuzu_memory.integrations.local_llm._tcp_probe", side_effect=probe),
        patch(
            "kuzu_memory.integrations.local_llm._lm_studio_list_models",
            return_value=["lmstudio-community/Llama-3.2-3B"],
        ),
    ):
        info = detect_local_llm()

    assert info.available is True
    assert info.provider == "lm_studio"
    assert info.default_model == "lmstudio-community/Llama-3.2-3B"


# ---------------------------------------------------------------------------
# chat_completion
# ---------------------------------------------------------------------------


def test_chat_completion_success() -> None:
    """chat_completion returns assistant message content on success."""
    response_payload = {
        "choices": [{"message": {"role": "assistant", "content": "The answer is 42."}}]
    }
    resp = _make_http_response(response_payload)

    with patch("urllib.request.urlopen", return_value=resp):
        result = chat_completion(
            endpoint="http://localhost:11434",
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "What is the answer?"}],
        )

    assert result == "The answer is 42."


def test_chat_completion_includes_system_message() -> None:
    """chat_completion correctly builds messages with system prompt."""
    captured_payload: list[dict] = []

    response_payload = {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
    resp = _make_http_response(response_payload)

    original_request = __import__("urllib.request", fromlist=["Request"]).Request

    def capture_request(url: str, data: bytes, **kw: object) -> object:
        captured_payload.append(json.loads(data.decode()))
        return original_request(url, data, **kw)

    with (
        patch("urllib.request.Request", side_effect=capture_request),
        patch("urllib.request.urlopen", return_value=resp),
    ):
        chat_completion(
            endpoint="http://localhost:11434",
            model="phi3:mini",
            messages=[
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Hi"},
            ],
        )

    assert len(captured_payload) == 1
    msgs = captured_payload[0]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"


def test_chat_completion_failure_propagates() -> None:
    """chat_completion raises when urllib raises."""
    import urllib.error

    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")),
        pytest.raises(urllib.error.URLError),
    ):
        chat_completion(
            endpoint="http://localhost:11434",
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "hello"}],
        )


# ---------------------------------------------------------------------------
# stream_chat_completion
# ---------------------------------------------------------------------------


def _make_sse_response(chunks: list[str], finish: bool = True) -> MagicMock:
    """Build a mock urllib response that yields SSE lines."""
    lines: list[bytes] = []
    for text in chunks:
        payload = json.dumps({"choices": [{"delta": {"content": text}, "finish_reason": None}]})
        lines.append(f"data: {payload}\n".encode())
    if finish:
        lines.append(b"data: [DONE]\n")
    mock_resp = MagicMock()
    mock_resp.__iter__ = MagicMock(return_value=iter(lines))
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_stream_yields_chunks_in_order() -> None:
    """stream_chat_completion yields each delta content chunk in arrival order."""
    resp = _make_sse_response(["Hello", ", ", "world", "!"])

    with patch("urllib.request.urlopen", return_value=resp):
        chunks = list(
            stream_chat_completion(
                endpoint="http://localhost:11434",
                model="gemma3:4b",
                messages=[{"role": "user", "content": "hi"}],
            )
        )

    assert chunks == ["Hello", ", ", "world", "!"]


def test_stream_stops_at_done() -> None:
    """stream_chat_completion stops cleanly when [DONE] sentinel is received."""
    resp = _make_sse_response(["token1", "token2"], finish=True)

    with patch("urllib.request.urlopen", return_value=resp):
        chunks = list(
            stream_chat_completion(
                "http://localhost:11434", "gemma3:4b", [{"role": "user", "content": "x"}]
            )
        )

    assert len(chunks) == 2


def test_stream_skips_non_data_lines() -> None:
    """stream_chat_completion ignores SSE comment/event lines (no 'data:' prefix)."""
    lines = [
        b": keep-alive\n",
        b"event: message\n",
        b'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":null}]}\n',
        b"data: [DONE]\n",
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__ = MagicMock(return_value=iter(lines))
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        chunks = list(
            stream_chat_completion(
                "http://localhost:11434", "gemma3:4b", [{"role": "user", "content": "x"}]
            )
        )

    assert chunks == ["hi"]


def test_stream_skips_malformed_json() -> None:
    """stream_chat_completion silently skips lines with invalid JSON."""
    lines = [
        b"data: not-json\n",
        b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}\n',
        b"data: [DONE]\n",
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__ = MagicMock(return_value=iter(lines))
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        chunks = list(
            stream_chat_completion(
                "http://localhost:11434", "gemma3:4b", [{"role": "user", "content": "x"}]
            )
        )

    assert chunks == ["ok"]


def test_stream_skips_empty_delta_content() -> None:
    """stream_chat_completion skips delta chunks with no 'content' key (role-only deltas)."""
    lines = [
        b'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}\n',
        b'data: {"choices":[{"delta":{"content":"text"},"finish_reason":null}]}\n',
        b"data: [DONE]\n",
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__ = MagicMock(return_value=iter(lines))
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        chunks = list(
            stream_chat_completion(
                "http://localhost:11434", "gemma3:4b", [{"role": "user", "content": "x"}]
            )
        )

    assert chunks == ["text"]


def test_stream_sends_stream_true_in_payload() -> None:
    """stream_chat_completion passes stream=true to the server."""
    captured: list[dict] = []
    resp = _make_sse_response(["ok"])

    original_request = __import__("urllib.request", fromlist=["Request"]).Request

    def capture(url: str, data: bytes, **kw: object) -> object:
        captured.append(json.loads(data.decode()))
        return original_request(url, data, **kw)

    with (
        patch("urllib.request.Request", side_effect=capture),
        patch("urllib.request.urlopen", return_value=resp),
    ):
        list(
            stream_chat_completion(
                "http://localhost:11434", "gemma3:4b", [{"role": "user", "content": "x"}]
            )
        )

    assert captured[0]["stream"] is True
    assert captured[0]["model"] == "gemma3:4b"


def test_stream_chat_completion_full_concatenates() -> None:
    """stream_chat_completion_full joins all chunks into a single string."""
    resp = _make_sse_response(["The ", "answer ", "is 42."])

    with patch("urllib.request.urlopen", return_value=resp):
        result = stream_chat_completion_full(
            "http://localhost:11434",
            "gemma3:4b",
            [{"role": "user", "content": "What is the answer?"}],
        )

    assert result == "The answer is 42."
