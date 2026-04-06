<h1 align="center">GeoTrave</h1>

**GeoTrave** 是一款多智能体（Multi-Agent）和 RAG（检索增强生成）架构的 AI 旅行规划专家。

---

- **智能分析**: 具备 **历史记忆感知**、**动态日期推算**、**旅行风格自动标签** 及 **硬约束/软偏好分类提取** (Hard/Soft Constraints Analysis) 系统。
- **对话引擎**: 基于 [LangGraph](https://langchain-ai.github.io/langgraph/) 的多 Agent 协作状态机。
- **混合大模型**:
  - 核心大脑 (Chat): **DeepSeek** (`deepseek-chat`)
  - 检索编码 (Embedding): **Google Gemini** (正在迁移至全本地模型)
- **知识检索 (RAG)**: [ChromaDB](https://www.trychroma.com/) 本地向量数据库。
- **对外接口**: [FastAPI](https://fastapi.tiangolo.com/)，支持 **session_id** 实多会话并发。
- **包管理器**: [uv](https://astral.sh/uv) Python 环境管理工具。

![alt text](assets/Gemini_Generated.png)
## Getting Started

### 1. 环境准备

项目使用 `uv` 驱动，请确保您的环境已准备好：

- Python `3.12+`
- [uv](https://astral.sh/uv)（请按照官方安装指南进行安装）

### 2. 环境变量配置

在项目根目录下创建一个 `.env` 文件。为了AGENT的正常运转，请完成在本地完成下列字段填写：
  - `ANALYZER_MODEL_ID`: 负责需求提取。
  - `RESEARCHER_MODEL_ID`: 负责规划搜索词与资料整理。
  - `LOG_LEVEL`: 设置为 `DEBUG` 可在控制台看到完整的 LLM Prompt 交互。
```env
# --- Analyzer (分析师) 模型配置 ---
# 负责提取用户需求、完善画像。建议使用推理能力较强的模型。
ANALYZER_MODEL_API_KEY=your_analyzer_api_key_here
ANALYZER_MODEL_BASE_URL=https://api.deepseek.com
ANALYZER_MODEL_ID=deepseek-chat

# --- Researcher (研究员) 专属模型配置 ---
RESEARCHER_MODEL_API_KEY=your_researcher_api_key_here
RESEARCHER_MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
RESEARCHER_MODEL_ID=gemini-1.5-flash

# --- Planner (规划师) 专属模型配置 (预留) ---
# 负责最终行程生成。
PLANNER_MODEL_API_KEY=your_planner_api_key_here
PLANNER_MODEL_BASE_URL=https://api.openai.com/v1
PLANNER_MODEL_ID=gpt-4o

# --- Embedding (嵌入) 模型配置 ---
# 用于 RAG 向量检索。
EMBEDDING_MODEL_API_KEY=your_embedding_api_key_here
EMBEDDING_MODEL_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=models/text-embedding-004
```

### 3. 安装依赖与启动服务
![alt text](assets/image.png)

```bash
git clone https://github.com/linnene/geotrave.git
cd geotrave
uv sync

# --- 方式 A: 启动 FastAPI 后端服务 ---
./script/set.ps1

# --- 方式 B: 启动 Streamlit 测试 UI (推荐用于调试) ---
# 确保在项目根目录下
uv run streamlit run test_ui.py
```