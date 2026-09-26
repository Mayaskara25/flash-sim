import { roleLabel } from '../format'
import { roleFocus } from '../roleFocus'
import type { IncidentActions } from '../useIncident'
import type { ActionQueueItem, CommandBrief, IncidentStateDTO } from '../types'
import { ActionList } from '../components/ActionList'
import { IncidentTimeline } from '../components/IncidentTimeline'
import { RoleSwitcher, type ViewRole } from '../components/RoleSwitcher'
import { SignalGrid } from '../components/SignalGrid'
import type { DetailsTab } from './detailsTabs'

/**
 * H14: the three main columns.
 *
 * Left — four key-signal tiles. Centre — one hero action, two compact rows
 * and "+N queued" (the merged action list; `P2ActionQueue` no longer exists).
 * Right — the last six key events. Everything else is one click away in the
 * details drawer, so each fact has exactly one home (UI_PLAN §2, §3).
 */
export function MainColumns({ state, command, role, busy, actions, onRoleChange, onOpenDetails, onQueueAction }: {
  state: IncidentStateDTO
  command: CommandBrief | null
  role: ViewRole
  busy: boolean
  actions: IncidentActions
  onRoleChange: (role: ViewRole) => void
  onOpenDetails: (tab?: DetailsTab) => void
  onQueueAction: (item: ActionQueueItem) => void
}) {
  const drafts = state.templates.filter((template) => template.status === 'surfaced').length
  const focus = roleFocus(state.sim.t, role)
  const pendingConfirm = state.severity.pending !== null
  return <main className="grid min-h-0 flex-1 gap-3 overflow-y-auto p-3 md:p-4 lg:grid-cols-[minmax(0,4fr)_minmax(0,5fr)_minmax(0,4fr)] lg:overflow-hidden">
    <div className="min-w-0 lg:min-h-0 lg:overflow-y-auto">
      <SignalGrid signals={state.signals} alerts={state.alerts} limit={4} onMore={() => onOpenDetails('signals')} />
    </div>
    <section className="min-w-0 border p-3 md:p-4 lg:min-h-0 lg:overflow-y-auto" style={{ borderColor: 'var(--line)', background: 'var(--surface)' }} aria-label="Do now">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-label" style={{ color: 'var(--muted)' }}>Do now · {role}</h2>
        <RoleSwitcher value={role} onChange={onRoleChange} team={command?.team} />
      </div>
      <p className="text-body mt-1.5 truncate border-l-2 py-1 pl-2 leading-snug" style={{ borderColor: 'var(--ink)' }}
        title={`${focus.phase} · ${role === 'All' ? 'Team' : roleLabel[role]}: ${focus.text}`}>
        <strong>{focus.phase} · {role === 'All' ? 'Team' : roleLabel[role]}:</strong> {focus.text}
      </p>
      {pendingConfirm && <div className="mt-3 border p-3" style={{ borderColor: 'var(--warn-border)', background: 'var(--warn-bg)' }}>
        <p className="text-body"><strong>Step-down ready:</strong> {state.severity.pending?.from} → {state.severity.pending?.to}. IC confirmation required.</p>
        <button type="button" disabled={busy || role !== 'IC'} onClick={() => void actions.confirmPending({ actor: 'IC' }).catch(() => {})}
          className="text-body mt-2 border px-2.5 py-1.5 font-semibold disabled:opacity-50" style={{ borderColor: 'var(--warn-fg)', color: 'var(--warn-fg)' }}>Confirm as IC</button>
      </div>}
      {state.reminders.length > 0 && <p className="text-body mt-3 border-l-2 py-1.5 pl-2" style={{ borderColor: 'var(--warn-fg)', background: 'var(--warn-bg)', color: 'var(--warn-fg)' }}>{state.reminders.join(' · ')}</p>}
      <div id="response-actions" className="mt-2">
        <ActionList actions={state.actions} queue={command?.queue ?? []} viewRole={role} busy={busy} pendingConfirm={pendingConfirm}
          onDecide={(action, decision, rationale, actor) => actions.decideAction(action.id, { decision, rationale, actor })}
          onQueueAction={onQueueAction} />
      </div>
      <div className="mt-2 border-t pt-2" style={{ borderColor: 'var(--line)' }}>
        {drafts > 0
          ? <button type="button" onClick={() => onOpenDetails('comms')} className="text-body font-semibold underline underline-offset-2" style={{ color: 'var(--ink)' }}>{drafts} draft{drafts === 1 ? '' : 's'} waiting · open Details › Comms</button>
          : <p className="text-body" style={{ color: 'var(--muted)' }}>No message drafts due.</p>}
      </div>
    </section>
    <div className="min-w-0 space-y-3 lg:min-h-0 lg:overflow-y-auto">
      <IncidentTimeline log={state.log} signals={state.signals} limit={6} />
      <button type="button" onClick={() => onOpenDetails('log')} className="text-body font-semibold underline underline-offset-2" style={{ color: 'var(--ink)' }}>Full log in Details ▸</button>
    </div>
  </main>
}
