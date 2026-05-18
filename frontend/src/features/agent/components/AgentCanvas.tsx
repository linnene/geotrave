import { ChevronDown, Loader2, Map } from 'lucide-react'

import type { AgentRoute, ExecutionSigns, TraceEntry } from '@/lib/api/chat'
import { cn } from '@/lib/utils'

type AgentCanvasProps = {
  isOpen: boolean
  loading: boolean
  route?: AgentRoute
  signs?: ExecutionSigns
  trace: TraceEntry[]
  onToggle: () => void
}

export function AgentCanvas({
  isOpen,
  loading,
  route,
  signs,
  trace,
  onToggle,
}: AgentCanvasProps) {
  const currentNode = route?.next_node ?? trace.at(-1)?.node ?? 'idle'

  return (
    <section className="rounded-md border border-[#b6bcb9] bg-[#dfe4e1]">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left"
        onClick={onToggle}
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-[#c8cecb]">
            {loading ? (
              <Loader2 className="size-5 animate-spin text-muted-foreground" aria-hidden="true" />
            ) : (
              <Map className="size-5 text-muted-foreground" aria-hidden="true" />
            )}
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-semibold">Agent workbench</span>
            <span className="block truncate text-xs text-muted-foreground">
              {loading ? `Running ${currentNode}` : `Current node: ${currentNode}`}
            </span>
          </span>
        </span>
        <ChevronDown
          className={cn('size-5 shrink-0 text-muted-foreground transition-transform', isOpen && 'rotate-180')}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div className="border-t border-[#c5cbc8] px-4 py-4">

          <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px]">
            <div className="rounded-md bg-white/60 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Route reason
              </p>
              <p className="mt-2 text-sm leading-6">
                {route?.reason ?? 'No route decision has been returned yet.'}
              </p>
            </div>
            <div className="rounded-md bg-white/60 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Signals
              </p>
              <div className="mt-2 space-y-1 text-sm">
                <p>core: {signs?.is_core_complete ? 'complete' : 'missing'}</p>
                <p>research rounds: {signs?.research_rounds ?? 0}</p>
                <p>plan: {signs?.is_plan_complete ? 'ready' : 'pending'}</p>
              </div>
            </div>
          </div>

          {trace.length > 0 && (
            <div className="mt-4 rounded-md bg-white/60 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Recent steps
              </p>
              <div className="mt-2 space-y-2">
                {trace.slice(-5).map((entry) => (
                  <div key={`${entry.node}-${entry.timestamp}`} className="flex justify-between gap-3 text-sm">
                    <span>{entry.node}</span>
                    <span className="text-muted-foreground">
                      {entry.status} · {entry.latency_ms}ms
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
