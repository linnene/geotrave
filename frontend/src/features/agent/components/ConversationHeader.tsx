import { Menu } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { SessionSummary } from '@/lib/api/sessions'

type ConversationHeaderProps = {
  activeSession?: SessionSummary
  latestUserInput: string
  onOpenSidebar: () => void
}

export function ConversationHeader({
  activeSession,
  latestUserInput,
  onOpenSidebar,
}: ConversationHeaderProps) {
  const displayText = latestUserInput || activeSession?.last_message || 'Start by describing your trip.'

  return (
    <header className="flex min-h-16 items-center gap-4">
      <section className="flex min-w-0 flex-1 items-center justify-end gap-4">
        <div className="min-w-0 flex-1 rounded-md bg-[#aeb6b2] px-5 py-3 text-right text-sm font-medium text-white shadow-sm">
          <p className="truncate">{displayText}</p>
        </div>
        <div className="size-12 shrink-0 rounded-full bg-[#9ca5a0]" aria-label="User profile" />
        <Button
          type="button"
          variant="secondary"
          size="icon"
          className="shrink-0"
          aria-label="Open plan conversations"
          onClick={onOpenSidebar}
        >
          <Menu className="size-5" aria-hidden="true" />
        </Button>
      </section>
    </header>
  )
}
