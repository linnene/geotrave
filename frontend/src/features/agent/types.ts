import type {
  AgentRoute,
  ChatResponse,
  ExecutionSigns,
  PlannerOutput,
  RecommendationData,
  TraceEntry,
} from '@/lib/api/chat'
import type { SessionSummary } from '@/lib/api/sessions'

export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  createdAt: string
}

export type AgentWorkspaceState = {
  sessionId: string
  sessions: SessionSummary[]
  messages: ChatMessage[]
  latestUserInput: string
  route?: AgentRoute
  signs?: ExecutionSigns
  trace: TraceEntry[]
  profile?: unknown
  recommendation?: RecommendationData
  plan?: PlannerOutput
  loading: boolean
  sessionsLoading: boolean
  error?: string
}

export type AgentChatResult = Pick<
  ChatResponse,
  'reply' | 'route' | 'signs' | 'trace' | 'profile' | 'recommendation' | 'plan'
>
