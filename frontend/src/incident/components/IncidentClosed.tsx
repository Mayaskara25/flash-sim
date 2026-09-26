import { useState } from 'react'
import { fmtNumber, simLabel } from '../format'
import type { IncidentStateDTO, IncidentSummary } from '../types'

/**
 * H15: full-width "incident closed" card shown over the console once the
 * incident resolves (or the sim clock reaches the scenario duration). The
 * live console keeps running underneath; this is a dismissible overlay, not
 * a route change.
 */
export function IncidentClosed({ state, summary, reportUrl, onViewTimeline, onBack }: {
  state: IncidentStateDTO
  summary: IncidentSummary | null
  reportUrl: string
  onViewTimeline: () => void
  onBack: () => void
}) {
  const [copyStatus, setCopyStatus] = useState('')

  const decisions = summary?.decisions.length ?? state.log.filter((entry) => entry.type === 'decision').length
  const comms = summary?.comms.length ?? state.log.filter((entry) => entry.type === 'comm').length
  const reviews = summary?.liquidation_reviews.length ?? state.log.filter((entry) => entry.liquidation_review != null).length
  const openItems = summary?.open_items ?? []
  const peakSev = summary?.peak_sev ?? state.severity.sev
  const peaks = summary?.peaks ?? []
  const duration = summary?.ended_t ?? state.sim.t
  const markdown = summary?.markdown
    ?? `# ${state.sim.scenario_name ?? 'Incident'} summary\nSeverity SEV-${state.severity.sev} at ${state.sim.t_label}.`

  const copy = async () => {
    try { await navigator.clipboard.writeText(markdown); setCopyStatus('Copied') }
    catch { setCopyStatus('Clipboard unavailable') }
  }

  return <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/60 p-4" role="dialog" aria-modal="true" aria-label="Incident closed">
    <div className="w-full max-w-2xl border border-navy bg-white p-5 shadow-2xl md:p-6">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-muted">MochaTrade / Operations</p>
      <h2 className="mt-1 text-xl font-bold">Incident closed</h2>
      <p className="mt-1 text-sm text-muted">{state.sim.scenario_name ?? 'Simulation'} · resolved at {simLabel(duration)}</p>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs md:grid-cols-3">
        <Metric label="Duration" value={simLabel(duration)} />
        <Metric label="Peak severity" value={`SEV-${peakSev}`} />
        <Metric label="Decisions" value={String(decisions)} />
        <Metric label="Comms sent" value={String(comms)} />
        <Metric label="Liquidation reviews" value={String(reviews)} />
        <Metric label="Open items" value={String(openItems.length)} />
      </div>

      {peaks.length > 0 && <div className="mt-4">
        <h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted">Peak signals</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {peaks.map((peak) => <span key={peak.signal} className="border border-line px-2 py-1 text-[11px]"><strong>{peak.signal}</strong> {fmtNumber(peak.value)} · {simLabel(peak.t)}</span>)}
        </div>
      </div>}

      {openItems.length > 0 && <div className="mt-3">
        <h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted">Open items</h3>
        <ul className="mt-1 list-disc pl-5 text-xs">{openItems.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>}

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <a href={reportUrl} target="_blank" rel="noreferrer" className="bg-navy px-3 py-2 text-xs font-semibold text-white">Download PDF report</a>
        <button type="button" onClick={onViewTimeline} className="border border-navy px-3 py-2 text-xs font-semibold text-navy">View timeline</button>
        <button type="button" onClick={() => void copy()} className="border border-line px-3 py-2 text-xs font-semibold">Copy summary (Markdown)</button>
        <span role="status" className="text-[11px] text-muted">{copyStatus}</span>
        <button type="button" onClick={onBack} className="ml-auto border border-line px-3 py-2 text-xs font-semibold text-muted">Back to console</button>
      </div>
    </div>
  </div>
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="border border-line bg-slate-50 p-2"><p className="text-[10px] uppercase tracking-wide text-muted">{label}</p><p className="mt-1 font-semibold">{value}</p></div>
}
