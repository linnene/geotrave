# PLAN — 下一步开发计划

## 1. 清理未实现工具 Stub

- [ ] 删除 `flight_api` (`tools.py:81-94`) — 抛 `NotImplementedError`，干扰 LLM 工具选择
- [ ] 删除 `hotel_api` (`tools.py:97-111`) — 同上
- [ ] 调整 `web_search` 注册顺序至末尾，降低 LLM 偏好

**文件**: `src/agent/nodes/search/tools.py`

## 2. 地理编码改为渐进截断

- [ ] 删除 `_geocode` 中的硬编码后缀列表 `("駅", "站", "寺", ...)`
- [ ] 改为渐进截断：精确匹配 → ILIKE 模糊 → 逐字去尾重试
- [ ] 更新对应单元测试（`test_geocode_suffix_stripping` → `test_geocode_truncation`）

**文件**: `src/agent/nodes/search/tools.py`, `test/unit/agent/nodes/search/test_tools.py`

## 3. Manager 路由代码级护栏

- [ ] `graph.py:manager_router` 增加强制逻辑：
  - 每次新用户消息的首个路由除了GateWay（安全路由）必须是 `analyst`
  - `is_core_complete=True` 且研究过期时，禁止跳过 `query_generator`
- [ ] 可能需要新增一个标记位（如 `analyst_visited_this_round`）到 ExecutionSigns

**文件**: `src/agent/graph.py`, `src/agent/state/schema.py`

## 4. QueryGenerator 空间上下文感知

- [ ] Prompt 增加规则：利用 `UserProfile.destination` + `Flex` 中的位置信息
- [ ] 引导 LLM 将用户隐含需求（如"想吃海鲜"）结合已知位置生成 spatial_search
- [ ] 确保 `history`（最近几轮对话）正确传入 QueryGenerator 上下文

**文件**: `src/utils/prompt.py`, `src/agent/nodes/query_generator/node.py`

## 5. 验证

- [ ] 单元测试全绿（`test/unit/`）
- [ ] 集成测试全绿（`test/integration/`，需 PostGIS 运行）
- [ ] E2E 手动测试：完整对话 → QueryGenerator 生成 spatial_search + 地理编码成功
