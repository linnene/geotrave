import { ConversationHeader } from '@/features/agent/components/ConversationHeader'
import { AgentCanvas } from '@/features/agent/components/AgentCanvas'
import { AgentNodeStatus } from '@/features/agent/components/AgentNodeStatus'
import { PromptInputBar } from '@/features/agent/components/PromptInputBar'

type MainWorkspaceProps = {
  onOpenSidebar: () => void
}

export function MainWorkspace({ onOpenSidebar }: MainWorkspaceProps) {
  return (
    <section className="flex min-h-screen min-w-0 flex-1 flex-col">
      <ConversationHeader onOpenSidebar={onOpenSidebar} />

      <div className="flex min-h-0 flex-1 flex-col gap-5 px-5 pb-6 sm:px-8 lg:px-10">
        <AgentCanvas />

        <footer className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
          <AgentNodeStatus />
          <PromptInputBar />
        </footer>
      </div>
    </section>
  )
}
