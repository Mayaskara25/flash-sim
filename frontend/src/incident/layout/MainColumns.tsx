import { roleLabel } from '../format'
import { roleFocus } from '../roleFocus'
import type { IncidentActions } from '../useIncident'
import type { CommandBrief, IncidentStateDTO } from '../types'
import { ActionList } from '../components/ActionList'
import { IncidentTimeline } from '../components/IncidentTimeline'
import { RoleSwitcher, type ViewRole } from '../components/RoleSwitcher'
import { SignalGrid } from '../components/SignalGrid'
import { TeamStatus } from '../components/TeamStatus'
import type { DetailsTab } from './detailsTabs'

export function MainColumns({ state, command, role, busy, actions, onRoleChange, onOpenDetails }: {
  state: IncidentStateDTO
  command: CommandBrief | null
  role: ViewRole
  busy: boolean
  actions: IncidentActions
  onRoleChange: (role: ViewRole) => void
  onOpenDetails: (tab?: DetailsTab) => void
}) {
  const drafts = state.templates.filter((template) => template.status === 'surfaced').length
  const focus = roleFocus(state.sim.t, role)
  return <main className="grid min-h-0 flex-1 gap-3 overflow-y-auto p-3 md:p-4 lg:grid-cols-[minmax(0,4fr)_minmax(0,5fr)_minmax(0,4fr)] lg:overflow-hidden">
    <div className="min-w-0 lg:min-h-0 lg:overflow-y-auto">
      <SignalGrid signals={state.signals} alerts={state.alerts} limit={4} onMore={() => onOpenDetails('signals')} />
    </div>
    <section className="min-w-0 border border-line bg-white p-3 md:p-4 lg:min-h-0 lg:overflow-y-auto" aria-label="Do now">
      <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xs font-bold uppercase tracking-[0.13em]">Do now · {role}</h2><RoleSwitcher value={role} onChange={onRoleChange} /></div>
      <p className="mt-2 text-xs text-muted">{role === 'All' ? 'Three-person response team' : roleLabel[role]} · human approval required for every control and message.</p>
      <p className="mt-1 border-l-2 border-navy bg-slate-50 px-2 py-1.5 text-[11px] leading-snug"><strong>{focus.phase}:</strong> {focus.text}</p>
      {state.severity.pending && <div className="mt-3 border border-amber-300 bg-amber-50 p-3 text-xs"><strong>Step-down ready:</strong> {state.severity.pending.from} → {state.severity.pending.to}. IC confirmation required. <button type="button" disabled={busy || role !== 'IC'} onClick={() => void actions.confirmPending({ actor: 'IC' }).catch(() => {})} className="ml-2 border border-amber-700 px-2 py-1 font-semibold text-amber-950 disabled:opacity-50">Confirm as IC</button></div>}
      {state.reminders.length > 0 && <div className="mt-3 border-l-2 border-amber-500 bg-amber-50 p-2 text-[11px] text-amber-950">{state.reminders.join(' · ')}</div>}
      <div id="response-actions" className="mt-3"><ActionList actions={state.actions} viewRole={role} busy={busy} onDecide={(action, decision, rationale, actor) => actions.decideAction(action.id, { decision, rationale, actor })} /></div>
      <div className="mt-3 border-t border-line pt-2">
        {drafts > 0
          ? <button type="button" onClick={() => onOpenDetails('comms')} className="text-xs font-semibold text-navy underline underline-offset-2">{drafts} draft{drafts === 1 ? '' : 's'} waiting · open Details › Comms</button>
          : <p className="text-xs text-muted">No message drafts due.</p>}
      </div>
    </section>
    <div className="min-w-0 space-y-3 lg:min-h-0 lg:overflow-y-auto">
      <IncidentTimeline log={state.log} limit={6} />
      <button type="button" onClick={() => onOpenDetails('log')} className="text-xs font-semibold text-navy underline underline-offset-2">Full log in Details ▸</button>
      {command && <TeamStatus team={command.team} />}
    </div>
  </main>
}
