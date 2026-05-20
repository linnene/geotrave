import { useState } from 'react'

import { AppSidebar } from '@/components/layout/AppSidebar'
import { DemoWorkspace } from '@/features/agent/DemoWorkspace'
import { cn } from '@/lib/utils'

const demoSessions = [
  {
    session_id: 'demo-hangzhou',
    title: '杭州三日自然与美食',
    summary: '西湖西线、良渚、杭帮菜与轻量交通。',
    last_message: '希望交通别太折腾，预算 3000 元。',
    created_at: '2026-05-19T08:30:00.000Z',
    updated_at: '2026-05-19T09:44:00.000Z',
  },
  {
    session_id: 'demo-chengdu',
    title: '成都周末美食线',
    summary: '宽窄巷子之外的本地餐饮与茶馆路线。',
    last_message: '想避开太商业的店。',
    created_at: '2026-05-17T12:20:00.000Z',
    updated_at: '2026-05-18T11:10:00.000Z',
  },
  {
    session_id: 'demo-xiamen',
    title: '厦门亲子慢旅行',
    summary: '海边、短交通、适合小朋友的半日节奏。',
    last_message: '每天活动不要太满。',
    created_at: '2026-05-12T10:00:00.000Z',
    updated_at: '2026-05-12T10:48:00.000Z',
  },
]

export function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(demoSessions[0].session_id)

  return (
    <main className="h-screen overflow-hidden bg-[#edf1ef] text-foreground">
      <div
        className={cn(
          'grid h-screen w-full bg-[#f4f6f5] transition-[grid-template-columns] duration-300 ease-out',
          isSidebarOpen ? 'grid-cols-[280px_minmax(0,1fr)]' : 'grid-cols-[0px_minmax(0,1fr)]',
        )}
      >
        <AppSidebar
          isOpen={isSidebarOpen}
          sessions={demoSessions}
          activeSessionId={activeSessionId}
          isLoading={false}
          onCreateSession={() => setActiveSessionId(demoSessions[0].session_id)}
          onSelectSession={(sessionId) => {
            setActiveSessionId(sessionId)
            setIsSidebarOpen(false)
          }}
          onClose={() => setIsSidebarOpen(false)}
        />
        <DemoWorkspace onOpenSidebar={() => setIsSidebarOpen(true)} />
      </div>
    </main>
  )
}
