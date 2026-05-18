import { Menu } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { SessionSummary } from '@/lib/api/sessions'

type ConversationHeaderProps = {
  activeSession?: SessionSummary
  latestUserInput: string
  onOpenSidebar: () => void
}

export function ConversationHeader({
  onOpenSidebar,
}: ConversationHeaderProps) {
  return (
    <header className="flex min-h-16 items-center gap-4">
      <section className="flex min-w-0 flex-1 items-center justify-end gap-4">
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
