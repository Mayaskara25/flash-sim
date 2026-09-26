import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Line, LineChart, ReferenceLine, ResponsiveContainer } from 'recharts'
import { fmtNumber } from '../format'
import { STATUS_TONE, STATUS_WORD, STAT_STATUS } from '../panels'
import type { AlertCard, SignalView } from '../types'
import { Badge } from '../ui'

const analystPath: Record<string, string> = {
  PX_CHG_5M: 'market-crash', LIQ_RATE: 'liquidations', LAR: 'liquidations',
  INS_FUND_PCT: 'exposure', BAD_DEBT_RATE: 'exposure', NET_EXPOSURE_PCT: 'exposure',
  STBL_PX: 'market-crash', TICKET_RATE: 'risk-response', SENTIMENT: 'risk-response',
}

const STROKE: Record<SignalView['status'], string> = {
  normal: 'var(--sev4-fg)', watch: 'var(--sev4-fg)', warn: 'var(--warn-fg)', critical: 'var(--crit-fg)',
}

/**
 * Backend units are written for logs and CSV (`%fund/min`, `count`,
 * `× baseline`). On a tile next to a 28px number they are noise, so they are
 * shortened here. The full unit stays in the tile's `title`.
 */
function shortUnit(unit: string): string {
  if (unit === 'count') return ''
  if (unit.startsWith('%')) return unit.replace('%fund', '')
  return unit.replace(' baseline', '')
}

/** True when the unit already carries a rate, so the trend must not add one. */
function isRate(unit: string): boolean {
  return unit.includes('/min')
}

/**
 * Tile labels are shortened to the noun the operator acts on. The full
 * backend label stays in the tile's `title` and in Details › Signals, where
 * there is room for it.
 */
function displayLabel(code: string, label: string): string {
  return TILE_LABELS[code] ?? label
}

const TILE_LABELS: Record<string, string> = {
  INS_FUND_PCT: 'Insurance fund',
  PX_CHG_5M: 'Price change (5m)',
  NET_EXPOSURE_PCT: 'Net exposure',
  BAD_DEBT_RATE: 'Bad debt rate',
  NEG_BAL_ACCTS: 'Negative-balance accts',
  ADL_COUNT: 'Auto-deleverage events',
  ORDER_LATENCY_P95: 'Order latency p95',
  SETTLE_FAIL_PCT: 'Settlement failures',
  LP_REJECT_PCT: 'LP rejects',
  UPI_FAIL_PCT: 'UPI failures',
  WDR_QUEUE_RATIO: 'Withdrawal queue',
  RUMOR_MENTIONS: 'Rumor mentions',
}

/**
 * H14: one signal tile, two sizes.
 *
 * `size="lg"` is the main-view tile — the value is `text-stat` (28px), the
 * status is a word in a badge (never colour alone), the trend carries an
 * arrow, and the sparkline keeps its warn/critical threshold lines.
 * `size="sm"` is the same tile at drawer scale (UI_PLAN §3, Signals).
 */
export function SignalCard({ signal, alerts, size = 'lg' }: { signal: SignalView; alerts: AlertCard[]; size?: 'lg' | 'sm' }) {
  const previous = useRef(signal.status)
  const [pulse, setPulse] = useState(false)
  const large = size === 'lg'

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
  const trendText = trend === 0
    ? '→ steady'
    : `${trend > 0 ? '↗' : '↘'} ${fmtNumber(Math.abs(trend))}${shortUnit(signal.unit) && !isRate(signal.unit) ? ` ${shortUnit(signal.unit)}` : ''}/min`
  const status = STAT_STATUS[signal.status]

  // Rule 5: only warn and critical get a colour. Everything else is neutral,
  // so a red or amber tile always means "act on this".
  const tone = status === 'warn' ? 'warn' : status === 'critical' ? 'crit' : 'sev4'
  return <article className={`min-w-0 ${pulse ? 'incident-crossed' : ''}`} style={{
    background: 'var(--surface)', border: '1px solid var(--line)', borderLeft: `4px solid var(--${tone}-fg)`,
    borderRadius: 8, padding: large ? '10px 14px' : '8px 12px',
  }}>
    <div className="flex items-start justify-between gap-2">
      {/* Signal labels are sentences, not eyebrows: uppercase + a narrow
          tile turns "Liquidation rate" into four lines. */}
      <div className="text-body min-w-0 font-semibold leading-tight" style={{ color: 'var(--muted)' }}
        title={`${signal.label} (${signal.unit})`}>{displayLabel(signal.code, signal.label)}</div>
      <Badge tone={STATUS_TONE[signal.status]}>{STATUS_WORD[signal.status]}</Badge>
    </div>
    <div className="mt-1 flex flex-wrap items-baseline gap-x-2">
      <strong className={`${large ? 'text-stat' : 'text-body-lg'} tabular font-bold`} style={{ color: `var(--${tone}-fg)` }}>{fmtNumber(signal.value)}</strong>
      {shortUnit(signal.unit) && <span className="text-body" style={{ color: 'var(--muted)' }}>{shortUnit(signal.unit)}</span>}
    </div>
    <div className="text-body mt-0.5 flex flex-wrap items-center justify-between gap-x-2" style={{ color: 'var(--muted)' }}>
      <span>{trendText}</span>
      {count > 0 && <span className="font-semibold">{count} alert{count === 1 ? '' : 's'}</span>}
    </div>
    <div style={{ height: large ? 34 : 26, marginTop: 6 }} aria-label={`${signal.label} recent history`}>
      {points.length > 1 ? <ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ top: 3, right: 2, bottom: 2, left: 2 }}>
        {signal.thresholds.warn !== null && <ReferenceLine y={signal.thresholds.warn} stroke="var(--warn-fg)" strokeDasharray="3 2" />}
        {signal.thresholds.critical !== null && <ReferenceLine y={signal.thresholds.critical} stroke="var(--crit-fg)" strokeDasharray="3 2" />}
        <Line dataKey="value" type="monotone" stroke={STROKE[signal.status]} strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart></ResponsiveContainer> : <div className="text-body flex h-full items-center" style={{ color: 'var(--muted)' }}>History appears as the scenario runs</div>}
    </div>
    {large && <Link className="text-body mt-0.5 inline-block font-medium underline underline-offset-2" style={{ color: 'var(--ink)' }} to={`/analyst/${analystPath[signal.code] ?? 'overview'}`}>Open analyst view ↗</Link>}
  </article>
}
