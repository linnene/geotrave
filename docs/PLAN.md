# Phase 6 — 代码质量加固与工程化

## 1. Git 提交计划

当前 `dev` 分支 ~27 个文件未提交，按逻辑拆分为 5 个 commit：

| # | 提交信息 | 文件范围 |
|---|---------|---------|
| 1 | `feat: Recommender/Planner 交付节点 + 用户选择交互流程` | `src/agent/nodes/recommender/`, `src/agent/nodes/planner/`, `src/agent/nodes/utils/research_loader.py`, `src/agent/state/schema.py` (RecommenderOutput, PlannerOutput, UserSelections), `src/agent/state/state.py`, `src/api/chat.py`, `src/agent/graph.py` |
| 2 | `fix: Retrieval DB JSONB 序列化 — asyncpg 直接传 dict 而非 json.dumps 字符串` | `src/database/retrieval_db.py`, `test/unit/database/postgis/test_retrieval_db.py` |
| 3 | `feat: 全节点北京时区感知 — Analyst/QG/Recommender/Planner/Reply 提示词注入当前时间` | `src/agent/nodes/utils/time_utils.py`, `src/agent/nodes/utils/__init__.py`, `src/agent/nodes/analyst/node.py`, `src/agent/nodes/research/query_generator/node.py`, `src/agent/nodes/recommender/node.py`, `src/agent/nodes/planner/node.py`, `src/agent/nodes/reply/node.py`, `src/utils/prompt.py` |
| 4 | `feat: Manager 用户选择提取 + Hash 研究内容存储 + Research 数据注入 Recommender/Planner` | `src/agent/nodes/manager/node.py`, `src/agent/nodes/research/hash/node.py`, `src/agent/nodes/utils/research_loader.py`, `src/utils/prompt.py` |
| 5 | `test: UserSelections 模型 + Recommender/Planner/Graph 路由 + Hash 修复 + CLAUDE.md 更新` | `test/unit/agent/nodes/recommender/`, `test/unit/agent/nodes/planner/`, `test/unit/agent/test_user_selections.py`, `test/unit/agent/nodes/research/test_hash.py`, `test/unit/agent/test_graph_routing.py`, `CLAUDE.md`, `docs/PLAN.md` |

---

## 2. 项目现状诊断

### Critical (必须立即修复)

**C1 — LLMFactory.get_model() 节点映射缺失**
- 文件: `src/utils/llm_factory.py:44-63`
- Recommender、Planner、Critic 调用 `get_model()` 时落入 else 分支，静默使用 GLOBAL_MODEL 配置。运营者无法为这些节点指定独立模型。
- 修复: 新增 `"Recommender"`, `"Planner"`, `"Critic"` 分支；`src/utils/config.py` 新增对应 env var。

**C2 — Env var 名称拼写不一致**
- 文件: `src/utils/config.py:26-28`
- Python 常量名 `ANALYST_MODEL_*`，但 `os.getenv("ANALYZER_MODEL_*")`。用户在 `.env` 中写 `ANALYST_MODEL_ID=xxx` 会被静默忽略。
- 修复: 统一 `os.getenv` key 为 `ANALYST_MODEL_*`，同步 `.env.example`。

**C3 — Recommender/Planner 异常时仍设 completion flag = True**
- 文件: `src/agent/nodes/recommender/node.py:59-66`, `src/agent/nodes/planner/node.py:110-115`
- LLM 调用失败时 `is_recommendation_complete` / `is_plan_complete` 被设为 True。Manager 看到 True 继续路由，使用空推荐/空行程输出。
- 修复: 错误路径不设置 completion flag；Manager prompt 新增"推荐/行程失败时重试或告知用户"规则。

**C4 — search/ 目录缺少 config.py**
- 文件: 新 `src/agent/nodes/research/search/config.py`
- 所有其他节点目录均有 config.py，唯独 search 没有。摘要长度等参数硬编码在 node.py 中。
- 修复: 新增 `config.py`，抽出 `CONTENT_SUMMARY_MAX_CHARS` 等常量。

### High (应尽快修复)

**H1 — Analyst 错误路径不更新 execution_signs**
- `analyst/node.py:88-98`: except 块只返回 trace，不设置 `is_core_complete=False`，state 残留旧值。

**H2 — needs_reselect 缺少代码层路由守卫**
- Manager LLM 提取 `needs_reselect=True` 后写入 state，但 `manager_router` 无硬守卫。若 LLM 决策不稳定，可能跳过重新推荐直接进入 Planner。
- 修复: `graph.py` 的 `manager_router` 新增 `needs_reselect → recommender` 硬守卫。

**H3 — LoopSummary.dimensions_covered 恒为空列表**
- `critic/node.py:353-379`: `aggregate_loop_summary()` 中 dimensions_covered 始终为 `[]`，Manager 失去维度覆盖信号。
- 修复: 建立 `SearchTask.dimension → ResearchResult → CriticResult.dimension → LoopSummary.dimensions_covered` 数据流。

**H4 — QueryGenerator 无条件追加 research_history**
- `query_generator/node.py:92-98`: 每轮 QG 都追加 current_request，多轮 Research Loop 造成重复条目。
- 修复: 追加前检查 `old_history[-1] != current_request`。

**H5 — 四个核心节点零测试覆盖**
- Gateway、Analyst、Manager、Reply 无任何单元测试。这些节点组成 Agent 对话骨架（~20KB 逻辑），安全入口和编排核心完全依赖手动测试。
- 每节点至少 4 个 P0 测试（正常路径 + LLM 降级 + 空状态 + 标志设置）。

