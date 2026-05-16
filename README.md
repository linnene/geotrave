<p align="center">
  <img src="assets/GeoTrave.png" alt="GeoTrave Logo" width="360" />
</p>

# GeoTrave

**GeoTrave 是一个基于 LangGraph 的多智能体旅行规划引擎。** 它把自然语言旅行需求拆解成安全过滤、用户画像提取、并行多维调研、检索质量评估、推荐生成和逐日行程规划等步骤，面向“边聊边规划”的个性化旅行助手场景。

## Highlights

| 能力 | 当前实现 |
|---|---|
| 多智能体编排 | LangGraph 父图 + Research 子图，支持 Manager 路由和并行 Send fan-out |
| 渐进式需求理解 | Gateway 安全过滤，Analyst 提取 `UserProfile`，Reply 追问缺失信息 |
| 多源旅行调研 | PostGIS/pgRouting、BM25 文档检索、DuckDuckGo + crawl4ai、Open-Meteo |
| 检索质量控制 | Critic 三层过滤：黑名单、LLM 评分、代码阈值 |
| 状态持久化 | LangGraph SQLite checkpoint + PostgreSQL JSONB research cache |
| 工程化保障 | pytest strict asyncio、功能分组 CI、Docker/CD workflow |

## Quick Start

### 1. 准备环境

```bash
uv sync
cp .env.example .env
```

在 `.env` 中至少配置 LLM 相关变量：

```bash
GLOBAL_MODEL_API_KEY=...
GLOBAL_MODEL_BASE_URL=...
GLOBAL_MODEL_ID=...
```

项目要求 Python 3.12+，所有 Python 命令统一通过 `uv run` 执行。

### 2. 启动 PostGIS

如果只想跑不依赖真实空间数据的单元测试，可以跳过本步骤。要启用 `spatial_search` / `route_search`，需要启动 PostGIS 并导入 OSM 数据：

```bash
cd database/postgis
docker compose up -d db
docker compose --profile init run --rm db-init
```

默认 DSN 为：

```bash
postgresql://geotrave:geotrave_dev@localhost:5432/geotrave
```

更多数据库与容器说明见 [docs/DOCKER.md](docs/DOCKER.md) 和 [Spatial_DB_Spec.md](src/database/postgis/Spatial_DB_Spec.md)。

### 3. 启动 API

```bash
uv run python -m src.main
```

常用入口：

| Endpoint | 用途 |
|---|---|
| `GET /health` | 服务健康检查 |
| `GET /docs` | FastAPI Swagger UI |
| `POST /chat/` | 多轮旅行规划对话 |

示例请求：

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"我想下个月去札幌玩三天，喜欢温泉和本地美食","session_id":"demo-trip"}'
```

可选调试 UI：

```bash
uv run streamlit run test/test_ui.py
```

## Commands

```bash
uv sync                                             # 安装依赖
uv run python -m src.main                           # 启动 API
uv run pytest --collect-only -q                     # 收集测试
uv run pytest test/unit -v --asyncio-mode=strict    # 单元测试
uv run pytest test/integration -v --asyncio-mode=strict
uv run python script/run_api_tests.py --timeout 120 # Newman API 集成测试
uv run streamlit run test/test_ui.py                # 调试 UI
```

## Architecture

```text
START
  -> gateway
  -> analyst
  -> manager
  -> dimension_planner
  -> [research_loop x N]
  -> research_merge
  -> manager
  -> recommender -> reply -> END
   | planner     -> END
   | reply       -> END
