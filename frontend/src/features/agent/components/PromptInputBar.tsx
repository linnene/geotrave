import { ArrowUp, MessageSquareText } from 'lucide-react'

import { Button } from '@/components/ui/button'

export function PromptInputBar() {
  return (
    <form className="flex min-h-20 items-center gap-3 rounded-md border-2 border-[#8f9692] bg-[#e4e8e6] px-4">
      <MessageSquareText className="size-6 shrink-0 text-[#9ca5a0]" aria-hidden="true" />
      <label className="sr-only" htmlFor="travel-prompt">
        Travel request
      </label>
      <input
        id="travel-prompt"
        className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        placeholder="告诉 GeoTrave 你的目的地、时间、预算或偏好..."
        type="text"
      />
      <Button type="button" size="icon" aria-label="Send travel request">
        <ArrowUp className="size-5" aria-hidden="true" />
      </Button>
    </form>
  )
}
