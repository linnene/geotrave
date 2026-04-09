# GeoTrave Project PLAN

## 核心愿景
构建一个**协作式**旅游规划 Agent，从“黑箱检索”转向“人工干预（Human-in-the-loop）”，让用户参与到景点、美食和住宿的选择过程中，最终生成高度定制化的行程。

## 迭代路线图

### 第一阶段：结构化与交互重构 (当前重点)
- [x] **研究员输出结构化**：将 Researcher 输出从纯文本改为 \`RetrievalItem\` 对象列表。
- [ ] **状态机扩展**：在 \`TravelState\` 中增加 \`recommendations\`（待选池）和 \`selected_items\`（确认池）。
- [ ] **推荐节点 (Recommender) 实现**：新增节点，负责从检索结果中提取精华供用户挑选。
- [ ] **交互式路由 (Router) 升级**：
    - 分析师需识别用户是在“提供需求”、“挑选结果”还是“要求生成计划”。
    - 实现从 Recommender 返回用户输入的等待机制（通过 Graph 中断实现）。
- [ ] **Planner 节点实现**：基于用户最终确认的 \`selected_items\` 生成详细行程。

### 第二阶段：检索质量与数据源优化
- [ ] **多源聚合检索**：集成 Google Search API 或 SearXNG 替代 DuckDuckGo。
- [ ] **特定领域工具链**：
    - 天气插件：实时查询目的地气温与降水。
    - 交通插件：查询机票/高铁价格趋势。
    - 酒店插件：获取实时住宿评价与价格。
- [ ] **本地 RAG 扩充**：编写爬虫获取主流旅游平台（小红书、携程）的深度攻略并向量化。

### 第三阶段：工程化与评价体系
- [ ] **长效记忆持久化**：将 \`Checkpoint\` 存储至 SQLite，支持跨 Web 服务重启恢复会话。
- [ ] **评估框架 (Eval)**：
    - 维度 1：RAG 召回精度（事实一致性）。
    - 维度 2：约束满足率（是否遵守了用户的硬性条件）。
    - 维度 3：规划合理性（地理位置闭环、时间分配）。
- [ ] **性能优化**：引入本地 Embedding 模型（如 \`BGE-small\`）降低 API 开销。

---

## 任务列表 (逐步实施)

### 1. 协议与状态层 (Protocols & State)
- [ ] 在 \`src/agent/state.py\` 定义 \`TravelState\` 新字段：\`recommendations\`, \`selected_items\`, \`user_decision\`。

### 2. 节点开发 (Nodes Development)
- [ ] **Recommender Node**: 逻辑：\`retrieval_results\` -> 筛选 Top N -> 更新 \`recommendations\`。
- [ ] **Analyzer Node Update**: 逻辑：判断 \`user_decision\` 状态，更新 \`selected_items\`。
- [ ] **Planner Node**: 逻辑：\`selected_items\` + \`constraints\` -> 固定格式行程。

### 3. 图拓扑调整 (Graph Topology)
- [ ] 修改 \`src/agent/graph.py\` 连线：
    - \`Analyzer\` -> \`Researcher\` (需要更多信息时)
    - \`Researcher\` -> \`Recommender\` (检索完成展示结果)
    - \`Recommender\` -> \`END\` (等待用户选择)
    - \`Analyzer\` -> \`Planner\` (用户确认后生成)

### 4. 提示词工程 (Prompt Engineering)
- [ ] 更新 \`src/utils/prompt.py\`：
    - 为 Analyzer 增加意图识别逻辑。
    - 为 Planner 增加基于结构化列表的生成逻辑。