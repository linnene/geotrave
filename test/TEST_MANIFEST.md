# TEST_MANIFEST

## 1. Coverage_and_Dimension_Matrix

| Dimension | Directory | Priority | Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Unit** | `test/unit/` | P0-P1 | Active | Core logic units (LLMFactory, Utils, Schemas) |
| **Node** | `test/unit/nodes/` | P0 | Active | LangGraph nodes logic with isolated mock data |
| **Integration** | `test/integration/` | P0 | Not Started | Graph state transitions and cross-module workflow |
| **Evaluation** | `test/eval/` | P1-P2 | Active | Quality scoring and performance benchmarking |

## 2. Testing_Architecture_Design

### 2.1 Mocking_vs_Evaluation_Strategy
The framework distinguishes between **Mocking (Input Simulation)** and **Evaluation (Verification Standard)**:

- **Directory: `test/mock/` (The "Actors")**:
  - `llm_responses/`: Pre-recorded LLM outputs for deterministic testing.
  - `tool_outputs/`: Mocked tool results (API, RAG, Web) to isolate environment dependencies.
- **Directory: `test/eval/` (The "Judges")**:
  - Contains datasets (`dataset.json`, `analyzer_dataset.json`) that define the Ground Truth for model outputs.

## 3. Detailed_Test_Item_Inventory

### 2.1 Multi_Agent_Node_Logic (test/unit/nodes/)
- **test_router.py** (P0): 
  - *Data Source*: `test/eval/dataset.json`
  - *Mock*: `AsyncMock` for LLM chain pipe operator.
  - *Focus*: Intent classification & Safety fallback.
- **test_analyzer.py** (P0):
  - *Data Source*: `test/eval/analyzer_dataset.json`
  - *Focus*: Requirement extraction and `TravelState` persistence.
- **test_researcher.py** (P0):
  - *Data Source*: `test/mock/llm_responses/`, `test/mock/tool_outputs/`
  - *Focus*: Concurrent task scheduling and data aggregation logic.


## 3. Core_High_Risk_Items_Deep_Dive

### Item: Researcher_Batch_Filtering
- **Input**: Large-scale mock retrieval metadata (30+ items).
- **Assertion**: Batch processing completion within defined timeouts; correct filtering logic.
- **Impact**: Critical for system responsiveness. Failing results in long-tail latency/hangs.

### Item: Cross_Session_Isolation
- **Input**: Concurrent requests with identical user profiles but different `thread_id`.
- **Assertion**: `checkpoint` state strictly isolated.
- **Impact**: Security and user experience privacy.

