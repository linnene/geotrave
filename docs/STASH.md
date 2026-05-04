# GeoTrave 项目状态快照

**更新日期**: 2026-05-04
**分支**: dev (领先 origin/dev 5 commits)

---

## 项目概要

GeoTrave 是基于 LangGraph 的多智能体旅行规划引擎。用户通过 FastAPI 聊天接口交互，系统逐步提取需求、执行 Web/RAG 研究、推荐目的地/住宿/餐饮，最终生成详细行程。

## 技术栈

| 层 | 技术 |
|---|------|
| Agent 框架 | LangGraph + LangChain |
| LLM | ChatOpenAI (DeepSeek 等兼容), LLMFactory 多节点模型配置 |
| API | FastAPI + Pydantic |
| 数据库 | PostgreSQL + PostGIS + pgRouting (空间), SQLite (Checkpointer), PostgreSQL JSONB (Retrieval) |
| 爬虫 | crawl4ai + Playwright |
| 测试 | pytest (166 例) + Newman/Postman |
| 包管理 | uv |

## Agent 图拓扑

```
gateway → analyst → manager → research_loop → manager
                            → recommender → reply → END
                            → planner → END
                            → reply → END
```

### 节点职责

| 节点 | 状态 | 职责 |
|------|------|------|
| gateway | 完成 | 安全过滤 + 意图分类 (legal/malicious/chitchat) + PII 脱敏 |
| analyst | 完成 | 提取 UserProfile，审计完备性，输出 missing_fields |
| manager | 完成 | LLM 驱动的路由调度，读取执行信号决定下一跳 |
| research_loop | 完成 | 子图: QueryGenerator → Search → Critic ⇄ QueryGenerator → Hash |
| recommender | 完成 | 逐维度 (destination→accommodation→dining) 生成推荐 |
| planner | 完成 | 生成每日行程 (含活动、时间、预算) |
| reply | 完成 | 3 场景: GUIDE (追问) / BLOCK (拦截) / RECOMMEND (推荐呈现) |

### 搜索工具 (5 个)

- `spatial_search` — PostGIS POI 空间搜索
- `route_search` — PostGIS pgRouting 路径计算
- `document_search` — 检索数据库 JSONB 文本搜索
- `web_search` — crawl4ai/Playwright 网页爬取
- `weather_search` — Open-Meteo 天气预报 (含 CJK→EN 地名映射)

## 提示词管理

`PromptManager` 管理 11 个 PromptTemplate 属性:

| 属性 | 节点 |
|------|------|
| gateway | 安全过滤 |
| analyst | 需求提取 |
| manager | 路由调度 |
| query_generator | 研究查询生成 |
| critic / critic_decision | 研究结果评估 |
| reply / reply_block / reply_recommend | 回复 (3 场景) |
| recommender | 推荐生成 |
| planner | 行程生成 |

## 测试状况

- pytest: **164/166 通过** (2 个预先存在的 hash 节点测试失败，与 web_search 拆分存储逻辑相关)
- Newman: 2 个 Postman Collection — `GeoTrave-API-Tests.json` (6 场景/17 断言) + `GeoTrave-TEST.json` (多轮对话 + 安全 + PII)
- 测试 UI: Streamlit (`test/test_ui.py`)

## 已知问题

| 问题 | 位置 | 状态 |
|------|------|------|
| test_persist_results_split_web_search 失败 | test_hash.py | 已知，web_search 拆分逻辑未对齐 |
| test_persist_results_split_key_lookup_safety 失败 | test_hash.py | 同上 |
| Open-Meteo 地理编码对 CJK 地名覆盖率有限 | weather.py | 已缓解: 76 个常用地名映射 + 多语言重试 |

## 目录结构

```
src/agent/
  graph.py              # StateGraph 拓扑
  state/schema.py       # Pydantic 模型 (450+ 行)
  nodes/
    gateway/            # 安全入口
    analyst/            # 需求分析
    manager/            # 调度中心
    reply/              # 用户回复 (3 模板)
    recommender/        # 推荐引擎
    planner/            # 行程规划
    research/
      subgraph.py       # 研究子图
      query_generator/  # 查询生成
      search/           # 搜索执行 (tools.py 5 工具)
      critic/           # 结果评估
      hash/             # 哈希持久化
src/api/                # FastAPI 路由
src/database/           # 数据访问层
src/utils/              # 基础设施 (LLM/Looger/Prompt)
script/                 # 运维脚本 (Newman/PowerShell)
postman/                # Postman 集合 + 环境配置
test/                   # 单元测试 + 集成测试
docs/                   # 文档
```

## 近期路线图 (PLAN.md)

1. 代码质量加固 — 静态分析、类型注解完善
2. 用户体验修复 — Reply 多模板已完成，推荐呈现优化
3. 测试自动化 — Newman CI 已集成，覆盖率提升中
4. 前端对接准备 — API 响应结构已就绪 (recommendation/plan 字段)
