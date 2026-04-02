# GeoTrave 开发暂存与进度日志 (STASH)

## 📅 当前日期：2026-04-02

### 🚀 今日完成项 (The Milestones)
1. **项目基础设施重构**
   - 确立了标准的 `src-layout` 目录结构，分离了业务逻辑（API）、模型编排（Agent）、数据持久化（Database）以及公共配置（Utils）。
   - 接入 `uv` 包管理器，秒级解析并安装了 FastAPI、LangGraph、ChromaDB 等核心生态依赖。

2. **RAG 向量检索基建初步跑通**
   - 在 `database/vector_db.py` 中封装了基于 ChromaDB 的知识库。
   - 解决了大模型间的异构兼容问题：主模型使用 **DeepSeek**，而向量模型 (Embedding) 最终成功接入并验证了 **Google Gemini (`models/gemini-embedding-001`)**。
   - 提供了 `test_vector.py`，验证了文本写入向量库及相似度检索流程的存通性。

3. **LangGraph 多智能体 (Multi-Agent) 骨架搭建**
   - 设立了状态共享“白板”：`TravelState` (在 `agent/state.py`，隔离循环引用)。
   - **完成【需求分析师】节点 (Analyzer Node)**：
     - 利用 `PydanticOutputParser` 替换强约束（兼容 DeepSeek 尚未开放的 JSON Schema 选项）。
     - 赋予大模型具体的人设（导游小李），通过 `prompt.py` 执行提示词分离。
     - 从历史聊天记录中精准提取了 `destination` (目的地)、`days` (天数) 和 `budget` (预算)，并能在缺失时优雅追问。
     - 开发了独立的 `test_analyzer.py` 终端交互沙盒。

### 🤔 架构考量与下一步计划 (Next Steps Considerations)
**当前图状 (Graph) 进展**：
目前图里只有一条支线 `START -> Analyzer -> END`。

**下一步我们要增加的结构**：
1. **条件边流转 (Conditional Edges)**：
   - 结合小李 (Analyzer) 提取到的 `TravelInfo`，我们需要在图里加上判断：如果关键字段（地、时、钱）存在 `None`，图应该流转回用户端继续追问；如果收集完毕，应该流转到下一步（调研员或规划师）。
2. **构建【资料搜集员】节点 (Researcher Node)**：
   - 它无需对话能力（甚至无需大模型），只需拿白板上的 `destination` 词条，去我们今天写好的 `search_similar_documents(destination)` 里把相关的 RAG 数据（攻略、景点记录）取出来，贴回白板（State）上。
3. **构建【行程规划师】节点 (Planner Node)**：
   - 这是出活的核心。接受完整的需求和 RAG 补充材料，输出最终的 JSON 路线表（经纬度、景点名称等），为前端地图展示提供数据支撑。