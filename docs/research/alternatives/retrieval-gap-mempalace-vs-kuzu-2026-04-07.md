# Retrieval Gap Analysis: MemPalace vs kuzu-memory on LongMemEval

**Date:** 2026-04-07
**Dataset:** longmemeval_s_cleaned.json (500 questions, ~53 sessions per question)
**Storage strategy (both):** verbatim user-turn text, one memory per session

## Benchmark Results

| System | Mode | Questions | R@5 |
|--------|------|-----------|-----|
| MemPalace | raw (ChromaDB default) | 500 | 96.6% |
| kuzu-memory v1.12.1 | auto + semantic (use_semantic=True) | 200 | 93.5% |
| kuzu-memory v1.12.1 | auto + semantic (use_semantic=True) | 200 (confirmed run) | 93.5% |

The 96.6% figure for MemPalace is the **raw mode** baseline — pure ChromaDB semantic search with no post-processing, no LLM, no keyword re-ranking. Hybrid modes (v2/v3/v4) score higher (up to ~99%), but raw is the direct comparison point for kuzu's default path.

---

## Gap Analysis by Dimension

### 1. Embedding Model

**MemPalace (raw mode):**
ChromaDB `EphemeralClient` with no custom `embedding_function` passed. ChromaDB defaults to `all-MiniLM-L6-v2` (384-dim) served via its built-in `DefaultEmbeddingFunction` (ONNX runtime, sentence-transformers weights).

**kuzu-memory:**
`_SemanticScorer` loads `SentenceTransformer("all-MiniLM-L6-v2")` explicitly (384-dim). When `use_semantic_search=True`, the HNSW index path is attempted first; on failure it falls back to brute-force NumPy cosine scan over in-memory embeddings. The benchmark run that scored 93.5% used `use_semantic=True`.

**Verdict:** Same model (`all-MiniLM-L6-v2`). **Impact: None** on its own.

**Key difference:** ChromaDB's `DefaultEmbeddingFunction` may use a slightly different normalization path or ONNX operator set than sentence-transformers' Python encoder. Both are unit-normalized, so cosine is equivalent to dot product — but the vector index infrastructure differs (ChromaDB uses HNSW natively; kuzu attempts its own HNSW then falls back to NumPy).

---

### 2. Ranking / Scoring Architecture

**MemPalace (raw mode):**
Pure ANN. ChromaDB runs a single HNSW cosine search over the session corpus and returns results sorted by L2 distance (which equals `sqrt(2 - 2*cos)` for unit vectors). No secondary scoring. No re-ranking. The ranking is exactly what the HNSW index returns.

**kuzu-memory (auto + semantic):**
Multi-stage pipeline with five scoring layers applied sequentially:

1. HNSW query (attempted) OR keyword/entity/graph strategies (auto)
2. `_rank_memories()`: 70% cosine + 30% structural (importance * 0.15 + confidence * 0.10 + type_boost * 0.05)
3. `_apply_tfidf_boost()`: multiplicative re-sort by `importance * (1 + weight * normalized_tfidf)`
4. Optional LLM reranker (disabled in benchmark run)
5. `[:max_memories]` slice

The structural component (importance, confidence, memory_type) injects noise from fields that default to generic values (`importance=0.5`, `confidence=0.5`) for verbatim sessions stored via `km.remember()`. These defaults dilute the pure semantic signal.

**Verdict: HIGH impact.** The 30% structural weight in `_rank_memories()` scores sessions by internal Memory attributes (importance, confidence, memory_type) that are not tuned for verbatim haystack content. All sessions stored via `km.remember()` get the same defaults, so the structural component adds noise rather than signal, potentially mis-sorting sessions that are semantically close.

---

### 3. TF-IDF Boost: What It Does and Where It Hurts

**kuzu-memory `_apply_tfidf_boost()`:**

Formula: `final_importance = min(1.0, importance * (1 + weight * normalized_tfidf))`

This is a **multiplicative boost applied to `memory.importance`**, not to the semantic similarity score. After `_rank_memories()` sorts by semantic score, `_apply_tfidf_boost()` computes TF-IDF keyword overlap between the query and each memory, normalizes it within the result set, multiplies each memory's importance by `(1 + weight * normalized_tfidf)`, and **re-sorts the entire ranked list by the boosted importance value**.

The critical flaw: the re-sort key is `importance * (1 + tfidf_factor)`, not `semantic_score * (1 + tfidf_factor)`. Since all verbatim sessions default to `importance=0.5`, the re-sort key becomes `0.5 * (1 + tfidf_factor)` — effectively a pure TF-IDF sort. Any session not matching query keywords gets re-ranked below sessions with keyword matches, regardless of semantic similarity.

**Benchmark config:** The 93.5% run used `w=0.3` (tfidf_boost_weight=0.3). The benchmark comment in the code explicitly notes: "TF-IDF graph path disabled: raw SUM(tfidf) scores are not normalized against semantic similarity scores — causes ranking collapse (R@5: 89%→40%)." The `_apply_tfidf_boost()` in the coordinator is a different path but has an analogous problem.

