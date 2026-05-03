<p align="center">
  <img src="assets/GeoTrave.png" alt="GeoTrave Logo" width="400" />
</p>

# GeoTrave — Multi-Agent Travel Planning Engine

GeoTrave 是一个基于 LangGraph 的多智能体旅行规划系统。用户通过自然语言对话渐进式表达需求，系统经过安全过滤、需求提取、空间检索、交互推荐，最终生成个性化行程方案。

## Quick Start

```bash
# 1. 安装依赖 (Python 3.12+)
uv sync

# 2. 配置 LLM 与数据库
cp .env.example .env   # 填写 GLOBAL_MODEL_API_KEY 等

# 3. 启动 PostGIS (Docker)
cd database/postgis
docker compose up -d db
docker compose --profile init run --rm db-init   # 首次 OSM 导入

# 4. 启动 API
uv run python -m src.main   # → http://localhost:8000/docs

# 5. 调试 UI (可选)
uv run streamlit run test/test_ui.py
```

OSM 数据默认使用北海道 (`hokkaido-latest.osm.pbf`)，可替换为任意 [Geofabrik](https://download.geofabrik.de/) 地区数据。

## Commands

```bash
uv sync                              # 安装依赖
uv run python -m src.main            # 启动开发服务器
uv run pytest test/ -v --asyncio-mode=strict          # 全部测试
uv run pytest test/unit/ -v --asyncio-mode=strict     # 单元测试
uv run streamlit run test/test_ui.py                   # 调试 UI
```

## Architecture

```
user input → gateway → analyst → manager → (research_loop → manager | recommender → reply | planner → reply)
                │                     ↑
                └── unsafe ──→ reply ┘
```

| 节点 | 职责 |
|---|---|
| **Gateway** | 安全网关 — 意图分类 (legal/malicious/chitchat) + PII 脱敏 |
| **Analyst** | 需求分析 — 提取 UserProfile，判定信息完备性 |
| **Manager** | 总调度官 — LLM 驱动路由，读 trace_history/research 信号决策 |
| **Research Loop** | 调研子图 — QueryGenerator → Search → Critic ⇄ QueryGenerator → Hash |
| **Recommender** | 推荐引擎 — 目的地/住宿/餐饮三维度渐进式推荐 |
| **Planner** | 行程规划 — 基于调研+推荐生成逐日行程方案 |
| **Reply** | 对话出口 — 收集缺失信息或呈现最终计划 |

> 拓扑细节与路由逻辑见 [src/agent/graph.py](src/agent/graph.py)，Prompt 设计见 [src/utils/prompt.py](src/utils/prompt.py)。

## Tech Stack

| 层 | 技术 |
|---|---|
| Agent 框架 | LangGraph + LangChain |
| LLM | ChatOpenAI 通用接口 (DeepSeek / OpenAI / 任意兼容 provider) |
| 地理空间 | PostGIS 3.5 + pgRouting 3.8 on PostgreSQL 17 |
| 数据源 | OpenStreetMap (osm2pgsql 导入) |
| API | FastAPI + uvicorn |
| 持久化 | SQLite Checkpointer (LangGraph 状态) + PostgreSQL (地理数据) |
| 部署 | Docker Compose + GitHub Actions CD |
| 测试 | pytest + pytest-asyncio (strict mode) |

## Project Structure

```
src/
├── agent/
│   ├── graph.py                  # LangGraph 拓扑定义
│   ├── state/                    # TravelState + Pydantic schema
│   └── nodes/
│       ├── gateway/              # 安全网关
│       ├── manager/              # LLM 路由调度
│       ├── analyst/              # 需求提取
│       ├── research/             # 调研子图 (QG / Search / Critic / Hash)
│       ├── recommender/          # 渐进式推荐
│       ├── planner/              # 行程规划
│       └── reply/                # 对话回复
├── api/                          # FastAPI 路由 + schema
├── database/
│   ├── checkpointer/             # SQLite 状态持久化
│   └── retrieval_db.py           # PostgreSQL JSONB 检索存储
└── utils/                        # LLM Factory, Prompt, Logger

database/postgis/
├── Dockerfile.postgis            # pgRouting + osm2pgsql 镜像
├── docker-compose.yml            # db + db-init 服务
├── init/                         # PostgreSQL 扩展初始化
├── scripts/                      # 视图/索引/拓扑 SQL
└── osm_data/                     # OSM .pbf 文件 (gitignored)

test/
├── unit/                         # 单元测试 (166 tests, 89 P0)
├── integration/                  # 集成测试 (需 PostGIS)
└── TEST_MANIFEST.md              # 测试覆盖矩阵
```

## Documentation

| 文档 | 内容 |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | 开发计划与完成状态 |
| [test/TEST_MANIFEST.md](test/TEST_MANIFEST.md) | 测试覆盖矩阵 (166 tests) |
| [src/database/postgis/Spatial_DB_Spec.md](src/database/postgis/Spatial_DB_Spec.md) | PostGIS 空间数据库规格 |
| [docs/local/stash/project_goal.md](docs/local/stash/project_goal.md) | 项目最终目标 |
| [docs/local/stash/development_plan.md](docs/local/stash/development_plan.md) | 原始分阶段开发计划 |

## License

MIT
