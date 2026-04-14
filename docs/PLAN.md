# GeoTrave Project PLAN: True Async Refactoring (真异步化改造)

**当前最高优先级目标**：彻底解决当前架构的伪异步阻塞问题。
当前的 Agent 节点中存在大量的同步阻塞操作（如 llm.invoke, 同步 DDGS, ChromaDB 等），这会导致在 FastAPI/多用户并发场景下，事件循环被死死卡住，造成单用户操作拖垮全局。
为此，必须将项目的底座改造为完全的非阻塞并发模型，以服务于多租户的后端生产环境。

## 核心改造路线 (The Async Migration)

### 1. LLM 调用的全面异步化 (Async LLM Invocation)
- [ ] **Researcher Node 改写**：将 ResearcherTools.generate_research_plan 中的同步 llm.invoke() 替换为异步的 wait llm.ainvoke()。
- [ ] **Router Node 检查**：确保意图识别的网关也没有任何同步的 invoke 调用残留。

### 2. 网络与检索 I/O 并发化 (Concurrent Search Scattering)
- [ ] **DuckDuckGo 异步化**：废弃同步的 DDGS，改用官方支持异步的 AsyncDDGS。
- [ ] **并发撒网 (Scatter & Gather)**：在拿到多个 Web Queries 或者混合本地查询时，摒弃 or 循环轮询的写法。利用 wait asyncio.gather(*tasks) 实现多任务齐发，按照最慢的那一根耗时结束战斗点，极大地缩短检索用时。

### 3. 遗留传统同步库的后台托管 (Threadpool Offloading)
- [ ] **本地 RAG 查询托管**：由于 ChromaDB 的核心 API 或本地检索是同步阻塞读写的，必须在其工具类中利用 syncio.to_thread(search_similar_documents, ...) 将计算和磁盘读取任务下放给 Python 后台线程池 (ThreadPoolExecutor)，以此确保 FastAPI 的主事件循环畅通无阻。

### 4. 数据隔离与持久化重构 (Multi-tenant Prep)
- [ ] **Checkpointer 换源**：在基础 Node 的异步化跑通后，抛弃 MemorySaver，对接真正适配云原生的持久化 Saver（如 AsyncSqliteSaver 或者更进阶的锁支持），为后续接入队列或请求排队机制铺平道路。

---

## 次要迭代路线 (后续开发)

### 推荐系统与规划生成 (Recommender & Planner)
- [ ] **Recommender Node**：整理异步 Researcher 产出的结构化数据，归类为游玩项目下放给用户确认。
- [ ] **Planner Node**：根据用户选定的内容进行路线排布和自动结构化。