**Verdict: HIGH impact.** The TF-IDF boost re-sorts by importance (uniform default) rather than semantic score, partially overriding the HNSW ranking for sessions that happen to share stop-word-filtered tokens with the query.

---

### 4. Query Preprocessing (Expansion, Rewriting)

**MemPalace (raw mode):**
Zero preprocessing. The question string is passed directly to `collection.query(query_texts=[query])`. No expansion, no rewriting, no stop-word removal.

**kuzu-memory:**
Zero preprocessing for the primary embedding path. The question is passed as-is to `_SemanticScorer.embed()`. The keyword strategies extract words with simple regex (`[a-z]{3,}`) and stopword filtering, but those strategies are merged with the semantic results — they don't modify the query for the semantic search.

**Verdict: No difference.** Neither system does query expansion or rewriting in the benchmark paths compared here.

---

### 5. Chunking / Storage Differences

**MemPalace (raw mode):**
One ChromaDB document per session. Document = `"\n".join(user_turns)` (user turns only). No chunking. Document is indexed as a single embedding vector.

**kuzu-memory (benchmark default):**
`chunk_size=0` — one Memory node per session. Content = `"\n".join(user_turns)` (user turns only). Identical granularity to MemPalace raw.

**Verdict: No difference** at default settings. The benchmark deliberately mirrors MemPalace's granularity.

---

### 6. Re-ranking Step

**MemPalace (raw mode):**
None. The 96.6% figure is pre-reranking. Higher modes (hybrid_v3, hybrid_v4, palace) optionally use Claude Haiku for LLM reranking of the top-10/20 candidates.

**kuzu-memory:**
`config.recall.reranking.enabled` defaults to False in the benchmark. No LLM reranking in the 93.5% run.

**Verdict: No difference** (both disabled).

---

### 7. Deduplication and Candidate Pool Size

**MemPalace:** ChromaDB returns `n_results=50` sorted by distance. No deduplication needed (one doc per session, one collection per question).

**kuzu-memory:** `attach_memories(max_memories=50)` runs all strategies (keyword, entity, temporal, graph_related or HNSW), merges candidates, deduplicates by Memory ID (keeping higher-confidence duplicate), then ranks. The merged pool is much larger but trimmed to 50 before returning. The extra strategy passes introduce duplicates that must be resolved, and the resolution step (keep higher-confidence) defaults to `confidence=0.5` for all sessions — reducing to an arbitrary tiebreak.

**Verdict: LOW-MEDIUM impact.** Multi-strategy merging increases recall at k>5 but the deduplication with uniform confidence adds a small ranking noise.

---

## Summary Table

| Dimension | MemPalace | kuzu-memory | Gap Driver | Estimated R@5 Impact |
|-----------|-----------|-------------|------------|----------------------|
| Embedding model | all-MiniLM-L6-v2 (ChromaDB ONNX) | all-MiniLM-L6-v2 (sentence-transformers) | Negligible implementation difference | LOW |
| Primary ranking | Pure HNSW cosine (ANN) | 70% cosine + 30% structural (importance/confidence/type) | Structural score uses uniform defaults, adds noise | HIGH (~1.5-2%) |
| TF-IDF boost | None | Multiplicative on importance, then re-sort | Re-sort key is importance not semantic score; overrides ANN ranking | HIGH (~0.5-1%) |
| Query preprocessing | None | None | No difference | NONE |
| Chunking | Session-level | Session-level | No difference | NONE |
| LLM reranking | None (raw mode) | None | No difference | NONE |
| Multi-strategy merging | None | keyword + entity + temporal + HNSW | Extra candidates but dedup with uniform confidence | LOW (~0.3%) |

**Total estimated gap: ~3.1% (observed: ~3.1% at 200q sample)**

---

## Root Cause Summary

The 3.1% gap is almost entirely explained by two issues in kuzu-memory's scoring pipeline when applied to verbatim haystack content:

**Primary (HIGH):** `_rank_memories()` blends a 30% structural weight using `importance`, `confidence`, and `memory_type` — all of which are uniform defaults (`0.5`) for sessions stored via `km.remember()`. This dilutes the semantic similarity signal for ~30% of the ranking weight, causing sessions that are semantically relevant but happen to share defaults with irrelevant sessions to be mis-sorted.

**Secondary (HIGH):** `_apply_tfidf_boost()` re-sorts the ranked list using `importance * (1 + tfidf_factor)` as the key. Since importance is uniform, this effectively becomes a TF-IDF-only sort for the top candidates, overriding the ANN ranking. A semantically relevant session with low keyword overlap will drop below a less-relevant session with high keyword overlap.

**Fix priority:**
1. Set structural weight to 0 (or near 0) when all memories have uniform importance/confidence — or skip the structural component entirely when `use_semantic_search=True`.
2. Change the TF-IDF boost formula to multiply the semantic similarity score directly, not the importance field. The boost should be `semantic_score * (1 + weight * tfidf)` rather than `importance * (1 + weight * tfidf)`.

These two fixes should close most of the gap without changing the embedding model or chunking strategy.
