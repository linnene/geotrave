# PLAN — 下一步开发计划

## 1. 清理未实现工具 Stub ✓

- [x] 删除 `flight_api` — 抛 `NotImplementedError`，干扰 LLM 工具选择
- [x] 删除 `hotel_api` — 同上
- [x] 删除 `web_search` mock — LLM 持续偏好 web_search 而忽视空间工具，已彻底移除
- [x] 新增 TOOL_METADATA 注册完整性测试 ×5 (P0×3, P1×2)

**文件**: `src/agent/nodes/search/tools.py`, `src/utils/prompt.py`, `src/agent/state/schema.py`, `test/unit/agent/nodes/search/test_tools.py`

## 2. 地理编码改为渐进截断 ✓

- [x] 删除 `_geocode` 中的硬编码后缀列表 `("駅", "站", "寺", ...)`
- [x] 改为渐进截断：精确匹配 → ILIKE 模糊 → 逐字去尾重试
- [x] 更新对应单元测试（`test_geocode_suffix_stripping` → `test_geocode_truncation`）

**文件**: `src/agent/nodes/search/tools.py`, `test/unit/agent/nodes/search/test_tools.py`

## 3. 图拓扑修正 + Manager 调研充分性判断

### 问题诊断

**问题一：Analyst 可以被跳过**

当前拓扑 `gateway(safe) → manager → analyst`。Manager 是 LLM 驱动的路由
节点，它决定下一跳。Prompt 说"必须先导向 analyst"但 Manager 可能不遵守，
导致新用户消息绕过需求提取直接进入调研或回复。

**问题二：Manager 误判调研已充分**

当前 Manager 看到 `is_core_complete=True` + `hashes_count > 0` 就认为调研
完成，直接路由到 recommender（当前 fallback 到 reply）。实际上：

- `hashes_count` 只是 verified_results 的条目数。`query_generator_node`
  每次运行时会把 `verified_results` 清空（`node.py:84-88`），所以这个值
  仅反映最近一轮 query_generator→search 的结果数，不代表多轮调研的总量
- Manager 忽略了 `trace_history`：近期没有经过 search 节点执行，却认为
  已有足够的调研结果
- 调研应该是增量的——可能需要多轮 query_generator→search 才能覆盖交通、
  住宿、景点、美食等多个维度

**问题三（设计原则）：不应该用代码覆盖 Manager 的路由决策**

`RouteMetadata` 的 `next_node` 和 `reason` 是 Manager（LLM）做出的决策。
如果在 `manager_router` 中强行覆盖，会导致 trace_history 记录的 reason
与实际走向不一致，下一轮 Manager 读到的决策链逻辑自相矛盾。

### 改进策略

#### 3.1 拓扑修正：Analyst 从条件边改为固定边

```
旧拓扑:
  gateway ──(safe)──→ manager ──(LLM决定)──→ analyst
                                      └───────→ query_generator / reply

新拓扑:
  gateway ──(safe)──→ analyst ──(固定边)──→ manager ──(LLM决定)──→ query_generator / reply
```

`gateway_router` 中 safe 的直接路由从 `"manager"` 改为 `"analyst"`。
Analyst 总是第一个接收新用户消息的业务节点。这是图拓扑级别的保证，
不需要任何护栏代码。

```python
# graph.py gateway_router — 改动前
return "manager"

# 改动后
return "analyst"
```

Manager 不再需要决定"是否去 analyst"——它只做 post-analyst 的路由决策。
Manager prompt 中对应的规则同步删除。

#### 3.2 Manager 调研充分性判断增强

不给 Manager 加代码护栏。改为在 prompt 中强化它对调研是否充分的判断能力。

**当前问题**：Manager 看到 hashes_count > 0 就下结论。看不到：
- 调研覆盖了几个维度（transportation / accommodation / dining / attraction）
- 最近一次 search 执行是在什么时候
- 之前的研究是不是为同一个 user_request 做的

**改进**：在 `manager_node.py` 中给 prompt 注入更细粒度的信号：

```
已完成的调研维度: [transportation, accommodation]  ← 从 verified_results 的 SearchTask.dimension 汇总
待覆盖的调研维度: [dining, attraction]               ← focus_areas 或 profile 推断
最近一轮调研是否为当前诉求: 是/否                      ← research_history[-1] vs user_request
```

