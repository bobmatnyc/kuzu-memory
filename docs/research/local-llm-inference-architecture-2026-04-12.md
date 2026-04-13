# Local LLM Inference Feature - Architecture Research

**Date**: 2026-04-12
**Purpose**: Understand kuzu-memory project structure to design local LLM inference detection and `/local-chat` endpoint.

---

## 1. MCP Server Entry Points

### Files
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/run_server.py` — stdio JSON-RPC 2.0 server loop
- `/Users/masa/Projects/kuzu-memory/src/kuzu_memory/mcp/server.py` — `KuzuMemoryMCPServer` class with tool handlers

### Startup Flow
1. `run_server.py::main()` reads `KUZU_MEMORY_PROJECT` env var (falls back to `Path.cwd()`)
2. Creates `KuzuMemoryMCPServer(project_root=...)`
3. Wraps in `MCPProtocolHandler` and calls `handler.run()` — blocks reading stdin in a `while self.running` loop
4. Tool dispatch: `tools/call` -> `_execute_tool(tool_name, args)` -> strips `kuzu_` prefix -> calls `self.server._<name>(**args)`

### Tool naming convention
The `run_server.py` dispatcher maps `kuzu_recall` → `server._recall()`, `kuzu_enhance` → `server._enhance()`, etc. (prefix `kuzu_` stripped, underscore prepended to look up method on `KuzuMemoryMCPServer`).

---

## 2. Config System

### File
`/Users/masa/Projects/kuzu-memory/src/kuzu_memory/core/config.py`

### Key dataclasses
| Dataclass | Notable fields |
|-----------|---------------|
| `KuzuMemoryConfig` | Top-level container; `storage`, `recall`, `memory`, `extraction`, `performance`, `retention`, `git_sync`, `prune`, `smart_prune`, `analytics`, `user` |
| `RecallConfig` | `default_strategy`, `strategies`, `strategy_weights`, `reranking: RerankingConfig`, `tfidf_boost_weight` |
| `RerankingConfig` | `enabled: bool = False`, `model: str = "claude-haiku-4-5"`, `top_k_to_rerank: int = 20`, `timeout_ms: int = 2000` |
| `StorageConfig` | `max_write_retries`, `write_retry_backoff_ms`, `connection_pool_size` |
| `UserConfig` | `mode: str = "project"` (`"project"` or `"user"`), `user_db_path`, `promotion_min_importance`, `promotion_knowledge_types` |
| `PerformanceConfig` | `max_recall_time_ms: float = 5000.0`, `max_generation_time_ms: float = 1000.0` |

### Loading
- `KuzuMemoryConfig.from_file(path)` — YAML via `yaml.safe_load`
- `KuzuMemoryConfig.from_dict(d)` — explicit key iteration (not `**kwargs`)
- `KuzuMemoryConfig.default()` — returns `cls()` with all dataclass defaults
- Environment overrides: `KUZU_MEMORY_RERANK=1`, `KUZU_MEMORY_MODE`, `KUZU_MEMORY_USER_DB_PATH`, `KUZU_MEMORY_TFIDF_BOOST_WEIGHT`, `KUZU_MEMORY_MAX_RECALL_TIME_MS`, `KUZU_MEMORY_PROMOTION_MIN_IMPORTANCE`

### Where to add local LLM config
Add a new `LocalLLMConfig` dataclass (alongside `RerankingConfig`) with fields like `enabled`, `endpoint`, `model`, `timeout_ms`. Wire it into `RecallConfig` and `KuzuMemoryConfig.to_dict()` / `from_dict()` following the same pattern used for `reranking`.

---

## 3. Recall Coordinator

### File
`/Users/masa/Projects/kuzu-memory/src/kuzu_memory/recall/coordinator.py`

### Class: `RecallCoordinator`
Constructor: `__init__(db_adapter: KuzuAdapter, config: KuzuMemoryConfig)`

### Primary entry point
```python
def attach_memories(
    self,
    prompt: str,
    max_memories: int = 10,
    strategy: str = "auto",
    user_id: str | None = None,
    session_id: str | None = None,
    agent_id: str = "default",
    apply_temporal_decay: bool = False,
    use_semantic_search: bool = False,
) -> MemoryContext
```

### Pipeline inside `attach_memories`
1. Validate input → `clean_prompt`
2. Classify speaker intent (`classify_speaker_intent`)
3. Cache check (`MemoryCache`)
4. Optionally call `_recall_with_hnsw` (HNSW vector index, MCP path only)
5. Run strategies (`_auto_recall` or `_single_strategy_recall`)
6. Merge HNSW + graph candidates
7. `_rank_memories` — Jaccard or cosine similarity scoring
8. `_apply_tfidf_boost` — optional TF-IDF multiplicative boost
9. Optional `LLMReranker.rerank()` (opt-in via `config.recall.reranking.enabled`)
10. Speaker-intent filtering
11. Slice to `max_memories`
12. Track access analytics
13. Build `MemoryContext` (enhanced prompt + memories)

### Strategies (in `recall/strategies.py`)
`KeywordRecallStrategy`, `EntityRecallStrategy`, `TemporalRecallStrategy`, `GraphRelatedRecallStrategy`

### Semantic scoring
`_SemanticScorer` — singleton wrapper around `sentence_transformers/all-MiniLM-L6-v2`, lazy-loaded.

### Existing LLM reranker integration point
`recall/reranker.py` — `LLMReranker` class. Instantiated lazily inside `attach_memories` when `config.recall.reranking.enabled`. Pattern to copy for a local LLM reranker.

---

## 4. CLI Entry Point

### File
`/Users/masa/Projects/kuzu-memory/src/kuzu_memory/cli/commands.py`

### Startup pattern
1. `_env_setup` module imported first (sets `TOKENIZERS_PARALLELISM` before heavy imports)
2. All subcommand groups imported from sibling files
3. `_silent_repair_mcp_configs()` runs on every CLI invocation to fix broken `~/.claude.json` args
4. Main Click group `kuzu_memory` created; subcommands registered

### Relevant sub-commands for local LLM feature
- `memory_commands.py` — `enhance`, `recall`, `recent`, `store`
- `mcp_server_command.py` — starts the MCP server via `kuzu-memory mcp`
- `setup_commands.py` — initial project setup

---

## 5. MCP Tools Currently Exposed

### In `run_server.py` (`_format_tools_for_mcp`)
| Tool | Required params |
|------|----------------|
| `kuzu_enhance` | `prompt` |
| `kuzu_learn` | `content` |
| `kuzu_recall` | `query` |
| `kuzu_remember` | `content` |
| `kuzu_stats` | — |
| `recent` | — |
| `cleanup` | — |
| `project` | — |
| `init` | — |

### In `server.py` (`_setup_handlers` via MCP SDK)
| Tool | Description |
|------|-------------|
| `kuzu_enhance` | RAG prompt augmentation |
| `kuzu_learn` | Async background learning |
| `kuzu_recall` | Semantic memory retrieval |
| `kuzu_remember` | Sync critical fact storage (has `knowledge_type`, `importance` fields) |
| `kuzu_stats` | Health check / diagnostics |
| `kuzu_optimize` | LLM-initiated memory optimization |
| `kuzu_merge` | Merge from another Kùzu DB |
| `kuzu_export_shared` | Export shared memories |
| `kuzu_import_shared` | Import shared memories |
| `kuzu_project_context` | Get recent project context (for session start) |
| `kuzu_user_context` | Get cross-project user context (user mode only) |

---

## 6. Existing Test Patterns (Unit / Recall)

### Directory
`/Users/masa/Projects/kuzu-memory/tests/unit/recall/`

### Test files
- `test_graph_related_strategy.py`
- `test_hnsw_recall.py`
- `test_keyword_graph_recall.py`
- `test_knowledge_type_access_count_ranking.py`
- `test_query_classifier.py`
- `test_reranker.py` — most relevant pattern for local LLM reranker tests
- `test_semantic_recall.py`
- `test_tfidf_boost.py`

`test_reranker.py` is the template for testing any LLM-backed reranking/inference component.

---

## Architectural Recommendations for Local LLM Feature

### Where to add config
1. Add `LocalLLMConfig` dataclass to `core/config.py` with `enabled: bool`, `endpoint: str`, `model: str`, `timeout_ms: int`, `detect_env_var: str = "OLLAMA_HOST"`.
2. Add `local_llm: LocalLLMConfig` field to `KuzuMemoryConfig`.
3. Add env var override `KUZU_MEMORY_LOCAL_LLM_ENDPOINT` in `from_dict`.

### Where to add detection
Create `src/kuzu_memory/integrations/local_llm.py` (or `src/kuzu_memory/services/local_llm_service.py`) with:
- `detect_local_llm()` — checks `OLLAMA_HOST`, `LM_STUDIO_URL`, etc.
- `LocalLLMClient` — thin async HTTP client wrapping the OpenAI-compatible endpoint

### Where to add `/local-chat` routing
Option A (MCP tool): Add `kuzu_local_chat` tool in `run_server.py::_format_tools_for_mcp` and implement `server._local_chat()` in `server.py`. Dispatch path is identical to other tools.

Option B (recall pipeline): Add a `LocalLLMReranker` in `recall/reranker.py` alongside the existing `LLMReranker`. Enable via `config.recall.local_llm.enabled`. The existing reranker hook in `attach_memories` (step 9 above) is the clean insertion point.

### Recommended approach
- Use Option B for memory-routing (reranker slot, minimal code change).
- Use Option A as a standalone chat tool for direct local LLM interaction.
- Follow `RerankingConfig` + `LLMReranker` pattern exactly.

---

## Key Files Summary

| Purpose | Path |
|---------|------|
| MCP stdio server loop | `src/kuzu_memory/mcp/run_server.py` |
| MCP tool implementations | `src/kuzu_memory/mcp/server.py` |
| Config dataclasses | `src/kuzu_memory/core/config.py` |
| Recall pipeline | `src/kuzu_memory/recall/coordinator.py` |
| Existing LLM reranker | `src/kuzu_memory/recall/reranker.py` |
| Recall strategies | `src/kuzu_memory/recall/strategies.py` |
| CLI entry point | `src/kuzu_memory/cli/commands.py` |
| MCP server CLI command | `src/kuzu_memory/cli/mcp_server_command.py` |
| Recall test patterns | `tests/unit/recall/test_reranker.py` |
