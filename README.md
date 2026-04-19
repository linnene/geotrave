<p align="center">
  <img src="assets/GeoTrave.png" alt="GeoTrave Logo" width="400" />
</p>

# GeoTrave: 基于 LangGraph 的多智能体协作旅行规划师

GeoTrave 是一个基于 [LangGraph](https://github.com/langchain-ai/langgraph) 构建的多智能体(Multi-Agent)旅行规划引擎。通过解耦路由调度、需求分析、意图分类与外部资料检索，实现从自然语言分析到复杂旅行任务拆解的完整工作流。

经过深度重构，项目当前集成了稳定的 FastAPI 后端接口服务、DuckDuckGo 及本地 Chroma 结构化知识检索，并构建了独立隔离的异步测试框架体系。 

## 核心特性 (Features)

- **多节点智能对话引擎**：
  - **Router Node (网关路由)**：负责意图分类与恶意指令拦截，判断用户提供的信息完整度。
  - **Analyzer Node (分析师)**：精准提取并合并用户的旅游意向、限制条件(Avoidances)、预算约束及行程偏好。
  - **Researcher Node (研究员)**：生成检索规划，利用本地知识库与 Web 搜索进行多维数据补充，并定制专属行程。
- **RAG & 外部检索 (Web Search)**：引入本地核心 ChromaDB 向量数据库，并集成了 DuckDuckGo (取代昂贵的第三方 API) 实现动态互联网调研与事实补全。
- **动态状态白板 (TravelState)**：利用图状态共享对话上下文，并联合 LangGraph 持久化记忆节点（MemorySaver）实现完美的多轮渐进式（Multi-turn Session）会话记忆累积机制。
- **Restful API 后端 (FastAPI)**：提供标准化的接口端点，包含 `/api/chat` (主会话推进) 和 `/api/rag` (基于知识库的增删查) 供外部业务无缝调用。
- **轻量大模型调试面板 (Streamlit)**：提供了可视化面板（`test_ui.py`），支持直观监测 Agent 决策流程、路径节点流转及状态树实时的属性抽取结果。

<p align="center">
  <img src="assets/Gragh.png" />
</p>

## 目录结构 (Project Structure)

```text
GeoTrave/
├── docs/                 # 相关计划、重构与评估文档 (PLAN/E2E/STASH)
├── src/                  # 核心服务源码
│   ├── main.py           # FastAPI 服务程序入口
│   ├── agent/            # LangGraph 状态图、路由图与智能节点 (Router/Analyzer/Researcher)
│   ├── api/              # FastAPI 端点路由逻辑及 Pydantic 模型 (Chat / RAG)
│   ├── database/         # 本地持久化与 Chroma 向量数据库核心操作
│   └── utils/            # 配置管理 (config)、日志 (logger) 及核心系统提示词配置 (prompt)
├── test/                 # 高覆盖率自动化异步测试集
│   ├── e2e/              # 端到端测试 (Agent Workflow 逻辑验证集合)
│   ├── integration/      # API 层级端点测试 (依赖集成验证)
│   ├── unit/             # 逻辑单元测试 (Prompts/Nodes/Tools 纯净态 Mock 测试)
│   ├── data/             # 数据夹 (如用于驱动 E2E 验证的 dataset.json)
│   └── conftest.py       # pytest 通用夹具及隔离环境控制
├── script/               # 批处理运维支持脚本
├── assets/               # 静态展示资源资源
└── README.md
```

## 环境准备 (Getting Started)

项目全面升级使用 [uv](https://astral.sh/uv) 进行虚拟环境与包的依赖管理。

### 1. 获取项目并安装依赖

```bash
git clone https://github.com/linnene/geotrave.git
cd geotrave

# 利用 uv 迅速同步项目并装配所有依赖
uv sync
```

### 2. 环境变量配置

在项目根目录下创建一个 `.env` 文件。项目使用动态层级配置策略，可设置通用 LLM 以简化启动项，或是特定为每个节点配备不同的供应商大模型：

```dotenv
# --- 通用大模型兜底配置 (Global Fallback) ---
GLOBAL_MODEL_API_KEY=sk-xxxxxx
GLOBAL_MODEL_BASE_URL=https://api.example.com/v1
GLOBAL_MODEL_ID=gpt-4o-mini # 或 gemini-1.5-pro 等

# --- 特定节点模型配置 (优先级高于全局配置) ---
# ROUTER_MODEL_ID=...
# ANALYZER_MODEL_ID=...
# RESEARCHER_MODEL_ID=...

# --- 向量模型配置 (Embedding & Vector DB) ---
EMBEDDING_MODEL_API_KEY=xxxxxxxx
EMBEDDING_MODEL_BASE_URL=https://api.example.com/v1
EMBEDDING_MODEL=models/text-embedding-004
```

> **提示**：具体支持的所有可配字段均可检查 `src/utils/config.py` 源文件。

### 3. 本地启动 API 后端服务

GeoTrave 提供了一个标准的交互级 API 服务器。

```bash
uv run python src/main.py
```
> 服务默认在 `127.0.0.1:8000` 激活。直接通过 `http://127.0.0.1:8000/docs` 即刻进入内置的 Swagger 互动界面测试各项功能 API。

### 4. 启动 Streamlit 测试 UI

此页面专供开发调试，用于监测当前用户的状态注入、历史上下文积累与 Agent 背后的推理折叠路径。

![测试界面](assets/test.png)

```bash
uv run streamlit run test/test_ui.py
```
*(注意项目结构更新后路径修改为 `test/test_ui.py`)*

## 自动化测试架构 (Testing Architecture)

项目现已重构出基于 `pytest` + `pytest-asyncio` 的完备层级测试体系，以保证代码每次流转时都稳定且一致。

- **Unit (单元组)**：针对各业务纯净态实现逻辑(`test_nodes.py`, `test_tools.py`, `test_prompts.py`)，运用 `AsyncMock` 及 LCEL 补丁规避在线 API 消耗，确保基类正常运作。
- **Integration (集成组)**：借助 FastAPI 的 TestClient 直接攻击 HTTP 路由并完成端点有效性审核。
- **E2E (端到端组)**：围绕 `test_agent_workflow.py` 将模拟对话推入 LangGraph 核心，并在节点末端抽取 `TravelState` 数据，进而比对 `dataset.json` 中的验证集参数预期（可观测各项场景或避雷需求的精准提纯度）。

**运行各层测试**：
```bash
# 激活根目录下所有测试并展示详细内容
uv run python -m pytest test/ -v
```

您亦可用已有预设脚本作全量触发与覆盖：
```powershell
./script/run_eval.ps1  # Windows (PowerShell)
```

