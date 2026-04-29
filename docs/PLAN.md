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

## 5. 验证

- [x] 单元测试全绿（`test/unit/`）— 28 tests
- [x] 集成测试全绿（`test/integration/`）— 4 tests
- [ ] E2E 手动测试：完整对话 → QueryGenerator 生成 spatial_search + 地理编码成功
