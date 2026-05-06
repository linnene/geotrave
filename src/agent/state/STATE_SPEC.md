# GeoTrave Agent State Specification

> 本文档为 GeoTrave Agent 2.0 全局 State 与 Schema 的权威规格说明。
> 所有节点必须遵守此处定义的权限边界，任何对 State 结构的变更必须先更新本文档。

---

## 1. TravelState — 全局状态字段

### 1.1 字段总览

| # | 字段 | 类型 | 分类 | 写入者 | 读取者 |
|---|------|------|------|--------|--------|
| 1 | `messages` | `Annotated[List[BaseMessage], add_messages]` | 对话上下文 | API (HumanMessage), Gateway (sanitized), Reply (AIMessage) | 全部节点 |
| 2 | `user_profile` | `UserProfile` | 业务数据 | Analyst | Manager, QG, Recommender, Planner, Reply |
| 3 | `user_request` | `str` | 业务数据 | Analyst | Manager, QG, Recommender, Planner, Reply |
| 4 | `missing_fields` | `List[str]` | 业务数据 | Analyst | QG, Reply |
| 5 | `research_data` | `ResearchManifest` | 调研状态 | Manager (reset), QG, Search, Critic, Hash | Manager, Recommender, Planner, Reply (via research_loader) |
| 6 | `recommendation_data` | `Optional[Dict[str, Any]]` | 交付数据 | Recommender | Manager, Recommender, Planner, Reply |
| 7 | `plan_data` | `Optional[Dict[str, Any]]` | 交付数据 | Planner | API response only |
| 8 | `user_selections` | `Optional[Dict[str, Any]]` | 用户交互 | Manager | Manager, Planner |
| 9 | `route_metadata` | `RouteMetadata` | 控制面 | Manager | gateway_router, manager_router, Recommender, Reply |
| 10 | `execution_signs` | `ExecutionSigns` | 控制面 | Gateway, Analyst, Manager, Recommender, Planner, Hash | Manager, manager_router, Recommender, Reply |
| 11 | `trace_history` | `Annotated[List[TraceLog], add]` | 可观测性 | 全部节点 | Manager, Reply |
| 12 | `needs_exit` | `bool` | 控制面 | Gateway | Reply (_detect_scenario) |

### 1.2 字段详细说明

#### messages — 对话历史
- **类型**: `Annotated[List[BaseMessage], add_messages]`
- **Reducer**: LangGraph `add_messages` — 新消息自动追加，同 ID 消息自动替换
- **写入节点**:
  - `API (chat.py)`: 每次请求写入 `HumanMessage(content=request.message)`
  - `Gateway`: 当检测到 PII 时写入脱敏后的 `HumanMessage(content=sanitized_text)` 替代原始消息
  - `Reply`: 写入 `AIMessage(content=reply_text)` 作为最终回复
- **读取节点**: 全部 7 个节点 + Research Loop 内部 4 个节点
- **生命周期**: 贯穿整个会话，由 LangGraph Checkpointer (SQLite) 持久化

#### user_profile — 结构化用户画像
- **类型**: `UserProfile` (Pydantic)
- **写入者**: **Analyst** (独占写入)
- **读取者**: Manager, QueryGenerator, Recommender, Planner, Reply
- **内容**: 目的地、天数/日期、人数、预算 + 软偏好（住宿/餐饮/交通/节奏）+ Flex 溢出袋
- **关键方法**: `check_completeness() -> (is_core_complete, all_missing)`

#### user_request — 核心诉求摘要
- **类型**: `str`
- **写入者**: **Analyst** (独占写入)
- **读取者**: Manager, QueryGenerator, Recommender, Planner, Reply
- **内容**: 从多轮对话中提取的一句用户核心意图，如 "User wants 小众 spots in Dali in May"

#### missing_fields — 缺失字段列表
- **类型**: `List[str]`
- **写入者**: **Analyst** (独占写入)——来自 `UserProfile.check_completeness()` 的 `all_missing`
- **读取者**: QueryGenerator (注入 prompt 上下文), Reply (Guide 模式引导用户补全)
- **⚠️ 已知问题**: 与 `UserProfile.check_completeness()` 计算结果重复，建议移入 UserProfile 内部

