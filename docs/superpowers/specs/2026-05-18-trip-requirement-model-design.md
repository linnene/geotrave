# 旅程需求模型与 Planner 架构调整

日期: 2026-05-18 | 状态: 已确认

## 核心决策

### 1. UserProfile 职责收窄

**改动**: UserProfile 从扁平表单重构为结构化旅程画像，强调多目的地顺序和分段偏好。

**边界**: UserProfile = 用户需求画像，仅供 Planner 参考。不等于最终计划。

**待加字段** (具体设计延后):
- `origin` / `return_to` — 出发/返回城市
- `stops: List[RouteStop]` — 有序停留序列 (city + nights + per-stop interests)

### 2. 独立的 Plan 结构

`plan_data` 由 Planner 独占维护。不与 UserProfile 耦合。具体结构后续单独设计。

### 3. Planner 从一次性终点变为增量编辑器

- **拓扑变化**: `planner → END` → `planner → reply`
- **策略**: 全量重新生成（每次输出完整 Plan），看效果后迭代
- **首次生成**: 不等待全量数据。有目的地+时间即可生成骨架（天+城市分配）
- **修改**: 把现有 Plan + 用户修改要求发给 LLM，输出新版

### 4. 生长阶段

| 阶段 | 触发条件 | Plan 内容 |
|------|---------|----------|
| 骨架 | 目的地 + 时间明确 | 天 + 城市分配，活动为空 |
| 填充 | 用户提活动 / 调研返回 POI | 逐天填充活动 |
| 细化 | 用户对具体天有反馈 | 修改目标天内容 |
| 确认 | 用户明确确认 | 状态标记为 confirmed |

### 5. Manager 路由

Manager 需识别"计划意图"以路由到 Planner:
- 生成请求: "生成行程"、"出个计划"
- 修改请求: "改第三天"、"删掉XX"、"加个午餐"
- 多条规则优先级: 安全 > 计划意图 > 显式搜索 > 推荐 > 首轮调研 > 默认(reply)

### 6. Reply 新增场景

Planner → Reply 需要 `reply_plan` 模板呈现计划变更。

## 暂不处理

- Plan 结构的详细 Pydantic 模型设计
- locked/confirmed 标记机制
- Planner 多轮调用的硬上限

## 不做

- JSON Patch 编辑指令
- Planner 独立路由
- 双模型并存
