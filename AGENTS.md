# GeoTrave — Multi-Agent Travel Planning Engine

## Project Overview

GeoTrave 是一个基于 LangGraph 的多智能体旅行规划系统。用户通过自然语言对话渐进式表达需求，系统经过安全过滤、需求提取、空间检索、交互推荐，最终生成个性化行程方案。

## Architecture

### Graph Topology

```
START → gateway → analyst → manager → dimension_planner → [research_loop × N] → research_merge
              │          ↑                              ↓
              └── unsafe ──→ reply               ←── manager (loop)
                                        recommender → reply
                                        planner → reply
                                        reply → END
```

### Nodes

| Node | File | Role |
|------|------|------|
| Gateway | `src/agent/nodes/gateway/node.py` | Safety filter + PII sanitization + intent classification |
| Analyst | `src/agent/nodes/analyst/node.py` | UserProfile extraction + completeness audit |
| Manager | `src/agent/nodes/manager/node.py` | LLM-driven routing (4 hard guards: core_complete, research_coverage, rounds limit, focus_dimension) |
| DimensionPlanner | `src/agent/nodes/research/dimension_planner/node.py` | Decomposes research into parallel dimensions, supports Manager pre-set short-circuit |
| Research Loop | `src/agent/nodes/research/subgraph.py` | QG → Search → Critic ⇄ QG → Hash (max 2 iterations) |
| Research Merge | `src/agent/nodes/research/merge/node.py` | Aggregation point for parallel Send fan-out branches |
| Recommender | `src/agent/nodes/recommender/node.py` | Three-dimension recommendation (destination/accommodation/dining) |
| Planner | `src/agent/nodes/planner/node.py` | Day-by-day itinerary from research + recommendations |
| Reply | `src/agent/nodes/reply/node.py` | 4 scenarios: guide/block/recommend/fallback |

### Parallel Architecture

DimensionPlanner fans out research via `Send` (graph.py:101-116). Results merge via `Annotated` reducer `_merge_research_manifest` (state.py:23-45).

### State

`TravelState` TypedDict (state.py:48). Each field has exactly ONE writer node. See `src/agent/state/STATE_SPEC.md` for full permissions.

Key state fields:
- `messages: Annotated[List[BaseMessage], add_messages]` — conversation
- `user_profile: UserProfile` — extracted requirements (Analyst writes)
- `research_data: Annotated[ResearchManifest, reducer]` — research results (Research Loop writes)
- `planned_dimensions / focus_dimension / dimension_hints` — Send fan-out control
- `route_metadata: RouteMetadata` — routing signal (Manager writes)
- `execution_signs: ExecutionSigns` — cross-node boolean flags
- `trace_history: Annotated[List[TraceLog], add]` — audit trail

## Tech Stack

- **Agent**: LangGraph + LangChain (ChatOpenAI)
- **API**: FastAPI + uvicorn
- **Spatial DB**: PostGIS 3.5 + pgRouting 3.8 on PostgreSQL 17
- **Checkpoint**: SQLite (LangGraph persistence)
- **Web Search**: DuckDuckGo (ddgs) + crawl4ai/Playwright browser pool (8 instances)
- **Deploy**: Docker Compose + GitHub Actions CD

## Commands

```bash
uv sync                                    # Install dependencies
uv run python -m src.main                  # Start dev server (port 8000)
uv run pytest test/ -v --asyncio-mode=strict  # All tests (191 tests)
uv run streamlit run test/test_ui.py       # Debug UI
```

## Key Constraints

1. **Worktree for experiments**: Never modify dev directly for experimental changes — use git worktrees
2. **uv for Python**: All Python commands use `uv run`, never find venv manually
3. **Commit format**: No `@` symbol in commit messages
4. **Async**: All langgraph nodes are async, pytest uses `asyncio-mode=strict`
5. **State field ownership**: Each state field has exactly ONE writer node — never write from multiple nodes
6. **Annotated reducers**: `research_data` uses custom `_merge_research_manifest` reducer; `messages` and `trace_history` use add reducer

## Test Structure

- `test/unit/` — mirrors `src/` directory structure exactly
- `test/integration/` — requires PostGIS
- Tests use priority markers: `@pytest.mark.priority("P0"/"P1"/"P2")`
- 191 tests total: 112 P0, 65 P1, 14 P2

## Critical Files

| File | Purpose |
|------|---------|
| `src/agent/graph.py` | LangGraph topology, conditional edges, Send fan-out |
| `src/agent/state/state.py` | TravelState definition + reducer |
| `src/agent/nodes/manager/node.py` | LLM routing + hard guards |
| `src/utils/prompt.py` | All prompt templates |
| `src/utils/llm_factory.py` | Per-node LLM configuration |
| `src/utils/config.py` | Environment-driven configuration |
| `src/agent/nodes/research/search/web_search.py` | Browser pool + DDG search |
| `src/agent/nodes/research/search/tools.py` | All 5 search tool implementations |
| `src/agent/state/STATE_SPEC.md` | State field ownership and permissions |
| `test/TEST_MANIFEST.md` | Full test coverage matrix |
