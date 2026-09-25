import { useState } from 'react'
import type { AlertCard, SignalView } from '../types'
import { SignalCard } from './SignalCard'

const rank = { critical: 0, warn: 1, watch: 2, normal: 3 }
const coreOrder = ['LIQ_RATE', 'INS_FUND_PCT', 'PX_CHG_5M', 'TICKET_RATE', 'LAR', 'STBL_PX']

export function SignalGrid({ signals, alerts }: { signals: SignalView[]; alerts: AlertCard[] }) {
  const [showMore, setShowMore] = useState(false)
  const coreRank = (code: string) => { const index = coreOrder.indexOf(code); return index < 0 ? coreOrder.length : index }
  const sorted = [...signals].sort((a, b) => Number(b.relevant) - Number(a.relevant) || rank[a.status] - rank[b.status] || coreRank(a.code) - coreRank(b.code) || a.code.localeCompare(b.code))
  const primary = sorted.slice(0, 6)
  const rest = sorted.slice(6)
  return <section aria-label="Active signals" className="border border-line bg-white p-3 md:p-4">
    <div className="mb-3 flex items-baseline justify-between gap-2"><h2 className="text-xs font-bold uppercase tracking-[0.13em] text-ink">Active signals</h2><span className="text-[11px] text-muted">{signals.length} monitored · 6 shown</span></div>
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-2">{primary.map((signal) => <SignalCard key={signal.code} signal={signal} alerts={alerts} />)}</div>
    {rest.length > 0 && <div className="mt-3 border-t border-line pt-2"><button type="button" className="text-xs font-semibold text-navy underline underline-offset-2" aria-expanded={showMore} onClick={() => setShowMore((value) => !value)}>{showMore ? 'Hide' : 'Show'} {rest.length} more signals</button>
      {showMore && <div className="mt-2 flex flex-wrap gap-1.5">{rest.map((signal) => <span key={signal.code} className="border border-line px-2 py-1 font-mono text-[10px] text-muted" title={signal.label}>{signal.code} {signal.value}</span>)}</div>}
    </div>}
  </section>
}