这样 Manager 可以做更精确的判断："已经覆盖了交通和住宿，但美食和景点还没搜，
应该再跑一轮 query_generator"。

### 涉及文件

| 文件 | 改动 |
|---|---|
| `src/agent/graph.py` | `gateway_router`: safe 路径从 `"manager"` 改为 `"analyst"`；`gateway` 条件边增加 `"analyst"` 目标；`manager_router` 移除 `"analyst"` 的映射（Manager 不再路由到 analyst） |
| `src/agent/nodes/manager/node.py` | 向 prompt 注入调研维度覆盖情况、search 最近执行时间戳等信号 |
| `src/utils/prompt.py` | Manager prompt: 删除"必须首先导向 analyst"规则（已由拓扑保证）；将调研充分性判断规则具体化（检查维度覆盖而非仅 hashes_count） |

### 验收标准

1. **拓扑正确性**: 新用户 safe 消息 → gateway → analyst → manager（固定路径，不走 LLM 路由）
2. **Manager 路由范围**: Manager 只能路由到 `query_generator` / `reply`（以及未来的 `recommender` / `planner`），不再路由到 `analyst`
3. **调研充分性判断**: 模拟对话中 Manager 看到部分维度已覆盖但全部维度尚未完成时，能判断"需继续调研"而非直接跳到 recommender
4. **回归测试**: 所有现有 25 个单元测试保持全绿

## 4. QueryGenerator 空间上下文感知 ✓

- [x] 新增"空间上下文感知规则"：强制 destination 不为空时生成 spatial_search
- [x] category 自动映射表：美食→restaurant, 住宿→hotel, 景点→attraction, 交通→transport
- [x] Flex 地理位置偏好挖掘引导（如"靠海"→调整搜索范围）
- [x] 目的地驱动规则：center/origin/destination 优先使用 destination 中的地名，禁止凭空编造坐标
- [x] `missing_fields` 加入 input_variables 并嵌入模板（修复之前 node 传参但模板未声明的问题）
- [x] `history` 已通过 `format_recent_history()` 正确传入（node.py:38,48）

**文件**: `src/utils/prompt.py`, `src/agent/nodes/query_generator/node.py`

## 5. Research Loop 子图 (subgraph)

### 5.0 架构概览

Research Loop 是一个 LangGraph 子图，封装从"任务规划"到"结果评估持久化"的完整检索闭环。子图拥有独立的内部 State，对外仅暴露最小接口：

```
┌─ Research Loop Subgraph ─────────────────────────────────────────────────┐
│                                                                          │
│   ┌──────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
│   │QueryGenerator│───▶│  Search  │───▶│  Critic  │───▶│     Hash  │    │
│   │   (entry)    │    │(并行执行) │    │(三层过滤) │    │(持久化+出口) │    ││
│   └──────┬───────┘    └──────────┘    └────┬─────┘    └──────────────┘   ││
│          │                                 │                             ││
│          │    Feedback + passed_queries    │                             ││
│          └─────────────────────────────────┘  (continue_loop=True)       ││
│                                                                          ││
│   Internal State                                                         ││
│   ┌─────────────────────────────────────────────────────────────────┐    ││
│   │ tasks · query_results · passed_results · feedback · loop_iter · │    ││
│   │ passed_queries · loop_summary                                   │    ││
│   └─────────────────────────────────────────────────────────────────┘    ││
└────────────────────────────────────┬─────────────────────────────────────┘│
                                     │                                      │
                                     ▼                                      │
   Global State: { query → [hash_keys] }          Retrieval DB: { hash_key → result }
```

**设计原则**：
- 检索原始结果仅 Recommender / Planner 需要，不写入全局 State（避免序列化膨胀和无关节点可见性）
- 全局 State 仅暴露 `{query: [hash_key, ...]}` 映射，下游按需查询 Retrieval DB
- Critic 的多层过滤用代码层实现确定性规则，LLM 仅负责语义判断（tag + 评分）

### 5.1 节点职责与输入/输出

#### 5.1.1 QueryGenerator — 循环入口

**触发**: Manager 路由到 Research Loop 子图

**输入**:

| 字段 | 来源 | 说明 |
|---|---|---|
| `history` | Global State.messages | 最近 N 轮对话 |
| `user_profile` | Global State.user_profile | 结构化需求画像 |
| `user_request` | Global State.user_request | 当前核心诉求 |
| `feedback` | Subgraph State (Critic 输出) | 上一轮 Critic 的结构化改进建议，首轮为 None |
| `passed_queries` | Subgraph State (Critic 累积) | 已通过评分的 query 集合，用于去重 |
| `tools_doc` | TOOL_METADATA | 可用工具列表及参数描述 |

