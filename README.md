<p align="center">
  <img src="assets/GeoTrave.png"/>
</p>

###  基于 LangGragh 的多智能体协作旅行规划师「GeoTrave」![alt text](assets/GeoTrave.ico)
## CORE  
- **对话引擎**：基于 **LangGraph** 构建的多Agent协作机，以期实现较为复杂的自然语言需求分析与任务拆解。包含独立的网关路由节点(Router)用于意图分类与拦截、分析师节点(Analyzer)负责需求提取与合并记忆、研究员节点(Researcher)进行多维度的数据获取。
- **RAG & DuckDuckGo**：整合本地 **ChromaDB** 向量数据库与云端互联网检索，提供结构化的旅游信息与决策支撑点。
- **动态状态白板**：精巧解耦的 `TravelState`，融合持久化记忆节点 (`MemorySaver`) 支持基于会话 (Session) 的多轮渐进式对话机制。
- **轻量前端**：基于 **Streamlit** 的测试面板，能够通过折叠菜单实时查阅状态树变化与大模型运行轨迹节点流转。

![alt text](assets/Gragh.png)

## Getting Started

### 环境准备

项目使用 `uv` 管理

- Python `3.12+`
- [uv](https://astral.sh/uv)（请按照官方安装指南进行安装）

### 环境变量配置

在项目根目录下根据 `.env.example` 模板文件创建一个 `.env` 文件并填写相关字段。
为了AGENT的正常运转，请将这几个Agent Node的LLM完成
  - `ANALYZER_MODEL`: 需求提取。
  - `RESEARCHER_MODEL`: 规划搜索词与资料整理。

### 启动服务

```bash
git clone https://github.com/linnene/geotrave.git

cd geotrave

uv sync

# 默认启动
uv run python src/main.py
```
### StreamLit 测试页面
![alt text](assets/test.png)
```bash
uv run streamlit run test/test_ui.py
```
> UI 界面经过重构，目前支持完整的流式实时输出和折叠式的状态推理路径（包括意图分类、置信度以及模型判断的检索标志）。

###  测试架构
*   **测试框架**：基于 `pytest` + `pytest-asyncio` 实现对 LangGraph 异步工作流的非阻塞断言。
*   **评测维度**：验证 `TravelState` 字段提取准确度、多轮对话记忆累积及 Session 隔离性、Router 拦截逻辑、特定场景下的 `needs_research` 唤起。
*   **本地运行**：
    ```powershell
    # Windows (PowerShell)
    ./script/run_eval.ps1
    # Linux/macOS (Bash)
    ./script/run_eval.sh
    ```


#### GitHub CI 部署与密钥配置
若要在你的 GitHub 仓库中启用 CI，请在仓库的 **Settings > Secrets and variables > Actions** 中添加以下 **Repository Secrets**：

| Secret 名称 | 描述 |
| :--- | :--- |
| `ANALYZER_MODEL_API_KEY` | Analyzer 节点使用的 API Key |
| `RESEARCHER_MODEL_API_KEY` | Researcher 节点使用的 API Key |
| `TAVILY_API_KEY` | Tavily 搜索服务 API Key (用于 Research 节点) |
| `GOOGLE_API_KEY` | Google AI API Key (用于 Embedding 向量模型) |
| `ANALYZER_MODEL_BASE_URL` | (可选) 自定义模型 Base URL |
| `ANALYZER_MODEL_ID` | (可选) 自定义模型 ID (如 gemini-1.5-flash) |

