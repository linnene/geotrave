# Spatial_DB_Spec — PostGIS + pgRouting 地理空间检索引擎

## 1. 架构动机

### 1.1 ChromaDB 替换原因

原 ChromaDB 向量检索存在三个根本性不适配：

| 缺陷 | 向量检索行为 | 旅行规划实际需求 |
|---|---|---|
| 语义≠地理相关性 | 文档语义相似即召回 | 需要空间邻近、包含、距离约束 |
| 无空间拓扑 | 无法表达"附近""区域内" | "大研古镇 1km 内的客栈"是最基础查询 |
| 结构化数据拍平 | POI、路网被切成无序文本片段 | OSM 数据天然是几何+属性结构化实体 |

### 1.2 目标能力

- 空间查询：点、线、面几何的存储与空间索引检索
- 路网拓扑：真实路网上的最短路径 / 等时圈 / 距离矩阵
- 属性过滤：几何+标签联合查询（"评分>4.0 且在景区 500m 内的餐厅"）
- Agent 工具化：`spatial_search` 和 `route_search` 两个新工具替代原 `vector_db`

---

## 2. 组件拓扑

```
┌─────────────────────────────────────────────────────┐
│                   Agent Layer                        │
│  query_generator ──► search ──► spatial_search      │
│                              ──► route_search        │
└──────────────────────┬──────────────────────────────┘
                       │ asyncpg / SQLAlchemy
┌──────────────────────▼──────────────────────────────┐
│              PostgreSQL + Extensions                 │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │   PostGIS     │  │   pgRouting  │                 │
│  │  (几何/GiST)  │  │  (Dijkstra)  │                 │
│  └──────────────┘  └──────────────┘                 │
│         │                  │                         │
│         ▼                  ▼                         │
│  ┌──────────────────────────────────┐               │
│  │         OSM 路网底表              │               │
│  │  planet_osm_road / point / line  │               │
│  │  + 自定义 POI 物化视图            │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

导入管线：

```
OSM .pbf 文件 ─► osm2pgsql ─► PostgreSQL/PostGIS 库
                                 │
                                 ├── planet_osm_point  (景点/餐厅/酒店)
                                 ├── planet_osm_line   (道路)
                                 ├── planet_osm_roads  (主干路网)
                                 └── planet_osm_polygon (建筑/区域)
```

---

## 3. 核心表结构设计

### 3.1 OSM 基础表（osm2pgsql 默认产出 + 扩展视图）

osm2pgsql 导入后自动生成以下表。在此基础上建立物化视图用于 Agent 查询：

```sql
-- 路网表（pgRouting 输入）
-- 来源: planet_osm_roads + planet_osm_line
CREATE VIEW routing_ways AS
SELECT
    osm_id,
    name,
    highway,
    maxspeed,
    oneway,
    ST_Length(way::geography) AS length_m,
    way AS geom
FROM planet_osm_roads
WHERE highway IS NOT NULL;
```

### 3.2 POI 统一视图

```sql
-- 面向 Agent 的 POI 统一检索视图
CREATE VIEW geotrave_poi AS
SELECT
    osm_id,
    name,
    amenity       AS category,
    tourism       AS sub_category,
    way           AS geom,
    ST_X(way)     AS lng,
    ST_Y(way)     AS lat,
    tags          AS raw_tags
