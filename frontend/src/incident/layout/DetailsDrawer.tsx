import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import type { IncidentActions } from '../useIncident'
import type { CommandBrief, IncidentStateDTO, IncidentSummary, Role } from '../types'
import { AICopilot } from '../components/AICopilot'
import { ForecastStrip } from '../components/ForecastStrip'
import { FundRunwayChart } from '../components/FundRunwayChart'
import { IncidentLog } from '../components/IncidentLog'
import { IncidentReport } from '../components/IncidentReport'
import { LiquidationInvestigator } from '../components/LiquidationInvestigator'
import { SignalCard } from '../components/SignalCard'
import { TemplatePanel } from '../components/TemplatePanel'
import { Button } from '../ui'
import { DETAILS_TABS, TAB_LABELS, type DetailsTab } from './detailsTabs'

/**
 * H14: the drawer is the "everything else" home.
 *
 * Signals · Liquidations · Comms · Log · Report · Copilot. Every panel that
 * lost its slot in the main view lives here, at drawer scale, and nothing
 * here repeats a fact that is already on screen.
 */
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

  // Alerts are sorted worst-first so the drawer matches the main-view order.
  const alertsRank = { critical: 0, warn: 1, watch: 2, normal: 3 } as const
  const allSignals = [...state.signals].sort((a, b) => alertsRank[a.status] - alertsRank[b.status] || a.code.localeCompare(b.code))

  return <div className="fixed inset-0 z-40">
    <div className="absolute inset-0 bg-slate-950/40" onClick={onClose} />
    <aside ref={panelRef} role="dialog" aria-modal="true" aria-label="Incident details" tabIndex={-1}
      className="absolute right-0 top-0 flex h-full w-[45%] min-w-[420px] flex-col shadow-xl focus:outline-none" style={{ background: 'var(--bg)' }}>
      <div className="flex shrink-0 flex-wrap items-center gap-1 border-b px-3 py-2" style={{ borderColor: 'var(--line)', background: 'var(--surface)' }}>
        <div role="tablist" aria-label="Details sections" className="flex min-w-0 flex-1 flex-wrap gap-1">
          {DETAILS_TABS.map((id) => <button key={id} type="button" role="tab" aria-selected={tab === id}
            onClick={() => onTabChange(id)}
            className="text-xs font-semibold border px-2.5 py-1"
            style={{
              borderColor: tab === id ? 'var(--ink)' : 'var(--line)',
              background: tab === id ? 'var(--ink)' : 'var(--surface)',
              color: tab === id ? 'var(--bg)' : 'var(--muted)',
            }}>
            {TAB_LABELS[id]}
          </button>)}
        </div>
        <button type="button" onClick={onClose} aria-label="Close details (Esc)" className="text-xs font-semibold border px-2.5 py-1" style={{ borderColor: 'var(--line)' }}>✕</button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3" role="tabpanel" style={{ background: 'var(--bg)' }}>
        {tab === 'signals' && <div className="space-y-4">
          <div>
            <h2 className="text-label" style={{ color: 'var(--muted)' }}>All signals · {allSignals.length}</h2>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">{allSignals.map((signal) => <SignalCard key={signal.code} signal={signal} alerts={state.alerts} size="sm" />)}</div>
          </div>
          {state.forecast && <div>
            <h2 className="text-label" style={{ color: 'var(--muted)' }}>Fund runway</h2>
            <div className="mt-2 border p-3" style={{ borderColor: 'var(--line)', background: 'var(--surface)' }}>
              <FundRunwayChart fund={fund} forecast={state.forecast} t={state.sim.t} />
            </div>
            <div className="mt-2"><ForecastStrip forecast={state.forecast} fund={fund} t={state.sim.t} /></div>
          </div>}
        </div>}
        {tab === 'liquidations' && <div className="space-y-3">
          {cluster ? <LiquidationInvestigator cluster={cluster} busy={busy} onDecision={(id, decision) => void actions.decideExecution(id, { decision, actor: 'TL' }).catch(() => {})} />
            : <p className="text-body p-4" style={{ border: '1px solid var(--line)', color: 'var(--muted)' }}>No abnormal liquidation cluster is under investigation. One appears here when the engine flags fills.</p>}
          {cluster && <Button variant="secondary" onClick={onOpenInvestigator}>Record that TL opened this cluster</Button>}
        </div>}
        {tab === 'comms' && <TemplatePanel templates={state.templates} actor={messageActor} busy={busy}
          onSend={(id, actor, text) => actions.sendTemplate(id, { actor, text })}
          onDismiss={(id, actor, rationale) => actions.dismissTemplate(id, { actor, rationale })} />}
        {tab === 'log' && <IncidentLog log={state.log} alerts={state.alerts} signals={state.signals} role={role} busy={busy}
          onAck={(id, actor) => actions.ackAlert(id, { actor })}
          onNote={(text, actor) => actions.addNote({ actor, text })}
          onReview={(verdict, rationale) => actions.reviewLiquidation({ verdict, actor: logActor === 'system' ? 'IC' : logActor, rationale })} />}
        {tab === 'report' && <div className="space-y-3">
          {command && <IncidentReport state={state} command={command} reportUrl={actions.reportUrl()} />}
          {summary ? <div className="border p-3" style={{ borderColor: 'var(--line)', background: 'var(--surface)' }}>
            <h2 className="text-label" style={{ color: 'var(--muted)' }}>Summary</h2>
            <p className="text-body mt-1"><strong>{summary.scenario_id}</strong> · peak SEV-{summary.peak_sev}</p>
            {summary.open_items.length > 0 && <ul className="text-body mt-2 list-disc pl-5">{summary.open_items.map((item) => <li key={item}>{item}</li>)}</ul>}
          </div> : <p className="text-body p-4" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>The full incident report is available once the incident resolves.</p>}
          <Link to={`/summary${mock ? '?mock=1' : ''}`} className="text-body inline-block border px-3 py-1.5 font-semibold" style={{ borderColor: 'var(--ink)' }}>Open full incident summary ↗</Link>
        </div>}
        {tab === 'copilot' && <AICopilot onAsk={(question) => actions.copilot({ question })} />}
      </div>
    </aside>
  </div>
}