```

### 主图节点

| Node | 文件 | 职责 |
|---|---|---|
| Gateway | [node.py](src/agent/nodes/gateway/node.py) | 安全过滤、PII 脱敏、意图分类 |
| Analyst | [node.py](src/agent/nodes/analyst/node.py) | 提取用户画像并审计核心信息完整性 |
| Manager | [node.py](src/agent/nodes/manager/node.py) | LLM 路由 + 硬守卫，决定调研、推荐、规划或回复 |
| DimensionPlanner | [node.py](src/agent/nodes/research/dimension_planner/node.py) | 将调研拆成并行维度，供 `Send` fan-out |
| Research Loop | [subgraph.py](src/agent/nodes/research/subgraph.py) | QG -> Search -> Critic -> Hash 的闭环调研子图 |
| Research Merge | [node.py](src/agent/nodes/research/merge/node.py) | 汇合并行调研分支 |
| Recommender | [node.py](src/agent/nodes/recommender/node.py) | 按维度生成推荐 |
| Planner | [node.py](src/agent/nodes/planner/node.py) | 生成逐日行程 |
| Reply | [node.py](src/agent/nodes/reply/node.py) | 追问、拦截、推荐呈现和降级回复 |

### 状态与数据流

`TravelState` 定义在 [src/agent/state/state.py](src/agent/state/state.py)。核心原则是状态字段拥有明确写入者，避免多个节点争抢同一字段。

- `messages` 使用 LangGraph `add_messages` reducer。
- `research_data` 使用 `_merge_research_manifest` 合并并行分支结果。
- 原始检索 payload 不进入全局 state，而是落到 PostgreSQL JSONB；下游通过 hash key 拉取。
- `planned_dimensions`、`focus_dimension`、`dimension_hints` 控制并行调研。

完整权限矩阵见 [STATE_SPEC.md](src/agent/state/STATE_SPEC.md)，Research 子图细节见 [ARCHITECTURE.md](src/agent/nodes/research/ARCHITECTURE.md)。

## Testing and CI

当前测试按功能拆分管理，`uv run pytest --collect-only -q` 可收集 **214** 个测试。

| CI Workflow | 覆盖范围 |
|---|---|
| `CI - Core Agent` | Gateway、Analyst、Manager、Reply、图编译、API schema |
| `CI - Research and Search` | Research Loop、QueryGenerator、Search、Web/Weather/Docs、ResearchLoader |
| `CI - Delivery` | Recommender、Planner |
| `CI - Database and Spatial` | PostGIS 配置、连接池、Retrieval DB、空间集成测试 |
| `CI - API Newman` | FastAPI 运行时与 Postman/Newman 场景 |

测试清单和风险矩阵见 [test/TEST_MANIFEST.md](test/TEST_MANIFEST.md)。PostGIS 集成测试依赖 `POSTGIS_DSN`；未配置时会按测试内 skip guard 跳过真实数据库场景。

## Project Structure

```text
src/
  agent/
    graph.py                 # LangGraph 主拓扑
    state/                   # TravelState 与 Pydantic schema
    nodes/                   # Gateway / Analyst / Manager / Research / Delivery
  api/                       # FastAPI router 与 schema
  database/
    checkpointer/            # SQLite checkpoint
    postgis/                 # PostGIS 连接与配置
    retrieval_db.py          # Research JSONB cache
  utils/                     # LLMFactory、Prompt、Logger、Config

database/postgis/            # PostGIS + pgRouting + osm2pgsql 容器与 SQL
postman/                     # Newman API 测试集合
test/                        # unit / integration / Streamlit debug UI
docs/                        # Docker、计划和项目状态文档
```

## Key Documents

| 文档 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | 项目约束、命令、关键文件和架构摘要 |
| [STATE_SPEC.md](src/agent/state/STATE_SPEC.md) | 全局状态字段 ownership 与权限矩阵 |
| [Research ARCHITECTURE.md](src/agent/nodes/research/ARCHITECTURE.md) | 调研子图、检索、Critic、Hash 持久化 |
| [Spatial_DB_Spec.md](src/database/postgis/Spatial_DB_Spec.md) | PostGIS / pgRouting 数据库规格 |
| [TEST_MANIFEST.md](test/TEST_MANIFEST.md) | 测试覆盖矩阵与 CI test clusters |
| [docs/DOCKER.md](docs/DOCKER.md) | Docker 构建与部署说明 |

## Development Notes

- 实验性改动使用 git worktree，不直接污染 `dev`。
- 所有 LangGraph 节点是 async，pytest 使用 `asyncio-mode=strict`。
- Commit message 不使用 `@` 符号。
- 变更 `TravelState` 字段时必须同步更新 [STATE_SPEC.md](src/agent/state/STATE_SPEC.md)。
- 新增测试时遵循 P0/P1/P2 priority marker，并维护 [TEST_MANIFEST.md](test/TEST_MANIFEST.md)。

## License

MIT
