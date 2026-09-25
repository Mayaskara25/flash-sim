export type Shortcut = 'IC' | 'TL' | 'CS' | 'All' | 'approve' | 'skip' | 'note' | 'clock' | 'help'

export function shortcutFor(event: KeyboardEvent): Shortcut | null {
  if (event.altKey || event.ctrlKey || event.metaKey || event.repeat) return null
  const target = event.target
  if (target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.closest('[role="dialog"]'))) return null
  const key = event.key.toLowerCase()
  return ({ '1': 'IC', '2': 'TL', '3': 'CS', '0': 'All', a: 'approve', s: 'skip', n: 'note', ' ': 'clock', '?': 'help' } as Record<string, Shortcut>)[key] ?? null
}
