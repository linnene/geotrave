# Project_Roadmap_Spec

## 1. Async_Architecture_Migration

### 1.1 Core_Evolution
- **Status**: Completed
- **Scope**: Parallelized search infrastructure and non-blocking LLM orchestration.
- **Key Implementation**:
  - `Researcher` node transitioned to `await llm.ainvoke()`.
  - Concurrent search using `asyncio.as_completed` for low-latency streaming.
  - Offloaded blocking I/O (ChromaDB, DDGS) to `asyncio.to_thread`.

### 1.2 Data_Filtering_Optimization
- **Status**: Completed
- **Mechanism**: Batch-based LLM secondary filtering (15 items per batch).
- **Metric**: Reduced latency by 3x compared to sequential processing.

## 2. Feature_Backlog

### 2.1 Query_Shortening_Strategy
- **Objective**: Refactor `research_query_prompt_template` to emphasize keyword extraction.
- **Expected Outcome**: Reduced token consumption and improved recall from search engines.

### 2.2 Universal_Web_Content_Crawler_&_Parser
- **Objective**: Develop a robust, anti-ad secondary parser to extract clean content from URLs.
- **Key Features**:
  - **Dynamic Fetching**: Integration of `Crawl4AI` or `Playwright` to handle SPA/JavaScript-heavy travel sites.
  - **Readability Cleaning**: Use `trafilatura` or `readability-lxml` to strip boilerplate (ads, nav, sidebars) and extract primary article text.
  - **Semantic Chunking**: Split long content into coherent sections for RAG injection.
- **Priority**: High (Enables deeper research beyond search snippets).

### 2.3 Recommender_Module_Integration
- **Objective**: Transform raw retrieved contexts into structured candidates.
- **Components**: Restaurant selection, attraction ranking, and accommodation matching.

### 2.3 Planner_Module_Finalization
- **Objective**: Sequential scheduling based on user-validated candidates.
- **Format**: Structured Markdown and PDF itinerary generation.

## 3. Knowledge_Expansion

### 3.1 External_API_Integration
- **Targets**: Real-time traffic data, global flight availability, and localized public transport APIs.
- **Pattern**: Integration via unified `Researcher` tools orchestration.
# Project_Roadmap_Spec
