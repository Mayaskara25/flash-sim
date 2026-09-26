import { useEffect, useState } from 'react'
import { roleLabel, simLabel, tagName } from '../format'
import type { ActionView } from '../types'
import { Badge, Button } from '../ui'
import { WhatIfBadge } from './WhatIfBadge'

/**
 * H14: one action, two densities.
 *
 * `variant="hero"` is the single primary action of the console — a large
 * title, the rationale hint, the what-if in a large font and a large Approve
 * button (UI_PLAN §2, centre column). `variant="row"` is the compact
 * "next" line: text, role and a small Approve. Both share the same
 * approve/skip dialog so a decision is always made the same way.
 */
export function ActionCard({ action, busy, onDecide, shortcutTarget, variant = 'row' }: {
  action: ActionView
  busy: boolean
  onDecide: (decision: 'approve' | 'skip', rationale: string) => Promise<void>
  shortcutTarget: boolean
  variant?: 'hero' | 'row'
}) {
  const [decision, setDecision] = useState<'approve' | 'skip' | null>(null)
  const [rationale, setRationale] = useState(action.rationale_hint)
  const [submitting, setSubmitting] = useState(false)
  const hero = variant === 'hero'

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

  const meta = <div className="flex flex-wrap items-center gap-1.5 text-label" style={{ color: 'var(--muted)' }}>
    <Badge tone={action.role === 'IC' ? 'sev1' : action.role === 'TL' ? 'sev2' : 'sev3'} title={roleLabel[action.role]}>{action.role}</Badge>
    {action.tag && <span className="border border-line px-1.5 py-0.5 text-xs font-semibold" title={action.tag}>{tagName(action.tag)}</span>}
    {action.expires_t != null && <span className="font-semibold" style={{ color: 'var(--warn-fg)' }}>Review by {simLabel(action.expires_t)}</span>}
  </div>

  if (!hero) {
    return <article className={`flex items-center gap-2 border-b border-line py-1.5 ${submitting ? 'opacity-55' : ''}`} style={{ borderColor: 'var(--line)' }}>
      <div className="min-w-0 flex-1">
        <p className="text-body truncate font-medium leading-snug" title={`${action.text}${action.rationale_hint ? ` — ${action.rationale_hint}` : ''}`}>
          <span className="mr-1.5 inline-flex align-middle"><Badge tone={action.role === 'IC' ? 'sev1' : action.role === 'TL' ? 'sev2' : 'sev3'} title={roleLabel[action.role]}>{action.role}</Badge></span>
          {action.text}
        </p>
      </div>
      {action.expires_t != null && <span className="text-xs whitespace-nowrap" style={{ color: 'var(--warn-fg)' }}>by {simLabel(action.expires_t)}</span>}
      <div className="flex shrink-0 gap-1.5">
        <Button variant="primary" disabled={busy || submitting} onClick={() => setDecision('approve')}>Approve</Button>
        <Button variant="ghost" disabled={busy || submitting} onClick={() => setDecision('skip')}>Skip</Button>
      </div>
      <DecisionDialog action={action} decision={decision} rationale={rationale} submitting={submitting}
        onRationale={setRationale} onCancel={() => setDecision(null)} onSubmit={() => void submit()} />
    </article>
  }

  return <article className={`border p-3 ${submitting ? 'opacity-55' : ''}`} style={{ borderColor: 'var(--ink)', borderLeft: '4px solid var(--sev1)', borderRadius: 8, background: 'var(--surface)' }}>
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      {meta}
      <span className="text-xs" style={{ color: 'var(--muted)' }}>human approval required · logged as {roleLabel[action.role]}</span>
    </div>
    <h3 className="text-body-lg mt-1 font-semibold leading-snug">{action.text}</h3>
    <p className="text-body mt-0.5 leading-snug" style={{ color: 'var(--muted)' }}>{action.rationale_hint}</p>
    <WhatIfBadge value={action.what_if} hero />
    <div className="mt-2.5 flex flex-wrap items-center gap-2">
      <Button variant="primary" size="lg" disabled={busy || submitting} onClick={() => setDecision('approve')}>Approve</Button>
      <Button variant="secondary" size="lg" disabled={busy || submitting} onClick={() => setDecision('skip')}>Skip</Button>
    </div>
    <DecisionDialog action={action} decision={decision} rationale={rationale} submitting={submitting}
      onRationale={setRationale} onCancel={() => setDecision(null)} onSubmit={() => void submit()} />
  </article>
}

function DecisionDialog({ action, decision, rationale, submitting, onRationale, onCancel, onSubmit }: {
  action: ActionView
  decision: 'approve' | 'skip' | null
  rationale: string
  submitting: boolean
  onRationale: (value: string) => void
  onCancel: () => void
  onSubmit: () => void
}) {
  if (!decision) return null
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget && !submitting) onCancel() }}>
    <div role="dialog" aria-modal="true" aria-label={`${decision} action`} className="w-full max-w-lg p-5 shadow-xl" style={{ background: 'var(--surface)' }}
      onKeyDown={(e) => { if (e.target instanceof HTMLTextAreaElement && e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSubmit() } }}>
      <h3 className="text-body-lg font-semibold">{decision === 'approve' ? 'Approve action' : 'Skip action'}</h3>
      <p className="text-body mt-2">{action.text}</p>
      <label className="text-label mt-4 block" htmlFor={`rationale-${action.id}`}>Reason (required)</label>
      <textarea id={`rationale-${action.id}`} className="text-body mt-1 min-h-24 w-full border p-2" style={{ borderColor: 'var(--line)' }} value={rationale} onChange={(e) => onRationale(e.target.value)} autoFocus />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" disabled={submitting} onClick={onCancel}>Cancel</Button>
        <Button variant="primary" loading={submitting} disabled={!rationale.trim()} onClick={onSubmit}>{decision === 'approve' ? 'Confirm approve' : 'Confirm skip'}</Button>
      </div>
    </div>
  </div>
}
