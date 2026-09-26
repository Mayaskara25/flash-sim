import type { LogEntry } from '../types'

export function IncidentTimeline({ log, limit = 10 }: { log: LogEntry[]; limit?: number }) {
  const entries = log.filter((entry) => ['transition', 'alert', 'decision', 'comm'].includes(entry.type)).slice(-limit).reverse()
  const owner = (role: LogEntry['actor']) => ({ IC: 'P1', TL: 'P2', CS: 'P3', system: 'SYS' })[role]
  return <section className="border border-line bg-white p-3" aria-label="Incident timeline"><div className="flex items-baseline justify-between gap-2"><h2 className="text-xs font-bold uppercase tracking-[0.13em]">Incident timeline</h2><span className="text-[10px] text-muted">auditable decision log</span></div><ol className="mt-2 divide-y divide-line">{entries.length ? entries.map((entry) => <li key={entry.id} className="grid grid-cols-[58px_1fr] gap-2 py-2 text-[11px]"><span className="font-mono text-muted">{entry.t_label}</span><div><p><strong className="mr-1 uppercase text-navy">{owner(entry.actor)}</strong>{entry.action}</p>{entry.rationale && <p className="mt-0.5 text-[10px] text-muted">Why: {entry.rationale}</p>}</div></li>) : <li className="py-3 text-xs text-muted">Timeline begins when a scenario starts.</li>}</ol></section>
}
