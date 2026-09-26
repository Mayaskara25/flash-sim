import { severityTone } from '../format'
import type { IncidentActions } from '../useIncident'
import type { IncidentStateDTO, ScenarioSummary } from '../types'
import { SimClockControls } from './SimClockControls'
import { TagChips } from './TagChips'
import { ForecastStrip } from './ForecastStrip'
import { AssumptionsPanel } from './AssumptionsPanel'
import type { DetailsTab } from '../layout/detailsTabs'

export function SeverityBanner({ state, scenarios, actions, busy, mock, stale, briefLine, flaggedFills, briefing, onBriefMe, onOpenDetails }: {
  state: IncidentStateDTO
  scenarios: ScenarioSummary[]
  actions: IncidentActions
  busy: boolean
  mock: boolean
  stale: boolean
  briefLine: string | null
  flaggedFills: number
  briefing: boolean
  onBriefMe: () => void
  onOpenDetails: (tab?: DetailsTab) => void
}) {
  const { severity, classifier, sim } = state
  const fund = state.signals.find((signal) => signal.code === 'INS_FUND_PCT')
  return <section className={`max-h-[150px] shrink-0 overflow-hidden border-b-4 px-4 py-1.5 md:px-6 ${severityTone[severity.sev] ?? severityTone[4]}`} aria-label="Incident status">
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span className="text-xl font-bold tracking-tight">SEV-{severity.sev} · {severity.state}</span>
      <span className="font-mono text-sm tabular">{sim.t_label}</span>
      <span className="text-xs opacity-75">{sim.scenario_name ?? 'No incident running'}</span>
      <TagChips tags={state.tags} />
      <span className="text-[11px] font-semibold">{classifier.verdict} · LAR {classifier.lar.toFixed(1)}</span>
      {flaggedFills > 0 && <button type="button" onClick={() => onOpenDetails('liquidations')} className="border border-amber-200 bg-amber-500 px-1.5 py-0.5 text-[11px] font-bold text-black">⚑ {flaggedFills} fills to review</button>}
      {severity.overrides.length > 0 && <span className="text-[10px]">Override: {severity.overrides.join(', ')}</span>}
      <span className="ml-auto flex flex-wrap items-center gap-2"><AssumptionsPanel />{mock && <span className="border border-white/35 px-1.5 py-0.5 text-[10px]">SAMPLE DATA</span>}{stale && <span className="border border-amber-200 bg-amber-500 px-1.5 py-0.5 text-[10px] text-black">CONNECTION STALE</span>}<SimClockControls state={state} scenarios={scenarios} actions={actions} busy={busy} /></span>
    </div>
    {briefLine && <p className="mt-0.5 truncate text-xs leading-snug opacity-90" title={briefLine}>{briefLine}</p>}
    <div className="mt-1 flex items-center gap-2">
      <div className="min-w-0 flex-1"><ForecastStrip forecast={state.forecast} fund={fund} t={sim.t} compact /></div>
      <button type="button" disabled={briefing} onClick={onBriefMe} className="shrink-0 border border-white/40 px-2 py-1 text-xs font-semibold hover:bg-white/10 disabled:opacity-50">{briefing ? 'Briefing…' : '🔊 Brief me'}</button>
      <button type="button" onClick={() => onOpenDetails()} className="shrink-0 border border-white bg-white px-2 py-1 text-xs font-semibold text-slate-900 hover:bg-slate-100">Details ▸</button>
    </div>
  </section>
}
