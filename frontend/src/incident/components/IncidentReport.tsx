import type { CommandBrief, IncidentStateDTO } from '../types'

/**
 * H14: available once the incident resolves or the run reaches its duration.
 * Lives in Details › Report; the link to the full end-of-incident summary
 * screen sits next to it on the console.
 */
export function IncidentReport({ state, command, reportUrl }: { state: IncidentStateDTO; command: CommandBrief; reportUrl: string }) {
  const ready = state.severity.state === 'RESOLVED' || state.sim.t >= state.sim.duration_s
  if (!ready) return null
  return <section aria-label="Incident summary and report" style={{ background: 'var(--surface)', border: '1px solid var(--ink)', borderRadius: 8, padding: 16 }}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-label" style={{ color: 'var(--muted)' }}>Incident summary</h2>
        <p className="text-body-lg mt-1 font-semibold">{state.sim.scenario_name ?? 'Simulation'} · {state.sim.t_label}</p>
        <p className="text-body mt-1" style={{ color: 'var(--muted)' }}>The report preserves peak metrics, timeline, decisions, communications and modelled evidence.</p>
      </div>
      <a href={reportUrl} target="_blank" rel="noreferrer" className="text-body inline-block px-3 py-2 font-semibold" style={{ background: 'var(--ink)', color: 'var(--bg)', borderRadius: 6 }}>Download PDF report ↗</a>
    </div>
    <div className="mt-3 grid grid-cols-2 gap-2 text-body md:grid-cols-4">
      <Metric label="Current cascade" value={`${command.cascade_score.toFixed(0)}/100`} />
      <Metric label="Liquidation rate" value={`${command.liquidation_rate.toFixed(0)}/min`} />
      <Metric label="Flagged executions" value={String(command.abnormal_liquidations)} />
      <Metric label="Near threshold" value={command.near_liquidation.toLocaleString()} />
    </div>
  </section>
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 6, padding: 8 }}>
    <p className="text-label" style={{ color: 'var(--muted)' }}>{label}</p>
    <p className="text-body-lg mt-1 font-semibold">{value}</p>
  </div>
}
