import { requestJson } from '@/lib/api/client'

export type ChatRequest = {
  message: string
  session_id: string
}

export type ChatResponse = {
  reply: string
  session_id: string
  status: 'success' | 'error'
  recommendation?: unknown
  plan?: unknown
}

export function sendChatMessage(request: ChatRequest) {
  return requestJson<ChatResponse>('/chat/', {
    method: 'POST',
    body: request,
  })
}