FROM planet_osm_point
WHERE amenity IS NOT NULL OR tourism IS NOT NULL;
```

### 3.3 空间索引

```sql
CREATE INDEX idx_poi_geom ON geotrave_poi USING GIST(geom);
CREATE INDEX idx_roads_geom ON planet_osm_roads USING GIST(way);
```

### 3.4 关键字段说明

| 表/视图 | 用途 | 核心列 |
|---|---|---|
| `planet_osm_point` | 点状 POI | `osm_id, name, amenity, tourism, way` |
| `planet_osm_roads` | 路网（主干） | `osm_id, name, highway, oneway, way` |
| `planet_osm_line` | 全部道路线 | `osm_id, name, highway, way` |
| `planet_osm_polygon` | 建筑/区域 | `osm_id, name, building, landuse, way` |
| `geotrave_poi` (视图) | 统一 POI 查询 | `osm_id, name, category, sub_category, geom, lng, lat` |
| `routing_ways` (视图) | 路网拓扑 | `osm_id, name, highway, length_m, geom` |

---

## 4. Agent 工具接口

### 4.1 spatial_search — 空间兴趣点检索

```
名称: spatial_search
描述: 基于地理位置检索 POI，支持空间范围过滤、类别筛选、属性排序
参数:
  - center: string (中心点坐标 "lng,lat")
  - radius_m: int (搜索半径，米)
  - category: string (可选: accommodation/dining/attraction/transport)
  - limit: int (返回条数上限，默认 10)
  - min_score: float (可选: 最低评分)
输出: RetrievalMetadata 列表，source 字段含 POI 名称/坐标/类别
```

**底层 SQL 示例**：
```sql
SELECT name, category, ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography) AS dist_m
FROM geotrave_poi
WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography, ?)
  AND category = ?
ORDER BY dist_m
LIMIT ?;
```

### 4.2 route_search — 路径与等时圈计算

```
名称: route_search
描述: 计算两点间的最短路径距离/时间，或某点的等时圈范围
参数:
  - origin: string (起点 "lng,lat")
  - destination: string (可选: 终点 "lng,lat")
  - mode: string ("shortest" | "isochrone")
  - isochrone_minutes: int (等时圈分钟数，默认 15)
输出: RetrievalMetadata，source 含距离(km)/时间(min)/等时圈边界坐标
```

**pgRouting 最短路径**：
```sql
SELECT * FROM pgr_dijkstra(
    'SELECT osm_id AS id, source, target, length_m AS cost FROM routing_ways',
    start_node_id, end_node_id, directed := false
);
```

---

## 5. 分阶段实现计划

### Phase 1 — 环境与数据准备

| 步骤 | 内容 | 验证方式 |
|---|---|---|
| 1.1 | 安装 PostgreSQL 15+、PostGIS 3.4+、pgRouting 3.5+ | `SELECT postgis_full_version();` |
| 1.2 | 安装 osm2pgsql，下载目标区域 OSM `.pbf` 文件（如中国或特定省份） | `osm2pgsql --version` |
| 1.3 | 执行 osm2pgsql 导入，生成 `planet_osm_*` 表 | `SELECT count(*) FROM planet_osm_point;` |
| 1.4 | 创建 `geotrave_poi` 和 `routing_ways` 视图，建立 GIST 空间索引 | 视图可查询，索引存在 |

**交付物**：可查询的 PostgreSQL 空间数据库，含完整 OSM 底表。

### Phase 2 — 数据库连接层

| 步骤 | 内容 | 验证方式 |
|---|---|---|
| 2.1 | 在 `pyproject.toml` 添加 `asyncpg`、`geoalchemy2` 依赖 | `uv sync` 成功 |
| 2.2 | 创建 `src/database/postgis/__init__.py`、`connection.py` — asyncpg 连接池管理 | 连接池创建并返回健康连接 |
| 2.3 | 创建 `src/database/postgis/config.py` — `POSTGIS_DSN` 环境变量提取 | 配置可正确加载 |
| 2.4 | 在 `.env` 添加 `POSTGIS_DSN=postgresql://user:pass@localhost:5432/geotrave` | 连接串可被读取 |

**交付物**：Agent 节点可通过 `from src.database.postgis import get_pool` 获取连接池。

### Phase 3 — 工具实现

| 步骤 | 内容 | 验证方式 |
|---|---|---|
| 3.1 | 在 `search/tools.py` 注册 `spatial_search` 工具，实现异步处理器 | 传入中心点+半径，返回实际 POI 数据 |
| 3.2 | 在 `search/tools.py` 注册 `route_search` 工具，实现 pgRouting 调用 | 传入两点坐标，返回路径距离和时间 |
| 3.3 | QueryGenerator 的 `TOOL_METADATA` 自动获取新工具文档（无需手动操作） | prompt 中可见两个新工具描述 |
| 3.4 | 添加 `run_import.py` 脚本在 `script/` 下，封装 osm2pgsql 调用和视图创建 | PowerShell 脚本可一键执行 |

