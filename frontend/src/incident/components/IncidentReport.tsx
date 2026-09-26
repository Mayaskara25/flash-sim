import type { CommandBrief, IncidentStateDTO } from '../types'

export function IncidentReport({ state, command, reportUrl }: { state: IncidentStateDTO; command: CommandBrief; reportUrl: string }) {
  const ready = state.severity.state === 'RESOLVED' || state.sim.t >= state.sim.duration_s
  if (!ready) return null
  return <section className="border border-navy bg-white p-3 md:p-4" aria-label="Incident summary and report"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xs font-bold uppercase tracking-[0.13em]">Incident summary</h2><p className="mt-1 text-sm font-semibold">{state.sim.scenario_name ?? 'Simulation'} · {state.sim.t_label}</p><p className="mt-1 text-xs text-muted">The report preserves peak metrics, timeline, decisions, communications and modelled evidence.</p></div><a href={reportUrl} target="_blank" rel="noreferrer" className="bg-navy px-3 py-2 text-xs font-semibold text-white">GENERATE PDF REPORT</a></div><div className="mt-3 grid grid-cols-2 gap-2 text-[11px] md:grid-cols-4"><Metric label="Current cascade" value={`${command.cascade_score.toFixed(0)}/100`} /><Metric label="Liquidation rate" value={`${command.liquidation_rate.toFixed(0)}/min`} /><Metric label="Flagged executions" value={String(command.abnormal_liquidations)} /><Metric label="Near threshold" value={command.near_liquidation.toLocaleString()} /></div></section>
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="border border-line bg-slate-50 p-2"><p className="text-[10px] uppercase tracking-wide text-muted">{label}</p><p className="mt-1 font-semibold">{value}</p></div> }