**输出**: `List[SearchTask]`，每个 Task 含 `tool_name` + `parameters` + `dimension` + `rationale`

**约束**:
- 多轮 Loop 时，必须跳过 `passed_queries` 中已有的 query
- 根据 `feedback` 中指明的维度缺口生成补充搜索
- 首轮搜索广度优先（覆盖多维度），后续轮次深度优先（聚焦 feedback 指出的不足）

**流转**: 无条件 → Search

---

#### 5.1.2 Search — 异步并行执行

**输入**: `List[SearchTask]`

**输出**: `Dict[str, Any]` — `{query: result}` KV 对，写入子图内部 `query_results`

**实现**:
- 使用 `asyncio.gather()` 并行调度 `TOOL_DISPATCH` 中的 handler（后续评估 LangGraph Send API）
- 单个 handler 返回后立即用 `ResearchResult` envelope 包裹
- 单个 Task 失败不阻塞其他 Task（错误 result 标记为 `{"error": str}` 交由 Critic 处理）
- 所有 Task 完成后统一流转

**流转**: 无条件 → Critic

---

#### 5.1.2.1 ResearchResult Envelope — 统一结果包装

不同工具的原始输出格式各异（`spatial_search` 返回 POI 列表、`web_search` 返回 `[{title, url}]`、爬虫返回长文本），Critic 和 Hash 不应感知每种工具的原始格式。Search 节点在每个 handler 返回后，使用统一 Schema 包裹：

```python
class ResearchResult(BaseModel):
    """所有工具返回结果的统一包装。下游节点通过该 envelope 消费结果。"""
    tool_name: Literal["spatial_search", "route_search", "web_search", "crawler", ...]
    query: str                                    # 原始 query 文本
    content_type: Literal["json", "text", "html", "url_list"]
    content: Any                                  # 原始结果全量（类型由 content_type 决定）
    content_summary: str                          # Short summary (≤500 chars) for Critic LLM scoring
    timestamp: str                                # ISO 8601
```

**设计要点**:
- `content`: 保留原始结果全部信息。下游节点按 `content_type` 分派解析
- `content_summary`: Critic LLM 评分的统一接口。无论原始结果多大（网页可上万字），LLM 只看摘要，避免 token 爆炸
- Hash 计算时的 result 参数取自 `json_dumps(content, sort_keys=True)`
- 摘要生成逻辑：JSON → 提取前 3 个字段的 key values；文本 → 截取前 500 chars；URL 列表 → 取前三项的 title+url

---

#### 5.1.3 Critic — 三层过滤 + 循环决策

这是 Research Loop 的核心质量控制节点。

**输入**: `query_results: Dict[str, Any]`

**输出**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `passed_results` | `List[CriticResult]` | 通过三层过滤的结果列表 |
| `continue_loop` | `bool` | 是否需要继续搜索 |
| `feedback` | `str \| None` | 若继续，给 QueryGenerator 的改进建议 |
| `loop_summary` | `dict` | 本轮统计摘要 |

**CriticResult Schema**:
```
{
  query: str
  result: Any
  safety_tag: "safe" | "unsafe"
  relevance_score: 0-100
  utility_score: 0-100
  rationale: str
}
```

**三层过滤管线**:

```
Layer 1 — 词汇黑名单 (纯代码, O(1))
  ├─ 词表来源: `src/agent/nodes/research/blacklist.yaml` (全语种覆盖)
  ├─ 匹配关键词：暴力、色情、非法、政治敏感、毒品、赌博等
  ├─ 命中 → 直接丢弃，记录过滤原因
  └─ 未命中 → 进入 Layer 2

Layer 2 — LLM 安全标签 + 双维评分 (单次 LLM 调用, 与 QueryGenerator 同模型)
  ├─ 每组 5 条 {query: ResearchResult} 打包发送，LLM 仅看 content_summary
  ├─ 对每条输出：safety_tag ("safe"|"unsafe") + relevance_score + utility_score + rationale
  ├─ Prompt 含：unsafe 判定边界 (暴力/色情/非法/仇恨/政治敏感)、评分 rubric 锚点、及格线告知
  └─ 返回完整 JSON 列表 → 进入 Layer 3

Layer 3 — 代码逻辑过滤 (规则透明)
  ├─ 筛掉: safety_tag == "unsafe"
  ├─ 筛掉: relevance_score < 60
  ├─ 筛掉: utility_score < 60
  └─ 通过结果 → 聚合统计
```

