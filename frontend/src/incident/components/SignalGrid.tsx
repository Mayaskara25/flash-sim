import type { AlertCard, SignalView } from '../types'
import { SignalCard } from './SignalCard'

const rank = { critical: 0, warn: 1, watch: 2, normal: 3 }
const coreOrder = ['LIQ_RATE', 'INS_FUND_PCT', 'PX_CHG_5M', 'TICKET_RATE', 'LAR', 'STBL_PX']

/**
 * H14: four big tiles, worst first, and one honest summary line for the rest
 * ("+17 more · all normal" / "· 3 watch"). The full grid lives in
 * Details › Signals, rendered from the same tile at drawer size, so a fact
 * never has two homes (UI_PLAN §3).
 */
export function SignalGrid({ signals, alerts, limit = 4, onMore }: { signals: SignalView[]; alerts: AlertCard[]; limit?: number; onMore?: () => void }) {
  const coreRank = (code: string) => { const index = coreOrder.indexOf(code); return index < 0 ? coreOrder.length : index }
  const sorted = [...signals].sort((a, b) => Number(b.relevant) - Number(a.relevant) || rank[a.status] - rank[b.status] || coreRank(a.code) - coreRank(b.code) || a.code.localeCompare(b.code))
  const primary = sorted.slice(0, limit)
  const rest = sorted.slice(limit)
  const watch = rest.filter((signal) => signal.status === 'watch').length
  const elevated = rest.filter((signal) => signal.status === 'warn' || signal.status === 'critical').length
  const tail = elevated > 0 ? `· ${elevated} elevated` : watch > 0 ? `· ${watch} watch` : '· all normal'
  if (import.meta.env.DEV && primary.length > 4) throw new Error('More than four key signal tiles on the main view')
  return <section aria-label="Key signals">
    <div className="mb-2 flex items-baseline justify-between gap-2">
      <h2 className="text-label" style={{ color: 'var(--muted)' }}>Key signals</h2>
      <span className="text-xs" style={{ color: 'var(--muted)' }}>{signals.length} monitored</span>
    </div>
    <div className="grid gap-2 sm:grid-cols-2">{primary.map((signal) => <SignalCard key={signal.code} signal={signal} alerts={alerts} />)}</div>
    {rest.length > 0 && onMore && (
      <button type="button" onClick={onMore} className="text-body mt-2 font-semibold underline underline-offset-2" style={{ color: 'var(--ink)' }}>
        +{rest.length} more {tail} · open Details › Signals
      </button>
    )}
  </section>
}
