import { useEffect, useState } from 'react'
import { simLabel } from '../format'
import type { ActionView } from '../types'
import { WhatIfBadge } from './WhatIfBadge'

export function ActionCard({ action, busy, onDecide, shortcutTarget }: { action: ActionView; busy: boolean; onDecide: (decision: 'approve' | 'skip', rationale: string) => Promise<void>; shortcutTarget: boolean }) {
  const [decision, setDecision] = useState<'approve' | 'skip' | null>(null)
  const [rationale, setRationale] = useState(action.rationale_hint)
  const [submitting, setSubmitting] = useState(false)
  useEffect(() => {
    if (!shortcutTarget) return
    const open = (event: Event) => { if (!busy) setDecision((event as CustomEvent<'approve' | 'skip'>).detail) }
    window.addEventListener('incident-action-shortcut', open)
    return () => window.removeEventListener('incident-action-shortcut', open)
  }, [busy, shortcutTarget])
  const submit = async () => {
    if (!decision || !rationale.trim()) return
    setSubmitting(true)
    try { await onDecide(decision, rationale.trim()); setDecision(null) } catch { /* Hook exposes the error; keep the draft. */ } finally { setSubmitting(false) }
  }
  return <article className={`border border-line bg-white p-3 ${submitting ? 'opacity-55' : ''}`}>
    <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide"><span className="bg-slate-900 px-1.5 py-0.5 text-white">{action.role}</span>{action.tag && <span className="border border-line px-1.5 py-0.5 text-muted">{action.tag}</span>}<span className="text-muted">Priority {action.priority}</span>{action.expires_t != null && <span className="text-warn">Review by {simLabel(action.expires_t)}</span>}</div>
    <p className="mt-2 text-[15px] font-medium leading-snug text-ink">{action.text}</p>
    <p className="mt-1 text-[11px] leading-snug text-muted">{action.rationale_hint}</p>
    <WhatIfBadge value={action.what_if} />
    <div className="mt-3 flex gap-2"><button type="button" disabled={busy || submitting} onClick={() => setDecision('approve')} className="bg-navy px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Approve</button><button type="button" disabled={busy || submitting} onClick={() => setDecision('skip')} className="border border-line px-3 py-1.5 text-xs text-muted disabled:opacity-50">Skip</button></div>
    {decision && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget && !submitting) setDecision(null) }}>
      <div role="dialog" aria-modal="true" aria-label={`${decision} action`} className="w-full max-w-lg bg-white p-5 shadow-xl" onKeyDown={(e) => { if (e.target instanceof HTMLTextAreaElement && e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void submit() } }}><h3 className="text-base font-semibold">{decision === 'approve' ? 'Approve action' : 'Skip action'}</h3><p className="mt-2 text-sm">{action.text}</p><label className="mt-4 block text-xs font-semibold" htmlFor={`rationale-${action.id}`}>Reason (required)</label><textarea id={`rationale-${action.id}`} className="mt-1 min-h-24 w-full border border-line p-2 text-sm" value={rationale} onChange={(e) => setRationale(e.target.value)} autoFocus />
        <div className="mt-4 flex justify-end gap-2"><button type="button" disabled={submitting} onClick={() => setDecision(null)} className="border border-line px-3 py-2 text-xs">Cancel</button><button type="button" disabled={submitting || !rationale.trim()} onClick={() => void submit()} className="bg-navy px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{submitting ? 'Saving…' : 'Confirm'}</button></div>
      </div>
    </div>}
  </article>
}

