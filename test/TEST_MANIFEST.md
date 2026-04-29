# TEST_MANIFEST — GeoTrave Test Coverage Matrix

## Coverage Dimension Matrix

| Module | Test File | P0 | P1 | P2 | Total |
|---|---|---|---|---|---|
| `src/api/schema.py` | `test/unit/test_api_schemas.py` | 0 | 1 | 0 | 1 |
| `src/database/postgis/config.py` | `test/unit/database/postgis/test_config.py` | 1 | 1 | 0 | 2 |
| `src/database/postgis/connection.py` | `test/unit/database/postgis/test_connection.py` | 2 | 2 | 1 | 5 |
| `src/database/retrieval_db.py` | `test/unit/database/postgis/test_retrieval_db.py` | 3 | 3 | 2 | 8 |
| `src/agent/nodes/search/tools.py` | `test/unit/agent/nodes/search/test_tools.py` | 5 | 9 | 2 | 16 |
| `src/agent/graph.py` | `test/unit/agent/test_graph_routing.py` | 4 | 0 | 0 | 4 |
| `src/agent/nodes/search/tools.py` | `test/integration/test_spatial_tools.py` | 4 | 0 | 0 | 4 |
| **Total** | | **19** | **16** | **5** | **40** |

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

## P2 — Edge Case Items

| # | Test | Module |
|---|---|---|
| 1 | `test_close_pool_none_is_noop` | Connection Pool |
| 2 | `test_parse_lnglat_invalid_format` | Search Tools |
| 3 | `test_spatial_search_empty_result` | Search Tools |
| 4 | `test_get_results_partial_match` | Retrieval DB |
| 5 | `test_store_result_overwrite` | Retrieval DB |

## High-Risk Evaluation Items

1. **PostGIS 连接不可用**: `spatial_search` 和 `route_search` 依赖运行中的 PostGIS 实例。Phase 4 集成测试 (4 P0) 已通过真实数据库验证端到端行为。
2. **坐标系不一致**: OSM 数据为 EPSG:3857，视图转换为 EPSG:4326。`ST_Distance` 需 `::geography` 投射以获取米制距离。若投射遗漏，距离结果将错误。
3. **pgRouting 拓扑过期**: `routing_network` 表在 OSM 导入时生成，OSM 数据更新后需重建拓扑，否则路径计算使用过时路网。
4. **图拓扑正确性**: `test_graph_routing.py` 守护 gateway → analyst 固定边、Manager 路由范围。若拓扑变更导致 analyst 被绕过，整个需求提取链路断裂。
5. **连接池事件循环校验**: `get_pool()` 在返回缓存池前校验 `_pool_loop is current_loop`。容器环境（uvicorn worker 回收/K8s 健康检查重启）中事件循环可能被替换，复用旧池将导致 `RuntimeError: Task got Future attached to a different loop`。`test_get_pool_recreates_on_loop_mismatch` 覆盖此场景。注意：测试中路由函数是 graph.py 闭包逻辑的副本，真实图编译需 async 环境。
6. **Retrieval DB 表缺失**: `retrieval_results` 表由 `init_retrieval_db()` 在应用启动时创建。若未调用或 DDL 执行失败，Hash 节点的 `batch_store_results` 将抛出 PostgreSQL 错误，整个 Research Loop 持久化链路断裂。`test_init_retrieval_db_executes_ddl` 验证 DDL 正确性。