#### research_data — 调研状态
- **类型**: `ResearchManifest` (Pydantic)
- **写入者**:
  - `Manager`: 路由到 research_loop 时 reset `loop_state` 为初始值
  - `QueryGenerator`: 写入 `loop_state.active_queries` + 追加 `research_history`
  - `Search`: 写入 `loop_state.query_results` + `loop_state.passed_doc_ids`
  - `Critic`: 写入 `loop_state.passed_results/all_passed_results/passed_queries/feedback/continue_loop/loop_iteration/loop_summary`
  - `Hash`: 写入 `research_hashes` + `matched_doc_ids`
- **读取者**: Manager (判断 research_matches_current), Recommender/Planner (via research_loader), Reply
- **⚠️ 已知问题**: `loop_state` (ResearchLoopInternal) 嵌套在全局可见模型中，父图节点理论上可访问
- **结构**:
  - `research_hashes`: `{query: [hash_key, ...]}` — 最小全局暴露，全量 payload 在 PG JSONB
  - `loop_state`: `ResearchLoopInternal` — 子图私有，外部严禁直接读写
  - `research_history`: `List[str]` — 有序 user_request 列表，用于 Manager 新鲜度检查
  - `matched_doc_ids`: `List[str]` — 文档检索匹配的 doc_id 列表

#### recommendation_data — 推荐数据
- **类型**: `Optional[Dict[str, Any]]`
- **写入者**: **Recommender** (独占写入，按维度累积: `{dimension: RecommenderOutput.model_dump()}`)
- **读取者**: Manager (摘要), Recommender (self-read 累积), Planner (约束), Reply (呈现)
- **⚠️ 已知问题**: 类型为裸 `Dict[str, Any]`，应改为 `Dict[str, RecommenderOutput]` 获得类型安全

#### plan_data — 行程计划
- **类型**: `Optional[Dict[str, Any]]`
- **写入者**: **Planner** (独占写入 —— `PlannerOutput.model_dump()`)
- **读取者**: API response only (`chat.py` 返回给前端)
- **⚠️ 已知问题**: 类型为裸 `Dict[str, Any]`，应直接存储 `PlannerOutput` 模型

#### user_selections — 用户选择
- **类型**: `Optional[Dict[str, Any]]`
- **写入者**: **Manager** (从 LLM 输出的 `UserSelections` 模型转为 dict 写入)
- **读取者**: Manager (hard guard: needs_reselect 检查), Planner (选择摘要)
- **⚠️ 已知问题**: Manager 写 dict, Planner 又重建 `UserSelections(**sel_data)` —— 类型不一致

#### route_metadata — 路由指令
- **类型**: `RouteMetadata`
- **写入者**: **Manager** (独占写入)
- **读取者**: `gateway_router` (N/A, 不读此字段), `manager_router` (读 `next_node`), Recommender (读 `focus_dimension`), Reply (读 `next_node` 判断场景)

#### execution_signs — 跨节点信号面
- **类型**: `ExecutionSigns`
- **写入者**: Gateway (`is_safe`), Analyst (`is_core_complete`), Manager (`is_selection_made`), Recommender (`recommended_dimensions`, `is_recommendation_complete`), Planner (`is_plan_complete`), Hash (`is_loop_exit`)
- **读取者**: Manager (全部字段), `manager_router` (N/A), Recommender (`recommended_dimensions`), Reply (`is_safe`, `recommended_dimensions`)
- **⚠️ 已知问题**:
  - `is_loop_exit` 是死字段 —— Hash 写入但无人消费
  - `is_selection_made` 与 `user_selections is not None` 语义重叠
  - `is_safe` 与 `needs_exit` 语义重叠
- **字段清单**:
  - `is_safe: bool` — Gateway 写入，默认 True
  - `is_core_complete: bool` — Analyst 写入，默认 False
  - `is_recommendation_complete: bool` — Recommender 写入，默认 False
  - `is_plan_complete: bool` — Planner 写入，默认 False
  - `is_selection_made: bool` — Manager 写入，默认 False
  - `recommended_dimensions: List[str]` — Recommender 写入，默认 []
  - `is_loop_exit: bool` — **⚠️ 死字段，计划删除**

