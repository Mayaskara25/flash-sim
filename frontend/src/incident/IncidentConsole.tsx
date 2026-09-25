import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { roleLabel } from './format'
import { useIncident } from './useIncident'
import { shortcutFor } from './shortcuts'
import { Toasts } from './Toasts'
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
  const [help, setHelp] = useState(false)
  const changeRole = (value: ViewRole) => { setRole(value); try { localStorage.setItem('incident-role', value) } catch { /* Optional preference. */ } }
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (help && event.key === 'Escape') { setHelp(false); return }
      if (help) return
      const shortcut = shortcutFor(event)
      if (!shortcut) return
      if (shortcut === 'IC' || shortcut === 'TL' || shortcut === 'CS' || shortcut === 'All') changeRole(shortcut)
      else if (shortcut === 'help') setHelp(true)
      else if (shortcut === 'note') { event.preventDefault(); document.getElementById('incident-note')?.focus() }
      else if (shortcut === 'clock' && state?.sim.started && !busy) { event.preventDefault(); void actions.clock({ op: state.sim.running ? 'pause' : 'resume' }).catch(() => {}) }
      else if ((shortcut === 'approve' || shortcut === 'skip') && !busy) { event.preventDefault(); window.dispatchEvent(new CustomEvent('incident-action-shortcut', { detail: shortcut })) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [actions, busy, help, state?.sim.running, state?.sim.started])
  if (!state) return <main className="min-h-screen bg-bg p-8 text-sm text-muted"><h1 className="text-base font-bold text-ink">Flash-crash incident console</h1><p className="mt-3">{error ? 'Unable to load incident state.' : 'Loading incident state…'}</p><Toasts error={error} onDismiss={actions.clearError} /></main>
  const messageActor: Role = role === 'All' ? 'CS' : role
  return <div className="min-h-screen bg-bg text-ink">
    <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-white px-4 py-2 md:px-6"><div><div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">MochaTrade / Operations</div><h1 className="text-base font-bold tracking-tight">Flash-crash incident console</h1></div><Link to="/analyst/overview" className="border border-line px-3 py-1.5 text-xs font-semibold text-navy hover:bg-slate-50">Open analyst views ↗</Link></header>
    <SeverityBanner state={state} scenarios={scenarios} actions={actions} busy={busy} mock={mock} stale={stale} />
    <Toasts error={error} onDismiss={actions.clearError} />
    <main className="grid gap-3 p-3 md:p-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <SignalGrid signals={state.signals} alerts={state.alerts} />
      <div className="min-w-0 space-y-3">
        <section className="border border-line bg-white p-3 md:p-4" aria-label="Next actions">
          <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xs font-bold uppercase tracking-[0.13em]">Next actions</h2><RoleSwitcher value={role} onChange={changeRole} /></div>
          <p className="mt-2 text-xs text-muted">{role === 'All' ? 'Three-person response team' : roleLabel[role]} · human approval required for every control and message.</p>
          {state.severity.pending && <div className="mt-3 border border-amber-300 bg-amber-50 p-3 text-xs"><strong>Step-down ready:</strong> {state.severity.pending.from} → {state.severity.pending.to}. IC confirmation required. <button type="button" disabled={busy || role !== 'IC'} onClick={() => void actions.confirmPending({ actor: 'IC' }).catch(() => {})} className="ml-2 border border-amber-700 px-2 py-1 font-semibold text-amber-950 disabled:opacity-50">Confirm as IC</button></div>}
          {state.reminders.length > 0 && <div className="mt-3 border-l-2 border-amber-500 bg-amber-50 p-2 text-[11px] text-amber-950">{state.reminders.join(' · ')}</div>}
          <div className="mt-3"><ActionList actions={state.actions} viewRole={role} busy={busy} onDecide={(action, decision, rationale, actor) => actions.decideAction(action.id, { decision, rationale, actor })} /></div>
        </section>
        <TemplatePanel templates={state.templates} actor={messageActor} busy={busy} onSend={(id, actor, text) => actions.sendTemplate(id, { actor, text })} onDismiss={(id, actor, rationale) => actions.dismissTemplate(id, { actor, rationale })} />
        <IncidentLog log={state.log} alerts={state.alerts} role={role} busy={busy} onAck={(id, actor) => actions.ackAlert(id, { actor })} onNote={(text, actor) => actions.addNote({ actor, text })} onReview={(verdict, rationale) => actions.reviewLiquidation({ verdict, actor: 'IC', rationale })} />
      </div>
    </main>
    {mock && <div className="fixed bottom-3 left-3 z-30 flex items-center gap-2 border border-amber-400 bg-amber-50 px-2 py-1.5 text-[11px] shadow"><span>Sample fixture mode</span><button type="button" onClick={() => void actions.nextFixture()} className="font-semibold text-navy underline">Next fixture</button><button type="button" onClick={() => void actions.inject({ event: 'stablecoin_dip' })} className="font-semibold text-navy underline">Emergency fixture</button></div>}
    <button type="button" className="fixed bottom-3 right-3 z-30 border border-line bg-white px-2 py-1 text-xs font-bold shadow" onClick={() => setHelp(true)} aria-label="Keyboard shortcuts">?</button>
    {help && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setHelp(false) }}><div role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" className="w-full max-w-sm bg-white p-5 text-sm shadow-xl"><h2 className="font-bold">Keyboard shortcuts</h2><p className="mt-3 leading-7">1 IC · 2 TL · 3 CS · 0 All<br />A approve top action · S skip top action<br />N add a note · Space pause or resume<br />? show shortcuts · Esc close</p><button type="button" onClick={() => setHelp(false)} className="mt-4 border border-line px-3 py-1.5 text-xs font-semibold">Close</button></div></div>}
  </div>
}


