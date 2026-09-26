import type { ActionQueueItem } from '../types'

const bandTone: Record<ActionQueueItem['band'], string> = {
  NOW: 'border-red-300 bg-red-50 text-red-950',
  NEXT: 'border-amber-300 bg-amber-50 text-amber-950',
  MONITOR: 'border-blue-300 bg-blue-50 text-blue-950',
}

export function P2ActionQueue({ items, busy, onAction }: { items: ActionQueueItem[]; busy: boolean; onAction: (item: ActionQueueItem) => void }) {
  const groups: ActionQueueItem['band'][] = ['NOW', 'NEXT', 'MONITOR']
  return <section id="p2-action-queue" className="border border-line bg-white p-3 md:p-4" aria-label="P2 action queue"><div className="flex flex-wrap items-baseline justify-between gap-2"><div><h2 className="text-xs font-bold uppercase tracking-[0.13em]">P2 action queue</h2><p className="mt-1 text-[11px] text-muted">Prioritized modelled actions. Controls and communications still require human approval.</p></div><span className="text-[10px] font-semibold text-muted">TOP {items.length} ITEMS</span></div><div className="mt-3 space-y-3">{groups.map((band) => { const rows = items.filter((item) => item.band === band); return rows.length ? <div key={band}><h3 className="mb-1 text-[10px] font-bold tracking-[0.14em] text-muted">{band}</h3><div className="space-y-1.5">{rows.map((item) => <article key={item.id} className={`border p-2.5 ${bandTone[band]}`}><div className="flex flex-wrap items-start justify-between gap-2"><div className="min-w-0"><div className="flex flex-wrap items-center gap-1.5"><span className="text-[10px] font-bold">{item.owner}</span><span className="text-[10px] uppercase text-muted">{item.status}</span>{item.eta && <span className="text-[10px] text-muted">ETA {item.eta}</span>}</div><p className="mt-1 text-xs font-semibold">{item.text}</p><p className="mt-1 text-[11px] leading-snug">{item.reason}</p></div>{item.button && <button type="button" disabled={busy} onClick={() => onAction(item)} className="shrink-0 border border-current bg-white px-2 py-1 text-[10px] font-bold disabled:opacity-50">{item.button}</button>}</div></article>)}</div></div> : null })}</div>{!items.length && <p className="mt-3 border border-dashed border-line p-3 text-xs text-muted">Start a scenario to populate P2's prioritized queue.</p>}</section>
}