#### trace_history — 审计轨迹
- **类型**: `Annotated[List[TraceLog], add]`
- **Reducer**: `operator.add` — 新 trace 自动追加到列表
- **写入者**: 全部 7 个主节点 + Research Loop 内部 4 个子节点
- **读取者**: Manager (格式化后注入 LLM context), Reply (Block 模式提取 Gateway 拦截类别)
- **内容**: 每条 `TraceLog` 含 node, status, detail, latency_ms, token_usage, timestamp

#### needs_exit — 全局终止信号
- **类型**: `bool`
- **写入者**: **Gateway** (独占写入——当 `is_valid=False` 时设为 True)
- **读取者**: Reply (`_detect_scenario()` —— 结合 `is_safe` 判断 Block 模式)
- **⚠️ 已知问题**: 语义与 `execution_signs.is_safe` 重叠，Gateway 返回 `needs_exit: True` 的同时也设 `is_safe: False`

---

## 2. Schema 模型分类

### 2.1 控制面 (Orchestration & Audit)

| 模型 | 用途 | 写入者 |
|------|------|--------|
| `RouteMetadata` | Manager 发出的路由指令 | Manager |
| `ExecutionSigns` | 跨节点布尔信号面 | Gateway, Analyst, Manager, Recommender, Planner, Hash |
| `TraceLog` | 单节点执行审计记录 | 全部节点 |

### 2.2 业务领域 (Domain)

| 模型 | 用途 | 写入者 |
|------|------|--------|
| `UserProfile` | 结构化用户画像 (含 `check_completeness()`) | Analyst |
| `SearchTask` | QueryGenerator 发出的工具调用指令 | QueryGenerator |
| `RetrievalMetadata` | 工具返回的原始信封 (仅供工具内部使用) | Search tools |

### 2.3 LLM 输出契约 (LLM Contracts)

| 模型 | 用途 | 消费节点 |
|------|------|---------|
| `GatewayOutput` | Gateway LLM 结构化输出 | Gateway → 自身解析后写入 State |
| `AnalystOutput` | Analyst LLM 结构化输出 | Analyst → 自身解析后写入 State |
| `ManagerOutput` | Manager LLM 结构化输出 | Manager → 提取 route_metadata + user_selections |
| `QueryGeneratorOutput` | QG LLM 结构化输出 | QG → 提取 tasks 写入 loop_state |

### 2.4 研究循环 (Research Loop)

| 模型 | 用途 | 可见性 |
|------|------|--------|
| `ResearchResult` | 统一信封，包裹工具结果送入 Critic | 子图内部 |
| `CriticResult` | Critic Layer 2a 产出的单条评估 | 子图内部 |
| `LoopSummary` | 单轮迭代聚合统计 | 子图内部 |
| `ResearchLoopInternal` | 子图私有状态（嵌套在 ResearchManifest 中） | **应仅子图可见** |
| `ResearchManifest` | 父图可见的调研状态视图 | 全局 (research_data) |

### 2.5 交付层 (Delivery)

| 模型 | 用途 | 写入者 |
|------|------|--------|
| `UserSelections` | 用户从推荐列表中的选择 | Manager (解析), Planner (遵守) |
| `RecommendationItem` | 单条推荐项 | Recommender |
| `RecommenderOutput` | Recommender 单维度输出 | Recommender |
| `Activity` | 单日行程中的活动项 | Planner |
| `DayPlan` | 单日行程 | Planner |
| `PlannerOutput` | Planner 完整输出 | Planner |

---

## 3. 节点权限矩阵

R=Read, W=Write, X=无权限

### 3.1 主图节点

| 字段 | Gateway | Analyst | Manager | Recommender | Planner | Reply |
|------|---------|---------|---------|-------------|---------|-------|
| `messages` | R/W | R | R | R | R | R/W |
| `user_profile` | X | R/W | R | R | R | R |
| `user_request` | X | W | R | R | R | R |
| `missing_fields` | X | W | X | X | X | R |
| `research_data` | X | X | R/W | R | R | R |
| `recommendation_data` | X | X | R | R/W | R | R |
| `plan_data` | X | X | X | X | W | X |
| `user_selections` | X | X | R/W | X | R | X |
| `route_metadata` | X | X | W | R | X | R |
| `execution_signs` | W | W | R/W | W | W | R |
| `trace_history` | W | W | W | W | W | W |
| `needs_exit` | W | X | X | X | X | R |

