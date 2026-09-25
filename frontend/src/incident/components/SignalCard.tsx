import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Line, LineChart, ReferenceLine, ResponsiveContainer } from 'recharts'
import { fmtNumber, signalTone } from '../format'
import type { AlertCard, SignalView } from '../types'

const analystPath: Record<string, string> = {
  PX_CHG_5M: 'market-crash', LIQ_RATE: 'liquidations', LAR: 'liquidations',
  INS_FUND_PCT: 'exposure', BAD_DEBT_RATE: 'exposure', NET_EXPOSURE_PCT: 'exposure',
  STBL_PX: 'market-crash', TICKET_RATE: 'risk-response', SENTIMENT: 'risk-response',
}

export function SignalCard({ signal, alerts }: { signal: SignalView; alerts: AlertCard[] }) {
  const previous = useRef(signal.status)
  const [pulse, setPulse] = useState(false)
  useEffect(() => {
    const levels = { normal: 0, watch: 1, warn: 2, critical: 3 }
    const crossed = levels[signal.status] > levels[previous.current]
    previous.current = signal.status
    if (!crossed) {
      const clear = window.setTimeout(() => setPulse(false), 0)
      return () => window.clearTimeout(clear)
    }
    const start = window.setTimeout(() => setPulse(true), 0)
    const end = window.setTimeout(() => setPulse(false), 5000)
    return () => { window.clearTimeout(start); window.clearTimeout(end) }
  }, [signal.status])
  const related = alerts.filter((alert) => alert.signal === signal.code)
  const count = related.reduce((sum, alert) => sum + alert.count, 0)
  const points = signal.history.map(([t, value]) => ({ t, value }))
  const trend = signal.trend_per_min
  return <article className={`min-w-0 border bg-white p-3 shadow-sm ${pulse ? 'incident-crossed' : ''} ${signalTone[signal.status].split(' ').find((token) => token.startsWith('border-')) ?? 'border-line'}`}>
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0"><div className="text-[11px] font-semibold uppercase tracking-wide text-muted">{signal.label}</div><div className="mt-1 flex items-baseline gap-1.5"><strong className="font-mono text-[22px] tabular text-ink">{fmtNumber(signal.value)}</strong><span className="text-xs text-muted">{signal.unit}</span></div></div>
      <span className={`shrink-0 border px-1.5 py-0.5 text-[10px] font-bold uppercase ${signalTone[signal.status]}`}>{signal.status}</span>
    </div>
    <div className="mt-1 flex items-center justify-between text-[11px] text-muted"><span>{trend === 0 ? '→ steady' : `${trend > 0 ? '↗' : '↘'} ${fmtNumber(Math.abs(trend))} ${signal.unit}/min`}</span>{count > 0 && <span className="font-semibold">{count} alert{count === 1 ? '' : 's'}</span>}</div>
    <div className="mt-2 h-12" aria-label={`${signal.label} recent history`}>
      {points.length > 1 ? <ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ top: 3, right: 2, bottom: 2, left: 2 }}>
        {signal.thresholds.warn !== null && <ReferenceLine y={signal.thresholds.warn} stroke="#b7791f" strokeDasharray="3 2" />}
        {signal.thresholds.critical !== null && <ReferenceLine y={signal.thresholds.critical} stroke="#b44a4a" strokeDasharray="3 2" />}
        <Line dataKey="value" type="monotone" stroke="#334e68" strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart></ResponsiveContainer> : <div className="flex h-full items-center text-[10px] text-muted">History appears as the scenario runs</div>}
    </div>
    <Link className="mt-1 inline-block text-[11px] font-medium text-navy underline underline-offset-2" to={`/analyst/${analystPath[signal.code] ?? 'overview'}`}>Open analyst view</Link>
  </article>
}
