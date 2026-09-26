import { useState } from 'react'
import { roleLabel } from '../format'
import { buildQueue, sliceForScreen, type QueueEntry } from '../panels'
import type { ActionQueueItem, ActionView, Role } from '../types'
import { Badge, Button } from '../ui'
import { ActionCard } from './ActionCard'
import type { ViewRole } from './RoleSwitcher'

/** Compact rows shown before the "+N queued" line (UI_PLAN rule 2). */
const ROWS = 2

/**
 * H14: the one action list.
 *
 * `P2ActionQueue.tsx` is gone — the backend command queue's NOW/NEXT/MONITOR
 * bands are now the *ordering* of this list, not a second panel competing for
 * the same screen. One hero card (the current role's top action), two compact
 * rows, then everything else behind "+N queued".
 */
export function ActionList({ actions, queue, viewRole, busy, pendingConfirm, onDecide, onQueueAction }: {
  actions: ActionView[]
  queue: ActionQueueItem[]
  viewRole: ViewRole
  busy: boolean
  pendingConfirm: boolean
  onDecide: (action: ActionView, decision: 'approve' | 'skip', rationale: string, actor: Role) => Promise<void>
  onQueueAction: (item: ActionQueueItem) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const entries = buildQueue(actions, queue, pendingConfirm)
  const { hero, rows, hidden } = sliceForScreen(entries, viewRole, 1, ROWS)
  const actorOf = (entry: QueueEntry): Role => (entry.kind === 'action' ? (viewRole === 'All' ? entry.action.role : viewRole) : entry.item.role)
  const decide = (entry: QueueEntry, decision: 'approve' | 'skip', rationale: string) =>
    entry.kind === 'action' ? onDecide(entry.action, decision, rationale, actorOf(entry)) : Promise.resolve()

  if (!entries.length) {
    return <p className="border border-dashed p-4 text-body" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
      Nothing to do for {viewRole === 'All' ? 'the team' : viewRole} right now. Actions appear here as the scenario proposes them.
    </p>
  }

  return <div className="space-y-2">
    {hero.map((entry) => entry.kind === 'action' && <ActionCard key={keyOf(entry)} action={entry.action} busy={busy} shortcutTarget variant="hero" onDecide={(decision, rationale) => decide(entry, decision, rationale)} />)}
    {rows.length > 0 && <div className="mt-2">
      <p className="text-label" style={{ color: 'var(--muted)' }}>Next</p>
      {rows.map((entry) => <QueueRow key={keyOf(entry)} entry={entry} busy={busy} onDecide={decide} onQueueAction={onQueueAction} />)}
    </div>}
    {hidden.length > 0 && <div>
      <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded} className="text-body font-semibold underline underline-offset-2" style={{ color: 'var(--ink)' }}>
        {expanded ? 'Hide queue' : `+${hidden.length} queued`}
      </button>
      {expanded && <div className="mt-1">{hidden.map((entry) => <QueueRow key={keyOf(entry)} entry={entry} busy={busy} onDecide={decide} onQueueAction={onQueueAction} />)}</div>}
    </div>}
  </div>
}

function keyOf(entry: QueueEntry): string {
  return entry.kind === 'action' ? `a:${entry.action.id}` : `q:${entry.item.id}`
}

/** A compact row for either a playbook action or a command-queue card. */
function QueueRow({ entry, busy, onDecide, onQueueAction }: {
  entry: QueueEntry
  busy: boolean
  onDecide: (entry: QueueEntry, decision: 'approve' | 'skip', rationale: string) => Promise<void>
  onQueueAction: (item: ActionQueueItem) => void
}) {
  if (entry.kind === 'action') {
    return <ActionCard action={entry.action} busy={busy} shortcutTarget={false} onDecide={(decision, rationale) => onDecide(entry, decision, rationale)} />
  }
  const { item } = entry
  return <article className="flex items-center gap-2 border-b border-line py-1.5" style={{ borderColor: 'var(--line)' }}>
    <p className="text-body min-w-0 flex-1 truncate font-medium leading-snug" title={`${item.text} — ${item.reason}`}>
      <span className="mr-1.5 inline-flex align-middle"><Badge tone={item.role === 'IC' ? 'sev1' : item.role === 'TL' ? 'sev2' : 'sev3'} title={roleLabel[item.role]}>{item.role}</Badge></span>
      {item.text}
    </p>
    {item.button && <Button variant="secondary" disabled={busy} onClick={() => onQueueAction(item)}>{item.button === 'RUN' ? 'Run' : 'Open'}</Button>}
  </article>
}
