import type { ActionView, Role } from '../types'
import type { ViewRole } from './RoleSwitcher'
import { ActionCard } from './ActionCard'

export function ActionList({ actions, viewRole, busy, onDecide }: { actions: ActionView[]; viewRole: ViewRole; busy: boolean; onDecide: (action: ActionView, decision: 'approve' | 'skip', rationale: string, actor: Role) => Promise<void> }) {
  const proposed = actions.filter((action) => action.status === 'proposed' && (viewRole === 'All' || action.role === viewRole)).sort((a, b) => a.priority - b.priority)
  const counts: Record<string, number> = {}
  const visible = proposed.filter((action) => { counts[action.role] = (counts[action.role] ?? 0) + 1; return counts[action.role] <= 3 })
  const queued = proposed.length - visible.length
  return <div className="space-y-2">{visible.length ? visible.map((action, index) => <ActionCard key={action.id} action={action} busy={busy} shortcutTarget={index === 0} onDecide={(decision, rationale) => onDecide(action, decision, rationale, viewRole === 'All' ? action.role : viewRole)} />) : <p className="border border-dashed border-line p-4 text-sm text-muted">No proposed actions for this role.</p>}{queued > 0 && <p className="text-xs text-muted">+{queued} queued actions · shown after higher-priority items</p>}</div>
}
