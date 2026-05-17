# Phase 6 — 代码质量加固与工程化

**状态: ✅ 全部完成 (2026-05-05)**

---

## 完成摘要

| Step | 内容 | 状态 |
|------|------|------|
| 1a | LLMFactory Manager/Reply 模型映射 + ANALYST 环境变量命名修复 | ✅ |
| 1b | Recommender/Planner/Analyst 异常路径标志位修复 + Manager needs_reselect 硬守卫 + Gateway UnboundLocalError | ✅ |
| 1c | research/search/config.py 抽取爬虫常量 | ✅ |
| 2a | LoopSummary.dimensions_covered 数据流修复 | ✅ |
| 2b | QueryGenerator research_history 去重 | ✅ |
| 2c | 2 个失败 hash 测试修复 (web_search 拆分存储对齐) | ✅ |
| 3 | 死代码清理 (is_error, is_loop_exit, ChatResponse, SESSION_PREFIX) | ✅ |
| 4a | SQLite Checkpointer 过期实例清理 | ✅ |
| 4b | asyncio.ensure_future → create_task | ✅ |
| 4c | PostGIS 连接池事件循环变更时关闭旧池 | ✅ |
| 5 | Gateway/Analyst/Manager/Reply 核心节点测试 (22 new, 188 total) | ✅ |
| 6a | 爬虫阻塞域名列表环境变量 CRAWLER_BLOCKED_DOMAINS 可配置 | ✅ |
| 6b | 日志格式统一为 % 惰性求值 | ✅ |
| 6c | LLM 输出解析模式统一 (迁移至 JsonOutputParser) | ✅ |

### 额外修复 (超出原计划)

| 项目 | 说明 |
|------|------|
| QG 温度 0.2 → 0.6 | 提高搜索策略生成多样性 |
| 推荐维度去限制化 | destination/accommodation/dining Literal → 自由 str，LLM 按需选择任意维度 |
| Reply 场景判断修复 | `_detect_scenario` 增加 route_metadata.next_node 检查，避免误入推荐模式 |
| Recommender 失败降级 | 新增 reply_guide_fallback 模板，推荐失败时礼貌告知 |
| RecommendationItem.reason 可选化 | LLM 缺字段时不再崩溃，设默认值 |

---

## 测试

```bash
uv run pytest test/ -v --asyncio-mode=strict
# 188 passed, 0 failed
```

## 原审计记录 (已完成修复)

<details>
<summary>Critical / High / Medium / Low 缺陷清单 (点击展开)</summary>

### Critical (已全部修复)

- **C1** — LLMFactory.get_model() 节点映射缺失 → 新增 Manager/Reply 分支
- **C2** — Env var ANALYZER vs ANALYST 不一致 → 统一
- **C3** — Recommender/Planner 异常时仍设 completion flag → 修复
- **C4** — search/ 缺少 config.py → 新建

### High (已全部修复)

- **H1** — Analyst 错误路径不更新 execution_signs → 修复
- **H2** — needs_reselect 缺少代码层路由守卫 → Manager 硬守卫
- **H3** — LoopSummary.dimensions_covered 恒为空 → 数据流修复
- **H4** — QueryGenerator 无条件追加 research_history → 去重
- **H5** — 四个核心节点零测试覆盖 → 22 个新测试

### Medium (已全部修复)

- **M1** — Manager MAX_TOKENS 偏低 → 已调整
- **M2** — SearchTask.dimension Literal 过严 → 已放宽
- **M3** — RetrievalMetadata 描述修正
- **M4** — 空 __init__.py 补全导出

</details>
