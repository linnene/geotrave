# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GeoTrave is a multi-agent travel planning engine built on LangGraph. Users interact via a chat API, and the system progressively extracts requirements, performs web/RAG research, recommends destinations/accommodations/dining, and generates detailed itineraries. The current branch (`feature/agent-2.0-refactor`) is restructuring the graph topology from a linear flow into a manager-orchestrated architecture.

## Essential Commands

```bash
# Install dependencies (Python >=3.12 required)
uv sync

# Activate virtual environment and run the FastAPI server
uv run python -m src.main

# Run all tests (strict asyncio mode enforced)
uv run pytest test/ -v --asyncio-mode=strict

# Run a single test file
uv run pytest test/unit/test_api_schemas.py -v --asyncio-mode=strict

# Run unit tests only
uv run pytest test/unit/ -v --asyncio-mode=strict

# Run the Streamlit test UI (separate terminal)
uv run streamlit run test/test_ui.py

# Batch evaluation (Windows PowerShell)
powershell -File script/run_eval.ps1
```

## Architecture

### Agent Graph Topology (Agent 2.0)

The LangGraph `StateGraph` in `src/agent/graph.py` is the core of the system. Nodes are LLM-driven and communicate through a shared `TravelState` TypedDict persisted via SQLite checkpointer.

**Flow:** `gateway` -> `manager` -> (`analyst` | `query_generator` -> `search` | `reply`) -> back to `manager`, with `reply` -> `END`

- **gateway** (`src/agent/nodes/gateway/`): Security filter + intent classifier. Classifies every user input as `legal`/`malicious`/`chitchat`. Performs PII sanitization. Rejects invalid inputs before they enter the agent loop.
- **manager** (`src/agent/nodes/manager/`): The LLM-driven orchestrator. Reads `execution_signs`, `trace_history`, and `hashes_count` from shared state, then issues routing decisions (`RouteMetadata.next_node`). Every node returns to manager for the next decision.
- **analyst** (`src/agent/nodes/analyst/`): Extracts structured travel requirements (`UserProfile`) from conversation. Merges with existing profile, audits completeness, and reports missing fields.
- **query_generator** (`src/agent/nodes/query_generator/`): Plans multi-dimensional research given the current `UserProfile` and `user_request`. Outputs a list of `SearchTask` objects bound to tools.
- **search** (`src/agent/nodes/search/`): Tool execution node (no LLM). Reads `ResearchManifest.active_queries`, dispatches each `SearchTask` to the registered tool handler, collects results.
- **reply** (`src/agent/nodes/reply/`): Generates natural-language follow-up questions when core info is missing.

### Shared State Design

`TravelState` (`src/agent/state/state.py`) is a TypedDict with these key fields:
- `messages`: Full conversation history (auto-merged via `add_messages` reducer)
- `user_profile`: `UserProfile` Pydantic model — structured constraints (destination, budget, days, preferences)
- `research_data`: `ResearchManifest` Pydantic model — active search tasks and verified result hashes
- `execution_signs`: `ExecutionSigns` Pydantic model — cross-node signal plane (`is_safe`, `is_core_complete`)
- `route_metadata`: `RouteMetadata` Pydantic model — routing instruction issued by manager (only manager writes this)
- `trace_history`: Audit trail (`TraceLog` entries, auto-reduced via `add`)
- `needs_exit`: Boolean termination flag

All Pydantic models are defined in `src/agent/state/schema.py`. The checkpointer serializer is explicitly configured with model paths in `graph.py` — when adding new Pydantic models to the state, you must register them there.

### Tool Registration

Tools in `src/agent/nodes/search/tools.py` use the `@register_tool` decorator. This automatically populates:
- `TOOL_METADATA` — used by `query_generator` to inject available tool documentation into its prompt
- `TOOL_DISPATCH` — used by `search` node to map tool names to async handler functions

Add new tools by writing an async function and decorating it. The function receives a `SearchTask` and must return `RetrievalMetadata`.

### LLM Configuration

`LLMFactory` (`src/utils/llm_factory.py`) provides per-node model instances via `ChatOpenAI`. Each node's model can be configured independently through `.env` variables (`GATEWAY_MODEL_ID`, `ANALYZER_MODEL_ID`, etc.), falling back to `GLOBAL_MODEL_*`. Nodes use `llm.bind(response_format={"type": "json_object"})` for structured output.

### API Layer

- `src/main.py`: FastAPI entry point with lifespan management (includes Windows ProactorEventLoop fix for Playwright)
- `src/api/chat.py`: Single `POST /chat/` endpoint that invokes the LangGraph with `thread_id`-based session persistence
- `src/api/rag.py`: CRUD endpoints for ChromaDB vector store (search, insert, upload)
- `src/api/schema.py`: Pydantic models for API request/response validation

### Database

- **PostGIS + pgRouting** (`database/postgis/`): Geospatial database engine for POI search, route computation, and OSM data. Docker-based deployment.
- **SQLite Checkpointer** (`src/database/checkpointer/sqlite.py`): LangGraph checkpoint persistence using `AsyncSqliteSaver`. Instances are loop-bound to prevent cross-loop lock errors. Path configured via `CHECKPOINT_DB_PATH` (default: `database/checkpointer/checkpoints.sqlite`).

### Key Patterns

- **Node structure**: Each node is an async function `(state: TravelState) -> Dict[str, Any]` that returns a partial state update dictionary.
- **Config per node**: Each node has a `config.py` with `TEMPERATURE`, `HISTORY_LIMIT`, `MAX_TOKENS` — tune these independently.
- **State serialization**: When adding Pydantic models referenced in `TravelState`, register their fully-qualified paths in `graph.py`'s `JsonPlusSerializer(allowed_msgpack_modules=...)`.
- **LLM output parsing**: Nodes use `response_format={"type": "json_object"}` + manual `json.loads()` + Pydantic constructor rather than `with_structured_output()`, for better cross-provider compatibility (DeepSeek, etc.).

### Current State of Development (feature/agent-2.0-refactor)

- Gateway, Analyst, Manager, QueryGenerator, Search, Reply nodes are implemented.
- Recommender and Planner nodes are stubbed (`manager_router` maps them to `"reply"`).
- Search tools (`spatial_search`, `route_search`) are PostGIS-backed and fully functional.
- Tests are minimal: API schema validation tests in `test/unit/` and an eval script stub.
