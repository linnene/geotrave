# TEST_MANIFEST — GeoTrave Test Coverage Matrix

## Coverage Dimension Matrix

| Module | Test File | P0 | P1 | P2 | Total |
|---|---|---|---|---|---|
| `src/api/schema.py` | `test/unit/test_api_schemas.py` | 0 | 1 | 0 | 1 |
| `src/database/postgis/config.py` | `test/unit/database/postgis/test_config.py` | 1 | 1 | 0 | 2 |
| `src/database/postgis/connection.py` | `test/unit/database/postgis/test_connection.py` | 2 | 2 | 1 | 5 |
| `src/database/retrieval_db.py` | `test/unit/database/postgis/test_retrieval_db.py` | 3 | 3 | 2 | 8 |
| `src/agent/nodes/search/tools.py` | `test/unit/agent/nodes/search/test_tools.py` | 5 | 9 | 2 | 16 |
| `src/agent/nodes/search/node.py` | `test/unit/agent/nodes/search/test_search_node.py` | 10 | 6 | 0 | 16 |
| `src/agent/nodes/search/docs/` | `test/unit/agent/nodes/search/test_docs.py` | 16 | 1 | 0 | 17 |
| `src/agent/nodes/query_generator/node.py` | `test/unit/agent/nodes/query_generator/test_query_generator.py` | 6 | 3 | 0 | 9 |
| `src/agent/nodes/research/critic.py` | `test/unit/agent/nodes/research/test_critic.py` | 9 | 7 | 2 | 18 |
| `src/agent/nodes/research/hash.py` | `test/unit/agent/nodes/research/test_hash.py` | 7 | 4 | 1 | 12 |
| `src/agent/graph.py` | `test/unit/agent/test_graph_routing.py` | 4 | 0 | 0 | 4 |
| `src/agent/nodes/search/tools.py` | `test/integration/test_spatial_tools.py` | 4 | 0 | 0 | 4 |
| **Total** | | **67** | **37** | **8** | **112** |

## P0 — Blocker Items

