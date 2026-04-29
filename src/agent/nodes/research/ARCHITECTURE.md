# Research Loop — Architecture

## Overview

Research Loop is a LangGraph subgraph that encapsulates the complete retrieval
closed-loop from task planning to result evaluation and persistence. The
subgraph owns an internal state nested in `ResearchManifest.loop_state` and
exposes only the `{query: [hash_key, ...]}` mapping to the parent graph.

```
┌─ Research Loop Subgraph ──────────────────────────────────────────────────┐
│                                                                           │
│   ┌──────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
│   │QueryGenerator│───▶│  Search  │───▶│  Critic  │───▶│     Hash     │   │
│   │   (entry)    │    │          │    │(3-layer) │    │(persist+exit)│   │
│   └──────┬───────┘    └──────────┘    └────┬─────┘    └──────────────┘   │
│          │                                 │                              │
│          │    feedback + passed_queries     │                              │
│          └─────────────────────────────────┘  (continue_loop=True)        │
│                                                                           │
│   Internal State                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │ active_queries · query_results · passed_results · feedback ·     │   │
│   │ passed_queries · continue_loop · loop_iteration · loop_summary   │   │
│   └──────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    ▼
  Global State: { query → [hash_keys] }     Retrieval DB: { hash_key → payload }
```

## Design Principles

- Raw search results are NOT written to global state (avoids serialization
  bloat and unnecessary visibility to non-research nodes).
- Global state exposes only `{query: [hash_key, ...]}` mapping. Downstream
  nodes (Recommender, Planner) query the Retrieval DB on demand.
- Critic's multi-layer filter uses deterministic code rules where possible;
  LLM handles only semantic judgment (safety tag + dual-dimension scoring).

---

## Nodes

### QueryGenerator (entry)

**Input**:

| Field | Source | Description |
|---|---|---|
| `history` | `TravelState.messages` | Recent N conversation turns |
| `user_profile` | `TravelState.user_profile` | Structured requirement profile |
| `user_request` | `TravelState.user_request` | Current core intent |
| `feedback` | `loop_state.feedback` | Critic's improvement suggestion (None in first round) |
| `passed_queries` | `loop_state.passed_queries` | Already-passed queries for dedup |
| `tools_doc` | `TOOL_METADATA` | Available tool list and parameter specs |

**Output**: `List[SearchTask]` written to `loop_state.active_queries`

**Constraints**:
- Skip queries already in `passed_queries`
- Prioritize dimension gaps identified by `feedback`
- Round 1: breadth-first (multi-dimension); subsequent rounds: depth-first (focus on gaps)

**Routing**: unconditional → Search

---

### Search

**Input**: `loop_state.active_queries`

**Output**: `Dict[str, ResearchResult]` written to `loop_state.query_results`

**Execution model**: `asyncio.gather()` dispatches tasks to registered tool
handlers in parallel. Each result is wrapped in a `ResearchResult` envelope
before storage. Individual task failure does not block other tasks.

**Routing**: unconditional → Critic

#### ResearchResult Envelope

Normalises heterogeneous tool outputs (POI JSON, route data, etc.) for
downstream consumption by Critic and Hash:

| Field | Type | Description |
|---|---|---|
| `tool_name` | `str` | Producing tool |
| `query` | `str` | Original query text |
| `content_type` | `"json" \| "text" \| "html" \| "url_list"` | Content shape |
| `content` | `Any` | Full original result |
| `content_summary` | `str` | ≤500 char summary for Critic LLM scoring |
| `timestamp` | `str` | ISO 8601 creation time |

---

### Critic — 3-Layer Quality Filter

**Input**: `loop_state.query_results`

**Output**:

| Field | Type | Description |
|---|---|---|
| `passed_results` | `List[CriticResult]` | Results passing current iteration |
| `all_passed_results` | `List[CriticResult]` | Cumulative across all iterations |
| `passed_queries` | `List[str]` | Query texts that have passed (dedup) |
| `continue_loop` | `bool` | Whether the loop should keep iterating |
| `feedback` | `str \| None` | Guidance for next QG round |
| `loop_summary` | `LoopSummary` | Aggregated stats for this iteration |

#### Layer 1 — Blacklist Keyword Filter (code, O(1))

Checks `content_summary` against `blacklist.yaml` keywords (violence,
pornography, illegal, political sensitivity, drugs, gambling, etc. —
multi-language). Hit → discard immediately.

#### Layer 2 — LLM Scoring

Batches of ≤5 `{query: ResearchResult}` pairs sent to Critic LLM. LLM sees
only `content_summary`, not full content. Outputs per item:
- `safety_tag`: `"safe"` | `"unsafe"`
- `relevance_score`: 0–100
- `utility_score`: 0–100
- `rationale`: natural language

Scoring rubric:

| Score | Relevance | Utility |
|---|---|---|
| 90+ | Exact match to query | Contains addresses/prices/times |
| 70–89 | Mostly relevant, minor gaps | Partial actionable info |
| 60–69 | Indirectly related | Vague, low actionability |
| <60 | Irrelevant or off-topic | Encyclopedia-style, no use |

#### Layer 3 — Threshold Filter (code)

Discards if:
- `safety_tag == "unsafe"`
- `relevance_score < 60`
- `utility_score < 60`

#### Loop Exit Decision (3-Condition Hybrid)

```python
def should_continue_loop(pass_count, pass_count_min, llm_continue_loop, loop_iter, max_loops):
    if loop_iter >= max_loops:
        return False   # Condition C: hard cap, forced exit

    a_insufficient = pass_count < pass_count_min   # Condition A
    b_wants_more = llm_continue_loop               # Condition B

    return a_insufficient or b_wants_more   # One wants more → re-loop
```

