import { requestJson } from '@/lib/api/client'

export type ChatRequest = {
  message: string
  session_id: string
}

export type AgentRoute = {
  next_node: string
  reason: string
  focus_dimension?: string | null
}

export type ExecutionSigns = {
  is_safe: boolean
  is_core_complete: boolean
  is_recommendation_complete: boolean
  is_plan_complete: boolean
  recommended_dimensions: string[]
  research_rounds: number
}

export type TraceEntry = {
  node: string
  status: string
  latency_ms: number
  detail: Record<string, unknown>
  timestamp: string
}

export type RecommendationItem = {
  name: string
  features: string
  reason: string
  rating: number
}

export type RecommendationOutput = {
  dimension: string
  items: RecommendationItem[]
  strategy: string
  tip: string
}

export type RecommendationData = Record<string, RecommendationOutput>

export type PlanActivity = {
  time: string
  place: string
  type: 'attraction' | 'dining' | 'transport' | 'rest' | 'accommodation'
  description: string
  duration_min: number
  transport?: string | null
}

export type DayPlan = {
  day: number
  date?: string | null
  activities: PlanActivity[]
}

export type PlannerOutput = {
  days: DayPlan[]
  total_budget_estimate?: string | null
  notes: string[]
}

export type ChatResponse = {
  reply: string
  session_id: string
  status: 'success' | 'error'
  route?: AgentRoute
  signs?: ExecutionSigns
  trace?: TraceEntry[]
  profile?: unknown
  recommendation?: RecommendationData
  plan?: PlannerOutput
}

export function sendChatMessage(request: ChatRequest) {
  return requestJson<ChatResponse>('/chat/', {
    method: 'POST',
    body: request,
  })
}
