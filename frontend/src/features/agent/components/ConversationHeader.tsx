import { Menu } from 'lucide-react'

import { Button } from '@/components/ui/button'

const latestUserInput = '下个月想去东京 5 天，预算中等，想要交通方便、吃得好。'

type ConversationHeaderProps = {
  onOpenSidebar: () => void
}

export function ConversationHeader({ onOpenSidebar }: ConversationHeaderProps) {
  return (
    <header className="flex min-h-24 items-center gap-4 px-5 py-4 sm:px-8 lg:px-10">
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

      <section className="ml-auto flex min-w-0 max-w-3xl flex-1 items-center justify-end gap-4">
        <div className="min-w-0 rounded-md bg-[#aeb6b2] px-5 py-3 text-right text-sm font-medium text-white shadow-sm">
          <p className="truncate">{latestUserInput}</p>
        </div>
        <div className="size-12 shrink-0 rounded-full bg-[#9ca5a0]" aria-label="User profile" />
      </section>
    </header>
  )
}
