import { Compass, MessageSquarePlus, MessageSquareText, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { SessionSummary } from '@/lib/api/sessions'
import { cn } from '@/lib/utils'

type AppSidebarProps = {
  isOpen: boolean
  sessions: SessionSummary[]
  activeSessionId: string
  isLoading: boolean
  onCreateSession: () => void
  onSelectSession: (sessionId: string) => void
  onClose: () => void
}

function formatDate(value: string) {
  if (!value) {
    return 'No activity'
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function AppSidebar({
  isOpen,
  sessions,
  activeSessionId,
  isLoading,
  onCreateSession,
  onSelectSession,
  onClose,
}: AppSidebarProps) {
  return (
    <div className="min-h-screen overflow-hidden">
      <aside
        className={cn(
          'flex h-full w-[280px] flex-col border-r border-border bg-[#d8dedb] transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(105, 115, 110, 0.34) 1px, transparent 1px)',
          backgroundSize: '18px 18px',
        }}
      >
        <div className="h-60 border-b border-border bg-[#8e9792]/90 px-5 py-5 text-white">
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

        <div className="border-b border-border px-4 py-4">
          <Button type="button" className="w-full" onClick={onCreateSession} disabled={isLoading}>
            <MessageSquarePlus className="size-4" aria-hidden="true" />
            New plan
          </Button>
        </div>

        <nav className="flex-1 space-y-2 overflow-y-auto px-4 py-5" aria-label="Plan conversations">
          {sessions.length === 0 && (
            <p className="px-3 text-sm text-muted-foreground">
              {isLoading ? 'Loading plans...' : 'No plan conversations yet.'}
            </p>
          )}

          {sessions.map((session) => (
            <button
              key={session.session_id}
              type="button"
              onClick={() => onSelectSession(session.session_id)}
              className={cn(
                'flex w-full items-start gap-3 rounded-md px-3 py-3 text-left transition-colors',
                session.session_id === activeSessionId
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-background/70 hover:text-foreground',
              )}
            >
              <MessageSquareText className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold">{session.title}</span>
                <span className="mt-1 block line-clamp-2 text-xs leading-5">
                  {session.summary || session.last_message || 'No summary yet'}
                </span>
                <span className="mt-2 block text-xs">{formatDate(session.updated_at)}</span>
              </span>
            </button>
          ))}
        </nav>
      </aside>
    </div>
  )
}
