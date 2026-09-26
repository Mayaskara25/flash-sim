/**
 * H14: shared presentation logic for the consolidated panels.
 *
 * `docs/UI_PLAN.md` §3 says each fact has exactly one home and that the
 * console shows one primary action. The rules that used to live inside
 * `P2ActionQueue.tsx` (NOW/NEXT/MONITOR bands) and `ActionList.tsx`
 * (per-role slicing) are merged here, together with the hero-ranking rule
 * from the H14 handoff:
 *
 *   1. an action that carries a control *and* a modelled what-if;
 *   2. any other action that carries a control;
 *   3. pending IC confirmations;
 *   4. communication drafts;
 *   5. everything else, including generic "acknowledge" items.
 *
 * Generic acknowledgement items deliberately rank last, but they still sort
 * among themselves by priority, so they are the hero when nothing else is on
 * offer.
 */
import type { ActionQueueItem, ActionView, Role, SignalStatus, TeamMember } from './types'
import type { ViewRole } from './components/RoleSwitcher'
import type { BadgeTone, StatStatus } from './ui'

/** Status words, so severity is never carried by colour alone (UI_PLAN rule 5). */
export const STATUS_WORD: Record<SignalStatus, string> = {
  normal: 'Normal', watch: 'Watch', warn: 'Warn', critical: 'Critical',
}

/**
 * Only warn and critical are coloured. `normal` and `watch` are neutral, so
 * red / amber / green in the tile grid always means "act on this" (rule 5).
 */
export const STATUS_TONE: Record<SignalStatus, BadgeTone> = {
  normal: 'neutral', watch: 'neutral', warn: 'warn', critical: 'crit',
}

export const STAT_STATUS: Record<SignalStatus, StatStatus> = {
  normal: 'normal', watch: 'watch', warn: 'warn', critical: 'critical',
}

/** A `Role` is never "system" in a human-facing list; the engine speaks as SYS. */
export const PERSON_ROLES: Role[] = ['IC', 'TL', 'CS']

const BAND_RANK: Record<ActionQueueItem['band'], number> = { NOW: 0, NEXT: 1, MONITOR: 2 }

const GENERIC = /^(acknowledge|ack |monitor|watch |review alert|continue )/i

export type QueueEntry =
  | { kind: 'action'; action: ActionView; band: ActionQueueItem['band']; rank: number }
  | { kind: 'queue'; item: ActionQueueItem; band: ActionQueueItem['band']; rank: number }

/** Hero rank: lower is more urgent. See the module docblock. */
export function heroRank(action: ActionView, pendingConfirm: boolean): number {
  if (action.control_id && action.what_if) return 0
  if (action.control_id) return 1
  if (pendingConfirm && action.role === 'IC') return 2
  if (action.template_id) return 3
  if (GENERIC.test(action.text.trim())) return 5
  return 4
}

/** Band lookup for a proposed action, from the backend command queue. */
function bandOf(queue: ActionQueueItem[], id: string): ActionQueueItem['band'] {
  return queue.find((item) => item.id === id)?.band ?? 'NEXT'
}

/**
 * One merged, ordered list of everything the operator can act on for
 * `viewRole` — approve-able playbook actions and the command queue's
 * non-actionable cards in a single sequence (UI_PLAN §3, "Actions: one list").
 */
export function buildQueue(actions: ActionView[], queue: ActionQueueItem[], pendingConfirm: boolean): QueueEntry[] {
  const proposed = actions.filter((action) => action.status === 'proposed')
  const decidable: QueueEntry[] = proposed
    .map((action) => ({
      kind: 'action' as const, action, band: bandOf(queue, action.id),
      rank: heroRank(action, pendingConfirm),
    }))
    // Queue cards that are not playbook actions (cluster review, stress run,
  // ticket monitor) stay in the same list, ranked after anything approvable.
    .sort((a, b) => a.rank - b.rank || BAND_RANK[a.band] - BAND_RANK[b.band] || a.action.priority - b.action.priority)

  const seen = new Set(proposed.map((action) => action.id))
  const advisory: QueueEntry[] = queue
    .filter((item) => !seen.has(item.id))
    .map((item) => ({ kind: 'queue' as const, item, band: item.band, rank: 10 + BAND_RANK[item.band] }))
    .sort((a, b) => a.rank - b.rank || (a.kind === 'queue' && b.kind === 'queue' ? a.item.priority - b.item.priority : 0))

  return [...decidable, ...advisory]
}

/**
 * Slice the list for one screen: `heroCount` hero cards plus `rowsPerGroup`
 * compact rows. With `viewRole === 'All'` the rows are budgeted per role, so
 * the "All" view cannot grow without bound (H12/H13 review finding 2).
 */
export function sliceForScreen(entries: QueueEntry[], viewRole: ViewRole, heroCount: number, rowsPerGroup: number) {
  const groups: Role[] = viewRole === 'All' ? PERSON_ROLES : [viewRole]
  const roleOf = (entry: QueueEntry) => (entry.kind === 'action' ? entry.action.role : entry.item.role)
  const hero: QueueEntry[] = []
  const rows: QueueEntry[] = []
  const taken = new Set<QueueEntry>()
  const budget = new Map<Role, number>()
  for (const entry of entries) {
    if (!groups.includes(roleOf(entry))) continue
    // Only an approvable action can be the hero — a command-queue card has
    // no Approve button, so it stays a compact row.
    if (entry.kind === 'action' && hero.length < heroCount) { hero.push(entry); taken.add(entry); continue }
    const role = roleOf(entry)
    const used = budget.get(role) ?? 0
    if (used >= rowsPerGroup) continue
    budget.set(role, used + 1)
    rows.push(entry)
  }
  const shown = new Set<QueueEntry>([...hero, ...rows])
  return { hero, rows, hidden: entries.filter((entry) => !taken.has(entry) && !shown.has(entry)) }
}

/** `IC ● Busy` — the team lives inside the role switcher from H14 on. */
export function teamDotClass(status: string): string {
  if (status === 'Available' || status === 'Active') return 'bg-slate-400'
  if (status === 'Busy') return 'bg-warn'
  return 'bg-slate-300'
}

export const STATUS_DOT_WORD: Record<string, string> = { Active: 'Active', Available: 'Available', Busy: 'Busy', Standby: 'Standby' }

export function teamByRole(team: TeamMember[] | undefined): Partial<Record<Role, TeamMember>> {
  const out: Partial<Record<Role, TeamMember>> = {}
  for (const member of team ?? []) if (member.role !== 'system') out[member.role] = member
  return out
}