| pass_count ≥ MIN | LLM says stop | loop_iter < MAX | Result |
|---|---|---|---|
| ✅ Yes | ✅ Stop | ✅ | **Exit Loop** |
| ✅ Yes | ❌ Continue | ✅ | Continue |
| ❌ No | ✅ Stop | ✅ | Continue |
| ❌ No | ❌ Continue | ✅ | Continue |
| Any | Any | ❌ (≥ MAX) | **Forced Exit** |

Defaults: `pass_count_min = 3`, `max_loops = 3` (tunable in `critic/config.py`).

**Routing**: `continue_loop` → QueryGenerator | `not continue_loop` → Hash

---

### Hash — Persist + Global Exposure

**Input**: `loop_state.all_passed_results` (cumulative across iterations)

**Hash key generation**: `SHA256(query + json_dumps(content, sort_keys=True)[:10])`

**Write to Retrieval DB**:
```
Key:   hash_key
Value: { query, result (envelope), tool_name, safety_tag,
         relevance_score, utility_score, timestamp }
```

**Write to Global State** (minimal exposure):
```
research_hashes[query].append(hash_key)
```

**Consumer pattern**: Recommender / Planner read `research_hashes`, query
Retrieval DB by hash_key, inject results into their prompts.

**Routing**: unconditional → END (parent graph Manager resumes)

---

## State Schema

### Subgraph-Internal (ResearchLoopInternal)

Nested in `ResearchManifest.loop_state`. Only Research Loop nodes may
read/write these fields:

| Field | Writer | Reader | Description |
|---|---|---|---|
| `active_queries` | QG | Search | Current iteration's SearchTask list |
| `query_results` | Search | Critic | `{query: ResearchResult}` for current iteration |
| `passed_results` | Critic | — | Current iteration's passing results |
| `all_passed_results` | Critic | Hash | Cumulative passing results |
| `passed_queries` | Critic | QG | Dedup set for next round |
| `feedback` | Critic | QG | Improvement guidance |
| `continue_loop` | Critic | subgraph router | Loop exit signal |
| `loop_iteration` | Critic | Critic | 0-indexed iteration counter |
| `loop_summary` | Critic | — | Current iteration stats |

### Global-State (ResearchManifest)

Parent-graph visible. Only Hash writes; Manager, Recommender, Planner read:

| Field | Type | Description |
|---|---|---|
| `research_hashes` | `Dict[str, List[str]]` | `{query: [hash_key, ...]}` mapping |
| `research_history` | `List[str]` | Ordered `user_request` history |
| `loop_state` | `ResearchLoopInternal` | Subgraph-private state (opaque to parent) |

---

## Subgraph Topology

```
Entry: query_generator

  query_generator ──▶ search ──▶ critic ──▶ hash ──▶ END
                         ▲          │
                         └──────────┘  (continue_loop=True)
```

- `query_generator → search`: unconditional
- `search → critic`: unconditional
- `critic → query_generator`: conditional (continue_loop=True)
- `critic → hash`: conditional (continue_loop=False or MAX_LOOPS reached)
- `hash → END`: unconditional (returns to parent graph)

---

## Config Per Node

Each node has its own `config.py` with independently tunable parameters:

| Node | Config File | Key Parameters |
|---|---|---|
| QueryGenerator | `query_generator/config.py` | `TEMPERATURE`, `HISTORY_LIMIT`, `MAX_TOKENS` |
| Search | `search/config.py` | (tool execution, no LLM params) |
| Critic | `critic/config.py` | `PASS_COUNT_MIN=3`, `MAX_LOOPS=3`, `CRITIC_TEMPERATURE=0.3`, `CRITIC_BATCH_SIZE=5`, `MIN_SCORE_THRESHOLD=60`, `MAX_TOKENS=3000` |
| Hash | `hash/config.py` | `SESSION_PREFIX` |

---

## Retrieval Database

| Attribute | Value |
|---|---|
| Technology | PostgreSQL JSONB (reuses existing PostGIS instance) |
| Key | `SHA256(query + json_dumps(content, sort_keys=True)[:10])` |
| Value | JSON: `{ query, result, tool_name, safety_tag, relevance_score, utility_score, timestamp }` |
| Query | `SELECT * WHERE hash_key IN (...)` |
| Lifecycle | Session-level (cleanable after dialogue ends) |

```sql
CREATE TABLE IF NOT EXISTS research_cache (
    hash_key TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_research_cache_session ON research_cache(session_id);
```

---

## Related Files

| File | Role |
|---|---|
| `subgraph.py` | StateGraph topology and compilation |
| `query_generator/node.py` | Entry node: multi-dimension research planning |
| `search/node.py` | Tool execution node (no LLM) |
| `search/tools.py` | Registered tool handlers (`spatial_search`, `route_search`) |
| `critic/node.py` | 3-layer quality filter + loop exit decision |
| `critic/blacklist.yaml` | Multi-language content safety keyword list |
| `hash/node.py` | Deterministic hash + Retrieval DB persistence |
| `../../state/schema.py` | Pydantic models: `ResearchLoopInternal`, `ResearchResult`, `CriticResult`, `LoopSummary`, `ResearchManifest` |
| `../../graph.py` | Parent graph: registers subgraph, Manager routes to `research_loop` |
| `../../../utils/prompt.py` | Critic prompt template |
| `../../../database/retrieval_db.py` | Retrieval DB read/write encapsulation |
