import { useState } from 'react'

import { ConversationHeader } from '@/features/agent/components/ConversationHeader'
import { ConversationFeed } from '@/features/agent/components/ConversationFeed'
import { PlanBoard } from '@/features/agent/components/PlanBoard'
import { PromptInputBar } from '@/features/agent/components/PromptInputBar'
import type { AgentWorkspaceState } from '@/features/agent/types'
import type { SessionSummary } from '@/lib/api/sessions'

type MainWorkspaceProps = {
  activeSession?: SessionSummary
  state: AgentWorkspaceState
  onOpenSidebar: () => void
  onSendMessage: (message: string) => Promise<void>
}

export function MainWorkspace({
  activeSession,
  state,
  onOpenSidebar,
  onSendMessage,
}: MainWorkspaceProps) {
  const [isWorkbenchOpen, setIsWorkbenchOpen] = useState(false)
  const isWorkbenchVisible = state.loading || isWorkbenchOpen

  return (
    <section className="flex min-h-screen min-w-0 flex-1 flex-col">
      <div className="grid min-h-0 flex-1 gap-5 px-5 py-6 sm:px-8 lg:grid-cols-[2fr_1fr] lg:px-10">
        <PlanBoard
          isWorkbenchOpen={isWorkbenchVisible}
          loading={state.loading}
          route={state.route}
          signs={state.signs}
          trace={state.trace}
          onToggleWorkbench={() => setIsWorkbenchOpen(!isWorkbenchVisible)}
        />

        <section className="flex min-h-0 flex-col gap-5">
          <ConversationHeader
            activeSession={activeSession}
            latestUserInput={state.latestUserInput}
            onOpenSidebar={onOpenSidebar}
          />
          <ConversationFeed error={state.error} messages={state.messages} />
          <PromptInputBar isLoading={state.loading} onSubmit={onSendMessage} />
        </section>
      </div>
    </section>
  )
}
