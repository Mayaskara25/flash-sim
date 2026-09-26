import { useEffect, useRef, useState } from 'react'
import { fmtNumber, roleLabel } from '../format'
import type { AlertCard, LiqReview, LogEntry, Role, SignalView } from '../types'

const filters = ['all', 'alert', 'transition', 'decision', 'comm', 'note'] as const

/**
 * H14: the full, filterable audit log. This is the only place free-text
 * notes and repeated signal alerts live — the main-view timeline keeps just
 * the key events (UI_PLAN §3, "IncidentLog: move, full and filterable").
 */
export function IncidentLog({ log, alerts, signals = [], role, busy, onAck, onNote, onReview }: { log: LogEntry[]; alerts: AlertCard[]; signals?: SignalView[]; role: Role | 'All'; busy: boolean; onAck: (id: string, actor: Role) => Promise<void>; onNote: (text: string, actor: Role) => Promise<void>; onReview: (verdict: LiqReview, rationale: string) => Promise<void> }) {
  const [filter, setFilter] = useState<(typeof filters)[number]>('all')
  const [note, setNote] = useState('')
  const [review, setReview] = useState<LiqReview>('under-review')
  const [rationale, setRationale] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)
  const labels = new Map(signals.map((signal) => [signal.code, signal.label]))
  const latestId = useRef(Math.max(0, ...log.map((entry) => entry.id)))
  const [newCount, setNewCount] = useState(0)
  useEffect(() => {
    const added = log.filter((entry) => entry.id > latestId.current).length
    latestId.current = Math.max(0, ...log.map((entry) => entry.id))
    if (added) setNewCount((count) => count + added)
  }, [log])
  const actor: Role = role === 'All' ? 'IC' : role
  const entries = log.filter((entry) => filter === 'all' || entry.type === filter).slice().reverse()
  const activeAlerts = alerts.filter((alert) => !alert.acknowledged_by)
  const inputClass = 'text-body border px-2 py-1.5'

  return <section aria-label="Incident log">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-label" style={{ color: 'var(--muted)' }}>Incident log</h2>
      <div className="flex items-center gap-2">
        {newCount > 0 && <button type="button" onClick={() => setNewCount(0)} className="text-xs font-semibold" style={{ color: 'var(--warn-fg)' }}>{newCount} new · dismiss</button>}
        <span className="text-xs" style={{ color: 'var(--muted)' }}>{log.length} entries · newest first</span>
      </div>
    </div>
    {activeAlerts.length > 0 && <div className="mt-2 flex flex-wrap gap-1.5">
      {activeAlerts.map((alert) => <button key={alert.id} type="button" disabled={busy} onClick={() => void onAck(alert.id, actor).catch(() => {})}
        className="text-body border px-2 py-1 disabled:opacity-50" style={{ borderColor: 'var(--warn-border)', background: 'var(--warn-bg)', color: 'var(--warn-fg)' }}>
        Acknowledge {labels.get(alert.signal) ?? alert.signal} · {alert.count}×
      </button>)}
    </div>}
    <div className="mt-2 flex flex-wrap gap-1" role="group" aria-label="Filter log entries">
      {filters.map((item) => <button key={item} type="button" onClick={() => setFilter(item)} aria-pressed={filter === item}
        className="text-xs font-semibold capitalize border px-2 py-1"
        style={{ borderColor: filter === item ? 'var(--ink)' : 'var(--line)', background: filter === item ? 'var(--ink)' : 'var(--surface)', color: filter === item ? 'var(--bg)' : 'var(--muted)' }}>
        {item}
      </button>)}
    </div>
    <ol className="mt-2 max-h-96 divide-y overflow-y-auto" style={{ borderColor: 'var(--line)', borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)' }}>
      {entries.length ? entries.map((entry) => <li key={entry.id} className="py-2 text-body">
        <div className="flex gap-2">
          <span className="w-14 shrink-0 font-mono text-xs tabular" style={{ color: 'var(--muted)' }}>{entry.t_label}</span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-semibold uppercase" style={{ color: 'var(--ink)' }}>{entry.type}</span>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>{entry.actor === 'system' ? 'Engine' : `${entry.actor} · ${roleLabel[entry.actor]}`} · SEV-{entry.sev}</span>
              {entry.liquidation_review && <span className="text-xs font-semibold" style={{ color: 'var(--warn-fg)' }}>Liq: {entry.liquidation_review}</span>}
            </div>
            <p className="mt-0.5 leading-snug">{entry.action}</p>
            {entry.rationale && <p className="text-body mt-1 leading-snug" style={{ color: 'var(--muted)' }}>Why: {entry.rationale}</p>}
            {Object.keys(entry.signal_snapshot).length > 0 && <>
              <button type="button" onClick={() => setExpanded((id) => id === entry.id ? null : entry.id)} className="text-body mt-1 underline" style={{ color: 'var(--ink)' }}>
                {expanded === entry.id ? 'Hide' : 'Show'} signal snapshot
              </button>
              {expanded === entry.id && <p className="text-xs mt-1 font-mono" style={{ color: 'var(--muted)' }}>
                {Object.entries(entry.signal_snapshot).map(([key, value]) => `${labels.get(key) ?? key} ${fmtNumber(value)}`).join(' · ')}
              </p>}
            </>}
          </div>
        </div>
      </li>) : <li className="p-4 text-body" style={{ color: 'var(--muted)' }}>No log entries match this filter.</li>}
    </ol>
    <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (note.trim()) void onNote(note.trim(), actor).then(() => setNote('')).catch(() => {}) }}>
      <label htmlFor="incident-note" className="sr-only">Add incident note</label>
      <input id="incident-note" className={`${inputClass} min-w-0 flex-1`} style={{ borderColor: 'var(--line)' }} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a decision or observation" />
      <button type="submit" disabled={busy || !note.trim()} className="text-body border px-3 py-1.5 font-semibold disabled:opacity-50" style={{ borderColor: 'var(--ink)' }}>Add note</button>
    </form>
    <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--line)' }}>
      <h3 className="text-label" style={{ color: 'var(--muted)' }}>Abnormal liquidation review · IC</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        <select className={`${inputClass} border`} style={{ borderColor: 'var(--line)' }} aria-label="Liquidation review verdict" value={review} onChange={(e) => setReview(e.target.value as LiqReview)} disabled={role !== 'IC'}>
          <option value="under-review">Under review</option>
          <option value="market-explained">Market-explained</option>
          <option value="wrongful">Wrongful</option>
        </select>
        <input className={`${inputClass} min-w-44 flex-1 border`} style={{ borderColor: 'var(--line)' }} aria-label="Liquidation review rationale" placeholder="Evidence and reason" value={rationale} onChange={(e) => setRationale(e.target.value)} disabled={role !== 'IC'} />
        <button type="button" disabled={busy || role !== 'IC' || !rationale.trim()} onClick={() => void onReview(review, rationale.trim()).then(() => setRationale('')).catch(() => {})} className="text-body border px-3 py-1.5 font-semibold disabled:opacity-50" style={{ borderColor: 'var(--ink)', background: 'var(--ink)', color: 'var(--bg)' }}>Record review</button>
      </div>
      {role !== 'IC' && <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Select IC to record a liquidation verdict.</p>}
    </div>
  </section>
}