**评分 Rubric (注入 Critic Prompt)**:
| 维度 | 90+ | 70-89 | 60-69 | <60 |
|---|---|---|---|---|
| **相关性** | 精确回答 query，信息完全匹配 | 大部分相关，少量偏差 | 间接相关，需推断 | 无关或答非所问 |
| **有效性** | 含具体地址/价格/时间等可操作信息 | 含部分操作信息但不够完整 | 泛泛介绍，操作性弱 | 纯百科描述，无操作价值 |

**聚合算法**:
```
passed = [r for r in results if Layer3_passes(r)]
pass_count = len(passed)
avg_score = mean([(r.relevance_score + r.utility_score) / 2 for r in passed])
dimensions_covered = unique([task.dimension for task in tasks_of(passed)])
```

**循环决策** (混合判断 — 已确认):

```
条件 a (代码规则): pass_count < pass_count_min → 结果数量不足，触发继续 Loop
条件 b (LLM 判断): Critic 输出 continue_loop=True → LLM 认为需要补充搜索
条件 c (硬上限):  loop_iter >= MAX_LOOPS → 强制退出
```

**退出逻辑**:
```python
def should_continue_loop(
    pass_count: int,
    pass_count_min: int,
    llm_continue_loop: bool,
    loop_iter: int,
    max_loops: int,
) -> bool:
    """Return True to re-loop, False to exit subgraph."""
    if loop_iter >= max_loops:
        return False   # c: 硬上限强制退出

    a_insufficient = pass_count < pass_count_min   # True → 需要继续
    b_wants_more = llm_continue_loop               # True → 需要继续

    # 任一条件要求继续 → re-loop；两者都允许退出 → exit
    return a_insufficient or b_wants_more
```

| 场景 | a (结果够?) | b (LLM) | 行为 |
|---|---|---|---|
| 结果充足 + LLM 满意 | ✅ | `False` | **退出 Loop** |
| 结果充足 + LLM 认为需补搜 | ✅ | `True` | 继续 Loop |
| 结果不足 + LLM 满意 | ❌ | `False` | 继续 Loop |
| 结果不足 + LLM 认为需补搜 | ❌ | `True` | 继续 Loop |
| 任意 + 达到 MAX_LOOPS | — | — | **强制退出** |

默认阈值: `pass_count_min = 3`, `MAX_LOOPS = 3` (后续实测调参)

**流转**:
- `continue_loop == True` + 未达上限 → QueryGenerator (下一轮)
- `continue_loop == False` 或达到上限 → Hash

---

#### 5.1.4 Hash — 持久化 + 全局暴露出口

**触发**: Critic 判定 `continue_loop == False` 或达到 `MAX_LOOPS`

**输入**: `passed_results` (所有轮次累积的通过结果)

**哈希键生成**:
`SHA256(query + json_dumps(result, sort_keys=True)[:10])` — result 取前 10 字符避免大结果导致哈希计算瓶颈。注意：此截断可能导致不同 result 产生相同 hash（尤其是相同开头的大 JSON），实际使用中需评估碰撞率

**写入 Retrieval DB**:
```
Key: hash_key = SHA256(query + json_dumps(content, sort_keys=True)[:10])
Value (JSONB): {
    query, result (envelope), tool_name,
    safety_tag, relevance_score, utility_score, timestamp
}
```

**写入 Global State** (最小暴露):
```
research_hashes[query].append(hash_key)
```

**消费方式**: Recommender / Planner 读取 `research_hashes` → 按 hash_key 查询 Retrieval DB → 注入各自 prompt

**流转**: 无条件 → 退出子图，Manager 重新接管

### 5.2 子图 State Schema (内部)

