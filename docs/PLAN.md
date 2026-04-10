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

### 第一阶段：结构化与交互重构 (当前重点)
- [x] **研究员输出结构化**：将 Researcher 输出从纯文本改为 \RetrievalItem\ 对象列表。
- [ ] **状态机扩展**：
    - 在 \TravelState\ 中增加 \
ecommendations\（备选池）和 \selected_items\（确认池）。
    - 增加 \
eeds_selection\ 标志位，由分析师根据用户需求变更和检索结果更新情况动态设置。
- [ ] **推荐与收集节点 (Recommender) 实现**：
    - **职责**：整理 Researcher 产出的原始数据，归类为景点/美食/住宿推荐给用户。
    - **逻辑**：只有当 \
eeds_selection=True\ 时才触发展示，并收集用户决策。
- [ ] **交互式路由 (Router) 升级**：
    - 分析师需识别用户是在提供需求、修改白板、挑选结果还是要求生成计划。
    - **关键逻辑**：若用户修改了目的地或关键约束，自动重置 \
eeds_selection\ 引导重新检索与挑选。
- [ ] **Planner 节点实现**：基于用户最终确认的 \selected_items\ 生成详细行程。

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
