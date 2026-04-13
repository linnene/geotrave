# 归档

## 概述
本文档用于归档已完成的里程碑、架构决策和已定型的功能。

## 已完成的里程碑

### 2026-04-13: 解耦升级、路由控制与序列化修复 (State & Routing Overhaul)
- **状态树解耦 (State Decoupling)**：
    - 将庞大的 `TravelState` 全局白板拆解为嵌套的业务子域：`CoreRequirementState`、`SearchState` 和 `RecommenderState`。
    - **重大的架构决策**：彻底放弃在 LangGraph 状态图定义中直接使用带运行态特性的 `Pydantic.BaseModel` (如 `HardConstraints`, `RetrievalItem`)。全部改写为纯 `TypedDict`，并在 Analyzer 写入时调用 `.model_dump()` 转换为原生字典。这一改动一劳永逸地解决了 LangGraph 底层 `msgpack` 检查点序列化报错（“Deserializing unregistered type...”）的严峻问题。
- **动态意图路由节点 (Intelligent Gateway)**：
    - 引入并置于 `START` 后的 `RouterNode`。通过提取用户的 `RouterIntent` 分类（如 `travel_query`, `prompt_injection`, `other`），拦截注入攻击并对需求分流，极大降低了后续深空大模型（如 Analyzer）的无效 Token 消耗。
- **分析师自主唤醒决策 (Analyzer Autonomy)**：
    - 废弃了在路由器或者规则文件中手动 `diff` 新老状态键值对的硬编码逻辑。
    - 赋予 Analyzer (`TravelInfo` 解析器) 独立标志位 `needs_research`，让大模型自行结合人类语义分析“是否在这次更新中包含了值得触发研究员的新线索”。
- **记忆合并设计 (Context Merging Prompt)**：
    - 修复了多轮对话中 Analyzer “间歇性失忆”不保留初始设定（如天数遗失）的严重 Bug。
    - 在 `prompt.py` 分析师的提示词中挂载 `{current_state}` 全局变量快照。强迫 Analyzer 模型基于该老状态 JSON 进行缝补、修改。
- **流式图 UI (Streamlit UI Tracking)**：
    - 将 `test/test_ui.py` 升级，监听 `graph_app.astream(..., stream_mode="updates")`，以折叠状态实时渲染节点流转及内部推理标志。

### 2026-04-10: 协作规划架构深化 - 决策权边界与动态交互 [Completed]
- **决策权边界确立 (Architectural Decision)**：
    - **用户参与决定**：景点、美食、住宿、节奏。
    - **Agent 独立决定**：路线规划优化、时间分配、推荐项扩充（池生成）。
- **动态选择机制定型 (Logical Design)**：
    - 引入 \
eeds_selection\ 标志位。
    - 逻辑：核心需求（目的地/偏好）更新 -> 重新检索 -> 标记为 \True\ -> 强制进入 Recommender 节点展示新结果。
    - 若需求未变，则 Researcher 后可直接跳过 Recommender（基于状态流转）。

### 2026-04-09: 架构重构 - 从黑箱 RAG转向协作交互 [Completed]
- **研究员输出结构化**：\RetrievalItem\ 对象化改造完成，支持 Pydantic 解析。
- **系统简化**：清除 \main.py\ 冗余逻辑，强制 \DEBUG\ 日志，删除旧版失效 Filter 节点。

### 2026-04-07: 评估与测试子系统
- 实现了流程自动化测试框架，支持 \Analyzer -> Researcher\ 端到端流转。

### 早期里程碑
- 2026-04-06: 智能搜索集成，接入 DuckDuckGo。
- 早期基础: 核心状态机与 LangGraph 内存记忆机制。
