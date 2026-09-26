import { tagFullName, tagName } from '../format'
import type { TagView } from '../types'

/**
 * H14: chips read `M2 · Insurance fund drain` with the full catalogue name in
 * the tooltip (UI_PLAN §3, "Tags"). Inactive tags stay visible but recede —
 * a tag that appeared and cleared is part of the story.
 */
export function TagChips({ tags }: { tags: TagView[] }) {
  if (!tags.length) return <span className="text-xs" style={{ opacity: 0.65 }}>No scenario tags</span>
  // The banner row must not wrap. Three most-recent tags fit at 1280px; the
  // full set is always in Details › Log and the scenario picker.
  const shown = tags.slice(0, 3)
  const rest = tags.length - shown.length
  return <div className="flex flex-nowrap items-center gap-1.5 overflow-hidden" aria-label="Scenario tags">{shown.map((item) => (
    <span key={item.tag} title={`${item.tag} · ${tagFullName(item.tag)}`}
      className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-semibold"
      style={{
        borderColor: item.active ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.22)',
        background: item.active ? 'rgba(255,255,255,0.2)' : 'transparent',
        color: item.active ? '#fff' : 'rgba(255,255,255,0.6)',
      }}>
      <span>{item.tag}</span>
      <span aria-hidden="true" style={{ opacity: 0.55 }}>·</span>
      <span>{tagName(item.tag)}</span>
    </span>
  ))}
    {rest > 0 && <span className="shrink-0 whitespace-nowrap text-xs" style={{ opacity: 0.7 }} title={tags.slice(3).map((item) => `${item.tag} · ${tagFullName(item.tag)}`).join('\n')}>+{rest}</span>}
  </div>
}
