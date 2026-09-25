import { severityTone } from '../format'
import type { IncidentActions } from '../useIncident'
import type { IncidentStateDTO, ScenarioSummary } from '../types'
import { SimClockControls } from './SimClockControls'
import { TagChips } from './TagChips'
import { ForecastStrip } from './ForecastStrip'
import { AssumptionsPanel } from './AssumptionsPanel'

export function SeverityBanner({ state, scenarios, actions, busy, mock, stale }: { state: IncidentStateDTO; scenarios: ScenarioSummary[]; actions: IncidentActions; busy: boolean; mock: boolean; stale: boolean }) {
  const { severity, classifier, sim } = state
  return <section className={`border-b-4 px-4 py-3 md:px-6 ${severityTone[severity.sev] ?? severityTone[4]}`} aria-label="Incident status">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-2xl font-bold tracking-tight md:text-3xl">SEV-{severity.sev} · {severity.state}</span>
          <span className="font-mono text-lg tabular">{sim.t_label}</span>
          <span className="text-xs opacity-75">{sim.scenario_name ?? 'No incident running'}</span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-3"><TagChips tags={state.tags} /><span className="text-xs font-semibold">{classifier.verdict} · LAR {classifier.lar.toFixed(1)}</span></div>
        <p className="mt-1 max-w-3xl text-xs leading-relaxed opacity-80">{classifier.explanation}</p>
        {severity.overrides.length > 0 && <div className="mt-2 flex flex-wrap gap-1">{severity.overrides.map((x) => <span key={x} className="border border-red-300 bg-red-800 px-2 py-0.5 text-[11px]">Override: {x}</span>)}</div>}
        <div className="mt-2 flex flex-wrap gap-1.5 text-[10px] tracking-wide"><AssumptionsPanel />{mock && <span className="border border-white/35 px-1.5 py-0.5">SAMPLE DATA</span>}{stale && <span className="border border-amber-200 bg-amber-500 px-1.5 py-0.5 text-black">CONNECTION STALE</span>}</div>
      </div>
      <SimClockControls state={state} scenarios={scenarios} actions={actions} busy={busy} />
    </div>
    <ForecastStrip forecast={state.forecast} fund={state.signals.find((signal) => signal.code === 'INS_FUND_PCT')} t={sim.t} />
  </section>
}
