import { Compass, MessageSquareText, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type PlanConversation = {
  id: string
  title: string
  summary: string
  updatedAt: string
  active: boolean
}

type AppSidebarProps = {
  isOpen: boolean
  plans: PlanConversation[]
  onClose: () => void
}

export function AppSidebar({ isOpen, plans, onClose }: AppSidebarProps) {
  return (
    <div className="min-h-screen overflow-hidden">
      <aside
        className={cn(
          'flex h-full w-[280px] flex-col border-r border-border bg-[#d8dedb] transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="h-60 border-b border-border bg-[#8e9792] px-5 py-5 text-white">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-md bg-white/20">
                <Compass className="size-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm text-white/75">GeoTrave</p>
                <h1 className="text-lg font-semibold">Travel plans</h1>
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/15"
              aria-label="Close sidebar"
              onClick={onClose}
            >
              <X className="size-5" aria-hidden="true" />
            </Button>
          </div>
        </div>

        <nav className="flex-1 space-y-2 overflow-y-auto px-4 py-5" aria-label="Plan conversations">
          {plans.map((plan) => (
            <button
              key={plan.id}
              type="button"
              className={cn(
                'flex w-full items-start gap-3 rounded-md px-3 py-3 text-left transition-colors',
                plan.active
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-background/70 hover:text-foreground',
              )}
            >
              <MessageSquareText className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold">{plan.title}</span>
                <span className="mt-1 block line-clamp-2 text-xs leading-5">{plan.summary}</span>
                <span className="mt-2 block text-xs">{plan.updatedAt}</span>
              </span>
            </button>
          ))}
        </nav>
      </aside>
    </div>
  )
}
