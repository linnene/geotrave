# GeoTrave 测试项目说明

本项目采用分层测试架构，旨在确保旅行规划智能体的稳定性、准确性和鲁棒性。

## 1. 测试目录结构

- [test/unit/](test/unit/): **单元测试**。针对单个节点逻辑、工具函数进行 Mock 测试，不依赖外部 API。
### 集成测试 ([test/integration/](test/integration/))
- **API 接口验证 ([test_api.py](test/integration/test_api.py))**:
    - **Chat 端点**: 验证会话生命周期、输入合法性校验及状态机返回。
    - **RAG 端点**: 验证向量库统计、大规模文档批量插入及语义检索召回。
    - **错误处理**: 验证非法文件上传过滤、空消息拦截及系统级异常捕获。
- **并发压力测试 ([test_concurrency.py](test/integration/test_concurrency.py))**:
    - 多线程下不同 `thread_id` 的隔离性验证。

### 效果评估 (E2E) ([test/eval/](test/eval/))

### 单元测试 ([test/unit/test_nodes.py](test/unit/test_nodes.py))
- **Router 节点**:
    - 意图分类识别（如 `new_destination`）。
    - 恶意 Prompt 注入拦截与拒答逻辑。
- **Analyzer 节点**:
    - 结构化需求提取（目的地、天数、预算等）。
    - 相对日期推算逻辑验证。
- **Researcher 节点**:
    - 异步检索计划生成。
    - 多目的地天气检索触发逻辑。
    - 检索结果的流式汇总。

### 工具测试 ([test/unit/test_tools.py](test/unit/test_tools.py))
- **天气工具 (Open-Meteo)**:
    - 地理编码转换。
    - 7天预报解析与行程日期匹配标记。
- **搜索工具 (DuckDuckGo)**:
    - 网络波动下的重试机制。
    - 结果解析与结构化。
- **本地知识库**:
    - 向量库检索集成验证。
- **质检过滤 (Filter)**:
    - 使用 LLM 剔除无关营销信息的逻辑验证。

## 3. 如何运行测试

### 运行所有单元测试
```powershell
.venv/Scripts/python.exe -m pytest test/unit/
```

### 运行特定测试文件
```powershell
.venv/Scripts/python.exe -m pytest test/unit/test_nodes.py
```

### 运行效果评估 (E2E)
```powershell
.venv/Scripts/python.exe -m pytest test/eval/test_agent_workflow.py
```

## 4. 后续规划
- 完善 `test/integration/` 下的跨节点状态流转测试。
- 增加针对 `Recommender` 节点（行程生成）的格式校验与偏好匹配测试。
- 自动化生成测试覆盖率报告。