### Medium (建议修复)

**M1 — Manager MAX_TOKENS=500 可能偏低**
- `manager/config.py`: Manager prompt 约 60 行中文 + 完整对话历史，500 token 输出限制可能截断 JSON 响应。

**M2 — SearchTask.dimension Literal 类型过于严格**
- `schema.py:130-132`: dimension 限制为 7 个值。如果 QG LLM 输出 "shopping" 或 "nightlife"，Pydantic 直接抛异常。
- 建议: 改为 `str` 或增加 fallback="general"。

**M3 — RetrievalMetadata.hash_key 描述误导**
- `schema.py:140`: 描述为 "Content-addressable key"，但工具 handler 使用时间戳或 UUID，并非内容寻址。
- 修复: 更新 Field description 反映实际用途。

**M4 — 部分 __init__.py 为空**
- `manager/`, `planner/`, `recommender/` 的 `__init__.py` 为 0 字节。其他节点均导出 node 函数。
- 修复: 添加 `from .node import X_node`。

### Low (可延后)

- prompt.py 中遗留的 TODO 注释块（line 67-71）
- CriticResult docstring 拼写 typos（"单条评估结过果" → "单条评估结果"）
- 中英文 docstring 混用，缺乏统一风格

---

## 3. Postman/Newman 自动化 API 测试方案

### 3.1 方案选择

使用 Newman（Postman CLI runner）自动化运行用户的 Postman 集合。
- **入口**: 通过 Python `subprocess` 封装 `npx newman`，与现有 uv/pep 723 工具链对齐
- **CI 集成**: GitHub Actions 新增 `api-test` job，先启动 API server 再运行 Newman

### 3.2 Postman 集合结构 (postman/GeoTrave-API-Tests.json)

```
Folder A: 单轮基础测试 (独立 session_id)
├─ 1. 正常咨询 → status=success, reply 非空
├─ 2. 恶意输入 → status=success, reply 含拒绝语
├─ 3. 闲聊 → status=success, reply 含友好回应
└─ 4. 空输入 → 不崩溃

Folder B: 多轮对话 (共享 session_id, 按顺序执行)
├─ 1. "我想去日本玩" → 提取 session_id 设集合变量
├─ 2. "预算 8000 元，4 天" (复用 session_id)
├─ 3. "我们两个人，喜欢美食" (复用 session_id)
├─ 4. "推荐一下吧" → 验证 recommendation 非空
└─ 5. "选第一个" → 验证 plan 非空

Folder C: 边界场景
├─ 1. 快速连续请求 (1 秒内 3 条)
└─ 2. 重新推荐 (验证不同的 recommendation)
```

### 3.3 环境变量 (postman/env/GeoTrave-Local.json)

```json
{
  "base_url": "http://localhost:8000",
  "api_path": "/chat/",
  "expected_status": "success"
}
```

### 3.4 Newman 运行命令

```bash
npx newman run postman/GeoTrave-API-Tests.json \
  --environment postman/env/GeoTrave-Local.json \
  --reporters cli,junit \
  --reporter-junit-export test/api-test-results.xml \
  --delay-request 500
```

或者通过 Python wrapper: `uv run python test/run_api_tests.py`

### 3.5 CI 集成

在 `.github/workflows/Agent-node-test.yml` 新增 job:
```yaml
api-test:
  needs: test
  steps:
    - ... checkout + uv install ...
    - name: Start API server
      run: uv run python -m src.main &
    - name: Health check
      run: for i in {1..20}; do curl -s http://localhost:8000/health && break; sleep 1; done
    - name: Run Newman
      run: npx newman run postman/GeoTrave-API-Tests.json \
        --env-var "base_url=http://localhost:8000" \
        --reporters cli,junit \
        --reporter-junit-export test/api-test-results.xml
```

### 3.6 注意事项

- API server 必须先启动：CI 中 background process + health-check loop
- 多轮对话顺序：Newman 默认按 folder 内顺序执行，`pm.collectionVariables` 跨请求共享 session_id
- 请求间隔 `--delay-request 500` 避免竞争
- Windows 本地开发需 Node.js 已安装

---

## 4. 实施顺序

```
Step 1 (P0 缺陷) ─── C1 (LLMFactory) + C2 (env var 命名)
Step 2 (P0 缺陷) ─── C3 (completion flags) + C4 (search config)
Step 3 (P0 守卫) ─── H1 (Analyst error path) + H2 (needs_reselect guard)
Step 4 (P1 数据流) ─ H3 (dimensions_covered) + H4 (research_history dedup)
Step 5 (P0 测试) ─── H5 (Gateway/Analyst/Manager/Reply 测试) + M1-M4 顺手修复
Step 6 (工具链) ─── Postman/Newman 集成 + CI job
```

**并行建议**:
- Steps 1-2 可并行（独立缺陷）
- Steps 3-4 可并行（不同模块）
- Step 5 在 Step 1-4 后（测试依赖修复完成）
- Step 6 可与 Step 5 并行

## 5. 验证

```bash
# 单元测试回归
uv run pytest test/ -v --asyncio-mode=strict
# 预期: ≥190 个测试全部通过

# API 集成测试
npx newman run postman/GeoTrave-API-Tests.json --env-var "base_url=http://localhost:8000"
# 预期: 全部请求通过
```
