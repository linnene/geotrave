# GeoTrave Project PLAN

构建一个**协作式**旅游规划 Agent，从黑箱检索转向人工干预（Human-in-the-loop），让用户参与到核心零件（景点、美食、住宿）的选择过程中，而 Agent 负责组装逻辑（路线、时间管理）。

## 决策权边界定义 (Architectural Decision)

### 1. 用户参与决策 (User Selection)
- **景点 (Attractions)**：用户决定去哪里。
- **美食 (Dining)**：用户决定吃什么。
- **住宿 (Accommodation)**：用户决定住哪个片区或具体酒店。
- **节奏 (Pace)**：用户决定每天的松紧程度。

### 2. Agent 独立决策 (Agent Autonomy)
- **路线规划 (Route Optimization)**：根据地理位置计算最优路径。
- **时间分配 (Time Management)**：估算每个景点的游玩时长与交通耗时。
- **备选扩充 (Candidate Expansion)**：当用户需求模糊时，Agent 负责检索并提供高质量的推荐列表（池）。

## 迭代路线图

### 第一阶段：结构化与交互重构 (当前阶段)
- [x] **状态结构重构 (State Decoupling)**：将全局巨大的 `TravelState` 解耦为 `SearchState`, `RecommenderState`, `CoreRequirementState`。使用原生 `TypedDict` 替代 Pydantic 的 `BaseModel` 以彻底解决 LangGraph Checkpointer (`MemorySaver`) 的 `msgpack` 序列化报错问题。
- [x] **交互式路由 (Router Node)**：
    - 新增独立意图网关节点，前置拦截恶意注入 (Prompt Injection) 和无关闲聊，提取 `RouterIntent`。
    - 根据识别到的 `latest_intent` 动态决定是否放行至 Analyzer。
- [x] **分析师动态唤起 (Analyzer Autonomy)**：
    - 废弃被动的字典 diff 快照对比，赋予 Analyzer 专属标志位 `needs_research`。
    - 改造 `prompt.py` 中 Analyzer 的提示词基底，支持传入 `{current_state}`，确保大模型拥有记忆继承能力，能根据当前基底进行增量更新。
- [x] **Streamlit 轨迹监视器优化**：在 UI 界面中通过 `st.status` 获取 `graph_app.astream` 的流式事件，实时展示节点流转路径与大模型给出的内部参数（如意图、置信度、是否检索）。
- [ ] **推荐系统搭建 (Recommender Node)**：
    - **职责**：整理 Researcher 产出的结构化数据，归类为景点/美食/住宿推荐给用户筛选。
- [ ] **Planner 节点实现**：基于用户最终确认的选中项生成详细行程安排。

### 第二阶段：检索质量与数据源优化
- [ ] **多源聚合检索**：集成 Google Search API 或 SearXNG。
- [ ] **特定领域工具链**：天气、交通、酒店实时数据插件。

### 第三阶段：工程化与评价体系
- [ ] **长效记忆持久化**：将 \Checkpoint\ 存储至 SQLite。
- [ ] **评估框架 (Eval)**：约束满足率、规划合理性验证。

---

## 任务列表 (逐步实施)

### 1. 协议与状态层 (Protocols & State)
- [ ] 在 \src/agent/state.py\ 定义新字段：\
ecommendations\, \selected_items\, \user_decision\, \
eeds_selection\。

### 2. 节点开发 (Nodes Development)
- [ ] **Recommender Node**: 逻辑：\
etrieval_results\ -> 筛选整理 -> 更新 \
ecommendations\ -> 等待用户。
- [ ] **Analyzer Node Update**: 
    - 逻辑 1：识别意图，更新白板。
    - 逻辑 2：若核心需求变更，标记 \
eeds_selection = True\。
- [ ] **Planner Node**: 逻辑：\selected_items\ + 自动路线优化 -> 结构化行程。

### 3. 图拓扑调整 (Graph Topology)
- [ ] 修改 \src/agent/graph.py\ 连线（待讨论）。
