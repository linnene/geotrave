# GeoTrave Frontend

React + TypeScript frontend scaffold for the GeoTrave multi-agent travel planning system.

The current frontend is an MVP foundation, not a finished product UI. It establishes the app shell, layout boundaries, styling stack, backend API access layer, and non-streaming Agent interaction state model.

## Current Status

- Built with Vite, React, TypeScript, Tailwind CSS, and shadcn/ui-compatible primitives.
- The left plan bar is a collapsible layout column. Opening it pushes the main workspace instead of floating above it.
- The main workspace is split into user-input display, agent workbench, current-node status, and prompt input areas.
- Backend API integration is wired for the planned non-streaming contract. It submits prompts, stores returned chat state, and renders reply, node status, recommendations, and plans.
- Session list integration is wired against the planned `/sessions/` API. If the backend API is unavailable, the UI falls back to a temporary local session and shows an error.

## Architecture

```text
src/
  app/
    App.tsx                       # Top-level composition and sidebar open state
  components/
    layout/AppSidebar.tsx         # Collapsible plan conversation sidebar
    ui/button.tsx                 # shadcn-style shared button primitive
  features/
    agent/
      MainWorkspace.tsx           # Main agent interaction layout
      types.ts                    # Agent workspace state and UI message types
      useAgentWorkspace.ts        # Non-streaming chat/session state orchestration
      components/
        ConversationHeader.tsx    # Latest user input display and sidebar trigger
        AgentCanvas.tsx           # Agent workbench / result display area
        AgentNodeStatus.tsx       # Current graph node status block
        PromptInputBar.tsx        # Bottom prompt input bar
    chat/types.ts                 # Shared chat message types
  lib/
    api/client.ts                 # JSON request helper and API error type
    api/chat.ts                   # Typed chat endpoint wrapper and Agent payload types
    api/sessions.ts               # Session metadata endpoint wrapper
    config.ts                     # Runtime config from Vite env
    utils.ts                      # Shared className merge helper
  styles/
    globals.css                   # Tailwind base layer and design tokens
```

## Design Boundaries

- `App.tsx` should stay thin. It may own app-level state such as sidebar visibility, but feature UI belongs under `features/`.
- Shared, reusable UI primitives belong under `components/ui/`.
- Layout-only shared components belong under `components/layout/`.
- Agent-specific screens, panels, and workspace state belong under `features/agent/`.
- API access should stay in `lib/api/`; components should not call `fetch` directly.

## Environment Isolation

Frontend dependencies are isolated under this directory:

```powershell
D:\program\geotrave\worktrees\frontend\frontend\node_modules
```

Do not use the Python `uv` environment for frontend commands.

## Commands

PowerShell blocks the `npm.ps1` shim on this machine. Use `npm.cmd`.

```powershell
npm.cmd install
npm.cmd run dev
npm.cmd run build
npm.cmd run lint
```

## API Configuration

Create `.env.local` from `.env.example` when a non-default backend URL is needed.

```powershell
VITE_API_BASE_URL=http://localhost:8000
```

The initial API client targets:

```text
POST /chat/
```

Expected chat response fields are currently modeled as:

```text
reply, session_id, status, route, signs, trace, profile, recommendation, plan
```

Expected session summary fields are:

```text
session_id, title, summary, created_at, updated_at, last_message
```

## Next Work

- Align with ClaudeCode backend changes for `/chat/` and `/sessions/`.
- Add richer recommendation and itinerary presentation once real payloads are stable.
- Add history retrieval if the backend exposes persisted message history per session.