```python
class ResearchLoopState(TypedDict, total=False):
    # === 从 Global State 注入的入口参数 ===
    user_profile: UserProfile        # 当前用户画像
    user_request: str                # 当前核心诉求
    history: str                     # 最近 N 轮对话

    # === QueryGenerator 输出 ===
    active_tasks: List[SearchTask]   # 本轮待执行任务

    # === Search 输出 ===
    query_results: Dict[str, Any]    # {query: result}

    # === Critic 输出 (累积) ===
    passed_results: List[CriticResult]        # 当前轮通过的结果
    all_passed_results: List[CriticResult]    # 所有轮次通过的累积
    passed_queries: Set[str]                  # 已通过 query 去重集合
    feedback: Optional[str]                   # 回传给 QueryGenerator
    continue_loop: bool
    loop_iteration: int
    loop_summary: dict                        # {pass_count, avg_score, dimensions_covered}
```

### 5.3 全局 State 增量

```python
# 在 TravelState 或 ResearchManifest 中新增:
research_hashes: Dict[str, List[str]]   # {query: [hash_key, ...]}
```

### 5.4 Retrieval Database 规格

| 属性 | 值 |
|---|---|
| **技术** | PostgreSQL JSONB — 复用现有 PostGIS 实例 |
| **Key** | `SHA256(query + json_dumps(content, sort_keys=True)[:10])` |
| **Value** | JSON: `{query, result, tool_name, safety_tag, relevance_score, utility_score, timestamp}` |
| **查询** | `SELECT * WHERE hash_key IN (...)` — 批量获取 |
| **生命周期** | Session 级 (对话结束后可清理) |

建表：
```sql
CREATE TABLE IF NOT EXISTS research_cache (
    hash_key TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_research_cache_session ON research_cache(session_id);
```

### 5.5 技术决策 (已确认)

| # | 决策点 | 确认方案 |
|---|---|---|
| 1 | **Retrieval DB 技术** | PostgreSQL JSONB — 复用现有 PostGIS 实例 |
| 2 | **哈希键源数据** | `SHA256(query + json_dumps(result)[:10])` — 取 result 前 10 字符避免大结果哈希瓶颈 |
| 3 | **循环退出判定** | 混合判断 (详见下方) |
| 4 | **退出阈值** | `pass_count_min = 3` / `MAX_LOOPS = 3` — 初始值，后续实测调参 |
| 5 | **子图实现方式** | LangGraph StateGraph 嵌套 (父图注册子图为节点) |
| 6 | **safety_tag 枚举** | 仅 2 值: `"safe"` \| `"unsafe"` |
| 7 | **黑名单词表位置** | YAML 配置文件 (`src/agent/nodes/research/blacklist.yaml`) |
| 8 | **黑名单词表内容** | 全语种覆盖 (中/日/英/韩等) |
| 9 | **Search 并行模型** | `asyncio.gather()` — 后续评估 LangGraph Send API |
| 10 | **Critic 模型选择** | 与 QueryGenerator 同模型 |

### 5.6 涉及文件

| 文件 | 改动 |
|---|---|
| `src/agent/nodes/research/` (新目录) | 子图定义 + 4 个节点 |
| `src/agent/nodes/research/subgraph.py` | Research Loop StateGraph 拓扑 |
| `src/agent/nodes/research/critic.py` | Critic 节点 — 三层过滤 + 循环决策 |
| `src/agent/nodes/research/hash.py` | Hash 节点 — 持久化 + 全局 State 写入 |
| `src/agent/nodes/query_generator/node.py` | 适配子图入口，新增 feedback/passed_queries 输入 |
| `src/agent/nodes/search/node.py` | 适配子图内部 State，移除全局 State 写入 |
| `src/agent/state/schema.py` | 新增 CriticResult, ResearchLoopState, 更新 ResearchManifest |
| `src/agent/graph.py` | Manager 路由到子图，注册子图到父图 |
| `src/database/retrieval_db.py` (新) | Retrieval DB 读写封装 |
| `src/utils/prompt.py` | Critic prompt 模板 |
| `test/unit/agent/nodes/research/` (新) | Critic 过滤测试、Hash 测试、子图流转测试 |

### 5.7 验证

- [ ] 单元测试：Critic 三层过滤各层独立测试 (黑名单命中/Discard、LLM 评分 mock、代码过滤)
- [ ] 单元测试：Hash 写入/查询 (mock DB)
- [ ] 单元测试：循环退出条件 (max_loops、pass_count=0 保底)
- [ ] 单元测试：passed_queries 去重逻辑
- [ ] 集成测试：完整子图流转 (mock LLM + 真实 PostGIS)
- [ ] 所有现有 32 测试无回归
