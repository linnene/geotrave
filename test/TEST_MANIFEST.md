# TEST_MANIFEST

## 1. Coverage_and_Dimension_Matrix

| Dimension | Directory | Priority | Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Unit** | `test/unit/` | P0-P1 | Initializing | Core logic units (LLMFactory, Utils, Schemas) |
| **Node** | `test/unit/nodes/` | P0 | Initializing | LangGraph nodes logic with isolated mock data |
| **Integration** | `test/integration/` | P0 | Not Started | Graph state transitions and cross-module workflow |
| **Evaluation** | `test/eval/` | P1-P2 | Not Started | Quality scoring and performance benchmarking |

## 2. Detailed_Test_Item_Inventory

### 2.1 Infrastructure_Unit_Tests (test/unit/)
- **test_llm_factory.py**
  - `test_singleton_pattern` (P0): Verify instance reuse.
  - `test_model_configuration` (P1): Validate param injection for different model IDs.
- **test_api_schemas.py**
  - `test_chat_request_validation` (P1): Check Pydantic constraints.

### 2.2 Multi_Agent_Node_Logic (test/unit/nodes/)
- **test_router_node.py** (P0): Maps to `src.agent.router`
  - *Data Source*: `test/eval/data/router_scenarios.json`
  - *Focus*: Intent classification accuracy.
- **test_analyzer_node.py** (P0): Maps to `src.agent.nodes.analyzer`
  - *Data Source*: `test/eval/data/analyzer_scenarios.json`
  - *Focus*: Slot filling and profile persistence.

## 3. Core_High_Risk_Items_Deep_Dive

### Item: Researcher_Batch_Filtering
- **Input**: Large-scale mock retrieval metadata (30+ items).
- **Assertion**: Batch processing completion within defined timeouts; correct filtering logic.
- **Impact**: Critical for system responsiveness. Failing results in long-tail latency/hangs.

### Item: Cross_Session_Isolation
- **Input**: Concurrent requests with identical user profiles but different `thread_id`.
- **Assertion**: `checkpoint` state strictly isolated.
- **Impact**: Security and user experience privacy.

