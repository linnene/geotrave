import { useState } from 'react'

import { AppSidebar } from '@/components/layout/AppSidebar'
import { MainWorkspace } from '@/features/agent/MainWorkspace'
import { useAgentWorkspace } from '@/features/agent/useAgentWorkspace'
import { cn } from '@/lib/utils'

export function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const agent = useAgentWorkspace()

  return (
    <main className="min-h-screen bg-[#edf1ef] text-foreground">
      <div
        className={cn(
          'grid min-h-screen w-full bg-[#f4f6f5] transition-[grid-template-columns] duration-300 ease-out',
          isSidebarOpen ? 'grid-cols-[280px_minmax(0,1fr)]' : 'grid-cols-[0px_minmax(0,1fr)]',
        )}
      >
        <AppSidebar
          isOpen={isSidebarOpen}
          sessions={agent.state.sessions}
          activeSessionId={agent.state.sessionId}
          isLoading={agent.state.sessionsLoading}
          onCreateSession={agent.createNewSession}
          onSelectSession={(sessionId) => {
            agent.selectSession(sessionId)
            setIsSidebarOpen(false)
          }}
          onClose={() => setIsSidebarOpen(false)}
        />
        <MainWorkspace
          activeSession={agent.activeSession}
          state={agent.state}
          onOpenSidebar={() => setIsSidebarOpen(true)}
          onSendMessage={agent.sendMessage}
        />
      </div>
    </main>
  )
}
