# GeoTrave

GeoTrave 是一款基于多智能体（Multi-Agent）和 RAG（检索增强生成）架构的 AI 旅行规划专家。
它并非简单地调用大模型聊天，而是通过一个精密协作的“虚拟旅行社”——从需求分析、资料检索到行程编排，为您生动地绘制出可视化的完美旅途。

---

## 核心架构 (Architecture)

本作致力于打造干净、现代、可扩展的工程典范。

- **编排引擎**: [LangGraph](https://langchain-ai.github.io/langgraph/) - 强大的多 Agent 状态机循环。
- **混合大模型**:
  - 核心大脑 (Chat): **DeepSeek** (`deepseek-chat`)
  - 检索编码 (Embedding): **Google Gemini** (`models/gemini-embedding-001`)
- **知识检索 (RAG)**: [ChromaDB](https://www.trychroma.com/) 本地向量数据库。
- **对外接口**: [FastAPI](https://fastapi.tiangolo.com/) 构建高性能 RESTful 路由。
- **包管理器**: [uv](https://astral.sh/uv) 极速的 Python 环境管理工具。

## 📂 项目结构 (Structure)

```text
geotrave/
├── .env                  # (需手动创建) 全局环境变量配置
├── data/
│   └── chroma/           # ChromaDB 向量持久化目录 (自动生成)
├── src/
│   ├── agent/            # 🧠 智能体大脑 (LangGraph)
│   │   ├── nodes/        # 各个独立 Agent 员工 (如 analyzer.py 需求分析师)
│   │   ├── graph.py      # 流水线与车间编排
│   │   └── state.py      # 全局状态“白板”(TravelState)
│   ├── api/              # 🔌 对外接口 (FastAPI Routers)
│   ├── database/         # 💾 数据库与检索逻辑 (ChromaDB)
│   ├── utils/            # 🛠️ 通用工具 (Prompt, Config)
│   └── main.py           # 🚀 主程序入口
└── pyproject.toml        # 项目依赖清单
```

---

## 快速启动 (Getting Started)

### 1. 环境准备

项目使用 `uv` 强力驱动，请确保你的系统环境已准备好：

- Python `3.12+`
- [uv](https://astral.sh/uv)（请按照官方安装指南进行安装）

### 2. 环境变量配置

在项目根目录下创建一个 `.env` 文件。为了混合模型能正常运转，请提供以下凭证：

```env
# 核心对话模型
OPENAI_API_KEY=你的-DEEPSEEK-API-KEY
MODEL_BASE_URL=https://api.deepseek.com
MODEL_ID=deepseek-chat

# 向量检索模型 (Google Gemini)
EMBEDDING_MODEL=models/gemini-embedding-001
EMBEDDING_MODEL_API_KEY=你的-GOOGLE-GEMINI-API-KEY
```

### 3. 安装依赖与启动服务

依托 `uv`，无需手动建立缓慢的虚拟环境：

```bash
# 进入源码目录
cd src

# 启动端点测试对话脚本 (需求分析师交互)
uv run test_analyzer.py

# 启动完整的 FastAPI 接口服务 (支持 Swagger 自动文档)
uv run uvicorn main:app --reload
```

> **API 调试**: 服务启动后，请在浏览器访问 `http://127.0.0.1:8000/docs` 进行图形化接口测试。

---

## ⚠️ 注意事项与边界 (Notices)

- **解析器兼容性**: 为兼容深层 API 特性，我们暂弃了 `with_structured_output()` 的 JSON Schema 强校验，转而采用更加普适稳健的 `PydanticOutputParser` 来约束大模型吐出标准数据格式。
- **模型混合策略**: DeepSeek 暂不提供对外部署的 Embedding 接口，我们采用 Google Gemini 的免费量级向量接口 `models/gemini-embedding-001` 作为 ChromaDB 的底层向量支撑， 这也是生产级 RAG 典型的混合最佳实践。
- **关于数据写入**: 测试脚本 `test_vector.py` 仅演示了硬编码文本如何写入。在实战阶段，系统可挂载外部爬虫抓取的小红书/马蜂窝攻略定期进行知识覆写。

---
> *Crafted with ❤️ by GeoTrave Developer.*