| # | Test | Risk |
|---|---|---|
| 1 | `test_default_dsn` — 默认 DSN 回退值 | 数据库连接失败将导致整个空间检索链路中断 |
| 2 | `test_get_pool_creates_new_pool` — 连接池初始化 | 无连接池则所有 spatial/route 工具不可用 |
| 3 | `test_get_pool_recreates_on_loop_mismatch` — 事件循环变更时重建池 | 容器环境事件循环回收后复用旧池连接导致 `RuntimeError: Task got Future attached to a different loop` |
| 4 | `test_parse_lnglat_valid` — 坐标解析正常路径 | 坐标解析是空间查询的入口，错误会传播到 SQL |
| 5 | `test_parse_lnglat_no_spaces` — 无空格坐标解析 | 用户传入的各种坐标格式必须兼容 |
| 6 | `test_tool_metadata_populated` — TOOL_METADATA 非空 | QueryGenerator 依赖元数据注入提示词，缺失将导致 LLM 不知道可用工具 |
| 7 | `test_tool_metadata_structure` — 元数据结构完整性 | name/description/parameters 缺失会导致提示词注入空值或格式异常 |
| 8 | `test_tool_dispatch_matches_metadata` — 注册一致性 | metadata 与 dispatch 不一致会导致 QueryGenerator 生成的工具名无对应 handler |
| 9 | `test_gateway_safe_routes_to_analyst` — 安全输入固定进 analyst | 拓扑核心变更：analyst 是 gateway 后的固定边，路由失败将跳过需求提取 |
| 10 | `test_gateway_unsafe_routes_to_reply` — 不安全输入直达 reply | 安全边界：malicious/chitchat 不得进入业务节点 |
| 11 | `test_manager_routes_query_generator` — Manager 调研路由 | 核心信息完整后必须能路由到 query_generator |
| 12 | `test_manager_routes_reply` — Manager 兜底路由 | 未知/异常情况下 fallback 到 reply |
| 13 | `test_spatial_search_returns_real_data` (INT) — 真实 POI 数据验证 | 实时数据库不可用将导致返回空结果 |
| 14 | `test_spatial_search_category_filter` (INT) — 类别过滤正确性 | 类别映射错误导致用户查询无结果 |
| 15 | `test_route_search_shortest_path` (INT) — 真实路网最短路径 | pgRouting 函数重载冲突已在 Phase 4 修复 |
| 16 | `test_route_search_isochrone` (INT) — 等时圈可达性 | 拓扑未构建或过时将导致零节点或错误距离 |
| 17 | `test_init_retrieval_db_executes_ddl` — 建表 DDL 正确执行 | 检索表缺失将导致 Hash 节点无法持久化结果 |
| 18 | `test_store_result_insert` — 单条结果写入并 JSON 序列化 | 写入失败将导致检索结果不可达 |
| 19 | `test_get_results_returns_payloads` — 按 hash_key 批量查询 | 查询失败将导致 Recommender/Planner 无法读取检索结果 |
| 20 | `test_blacklist_filter_hit` — 黑名单命中剔除 | 黑名单失效将导致不安全内容进入 LLM |
| 21 | `test_code_filter_unsafe_tag` — unsafe tag 剔除 | Layer 3 失效将导致违规内容通过 |
| 22 | `test_code_filter_low_relevance` — 低相关度剔除 | 阈值失效将导致无关结果污染检索库 |
| 23 | `test_code_filter_low_utility` — 低实用性剔除 | 无实用价值的结果浪费存储和后续计算 |
| 24 | `test_should_continue_loop_enough_passed_and_llm_false` — 充分时退出 | 循环无法退出将导致无限迭代 |
| 25 | `test_should_continue_loop_not_enough_passed` — 不充分时继续 | 过早退出将导致调研覆盖不足 |
| 26 | `test_should_continue_loop_max_loops_exceeded` — 硬上限强制退出 | 无限循环保护失效将阻塞整个 Agent |
| 27 | `test_critic_node_empty_results_skips` — 空输入跳过 | 空结果未处理将导致异常 |
| 28 | `test_critic_node_full_pipeline` — 完整三层管线 | 端到端过滤链路断裂将导致质量问题 |
| 29 | `test_generate_hash_key_deterministic` — hash 确定性 | 去重依赖相同输入产生相同 hash，不一致将导致重复存储 |
| 30 | `test_generate_hash_key_different_content` — 不同内容不同 hash | hash 碰撞将导致不同结果被误判为重复 |
| 31 | `test_persist_results_creates_mapping` — 映射正确性 | query→hashes 映射错误将导致父图无法索引检索结果 |
| 32 | `test_hash_node_empty_skips` — 空结果跳过 | 空结果未处理导致异常 |
| 33 | `test_hash_node_persists_and_exposes_hashes` — 持久化+暴露 | 核心链路：结果持久化失败将导致 Recommender/Planner 无数据可用 |
| 34 | `test_generate_summary_poi_list` — POI 摘要生成 | 摘要字段是 Critic LLM 评分的输入，缺失将导致评分质量下降 |
| 35 | `test_generate_summary_shortest_route` — 路线摘要生成 | 路线类型结果摘要错误将导致 Critic 无法正确评估 |
| 36 | `test_generate_summary_isochrone` — 等时圈摘要生成 | 等时圈摘要字段缺失影响可达性评估 |
| 37 | `test_execute_tasks_wraps_in_research_result` — envelope 包裹 | Search 输出必须为 ResearchResult 格式，否则 Critic 无法解析 |
| 38 | `test_execute_tasks_handler_exception` — 工具异常不崩溃 | 单个工具失败不得中断整个搜索批次 |
| 39 | `test_search_node_missing_research_data` — 空状态跳过 | search_node 缺少 research_data 时必须优雅跳过 |
| 40 | `test_search_node_empty_active_queries` — 空任务跳过 | 无活跃查询时正常返回 |
| 41 | `test_search_node_writes_to_loop_state` — loop_state 写入 | 结果写入 loop_state.query_results 是整个 Research Loop 的数据入口 |
| 42 | `test_qg_injects_feedback_into_prompt` — Critic 反馈注入 | QueryGenerator 忽略反馈将导致 Research Loop 迭代无改进 |
| 43 | `test_qg_injects_passed_queries_into_prompt` — 去重查询注入 | 已通过查询未去重将导致重复搜索浪费资源 |
| 44 | `test_qg_preserves_loop_state` — model_copy 保留 loop_state | 重建 ResearchManifest 会丢弃 feedback/passed_queries，导致迭代环路断裂 |
| 45 | `test_qg_preserves_research_hashes` — 保留 research_hashes | research_hashes 丢失将导致 Hash 节点持久化映射被清空 |
| 46 | `test_qg_appends_research_history` — 追加调研历史 | history 错误将影响后续 LLM 节点上下文质量 |
| 47 | `test_qg_creates_manifest_when_none` — 无数据时创建 | 首轮调研无 ResearchManifest 时必须正确初始化 |
| 48 | `test_gen_doc_id_deterministic` — doc_id 确定性 | 相同内容必须产生相同 SHA256 doc_id，否则文档去重失效 |
| 49 | `test_search_basic` — BM25 检索正常路径 | 文档检索核心链路，失败将导致 document_search 工具不可用 |
| 50 | `test_search_place_filter` — 地名过滤 | 跨目的地查询时地名过滤失效将返回无关文档 |
| 51 | `test_search_score_threshold` — 相关度阈值过滤 | BM25_SCORE_THRESHOLD 失效将导致低质文档进入结果 |
| 52 | `test_ingest` — 文档入库+索引更新 | ingest 链路断裂将导致离线管线无法注入文档 |
| 53 | `test_document_search_tool` — 工具注册与 handler | document_search 工具未正确注册将导致 QG 生成任务无 handler 执行 |
| 54 | `test_document_search_missing_query` — 必填参数校验 | 空 query 调用 BM25 将导致异常 |
| 55 | `test_search_node_splits_doc_from_non_doc` — 文档/非文档分流 | 文档结果误入 query_results 会进入 Critic 审查；非文档误入 passed_doc_ids 会跳过 Hash |
| 56 | `test_search_node_doc_results_accumulate` — doc_ids 跨迭代累积 | passed_doc_ids 覆盖式写入将丢失前几轮检索到的文档 |
| 57 | `test_hash_node_promotes_passed_doc_ids` — doc_ids 提升到 Manifest | Hash 节点未提升 doc_ids 将导致 matched_doc_ids 始终为空，下游无文档可用 |
| 58 | `test_hash_node_merges_matched_doc_ids` — 跨轮合并 matched_doc_ids | 覆盖式写入 matched_doc_ids 将丢弃之前轮次的文档检索结果 |

