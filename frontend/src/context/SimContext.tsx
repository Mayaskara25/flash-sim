import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../services/api'
import type { Overview, SimParams } from '../types'

const PHASE_LABELS = [
  'Phase 1 — Normal market',
  'Phase 2 — Price begins falling',
  'Phase 3 — High-leverage positions become at risk',
  'Phase 4 — Liquidations increase',
  'Phase 5 — AI cascade score rises',
  'Phase 6 — Monte Carlo shows severe scenarios',
  'Phase 7 — Risk alert HIGH / CRITICAL',
]

type SimContextValue = {
  overview: Overview | null
  params: SimParams | null
  loading: boolean
  error: string | null
  demoRunning: boolean
  demoPhase: number | null
  demoLabel: string | null
  revision: number
  refresh: () => Promise<void>
  update: (patch: Record<string, unknown>) => Promise<void>
  reset: () => Promise<void>
  startDemo: () => void
  stopDemo: () => void
}

const SimContext = createContext<SimContextValue | null>(null)

export function SimProvider({ children }: { children: ReactNode }) {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [demoRunning, setDemoRunning] = useState(false)
  const [demoPhase, setDemoPhase] = useState<number | null>(null)
  const [revision, setRevision] = useState(0)
  const timer = useRef<number | null>(null)

  const bump = () => setRevision((r) => r + 1)

  const refresh = useCallback(async () => {
    try {
      const ov = await api.overview()
      setOverview(ov)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load simulation')
    } finally {
      setLoading(false)
    }
  }, [])

  const update = useCallback(async (patch: Record<string, unknown>) => {
    setLoading(true)
    try {
      const ov = await api.run(patch)
      setOverview(ov)
      bump()
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const stopDemo = useCallback(() => {
    if (timer.current) window.clearInterval(timer.current)
    timer.current = null
    setDemoRunning(false)
  }, [])

  const reset = useCallback(async () => {
    stopDemo()
    setDemoPhase(null)
    setLoading(true)
    try {
      const ov = await api.reset()
      setOverview(ov)
      bump()
    } finally {
      setLoading(false)
    }
  }, [stopDemo])

  const startDemo = useCallback(() => {
    stopDemo()
    setDemoRunning(true)
    setDemoPhase(0)
    void api.demo(0).then((ov) => {
      setOverview(ov)
      bump()
    })
    let phase = 0
    timer.current = window.setInterval(() => {
      phase += 1
      if (phase > 6) {
        stopDemo()
        setDemoPhase(6)
        return
      }
      setDemoPhase(phase)
      void api.demo(phase).then((ov) => {
        setOverview(ov)
        bump()
      })
    }, 14000)
  }, [stopDemo])

  useEffect(() => {
    void refresh()
    return () => {
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [refresh])

  const value = useMemo<SimContextValue>(
    () => ({
      overview,
      params: overview?.params ?? null,
      loading,
      error,
      demoRunning,
      demoPhase,
      demoLabel: demoPhase == null ? null : PHASE_LABELS[demoPhase],
      revision,
      refresh,
      update,
      reset,
      startDemo,
      stopDemo,
    }),
    [overview, loading, error, demoRunning, demoPhase, revision, refresh, update, reset, startDemo, stopDemo],
  )

  return <SimContext.Provider value={value}>{children}</SimContext.Provider>
}

export function useSim() {
  const ctx = useContext(SimContext)
  if (!ctx) throw new Error('useSim outside provider')
  return ctx
}
