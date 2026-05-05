# GeoTrave 项目状态快照

**更新日期**: 2026-05-05
**分支**: dev (领先 origin/master 25+ commits)
**测试**: 188/188 全部通过

---

## 项目概要

GeoTrave 是基于 LangGraph 的多智能体旅行规划引擎。用户通过 FastAPI 聊天接口交互，系统逐步提取需求、执行空间/Web/文档多维研究、推荐旅行方案（任意维度），最终生成详细行程。

## 技术栈

| 层 | 技术 |
|---|------|
| Agent 框架 | LangGraph + LangChain |
| LLM | ChatOpenAI (DeepSeek 等兼容), LLMFactory 9 节点独立模型配置 |
| API | FastAPI + Pydantic v2 |
| 数据库 | PostgreSQL + PostGIS + pgRouting (空间), SQLite (Checkpointer), PostgreSQL JSONB (Retrieval) |
| 爬虫 | DuckDuckGo + crawl4ai + Playwright (浏览器池) |
| 测试 | pytest 188 例 (asyncio strict) + Newman/Postman |
| 包管理 | uv |

## Agent 图拓扑 (7 节点)

```
gateway → analyst → manager ─┬─ research_loop (子图) → manager
                              ├─ recommender → reply → END
                              ├─ planner → END
                              └─ reply → END
```

### 节点职责

| 节点 | 测试数 | 职责 |
|------|--------|------|
| gateway | 6 P0 | 安全过滤 + 意图分类 (legal/malicious/chitchat) + PII 脱敏 |
| analyst | 6 P0 | 提取 UserProfile，审计完备性，输出 missing_fields |
| manager | 6 P0 | LLM 路由调度，硬守卫 (core_complete/needs_reselect)，重置研究状态 |
| research_loop | 107 | 子图: QueryGenerator → Search → Critic ⇄ QueryGenerator → Hash |
| recommender | 5 | 单维度推荐（自由维度，由 Manager focus_dimension 驱动） |
| planner | 5 | 生成每日行程 (含活动、时间、预算) |
| reply | 4 | 3 场景: GUIDE (追问) / BLOCK (拦截) / RECOMMEND (推荐呈现+失败降级) |

### 搜索工具 (5 个)

- `spatial_search` — PostGIS POI 空间搜索 (含类别过滤)
- `route_search` — PostGIS pgRouting 最短路径 + 等时圈
- `document_search` — BM25 检索数据库文本搜索 (ingest/search)
- `web_search` — DuckDuckGo + crawl4ai/Playwright 网页爬取 (可配置并发/超时)
- `weather_search` — Open-Meteo 天气预报 (含 CJK→EN 地名映射)

## 提示词管理

`PromptManager` 管理 12 个 PromptTemplate:

| 属性 | 节点/场景 |
|------|-----------|
| gateway | 安全过滤 |
| analyst | 需求提取 |
| manager | 路由调度 |
| query_generator | 研究查询生成 |
| critic / critic_decision | 研究结果评估 |
| reply / reply_block / reply_recommend / reply_guide_fallback | 回复 (4 场景) |
| recommender | 推荐生成 |
| planner | 行程生成 |

## LLMFactory 节点配置

每个节点可独立配置 API Key / Base URL / Model ID:
`GATEWAY_MODEL_*`, `ANALYST_MODEL_*`, `MANAGER_MODEL_*`, `QG_MODEL_*`,
`CRITIC_MODEL_*`, `SEARCH_MODEL_*`, `RECOMMENDER_MODEL_*`, `PLANNER_MODEL_*`, `REPLY_MODEL_*`

均回退至 `GLOBAL_MODEL_*`。

## 最近改动 (2026-05-05)

| 提交 | 范围 |
|------|------|
| `fix: LLMFactory Manager/Reply 映射 + ANALYST env 命名` | 配置层 |
| `fix: 错误路径标志位 + needs_reselect 守卫 + UnboundLocalError` | 5 个节点 |
| `feat: search config + dimensions_covered + research_history dedup` | 研究子图 |
| `refactor: 死代码清理 + 资源泄漏修复 + 爬虫域名可配置` | 全项目 |
| `test: Gateway Analyst Manager Reply P0 测试 (22 new, 188 total)` | 测试层 |
| `调整 QG 温度 0.2→0.6 + 推荐维度去限制化 + Reply 场景判断修复` | QG/Recommender/Reply |
| `RecommendationItem.reason 可选化防 LLM 缺少字段时崩溃` | schema |

## 测试状况

- pytest: **188/188 全部通过** (P0 111 + P1 63 + P2 14)
- Newman: 2 个 Postman Collection — 6 场景/17 断言
- 测试 UI: Streamlit (`test/test_ui.py`)
- 测试覆盖: 全部 7 个节点 + 数据库层 + API schema + 集成测试

## 已知问题

无已知测试失败。以下为监控项：

| 项 | 说明 |
|----|------|
| Open-Meteo CJK 地理编码 | 76 个常用地名映射 + 多语言重试，覆盖率有限 |
| DDGS 限流 | 可能返回 202，已降级为空列表 |
| Recommender LLM 偶尔缺字段 | `reason` 已设默认值，容错不崩溃 |
| Crawler 耗时 | deep 模式单次 30s+，Semaphore(2)+60s 总超时保护 |

## 目录结构

```
src/
  agent/
    graph.py              # StateGraph 拓扑 + 条件边
    state/
      schema.py            # Pydantic 模型 (~450 行)
      state.py             # TravelState
    nodes/
      gateway/             # 安全入口
      analyst/             # 需求分析
      manager/             # 调度中心 (LLM + 硬守卫)
      reply/               # 用户回复 (4 模板)
      recommender/         # 推荐引擎 (自由维度)
      planner/             # 行程规划
      research/
        subgraph.py        # 研究子图
        query_generator/   # 查询生成
        search/            # 搜索执行 (5 工具 + 文档管理 + 天气)
        critic/            # 三层过滤评估 (黑名单/LLM/代码规则)
        hash/              # 哈希持久化 + doc_id 提升
      utils/               # 共享工具 (content/history/research_loader/time)
  api/                     # FastAPI 路由 + schema
  database/
    checkpointer/sqlite.py # LangGraph SQLite 检查点
    postgis/               # PostGIS 连接池 + 配置 + 空间查询
    retrieval_db.py        # 检索结果 JSONB 存储
  crawler/                 # crawl4ai 爬虫 (fetcher/parser/schema)
  utils/                   # 基础设施 (LLM/Logger/Prompt/Config)
script/                    # 运维脚本 (Newman/API 测试)
postman/                   # Postman 集合 + 环境
test/
  unit/                    # 单元测试 (按模块镜像 src 结构)
  integration/             # 集成测试 (PostGIS 空间工具)
docs/                      # 文档
```