## P1 — Critical Items

| # | Test | Module |
|---|---|---|
| 1 | `test_chat_request_validation` | API Schema |
| 2 | `test_custom_dsn_from_env` | PostGIS Config |
| 3 | `test_get_pool_reuses_existing_pool` | Connection Pool |
| 4 | `test_close_pool_releases_and_nulls` | Connection Pool |
| 5 | `test_spatial_search_returns_pois` | Search Tools |
| 6 | `test_route_search_shortest_path` | Search Tools |
| 7 | `test_route_search_isochrone` | Search Tools |
| 8 | `test_route_search_invalid_mode` | Search Tools |
| 9 | `test_route_search_shortest_missing_destination` | Search Tools |
| 10 | `test_parse_lnglat_invalid_format` | Search Tools |
| 11 | `test_resolve_location_coords` | Search Tools |
| 12 | `test_geocode_by_name` | Search Tools |
| 13 | `test_geocode_truncation` | Search Tools |
| 14 | `test_batch_store_results` | Retrieval DB |
| 15 | `test_cleanup_session` | Retrieval DB |
| 16 | `test_get_results_empty_list_short_circuits` | Retrieval DB |
| 17 | `test_blacklist_filter_all_pass` | Critic Node |
| 18 | `test_blacklist_filter_case_insensitive` | Critic Node |
| 19 | `test_code_filter_all_pass` | Critic Node |
| 20 | `test_should_continue_loop_llm_wants_more` | Critic Node |
| 21 | `test_aggregate_loop_summary` | Critic Node |
| 22 | `test_load_blacklist_returns_list` | Critic Node |
| 23 | `test_critic_node_llm_error_graceful` | Critic Node |
| 24 | `test_generate_hash_key_different_query` | Hash Node |
| 25 | `test_persist_results_empty_list` | Hash Node |
| 26 | `test_hash_node_merges_existing_hashes` | Hash Node |
| 27 | `test_generate_summary_poi_truncation` | Search Node |
| 28 | `test_generate_summary_fallback_json` | Search Node |
| 29 | `test_execute_tasks_unsupported_tool` | Search Node |
| 30 | `test_search_node_preserves_existing_loop_state` | Search Node |
| 31 | `test_qg_empty_feedback_and_passed_queries` | QueryGenerator Node |
| 32 | `test_qg_llm_error_graceful` | QueryGenerator Node |
| 33 | `test_qg_content_list_merge` | QueryGenerator Node |
| 34 | `test_tokenize_empty` | DocumentManager |
| 35 | `test_search_empty_index` | DocumentManager |
| 36 | `test_search_node_empty_doc_results` | Search Node |
| 37 | `test_search_node_only_non_doc_results` | Search Node |
| 38 | `test_hash_node_dedup_matched_doc_ids` | Hash Node |
| 39 | `test_build_index_empty` | DocumentManager |
| 40 | `test_build_index_json_str_payload` | DocumentManager |
| 41 | `test_get_document_manager_singleton` | DocumentManager |

## P2 — Edge Case Items

| # | Test | Module |
|---|---|---|
| 1 | `test_close_pool_none_is_noop` | Connection Pool |
| 2 | `test_parse_lnglat_invalid_format` | Search Tools |
| 3 | `test_spatial_search_empty_result` | Search Tools |
| 4 | `test_get_results_partial_match` | Retrieval DB |
| 5 | `test_store_result_overwrite` | Retrieval DB |
| 6 | `test_aggregate_loop_summary_empty` | Critic Node |
| 7 | `test_critic_node_accumulates_all_passed` | Critic Node |
| 8 | `test_hash_node_dedup_same_query_same_content` | Hash Node |
| 9 | `test_gen_doc_id_different_content` | DocumentManager |
| 10 | `test_build_index_json_str_payload` | DocumentManager |
| 11 | `test_build_index_empty` | DocumentManager |

