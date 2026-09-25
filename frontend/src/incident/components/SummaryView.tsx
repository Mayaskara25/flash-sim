import { useState } from 'react'
import { Link } from 'react-router-dom'
import { fmtNumber, simLabel } from '../format'
import type { IncidentSummary, TemplateView } from '../types'

function EntryList({ title, entries }: { title: string; entries: IncidentSummary['timeline'] }) {
  return <section className="border border-line bg-white p-4"><h2 className="text-sm font-bold">{title}</h2><ol className="mt-3 divide-y divide-line">{entries.map((entry) => <li key={entry.id} className="grid gap-1 py-2 text-xs sm:grid-cols-[78px_36px_1fr]"><span className="font-mono text-muted">{entry.t_label}</span><span className="font-bold">{entry.actor}</span><div>{entry.action}{entry.liquidation_review && <span className="ml-2 border border-amber-300 px-1.5 py-0.5 text-amber-900">{entry.liquidation_review}</span>}{entry.rationale && <p className="mt-1 text-muted">Why: {entry.rationale}</p>}</div></li>)}</ol></section>
}

export function SummaryView({ summary, templates, mock }: { summary: IncidentSummary | null; templates: TemplateView[]; mock: boolean }) {
  const [copyStatus, setCopyStatus] = useState('')
  const copy = async () => {
    if (!summary) return
    try { await navigator.clipboard.writeText(summary.markdown); setCopyStatus('Copied') }
    catch { setCopyStatus('Clipboard unavailable; select the Markdown from the page instead') }
  }
  return <main className="min-h-screen bg-bg p-4 text-ink md:p-6"><div className="mx-auto max-w-5xl">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-widest text-muted">MochaTrade / Operations</p><h1 className="mt-1 text-2xl font-bold">Incident summary</h1></div><Link to="/" className="border border-line bg-white px-3 py-2 text-xs font-semibold">← Incident console</Link></div>
    {mock && <p className="mt-4 border border-amber-300 bg-amber-50 p-2 text-xs font-semibold text-amber-900">Sample fixture data — this is not a completed live run.</p>}
    {!summary ? <p className="mt-8 border border-line bg-white p-5 text-sm">Summary becomes available after the incident resolves.</p> : <>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border border-line bg-white p-4"><div className="text-sm"><strong>{summary.scenario_id}</strong> · peak SEV-{summary.peak_sev} · {simLabel(summary.started_t)} to {summary.ended_t == null ? 'ongoing' : simLabel(summary.ended_t)}</div><div className="flex items-center gap-2"><span role="status" className="text-xs text-muted">{copyStatus}</span><button type="button" onClick={() => void copy()} className="bg-navy px-3 py-2 text-xs font-semibold text-white">Copy as Markdown</button></div></div>
      <div className="mt-4 grid gap-4">
        <EntryList title="Timeline" entries={summary.timeline} />
        <section className="border border-line bg-white p-4"><h2 className="text-sm font-bold">Peak signals</h2><div className="mt-3 flex flex-wrap gap-2">{summary.peaks.map((peak) => <span key={peak.signal} className="border border-line px-2 py-1.5 text-xs"><strong>{peak.signal}</strong> {fmtNumber(peak.value)} · {simLabel(peak.t)}</span>)}</div></section>
        <EntryList title="Decisions · who, when, why" entries={summary.decisions} />
        <section className="border border-line bg-white p-4"><h2 className="text-sm font-bold">Communications sent</h2><ol className="mt-3 divide-y divide-line">{summary.comms.map((entry) => { const template = templates.find((item) => item.id === entry.ref); return <li key={entry.id} className="py-2 text-xs"><strong>{entry.t_label} · {entry.actor}</strong> — {entry.action}{template?.text && <p className="mt-1 whitespace-pre-wrap border-l-2 border-line pl-2 text-muted">{template.text}</p>}</li> })}</ol></section>
        <EntryList title="Liquidation reviews" entries={summary.liquidation_reviews} />
        <section className="border border-line bg-white p-4"><h2 className="text-sm font-bold">Open items</h2><ul className="mt-2 list-disc pl-5 text-xs">{summary.open_items.map((item) => <li key={item}>{item}</li>)}</ul></section>
        {copyStatus.startsWith('Clipboard unavailable') && <textarea readOnly aria-label="Summary Markdown" className="h-48 w-full border border-line bg-white p-3 font-mono text-xs" value={summary.markdown} />}
      </div>
    </>}
  </div></main>
}
