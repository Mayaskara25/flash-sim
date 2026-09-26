import type { WhatIf } from '../types'

/**
 * H14: the modelled what-if for the hero action. `hero` renders
 * `68% → 21%` at `text-stat` so a stranger can read the effect of approving
 * from across a room; the compact form is used inside the details drawer.
 */
export function WhatIfBadge({ value, hero = false }: { value: WhatIf | null; hero?: boolean }) {
  if (!value) return null
  const before = Math.round(value.p_sev1_15_before * 100)
  const after = Math.round(value.p_sev1_15_after * 100)
  const better = after < before
  // The backend sends raw float precision; the tile shows whole percents.
  const fundBefore = Math.round(value.fund_p50_15_before)
  const fundAfter = Math.round(value.fund_p50_15_after)
  if (!hero) {
    return <p className="text-body mt-2 font-semibold" style={{ color: better ? 'var(--ok-fg)' : 'var(--crit-fg)' }}
      title={`${value.text} Fund p50 at 15 min: ${fundBefore}% → ${fundAfter}%.`}>
      P(SEV-1 in 15 min) {before}% → {after}% · fund p50 {fundBefore}% → {fundAfter}%
    </p>
  }
  return <div className="mt-2.5 border px-2.5 py-1.5" style={{ borderColor: 'var(--line)', borderLeft: `4px solid ${better ? 'var(--ok-fg)' : 'var(--crit-fg)'}`, borderRadius: 8 }}>
    <p className="flex flex-wrap items-baseline gap-x-2">
      <span className="text-label" style={{ color: 'var(--muted)' }}>If approved</span>
      <span className="text-body-lg" style={{ color: 'var(--muted)' }}>P(SEV-1 ≤15m)</span>
      <span className="text-stat tabular" style={{ color: 'var(--muted)' }}>{before}%</span>
      <span className="text-body-lg" aria-hidden="true">→</span>
      <span className="text-stat tabular" style={{ color: better ? 'var(--ok-fg)' : 'var(--crit-fg)' }}>{after}%</span>
      <span className="text-body" style={{ color: 'var(--muted)' }}>· fund p50 {fundBefore}% → {fundAfter}%</span>
    </p>
  </div>
}
