import { useState } from 'react'
import { Link } from 'react-router-dom'
import { roleLabel } from './format'
import { useIncident } from './useIncident'
import type { Role } from './types'
import { ActionList } from './components/ActionList'
import { IncidentLog } from './components/IncidentLog'
import { RoleSwitcher, type ViewRole } from './components/RoleSwitcher'
import { SeverityBanner } from './components/SeverityBanner'
import { SignalGrid } from './components/SignalGrid'
import { TemplatePanel } from './components/TemplatePanel'

function initialRole(): ViewRole {
  try {
    const value = localStorage.getItem('incident-role')
    if (value === 'All' || value === 'IC' || value === 'TL' || value === 'CS') return value
  } catch { /* Private browsing may disallow storage. */ }
  return 'All'
}

export function IncidentConsole() {
  const incident = useIncident()
  const { state, actions, busy, mock, stale, error, scenarios } = incident
  const [role, setRole] = useState<ViewRole>(initialRole)
  const changeRole = (value: ViewRole) => { setRole(value); try { localStorage.setItem('incident-role', value) } catch { /* Optional preference. */ } }
  if (!state) return <main className="p-8 text-sm text-muted">Loading incident state…</main>
  const messageActor: Role = role === 'All' ? 'CS' : role
  return <div className="min-h-screen bg-bg text-ink">
    <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-white px-4 py-2 md:px-6"><div><div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">MochaTrade / Operations</div><h1 className="text-base font-bold tracking-tight">Flash-crash incident console</h1></div><Link to="/analyst/overview" className="border border-line px-3 py-1.5 text-xs font-semibold text-navy hover:bg-slate-50">Open analyst views ↗</Link></header>
    <SeverityBanner state={state} scenarios={scenarios} actions={actions} busy={busy} mock={mock} stale={stale} />
    {error && <div role="alert" className="flex items-center justify-between gap-3 border-b border-red-300 bg-red-50 px-4 py-2 text-xs text-red-900"><span>{error}</span><button type="button" onClick={actions.clearError} className="font-semibold underline">Dismiss</button></div>}
    <main className="grid gap-3 p-3 md:p-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <SignalGrid signals={state.signals} alerts={state.alerts} />
      <div className="min-w-0 space-y-3">
        <section className="border border-line bg-white p-3 md:p-4" aria-label="Next actions">
          <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xs font-bold uppercase tracking-[0.13em]">Next actions</h2><RoleSwitcher value={role} onChange={changeRole} /></div>
          <p className="mt-2 text-xs text-muted">{role === 'All' ? 'Three-person response team' : roleLabel[role]} · human approval required for every control and message.</p>
          {state.severity.pending && <div className="mt-3 border border-amber-300 bg-amber-50 p-3 text-xs"><strong>Step-down ready:</strong> {state.severity.pending.from} → {state.severity.pending.to}. IC confirmation required. <button type="button" disabled={busy || role !== 'IC'} onClick={() => void actions.confirmPending({ actor: 'IC' })} className="ml-2 border border-amber-700 px-2 py-1 font-semibold text-amber-950 disabled:opacity-50">Confirm as IC</button></div>}
          {state.reminders.length > 0 && <div className="mt-3 border-l-2 border-amber-500 bg-amber-50 p-2 text-[11px] text-amber-950">{state.reminders.join(' · ')}</div>}
          <div className="mt-3"><ActionList actions={state.actions} viewRole={role} busy={busy} onDecide={(action, decision, rationale, actor) => actions.decideAction(action.id, { decision, rationale, actor })} /></div>
        </section>
        <TemplatePanel templates={state.templates} actor={messageActor} busy={busy} onSend={(id, actor, text) => actions.sendTemplate(id, { actor, text })} onDismiss={(id, actor, rationale) => actions.dismissTemplate(id, { actor, rationale })} />
        <IncidentLog log={state.log} alerts={state.alerts} role={role} busy={busy} onAck={(id, actor) => actions.ackAlert(id, { actor })} onNote={(text, actor) => actions.addNote({ actor, text })} onReview={(verdict, rationale) => actions.reviewLiquidation({ verdict, actor: 'IC', rationale })} />
      </div>
    </main>
    {mock && <div className="fixed bottom-3 left-3 z-30 flex items-center gap-2 border border-amber-400 bg-amber-50 px-2 py-1.5 text-[11px] shadow"><span>Sample fixture mode</span><button type="button" onClick={() => void actions.nextFixture()} className="font-semibold text-navy underline">Next fixture</button><button type="button" onClick={() => void actions.inject({ event: 'stablecoin_dip' })} className="font-semibold text-navy underline">Emergency fixture</button></div>}
  </div>
}
