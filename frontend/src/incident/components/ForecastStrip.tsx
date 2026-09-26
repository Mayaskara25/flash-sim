import { useState } from 'react'
import type { Forecast, SignalView } from '../types'
import { FundRunwayChart } from './FundRunwayChart'

const colours = ['bg-red-500', 'bg-orange-400', 'bg-amber-300', 'bg-green-400']
const percent = (value: number) => `${Math.round(value * 100)}%`
const eta = (value: number | null) => value == null ? 'beyond horizon' : `${Math.round(value)} min`

export function ForecastStrip({ forecast, fund, t, compact = false }: { forecast: Forecast | null; fund: SignalView | undefined; t: number; compact?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  if (!forecast) return null
  const point = forecast.sev_probs.find((item) => item.h === 15) ?? forecast.sev_probs.at(-1)
  const risk = forecast.eta_sev1_min.prob_within_15
  if (compact) return <p className="truncate text-xs font-medium leading-snug" title={`${forecast.headline} · SEV-1 within 15 min ${percent(risk)}.`} aria-label="Simulated forecast">⚠ {forecast.headline} · SEV-1 ≤15m: {percent(risk)}</p>
  const drivers = forecast.drivers.map((driver) => `${driver.signal}: ${driver.text} (${percent(driver.contribution)})`).join(' · ')
  return <div className="mt-3 border border-white/30 bg-white/10 p-2.5" aria-label="Simulated forecast">
    <button type="button" className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 text-left" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)} title={`${forecast.label}. ${drivers}. Cascade model probability ${percent(forecast.cascade_model_p)}.`}>
      <span className="min-w-48 flex-1 text-sm font-semibold leading-snug">{forecast.headline}</span>
      {point && <span className="w-28 shrink-0"><span className="block text-[10px]">Severity in 15 min</span><span className="mt-1 flex h-2.5 overflow-hidden" role="img" aria-label={`SEV-1 ${percent(point.p['1'])}, SEV-2 ${percent(point.p['2'])}, SEV-3 ${percent(point.p['3'])}, SEV-4 ${percent(point.p['4'])}`}>{(['1', '2', '3', '4'] as const).map((level, index) => <span key={level} className={colours[index]} style={{ width: percent(point.p[level]) }} />)}</span></span>}
      <span className={`text-xs font-bold ${risk >= .5 ? 'text-amber-200' : 'text-green-200'}`}>SEV-1 ≤15m: {percent(risk)}</span>
      <span className="flex items-center gap-2 text-xs"><span>Fund → 25%: {eta(forecast.eta_fund_25_min.p50)} p50 / {eta(forecast.eta_fund_25_min.p90)} p90</span><svg width="75" height="26" viewBox="0 0 75 26" aria-label="Fund p50 projected runway"><line x1="0" y1="19.5" x2="75" y2="19.5" stroke="#fca5a5" strokeDasharray="3 2" /><polyline points={[`0,${26 - Math.min(100, fund?.value ?? 100) * .26}`, ...forecast.ins_fund.map((point) => `${point.h * 5},${26 - Math.min(100, point.p50) * .26}`)].join(' ')} fill="none" stroke="#93c5fd" strokeWidth="2" /></svg></span>
      <span className="text-xs font-semibold underline">{expanded ? 'Hide runway' : 'Expand runway ↓'}</span>
    </button>
    <p className="mt-1 text-[10px] opacity-75">{forecast.label} · {forecast.n_paths} paths · computed at {Math.round(forecast.computed_t / 60)} min</p>
    {expanded && <div className="mt-3 border-t border-white/25 pt-3"><FundRunwayChart fund={fund} forecast={forecast} t={t} /><p className="mt-2 text-[11px] opacity-85">Drivers: {drivers}. Cascade model p {percent(forecast.cascade_model_p)}.</p></div>}
  </div>
}
