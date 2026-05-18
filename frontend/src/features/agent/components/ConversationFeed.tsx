import type { ChatMessage } from '@/features/agent/types'

type ConversationFeedProps = {
  error?: string
  messages: ChatMessage[]
}

export function ConversationFeed({ error, messages }: ConversationFeedProps) {
  return (
    <section className="min-h-0 flex-1 overflow-y-auto rounded-md bg-[#c8cecb] p-5">
      {error && (
        <div className="mb-4 rounded-md border border-destructive/40 bg-white/70 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {messages.length === 0 && (
        <div className="flex min-h-[360px] items-center justify-center text-center">
          <div className="max-w-md">
            <p className="text-lg font-semibold">Ready for a travel request</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Send a prompt to start the non-streaming Agent workflow.
            </p>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {messages.map((message) => (
          <article
            key={message.id}
            className={`max-w-[50%] rounded-2xl px-4 py-3 text-sm leading-6 max-sm:max-w-[85%] ${
              message.role === 'user'
                ? 'ml-auto bg-[#aeb6b2] text-white'
                : 'bg-white/75 text-foreground'
            }`}
          >
            {message.content}
          </article>
        ))}
      </div>
    </section>
  )
}
