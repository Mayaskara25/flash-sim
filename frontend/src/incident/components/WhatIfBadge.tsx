import type { WhatIf } from '../types'

export function WhatIfBadge({ value }: { value: WhatIf | null }) {
  if (!value) return null
  const before = Math.round(value.p_sev1_15_before * 100)
  const after = Math.round(value.p_sev1_15_after * 100)
  return <div className={`mt-2 border px-2 py-1.5 text-[11px] font-semibold ${after < before ? 'border-green-300 bg-green-50 text-green-900' : 'border-red-300 bg-red-50 text-red-900'}`} title={`${value.text} Fund p50 at 15 min: ${value.fund_p50_15_before}% → ${value.fund_p50_15_after}%.`}>
    P(SEV-1 in 15m) {before}% → {after}% <span className="font-normal">· fund p50 {value.fund_p50_15_before}% → {value.fund_p50_15_after}%</span>
  </div>
}
