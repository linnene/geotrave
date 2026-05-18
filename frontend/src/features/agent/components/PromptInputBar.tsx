import { useState, type FormEvent } from 'react'
import { ArrowUp, MessageSquareText } from 'lucide-react'

import { Button } from '@/components/ui/button'

type PromptInputBarProps = {
  isLoading: boolean
  onSubmit: (message: string) => Promise<void>
}

export function PromptInputBar({ isLoading, onSubmit }: PromptInputBarProps) {
  const [value, setValue] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = value.trim()

    if (!message || isLoading) {
      return
    }

    setValue('')
    await onSubmit(message)
  }

  return (
    <form
      className="flex min-h-20 items-center gap-3 rounded-md border-2 border-[#8f9692] bg-[#e4e8e6] px-4"
      onSubmit={handleSubmit}
    >
      <MessageSquareText className="size-6 shrink-0 text-[#9ca5a0]" aria-hidden="true" />
      <label className="sr-only" htmlFor="travel-prompt">
        Travel request
      </label>
      <input
        id="travel-prompt"
        className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        disabled={isLoading}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Tell GeoTrave your destination, dates, budget, or preferences..."
        type="text"
        value={value}
      />
      <Button type="submit" size="icon" aria-label="Send travel request" disabled={isLoading}>
        <ArrowUp className="size-5" aria-hidden="true" />
      </Button>
    </form>
  )
}
