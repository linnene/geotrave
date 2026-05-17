import { Map } from 'lucide-react'

const workbenchItems = [
  { label: 'Profile extraction', value: 'Ready' },
  { label: 'Research coverage', value: 'No active run' },
  { label: 'Plan output', value: 'Waiting for request' },
]

export function AgentCanvas() {
  return (
    <section className="flex min-h-[420px] flex-1 flex-col rounded-md bg-[#c8cecb] p-5 sm:min-h-[520px]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Agent workbench</p>
          <h2 className="mt-1 text-xl font-semibold">规划过程与结果展示区</h2>
        </div>
        <Map className="size-6 shrink-0 text-muted-foreground" aria-hidden="true" />
      </div>

      <div className="mt-auto grid gap-3 pt-8 sm:grid-cols-3">
        {workbenchItems.map((item) => (
          <div key={item.label} className="rounded-md bg-white/45 px-4 py-3">
            <p className="text-xs font-medium text-muted-foreground">{item.label}</p>
            <p className="mt-1 text-sm font-semibold">{item.value}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
