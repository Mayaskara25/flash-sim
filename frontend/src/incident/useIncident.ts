/**
 * Stable H4 → H6 UI boundary. Components consume {state, catalogue, scenarios,
 * summary, mock, busy, stale, error, actions}. Every action returns Promise<void>
 * and replaces state from its result. H4 uses contract fixtures; H6 supplies
 * polling and HTTP while keeping this public hook shape.
 */
import { useCallback, useMemo, useState } from 'react'
import { FIXTURES, SEQUENCE, SUMMARY_C1 } from './fixtures'
import type {
  ActionDecideBody, AlertAckBody, CatalogueDTO, ClockBody, IncidentStateDTO,
  IncidentSummary, InjectBody, LiquidationReviewBody, NotesBody, PendingConfirmBody,
  ScenarioSummary, SeverityBody, StartBody, TemplateDismissBody, TemplateSendBody,
} from './types'

export type IncidentActions = {
  start: (body: StartBody) => Promise<void>
  clock: (body: ClockBody) => Promise<void>
  reset: () => Promise<void>
  ackAlert: (id: string, body: AlertAckBody) => Promise<void>
  decideAction: (id: string, body: ActionDecideBody) => Promise<void>
  sendTemplate: (id: string, body: TemplateSendBody) => Promise<void>
  dismissTemplate: (id: string, body: TemplateDismissBody) => Promise<void>
  addNote: (body: NotesBody) => Promise<void>
  setSeverity: (body: SeverityBody) => Promise<void>
  confirmPending: (body: PendingConfirmBody) => Promise<void>
  reviewLiquidation: (body: LiquidationReviewBody) => Promise<void>
  inject: (body: InjectBody) => Promise<void>
  nextFixture: () => Promise<void>
  clearError: () => void
}

export type IncidentHook = {
  state: IncidentStateDTO | null
  catalogue: CatalogueDTO | null
  scenarios: ScenarioSummary[]
  summary: IncidentSummary | null
  mock: boolean
  busy: boolean
  stale: boolean
  error: string | null
  actions: IncidentActions
}

const SAMPLE_SCENARIOS: ScenarioSummary[] = [
  { id: 'C1', name: 'Black Tuesday', description: 'Price fall → customer panic → liquidation cascade', duration_s: 3600, tags_expected: ['M1', 'I1', 'M2'] },
]

export function useIncident(): IncidentHook {
  const [fixtureIndex, setFixtureIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const nextFixture = useCallback(async () => { setFixtureIndex((n) => Math.min(n + 1, SEQUENCE.length - 1)) }, [])
  const reset = useCallback(async () => { setFixtureIndex(0) }, [])
  const start = useCallback(async () => { setFixtureIndex(1) }, [])
  const inject = useCallback(async () => { setFixtureIndex(-1) }, [])
  const advance = useCallback(async () => { setFixtureIndex((n) => n < 0 ? 4 : Math.min(n + 1, SEQUENCE.length - 1)) }, [])
  const actions = useMemo<IncidentActions>(() => ({
    start, reset, inject, nextFixture,
    clock: advance, ackAlert: advance, decideAction: advance, sendTemplate: advance,
    dismissTemplate: advance, addNote: advance, setSeverity: advance,
    confirmPending: advance, reviewLiquidation: advance,
    clearError: () => setError(null),
  }), [start, reset, inject, nextFixture, advance])
  return {
    state: fixtureIndex < 0 ? FIXTURES.emergency : FIXTURES[SEQUENCE[fixtureIndex]],
    catalogue: null,
    scenarios: SAMPLE_SCENARIOS,
    summary: SUMMARY_C1,
    mock: true, busy: false, stale: false, error,
    actions,
  }
}
