import { useState } from 'react'

import { AppSidebar } from '@/components/layout/AppSidebar'
import { MainWorkspace } from '@/features/agent/MainWorkspace'
import { cn } from '@/lib/utils'

const plans = [
  {
    id: 'tokyo-spring',
    title: 'Tokyo spring trip',
    summary: 'Family route, 5 days, food and transit focused',
    updatedAt: 'Today',
    active: true,
  },
  {
    id: 'kyoto-weekend',
    title: 'Kyoto weekend',
    summary: 'Temples, ryokan, local dining options',
    updatedAt: 'Yesterday',
    active: false,
  },
  {
    id: 'osaka-food',
    title: 'Osaka food map',
    summary: 'Dotonbori, market stops, late-night meals',
    updatedAt: 'May 15',
    active: false,
  },
]

export function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

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
          plans={plans}
          onClose={() => setIsSidebarOpen(false)}
        />
        <MainWorkspace onOpenSidebar={() => setIsSidebarOpen(true)} />
      </div>
    </main>
  )
}
