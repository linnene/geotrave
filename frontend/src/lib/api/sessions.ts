import { requestJson } from '@/lib/api/client'

export type SessionSummary = {
  session_id: string
  title: string
  summary: string
  created_at: string
  updated_at: string
  last_message: string
}

export type CreateSessionRequest = {
  session_id?: string
  title?: string
  summary?: string
}

export type UpdateSessionRequest = Partial<Pick<SessionSummary, 'title' | 'summary' | 'last_message'>>

type ListSessionsResponse = {
  sessions: SessionSummary[]
  count: number
}

function createSessionId() {
  return crypto.randomUUID()
}

export async function listSessions() {
  const response = await requestJson<ListSessionsResponse>('/sessions/')
  return response.sessions
}

export function createSession(request: CreateSessionRequest = {}) {
  return requestJson<SessionSummary>('/sessions/', {
    method: 'POST',
    body: {
      session_id: request.session_id ?? createSessionId(),
      title: request.title,
    },
  })
}

export function updateSession(sessionId: string, request: UpdateSessionRequest) {
  return requestJson<SessionSummary>(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: request,
  })
}

export function deleteSession(sessionId: string) {
  return requestJson<{ status: 'deleted'; session_id: string }>(`/sessions/${sessionId}`, {
    method: 'DELETE',
  })
}
