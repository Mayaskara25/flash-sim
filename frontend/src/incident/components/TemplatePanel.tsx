import { useState } from 'react'
import type { Role, TemplateView } from '../types'

function TemplateDraft({ template, actor, busy, onSend, onDismiss }: { template: TemplateView; actor: Role; busy: boolean; onSend: (id: string, actor: Role, text: string) => Promise<void>; onDismiss: (id: string, actor: Role, rationale: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(template.text)
  const [pending, setPending] = useState(false)
  const [dismissReason, setDismissReason] = useState('Not relevant to the confirmed incident')
  const unresolved = template.missing.filter((name) => text.includes(`{${name}}`))
  const send = async () => { setPending(true); try { await onSend(template.id, actor, text); setEditing(false) } catch { /* Preserve draft on API error. */ } finally { setPending(false) } }
  const dismiss = async () => { setPending(true); try { await onDismiss(template.id, actor, dismissReason); setEditing(false) } catch { /* Preserve draft on API error. */ } finally { setPending(false) } }
  return <article className="border border-line bg-white p-3"><div className="flex flex-wrap items-center gap-2"><strong className="text-xs">{template.title}</strong><span className="border border-line px-1.5 py-0.5 text-[10px] text-muted">{template.audience} · {template.channel}</span></div>
    {editing ? <><label className="mt-2 block text-[11px] font-semibold" htmlFor={`draft-${template.id}`}>Message draft</label><textarea id={`draft-${template.id}`} className="mt-1 min-h-28 w-full border border-line p-2 text-xs" value={text} onChange={(e) => setText(e.target.value)} /><label className="mt-2 block text-[11px]" htmlFor={`dismiss-${template.id}`}>Reason if dismissing</label><input id={`dismiss-${template.id}`} className="mt-1 w-full border border-line p-2 text-xs" value={dismissReason} onChange={(e) => setDismissReason(e.target.value)} /></> : <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-muted">{template.text}</p>}
    {unresolved.length > 0 && <p className="mt-2 text-[11px] font-semibold text-crit">Fill before sending: {unresolved.join(', ')}</p>}
    <div className="mt-2 flex flex-wrap gap-2">{!editing && <button type="button" onClick={() => setEditing(true)} className="border border-line px-2 py-1 text-[11px]">Edit / approve</button>}{editing && <><button type="button" disabled={busy || pending || !text.trim() || unresolved.length > 0} onClick={() => void send()} className="bg-navy px-2 py-1 text-[11px] font-semibold text-white disabled:opacity-50">Approve &amp; log as {actor}</button><button type="button" disabled={busy || pending || !dismissReason.trim()} onClick={() => void dismiss()} className="border border-line px-2 py-1 text-[11px] disabled:opacity-50">Dismiss</button><button type="button" disabled={pending} onClick={() => setEditing(false)} className="px-2 py-1 text-[11px]">Cancel</button></>}</div>
  </article>
}

export function TemplatePanel({ templates, actor, busy, onSend, onDismiss }: { templates: TemplateView[]; actor: Role; busy: boolean; onSend: (id: string, actor: Role, text: string) => Promise<void>; onDismiss: (id: string, actor: Role, rationale: string) => Promise<void> }) {
  const surfaced = templates.filter((item) => item.status === 'surfaced')
  return <section className="border border-line bg-slate-50 p-3"><h3 className="mb-2 text-xs font-bold uppercase tracking-wider">Communication drafts <span className="font-normal text-muted">({surfaced.length})</span></h3><div className="space-y-2">{surfaced.length ? surfaced.map((template) => <TemplateDraft key={template.id} template={template} actor={actor} busy={busy} onSend={onSend} onDismiss={onDismiss} />) : <p className="text-xs text-muted">No message is due. Thresholds never send messages automatically.</p>}</div></section>
}
