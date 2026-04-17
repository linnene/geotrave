# GeoTrave 测试项目说明

本项目采用分层测试架构，旨在确保旅行规划智能体的稳定性、准确性和鲁棒性。

## 1. 测试目录结构

- [test/unit/](test/unit/): **单元测试**。针对单个节点逻辑、工具函数进行 Mock 测试，不依赖外部 API。
- [test/integration/](test/integration/): **集成测试**。测试多个节点间的状态流转与协作（待完善）。
- [test/eval/](test/eval/): **效果评估**。基于 [dataset.json](test/eval/dataset.json) 的端到端质量评估，用于衡量 LLM 输出的实际业务价值。

## 2. 当前已实现的测试项

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
