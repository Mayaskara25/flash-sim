import { useState } from 'react'
import type { CommandBrief } from '../types'
import { fmtNumber } from '../format'

const tone: Record<CommandBrief['risk_level'], string> = {
  NORMAL: 'border-slate-400 bg-slate-50 text-slate-800',
  WATCH: 'border-blue-400 bg-blue-50 text-blue-950',
  ACTION: 'border-amber-500 bg-amber-50 text-amber-950',
  CRITICAL: 'border-red-700 bg-red-50 text-red-950',
}

export function RiskBrief({ command, onInvestigate }: { command: CommandBrief; onInvestigate: () => void }) {
  const [analysis, setAnalysis] = useState(false)
  return <section className={`border-l-4 ${tone[command.risk_level]} bg-white p-3 md:p-4`} aria-label="P2 risk brief">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-[10px] font-bold uppercase tracking-[0.16em]">P2 risk brief</p><div className="mt-1 flex flex-wrap items-baseline gap-x-2"><strong className="text-xl tracking-tight">{command.risk_level}</strong><span className="font-mono text-lg">{fmtNumber(command.cascade_score)}/100</span>{command.incident_mode && <span className="border border-red-500 bg-red-700 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-white">INCIDENT MODE</span>}</div></div>
      <span className="max-w-xs text-right text-[10px] leading-snug text-muted">{command.label}</span>
    </div>
    <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
      <div><h2 className="text-[11px] font-bold uppercase tracking-[0.12em]">What is happening</h2><ol className="mt-1.5 space-y-1 text-xs leading-snug">{command.reasons.map((reason, index) => <li key={reason}><strong className="mr-1 text-navy">{index + 1}.</strong>{reason}</li>)}</ol></div>
      <div className="border-l-2 border-navy bg-slate-50 px-3 py-2"><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted">First priority</p><p className="mt-1 text-sm font-semibold text-navy">{command.first_priority}</p><p className="mt-1 text-xs leading-snug">{command.why_first}</p><p className="mt-2 text-xs"><strong>Next:</strong> {command.next_step}</p>{command.cluster && <button type="button" onClick={onInvestigate} className="mt-2 border border-navy bg-white px-2.5 py-1 text-[11px] font-bold text-navy">INVESTIGATE {command.cluster.id}</button>}</div>
    </div>
    <div className="mt-3 border-t border-line pt-2"><button type="button" onClick={() => setAnalysis((value) => !value)} className="text-xs font-semibold text-navy underline">{analysis ? 'Hide analysis' : 'View analysis'}</button>{analysis && <div className="mt-2 grid gap-2 md:grid-cols-3"><div className="border border-line bg-slate-50 p-2 text-[11px]"><strong>Liquidations</strong><br />{fmtNumber(command.liquidation_rate)}/min vs {fmtNumber(command.liquidation_baseline)} baseline</div><div className="border border-line bg-slate-50 p-2 text-[11px]"><strong>Threshold proximity</strong><br />{command.near_liquidation.toLocaleString()} modelled positions</div><div className="border border-line bg-slate-50 p-2 text-[11px]"><strong>Liquidity</strong><br />{fmtNumber(command.liquidity_change)}% modelled change</div><div className="md:col-span-3"><p className="mb-1 text-[10px] font-bold uppercase tracking-[0.12em] text-muted">Why important alerts fired</p><div className="grid gap-2 md:grid-cols-2">{command.why_alerts.map((alert) => <details key={alert.signal} className="border border-line bg-white px-2 py-1.5 text-[11px]"><summary className="cursor-pointer font-semibold">WHY · {alert.signal}</summary><p className="mt-1">{fmtNumber(alert.value)} {alert.unit} vs {fmtNumber(alert.baseline)} baseline{alert.change_pct != null ? ` (${alert.change_pct >= 0 ? '+' : ''}${fmtNumber(alert.change_pct)}%)` : ''}.</p><p className="mt-1 text-muted">{alert.conclusion}</p></details>)}</div></div></div>}</div>
  </section>
}