### 3.2 Research Loop 子图节点

| 字段 | QG | Search | Critic | Hash |
|------|-----|--------|--------|------|
| `messages` | R | X | X | R (session_id fallback) |
| `user_profile` | R | X | X | X |
| `user_request` | R | X | X | X |
| `missing_fields` | R | X | X | X |
| `research_data` | R/W | R/W | R/W | R/W |
| `recommendation_data` | X | X | X | X |
| `plan_data` | X | X | X | X |
| `user_selections` | X | X | X | X |
| `route_metadata` | X | X | X | X |
| `execution_signs` | X | X | X | W (`is_loop_exit`) |
| `trace_history` | W | W | W | W |
| `needs_exit` | X | X | X | X |

### 3.3 条件边 (Router)

| 路由函数 | 读取字段 | 写入 |
|---------|---------|------|
| `gateway_router` | `execution_signs.is_safe` | X |
| `manager_router` | `route_metadata.next_node` | X |
| `_critic_router` (subgraph) | `research_data.loop_state.continue_loop` | X |

### 3.4 API 层 (chat.py)

| 操作 | 字段 |
|------|------|
| 写入 (input) | `messages` (HumanMessage) |
| 读取 (output) | `messages[-1].content` → reply, `recommendation_data` → recommendation, `plan_data` → plan |

---

## 4. 已知问题清单

### 4.1 类型安全问题

| # | 问题 | 严重度 | 计划 |
|---|------|--------|------|
| T1 | `recommendation_data: Optional[Dict[str, Any]]` — 应改为 `Dict[str, RecommenderOutput]` | 高 | 立即修复 |
| T2 | `plan_data: Optional[Dict[str, Any]]` — 应直接存储 `PlannerOutput` | 中 | 立即修复 |
| T3 | `user_selections: Optional[Dict[str, Any]]` — 应改为 `Optional[UserSelections]` | 中 | 立即修复 |
| T4 | Manager 写 `user_selections` 时 `UserSelections` → dict → Planner 又 `UserSelections(**dict)` 来回转换 | 中 | 随 T3 修复 |

### 4.2 结构问题

| # | 问题 | 严重度 | 计划 |
|---|------|--------|------|
| S1 | `missing_fields` 在 TravelState 顶层，逻辑上应属于 UserProfile | 中 | 移入 UserProfile |
| S2 | `ResearchLoopInternal` 嵌套在全局可见的 `ResearchManifest` 中 | 高 | 子图隔离（延后） |
| S3 | Research Loop 子图用 `StateGraph(TravelState)` 编译，可访问全部全局状态 | 高 | 子图隔离（延后） |
| S4 | `needs_exit` 与 `execution_signs.is_safe` 语义重叠 | 低 | 保留两者，各有明确用途 |
| S5 | `schema.py` 514 行混入 5 类职责的模型 | 中 | 拆分为子模块 |

### 4.3 死代码

| # | 问题 | 严重度 | 计划 |
|---|------|--------|------|
| D1 | `ExecutionSigns.is_loop_exit` — Hash 写入但无消费者 | 低 | 删除 |

### 4.4 序列化风险

| # | 问题 | 严重度 | 计划 |
|---|------|--------|------|
| C1 | `graph.py` JsonPlusSerializer 注册列表需与 TravelState 实际类型保持同步 | 中 | 类型强化后更新 |
| C2 | 旧 checkpoint 中的 `Dict[str, Any]` 反序列化为新类型可能失败 | 低 | 类型强化后测试向后兼容 |

---

## 5. 设计原则 (重构目标)

1. **单一写入者**: 每个 State 字段有且仅有一个节点负责写入
2. **强类型化**: 消除所有 `Dict[str, Any]` 裸类型，使用具体 Pydantic 模型
3. **权限最小化**: Research Loop 子图不应访问无关的全局 State
4. **关注点分离**: 控制面、业务数据、交付数据、LLM 契约各有其位
5. **向后兼容**: API 响应格式不变，checkpoint 可恢复
