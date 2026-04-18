# GeoTrave Project PLAN: True Async Refactoring & Quality Control

**当前最高优先级目标**：解决系统的性能瓶颈，清理冗余脏数据，实现完全异步无阻塞的检索与质检体验。

## 架构重构路线 (The Async Migration & Quality Control)

### 1. LLM 调用的全异步化 (Async LLM Invocation) [ Done]
- [x] **Researcher Node 改写**：将 ResearcherTools.generate_research_plan 中的同步 llm.invoke() 替换为异步 await llm.ainvoke()。
- [x] **Router Node 梳理**：确保意图识别、提取也都没有任何同步的 invoke 调用遗留。

### 2. 检索源并发与流式架构 (Concurrent Search Scattering & Streaming) [ Done]
- [x] **网络检索并发撒网**：通过 asyncio.as_completed 并发处理多条查询任务。
- [x] **流式数据推送 (Yielding)**：即便在搜集中，只要有任何一条网络查询完成，立刻 Yield 增量结果给前端 UI。

### 3. 同步 I/O 的后台线程脱离 (Threadpool Offloading) [ Done]
- [x] **脱离 RAG 查询阻塞**：将 ChromaDB 的同步 API 调用包裹在 asyncio.to_thread 中丢入后台线程池执行。
- [x] **脱离 DDGS 阻塞**：将 DuckDuckGo 的同步 API 挂载在线程池中执行。

### 4. 二级检索质检系统 (Secondary RAG Filtering & Stats) [ Done]
- [x] **LLM 结果清洗**：拉取回来的 Snippet 进行内容可用性初步 LLM 判断。
- [x] **宽容防误杀策略**：由于长 Query 在传统搜索引擎常因为长尾匹配度低而被模型视为不相关，修改判断为宽容条件（未明确说明不相关则放行），并在抛弃时输出具体 Reason 以便调试。
- [x] **内存脏数据彻底释放**：被丢弃结果不再存入内存或打标，而是直接释放抛弃，避免污染 Context Token。仅在状态栏中统计数字。

---

## 规划中的新点子 (New Ideas & Next Steps)

### 1. 探索长查询降级（Query Shortening Optimization）
- **Idea**: 目前由大模型提取用户所有要素拼接生成的 Search Query 有时过长（例如北海道小樽 2027年1月 6天5晚 家庭自驾...），导致传统搜索引擎（如 DDG）返回极短的无意义片段，进而导致高比例触发 LLM Secondary Filter 误杀。
- **Next Step**: 需要优化 research_query_prompt_template 或者针对 Web Search 专门增加一道短词化提取逻辑，让搜索引擎接收小樽 亲子 景点等传统短词。

### 2. 探索轻量化模型质检（Local OpenSource Filtering）
- **Idea**: 当前单向 Boolean Check 会带来较高的延迟和 Token 成本消耗，可以探索针对这项功能搭载专门微调的小参数开源模型专门用作分类器（YES/NO），从而提高并发速度，降低成本。

### 3. 规划系统开发 (Recommender & Planner)
- [ ] **Recommender Node**：接收清洗完毕的优质数据源，将其转换为清晰的旅游项目（交通、住宿、餐馆、景点）推送给用户确认。
- [ ] **Planner Node**：根据用户选择的素材项开始串联自动生成结构化、连贯的行程单。

### 4. 扩充检索维度 (Expand Retrieval Dimensions) [ Done]
- [x] **天气 API 集成**：接入 Open-Meteo 实现全球 7 天天气预报。
- [x] **状态解耦**：将天气信息从通用检索结果中剥离，在 TravelState 中开设独立 `weather_info` 频道。

---

## 架构升级与代码重构 (Architecture & Refactoring)

### 1. 代码组织结构重新设计 (Code Structure Re-organization)
- [ ] **解耦 Node 逻辑**：目前 `router.py`, `analyzer.py`, `researcher.py` 中混杂了大量初始化 LLM、定义 Pydantic Schema 的样板代码。
- [ ] **统一工厂化**：建立 `factory/llm.py` 统一管理所有节点的模型实例初始化，支持从 `config.py` 动态加载。
- [ ] **Schema 集中管理**：将零散在各 Node 文件中的 Pydantic Model 迁移至 `agent/schema.py` 或专门的 `types/` 目录，提高复用性。
- [ ] **Middlewares 引入**：探索在 LangGraph 节点间引入中间件机制，处理通用的状态检查、错误捕获和日志记录。

### 2. 健壮性与可维护性提升
- [ ] **类型标记强化**：全面引入 `typing`（如 `Protocol`, `Generic`）对 `TravelState` 进行更严格的约束。
- [ ] **测试架构升级**：
    - [x] 单元测试覆盖核心 Node & Tools。
    - [x] E2E 工作流自动化评估。
    - [ ] 引入 `pytest-cov` 监控测试覆盖率。

### 3. 长查询降级与性能优化 (Pending)
- [ ] **Query Shortening**：优化搜索引擎关键词提取逻辑，避免长句搜索导致的匹配失效。
- [ ] **缓存层设计**：引入 Redis 或本地缓存，对相同目的地与日期的天气、网页检索结果进行短时缓存。
