# TEST_MANIFEST — GeoTrave Test Coverage Matrix

## Coverage Dimension Matrix

| Module | Test File | P0 | P1 | P2 | Total |
|---|---|---|---|---|---|
| `src/api/schema.py` | `test/unit/test_api_schemas.py` | 0 | 1 | 0 | 1 |
| `src/database/postgis/config.py` | `test/unit/database/postgis/test_config.py` | 1 | 1 | 0 | 2 |
| `src/database/postgis/connection.py` | `test/unit/database/postgis/test_connection.py` | 1 | 2 | 1 | 4 |
| `src/agent/nodes/search/tools.py` | `test/unit/agent/nodes/search/test_tools.py` | 2 | 6 | 1 | 9 |
| **Total** | | **4** | **10** | **2** | **16** |

## P0 — Blocker Items

| # | Test | Risk |
|---|---|---|
| 1 | `test_default_dsn` — 默认 DSN 回退值 | 数据库连接失败将导致整个空间检索链路中断 |
| 2 | `test_get_pool_creates_new_pool` — 连接池初始化 | 无连接池则所有 spatial/route 工具不可用 |
| 3 | `test_parse_lnglat_valid` — 坐标解析正常路径 | 坐标解析是空间查询的入口，错误会传播到 SQL |
| 4 | `test_parse_lnglat_no_spaces` — 无空格坐标解析 | 用户传入的各种坐标格式必须兼容 |

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

## High-Risk Evaluation Items

1. **PostGIS 连接不可用**: `spatial_search` 和 `route_search` 依赖运行中的 PostGIS 实例。当前仅通过 mock 测试覆盖逻辑层，需 Phase 4 集成测试验证端到端行为。
2. **坐标系不一致**: OSM 数据为 EPSG:3857，视图转换为 EPSG:4326。`ST_Distance` 需 `::geography` 投射以获取米制距离。若投射遗漏，距离结果将错误。
3. **pgRouting 拓扑过期**: `routing_network` 表在 OSM 导入时生成，OSM 数据更新后需重建拓扑，否则路径计算使用过时路网。
