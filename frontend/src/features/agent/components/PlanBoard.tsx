import { AgentCanvas } from '@/features/agent/components/AgentCanvas'
import type { AgentRoute, ExecutionSigns, TraceEntry } from '@/lib/api/chat'

type PlanBoardProps = {
  isWorkbenchOpen: boolean
  loading: boolean
  route?: AgentRoute
  signs?: ExecutionSigns
  trace: TraceEntry[]
  onToggleWorkbench: () => void
}

export function PlanBoard({
  isWorkbenchOpen,
  loading,
  route,
  signs,
  trace,
  onToggleWorkbench,
}: PlanBoardProps) {
  return (
    <aside className="min-h-0 overflow-hidden rounded-md border border-[#b8c0bc] bg-[#e2e7e4]">
      <div
        className="flex h-full min-h-[560px] flex-col gap-4 overflow-y-auto p-5"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(105, 115, 110, 0.28) 1px, transparent 1px)',
          backgroundSize: '18px 18px',
        }}
      >
        <AgentCanvas
          isOpen={isWorkbenchOpen}
          loading={loading}
          route={route}
          signs={signs}
          trace={trace}
          onToggle={onToggleWorkbench}
        />
      </div>
    </aside>
  )
}
