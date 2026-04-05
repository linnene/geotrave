<h1 align="center">GeoTrave</h1>

**GeoTrave** 是一款多智能体（Multi-Agent）和 RAG（检索增强生成）架构的 AI 旅行规划专家。

---

本作致力于打造干净、现代、可扩展的工程典范。

- **智能分析**: 具备 **历史记忆感知**、**动态日期推算**、**旅行风格自动标签** 及 **硬约束/软偏好分类提取** (Hard/Soft Constraints Analysis) 系统。
- **对话引擎**: 基于 [LangGraph](https://langchain-ai.github.io/langgraph/) 的多 Agent 协作状态机。
- **混合大模型**:
  - 核心大脑 (Chat): **DeepSeek** (`deepseek-chat`)
  - 检索编码 (Embedding): **Google Gemini** (正在迁移至全本地模型)
- **知识检索 (RAG)**: [ChromaDB](https://www.trychroma.com/) 本地向量数据库。
- **对外接口**: [FastAPI](https://fastapi.tiangolo.com/)，支持 **session_id** 实多会话并发。
- **包管理器**: [uv](https://astral.sh/uv) 极速的 Python 环境管理工具。



## Getting Started

### 1. 环境准备

项目使用 `uv` 驱动，请确保您的环境已准备好：

- Python `3.12+`
- [uv](https://astral.sh/uv)（请按照官方安装指南进行安装）

### 2. 环境变量配置

在项目根目录下创建一个 `.env` 文件。为了AGENT的正常运转，请完成在本地完成下列字段填写：

```env
# 核心对话模型
OPENAI_API_KEY=Your-API-KEY
MODEL_BASE_URL=https://api.base.com
MODEL_ID=chat-model

# 向量检索模型
EMBEDDING_MODEL=models/example-001
EMBEDDING_MODEL_API_KEY= Your-API-KEY
```

### 3. 安装依赖与启动服务

```bash
# 进入源码目录
cd src

# 启动完整的 FastAPI 接口服务 (支持 Swagger 自动文档)
uv run uvicorn main:app --reload
```

> **API 调试**: 服务启动后，请在浏览器访问 `http://127.0.0.1:8000/docs` 进行图形化接口测试。

---
> *Crafted with ❤️ by GeoTrave Developer.*
