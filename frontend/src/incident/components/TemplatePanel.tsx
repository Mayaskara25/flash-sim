import { useState } from 'react'
import { roleLabel } from '../format'
import type { Role, TemplateView } from '../types'
import { Badge, Button } from '../ui'

function TemplateDraft({ template, actor, busy, onSend, onDismiss }: { template: TemplateView; actor: Role; busy: boolean; onSend: (id: string, actor: Role, text: string) => Promise<void>; onDismiss: (id: string, actor: Role, rationale: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(template.text)
  const [pending, setPending] = useState(false)
  const [dismissReason, setDismissReason] = useState('Not relevant to the confirmed incident')
  const unresolved = template.missing.filter((name) => text.includes(`{${name}}`))
  const send = async () => { setPending(true); try { await onSend(template.id, actor, text); setEditing(false) } catch { /* Preserve draft on API error. */ } finally { setPending(false) } }
  const dismiss = async () => { setPending(true); try { await onDismiss(template.id, actor, dismissReason); setEditing(false) } catch { /* Preserve draft on API error. */ } finally { setPending(false) } }
  return <article style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 8, padding: 12 }}>
    <div className="flex flex-wrap items-center gap-2">
      <strong className="text-body-lg">{template.title}</strong>
      <Badge tone="neutral" title={`${template.audience} · ${template.channel}`}>{template.audience} · {template.channel}</Badge>
    </div>
    {editing ? <><label className="text-label mt-2 block" htmlFor={`draft-${template.id}`}>Message draft</label><textarea id={`draft-${template.id}`} className="text-body mt-1 min-h-28 w-full border p-2" style={{ borderColor: 'var(--line)' }} value={text} onChange={(e) => setText(e.target.value)} /><label className="text-label mt-2 block" htmlFor={`dismiss-${template.id}`}>Reason if dismissing</label><input id={`dismiss-${template.id}`} className="text-body mt-1 w-full border p-2" style={{ borderColor: 'var(--line)' }} value={dismissReason} onChange={(e) => setDismissReason(e.target.value)} /></> : <p className="text-body mt-2 whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--muted)' }}>{template.text}</p>}
    {unresolved.length > 0 && <p className="text-body mt-2 font-semibold" style={{ color: 'var(--crit-fg)' }}>Fill before sending: {unresolved.join(', ')}</p>}
    <div className="mt-2 flex flex-wrap gap-2">
      {!editing && <Button variant="secondary" onClick={() => setEditing(true)}>Edit / approve</Button>}
      {editing && <>
        <Button variant="primary" loading={pending} disabled={busy || !text.trim() || unresolved.length > 0} onClick={() => void send()}>Approve &amp; log as {actor} · {roleLabel[actor]}</Button>
        <Button variant="secondary" loading={pending} disabled={busy || !dismissReason.trim()} onClick={() => void dismiss()}>Dismiss</Button>
        <Button variant="ghost" disabled={pending} onClick={() => setEditing(false)}>Cancel</Button>
      </>}
    </div>
  </article>
}

/**
 * H14: the full communication editor lives in Details › Comms. The centre
 * column keeps only a correctly counted "N drafts waiting" link, so the same
 * draft count never appears in two places (UI_PLAN §3, "Comms").
 */
export function TemplatePanel({ templates, actor, busy, onSend, onDismiss }: { templates: TemplateView[]; actor: Role; busy: boolean; onSend: (id: string, actor: Role, text: string) => Promise<void>; onDismiss: (id: string, actor: Role, rationale: string) => Promise<void> }) {
  const surfaced = templates.filter((item) => item.status === 'surfaced')
  return <section aria-label="Communication drafts">
    <div className="mb-2 flex items-baseline justify-between gap-2">
      <h2 className="text-label" style={{ color: 'var(--muted)' }}>Communication drafts</h2>
      <span className="text-xs" style={{ color: 'var(--muted)' }}>{surfaced.length} waiting</span>
    </div>
    <div className="space-y-2">
      {surfaced.length
        ? surfaced.map((template) => <TemplateDraft key={template.id} template={template} actor={actor} busy={busy} onSend={onSend} onDismiss={onDismiss} />)
        : <p className="text-body" style={{ color: 'var(--muted)' }}>No message is due. Thresholds never send messages automatically.</p>}
    </div>
  </section>
}
