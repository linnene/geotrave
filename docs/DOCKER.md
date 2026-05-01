# GeoTrave Docker 部署指南

## 服务清单

| 服务 | 容器名 | 镜像 | 端口 |
|------|--------|------|------|
| PostGIS 数据库 | `geotrave-db` | `teadark/geotrave-db:latest` | `5432` |
| GeoTrave API | `geotrave` | `teadark/geotrave:latest` | `8000` (API) + `8501` (Streamlit) |

数据库镜像基于 `postgis/postgis:17-3.5`，额外安装了 `pgRouting`、`osm2pgsql` 和自定义扩展/视图脚本。

---

## 前置条件

- **Docker** ≥ 24.x + **Docker Compose** ≥ 2.x
- **OSM 数据文件**（`.osm.pbf`），放置在 `OSM_DATA_DIR` 指定的目录中
- **LLM API Key**（DeepSeek / OpenAI / Gemini 等）

---

## 快速开始

### 1. 准备环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```ini
GLOBAL_MODEL_API_KEY=sk-your-key-here
GLOBAL_MODEL_BASE_URL=https://api.deepseek.com
GLOBAL_MODEL_ID=deepseek-chat

DB_PASSWORD=your_secure_password
OSM_DATA_DIR=/path/to/your/osm_data
```

### 2. 选择部署模式

GeoTrave 提供两种部署拓扑：

**模式 A：数据库 + 应用分离（推荐生产环境）**

数据库和应用使用独立 compose 文件，可分别扩缩容：

```bash
# 终端 1：启动数据库
docker compose -f docker-compose.db.yml up -d

# 终端 2（数据库就绪后）：初始化 OSM 数据（仅首次）
docker compose -f docker-compose.db.yml --profile init run db-init

# 终端 3：启动应用
docker compose up -d
```

**模式 B：本地开发（数据库本地运行）**

仅启动应用容器，数据库直接连本机 PostGIS：

```bash
# .env 中设置
POSTGIS_DSN=postgresql://geotrave:geotrave_dev@host.docker.internal:5432/geotrave

docker compose up -d
```

> **Windows 注意**：`host.docker.internal` 在 Docker Desktop 中自动解析；如使用 Podman，改为宿主机的局域网 IP。

---

## 存储卷

### 数据库 (`docker-compose.db.yml`)

| 卷名 | 容器路径 | 说明 |
|------|---------|------|
| `pgdata` | `/var/lib/postgresql/data` | PostgreSQL 持久化数据（命名卷） |
| OSM 数据目录 | `/osm_data:ro` | `.osm.pbf` 源文件（只读 bind mount） |

### 应用 (`docker-compose.yml`)

| 卷名 | 容器路径 | 说明 |
|------|---------|------|
| `checkpoints` | `/app/database/checkpointer` | SQLite checkpoint 文件（命名卷） |
| `chrome_profile` | `/app/data/chrome_profile` | 浏览器反爬指纹 Profile（命名卷） |
| `.env` | `/app/.env:ro` | 配置文件（只读 bind mount） |

> **checkpoints 卷**：包含 LangGraph 对话状态，丢失会导致所有进行中的会话中断。建议定期备份。

---

## 初始化步骤详解

### 首次 OSM 数据导入

```bash
# 1. 启动数据库
docker compose -f docker-compose.db.yml up -d

# 2. 等待健康检查通过
docker ps --filter "name=geotrave-db" --format "{{.Status}}"

# 3. 执行初始化（导入 OSM + 创建视图/索引）
docker compose -f docker-compose.db.yml --profile init run db-init
```

`db-init` 服务会依次执行：
1. 使用 `osm2pgsql` 导入 `/osm_data/*.osm.pbf`（第一个文件 `-c` 建表，后续 `-a` 追加）
2. 运行 `database/postgis/init/01-extensions.sql` — 启用 PostGIS + pgRouting 扩展
3. 运行 `database/postgis/scripts/*.sql` — 创建 `geotrave_poi` 视图、`routing_network` 表、索引

### 更新 OSM 数据

```bash
# 替换 .osm.pbf 文件后重新运行 init profile
docker compose -f docker-compose.db.yml --profile init run db-init
```

---

## 健康检查

```bash
# 数据库
docker exec geotrave-db pg_isready -U geotrave -d geotrave

# 应用（FastAPI 内置 docs 端点，可用于探活）
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
# 预期输出: 200

# 完整对话测试
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "health-check"}'
```

---

## 常用运维命令

```bash
# 查看日志
docker compose logs -f app
docker compose -f docker-compose.db.yml logs -f db

# 重启服务
docker compose restart app

# 进入容器调试
docker exec -it geotrave bash

# 数据库备份
docker exec geotrave-db pg_dump -U geotrave geotrave > backup.sql

# 数据库恢复
docker exec -i geotrave-db psql -U geotrave geotrave < backup.sql

# 清理全部资源（包括卷）
docker compose down -v
docker compose -f docker-compose.db.yml down -v
```

---

## 环境变量参考

完整列表见 `.env.example`。关键变量：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `GLOBAL_MODEL_API_KEY` | 是 | — | LLM API Key |
| `GLOBAL_MODEL_BASE_URL` | 否 | — | LLM API 地址 |
| `GLOBAL_MODEL_ID` | 否 | — | 模型 ID |
| `DB_PASSWORD` | 否 | `geotrave_dev` | 数据库密码 |
| `POSTGIS_DSN` | 否 | 自动拼接 | 数据库连接串（全量覆盖） |
| `LOG_LEVEL` | 否 | `DEBUG` | 日志等级 |
| `LOG_NO_COLOR` | 否 | `0` | 设为 `1` 禁用 ANSI 颜色 |
| `LOG_FILE` | 否 | — | 日志文件路径 |
| `OSM_DATA_DIR` | 首次 | — | OSM 数据目录（仅 db-init 需要） |

---

## Windows 注意事项

1. **路径格式**：`OSM_DATA_DIR` 使用正斜杠 `/c/Users/...` 或 Docker Desktop 的共享目录
2. **Playwright 浏览器**：Dockerfile 中安装 Chromium，但 WebSearch 工具依赖 Chromium 深度抓取模式，内存 < 2GB 时可能 OOM
3. **ProactorEventLoop**：`src/main.py` 启动时自动检测 Windows 平台并应用修复
4. **换行符**：`.env` 文件使用 LF，PowerShell 编辑时注意（VS Code 右下角切换）
