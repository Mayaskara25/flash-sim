import type {
  Anomaly,
  Cascade,
  Exposure,
  LiqSummary,
  MonteCarlo,
  Overview,
  PositionRow,
  RiskSummary,
  SimParams,
} from '../types'

const BASE = '/api'

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json() as Promise<T>
}

export const api = {
  overview: () => j<Overview>('/overview'),
  params: () => j<SimParams>('/simulation/params'),
  run: (body: Record<string, unknown>) =>
    j<Overview>('/simulation/run', { method: 'POST', body: JSON.stringify(body) }),
  reset: () => j<Overview>('/simulation/reset', { method: 'POST', body: '{}' }),
  demo: (phase: number) =>
    j<Overview>('/simulation/demo', { method: 'POST', body: JSON.stringify({ phase }) }),
  market: () => j<Overview['market']>('/market-state'),
  positions: (q: string) =>
    j<{ rows: PositionRow[]; total_filtered: number; page: number; book_size: number; model_label: string }>(
      `/positions?${q}`,
    ),
  liquidations: () => j<LiqSummary>('/liquidations'),
  exposure: () => j<Exposure>('/exposure'),
  cascade: () => j<Cascade>('/cascade-risk'),
  anomalies: () => j<{ items: Anomaly[]; simulated: boolean }>('/anomalies'),
  risk: () => j<RiskSummary>('/risk-summary'),
  dataStatus: () => j<Record<string, string>>('/data-status'),
  monteCarlo: (body: {
    n_simulations: number
    crash_severity?: number
    volatility?: string
    time_horizon_minutes?: number
  }) => j<MonteCarlo>('/monte-carlo/run', { method: 'POST', body: JSON.stringify(body) }),
}