**交付物**：两个可工作的空间检索工具，替代原 `vector_db`。

### Phase 4 — 集成验证

| 步骤 | 内容 | 验证方式 |
|---|---|---|
| 4.1 | 端到端测试：用户输入"推荐大研古镇附近的客栈"→ Agent 路由到 spatial_search → 返回真实 OSM 数据 | 手动 Streamlit 测试通过 |
| 4.2 | 性能验证：空间索引查询在 100ms 内返回结果 | 日志确认 latency |
| 4.3 | 添加 `test/unit/test_spatial_tools.py` — 针对 spatial_search 和 route_search 的 mock 数据库测试 | pytest 通过 |

---

## 6. 期望最终效果

### 6.1 查询能力对比

| 查询类型 | ChromaDB (旧) | PostGIS (新) |
|---|---|---|
| "丽江古城附近的客栈" | 语义相似度搜索，结果可能远在香格里拉 | `ST_DWithin` 空间半径查询，精确返回 1km 内客栈 |
| "从酒店到大理古城步行多久" | 无法回答 | pgRouting Dijkstra 最短路径 + 步行速度估算 |
| "评分>4.5 的海鲜餐厅，按距离排序" | 无结构化评分字段 | 几何+属性联合查询，`ORDER BY dist_m` |
| "15 分钟步行范围内有哪些景点" | 无法回答 | pgr_drivingDistance 等时圈查询 |

### 6.2 Agent 对话示例

```
用户: 我想去大理，推荐古城附近步行10分钟以内的客栈，预算300以内

Gateway → Manager → Analyst → Manager
  提取: destination=[大理], accommodation_preference="古城附近步行10分钟以内", budget_limit=300

Manager → query_generator → spatial_search + route_search
  spatial_search: center="100.16,25.69", radius_m=800, category="accommodation"
  route_search: mode="isochrone", origin="100.16,25.69", isochrone_minutes=10

Search → 返回:
  - 大理古城兰林阁酒店 (坐标 100.164,25.692, 距离古城中心 320m)
  - 大理风花雪月客栈 (坐标 100.161,25.688, 距离古城中心 180m)
  - 等时圈边界: 步行 10 分钟覆盖范围约 800m

Manager → reply (或未来 Recommender)
  为您找到古城步行10分钟内的 2 家客栈...
```

### 6.3 最终数据库架构

```
PostgreSQL (geotrave)
├── public
│   ├── planet_osm_point      ← osm2pgsql 导入
│   ├── planet_osm_line        ← osm2pgsql 导入
│   ├── planet_osm_roads       ← osm2pgsql 导入
│   ├── planet_osm_polygon     ← osm2pgsql 导入
│   ├── geotrave_poi           ← 物化视图 (POI 统一入口)
│   ├── routing_ways           ← 视图 (pgRouting 输入)
│   └── spatial_ref_sys        ← PostGIS 坐标系表
├── postgis 扩展
└── pgrouting 扩展
```

---

## 7. 注意事项

- **OSM 数据更新**：`.pbf` 文件需要定期重新导入，建议编写定时任务或触发式更新脚本
- **路网拓扑构建**：osm2pgsql 不自动建立 pgRouting 的 `source/target` 节点列，需 `pgr_createTopology()` 预处理
- **坐标系**：OSM 数据为 EPSG:4326，距离计算使用 `geography` 类型投射保证精度
- **中国数据**：下载 [Geofabrik](https://download.geofabrik.de/asia/china.html) 的中国区域 `.pbf`，约 1GB
- **性能基准**：GIST 空间索引下，百万级 POI 的 `ST_DWithin` 查询应 <50ms
