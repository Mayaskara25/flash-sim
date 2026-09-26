import { useState } from 'react'
import { fmtNumber } from '../format'
import type { ExecutionView, InvestigationCluster } from '../types'
import { Badge, Button } from '../ui'

const STATUS_TONE: Record<ExecutionView['status'], 'warn' | 'crit' | 'neutral' | 'ok'> = {
  flagged: 'warn', investigate: 'neutral', valid: 'ok', escalated: 'crit',
}

/**
 * H14: restyled for Details › Liquidations.
 *
 * Flagged executions come first, each row states the evidence that matters
 * for a decision (modelled threshold vs observed fill, and the execution
 * delay), and every decision button writes to the incident log.
 */
export function LiquidationInvestigator({ cluster, busy, onDecision }: { cluster: InvestigationCluster; busy: boolean; onDecision: (id: string, decision: 'valid' | 'investigate' | 'escalated') => void }) {
  const ranked = [...cluster.executions].sort((a, b) => {
    const weight = { flagged: 0, investigate: 1, escalated: 2, valid: 3 }
    return weight[a.status] - weight[b.status] || b.deviation_pct - a.deviation_pct
  })
  const [selected, setSelected] = useState(ranked[0]?.id ?? '')
  const row = ranked.find((execution) => execution.id === selected) ?? ranked[0]

  return <section aria-label="Abnormal liquidation investigator" style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 8, padding: 16 }}>
    <header>
      <h2 className="text-body-lg font-bold">{cluster.id} · {cluster.asset}</h2>
      <p className="text-body mt-1" style={{ color: 'var(--muted)' }}>{cluster.flagged_count} executions flagged. Modelled evidence only — no system or exchange error is asserted.</p>
      <p className="text-body mt-1" style={{ color: 'var(--muted)' }}>{cluster.why}</p>
    </header>
    <div className="mt-4 grid gap-4 md:grid-cols-[minmax(220px,0.8fr)_minmax(0,1.2fr)]">
      <div>
        <h3 className="text-label" style={{ color: 'var(--muted)' }}>Flagged executions</h3>
        <div className="mt-2 space-y-1.5">
          {ranked.map((execution) => <button key={execution.id} type="button" onClick={() => setSelected(execution.id)}
            aria-pressed={selected === execution.id}
            className="w-full border p-2 text-left" style={{ borderColor: selected === execution.id ? 'var(--ink)' : 'var(--line)', background: selected === execution.id ? 'var(--bg)' : 'var(--surface)' }}>
            <div className="flex items-center justify-between gap-2">
              <strong className="text-body">{execution.id}</strong>
              <Badge tone={STATUS_TONE[execution.status]}>{execution.status}</Badge>
            </div>
            <p className="text-body mt-0.5" style={{ color: 'var(--muted)' }}>{execution.trader_id} · {execution.side} · {fmtNumber(execution.leverage)}×</p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              threshold ${fmtNumber(execution.modelled_threshold)} vs fill ${fmtNumber(execution.observed_execution)} · delay {fmtNumber(execution.execution_delay_ms)} ms
            </p>
          </button>)}
        </div>
      </div>
      {row && <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-body-lg font-bold">{row.id} · {row.trader_id}</h3>
          <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge>
        </div>
        <p className="text-body mt-1" style={{ color: 'var(--muted)' }}>{row.label}</p>
        <div className="mt-4 grid gap-x-5 gap-y-3 sm:grid-cols-2">
          <Metric label="Asset / side" value={`${row.asset} · ${row.side}`} />
          <Metric label="Leverage" value={`${fmtNumber(row.leverage)}×`} />
          <Metric label="Modelled threshold" value={`$${fmtNumber(row.modelled_threshold)}`} />
          <Metric label="Observed execution" value={`$${fmtNumber(row.observed_execution)}`} />
          <Metric label="Deviation" value={`${fmtNumber(row.deviation_pct)}%`} />
          <Metric label="Execution delay" value={`${fmtNumber(row.execution_delay_ms)} ms`} />
          <Metric label="Market price" value={`$${fmtNumber(row.market_price)}`} />
          <Metric label="Liquidity condition" value={row.liquidity_condition} />
        </div>
        <div className="mt-4 border-l-2 p-3 text-body" style={{ borderColor: 'var(--warn-fg)', background: 'var(--warn-bg)' }}>
          <strong>Why flagged</strong>
          <ul className="mt-1 list-disc pl-4">{row.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" disabled={busy || row.status === 'valid'} onClick={() => onDecision(row.id, 'valid')}>Mark valid</Button>
          <Button variant="secondary" disabled={busy || row.status === 'escalated'} onClick={() => onDecision(row.id, 'investigate')}>Keep investigating</Button>
          <Button variant="primary" disabled={busy || row.status === 'escalated'} onClick={() => onDecision(row.id, 'escalated')}>Escalate</Button>
        </div>
        <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>Each choice records the actor, timestamp, decision, reason and status in the incident log.</p>
      </div>}
    </div>
  </section>
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div>
    <p className="text-label" style={{ color: 'var(--muted)' }}>{label}</p>
    <p className="text-body mt-0.5 font-medium">{value}</p>
  </div>
}
