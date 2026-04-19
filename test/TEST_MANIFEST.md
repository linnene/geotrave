# GeoTrave Project Test Manifest (TEST_MANIFEST.md)

## 1. Coverage and Dimension Matrix

| Testing Dimension | Priority | Target / Module | Status | Core Tools |
| :--- | :--- | :--- | :--- | :--- |
| **Unit Testing** | P0/P1 | Prompt Logic, Schema, Utils | ✅ Active | pytest, Pydantic |
| **Integration Testing** | P1 | FastAPI, VectorDB, LLM Tools | 🛠 Refactoring | httpx, pytest-asyncio |
| **E2E Testing** | P0 | Full Agent Workflow | 🛠 Refactoring | LangGraph |
| **Non-functional** | P1 | Concurrency, Security Injection | ✅ Active | pytest, customized prompts |

## 2. Detailed Test Item Table

### A. Unit Tests (`test/unit/`)
| File | Test Item | Priority | Focus Area | Assertion Standard |
| :--- | :--- | :--- | :--- | :--- |
| `test_prompts.py` | Router Intent | P0 | Journey Routing & Security | Intent must match predefined categories (incl. injection check) |
| `test_prompts.py` | Analyzer Extraction | P1 | User Profile Management | Core tags (destination/days) extracted; trigger logic correct |
| `test_prompts.py` | Researcher Query | P1 | Retrieval Accuracy | Avoidance constraints must propagate to search queries |

### B. Integration Tests (`test/integration/`)
| File | Test Item | Priority | Focus Area | Assertion Standard |
| :--- | :--- | :--- | :--- | :--- |
| `test_api.py` | Chat Endpoint | P1 | API Communication | HTTP 200, Valid JSON Response Schema |
| `test_concurrency.py`| Concurrent Requests| P1 | System Stability | No race conditions; all requests complete within timeout |

### C. E2E Tests (`test/e2e/`)
| File | Test Item | Priority | Focus Area | Assertion Standard |
| :--- | :--- | :--- | :--- | :--- |
| `test_agent_workflow.py`| Full Path | P0 | Business Logic Closure | User Input -> ... -> Final Plan Generation |
| `test_quality_filter.py`| Content Safety | P1 | Output Quality | No hallucination or unsafe content in generated plans |

## 3. High-Risk Item Deep Dive

### 3.1 Router Security Injection (P0)
* **Input**: Prompt injection strings ("Ignore previous instructions..."), off-topic queries.
* **Failure Impact**: Model jailbreak, system resource misuse for non-travel tasks.
* **Evaluation**: `enum_intent` must be strictly `chit_chat_or_malicious`.

### 3.2 Full Workflow Success (P0)
* **Input**: Complete travel requirements (Destination, Duration, Preferences).
* **Output Assertion**: A valid `TravelPlan` object containing non-empty `itinerary` and `recommendations`.
* **Failure Impact**: Critical failure; agent is unusable.
