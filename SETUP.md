# GeoTrave 环境搭建指南

> 适用于首次搭建 GeoTrave 多智能体旅行规划系统的开发者。

## 前提条件

无论选择哪种方式，你都需要：

| 依赖 | 最低版本 | 用途 |
|------|---------|------|
| Python | 3.12+ | 后端运行时 |
| Node.js | 22（推荐） | 前端构建工具链 |
| PostgreSQL + PostGIS | 17 / 3.5 | 空间数据库 |
| Git | 2.x | 代码克隆 |

---

## 方式一：Docker 部署（推荐）

最简路径，无需手动配置 Python/Node/PostGIS 环境。

### 1. 克隆仓库

```bash
git clone <repo-url> geotrave
cd geotrave
```

### 2. 拉取镜像并启动数据库

```bash
# 拉取 PostGIS 数据库镜像
docker compose -f docker-compose.db.yml pull db

# 启动数据库（端口 5432）
docker compose -f docker-compose.db.yml up -d db
```

验证数据库就绪：

```bash
docker exec geotrave-db pg_isready -U geotrave -d geotrave
# 输出: /var/run/postgresql:5432 - accepting connections
```

### 3. 导入 OSM 地图数据（可选）

如需空间搜索功能（POI 查询、路线规划），导入 OpenStreetMap 数据：

```bash
# 准备 .osm.pbf 文件并设置环境变量
export OSM_DATA_DIR=/path/to/your/osm_data

# 运行一次性初始化（--profile init）
docker compose -f docker-compose.db.yml --profile init up db-init
```

如果没有 OSM 数据，空间搜索功能将不可用，但 Agent 对话仍可正常工作。

### 4. 配置环境变量

从模板创建 `.env` 文件，填入你的 LLM API 密钥：

```bash
cp .env.example .env
```

**必须配置的变量：**

```ini
GLOBAL_MODEL_API_KEY=sk-your-api-key-here
GLOBAL_MODEL_BASE_URL=https://api.deepseek.com
GLOBAL_MODEL_ID=deepseek-chat
POSTGIS_DSN=postgresql://geotrave:geotrave_dev@geotrave-db:5432/geotrave
LOG_LEVEL=INFO
```

> **注意**：Docker 环境下的 `POSTGIS_DSN` 主机名是 `geotrave-db`（容器名）。本地开发时改为 `localhost`。

### 5. 启动应用

```bash
# 拉取应用镜像
docker compose pull app

# 启动应用（端口 8000）
docker compose up -d app
```

### 6. 验证

```bash
# 健康检查
curl http://localhost:8000/docs

# 发送测试对话
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "推荐北京3日游", "session_id": "test-001"}'
```

---

## 方式二：本地开发（Clone + uv）

适合需要修改代码或调试的开发者。

### 1. 克隆仓库

```bash
git clone <repo-url> geotrave
cd geotrave
```

### 2. 安装 Python 依赖

项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 依赖，无需手动创建虚拟环境。

```bash
# 安装 uv（如未安装）
pip install uv

# 安装 Python 依赖（自动创建 .venv）
uv sync
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

> **Windows 用户**：PowerShell 可能阻止 `npm.ps1`，请使用 `npm.cmd` 替代 `npm`。

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入配置：

```ini
GLOBAL_MODEL_API_KEY=sk-your-api-key-here
GLOBAL_MODEL_BASE_URL=https://api.deepseek.com
GLOBAL_MODEL_ID=deepseek-chat
POSTGIS_DSN=postgresql://geotrave:geotrave_dev@localhost:5432/geotrave
LOG_LEVEL=DEBUG
```

> 每个 Agent 节点可独立配置模型，详见 `.env.example` 注释。未配置的节点自动回退到全局设置。

### 5. 搭建 PostGIS 数据库

需要安装 PostgreSQL 17 + PostGIS 3.5 扩展。如果本地没有，用 Docker 最方便：

```bash
docker compose -f docker-compose.db.yml up -d db
```

数据库连接信息：
- 主机：`localhost`
- 端口：`5432`
- 数据库：`geotrave`
- 用户：`geotrave`
- 密码：`geotrave_dev`

### 6. 导入 OSM 数据（可选）

```bash
export OSM_DATA_DIR=/path/to/osm_data
docker compose -f docker-compose.db.yml --profile init up db-init
```

### 7. 启动服务

**方式 A：一键启动前后端（推荐）**

打开两个终端：

```bash
# 终端 1 — 后端（端口 8000）
uv run python -m src.main

# 终端 2 — 前端（端口 5173）
cd frontend && npm run dev
```

前端 Vite 开发服务器自动将 `/chat`、`/health`、`/sessions` 请求代理到后端 `localhost:8000`。

**方式 B：仅启动后端 API**

```bash
uv run python -m src.main
# 或
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 8. 验证

```bash
# 后端文档页
open http://localhost:8000/docs

# 前端界面
open http://localhost:5173

# Newman API 集成测试
uv run python script/run_api_tests.py --timeout 120
```

### 9. 运行测试

```bash
# 全部单元测试
uv run pytest test/ -v --asyncio-mode=strict

# 按模块测试
uv run pytest test/unit/agent/nodes/gateway/ -v

# 按优先级测试
uv run pytest test/ -v -m "P0"
```

---

## 启动流程说明

后端启动时按顺序初始化以下组件（日志可见）：

```
1. PostGIS 连接池       → 空间数据库连接
2. Retrieval DB 表      → 研究成果缓存
3. BM25 文档索引        → 系统文档搜索
4. Session 存储         → 会话元数据（SQLite）
5. 浏览器池预热         → Crawl4AI 抓取就绪
```

启动成功后输出 `API Server: Initializing Infrastructure` 系列日志，最后一行类似：

```
Uvicorn running on http://0.0.0.0:8000
```

关闭时自动释放浏览器实例和数据库连接池。

---

## 可选配置

### 单节点模型覆盖

每个 Agent 节点可使用独立模型，在 `.env` 中解开对应注释：

```ini
# 让研究员使用 Gemini
RESEARCHER_MODEL_API_KEY=sk-xxx
RESEARCHER_MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
RESEARCHER_MODEL_ID=gemini-1.5-flash
```

可覆盖的节点：`ANALYST`、`RESEARCHER`、`PLANNER`、`RECOMMENDER`、`CRITIC`、`ROUTER`（Gateway）、`MANAGER`、`DIMENSION_PLANNER`、`REPLY`

### 日志控制

```ini
LOG_LEVEL=DEBUG          # 调试详情
LOG_FILE=logs/app.log    # 输出到文件
LOG_NO_COLOR=1           # 纯文本（CI 环境）
```

### 屏蔽城市列表

```ini
BLOCKED_CITIES=东京,Tokyo,大阪,Osaka
```

---

## 常见问题

### uv sync 报错

确保 Python 版本 ≥ 3.12：

```bash
python --version
```

### 数据库连接失败

检查 PostGIS 容器是否运行：

```bash
docker compose -f docker-compose.db.yml ps
```

### Windows 上 npm 命令不可用

PowerShell 阻止了 `npm.ps1`，使用 `npm.cmd` 代替：

```powershell
npm.cmd install
npm.cmd run dev
```

### 前端代理失败

确保后端先启动在 8000 端口，Vite 代理依赖后端先就绪。

### Playwright 浏览器问题

Linux 下需要安装系统依赖：

```bash
playwright install-deps chromium
playwright install chromium
```
