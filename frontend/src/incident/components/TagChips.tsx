import type { TagView } from '../types'

export function TagChips({ tags }: { tags: TagView[] }) {
  if (!tags.length) return <span className="text-xs opacity-65">No scenario tags</span>
  return <div className="flex flex-wrap gap-1.5" aria-label="Scenario tags">{tags.map((item) => (
    <span key={item.tag} title={item.name} className={`border px-2 py-0.5 text-[11px] font-semibold ${item.active ? 'border-white/50 bg-white/20 text-white' : 'border-white/20 text-white/55'}`}>
      {item.tag}
    </span>
  ))}</div>
}
