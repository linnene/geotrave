<h1 align="center">GeoTrave</h1>

**GeoTrave** 是一款多智能体（Multi-Agent）和 RAG（检索增强生成）架构的 AI 旅行规划专家。

---

- **智能分析**: 具备 **历史记忆感知**、**动态日期推算**、**旅行风格自动标签** 及 **硬约束/软偏好分类提取** (Hard/Soft Constraints Analysis) 系统。
- **对话引擎**: 基于 [LangGraph](https://langchain-ai.github.io/langgraph/) 的多 Agent 协作状态机。
- **混合大模型**:
  - 检索编码 (Embedding): **Google Gemini** (正在迁移至全本地模型)
- **知识检索 (RAG)**: [ChromaDB](https://www.trychroma.com/) 本地向量数据库。
- **对外接口**: [FastAPI](https://fastapi.tiangolo.com/)，支持 **session_id** 实多会话并发。
- **包管理器**: [uv](https://astral.sh/uv) Python 环境管理工具。
- **全维度评测**: 集成 **数据驱动型 Agent 协作测试** (Dimension 2)，支持 **多轮对话历史继承**、**并发会话隔离** 及 **自动化状态机断言**。

![alt text](assets/Gemini_Generated.png)
## Getting Started

### 1. 环境准备

项目使用 `uv` 驱动，请确保您的环境已准备好：

- Python `3.12+`
- [uv](https://astral.sh/uv)（请按照官方安装指南进行安装）

### 2. 环境变量配置

在项目根目录下创建一个 `.env` 文件并填写相关字段。
为了AGENT的正常运转，请完成这几个Agent Node的字段完善
  - `ANALYZER_MODEL`: 负责需求提取。
  - `RESEARCHER_MODEL`: 负责规划搜索词与资料整理。
  - `LOG_LEVEL`: 设置为 `DEBUG` 可在控制台看到完整的 LLM Prompt 交互。

### 3. 安装依赖与启动服务
![alt text](assets/image.png)

```bash
git clone https://github.com/linnene/geotrave.git
cd geotrave
uv sync

# --- 方式 A: 启动 FastAPI 后端服务 ---
./script/set.ps1

# --- 方式 B: 启动 Streamlit 可视化测试 UI (推荐用于调试) ---
uv run streamlit run test/test_ui.py
```

### 4. 自动化评估与测试

自动化评估，已集成至 **CI** 工作流中。

*   **测试框架**：基于 `pytest` + `pytest-asyncio` 实现对 LangGraph 异步工作流的非阻塞断言。
*   **评测维度**：
    *   **Dimension 2 (Workflow)**: 验证 `TravelState` 字段提取准确率、多轮对话记忆累积及 Session 隔离性。
*   **结果要求**：要求测试用例 95% 通过（PASS）。若出现 `FAIL`，通常意味着 LLM 提取逻辑偏差或状态机转移异常。

**运行评测脚本：**
```powershell
# Windows (PowerShell)
./script/run_eval.ps1

# Linux/macOS (Bash)
./script/run_eval.sh
```
