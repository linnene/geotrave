# STASH — 搁置工作清单

## 节点实现

### Recommender 节点
- **状态**: Stub — `manager_router` 中 `"recommender" → "reply"`
- **目标**: 基于调研结果生成结构化推荐列表（餐厅排序、景点评分、住宿匹配）
- **输入**: ResearchManifest.verified_results
- **输出**: 候选推荐列表

### Planner 节点
- **状态**: Stub — `manager_router` 中 `"planner" → "reply"`
- **目标**: 基于用户确认的候选生成完整行程计划（Markdown/PDF）
- **依赖**: Recommender 完成后

### Evaluator 评估系统
- **状态**: 未启动
- **目标**: 多维度评估（RAG 质量、状态转换正确性、约束合规性）
- **指标**: Context precision、faithfulness、constraint violation rate

## 工具实现

### Universal Web Content Crawler
- **状态**: 未启动
- **目标**: 动态抓取 + 可读性清洗 + 语义分块
- **技术栈**: Playwright / Crawl4AI + trafilatura / readability-lxml
- **说明**: web_search 已删除（LLM 偏好该工具而忽视空间工具），待 Crawler 完成后再重新注册

## 知识库

### ChromaDB 向量库迁移
- **状态**: 已移除依赖（`uv sync` 清理 35 个 chromadb 包），代码仍保留
- **决策**: PostGIS 替代空间检索，向量语义检索需求后续评估

## 架构优化

### Query 缩短策略
- **目标**: 优化 search query 关键词提取，减少 token 消耗
- **影响范围**: `src/utils/prompt.py` — query_generator 模板
