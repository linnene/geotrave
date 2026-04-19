# GeoTrave Project Roadmap: System Optimization and Expansion

This document outlines the strategic progression for the GeoTrave intelligent travel agent, focusing on asynchronous performance, structural integrity, and logic refinement.

## Phase 1: Core Architecture Refactoring [Completed]

### 1. Asynchronous Transition
*   **Asynchronous LLM Invocation**: Migrated all node execution logic (Router, Analyzer, Researcher) from synchronous `invoke()` to asynchronous `ainvoke()`.
*   **Concurrent Resource Acquisition**: Implemented `asyncio.as_completed` in the Researcher node to orchestrate parallel execution of local retrieval, web search, and weather API tasks.

### 2. State and Factory Standardization
*   **Centralized Model Management**: Consolidated dispersed Pydantic models into `src/agent/schema.py`.
*   **LLM Factory Implementation**: Introduced `src/agent/factory.py` for unified model instantiation with configurable parameters.
*   **Global State Initialization**: Refactored `src/agent/state.py` with explicit default initializers to prevent field mismatches during state transitions.

---

## Phase 2: Intelligence and Logic Refinement [In Progress]

### 1. Multi-Node Prompt Engineering
*   **Task**: Systematic optimization of prompt templates to enhance extraction precision and tool-calling triggers.
*   **Router Optimization**: Refine intent classification to accurately distinguish between preference updates and new destination requests.
*   **Analyzer Optimization**: Enhance entity extraction logic; ensure `needs_research` triggers correctly based on information completeness and explicit user requests for real-time data.
*   **Researcher Optimization**: Improve query generation to produce concise, high-relevance keywords for both local and web search, incorporating user avoidances.
*   **Recommender Optimization**: Define structured summary logic to distill raw search results into professional recommendation sets.

### 2. Automated Validation Cycle
*   **E2E Workflow Testing**: Maintain 100% pass rate for core scenarios (except temporarily skipped cases).
*   **Dataset Expansion**: Update `test/eval/dataset.json` with higher fidelity user inputs to validate complex logic branches.

---

## Phase 3: Targeted Feature Expansion [Scheduled]

### 1. Component Implementation: Recommender Node
*   Summarization of heterogeneous search results.
*   Generation of independent recommendation lists for Dining, Attractions, and Accommodations.
*   Output schema: [Name, Description, Justification, Professional Index].

### 2. Component Implementation: Planner Node
*   Spatio-temporal itinerary synthesis based on confirmed recommendations.
*   Integration of weather data into logic flow for activity timing.
*   Final output generation in professional Markdown format.

---

## Phase 4: System Governance and Reliability [Scheduled]

### 1. Advanced Error Handling
*   Implementation of circuit breakers for external API failures.
*   Conversational fallback mechanisms for LLM parsing exceptions.

### 2. Quality Assurance Expansion
*   Integration of `pytest-cov` for comprehensive coverage reporting.
*   Implementation of RAG quality metrics (Precision/Recall) for the Researcher node.