/** Stable console boundary shared by fixture and HTTP modes. */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { incidentApi } from './api'
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

const MOCK = import.meta.env.VITE_INCIDENT_MOCK === '1' || new URLSearchParams(window.location.search).get('mock') === '1'
const SAMPLE_SCENARIOS: ScenarioSummary[] = [
  { id: 'C1', name: 'Black Tuesday', description: 'Price fall → customer panic → liquidation cascade', duration_s: 3600, tags_expected: ['M1', 'I1', 'M2'] },
]

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export function useIncident(): IncidentHook {
  const [fixtureIndex, setFixtureIndex] = useState(0)
  const [state, setState] = useState<IncidentStateDTO | null>(null)
  const [catalogue, setCatalogue] = useState<CatalogueDTO | null>(null)
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>(MOCK ? SAMPLE_SCENARIOS : [])
  const [summary, setSummary] = useState<IncidentSummary | null>(MOCK ? SUMMARY_C1 : null)
  const [busy, setBusy] = useState(false)
  const [stale, setStale] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const lastSuccess = useRef(0)
  const polling = useRef(false)
  const mutating = useRef(false)
  const mutationError = useRef(false)
  const epoch = useRef(0)

  useEffect(() => {
    if (MOCK) return
    let active = true
    lastSuccess.current = Date.now()
    void incidentApi.catalogue().then((data) => { if (active) setCatalogue(data) }).catch((reason: unknown) => { if (active) setError(message(reason)) })
    void incidentApi.scenarios().then((data) => { if (active) setScenarios(data) }).catch((reason: unknown) => { if (active) setError(message(reason)) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (MOCK) return
    let active = true
    const poll = async () => {
      if (!active || document.hidden || polling.current || mutating.current) return
      polling.current = true
      const startedEpoch = epoch.current
      try {
        const response = await incidentApi.state()
        if (active && startedEpoch === epoch.current) {
          setState(response)
          lastSuccess.current = Date.now()
          setStale(false)
          if (!mutationError.current) setError(null)
        }
      } catch (reason) {
        if (active) setError(message(reason))
      } finally {
        polling.current = false
        if (active && Date.now() - lastSuccess.current >= 3000) setStale(true)
      }
    }
    void poll()
    const timer = window.setInterval(() => {
      if (Date.now() - lastSuccess.current >= 3000) setStale(true)
      void poll()
    }, 1000)
    document.addEventListener('visibilitychange', poll)
    return () => { active = false; window.clearInterval(timer); document.removeEventListener('visibilitychange', poll) }
  }, [])

  useEffect(() => {
    if (MOCK || state?.severity.state !== 'RESOLVED') return
    let active = true
    void incidentApi.summary().then((data) => { if (active) setSummary(data) }).catch((reason: unknown) => { if (active) setError(message(reason)) })
    return () => { active = false }
  }, [state?.severity.state])

  const run = useCallback(async (request: () => Promise<IncidentStateDTO>) => {
    if (mutating.current) return
    mutating.current = true
    setBusy(true)
    setError(null)
    mutationError.current = false
    ++epoch.current
    try {
      const response = await request()
      ++epoch.current
      setState(response)
      lastSuccess.current = Date.now()
      setStale(false)
      if (response.severity.state !== 'RESOLVED') setSummary(null)
    } catch (reason) {
      mutationError.current = true
      setError(message(reason))
      throw reason
    } finally {
      mutating.current = false
      setBusy(false)
    }
  }, [])

  const nextFixture = useCallback(async () => { if (MOCK) setFixtureIndex((n) => Math.min(n + 1, SEQUENCE.length - 1)) }, [])
  const mockAdvance = useCallback(async () => { setFixtureIndex((n) => n < 0 ? 4 : Math.min(n + 1, SEQUENCE.length - 1)) }, [])
  const actions = useMemo<IncidentActions>(() => MOCK ? {
    start: async () => { setFixtureIndex(1) },
    reset: async () => { setFixtureIndex(0) },
    inject: async () => { setFixtureIndex(-1) },
    nextFixture,
    clock: mockAdvance, ackAlert: mockAdvance, decideAction: mockAdvance,
    sendTemplate: mockAdvance, dismissTemplate: mockAdvance, addNote: mockAdvance,
    setSeverity: mockAdvance, confirmPending: mockAdvance, reviewLiquidation: mockAdvance,
    clearError: () => setError(null),
  } : {
    start: (body) => run(() => incidentApi.start(body)),
    clock: (body) => run(() => incidentApi.clock(body)),
    reset: () => run(incidentApi.reset),
    ackAlert: (id, body) => run(() => incidentApi.ackAlert(id, body)),
    decideAction: (id, body) => run(() => incidentApi.decideAction(id, body)),
    sendTemplate: (id, body) => run(() => incidentApi.sendTemplate(id, body)),
    dismissTemplate: (id, body) => run(() => incidentApi.dismissTemplate(id, body)),
    addNote: (body) => run(() => incidentApi.addNote(body)),
    setSeverity: (body) => run(() => incidentApi.setSeverity(body)),
    confirmPending: (body) => run(() => incidentApi.confirmPending(body)),
    reviewLiquidation: (body) => run(() => incidentApi.reviewLiquidation(body)),
    inject: (body) => run(() => incidentApi.inject(body)),
    nextFixture,
    clearError: () => { mutationError.current = false; setError(null) },
  }, [mockAdvance, nextFixture, run])

  return { state: MOCK ? (fixtureIndex < 0 ? FIXTURES.emergency : FIXTURES[SEQUENCE[fixtureIndex]]) : state, catalogue, scenarios, summary, mock: MOCK, busy, stale, error, actions }
}
