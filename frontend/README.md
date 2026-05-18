# GeoTrave 前端

基于 React + TypeScript 的 GeoTrave 多智能体旅行规划系统前端脚手架。

当前前端为 MVP 基础版本，非最终产品界面。它建立了应用外壳、布局边界、样式体系、后端 API 访问层以及非流式 Agent 交互状态模型。

## 当前状态

- 基于 Vite 8、React 19、TypeScript 6、Tailwind CSS 3 和 shadcn/ui 兼容的组件基元构建。
- 左侧规划栏为可折叠布局列。展开时会推开主工作区，而非浮动覆盖其上。
- 主工作区划分为会话头部、Agent 工作台（含规划面板和对话流）、当前节点状态区和提示词输入区。
- 后端 API 集成已对接非流式 `/chat/` 接口，负责提交提示词、存储返回的聊天状态，并渲染回复、节点状态、推荐和行程计划。
- 会话列表已对接 `/sessions/` API。若后端 API 不可用，UI 会降级到临时本地会话并显示错误提示。
- 该前端已合并至 `dev` 分支，不再位于独立 worktree 中。

## 架构

```text
src/
  app/
    App.tsx                       # 顶层组合与侧边栏展开状态
  components/
    layout/AppSidebar.tsx         # 可折叠的规划对话侧边栏
    ui/button.tsx                 # shadcn 风格的通用按钮基元
  features/
    agent/
      MainWorkspace.tsx           # Agent 主交互布局
      types.ts                    # Agent 工作区状态与 UI 消息类型
      useAgentWorkspace.ts        # 非流式聊天/会话状态编排
      components/
        ConversationHeader.tsx    # 最新用户输入展示与侧边栏触发器
        AgentCanvas.tsx           # Agent 工作台 / 结果展示区
        AgentNodeStatus.tsx       # 当前图节点状态块
        ConversationFeed.tsx      # 对话消息流展示
        PlanBoard.tsx             # 规划面板（推荐/行程展示）
        PromptInputBar.tsx        # 底部提示词输入栏
    chat/types.ts                 # 共享的聊天消息类型
  lib/
    api/client.ts                 # JSON 请求辅助函数与 API 错误类型
    api/chat.ts                   # 类型化的聊天端点封装与 Agent 载荷类型
    api/sessions.ts               # 会话元数据端点封装
    config.ts                     # 来自 Vite 环境变量的运行时配置
    utils.ts                      # 共享的 className 合并工具
  styles/
    globals.css                   # Tailwind 基础层与设计令牌
```

## 设计边界

- `App.tsx` 应保持精简。它可以持有应用级状态（如侧边栏可见性），但功能 UI 应归属 `features/`。
- 可复用的通用 UI 基元归属 `components/ui/`。
- 纯布局类共享组件归属 `components/layout/`。
- Agent 专属的界面、面板和工作区状态归属 `features/agent/`。
- API 访问应保持在 `lib/api/` 内；组件不应直接调用 `fetch`。

## 环境隔离

前端依赖安装在 `frontend/` 目录下，与后端 Python 环境完全隔离：

```text
D:\program\geotrave\frontend\node_modules
```

前端命令不要使用 Python `uv` 环境。

## 命令

本机 PowerShell 阻止了 `npm.ps1` 脚本，请使用 `npm.cmd`。所有命令在 `frontend/` 目录下执行。

```powershell
npm.cmd install          # 安装依赖
npm.cmd run dev          # 启动开发服务器 (port 5173)
npm.cmd run build        # 生产构建
npm.cmd run lint         # 代码检查
npm.cmd run preview      # 预览生产构建
```

## 联合调试

前后端需要同时运行才能完整调试。项目根目录已提供 `dev.ps1` 脚本一键启动两边服务，也可分别启动：

```powershell
# 终端 1 — 后端 (port 8000)
cd D:\program\geotrave
uv run python -m src.main

# 终端 2 — 前端 (port 5173)
cd D:\program\geotrave\frontend
npm.cmd run dev
```

Vite 开发服务器已将以下路径代理到后端 `http://localhost:8000`：

```text
/chat       → localhost:8000
/health     → localhost:8000
/sessions   → localhost:8000
```

## API 配置

需要非默认后端地址时，从 `.env.example` 创建 `.env.local`：

```powershell
VITE_API_BASE_URL=http://localhost:8000
```

初始 API 客户端对接：

```text
POST /chat/
```

当前建模的聊天响应字段如下：

```text
reply, session_id, status, route, signs, trace, profile, recommendation, plan
```

会话摘要字段如下：

```text
session_id, title, summary, created_at, updated_at, last_message
```

## 后续工作

- 与 ClaudeCode 后端 `/chat/` 和 `/sessions/` 的变更对齐。
- 实际数据稳定后，增加更丰富的推荐和行程展示。
- 若后端暴露历史消息持久化接口，增加历史记录查询功能。
