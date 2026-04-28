<p align="">
  <img src="assets/GeoTrave.png" alt="GeoTrave Logo" width="400" />
</p>

# GeoTrave — Multi-Agent Travel Planning Engine

GeoTrave 是一个基于 **LangGraph** 的多智能体旅行规划系统，通过 Manager 编排的 Agent 拓扑结构将自然语言对话转化为结构化的旅行调研与行程方案。

## Architecture

```
gateway → manager → (analyst | query_generator → search | reply) → manager → ...
```

| 节点 | 职责 |
|---|---|
| **Gateway** | 安全网关 — 意图分类 (legal/malicious/chitchat) + PII 脱敏 |
| **Manager** | 总调度官 — LLM 驱动的路由决策，读取状态信号决定下一步 |
| **Analyst** | 需求分析 — 从对话中提取结构化 UserProfile，判定信息完备性 |
| **QueryGenerator** | 研究规划 — 基于画像和上下文制定多维度检索方案，选择工具 |
| **Search** | 工具执行 — 无 LLM，按 SearchTask 调度 PostGIS/web 工具 |
| **Reply** | 对话出口 — 生成人情味回复，循循善诱收集缺失信息 |

后链节点 **Recommender** / **Planner** 处于设计阶段，当前路由至 Reply。

## Tech Stack

| 层 | 技术 |
|---|---|
| **Agent 框架** | LangGraph + LangChain |
| **LLM** | ChatOpenAI 通用接口（DeepSeek / OpenAI / 任意兼容 provider） |
| **地理空间** | PostGIS 3.5 + pgRouting 3.8 on PostgreSQL 17 |
| **数据源** | OpenStreetMap (osm2pgsql 导入) |
| **API** | FastAPI + uvicorn |
| **持久化** | SQLite Checkpointer（LangGraph 状态） + PostgreSQL（地理数据） |
| **部署** | Docker Compose（db + api + ui），GitHub Actions CD |
| **测试** | pytest + pytest-asyncio (strict mode) |

## Quick Start

### 前置条件

- Python 3.12+
- [uv](https://astral.sh/uv)
- Docker（运行 PostGIS）

### 1. 启动 PostGIS 数据库

```bash
cd database/postgis
docker compose up -d db
```

首次使用需导入 OSM 数据（仅一次）：

```bash
# 下载 OSM 数据
mkdir -p osm_data
wget -P osm_data https://download.geofabrik.de/asia/japan/hokkaido-latest.osm.pbf

# 导入
docker compose --profile init run --rm db-init
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

必填项：

```bash
# LLM
GLOBAL_MODEL_API_KEY=your_api_key
GLOBAL_MODEL_BASE_URL=https://api.deepseek.com/v1
GLOBAL_MODEL_ID=deepseek-chat

# PostGIS (本地开发默认即可)
POSTGIS_DSN=postgresql://geotrave:geotrave_dev@localhost:5432/geotrave
```

### 3. 安装依赖并启动

```bash
uv sync
uv run python -m src.main
```

API 运行在 `http://localhost:8000`，访问 `/docs` 查看 Swagger。

### 4. 调试 UI（可选）

```bash
uv run streamlit run test/test_ui.py
```

## Testing

```bash
# 全部测试
uv run pytest test/ -v --asyncio-mode=strict

# 仅单元测试
uv run pytest test/unit/ -v --asyncio-mode=strict

# 仅 P0
uv run pytest test/ -m "priority('P0')" -v --asyncio-mode=strict
```

集成测试需要运行中的 PostGIS，`POSTGIS_DSN` 为空时自动跳过。

## Deployment

推送到 `master` 分支触发 GitHub Actions CD：

1. **构建**: `geotrave-db` / `geotrave-api` / `geotrave-ui` 三个镜像
2. **推送**: Docker Hub
3. **部署**: SSH → 服务器 `docker compose up -d`（数据卷不清空）

首次部署后需在服务器上手动导入 OSM（仅一次）：

```bash
cd /home/geotrave
docker compose --profile init run --rm db-init
```

## Repository Structure

```
src/
├── agent/
│   ├── graph.py              # LangGraph StateGraph 拓扑
│   ├── state/                # TravelState + Pydantic schema
│   └── nodes/
│       ├── gateway/          # 安全网关
│       ├── manager/          # LLM 路由调度
│       ├── analyst/          # 需求提取
│       ├── query_generator/  # 研究方案规划
│       ├── search/           # 工具执行 + @register_tool
│       └── reply/            # 对话回复
├── api/                      # FastAPI 路由 + schema
├── database/
│   ├── checkpointer/         # SQLite 状态持久化
│   └── postgis/              # asyncpg 连接池
└── utils/                    # LLM Factory, Prompt, Logger

database/
├── postgis/                  # Dockerfile + SQL 脚本 + compose
│   ├── init/                 # PostgreSQL 扩展初始化
│   ├── scripts/              # 视图/索引/拓扑 SQL
│   └── osm_data/             # OSM 数据文件 (gitignored)
└── checkpointer/             # SQLite checkpoint (gitignored)

test/
├── unit/                     # 单元测试（目录镜像 src 结构）
├── integration/              # 集成测试（需 PostGIS）
└── TEST_MANIFEST.md          # 测试覆盖矩阵

.github/workflows/
├── Agent-node-test.yml       # CI — 测试
└── cd.yml                    # CD — 构建 + 部署
```

## Documentation

- **[PLAN.md](docs/PLAN.md)** — 下一步开发计划
- **[STASH.md](docs/STASH.md)** — 搁置工作清单
- **[TEST_MANIFEST.md](test/TEST_MANIFEST.md)** — 测试覆盖矩阵
- **[Spatial_DB_Spec.md](src/database/Spatial_DB_Spec.md)** — PostGIS 地理空间架构规格
