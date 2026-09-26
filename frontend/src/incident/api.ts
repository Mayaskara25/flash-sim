import type {
  ActionDecideBody,
  AlertAckBody,
  CatalogueDTO,
  ClockBody,
  CopilotBody,
  CopilotReply,
  ExecutionDecisionBody,
  IncidentStateDTO,
  IncidentSummary,
  InjectBody,
  LiquidationReviewBody,
  NotesBody,
  PendingConfirmBody,
  QueueRecordBody,
  ScenarioSummary,
  SeverityBody,
  StartBody,
  TemplateDismissBody,
  TemplateSendBody,
} from './types'

// Backend paths have no /api; the Vite dev proxy strips it (vite.config.ts).
const BASE = '/api/incident'

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    let detail = text || res.statusText
    try {
      const parsed: unknown = JSON.parse(text)
      if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
        const value = (parsed as { detail: unknown }).detail
        detail = typeof value === 'string' ? value : JSON.stringify(value)
      }
    } catch { /* Non-JSON errors still carry their response text. */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const incidentApi = {
  scenarios: () => j<ScenarioSummary[]>('/scenarios'),
  catalogue: () => j<CatalogueDTO>('/catalogue'),
  start: (body: StartBody) => j<IncidentStateDTO>('/start', { method: 'POST', body: JSON.stringify(body) }),
  clock: (body: ClockBody) => j<IncidentStateDTO>('/clock', { method: 'POST', body: JSON.stringify(body) }),
  reset: () => j<IncidentStateDTO>('/reset', { method: 'POST', body: '{}' }),
  state: () => j<IncidentStateDTO>('/state'),
  ackAlert: (id: string, body: AlertAckBody) =>
    j<IncidentStateDTO>(`/alerts/${encodeURIComponent(id)}/ack`, { method: 'POST', body: JSON.stringify(body) }),
  decideAction: (id: string, body: ActionDecideBody) =>
    j<IncidentStateDTO>(`/actions/${encodeURIComponent(id)}/decide`, { method: 'POST', body: JSON.stringify(body) }),
  sendTemplate: (id: string, body: TemplateSendBody) =>
    j<IncidentStateDTO>(`/templates/${encodeURIComponent(id)}/send`, { method: 'POST', body: JSON.stringify(body) }),
  dismissTemplate: (id: string, body: TemplateDismissBody) =>
    j<IncidentStateDTO>(`/templates/${encodeURIComponent(id)}/dismiss`, { method: 'POST', body: JSON.stringify(body) }),
  addNote: (body: NotesBody) => j<IncidentStateDTO>('/notes', { method: 'POST', body: JSON.stringify(body) }),
  setSeverity: (body: SeverityBody) =>
    j<IncidentStateDTO>('/severity', { method: 'POST', body: JSON.stringify(body) }),
  confirmPending: (body: PendingConfirmBody) =>
    j<IncidentStateDTO>('/pending/confirm', { method: 'POST', body: JSON.stringify(body) }),
  reviewLiquidation: (body: LiquidationReviewBody) =>
    j<IncidentStateDTO>('/liquidations/review', { method: 'POST', body: JSON.stringify(body) }),
  decideExecution: (id: string, body: ExecutionDecisionBody) =>
    j<IncidentStateDTO>(`/liquidations/${encodeURIComponent(id)}/decision`, { method: 'POST', body: JSON.stringify(body) }),
  recordQueueEvent: (id: string, body: QueueRecordBody) =>
    j<IncidentStateDTO>(`/queue/${encodeURIComponent(id)}/record`, { method: 'POST', body: JSON.stringify(body) }),
  copilot: (body: CopilotBody) => j<CopilotReply>('/copilot', { method: 'POST', body: JSON.stringify(body) }),
  reportUrl: () => `${BASE}/report.pdf`,
  inject: (body: InjectBody) => j<IncidentStateDTO>('/inject', { method: 'POST', body: JSON.stringify(body) }),
  summary: () => j<IncidentSummary>('/summary'),
}
