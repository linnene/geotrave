import type { AgentRoute, ExecutionSigns, TraceEntry } from '@/lib/api/chat'

type AgentNodeStatusProps = {
  route?: AgentRoute
  signs?: ExecutionSigns
  trace: TraceEntry[]
}

export function AgentNodeStatus({ route, signs, trace }: AgentNodeStatusProps) {
  const latestTrace = trace.at(-1)
  const nodeName = route?.next_node ?? latestTrace?.node ?? 'idle'
  const detail = route?.reason ?? latestTrace?.status ?? 'Waiting for the next user request.'

  return (
    <section className="min-h-20 rounded-md border-2 border-[#b6bcb9] bg-[#e4e8e6] px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Current node
      </p>
      <p className="mt-1 text-base font-semibold">{nodeName}</p>
      <p className="mt-1 line-clamp-2 text-sm leading-5 text-muted-foreground">{detail}</p>
      {signs && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-sm bg-white/60 px-2 py-1">
            core: {signs.is_core_complete ? 'complete' : 'missing'}
          </span>
          <span className="rounded-sm bg-white/60 px-2 py-1">
            research: {signs.research_rounds}
          </span>
          <span className="rounded-sm bg-white/60 px-2 py-1">
            plan: {signs.is_plan_complete ? 'ready' : 'pending'}
          </span>
        </div>
      )}
    </section>
  )
}