## High-Risk Evaluation Items

1. **PostGIS 连接不可用**: `spatial_search` 和 `route_search` 依赖运行中的 PostGIS 实例。Phase 4 集成测试 (4 P0) 已通过真实数据库验证端到端行为。
2. **坐标系不一致**: OSM 数据为 EPSG:3857，视图转换为 EPSG:4326。`ST_Distance` 需 `::geography` 投射以获取米制距离。若投射遗漏，距离结果将错误。
3. **pgRouting 拓扑过期**: `routing_network` 表在 OSM 导入时生成，OSM 数据更新后需重建拓扑，否则路径计算使用过时路网。
4. **图拓扑正确性**: `test_graph_routing.py` 守护 gateway → analyst 固定边、Manager 路由范围。若拓扑变更导致 analyst 被绕过，整个需求提取链路断裂。
5. **连接池事件循环校验**: `get_pool()` 在返回缓存池前校验 `_pool_loop is current_loop`。容器环境（uvicorn worker 回收/K8s 健康检查重启）中事件循环可能被替换，复用旧池将导致 `RuntimeError: Task got Future attached to a different loop`。`test_get_pool_recreates_on_loop_mismatch` 覆盖此场景。注意：测试中路由函数是 graph.py 闭包逻辑的副本，真实图编译需 async 环境。
6. **Retrieval DB 表缺失**: `retrieval_results` 表由 `init_retrieval_db()` 在应用启动时创建。若未调用或 DDL 执行失败，Hash 节点的 `batch_store_results` 将抛出 PostgreSQL 错误，整个 Research Loop 持久化链路断裂。`test_init_retrieval_db_executes_ddl` 验证 DDL 正确性。
7. **Critic 三层过滤失效**: Layer 1 黑名单若加载失败或匹配逻辑错误，不安全内容将进入 LLM 评分环节。Layer 3 阈值若设置不当（过高或过低），将导致有效结果被丢弃或无效结果通过。`test_critic_node_full_pipeline` 覆盖端到端过滤链路。当前测试中 Layer 2 LLM 调用已 mock，真实 LLM 行为需在集成测试中验证。
8. **ResearchManifest 重建丢失 loop_state**: QueryGenerator 旧代码使用 `ResearchManifest(...)` 新建实例，导致 `loop_state`（feedback、passed_queries、all_passed_results）和 `research_hashes` 被清空。这意味着 Research Loop 多轮迭代中 Critic 反馈和去重信息全部丢失，循环无法正确收敛。已修复为 `model_copy(update=...)` 并在 `test_qg_preserves_loop_state` / `test_qg_preserves_research_hashes` 中守护。
9. **全局 State 字段泄漏**: `active_queries`/`verified_results`/`feedback_history` 曾是 ResearchManifest 上的全局字段。已清理：`active_queries` 迁移至 `ResearchLoopInternal`（子图私有），`verified_results` 和 `feedback_history` 删除。Manager 的 `hashes_count` 改用 `research_hashes` 计算。Serializer 新增 `ResearchLoopInternal`/`ResearchResult`/`CriticResult`/`LoopSummary` 注册。
10. **文档检索结果丢失**: `document_search` 返回的 doc_id 通过 `passed_doc_ids`（Search 写入）→ `matched_doc_ids`（Hash 提升）路径传递。Search 节点必须正确分流文档/非文档结果（by `tool_name == "document_search"`），Hash 节点即使在 `all_passed_results` 为空时也必须完成 doc_ids 提升。若任一环节遗漏，文档检索结果将静默丢失。`test_search_node_splits_doc_from_non_doc` / `test_hash_node_promotes_passed_doc_ids` 守护此链路。
11. **BM25 空索引启动**: `DocumentManager.build_index()` 在 `retrieval_results` 表无 `_system` 文档时不会创建 `BM25Okapi`（该库不支持空语料）。此时 `is_loaded = False`，`search()` 返回空列表。`main.py` lifespan 启动时自动加载，若 PostgreSQL 不可达或表未初始化，文档检索功能静默降级而非崩溃。`test_build_index_empty` 覆盖此场景。
12. **doc_id 碰撞**: SHA256 前 16 位作为 doc_id，在文档量 <10^6 时碰撞概率极低。但若离线管线错误地用相同内容多次调用 `ingest()`，PostgreSQL `ON CONFLICT (hash_key) DO UPDATE` 会正确覆盖而非产生重复行。`test_gen_doc_id_deterministic` 验证确定性。
