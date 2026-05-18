import { useCallback, useEffect, useMemo, useState } from 'react'

import { sendChatMessage } from '@/lib/api/chat'
import { createSession, listSessions, type SessionSummary } from '@/lib/api/sessions'
import type { AgentWorkspaceState, ChatMessage } from '@/features/agent/types'

function nowIso() {
  return new Date().toISOString()
}

function createClientId() {
  return crypto.randomUUID()
}

function createFallbackSession(): SessionSummary {
  const timestamp = nowIso()

  return {
    session_id: createClientId(),
    title: 'Local draft plan',
    summary: 'Session metadata API is unavailable.',
    created_at: timestamp,
    updated_at: timestamp,
    last_message: '',
  }
}

function message(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: createClientId(),
    role,
    content,
    createdAt: nowIso(),
  }
}

function errorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message
  }
  return 'Unexpected request failure'
}

export function useAgentWorkspace() {
  const [state, setState] = useState<AgentWorkspaceState>(() => ({
    sessionId: '',
    sessions: [],
    messages: [],
    latestUserInput: '',
    trace: [],
    loading: false,
    sessionsLoading: true,
  }))

  const activeSession = useMemo(
    () => state.sessions.find((session) => session.session_id === state.sessionId),
    [state.sessionId, state.sessions],
  )

  const refreshSessions = useCallback(async () => {
    setState((current) => ({ ...current, sessionsLoading: true }))

    try {
      const sessions = await listSessions()
      const fallback = sessions[0] ?? (await createSession({ title: 'New travel plan' }))
      const nextSessions =
        sessions.length > 0 ? sessions : [fallback]

      setState((current) => ({
        ...current,
        sessionId: current.sessionId || fallback.session_id,
        sessions: nextSessions,
        sessionsLoading: false,
        error: undefined,
      }))
    } catch (error) {
      const fallback = createFallbackSession()

      setState((current) => ({
        ...current,
        sessionId: current.sessionId || fallback.session_id,
        sessions: current.sessions.length > 0 ? current.sessions : [fallback],
        sessionsLoading: false,
        error: `Session API unavailable: ${errorMessage(error)}`,
      }))
    }
  }, [])

  const createNewSession = useCallback(async () => {
    setState((current) => ({ ...current, sessionsLoading: true, error: undefined }))

    try {
      const session = await createSession({ title: 'New travel plan' })

      setState((current) => ({
        ...current,
        sessionId: session.session_id,
        sessions: [session, ...current.sessions.filter((item) => item.session_id !== session.session_id)],
        messages: [],
        latestUserInput: '',
        route: undefined,
        signs: undefined,
        trace: [],
        profile: undefined,
        recommendation: undefined,
        plan: undefined,
        sessionsLoading: false,
      }))
    } catch (error) {
      const fallback = createFallbackSession()

      setState((current) => ({
        ...current,
        sessionId: fallback.session_id,
        sessions: [fallback, ...current.sessions],
        messages: [],
        latestUserInput: '',
        route: undefined,
        signs: undefined,
        trace: [],
        profile: undefined,
        recommendation: undefined,
        plan: undefined,
        sessionsLoading: false,
        error: `Session API unavailable: ${errorMessage(error)}`,
      }))
    }
  }, [])

  const selectSession = useCallback((sessionId: string) => {
    setState((current) => ({
      ...current,
      sessionId,
      messages: [],
      latestUserInput: '',
      route: undefined,
      signs: undefined,
      trace: [],
      profile: undefined,
      recommendation: undefined,
      plan: undefined,
      error: undefined,
    }))
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    const trimmed = content.trim()
    if (!trimmed) {
      return
    }

    let sessionId = state.sessionId
    let localSessions = state.sessions

    if (!sessionId) {
      const fallback = createFallbackSession()
      sessionId = fallback.session_id
      localSessions = [fallback]
    }

    setState((current) => ({
      ...current,
      sessionId,
      sessions: localSessions.length > current.sessions.length ? localSessions : current.sessions,
      latestUserInput: trimmed,
      loading: true,
      error: undefined,
      messages: [...current.messages, message('user', trimmed)],
    }))

    try {
      const response = await sendChatMessage({ message: trimmed, session_id: sessionId })

      setState((current) => ({
        ...current,
        sessionId: response.session_id,
        messages: response.reply
          ? [...current.messages, message('assistant', response.reply)]
          : current.messages,
        route: response.route,
        signs: response.signs,
        trace: response.trace ?? [],
        profile: response.profile,
        recommendation: response.recommendation,
        plan: response.plan,
        loading: false,
        error: response.status === 'error' ? response.reply : undefined,
      }))

      void refreshSessions()
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: `Chat request failed: ${errorMessage(error)}`,
      }))
    }
  }, [refreshSessions, state.sessionId, state.sessions])

  useEffect(() => {
    void refreshSessions()
  }, [refreshSessions])

  return {
    state,
    activeSession,
    refreshSessions,
    createNewSession,
    selectSession,
    sendMessage,
  }
}
