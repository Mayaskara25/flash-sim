import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import type { IncidentActions } from '../useIncident'
import type { CommandBrief, IncidentStateDTO, IncidentSummary, Role } from '../types'
import { ForecastStrip } from '../components/ForecastStrip'
import { FundRunwayChart } from '../components/FundRunwayChart'
import { IncidentLog } from '../components/IncidentLog'
import { IncidentReport } from '../components/IncidentReport'
import { SignalGrid } from '../components/SignalGrid'
import { TemplatePanel } from '../components/TemplatePanel'
import { DETAILS_TABS, TAB_LABELS, type DetailsTab } from './detailsTabs'

export function DetailsDrawer({ tab, onTabChange, onClose, state, command, role, busy, mock, summary, actions, onOpenInvestigator }: {
  tab: DetailsTab
  onTabChange: (tab: DetailsTab) => void
  onClose: () => void
  state: IncidentStateDTO
  command: CommandBrief | null
  role: Role | 'All'
  busy: boolean
  mock: boolean
  summary: IncidentSummary | null
  actions: IncidentActions
  onOpenInvestigator: () => void
}) {
  const panelRef = useRef<HTMLElement | null>(null)
  const messageActor: Role = role === 'All' ? 'CS' : role
  const logActor: Role = role === 'All' ? 'IC' : role
  const fund = state.signals.find((signal) => signal.code === 'INS_FUND_PCT')
  const cluster = command?.cluster ?? null

  useEffect(() => {
    const node = panelRef.current
    node?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.stopPropagation(); onClose(); return }
      if (event.key !== 'Tab' || !node) return
      const items = node.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
      const enabled = [...items].filter((element) => !element.hasAttribute('disabled'))
      if (enabled.length === 0) return
      const first = enabled[0]
      const last = enabled[enabled.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [onClose, tab])

  return <div className="fixed inset-0 z-40">
    <div className="absolute inset-0 bg-slate-950/40" onClick={onClose} />
    <aside ref={panelRef} role="dialog" aria-modal="true" aria-label="Incident details" tabIndex={-1} className="absolute right-0 top-0 flex h-full w-[45%] min-w-[400px] flex-col bg-bg shadow-xl focus:outline-none">
      <div className="flex shrink-0 flex-wrap items-center gap-1 border-b border-line bg-white px-3 py-2">
        <div role="tablist" aria-label="Details sections" className="flex min-w-0 flex-1 flex-wrap gap-1">
          {DETAILS_TABS.map((id) => <button key={id} type="button" role="tab" aria-selected={tab === id}
            onClick={() => onTabChange(id)}
            className={`border px-2.5 py-1 text-xs font-semibold ${tab === id ? 'border-navy bg-navy text-white' : 'border-line bg-white text-muted hover:bg-slate-50'}`}>
            {TAB_LABELS[id]}
          </button>)}
        </div>
        <button type="button" onClick={onClose} aria-label="Close details (Esc)" className="border border-line px-2.5 py-1 text-xs font-semibold">✕</button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3" role="tabpanel">
        {tab === 'signals' && <div className="space-y-3">
          {state.forecast && fund && <div className="border border-line bg-slate-950 p-3 text-white"><FundRunwayChart fund={fund} forecast={state.forecast} t={state.sim.t} /></div>}
          {state.forecast && <ForecastStrip forecast={state.forecast} fund={fund} t={state.sim.t} />}
          <SignalGrid signals={state.signals} alerts={state.alerts} />
        </div>}
        {tab === 'liquidations' && <div className="space-y-3">
          {cluster ? <>
            <div className="border border-line bg-white p-3">
              <h2 className="text-sm font-bold">{cluster.id} · {cluster.asset}</h2>
              <p className="mt-1 text-xs text-muted">{cluster.flagged_count} executions flagged for investigation. Modelled evidence only — no system or exchange error is asserted.</p>
              <p className="mt-2 text-xs">{cluster.why}</p>
              <button type="button" onClick={onOpenInvestigator} className="mt-3 border border-navy bg-white px-3 py-1.5 text-xs font-bold text-navy">Open investigator</button>
            </div>
            <div className="border border-line bg-white p-3"><h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted">Flagged executions</h3>
              <ul className="mt-2 divide-y divide-line">{cluster.executions.filter((row) => row.status !== 'valid').map((row) => <li key={row.id} className="py-2 text-xs"><strong>{row.id}</strong> · {row.trader_id} · {row.side} {row.leverage}× <span className="ml-1 uppercase text-muted">{row.status}</span><p className="mt-0.5 text-[11px] text-muted">{row.label}</p></li>)}</ul>
            </div>
          </> : <p className="border border-line bg-white p-4 text-xs text-muted">No abnormal liquidation cluster is under investigation. One appears here when P2 flags fills.</p>}
        </div>}
        {tab === 'comms' && <TemplatePanel templates={state.templates} actor={messageActor} busy={busy}
          onSend={(id, actor, text) => actions.sendTemplate(id, { actor, text })}
          onDismiss={(id, actor, rationale) => actions.dismissTemplate(id, { actor, rationale })} />}
        {tab === 'log' && <IncidentLog log={state.log} alerts={state.alerts} role={role} busy={busy}
          onAck={(id, actor) => actions.ackAlert(id, { actor })}
          onNote={(text, actor) => actions.addNote({ actor, text })}
          onReview={(verdict, rationale) => actions.reviewLiquidation({ verdict, actor: logActor === 'system' ? 'IC' : logActor, rationale })} />}
        {tab === 'report' && <div className="space-y-3">
          {command && <IncidentReport state={state} command={command} reportUrl={actions.reportUrl()} />}
          {summary ? <div className="border border-line bg-white p-3">
            <h2 className="text-xs font-bold uppercase tracking-[0.13em]">Summary</h2>
            <p className="mt-1 text-xs"><strong>{summary.scenario_id}</strong> · peak SEV-{summary.peak_sev}</p>
            {summary.open_items.length > 0 && <ul className="mt-2 list-disc pl-5 text-xs">{summary.open_items.map((item) => <li key={item}>{item}</li>)}</ul>}
          </div> : <p className="border border-line bg-white p-4 text-xs text-muted">The full incident report is available once the incident resolves.</p>}
          <Link to={`/summary${mock ? '?mock=1' : ''}`} className="inline-block border border-navy px-3 py-1.5 text-xs font-semibold text-navy">Open full incident summary ↗</Link>
        </div>}
      </div>
    </aside>
  </div>
}
