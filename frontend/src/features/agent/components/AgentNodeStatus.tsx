const currentNode = {
  name: 'manager',
  label: '当前节点',
  detail: '等待路由到调研、推荐或行程规划。',
}

export function AgentNodeStatus() {
  return (
    <section className="min-h-20 rounded-md border-2 border-[#b6bcb9] bg-[#e4e8e6] px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {currentNode.label}
      </p>
      <p className="mt-1 text-base font-semibold">{currentNode.name}</p>
      <p className="mt-1 text-sm leading-5 text-muted-foreground">{currentNode.detail}</p>
    </section>
  )
}
